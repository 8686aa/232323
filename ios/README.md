# iOS 端（ReplayKit + VideoToolbox）

iOS 上无法像 Android 那样任意截屏。整机投屏**必须**使用 ReplayKit 的「广播上传扩展」（Broadcast Upload Extension），
由系统在控制中心持续把屏幕 `CMSampleBuffer` 交给扩展进程处理。

因此 iOS 端由两个 target 组成：

| target | 类型 | 职责 |
| --- | --- | --- |
| `UdpCast` | Application | SwiftUI 配置界面、拉起系统广播选择器 |
| `BroadcastExtension` | App Extension | 接收 ReplayKit 画面 → VideoToolbox 硬编 → UDP 发送 |

数据流：`ReplayKit → H264Encoder(VideoToolbox) → UdpSender(NWConnection) → PC`

> **只想打包用全能签安装？看 [`SIGNING.md`](SIGNING.md)** —— 走 GitHub Actions，不需要 Mac。

---

## 配置是怎么传的（关键设计）

主 App 和广播扩展是两个独立进程，Apple 官方做法是用 App Group 共享 `UserDefaults`。
但 **App Groups 需要描述文件支持**，自签工具（全能签等）通常拿不到这个权限。

因此配置按下面的顺序取，前一级失效就退到下一级：

```
1. App Group 里的用户设置                  ← 有权限时用（可运行时改参数）
2. 扩展自己 Info.plist 的 UdpCastDefault*  ← 自签场景走这里
3. 代码内置默认值
```

另外广播扩展在拿不到有效地址时，**会自己广播发现接收端**
（`SampleHandler.broadcastStarted` 里调用 `UdpDiscovery.discover()`）。
所以只要 PC 上跑着 `receiver.py`，**没有任何 App Group 权限也能投屏成功**。

> 这也是 `UdpDiscovery.swift` 放在 `Shared/` 而不是 `App/` 的原因 —— 两个 target 都要编译它。
>
> 判断 App Group 是否可用用的是
> `FileManager.containerURL(forSecurityApplicationGroupIdentifier:)` 返回 nil，
> **不能**用 `UserDefaults(suiteName:) != nil` —— 权限缺失时它照样返回对象，
> 只是写到进程私有位置，主 App 和扩展互相看不到，排查起来非常费劲。

---

## 一、构建（需要 macOS + Xcode 15+）

本目录用 **XcodeGen** 管理工程（不把 `.xcodeproj` 提交进仓库，避免二进制冲突）。

```bash
# 1. 安装 XcodeGen
brew install xcodegen

# 2. 生成工程
cd ios
xcodegen generate

# 3. 打开
open UdpCast.xcodeproj
```

不想装 XcodeGen 也能手工建工程，见本文档末尾「手工建工程」。

---

## 二、在 Xcode 里要做的 4 件事

### 1. 填 Team ID

`project.yml` 里 `DEVELOPMENT_TEAM` 是空的。在 Xcode 中选中**两个 target** → `Signing & Capabilities` → 勾选 `Automatically manage signing` 并选择你的 Team。

### 2. 开启 App Groups（可选）

> **自签（全能签）用户请跳过这一步。** 代码已内置回退，不开也能正常投屏。

如果你的证书支持 App Groups，选中 `UdpCast` target → `Signing & Capabilities` → `+ Capability` → `App Groups` → 添加：

```
group.com.udpcast.sender
```

**对 `BroadcastExtension` target 重复一遍。** 两个 target 必须一致，否则扩展读不到主 App 保存的参数。
开好之后，主 App 界面上的参数就能生效了。

### 3. 确认 Bundle Identifier 匹配

| target | Bundle ID |
| --- | --- |
| UdpCast | `com.udpcast.sender` |
| BroadcastExtension | `com.udpcast.sender.broadcast` |

`ContentView.swift` 里的 `broadcastExtensionId` 必须等于扩展的 Bundle ID，否则系统选择器里不出现我们的条目：

