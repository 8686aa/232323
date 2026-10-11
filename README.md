# UDP 投屏

安卓 / iOS 手机 **局域网 UDP 投屏**工具。手机采集屏幕 → 硬编码 H.264 → UDP 分片发送，电脑接收重组并实时播放。

- **无第三方运行时依赖**：Android 只用 `MediaProjection` + `MediaCodec`，iOS 只用 `ReplayKit` + `VideoToolbox`，PC 端只用 Python 标准库。
- **一套协议三端通用**：Android 与 iOS 发送端字节级一致，同一份接收器都能收。
- **极低延迟**：不走重传、不走拥塞控制队列，局域网内端到端延迟通常在 100~200 ms。
- **抗丢包**：每个关键帧自带 SPS/PPS，丢包后最多等一个 I 帧间隔自动恢复。

---

## 目录结构

```
udp投屏/
├── android/                         Android 发送端（Kotlin，可直接构建）
│   ├── app/src/main/java/com/udpcast/sender/
│   │   ├── MainActivity.kt          配置界面 + 接收端发现
│   │   ├── ScreenCastService.kt     前台服务：MediaProjection → VirtualDisplay
│   │   ├── H264Encoder.kt           MediaCodec Surface 输入硬编码
│   │   ├── UdpFrameSender.kt        分片 + 独立发送线程
│   │   ├── CastProtocol.kt          协议常量与包头写入
│   │   └── ReceiverDiscovery.kt     广播搜索接收端
│   ├── gradlew / gradlew.bat        已生成，可直接用
│   └── app/build/outputs/apk/debug/app-debug.apk   已构建产物
│
├── ios/                             iOS 发送端（Swift，需 macOS + Xcode）
│   ├── project.yml                  XcodeGen 工程描述
│   ├── README.md                    工程结构与构建
│   ├── SIGNING.md                   打包 + 全能签自签完整流程
│   └── UdpCast/
│       ├── App/                     主 App（SwiftUI）
│       ├── Shared/                  协议 / 发送 / 编码 / 发现（两个 target 共用）
│       └── BroadcastExtension/      ReplayKit 广播上传扩展
│
├── .github/workflows/
│   └── ios-unsigned-ipa.yml         CI：产出未签名 IPA，供自签工具使用
│
├── receiver/
│   ├── receiver.py                  PC 端接收器（实时播放 / 落盘 / MP4）
│   ├── player.py                    自带播放窗口（ffmpeg 解码 + tkinter 显示）
│   ├── demo_stream.py               演示发送端：没有手机时灌测试视频验证链路
│   └── selftest.py                  端到端自测（不需真机，已全绿）
│
└── docs/protocol.md                 协议规范（改协议必读）
```

---

## 快速开始

### 1. 电脑端先跑起来

```bash
cd receiver
pip install imageio-ffmpeg pillow    # 实时播放需要（约 90 MB，装一次即可）
python receiver.py
```

`python receiver.py` 默认就会开一个播放窗口：

| 情况 | 行为 |
| --- | --- |
| 本机有 ffplay | 用 ffplay 播放（最省 CPU） |
| 没有 ffplay，但有 Pillow | 用自带播放窗口 `player.py`（ffmpeg 解码 + tkinter 显示） |
| 两者都没有 | 退化为落盘 `udpcast_<时间>.h264` |

不想看实时画面，只想要文件：

```bash
python receiver.py --out session.h264        # 落盘裸流
python receiver.py --mp4 session.mp4         # 边收边封装 MP4
python receiver.py --player                  # 强制使用自带播放窗口
python receiver.py --tee debug.h264          # 边播边存一份，排查问题用
python receiver.py --player-debug            # 打印播放器解码/渲染状态
```

自带播放窗口的快捷键：`Esc` 关闭，`F11` / 双击切换全屏。

### 还没拿到手机？先自检一遍链路

```bash
# 终端 1
python receiver.py
# 终端 2
python demo_stream.py --duration 20
```

`demo_stream.py` 会用本机 ffmpeg 生成一段带时间码的 720p30 测试视频，
按真实 UDP 协议打给接收器。窗口里出现动态测试图案，
就说明「接收 → 重组 → 解码 → 上屏」整条链路是通的。

### 2. 装 Android 端

