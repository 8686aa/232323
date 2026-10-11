package com.udpcast.sender

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.IBinder
import android.util.Log

/**
 * 投屏前台服务。
 *
 * 职责链：
 *   MediaProjection  ->  VirtualDisplay  ->  MediaCodec(InputSurface)  ->  UdpFrameSender
 *
 * Android 14 (API 34) 的硬性顺序要求：
 *   1. 先 startForeground(type = mediaProjection)
 *   2. 再 getMediaProjection(resultCode, data)
 *   3. 注册 MediaProjection.Callback
 *   4. 最后 createVirtualDisplay
 * 顺序颠倒会直接抛 SecurityException。
 */
class ScreenCastService : Service() {

    companion object {
        private const val TAG = "ScreenCastService"

        const val ACTION_START = "com.udpcast.sender.START"
        const val ACTION_STOP = "com.udpcast.sender.STOP"

        const val EXTRA_RESULT_CODE = "result_code"
        const val EXTRA_RESULT_DATA = "result_data"
        const val EXTRA_HOST = "host"
        const val EXTRA_PORT = "port"
        const val EXTRA_BITRATE = "bitrate"
        const val EXTRA_FPS = "fps"
        const val EXTRA_SCALE = "scale"

        /** 广播本地统计信息，供 UI 刷新 */
        const val ACTION_STATS = "com.udpcast.sender.STATS"
        const val EXTRA_STATS_TEXT = "stats_text"

        private const val CHANNEL_ID = "udpcast_channel"
        private const val NOTIF_ID = 0xC0DE

        fun start(
            ctx: Context,
            resultCode: Int,
            resultData: Intent,
            host: String,
            port: Int,
            bitRate: Int,
            fps: Int,
            scale: Float
        ) {
            val i = Intent(ctx, ScreenCastService::class.java).apply {
                action = ACTION_START
                putExtra(EXTRA_RESULT_CODE, resultCode)
                putExtra(EXTRA_RESULT_DATA, resultData)
                putExtra(EXTRA_HOST, host)
                putExtra(EXTRA_PORT, port)
                putExtra(EXTRA_BITRATE, bitRate)
                putExtra(EXTRA_FPS, fps)
                putExtra(EXTRA_SCALE, scale)
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                ctx.startForegroundService(i)
            } else {
                ctx.startService(i)
            }
        }

        fun stop(ctx: Context) {
            ctx.startService(
                Intent(ctx, ScreenCastService::class.java).apply { action = ACTION_STOP }
            )
        }
    }

    private var projection: MediaProjection? = null
    private var virtualDisplay: VirtualDisplay? = null
    private var encoder: H264Encoder? = null
    private var sender: UdpFrameSender? = null

    private var projectionCallback: MediaProjection.Callback? = null
    private var encoderThread: HandlerThread? = null
    private var encoderHandler: Handler? = null
    private var statsHandler: Handler? = null

