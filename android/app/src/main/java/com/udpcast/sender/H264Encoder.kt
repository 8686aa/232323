package com.udpcast.sender

import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.os.Build
import android.util.Log
import android.view.Surface

/**
 * 基于 MediaCodec 的 H.264 硬编码器。
 *
 * 使用 Surface 输入模式：由 VirtualDisplay 直接把屏幕画面渲染到
 * [inputSurface]，无需 CPU 参与像素拷贝，功耗和延迟都最优。
 *
 * 输出线程把所有编码结果回调给 [onFrame]：
 *  - CODEC_CONFIG（SPS/PPS）会被缓存；
 *  - 遇到关键帧时，把缓存的 SPS/PPS 前置拼接到关键帧数据上一起回调，
 *    这样每个关键帧都能独立解码，UDP 丢包后接收端能自愈。
 */
class H264Encoder(
    private val width: Int,
    private val height: Int,
    private val bitRate: Int,
    private val frameRate: Int,
    private val iFrameIntervalSec: Int,
    private val onFrame: (data: ByteArray, flags: Int) -> Unit
) {

    companion object {
        private const val TAG = "H264Encoder"
        private const val MIME = MediaFormat.MIMETYPE_VIDEO_AVC
    }

    var inputSurface: Surface? = null
        private set

    private var codec: MediaCodec? = null
    private var outputThread: Thread? = null

    @Volatile
    private var running = false

    /** 缓存的 SPS/PPS（CODEC_CONFIG） */
    @Volatile
    private var codecConfig: ByteArray? = null

    /**
     * 创建并启动编码器，返回待渲染的输入 Surface。
     * 必须在创建 VirtualDisplay 之前调用。
     */
    fun prepare(): Surface {
        val format = MediaFormat.createVideoFormat(MIME, width, height).apply {
            setInteger(
                MediaFormat.KEY_COLOR_FORMAT,
                MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface
            )
            setInteger(MediaFormat.KEY_BIT_RATE, bitRate)
            setInteger(MediaFormat.KEY_FRAME_RATE, frameRate)
            setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, iFrameIntervalSec)
            // 恒定码率，弱网下画面更稳
            setInteger(
                MediaFormat.KEY_BITRATE_MODE,
                MediaCodecInfo.EncoderCapabilities.BITRATE_MODE_CBR
            )
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                // 屏幕内容：允许编码器在画面长时间静止时重复上一帧，
                // 既保持低延迟又能大幅省码率
                setLong(MediaFormat.KEY_REPEAT_PREVIOUS_FRAME_AFTER, 100_000L) // 100ms
            }
        }

        val c = MediaCodec.createEncoderByType(MIME)
        c.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        val surface = c.createInputSurface()
        c.start()

        codec = c
        inputSurface = surface
        Log.i(TAG, "encoder ready ${width}x${height} @${frameRate}fps ${bitRate / 1000}kbps")
        return surface
    }

    /** 启动输出泵线程（在 VirtualDisplay 创建之后调用） */
    fun start() {
        if (running) return
        running = true
        outputThread = Thread({ drain() }, "h264-drain").apply {
            priority = Thread.MAX_PRIORITY
            start()
        }
    }

    /** 运行时动态调码率（不重建编码器） */
    fun updateBitRate(newBitRate: Int) {
        val c = codec ?: return
        try {
            val params = android.os.Bundle().apply {
                putInt(MediaCodec.PARAMETER_KEY_VIDEO_BITRATE, newBitRate)
            }
            c.setParameters(params)
        } catch (e: Throwable) {
            Log.w(TAG, "updateBitRate failed: ${e.message}")
        }
    }

    /** 立刻强制一个关键帧 */
    fun requestKeyFrame() {
        val c = codec ?: return
        try {
            val params = android.os.Bundle().apply {
                putInt(MediaCodec.PARAMETER_KEY_REQUEST_SYNC_FRAME, 0)
            }
            c.setParameters(params)
        } catch (e: Throwable) {
            Log.w(TAG, "requestKeyFrame failed: ${e.message}")
        }
    }

    fun stop() {
        running = false
        outputThread?.interrupt()
        outputThread = null

        try {
            codec?.stop()
        } catch (_: Throwable) {
        }
        try {
            codec?.release()
        } catch (_: Throwable) {
        }
        codec = null

        try {
            inputSurface?.release()
        } catch (_: Throwable) {
        }
        inputSurface = null
        Log.i(TAG, "encoder stopped")
    }

    // ------------------------------------------------------------------

    private fun drain() {
        val c = codec ?: return
        val info = MediaCodec.BufferInfo()

        while (running) {
            val index = try {
                c.dequeueOutputBuffer(info, 10_000L)
            } catch (e: IllegalStateException) {
                Log.w(TAG, "dequeue failed: ${e.message}")
                break
            }

            when {
                index == MediaCodec.INFO_TRY_AGAIN_LATER -> continue

                index == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                    Log.i(TAG, "output format: ${c.outputFormat}")
                    continue
                }

                index >= 0 -> {
                    if (info.size <= 0) {
                        c.releaseOutputBuffer(index, false)
                        continue
                    }
                    val buf = c.getOutputBuffer(index)
                    if (buf == null) {
                        c.releaseOutputBuffer(index, false)
                        continue
                    }
                    buf.position(info.offset)
                    buf.limit(info.offset + info.size)
                    val data = ByteArray(info.size)
                    buf.get(data)
                    c.releaseOutputBuffer(index, false)

                    val isConfig = info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG != 0
                    if (isConfig) {
                        codecConfig = data
                        continue
                    }

                    val isKey = info.flags and MediaCodec.BUFFER_FLAG_KEY_FRAME != 0
                    val cfg = codecConfig
                    if (isKey && cfg != null) {
                        // SPS/PPS + IDR 拼成可独立解码的一帧
                        onFrame(cfg + data, CastProtocol.FLAG_KEYFRAME)
                    } else {
                        onFrame(data, if (isKey) CastProtocol.FLAG_KEYFRAME else 0)
                    }
                }
            }
        }
    }
}