```swift
private static let broadcastExtensionId = "com.udpcast.sender.broadcast"
```

### 4. 本地网络权限

`Info.plist` 已声明 `NSLocalNetworkUsageDescription`。首次投屏时 iOS 会弹「是否允许访问本地网络」——**必须点允许**，否则 UDP 包发不出去，PC 端一个包都收不到。

> 如果误点了不允许：设置 → 隐私与安全性 → 本地网络 → 找到「UDP投屏」打开开关；找不到就删掉 App 重装。

---

## 三、使用流程

1. 在 PC 上先跑 `receiver/receiver.py`。
2. 打开 iOS App，点「搜索接收端」自动填 IP（或手动填），调整参数。
3. 点「保存参数」。
   - 有 App Groups 权限 → 保存成功，扩展启动时读取。
   - 无权限（自签）→ 会提示保存失败，**这是正常的**，忽略即可：
     扩展会用 Info.plist 默认参数（8Mbps / 30fps / 75%）并自动搜索接收端。
4. 点蓝色圆形按钮 → 系统列表里选「UDP投屏」→ 点「开始直播」。
5. 回到桌面，投屏继续（ReplayKit 会一直在后台采屏）。结束请从控制中心停止。

---

## 四、H.264 格式上的两个关键点

跨端兼容全靠这两点，改动时务必注意：

### 1. VideoToolbox 输出的是 AVCC，必须转 Annex-B

VideoToolbox 输出的 NAL 单元是 **4 字节长度前缀**（AVCC）格式，而 Android 的 MediaCodec 输出的是 **`00 00 00 01` 起始码**（Annex-B）。

接收端只认 Annex-B。转换在 `H264Encoder.annexBData(from:)` 里完成。

### 2. 关键帧必须前置 SPS/PPS

SPS/PPS 从 `CMVideoFormatDescriptionGetH264ParameterSetAtIndex` 提取，在关键帧时拼到该帧数据前面，与 Android 端行为一致。

这样接收端丢包后不需要重传，等下一个 I 帧即可自愈。

---

## 五、已知限制

- **v1.0 不投声音**。`processSampleBuffer` 里的 `.audioApp` / `.audioMic` 分支留了位置，要加音频需引入 AAC 编码和新的 payload 类型。
- **不处理屏幕旋转**。ReplayKit 会通过 `RPVideoSampleOrientationKey` 附件告知方向，当前未做旋转，横竖屏切换时画面方向可能不对。要处理的话在编码前用 `CIContext` 旋转 `CVPixelBuffer`。
- **扩展内存上限约 50 MB**。全程走硬件编码，不做像素数据的 CPU 拷贝，正常不会触顶。
- **最低 iOS 16.0**。
- 自动发现会占用扩展启动后约 1.2 秒（`UdpDiscovery.defaultTimeout`），这段时间的画面被丢弃。
  想更快可以去掉 `UdpCastAutoDiscover`，改成直接填 `UdpCastDefaultHost` 为固定 IP。

---

## 手工建工程（不想用 XcodeGen）

1. Xcode → `File > New > Project` → iOS App，名字 `UdpCast`，Interface 选 SwiftUI，Bundle ID `com.udpcast.sender`。
2. 把 `UdpCast/App/*.swift` 和 `UdpCast/Shared/*.swift` 拖进主 target。
3. `File > New > Target` → iOS → `Broadcast Upload Extension`，名字 `BroadcastExtension`，Bundle ID `com.udpcast.sender.broadcast`。
4. 把 `UdpCast/BroadcastExtension/SampleHandler.swift` 覆盖掉模板生成的同名文件。
5. 把 `UdpCast/Shared/*.swift` **同时**加入扩展 target 的 Compile Sources（两个 target 都编译同一份协议与编码代码）。
6. 用仓库里的 `Info.plist` / `.entitlements` 替换模板生成的文件。
7. 如果想用 App Groups，两个 target 都要在 Signing & Capabilities 里加上 `group.com.udpcast.sender`。