    private var outWidth = 0
    private var outHeight = 0
    private var configuredBitrate = 0

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            Log.i(TAG, "stop requested")
            teardown()
            stopForegroundCompat()
            stopSelf()
            return START_NOT_STICKY
        }

        val resultCode = intent?.getIntExtra(EXTRA_RESULT_CODE, 0) ?: 0
        val resultData = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            intent?.getParcelableExtra(EXTRA_RESULT_DATA, Intent::class.java)
        } else {
            @Suppress("DEPRECATION")
            intent?.getParcelableExtra<Intent>(EXTRA_RESULT_DATA)
        }
        val host = intent?.getStringExtra(EXTRA_HOST)
        val port = intent?.getIntExtra(EXTRA_PORT, 5000) ?: 5000
        val bitRate = intent?.getIntExtra(EXTRA_BITRATE, 8_000_000) ?: 8_000_000
        val fps = intent?.getIntExtra(EXTRA_FPS, 30) ?: 30
        val scale = intent?.getFloatExtra(EXTRA_SCALE, 0.5f) ?: 0.5f

        if (resultData == null || host.isNullOrBlank()) {
            Log.e(TAG, "invalid start intent (resultData=$resultData host=$host)")
            stopSelf()
            return START_NOT_STICKY
        }

        // ---- 1. 必须先转前台（Android 14 要求 mediaProjection FGS 先于 getMediaProjection）----
        createChannel()
        startForegroundCompat()

        return try {
            startPipeline(resultCode, resultData, host, port, bitRate, fps, scale)
            START_NOT_STICKY
        } catch (t: Throwable) {
            Log.e(TAG, "startPipeline failed", t)
            broadcastStats("启动失败：${t.message}")
            teardown()
            stopForegroundCompat()
            stopSelf()
            START_NOT_STICKY
        }
    }

    // ------------------------------------------------------------------

    private fun startPipeline(
        resultCode: Int,
        resultData: Intent,
        host: String,
        port: Int,
        bitRate: Int,
        fps: Int,
        scale: Float
    ) {
        val mpm = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager

        // ---- 2. 拿到 MediaProjection ----
        val mp = mpm.getMediaProjection(resultCode, resultData)
            ?: throw IllegalStateException("getMediaProjection 返回 null，录屏授权可能已失效")

        // ---- 3. 必须注册 Callback（且在 createVirtualDisplay 之前）----
        val cb = object : MediaProjection.Callback() {
            override fun onStop() {
                Log.i(TAG, "MediaProjection stopped by user/system")
                broadcastStats("录屏授权已结束")
                teardown()
                stopForegroundCompat()
                stopSelf()
            }
        }
        mp.registerCallback(cb, Handler(mainLooper))
        projectionCallback = cb
        projection = mp

        // ---- 计算编码尺寸（对齐到 16 的倍数，兼容各类硬编）----
        val dm = resources.displayMetrics
        val srcW = dm.widthPixels
        val srcH = dm.heightPixels
        val dpi = dm.densityDpi

        outWidth = align16((srcW * scale).toInt())
        outHeight = align16((srcH * scale).toInt())
        configuredBitrate = bitRate

        // ---- 4. 编码器 + 发送器 ----
        val s = UdpFrameSender(host, port).also {
            it.start()
            sender = it
        }

        val enc = H264Encoder(
            width = outWidth,
            height = outHeight,
            bitRate = bitRate,
            frameRate = fps,
            iFrameIntervalSec = 2,
            onFrame = { data, flags -> s.offer(data, flags) }
        )
        val surface = enc.prepare()
        encoder = enc

        val ht = HandlerThread("udpcast-encoder").apply { start() }
        encoderThread = ht
        val handler = Handler(ht.looper).also { encoderHandler = it }

        // ---- 5. VirtualDisplay 把屏幕渲染进编码器 Surface ----
        virtualDisplay = mp.createVirtualDisplay(
            "UdpCastVirtualDisplay",
            outWidth,
            outHeight,
            dpi,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
            surface,
            null,
            handler
        )

        enc.start()

        Log.i(TAG, "casting ${srcW}x${srcH} -> ${outWidth}x${outHeight} @${fps}fps " +
                "${bitRate / 1000}kbps -> $host:$port")
        broadcastStats("投屏中 ${outWidth}x$outHeight @${fps}fps → $host:$port")

        startStatsTicker()
    }

    private fun align16(v: Int): Int {
        val a = (v / 16) * 16
        return if (a < 16) 16 else a
    }

    // ------------------------------------------------------------------

    private fun startStatsTicker() {
        val h = Handler(mainLooper)
        statsHandler = h
        val tick = object : Runnable {
            override fun run() {
                val s = sender ?: return
                val packets = s.sentPackets.get()
                val frames = s.sentFrames.get()
                val drops = s.droppedFrames.get()
                broadcastStats(
                    "投屏中 ${outWidth}x$outHeight  码率 ${configuredBitrate / 1000}kbps\n" +
                            "帧 $frames  数据报 $packets  丢帧 $drops\n" +
                            "≈ ${packets * CastProtocol.MTU / 1024 / 2} KB/s"
                )
                h.postDelayed(this, 1000L)
            }
        }
        h.postDelayed(tick, 1000L)
    }

    private fun broadcastStats(text: String) {
        sendBroadcast(
            Intent(ACTION_STATS).setPackage(packageName).putExtra(EXTRA_STATS_TEXT, text)
        )
    }

    // ------------------------------------------------------------------

    private fun teardown() {
        statsHandler?.removeCallbacksAndMessages(null)
        statsHandler = null

        try {
            virtualDisplay?.release()
        } catch (_: Throwable) {
        }
        virtualDisplay = null

        encoder?.stop()
        encoder = null

        sender?.stop()
        sender = null

        projectionCallback?.let { cb ->
            try {
                projection?.unregisterCallback(cb)
            } catch (_: Throwable) {
            }
        }
        projectionCallback = null

        try {
            projection?.stop()
        } catch (_: Throwable) {
        }
        projection = null

        encoderThread?.quitSafely()
        encoderThread = null
        encoderHandler = null

        Log.i(TAG, "teardown done")
    }

    override fun onDestroy() {
        teardown()
        super.onDestroy()
    }

    // ------------------------------------------------------------------
    // 通知

    private fun createChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val nm = getSystemService(NotificationManager::class.java)
        if (nm.getNotificationChannel(CHANNEL_ID) != null) return

        val ch = NotificationChannel(
            CHANNEL_ID,
            getString(R.string.notif_channel_name),
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            setShowBadge(false)
            description = "屏幕投屏运行时的常驻通知"
        }
        nm.createNotificationChannel(ch)
    }

    private fun buildNotification(): Notification {
        val open = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val stopIntent = PendingIntent.getService(
            this,
            1,
            Intent(this, ScreenCastService::class.java).apply { action = ACTION_STOP },
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, CHANNEL_ID)
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
        }

        return builder
            .setContentTitle(getString(R.string.notif_title))
            .setSmallIcon(R.drawable.ic_notification)
            .setContentIntent(open)
            .setOngoing(true)
            .addAction(
                Notification.Action.Builder(
                    null,
                    getString(R.string.notif_stop),
                    stopIntent
                ).build()
            )
            .build()
    }

    private fun startForegroundCompat() {
        val n = buildNotification()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIF_ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION)
        } else {
            startForeground(NOTIF_ID, n)
        }
    }

    private fun stopForegroundCompat() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            stopForeground(STOP_FOREGROUND_REMOVE)
        } else {
            @Suppress("DEPRECATION")
            stopForeground(true)
        }
    }
}
