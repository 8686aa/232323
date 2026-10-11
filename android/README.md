# Android 端

## 构建

命令行（本机已验证可编译通过，Gradle 8.7 + AGP 8.5.2 + JDK 17）：

```bash
cd android
./gradlew :app:assembleDebug
```

产物：`app/build/outputs/apk/debug/app-debug.apk`

安装：

```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

也可以用 Android Studio 直接打开 `android/` 目录，Sync 后 Run。

## 环境要求

| 项目 | 版本 |
| --- | --- |
| compileSdk / targetSdk | 34 |
| minSdk | 26（Android 8.0） |
| JDK | 17+ |
| Gradle | 8.7（wrapper 已配好） |
| AGP / Kotlin | 8.5.2 / 1.9.24 |

`local.properties` 里已写入本机 SDK 路径，换机器需改成自己的：

```properties
sdk.dir=C\:\\Users\\<你>\\AppData\\Local\\Android\\Sdk
```

## 关于包名

debug 构建的 applicationId 带了 `.debug` 后缀（`com.udpcast.sender.debug`），
方便和 release 版共存。要改回一致，去掉 `app/build.gradle.kts` 里的：

```kotlin
debug {
    applicationIdSuffix = ".debug"
}
```

## 代码结构

```
app/src/main/java/com/udpcast/sender/
├── MainActivity.kt           配置 UI、录屏授权、接收端发现
├── ScreenCastService.kt      前台服务编排：MediaProjection → VirtualDisplay → 编码 → 发送
├── H264Encoder.kt            MediaCodec，Surface 输入模式，零拷贝
├── UdpFrameSender.kt         分帧 + 独立发送线程（网络慢时不阻塞编码）
├── CastProtocol.kt           协议常量与包头写入
└── ReceiverDiscovery.kt      广播搜索接收端（5001 端口）
```

### 关键实现点

**Android 14 (API 34) 的调用顺序**（顺序错会直接抛 `SecurityException`）：

```
1. startForeground(type = FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION)
2. mediaProjectionManager.getMediaProjection(resultCode, data)
3. projection.registerCallback(...)          ← 必须在 createVirtualDisplay 之前
4. projection.createVirtualDisplay(...)
```

见 `ScreenCastService.startPipeline()`。

**编码尺寸对齐到 16 的倍数**，避免部分机型硬编拒绝非对齐尺寸：

```kotlin
outWidth  = align16((srcW * scale).toInt())
outHeight = align16((srcH * scale).toInt())
```

**发送不阻塞编码**：编码输出线程只负责切包入队，另有一个高优先级线程专门 send。
队列满时**丢整帧**而不是丢半个，接收端不会白等一个永远不会齐的帧。

**关键帧带 SPS/PPS**：`H264Encoder` 缓存 `BUFFER_FLAG_CODEC_CONFIG`，
在每个 IDR 输出时前置拼接，这样单个关键帧可独立解码。

## 含中文路径的说明

工程位于 `.../udp投屏/android`，AGP 默认会因非 ASCII 路径拒绝构建，
已在 `gradle.properties` 中加：

```properties
android.overridePathCheck=true
```

本机实测（JDK 21 + AGP 8.5.2 + aapt2）可正常编译出包。
如果你的环境仍报 aapt2 相关错误，把 `android/` 整个复制到纯英文路径下再构建。

## 调试

```bash
adb logcat -s ScreenCastService H264Encoder UdpFrameSender ReceiverDiscovery
```
