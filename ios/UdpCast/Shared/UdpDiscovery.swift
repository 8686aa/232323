import Foundation
import Darwin
import Network

/// 局域网发现：广播 `UDPCAST_DISCOVER` 并等待接收器回 `UDPCAST_HERE`。
///
/// 放在 Shared 里，**主 App 和广播扩展共用**。
///
/// ## 这一版修掉的问题（都是真机上「搜不到接收端」的原因）
///
/// 1. **广播地址写死**
///    旧版硬编码 `192.168.1.255 / 192.168.0.255 / 10.0.0.255` 等几个地址。
///    一旦实际网段不在这个列表里（例如 `192.168.110.0/24`），
///    包就发到了根本不存在的网段。现在改为用 `getifaddrs` 遍历网卡，
///    **按实际 IP+掩码算出每个接口的广播地址**，任何网段都自动适配。
///
/// 2. **`sendto` 的返回值被忽略**
///    权限被拒、网卡不可用时 `sendto` 会失败并设置 errno，但旧代码
///    写的是 `_ = sendto(...)`，失败与否完全看不出来，
///    界面上只表现为「搜不到」，无从排查。现在逐个记录错误并回报给 UI。
///
/// 3. **没有主动申请「本地网络」权限**
///    iOS 14+ 起，App 访问局域网需要用户授权。但**只声明
///    `NSLocalNetworkUsageDescription` 并不会弹窗** —— 必须实际发起
///    本地网络访问。而且实测纯 UDP 广播经常不触发弹窗，导致权限一直
///    处于「未决定」，系统静默丢弃所有出站局域网包。
///    现在用 `NWBrowser` 做一次 Bonjour 浏览，可靠地把弹窗拉起来。
///
/// 4. **多接口时选错出口**
///    iPhone 常同时有 Wi-Fi 和蜂窝。不绑定接口时，系统可能把广播
///    从蜂窝送出去（必然失败）。现在**对每个具备广播能力的接口单独建 socket
///    并 bind 到该接口的 IP**，确保走的是 Wi-Fi。
public enum UdpDiscovery {

    /// 单次发现的同步阻塞时长。
    /// 广播扩展里这个值会占用启动时间，1.5 秒是「尽量找到」和「别拖太久」的折中。
    public static let defaultTimeout: TimeInterval = 1.5

    // MARK: - 数据结构

    /// 一个具备广播能力的网络接口
    public struct CastInterface {
        public let name: String
        public let ip: String
        public let broadcast: String
    }

    /// 发现过程的详细报告，供 UI 展示，便于用户自查
    public struct Report {
        public var interfaces: [CastInterface] = []
        public var sentTargets: [String] = []
        public var errors: [String] = []
        public var receivedFrom: [String] = []
        public var foundHost: String?
        public var elapsed: TimeInterval = 0

        /// 一句话结论
        public var summary: String {
            if let h = foundHost {
                return "已发现接收端：\(h)"
            }
            if interfaces.isEmpty {
                return "没有找到可用的局域网接口。请确认已连接 Wi-Fi"
                    + "（仅开蜂窝网络无法投屏）。"
            }
            if errors.count == sentTargets.count && !sentTargets.isEmpty {
                return "数据包全部发送失败：\n"
                    + errors.joined(separator: "\n")
                    + "\n\n多半是「本地网络」权限被拒绝。"
                    + "请到 设置 → 隐私与安全性 → 本地网络 里打开本 App 的开关。"
            }
            return "已发出 \(sentTargets.count) 个广播，但没有收到回应。\n"
                + "排查：\n"
                + "1. 电脑上是否已运行 receiver.py\n"
                + "2. iPhone 与电脑是否连的同一个 Wi-Fi\n"
                + "3. 电脑防火墙是否放行 UDP 5000/5001\n"
                + "4. 设置 → 隐私与安全性 → 本地网络 里本 App 是否已打开"
        }
    }

    // MARK: - 本地网络权限

    /// 主动触发 iOS 的「本地网络」权限弹窗。
    ///
    /// 为什么要单独做这一步：`NSLocalNetworkUsageDescription` 只是文案，
    /// **不代表会弹窗**。只有真正发起本地网络访问时系统才询问。
    /// 纯 UDP 广播在部分 iOS 版本上不触发，因此这里用 Bonjour 浏览
    /// （`NWBrowser`）来可靠地把弹窗拉起来。
    ///
    /// - Note: 浏览的服务类型必须已在 Info.plist 的 `NSBonjourServices`
    ///         中声明，否则会直接失败。本项目声明的是 `_udpcast._udp`。
    public static func prepareLocalNetworkPermission(timeout: TimeInterval = 2.5) {
        let params = NWParameters.tcp
        params.includePeerToPeer = false

        let browser = NWBrowser(
            for: .bonjour(type: "_udpcast._udp", domain: nil),
            using: params
        )

        let done = DispatchSemaphore(value: 0)
        browser.stateUpdateHandler = { state in
            switch state {
            case .ready, .failed, .cancelled:
                done.signal()
            default:
                break
            }
        }

        browser.start(queue: .global(qos: .userInitiated))
        _ = done.wait(timeout: .now() + timeout)
        browser.cancel()
    }

