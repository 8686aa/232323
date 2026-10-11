package com.udpcast.sender

import android.util.Log
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.NetworkInterface

/**
 * 接收端发现：向局域网广播 UDPCAST_DISCOVER，等待在 5001 端口监听接收器回应。
 * 收到 UDPCAST_HERE 后返回对方 IP。
 *
 * ## 为什么广播地址要动态算
 *
 * 早期版本把候选广播地址写死成 `255.255.255.255 / 192.168.1.255 / 192.168.0.255`，
 * 这在 `192.168.137.0/24`（Windows 移动热点）这类网络下**必然失败**：
 * 真实广播地址是 192.168.137.255，不在列表里；另外两个发往不存在的网段；
 * 而 255.255.255.255 常被热点/AP 直接丢弃。
 *
 * 现在改为遍历本机网卡，**按实际 IP+掩码算出每个网段的广播地址**，
 * 因此 192.168.x/10.x/172.x 等任何网段都能自动适配。
 *
 * 另外补两个兜底目标：
 *  - 默认网关（热点场景下接收端往往就是网关这台电脑）
 *  - 组播地址 224.0.0.1（少数网络放行组播但拦广播）
 *
 * 全部失败也不影响使用 —— 手工填 IP 即可。
 */
object ReceiverDiscovery {

    private const val TAG = "ReceiverDiscovery"

    /** 无论网卡是什么配置，都额外尝试这几个目标 */
    private val EXTRA_TARGETS = listOf(
        "255.255.255.255",   // 受限广播
        "224.0.0.1",         // 全主机组播
    )

    /**
     * 收集所有应该发送发现请求的目标地址。
     *
     * @return 去重后的地址列表
     */
    private fun collectTargets(): List<String> {
        val targets = LinkedHashSet<String>()

        // 1) 每个 IPv4 网卡的网段广播地址
        try {
            val ifaces = NetworkInterface.getNetworkInterfaces()
            while (ifaces != null && ifaces.hasMoreElements()) {
                val nif = ifaces.nextElement()
                if (!nif.isUp || nif.isLoopback) continue

                for (ia in nif.interfaceAddresses) {
                    val addr = ia.address
                    if (addr !is InetAddress) continue
                    // 只要 IPv4（IPv4 地址返回 4 字节）
                    if (addr.address.size != 4) continue
                    val bcast = ia.broadcast
                    if (bcast != null) {
                        targets.add(bcast.hostAddress ?: continue)
                    }
                }
            }
        } catch (e: Exception) {
            Log.w(TAG, "枚举网卡失败: ${e.message}")
        }

        // 2) 默认网关。热点模式下接收端通常就是网关（192.168.137.1 这种）
        defaultGateway()?.let { targets.add(it) }

        // 3) 通用兜底
        targets.addAll(EXTRA_TARGETS)

        return targets.toList()
    }

    /**
     * 从 /proc/net/route 读默认网关。
     * 不需要任何权限，比走 ConnectivityManager 更省事（也就不用传 Context）。
     *
     * 该文件里 Gateway 是**小端序的 16 进制**，例如
     * `0189A8C0` 表示 192.168.137.1。
     */
    private fun defaultGateway(): String? = try {
        val lines = java.io.File("/proc/net/route").readLines()
        var gw: String? = null
        for (line in lines.drop(1)) {
            val f = line.trim().split(Regex("\\s+"))
            if (f.size < 3) continue
            // Destination == 00000000 表示默认路由
            if (f[1] != "00000000") continue
            val hex = f[2]
            if (hex.length != 8) continue
            // 小端序还原成点分十进制
            val b = ByteArray(4)
            for (i in 0 until 4) {
                b[i] = hex.substring((3 - i) * 2, (3 - i) * 2 + 2).toInt(16).toByte()
            }
            gw = InetAddress.getByAddress(b).hostAddress
            break
        }
        gw
    } catch (e: Exception) {
        Log.w(TAG, "读取默认网关失败: ${e.message}")
        null
    }

    /**
     * 搜索接收端。
     *
     * @param timeoutMs 总等待时间
     * @return 找到的接收端 IP；未找到返回 null
     */
    fun discover(timeoutMs: Int = 1500): String? {
        val targets = collectTargets()
        Log.i(TAG, "发现目标: $targets")

        DatagramSocket().use { socket ->
            socket.broadcast = true
            socket.soTimeout = 200
            socket.reuseAddress = true

            for (addr in targets) {
                try {
                    socket.send(
                        DatagramPacket(
                            CastProtocol.DISCOVER_REQ,
                            CastProtocol.DISCOVER_REQ.size,
                            InetAddress.getByName(addr),
                            CastProtocol.DISCOVER_PORT
                        )
                    )
                    Log.d(TAG, "已发送发现请求 -> $addr")
                } catch (e: Exception) {
                    // 单个目标失败无所谓，继续试下一个
                    Log.d(TAG, "发送到 $addr 失败: ${e.message}")
                }
            }

            val buf = ByteArray(256)
            val deadline = System.currentTimeMillis() + timeoutMs
            while (System.currentTimeMillis() < deadline) {
                val resp = DatagramPacket(buf, buf.size)
                try {
                    socket.receive(resp)
                } catch (_: Exception) {
                    continue
                }
                val text = String(resp.data, 0, resp.length, Charsets.UTF_8)
                if (text.startsWith(CastProtocol.DISCOVER_RSP_PREFIX)) {
                    val ip = resp.address?.hostAddress ?: continue
                    Log.i(TAG, "找到接收端 $ip ($text)")
                    return ip
                }
            }
            Log.i(TAG, "未发现接收端（已尝试 $targets）")
            return null
        }
    }

    /**
     * 校验用户手填的地址能否解析。
     * 注意：Android 上解析失败会抛 UnknownHostException，不会返回 null。
     */
    fun resolveHost(host: String): Boolean = try {
        InetAddress.getByName(host)
        true
    } catch (_: Exception) {
        false
    }
}
