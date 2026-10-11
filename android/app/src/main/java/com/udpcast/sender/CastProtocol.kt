package com.udpcast.sender

/**
 * UDP 投屏协议 v1.0
 *
 * 三端（Android 发送 / iOS 发送 / PC 接收）字节级一致，任何一端改动都必须同步。
 *
 * 单个 UDP 包布局（全部大端序 Big-Endian）：
 *
 *   偏移   长度   字段          说明
 *   ---------------------------------------------------------------
 *   0      4      magic         0x55 0x44 0x50 0x31  ("UDP1")
 *   4      4      frameId       uint32，单调递增；同一帧的所有分片相同
 *   8      2      packetIndex   uint16，本分片在该帧内的序号，从 0 开始
 *   10     2      packetCount   uint16，该帧分片总数（>=1）
 *   12     1      flags         bit0=关键帧  bit1=编解码器配置  bit2=帧结束(未使用)
 *   13     1      reserved      保留，固定 0x00
 *   14     2      payloadLen    uint16，负载字节数（<= MAX_PAYLOAD）
 *   16     N      payload       H.264 Annex-B 裸流字节
 *
 * 发送端行为约定：
 *  - 每个关键帧前会先附上 SPS/PPS（MediaCodec 的 CODEC_CONFIG buffer），
 *    与关键帧数据拼成一个逻辑帧一起发送，因此关键帧天然可独立解码。
 *    UDP 丢包后接收端最多等待下一个关键帧即可恢复，不需要 NACK/重传。
 *  - 发送端不做重传；接收端按 frameId 组包，超时未集齐直接丢弃该帧。
 */
object CastProtocol {

    /** 包头长度 */
    const val HEADER_SIZE = 16

    /** 单个 UDP 数据报总长度上限（含包头）。1400 可安全穿过绝大多数以太网/Wi-Fi MTU=1500 */
    const val MTU = 1400

    /** 单包最大负载 */
    const val MAX_PAYLOAD = MTU - HEADER_SIZE   // 1384

    /** flags 位定义 */
    const val FLAG_KEYFRAME = 1 shl 0
    const val FLAG_CONFIG = 1 shl 1
    const val FLAG_END = 1 shl 2

    /** 发现服务：发送端向局域网广播该端口寻找接收端 */
    const val DISCOVER_PORT = 5001
    val DISCOVER_REQ: ByteArray = "UDPCAST_DISCOVER".toByteArray(Charsets.US_ASCII)
    const val DISCOVER_RSP_PREFIX = "UDPCAST_HERE"

    /**
     * 把一个分片的包头写入 [buf] 的前 16 字节。
     * [buf] 长度至少为 [HEADER_SIZE]。
     */
    fun writeHeader(
        buf: ByteArray,
        frameId: Int,
        index: Int,
        count: Int,
        flags: Int,
        len: Int
    ) {
        buf[0] = 0x55
        buf[1] = 0x44
        buf[2] = 0x50
        buf[3] = 0x31
        buf[4] = (frameId ushr 24).toByte()
        buf[5] = (frameId ushr 16).toByte()
        buf[6] = (frameId ushr 8).toByte()
        buf[7] = frameId.toByte()
        buf[8] = (index ushr 8).toByte()
        buf[9] = index.toByte()
        buf[10] = (count ushr 8).toByte()
        buf[11] = count.toByte()
        buf[12] = flags.toByte()
        buf[13] = 0
        buf[14] = (len ushr 8).toByte()
        buf[15] = len.toByte()
    }
}
