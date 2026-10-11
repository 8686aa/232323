package com.udpcast.sender

import android.util.Log
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress

/**
 * 接收端发现：向局域网广播 UDPCAST_DISCOVER，等待在 5001 端口监听接收器回应。
 * 收到 UDPCAST_HERE 后返回对方 IP。
 *
 * 收不到回应也不影响使用 —— 手工填 IP 即可。部分路由器/AP 隔离会拦截广播。
 */
object ReceiverDiscovery {

    private const val TAG = "ReceiverDiscovery"
    private val BROADCAST_ADDRS = listOf("255.255.255.255", "192.168.1.255", "192.168.0.255")

    /**
     * @param timeoutMs 单个广播地址的等待时间
     * @return 找到的接收端 IP；未找到返回 null
     */
    fun discover(timeoutMs: Int = 1500): String? {
        DatagramSocket().use { socket ->
            socket.broadcast = true
            socket.soTimeout = timeoutMs
            socket.reuseAddress = true

            val req = DatagramPacket(
                CastProtocol.DISCOVER_REQ,
                CastProtocol.DISCOVER_REQ.size,
                InetAddress.getByName("255.255.255.255"),
                CastProtocol.DISCOVER_PORT
            )

            try {
                socket.send(req)
            } catch (e: Exception) {
                Log.w(TAG, "broadcast failed: ${e.message}")
            }

            // 有些网络环境下 255.255.255.255 被丢弃，补发子网广播地址
            for (addr in BROADCAST_ADDRS) {
                try {
                    socket.send(
                        DatagramPacket(
                            CastProtocol.DISCOVER_REQ,
                            CastProtocol.DISCOVER_REQ.size,
                            InetAddress.getByName(addr),
                            CastProtocol.DISCOVER_PORT
                        )
                    )
                } catch (_: Exception) {
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
                    Log.i(TAG, "found receiver at $ip ($text)")
                    return ip
                }
            }
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
