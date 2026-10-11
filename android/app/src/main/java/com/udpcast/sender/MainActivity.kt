package com.udpcast.sender

import android.Manifest
import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.media.projection.MediaProjectionManager
import android.net.wifi.WifiManager
import android.os.Build
import android.os.Bundle
import android.text.format.Formatter
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.google.android.material.button.MaterialButton
import com.google.android.material.slider.Slider
import java.net.Inet4Address
import java.net.NetworkInterface

class MainActivity : AppCompatActivity() {

    companion object {
        private const val REQ_PROJECTION = 1001
        private const val REQ_NOTIFICATION = 1002
    }

    private lateinit var etHost: EditText
    private lateinit var etPort: EditText
    private lateinit var sliderBitrate: Slider
    private lateinit var sliderFps: Slider
    private lateinit var sliderScale: Slider
    private lateinit var tvBitrate: TextView
    private lateinit var tvFps: TextView
    private lateinit var tvScale: TextView
    private lateinit var tvStatus: TextView
    private lateinit var tvLocalInfo: TextView
    private lateinit var btnStart: MaterialButton
    private lateinit var btnStop: MaterialButton
    private lateinit var btnDiscover: MaterialButton

    private val statsReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            val text = intent?.getStringExtra(ScreenCastService.EXTRA_STATS_TEXT) ?: return
            tvStatus.text = text
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        etHost = findViewById(R.id.etHost)
        etPort = findViewById(R.id.etPort)
        sliderBitrate = findViewById(R.id.sliderBitrate)
        sliderFps = findViewById(R.id.sliderFps)
        sliderScale = findViewById(R.id.sliderScale)
        tvBitrate = findViewById(R.id.tvBitrate)
        tvFps = findViewById(R.id.tvFps)
        tvScale = findViewById(R.id.tvScale)
        tvStatus = findViewById(R.id.tvStatus)
        tvLocalInfo = findViewById(R.id.tvLocalInfo)
        btnStart = findViewById(R.id.btnStart)
        btnStop = findViewById(R.id.btnStop)
        btnDiscover = findViewById(R.id.btnDiscover)

        bindSliders()
        requestNotificationPermissionIfNeeded()

        btnStart.setOnClickListener { onStartClicked() }
        btnStop.setOnClickListener { onStopClicked() }
        btnDiscover.setOnClickListener { onDiscoverClicked() }

        tvLocalInfo.text = "本机：${localIpv4() ?: "未连接 Wi-Fi"}"
    }

    override fun onResume() {
        super.onResume()
        val filter = IntentFilter(ScreenCastService.ACTION_STATS)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(statsReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            @Suppress("UnspecifiedRegisterReceiverFlag")
            registerReceiver(statsReceiver, filter)
        }
    }

    override fun onPause() {
        try {
            unregisterReceiver(statsReceiver)
        } catch (_: Throwable) {
        }
        super.onPause()
    }

    // ------------------------------------------------------------------
    // 参数面板

    private fun bindSliders() {
        sliderBitrate.addOnChangeListener { _, value, _ ->
            tvBitrate.text = "码率  ${value.toInt()} Mbps"
        }
        tvBitrate.text = "码率  ${sliderBitrate.value.toInt()} Mbps"

        sliderFps.addOnChangeListener { _, value, _ ->
            tvFps.text = "帧率  ${value.toInt()} fps"
        }
        tvFps.text = "帧率  ${sliderFps.value.toInt()} fps"

        sliderScale.addOnChangeListener { _, value, _ ->
            tvScale.text = "分辨率缩放  ${scaleLabel(value.toInt())}"
        }
        tvScale.text = "分辨率缩放  ${scaleLabel(sliderScale.value.toInt())}"
    }

    private fun scaleLabel(v: Int): String = when (v) {
        1 -> "25%"
        2 -> "50%"
        3 -> "75%"
        else -> "100%"
    }

    private fun scaleOf(v: Int): Float = v / 4f

    // ------------------------------------------------------------------
    // 动作

    private fun onStartClicked() {
        val host = etHost.text.toString().trim()
        if (host.isEmpty()) {
            toast("请先填写接收端 IP")
            return
        }
        val port = etPort.text.toString().trim().toIntOrNull()
        if (port == null || port !in 1..65535) {
            toast("端口不合法")
            return
        }

        val mpm = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        startActivityForResult(mpm.createScreenCaptureIntent(), REQ_PROJECTION)
    }

    private fun onStopClicked() {
        ScreenCastService.stop(this)
        setCastingUi(false)
        tvStatus.text = "已停止"
    }

    private fun onDiscoverClicked() {
        btnDiscover.isEnabled = false
        tvStatus.text = "正在搜索接收端…"
        Thread {
            val ip = ReceiverDiscovery.discover()
            runOnUiThread {
                btnDiscover.isEnabled = true
                if (ip != null) {
                    etHost.setText(ip)
                    tvStatus.text = "已发现接收端：$ip"
                } else {
                    tvStatus.text = "未发现接收端。\n请在 PC 上运行 receiver.py 后重试，或手动填写 IP。"
                }
            }
        }.start()
    }

    @Suppress("DEPRECATION")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)

        if (requestCode != REQ_PROJECTION) return

        if (resultCode != Activity.RESULT_OK || data == null) {
            tvStatus.text = "用户取消了录屏授权"
            return
        }

        val host = etHost.text.toString().trim()
        val port = etPort.text.toString().trim().toIntOrNull() ?: 5000
        val bitRate = (sliderBitrate.value.toInt()) * 1_000_000
        val fps = sliderFps.value.toInt()
        val scale = scaleOf(sliderScale.value.toInt())

        ScreenCastService.start(
            ctx = this,
            resultCode = resultCode,
            resultData = data,
            host = host,
            port = port,
            bitRate = bitRate,
            fps = fps,
            scale = scale
        )

        setCastingUi(true)
        tvStatus.text = "启动中…"
    }

    // ------------------------------------------------------------------

    private fun setCastingUi(active: Boolean) {
        btnStart.isEnabled = !active
        btnStop.isEnabled = active
        etHost.isEnabled = !active
        etPort.isEnabled = !active
        sliderBitrate.isEnabled = !active
        sliderFps.isEnabled = !active
        sliderScale.isEnabled = !active
        btnDiscover.isEnabled = !active
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
            == PackageManager.PERMISSION_GRANTED
        ) return

        ActivityCompat.requestPermissions(
            this,
            arrayOf(Manifest.permission.POST_NOTIFICATIONS),
            REQ_NOTIFICATION
        )
    }

    private fun toast(msg: String) = Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()

    /** 取本机 Wi-Fi 上的 IPv4，用于让用户确认手机和 PC 在同一网段 */
    private fun localIpv4(): String? = try {
        NetworkInterface.getNetworkInterfaces().toList()
            .filter { it.isUp && !it.isLoopback }
            .flatMap { it.inetAddresses.toList() }
            .filterIsInstance<Inet4Address>()
            .firstOrNull { !it.isLoopbackAddress }
            ?.hostAddress
            ?: run {
                @Suppress("DEPRECATION")
                val wm = applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
                Formatter.formatIpAddress(wm.connectionInfo.ipAddress)
            }
    } catch (_: Throwable) {
        null
    }
}