    // MARK: - 枚举接口

    /// 列出所有「已启用 + 支持广播 + 是 IPv4」的接口及其广播地址。
    static func broadcastInterfaces() -> [CastInterface] {
        var out: [CastInterface] = []

        var ifaddrPtr: UnsafeMutablePointer<ifaddrs>?
        guard getifaddrs(&ifaddrPtr) == 0 else { return out }
        defer { freeifaddrs(ifaddrPtr) }

        var ptr = ifaddrPtr
        while let cur = ptr {
            let ifa = cur.pointee
            ptr = ifa.ifa_next

            let flags = Int32(bitPattern: ifa.ifa_flags)
            guard (flags & IFF_UP) != 0,
                  (flags & IFF_BROADCAST) != 0,
                  (flags & IFF_LOOPBACK) == 0 else { continue }

            // 本接口自己的地址，必须是 IPv4
            guard let sa = ifa.ifa_addr, sa.pointee.sa_family == UInt8(AF_INET) else { continue }

            let name = String(cString: ifa.ifa_name)
            // 只保留常见的真实网卡，跳过 pdp_ip（蜂窝）与 utun（VPN）
            guard name.hasPrefix("en") || name.hasPrefix("bridge") else { continue }

            let ip = numericHost(sa)
            guard !ip.isEmpty, ip != "0.0.0.0" else { continue }

            // 广播地址放在 ifa_dstaddr
            var bcast = ""
            if let dst = ifa.ifa_dstaddr, dst.pointee.sa_family == UInt8(AF_INET) {
                bcast = numericHost(dst)
            }
            // 兜底：由 IP + 掩码推算
            if bcast.isEmpty || bcast == "0.0.0.0" {
                if let mask = ifa.ifa_netmask, mask.pointee.sa_family == UInt8(AF_INET) {
                    bcast = computeBroadcast(ip: ip, mask: mask) ?? ""
                }
            }
            guard !bcast.isEmpty, bcast != "0.0.0.0" else { continue }

            out.append(CastInterface(name: name, ip: ip, broadcast: bcast))
        }
        return out
    }

    /// 用 getnameinfo 取数字形式的地址（比 inet_ntoa 线程安全）
    private static func numericHost(_ sa: UnsafeMutablePointer<sockaddr>) -> String {
        var buf = [CChar](repeating: 0, count: Int(NI_MAXHOST))
        let r = getnameinfo(
            sa,
            socklen_t(sa.pointee.sa_len),
            &buf,
            socklen_t(buf.count),
            nil,
            0,
            NI_NUMERICHOST
        )
        guard r == 0 else { return "" }
        return String(cString: buf)
    }

    /// 由 IP 和子网掩码算广播地址（用于 ifa_dstaddr 不可用的情况）
    private static func computeBroadcast(
        ip: String,
        mask: UnsafeMutablePointer<sockaddr>
    ) -> String? {
        guard let ipAddr = ipv4ToUInt32(ip) else { return nil }
        var m = mask.pointee
        guard m.sa_family == UInt8(AF_INET) else { return nil }
        let maskValue = withUnsafePointer(to: &m) { mp -> UInt32 in
            mp.withMemoryRebound(to: sockaddr_in.self, capacity: 1) { sin in
                UInt32(bigEndian: sin.pointee.sin_addr.s_addr)
            }
        }
        let bcast = ipAddr | ~maskValue
        return uint32ToIPv4(bcast)
    }

    private static func ipv4ToUInt32(_ s: String) -> UInt32? {
        let parts = s.split(separator: ".")
        guard parts.count == 4 else { return nil }
        var v: UInt32 = 0
        for p in parts {
            guard let n = UInt32(p), n <= 255 else { return nil }
            v = (v << 8) | n
        }
        return v
    }

    private static func uint32ToIPv4(_ v: UInt32) -> String {
        "\((v >> 24) & 0xFF).\((v >> 16) & 0xFF).\((v >> 8) & 0xFF).\(v & 0xFF)"
    }

    // MARK: - 发现

    /// 简化接口：只返回找到的接收端 IP（广播扩展在用这个）
    public static func discover(timeout: TimeInterval = defaultTimeout) -> String? {
        discoverDetailed(timeout: timeout).foundHost
    }

