import ReplayKit
import CoreMedia
import VideoToolbox
import os.log

/// ReplayKit 广播上传扩展入口。
///
/// 系统在用户从控制中心 / `RPSystemBroadcastPickerView` 选择本扩展后，
/// 会持续把屏幕画面作为 `CMSampleBuffer` 喂给 `processSampleBuffer`。
///
/// 数据流：
///   ReplayKit  ->  H264Encoder(VideoToolbox)  ->  UdpSender(NWConnection)
///
/// ## 地址从哪来（自签场景的重点）
///
/// 按下面的顺序确定接收端地址，任何一步成功就停：
///   1. App Group 里主 App 保存的地址（自签通常拿不到这个权限）
///   2. 本扩展 Info.plist 里的 `UdpCastDefaultHost`
///   3. **自己广播发现**：只要 PC 上跑着 receiver.py 就能找到
///
/// 所以即使完全没有 App Group 权限，也能正常投屏。
///
/// ⚠️ 扩展进程内存上限约 50MB，因此全程走硬件编码，不做像素数据的 CPU 拷贝。
final class SampleHandler: RPBroadcastSampleHandler {

    private let log = OSLog(subsystem: "com.udpcast.broadcast", category: "cast")

    private var encoder: H264Encoder?
    private var sender: UdpSender?
    private var config = CastConfig.default

    private var videoFramesSeen: UInt64 = 0
    /// 地址还没确定时，先丢掉画面，避免编码器空转
    private var waitingForHost = true

    // MARK: - ReplayKit 生命周期

    override func broadcastStarted(withSetupInfo: [String: NSObject]?) {
        var cfg = CastConfig.load()

        os_log("broadcastStarted host=%{public}@ port=%d appGroup=%{public}@",
               log: log, type: .info,
               cfg.host, cfg.port,
               CastConfig.isAppGroupAvailable ? "yes" : "no")

        // 地址不可用就自己找。这一步会阻塞 1~2 秒，期间画面被丢弃，
        // 但换来的是「不需要 App Group 也能用」。
        if !cfg.hasUsableHost && CastConfig.autoDiscoverEnabled {
            os_log("地址未配置，开始广播发现接收端…", log: log, type: .info)
            if let found = UdpDiscovery.discover() {
                cfg.host = found
                os_log("自动发现到接收端 %{public}@", log: log, type: .info, found)
            } else {
                os_log("自动发现失败，将使用 Info.plist 默认地址 %{public}@",
                       log: log, type: .error, cfg.host)
            }
        }

        config = cfg

        guard cfg.hasUsableHost else {
            finishBroadcastWithError(
                NSError(
                    domain: "UdpCast",
                    code: -2,
                    userInfo: [NSLocalizedDescriptionKey:
                        "没有可用的接收端地址。请先在 PC 上运行 receiver.py（同一个 Wi-Fi），"
                        + "或在主 App 里填写电脑 IP 后重试。"]
                )
            )
            return
        }

        guard let s = UdpSender(host: cfg.host, port: cfg.port) else {
            finishBroadcastWithError(
                NSError(
                    domain: "UdpCast",
                    code: -1,
                    userInfo: [NSLocalizedDescriptionKey:
                        "无法创建 UDP 连接：\(cfg.host):\(cfg.port) 不是合法地址"]
                )
            )
            return
        }

        sender = s
        waitingForHost = false
        os_log("开始投屏 -> %{public}@:%d  %dkbps %dfps %.0f%%",
               log: log, type: .info,
               cfg.host, cfg.port, cfg.bitrate / 1000, cfg.fps, cfg.scale * 100)
    }

    override func processSampleBuffer(_ sampleBuffer: CMSampleBuffer, with sampleBufferType: RPSampleBufferType) {
        // 地址还没确定时直接丢帧：此时 init 编码器没有意义
        guard !waitingForHost else { return }

        switch sampleBufferType {
        case .video:
            if encoder == nil {
                setupEncoder(with: sampleBuffer)
            }
            encoder?.encode(sampleBuffer)
            videoFramesSeen &+= 1

        case .audioApp, .audioMic:
            // v1.0 只投画面。需要声音时在这里加 AAC 编码与新的 payload 类型
            break

        @unknown default:
            break
        }
    }

    override func broadcastPaused() {
        os_log("broadcastPaused", log: log, type: .info)
    }

    override func broadcastResumed() {
        os_log("broadcastResumed", log: log, type: .info)
        // 恢复时强制一个关键帧，避免接收端长时间花屏
        encoder?.requestKeyframe()
    }

    override func broadcastFinished() {
        os_log("broadcastFinished frames=%llu", log: log, type: .info, videoFramesSeen)
        encoder?.finish()
        encoder = nil
        sender?.close()
        sender = nil
    }

    // MARK: - 内部

    private func setupEncoder(with sampleBuffer: CMSampleBuffer) {
        guard let fmt = CMSampleBufferGetFormatDescription(sampleBuffer) else { return }
        let dims = CMVideoFormatDescriptionGetDimensions(fmt)

        let srcW = Int(dims.width)
        let srcH = Int(dims.height)
        guard srcW > 0, srcH > 0 else { return }

        // H.264 要求宽高为偶数；对齐到 16 让硬编最省心
        let w = max(16, (Int(Double(srcW) * config.scale) / 16) * 16)
        let h = max(16, (Int(Double(srcH) * config.scale) / 16) * 16)

        os_log("encoder %dx%d -> %dx%d @%dfps %dkbps", log: log, type: .info,
               srcW, srcH, w, h, config.fps, config.bitrate / 1000)

        encoder = H264Encoder(
            width: w,
            height: h,
            bitRate: config.bitrate,
            fps: config.fps,
            keyframeIntervalSec: 2
        ) { [weak self] data, flags in
            self?.sender?.send(payload: data, flags: flags)
        }
    }
}
