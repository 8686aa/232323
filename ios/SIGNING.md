# iOS 打包与自签（全能签）

本工程提供两条路线：

| 路线 | 是否需要 Mac | 产出 | 适用 |
| --- | --- | --- | --- |
| **GitHub Actions（推荐）** | ❌ 不需要 | 未签名 `.ipa` | 用全能签等工具在设备上自签 |
| 本地 Xcode | ✅ 需要 | 直接安装 / 也可导出 IPA | 有开发者账号，要 Long-term 使用 |

---

## 一、用 GitHub Actions 产出未签名 IPA（不需要 Mac）

推送到 GitHub 后自动触发，也可以在 Actions 页面手动点 `Run workflow`。

```bash
git add .
git commit -m "feat: UDP 投屏工具"
git branch -M main
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

推送完成后：

1. 打开仓库 → **Actions** → 左侧 `Build unsigned IPA`
2. 等它跑完（首次约 5~8 分钟，主要是装 XcodeGen 和编译）
3. 在运行详情页最下方 **Artifacts** 里下载 `UdpCast-unsigned-ipa`
4. 解压得到 **`UdpCast-unsigned.ipa`**

打了 `v*` 标签的话还会自动创建 Release 并挂上 IPA：

```bash
git tag v1.0 && git push origin v1.0
```

产物为什么是「未签名」：工作流用 `CODE_SIGNING_ALLOWED=NO` 构建，并在打包前删掉
`_CodeSignature`、`CodeResources` 和 `embedded.mobileprovision`。
已被签过的包再重签容易冲突，所以必须是干净的未签名包。

---

## 二、本地 Mac 构建（可选）

```bash
brew install xcodegen
cd ios
xcodegen generate
open UdpCast.xcodeproj
```

真机运行请在两个 target 的 Signing & Capabilities 里选上你的 Team。
要导出未签名 IPA：

```bash
cd ios
xcodebuild -project UdpCast.xcodeproj -scheme UdpCast \
  -configuration Release -sdk iphoneos \
  -destination 'generic/platform=iOS' -derivedDataPath build \
  CODE_SIGN_IDENTITY="" CODE_SIGNING_REQUIRED=NO CODE_SIGNING_ALLOWED=NO \
  build

mkdir -p Payload && cp -R build/Build/Products/Release-iphoneos/UdpCast.app Payload/
zip -qry UdpCast-unsigned.ipa Payload
```

---

## 三、用全能签签名安装

1. 把 `UdpCast-unsigned.ipa` 传到 iPhone（AirDrop / 微信文件 / iCloud 均可）
2. 打开**全能签** → 选这个 IPA
3. 选择你的签名证书 / 描述文件，点签名
4. 装完后**先别急着用**，往下看权限那一步

### 安装后必做：打开本地网络权限

首次点「开始直播」时，iOS 会弹 **「是否允许访问本地网络」** —— **必须点允许**，
否则 UDP 包发不出去，PC 端一个包都收不到。

> 如果误点了「不允许」：
> 设置 → 隐私与安全性 → 本地网络 → 找到「UDP投屏」打开开关。
> 找不到就删除 App 重装。

---

## 四、App Groups 的问题（重要）

Apple 的 **App Groups 属于需要描述文件支持的 capability**。
全能签用的个人证书 / 企业证书通常**没有**这个权限，所以主 App 保存的参数
无法共享给广播扩展。

**本工程已经处理好这种情况，你不需要做任何额外配置。** 配置按下面的顺序取：

```
1. App Groups 里主 App 保存的值      ← 有权限时用这个（功能最全）
2. 广播扩展自己 Info.plist 的默认值   ← 自签场景走这里
3. 内置默认值                        ← 兜底
```

而且**广播扩展会自己广播发现接收端**：
只要 PC 上跑着 `receiver.py`，扩展启动时会在局域网里搜一次，
搜到就直接用，连 IP 都不用填。

所以自签后：

- 「保存参数」会提示失败 → **正常现象**，忽略即可
- 参数使用编译期默认值：**8 Mbps / 30fps / 75%**
- 接收端地址自动发现，**不需要手填**

### 想改默认参数怎么办

改 `ios/UdpCast/BroadcastExtension/Info.plist` 里的这几项，
然后重新推送到 GitHub 重新打包：

| 键 | 默认值 | 说明 |
| --- | --- | --- |
| `UdpCastDefaultHost` | `0.0.0.0` | 占位符 = 每次自动发现。填固定 IP 可跳过发现 |
| `UdpCastDefaultPort` | `5000` | 与 PC 端 `--port` 保持一致 |
| `UdpCastDefaultBitrate` | `8000000` | 8 Mbps |
| `UdpCastDefaultFps` | `30` | |
| `UdpCastDefaultScale` | `0.75` | 分辨率缩放 75% |
| `UdpCastAutoDiscover` | `true` | 设为 `false` 则不自动发现 |

> 如果你有带 App Groups 权限的证书，可以在两个 target 上开
> `group.com.udpcast.sender`，此时主 App 界面上的参数就能生效了。

---

## 五、排查

先把 PC 端跑起来，再开启投屏：

```bash
cd receiver
python receiver.py
```

**PC 端一直没有「收到第一个媒体包」**

手机和 PC 必须同一个 Wi-Fi（手机热点/路由器都行）。确认：

```bash
python receiver.py --player-debug
```

页面里应能看到来自手机的发现请求。

**提示「没有可用的接收端地址」**

说明自动发现失败。两种可能：

1. PC 上没跑 `receiver.py`，或防火墙没放行（见主 README）
2. 路由器开了 AP 隔离，拦掉了广播

对策：把 `UdpCastDefaultHost` 改成你 PC 的 IP，重新打包。
PC 的 IP 看这个命令：

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' }
```

**扩展根本没出现在系统广播列表里**

- 确认 IPA 里的 `UdpCast.app/PlugIns/BroadcastExtension.appex` 存在
  （CI 里有一步专门检查这个，缺了会直接报错）
- 确认签名时**扩展也被签了**。全能签一般会自动处理，
  如果它允许单独选证书，注意两个 target 用同一个证书和描述文件

**能连上但画面不出来**

用 `--player-debug` 看 PC 端日志里有没有 `已定位到关键帧`。
详细排查步骤见主 README 的「窗口全黑」一节。

---

## 六、已知限制

- **需要 iOS 16.0 及以上**
- v1.0 只投画面，没有声音（`SampleHandler` 里已留好音频分支位置）
- 横竖屏切换时画面方向可能不对（ReplayKit 的方向附件尚未处理）
- 自签证书有效期到期后需要重新签名安装
