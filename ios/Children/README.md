# 家庭时光机 iOS

用 Mac 上的 Xcode 15 或更新版本打开 `Children.xcodeproj`。选择 `Children` scheme、模拟器或 iPhone，然后在 Signing & Capabilities 里选自己的 Team，按 ⌘R 编译运行。最低 iOS 15。

首页是原生 SwiftUI 照护流水，可按宝宝和日期查看、添加或修改吃奶、便便、尿尿、睡眠等记录；“成长手册”标签在应用内打开现有完整网页功能。两者使用同一个账号和服务器数据。语音录入先取得麦克风权限，上传 m4a 到受登录保护的接口，识别文字由用户核对后才写入记录。

若在服务器的 `/etc/children/children.env` 设置 `OPENAI_API_KEY` 并重启 `children.service`，语音优先使用 `gpt-transcribe`；否则 iOS 自动使用 Apple 的中文语音识别。密钥只放服务器，不写进 iOS 工程。两种识别结果都先供家长核对。

## 只有普通 Apple ID 时

仓库的 GitHub Actions“Build iPhone IPA”使用云端 Mac 构建未签名的 `Children-unsigned.ipa`。它是真正的 iOS 应用包，但尚不能直接点开安装。可在 Mac（无需 Xcode，macOS 11 或更新）装 AltServer，再在 iPhone 装 AltStore Classic；将 IPA 导入 AltStore，由你的普通 Apple ID 在本地签名后安装。Apple 对免费账号的签名有效期是 7 天，需通过 AltStore 定期刷新。不要把 Apple ID、密码或证书上传到本仓库。
