import Foundation
import Darwin

/// 局域网发现：广播 `UDPCAST_DISCOVER` 并等待接收器回 `UDPCAST_HERE`，
/// 从而拿到 PC 的 IP。
///
/// 放在 Shared 里，**主 App 和广播扩展共用**。扩展侧会用它在拿不到
/// App Group 配置时自行定位接收端 —— 这是自签场景下能正常投屏的关键。
///
/// 用 BSD socket 而不是 Network.framework：后者的 UDP 广播需要手动构造
/// NWEndpoint，且对 255.255.255.255 的支持不稳定。
public enum UdpDiscovery {

    /// 单次发现的同步阻塞时长。
    /// 广播扩展里这个值会占用启动时间，1.2 秒是「尽量找到」和「别拖太久」的折中。
    public static let defaultTimeout: TimeInterval = 1.2

    /// 广播到的目标地址。255.255.255.255 在部分路由器上会被丢弃，
    /// 所以再补发子网定向广播。
    private static let broadcastTargets = [
        "255.255.255.255",
        "192.168.1.255",
        "192.168.137.255",
        "192.168.0.255",
        "10.0.0.255",
    ]

    /// 同步发现接收端。
    /// - Parameter timeout: 总超时
    /// - Returns: 接收端 IP，未找到返回 nil
    public static func discover(timeout: TimeInterval = defaultTimeout) -> String? {
        let fd = socket(AF_INET, SOCK_DGRAM, 0)
        guard fd >= 0 else { return nil }
        defer { close(fd) }

        var on: Int32 = 1
        _ = setsockopt(fd, SOL_SOCKET, SO_BROADCAST, &on, socklen_t(MemoryLayout<Int32>.size))

        var tv = timeval(tv_sec: 1, tv_usec: 0)
        _ = setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, socklen_t(MemoryLayout<timeval>.size))

        let req = CastProtocol.discoverRequest

        // 主广播地址 + 各子网广播地址，各发一次
        for target in broadcastTargets {
            var addr = sockaddr_in()
            addr.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
            addr.sin_family = sa_family_t(AF_INET)
            addr.sin_port = CastProtocol.discoverPort.bigEndian
            addr.sin_addr.s_addr = inet_addr(target)

            req.withUnsafeBytes { raw in
                var a = addr
                withUnsafePointer(to: &a) { p in
                    p.withMemoryRebound(to: sockaddr.self, capacity: 1) { sa in
                        _ = sendto(
                            fd,
                            raw.baseAddress,
                            raw.count,
                            0,
                            sa,
                            socklen_t(MemoryLayout<sockaddr_in>.size)
                        )
                    }
                }
            }
        }

        let deadline = Date().addingTimeInterval(timeout)
        var buf = [UInt8](repeating: 0, count: 512)

        while Date() < deadline {
            var from = sockaddr_storage()
            var fromLen = socklen_t(MemoryLayout<sockaddr_storage>.size)

            let n = withUnsafeMutablePointer(to: &from) { fp -> Int in
                fp.withMemoryRebound(to: sockaddr.self, capacity: 1) { sa in
                    buf.withUnsafeMutableBytes { bp -> Int in
                        recvfrom(fd, bp.baseAddress, bp.count, 0, sa, &fromLen)
                    }
                }
            }
            guard n > 0 else { continue }

            guard let text = String(bytes: buf[0..<n], encoding: .utf8),
                  text.hasPrefix(CastProtocol.discoverResponsePrefix) else { continue }

            var hostBuf = [CChar](repeating: 0, count: Int(NI_MAXHOST))
            let r = withUnsafePointer(to: &from) { fp -> Int32 in
                fp.withMemoryRebound(to: sockaddr.self, capacity: 1) { sa in
                    getnameinfo(
                        sa,
                        fromLen,
                        &hostBuf,
                        socklen_t(hostBuf.count),
                        nil,
                        0,
                        NI_NUMERICHOST
                    )
                }
            }
            if r == 0 {
                return String(cString: hostBuf)
            }
        }
        return nil
    }
}
