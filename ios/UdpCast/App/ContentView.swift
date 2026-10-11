import SwiftUI
import ReplayKit

struct ContentView: View {

    /// 广播扩展的 Bundle Identifier —— 必须与扩展 target 一致，
    /// 否则系统选择器里不会出现我们的条目。
    private static let broadcastExtensionId = "com.udpcast.sender.broadcast"

    @State private var host: String
    @State private var portText: String
    @State private var bitrateMbps: Double
    @State private var fps: Double
    @State private var scaleIndex: Double
    @State private var status: String = "就绪"
    @State private var discovering = false

    /// App Group 是否可用。自签（如全能签）时通常为 false ——
    /// 此时参数无法保存，扩展会改用 Info.plist 默认值 + 自动发现。
    private let appGroupOK = CastConfig.isAppGroupAvailable

    init() {
        let c = CastConfig.load()
        _host = State(initialValue: c.hasUsableHost ? c.host : "")
        _portText = State(initialValue: String(c.port))
        _bitrateMbps = State(initialValue: Double(c.bitrate) / 1_000_000)
        _fps = State(initialValue: Double(c.fps))
        _scaleIndex = State(initialValue: ContentView.scaleToIndex(c.scale))
    }

    var body: some View {
        NavigationStack {
            Form {
                if !appGroupOK {
                    Section {
                        Label {
                            Text("当前签名未提供 App Groups 权限，参数无法保存到扩展。\n广播扩展会自动在局域网里搜索接收端（需 PC 上已运行 receiver.py），因此仍然可以正常投屏。")
                                .font(.footnote)
                        } icon: {
                            Image(systemName: "info.circle")
                        }
                    }
                }

                Section {
                    TextField("接收端 IP（留空则自动搜索）", text: $host)
                        .keyboardType(.decimalPad)
                        .autocorrectionDisabled()
                    TextField("端口", text: $portText)
                        .keyboardType(.numberPad)

                    Button {
                        runDiscovery()
                    } label: {
                        HStack {
                            Text(discovering ? "正在搜索…" : "搜索接收端")
                            Spacer()
                            if discovering { ProgressView() }
                        }
                    }
                    .disabled(discovering)
                } header: {
                    Text("接收端")
                } footer: {
                    Text("在 PC 上运行 receiver.py 后点「搜索接收端」可自动填入 IP。\n留空也可以——广播扩展启动时会自己再搜一次。")
                }

                Section("编码参数") {
                    VStack(alignment: .leading) {
                        Text("码率  \(Int(bitrateMbps)) Mbps")
                        Slider(value: $bitrateMbps, in: 1...40, step: 1)
                    }
                    VStack(alignment: .leading) {
                        Text("帧率  \(Int(fps)) fps")
                        Slider(value: $fps, in: 5...60, step: 5)
                    }
                    VStack(alignment: .leading) {
                        Text("分辨率缩放  \(Self.scaleLabel(Int(scaleIndex)))")
                        Slider(value: $scaleIndex, in: 1...4, step: 1)
                    }
                }

                Section {
                    Button {
                        saveConfig()
                    } label: {
                        Text("保存参数")
                            .frame(maxWidth: .infinity)
                    }
                } footer: {
                    Text(appGroupOK
                         ? "参数保存在 App Group 中，广播扩展启动时读取。**建议先保存再开始投屏。**"
                         : "⚠️ 当前签名没有 App Groups 权限，保存不会生效。扩展将使用编译期默认参数（8Mbps / 30fps / 75%）并自动搜索接收端。")
                }

                Section {
                    HStack {
                        Spacer()
                        BroadcastPickerView(
                            preferredExtension: Self.broadcastExtensionId,
                            size: CGSize(width: 64, height: 64)
                        )
                        .frame(width: 64, height: 64)
                        Spacer()
                    }
                    .padding(.vertical, 8)
                } header: {
                    Text("开始投屏")
                } footer: {
                    Text("点上面的蓝色按钮，在系统列表里选择「UDP投屏」，然后点「开始直播」。\n结束后回到这里，按钮会恢复可点状态。")
                }

                Section("状态") {
                    Text(status)
                        .font(.system(.footnote, design: .monospaced))
                        .foregroundStyle(.secondary)
                    Text("配置来源：\(CastConfig.sourceDescription())")
                        .font(.system(.caption, design: .monospaced))
                        .foregroundStyle(.tertiary)
                }
            }
            .navigationTitle("UDP投屏")
        }
    }

    // MARK: - 行为

    private func saveConfig() {
        let trimmedHost = host.trimmingCharacters(in: .whitespaces)
        guard let p = UInt16(portText.trimmingCharacters(in: .whitespaces)) else {
            status = "端口不合法"
            return
        }

        let c = CastConfig(
            host: trimmedHost,
            port: p,
            bitrate: Int(bitrateMbps) * 1_000_000,
            fps: Int(fps),
            scale: Self.indexToScale(Int(scaleIndex))
        )

        if c.save() {
            status = "已保存 → \(c.hasUsableHost ? c.host : "自动搜索"):\(c.port)  "
                + "\(c.bitrate / 1_000_000)Mbps \(c.fps)fps \(Int(c.scale * 100))%"
        } else {
            status = "保存失败：当前签名没有 App Groups 权限。\n"
                + "扩展将使用默认参数（8Mbps / 30fps / 75%）并自动搜索接收端。"
        }
    }

    private func runDiscovery() {
        discovering = true
        status = "正在广播搜索…"
        DispatchQueue.global(qos: .userInitiated).async {
            let ip = UdpDiscovery.discover(timeout: 2.0)
            DispatchQueue.main.async {
                discovering = false
                if let ip {
                    host = ip
                    status = "已发现接收端：\(ip)" + (appGroupOK ? "" : "\n（无法保存，扩展会自行搜索）")
                } else {
                    status = "未发现接收端。请确认 PC 已运行 receiver.py，且与本机在同一局域网。"
                }
            }
        }
    }

    // MARK: - 缩放档位

    private static func scaleLabel(_ v: Int) -> String {
        switch v {
        case 1: return "25%"
        case 2: return "50%"
        case 3: return "75%"
        default: return "100%"
        }
    }

    private static func indexToScale(_ v: Int) -> Double { Double(v) / 4.0 }

    private static func scaleToIndex(_ s: Double) -> Double {
        max(1, min(4, (s * 4).rounded()))
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