```bash
cd android
./gradlew :app:assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

或者用 Android Studio 打开 `android/` 目录直接 Run。

### 3. 开始投屏

1. 手机和电脑连**同一个 Wi-Fi**。
2. 打开 App，点「搜索接收端」自动填入电脑 IP（失败就手动填）。
3. 按需调整码率 / 帧率 / 分辨率缩放。
4. 点「开始投屏」，在系统弹窗里同意录屏授权。
5. 电脑上立刻出画面。通知栏的「停止」按钮或 App 内「停止投屏」都能结束。

---

## 参数怎么选

| 参数 | 建议 | 说明 |
| --- | --- | --- |
| 分辨率缩放 | **50% ~ 75%** | 1080p 全屏下发 100% 在 Wi-Fi 上容易丢包花屏 |
| 码率 | 1080p→**8~12 Mbps**；720p→**4~6 Mbps** | 过高会把 Wi-Fi 打满，反而更卡 |
| 帧率 | **30 fps** | 60 fps 对投屏意义不大，翻倍消耗带宽 |
| 端口 | 5000 | 数据端口；5001 是发现服务固定端口 |

**Wi-Fi 建议走 5 GHz 频段**，2.4 GHz 在 1080p 下几乎必然丢包。

---

## 延迟与丢包

接收器每 2 秒打印一行统计：

```
[stat]   12.0s |   9.42 Mbps | 收包    812345 | 丢包    1204 ( 0.15%) | 丢帧     18 | 写入 14.1MB
```

- **丢包率 < 1%**：正常，画面靠 I 帧自愈，基本无感。
- **丢包率 1% ~ 5%**：降码率或降分辨率缩放，或切到 5 GHz。
- **丢包率 > 5%**：多半是 2.4 GHz 拥挤或 AP 隔离，先排查网络。

---

## 常见问题

**搜不到接收端**
企业 AP 常开启客户端隔离（AP Isolation），会拦截广播。手动填写电脑 IP 即可。
确认电脑防火墙放行 UDP 5000/5001：

```powershell
New-NetFirewallRule -DisplayName "UDP投屏" -Direction Inbound -Protocol UDP -LocalPort 5000,5001 -Action Allow
```

**窗口全黑 / 一直不出画面**
接收器已经能收到包，但画面不出来时，按这个顺序排查：

```bash
# 1. 打开播放器诊断，看它到底解出了几帧
python receiver.py --player-debug
```

看输出里这两行：

| 现象 | 含义 | 处理 |
| --- | --- | --- |
| 没有 `已定位到关键帧` | 一个关键帧都没收到，发送端没正常工作 | 看手机 App 上「帧」计数是否在涨 |
| 有 `已渲染 N 帧` 且 N 在涨 | 正常，画面已经在窗口里 | 窗口可能被别的窗口挡住 |
| `解出 0` 且大量 ffmpeg 报错 | 码流有问题 | 见下一条 |

**确认码流本身是否正常**

把同一份流同时存一份下来，用 ffmpeg 独立解一遍：

```bash
python receiver.py --tee debug.h264
# 跑一会儿后 Ctrl+C，然后：
ffmpeg -f h264 -i debug.h264 -f null -      # 有 libx264 的 ffmpeg 即可
```

`ffmpeg` 解出的帧数和接收器报的「写入」量对得上，就说明发送端没问题，问题在播放端。

**画面花屏后长时间不恢复**
I 帧间隔是 2 秒，正常情况下最多 2 秒恢复。若一直花屏，说明丢包率过高，降码率。

**PC 端收不到任何包**
先确认手机和电脑在同一网段（App 顶部会显示手机 IP）。用 `--bind 0.0.0.0`（默认）而不是 `127.0.0.1`。
手机若连的是电脑开的热点，网段通常是 `192.168.137.x`，电脑侧地址是 `192.168.137.1`，这是正常的。

**Android 14/15 上授权后立刻停止**
Android 14 起 `mediaProjection` 类型前台服务有严格的调用顺序要求（本项目已按正确顺序实现）。如果仍失败，看 logcat：

```bash
adb logcat -s ScreenCastService H264Encoder UdpFrameSender
```

**帧率只有 10 左右**
手机屏幕静止时编码器按设计每 100ms 重复一帧，省带宽，画面依然是正确的。屏幕有变化时会自动回到 30fps。

---

## iOS 端

iOS 的屏幕采集必须走 ReplayKit 广播上传扩展，且需要 macOS + Xcode 构建。

**用全能签等工具自签安装 → 看 [`ios/SIGNING.md`](ios/SIGNING.md)。**
推送到 GitHub 后 Actions 会自动产出**未签名 IPA**，下载后直接导入全能签即可，全程不需要 Mac：

```bash
git add . && git commit -m "feat: UDP 投屏"
git branch -M main
git remote add origin https://github.com/<用户名>/<仓库名>.git
git push -u origin main
```

然后到仓库的 **Actions → Build unsigned IPA** 下载 Artifacts 里的 `UdpCast-unsigned-ipa`。

配置传递做了回退链（App Group → Info.plist → 内置默认），并且广播扩展会自己广播发现接收端，
所以**自签拿不到 App Groups 权限也能正常投屏**。协议与 Android 完全一致，
同一个 `receiver.py` 直接就能收 iOS 的画面。

---

## 自测

```bash
cd receiver
python selftest.py
```

不需要真机，会验证分片重组、帧内乱序、丢帧强制推进、超时清理、重复包拒绝与发现服务响应。

---

## 改协议的正确姿势

协议是两端耦合点，改动必须同步三处：

1. `android/.../CastProtocol.kt`
2. `ios/UdpCast/Shared/CastProtocol.swift`
3. `receiver/receiver.py`（`HEADER_FMT`）

改完跑 `python receiver/selftest.py`，再对照 [`docs/protocol.md`](docs/protocol.md) 第 8 节的检查清单。