    /// 带诊断信息的发现。UI 上「搜索接收端」按钮用这个，
    /// 失败时能把原因显示给用户，而不是干巴巴一句「没找到」。
    public static func discoverDetailed(timeout: TimeInterval = defaultTimeout) -> Report {
        var report = Report()
        let started = Date()

        let ifaces = broadcastInterfaces()
        report.interfaces = ifaces

        guard !ifaces.isEmpty else {
            report.elapsed = Date().timeIntervalSince(started)
            return report
        }

        let req = CastProtocol.discoverRequest
        let port = CastProtocol.discoverPort

        // 每个接口单独建 socket 并 bind 到它的 IP，
        // 保证广播从 Wi-Fi 出去，而不是被系统挑到蜂窝接口。
        var sockets: [Int32] = []
        for iface in ifaces {
            let fd = socket(AF_INET, SOCK_DGRAM, 0)
            if fd < 0 {
                report.errors.append("socket 创建失败: \(errnoText())")
                continue
            }

            var on: Int32 = 1
            _ = setsockopt(fd, SOL_SOCKET, SO_BROADCAST, &on,
                           socklen_t(MemoryLayout<Int32>.size))
            var tv = timeval(tv_sec: 0, tv_usec: 200_000)
            _ = setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv,
                           socklen_t(MemoryLayout<timeval>.size))

            // bind 到本接口 IP
            var local = sockaddr_in()
            local.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
            local.sin_family = sa_family_t(AF_INET)
            local.sin_port = 0
            local.sin_addr.s_addr = inet_addr(iface.ip)

            let bindOK = withUnsafePointer(to: &local) { lp in
                lp.withMemoryRebound(to: sockaddr.self, capacity: 1) { sa in
                    bind(fd, sa, socklen_t(MemoryLayout<sockaddr_in>.size)) == 0
                }
            }
            if !bindOK {
                report.errors.append("绑定 \(iface.ip) 失败: \(errnoText())")
                close(fd)
                continue
            }

            // 发送：先发本网段的定向广播，再发受限广播兜底
            for target in [iface.broadcast, "255.255.255.255"] {
                report.sentTargets.append(target)
                let sent = sendDiscover(fd: fd, target: target, port: port, payload: req)
                if sent < 0 {
                    report.errors.append("发往 \(target) 失败: \(errnoText())")
                }
            }

            sockets.append(fd)
        }

        guard !sockets.isEmpty else {
            report.elapsed = Date().timeIntervalSince(started)
            return report
        }

        // 收回应
        let deadline = Date().addingTimeInterval(timeout)
        var buf = [UInt8](repeating: 0, count: 512)

        while Date() < deadline {
            for fd in sockets {
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

                guard let text = String(bytes: buf[0..<n], encoding: .utf8) else { continue }
                let host = withUnsafePointer(to: &from) { fp -> String in
                    fp.withMemoryRebound(to: sockaddr.self, capacity: 1) { sa in
                        numericHost(sa)
                    }
                }
                if !host.isEmpty {
                    report.receivedFrom.append(host)
                }
                guard text.hasPrefix(CastProtocol.discoverResponsePrefix) else { continue }
                if !host.isEmpty {
                    report.foundHost = host
                    report.elapsed = Date().timeIntervalSince(started)
                    sockets.forEach { close($0) }
                    return report
                }
            }
        }

        sockets.forEach { close($0) }
        report.elapsed = Date().timeIntervalSince(started)
        return report
    }

    /// 底层发送。返回实际发送字节数，失败返回负值并把原因记进 errno。
    /// **绝不能用 `_ = sendto(...)`** —— 那样权限被拒也看不出来。
    private static func sendDiscover(
        fd: Int32,
        target: String,
        port: UInt16,
        payload: Data
    ) -> Int {
        var addr = sockaddr_in()
        addr.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
        addr.sin_family = sa_family_t(AF_INET)
        addr.sin_port = port.bigEndian
        addr.sin_addr.s_addr = inet_addr(target)
        guard addr.sin_addr.s_addr != INADDR_NONE else { return -1 }

        return payload.withUnsafeBytes { raw -> Int in
            var a = addr
            return withUnsafePointer(to: &a) { p in
                p.withMemoryRebound(to: sockaddr.self, capacity: 1) { sa in
                    sendto(
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

    private static func errnoText() -> String {
        String(cString: strerror(errno))
    }

    // MARK: - 地址校验

    /// 校验用户手填的地址能否解析。
    /// 注意：Android 上解析失败返回 null，而 iOS 会抛异常，这里统一成 Bool。
    public static func resolveHost(_ host: String) -> Bool {
        var addr = in_addr()
        return host.withCString { inet_pton(AF_INET, $0, &addr) } == 1
    }
}
