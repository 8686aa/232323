package com.udpcast.sender

import android.util.Log
import java.io.IOException
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetSocketAddress
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicLong

/**
 * 把已编码的 H.264 帧切分成 UDP 分片并发送。
 *
 * 设计要点：
 *  - 编码线程调用 [offer] 只做「切包 + 入队」，绝不阻塞 MediaCodec 的输出循环。
 *  - 独立发送线程从队列取包落 socket，网络拥塞时丢帧而不是拖慢编码。
 *  - 队列接近满时整帧丢弃（保证不会发出半帧数据，接收端不会白等）。
 */
class UdpFrameSender(
    private val host: String,
    private val port: Int,
    private val queueCapacityFrames: Int = 64
) {

    companion object {
        private const val TAG = "UdpFrameSender"
    }

    private val socket: DatagramSocket = DatagramSocket()
    private val target = InetSocketAddress(host, port)

    /** 队列元素是「已经带好包头、可以直接 send 的完整数据报」 */
    private val queue = LinkedBlockingQueue<ByteArray>(queueCapacityFrames * 8)

    private val frameIdGen = AtomicInteger(0)

    @Volatile
    private var running = false
    private var thread: Thread? = null

    /** 统计：已发送数据报 / 已丢弃整帧 / 已发送帧数 */
    val sentPackets = AtomicLong(0)
    val droppedFrames = AtomicLong(0)
    val sentFrames = AtomicLong(0)

    fun start() {
        if (running) return
        running = true
        thread = Thread({ loop() }, "udp-sender").apply {
            priority = Thread.MAX_PRIORITY
            start()
        }
    }

    fun stop() {
        running = false
        thread?.interrupt()
        thread = null
        try {
            socket.close()
        } catch (_: Throwable) {
        }
    }

    /**
     * 提交一帧。内部完成分片与入队。
     * @param payload H.264 Annex-B 裸流（关键帧时应已前置 SPS/PPS）
     * @param flags   CastProtocol 中定义的 flags 位
     */
    fun offer(payload: ByteArray, flags: Int) {
        if (!running || payload.isEmpty()) return

        val count = (payload.size + CastProtocol.MAX_PAYLOAD - 1) / CastProtocol.MAX_PAYLOAD
        if (count <= 0 || count > 0xFFFF) return

        // 队列余量不足以容纳整帧 -> 丢整帧，避免把半帧塞进去
        if (queue.remainingCapacity() < count) {
            droppedFrames.incrementAndGet()
            return
        }

        val fid = frameIdGen.incrementAndGet()
        for (i in 0 until count) {
            val offset = i * CastProtocol.MAX_PAYLOAD
            val len = minOf(CastProtocol.MAX_PAYLOAD, payload.size - offset)
            val pkt = ByteArray(CastProtocol.HEADER_SIZE + len)
            CastProtocol.writeHeader(pkt, fid, i, count, flags, len)
            System.arraycopy(payload, offset, pkt, CastProtocol.HEADER_SIZE, len)
            if (!queue.offer(pkt)) {
                droppedFrames.incrementAndGet()
                return
            }
        }
        sentFrames.incrementAndGet()
    }

    private fun loop() {
        while (running || queue.isNotEmpty()) {
            val pkt = try {
                queue.poll(200, TimeUnit.MILLISECONDS)
            } catch (_: InterruptedException) {
                if (!running) break else continue
            } ?: continue

            try {
                socket.send(DatagramPacket(pkt, pkt.size, target))
                sentPackets.incrementAndGet()
            } catch (e: IOException) {
                // 网络切换 / socket 已关闭：不致命，等下一次成功
                if (running) Log.w(TAG, "send failed: ${e.message}")
            }
        }
    }
}
