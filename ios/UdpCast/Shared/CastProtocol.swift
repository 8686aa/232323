import Foundation

/// UDP 投屏协议 v1.0 —— 与 Android 端 `CastProtocol.kt` 字节级一致。
///
/// 单包布局（全部大端序）：
///   0..3   magic         0x55 0x44 0x50 0x31 ("UDP1")
///   4..7   frameId       UInt32
///   8..9   packetIndex   UInt16
///   10..11 packetCount   UInt16
///   12     flags         bit0=关键帧 bit1=编解码配置 bit2=帧结束
///   13     reserved      0x00
///   14..15 payloadLen    UInt16
///   16..N  payload       H.264 Annex-B 裸流
public enum CastProtocol {

    public static let headerSize = 16
    public static let mtu = 1400
    public static let maxPayload = mtu - headerSize      // 1384

    public static let flagKeyframe: UInt8 = 1 << 0
    public static let flagConfig: UInt8 = 1 << 1
    public static let flagEnd: UInt8 = 1 << 2

    // ---- 接收端发现 ----
    public static let discoverPort: UInt16 = 5001
    public static let discoverRequest = Data("UDPCAST_DISCOVER".utf8)
    public static let discoverResponsePrefix = "UDPCAST_HERE"

    // ---- App Group（主 App 与广播扩展共享配置）----
    // 注意：App Group 需要描述文件支持。用「全能签」等自签工具时通常拿不到这个权限，
    // 因此它只是**首选**配置来源，不是必需项 —— 见 CastConfig 的回退链。
    public static let appGroupId = "group.com.udpcast.sender"
    public static let keyHost = "host"
    public static let keyPort = "port"
    public static let keyBitrate = "bitrate"
    public static let keyFps = "fps"
    public static let keyScale = "scale"

    // ---- 无 App Group 时的回退配置（写在各自 target 的 Info.plist 里）----
    /// 这些键让主 App 和广播扩展在拿不到 App Group 权限时，
    /// 依然能通过各自的 Info.plist 读到一套编译期确定的默认参数。
    public static let plistHost = "UdpCastDefaultHost"
    public static let plistPort = "UdpCastDefaultPort"
    public static let plistBitrate = "UdpCastDefaultBitrate"
    public static let plistFps = "UdpCastDefaultFps"
    public static let plistScale = "UdpCastDefaultScale"
    /// 设为 false 可强制扩展每次都重新做局域网发现
    public static let plistAutoDiscover = "UdpCastAutoDiscover"

    /// 组装一个带包头的完整 UDP 数据报
    public static func packet(
        frameId: UInt32,
        index: UInt16,
        count: UInt16,
        flags: UInt8,
        payload: Data
    ) -> Data {
        var d = Data(capacity: headerSize + payload.count)
        d.append(0x55)
        d.append(0x44)
        d.append(0x50)
        d.append(0x31)
        d.appendU32BE(frameId)
        d.appendU16BE(index)
        d.appendU16BE(count)
        d.append(flags)
        d.append(0x00)
        d.appendU16BE(UInt16(payload.count))
        d.append(payload)
        return d
    }
}

public extension Data {
    mutating func appendU32BE(_ value: UInt32) {
        append(UInt8((value >> 24) & 0xFF))
        append(UInt8((value >> 16) & 0xFF))
        append(UInt8((value >> 8) & 0xFF))
        append(UInt8(value & 0xFF))
    }

    mutating func appendU16BE(_ value: UInt16) {
        append(UInt8((value >> 8) & 0xFF))
        append(UInt8(value & 0xFF))
    }

    mutating func appendAnnexBStartCode() {
        append(contentsOf: [0x00, 0x00, 0x00, 0x01])
    }
}
