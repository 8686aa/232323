import Foundation

/// 投屏配置，以及它在主 App 与广播扩展之间的传递方式。
///
/// ## 为什么要有回退链
///
/// 最理想的方式是用 App Group 让两个 target 共享一份 UserDefaults。
/// 但 App Group 属于需要描述文件支持的 capability —— 用「全能签」这类
/// 自签工具、或个人免费证书签名时，**通常拿不到这个权限**，
/// 一旦强制依赖它，扩展就只能读到默认值，投屏直接不可用。
///
/// 因此这里按下面的顺序取配置，前一级失效就退到下一级：
///
///   1. App Group 里的用户设置（功能最完整，可运行时改）
///   2. 本 bundle 自己 Info.plist 里的 `UdpCastDefault*`（编译期写死，随包分发）
///   3. 代码内置默认值
///
/// 另外广播扩展在拿不到有效地址时，会自己跑一次局域网发现
/// （见 `SampleHandler.broadcastStarted`），所以只要 PC 上跑着接收器，
/// **即使没有任何 App Group 权限也能投屏成功**。
public struct CastConfig {

    public var host: String
    public var port: UInt16
    public var bitrate: Int
    public var fps: Int
    public var scale: Double

    /// 占位地址：视为「尚未配置」，触发自动发现
    public static let placeholderHost = "0.0.0.0"

    public static let `default` = CastConfig(
        host: placeholderHost,
        port: 5000,
        bitrate: 8_000_000,
        fps: 30,
        scale: 0.75
    )

    public init(host: String, port: UInt16, bitrate: Int, fps: Int, scale: Double) {
        self.host = host
        self.port = port
        self.bitrate = bitrate
        self.fps = fps
        self.scale = scale
    }

    /// 地址是否可用（非空、非占位符）
    public var hasUsableHost: Bool {
        let h = host.trimmingCharacters(in: .whitespaces)
        return !h.isEmpty && h != CastConfig.placeholderHost
    }

    // MARK: - App Group

    /// App Group 是否真的可用。
    ///
    /// 不能用 `UserDefaults(suiteName:) != nil` 判断 —— 权限缺失时它照样返回对象，
    /// 只是写到一个进程私有的位置，主 App 和扩展互相看不到，很难排查。
    /// `containerURL(forSecurityApplicationGroupIdentifier:)` 在无权限时返回 nil，
    /// 这才是可靠的判断依据。
    public static var isAppGroupAvailable: Bool {
        FileManager.default
            .containerURL(forSecurityApplicationGroupIdentifier: CastProtocol.appGroupId) != nil
    }

    private static var store: UserDefaults? {
        guard isAppGroupAvailable else { return nil }
        return UserDefaults(suiteName: CastProtocol.appGroupId)
    }

    // MARK: - 读取

    /// 按「App Group → Info.plist → 内置默认」的顺序取配置。
    public static func load() -> CastConfig {
        var cfg = fromInfoPlist()

        if let d = store {
            if let h = d.string(forKey: CastProtocol.keyHost), !h.isEmpty {
                cfg.host = h
            }
            if let p = d.object(forKey: CastProtocol.keyPort) as? Int, p > 0, p <= 65535 {
                cfg.port = UInt16(p)
            }
            if let b = d.object(forKey: CastProtocol.keyBitrate) as? Int, b > 0 {
                cfg.bitrate = b
            }
            if let f = d.object(forKey: CastProtocol.keyFps) as? Int, f > 0 {
                cfg.fps = f
            }
            if let s = d.object(forKey: CastProtocol.keyScale) as? Double, s > 0 {
                cfg.scale = s
            }
        }

        return cfg
    }

    /// 只从本 bundle 的 Info.plist 读，用于两个 target 各自的编译期默认值。
    public static func fromInfoPlist() -> CastConfig {
        let info = Bundle.main.infoDictionary ?? [:]
        var cfg = CastConfig.default

        if let h = info[CastProtocol.plistHost] as? String, !h.isEmpty {
            cfg.host = h
        }
        if let p = info[CastProtocol.plistPort] as? Int, p > 0, p <= 65535 {
            cfg.port = UInt16(p)
        }
        if let b = info[CastProtocol.plistBitrate] as? Int, b > 0 {
            cfg.bitrate = b
        }
        if let f = info[CastProtocol.plistFps] as? Int, f > 0 {
            cfg.fps = f
        }
        if let s = info[CastProtocol.plistScale] as? Double, s > 0 {
            cfg.scale = s
        }
        return cfg
    }

    /// Info.plist 是否允许广播扩展自动做局域网发现（默认允许）
    public static var autoDiscoverEnabled: Bool {
        (Bundle.main.infoDictionary?[CastProtocol.plistAutoDiscover] as? Bool) ?? true
    }

    // MARK: - 保存

    /// 保存到 App Group。
    /// - Returns: 是否保存成功。App Group 不可用时返回 false，
    ///            调用方应当提示用户改用 Info.plist 默认值或依赖自动发现。
    @discardableResult
    public func save() -> Bool {
        guard let d = CastConfig.store else { return false }
        d.set(host, forKey: CastProtocol.keyHost)
        d.set(Int(port), forKey: CastProtocol.keyPort)
        d.set(bitrate, forKey: CastProtocol.keyBitrate)
        d.set(fps, forKey: CastProtocol.keyFps)
        d.set(scale, forKey: CastProtocol.keyScale)
        d.synchronize()
        return true
    }

    /// 人类可读的配置来源，用于界面提示
    public static func sourceDescription() -> String {
        if isAppGroupAvailable { return "App Group（可运行时修改）" }
        return "Info.plist 默认值 + 自动发现（App Group 不可用）"
    }
}
