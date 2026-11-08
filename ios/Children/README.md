# 家庭时光机 iOS

用 Mac 上的 Xcode 15 或更新版本打开 `Children.xcodeproj`。选择 `Children` scheme、模拟器或 iPhone，然后在 Signing & Capabilities 里选自己的 Team，按 ⌘R 编译运行。最低 iOS 17。

首页是原生 SwiftUI 照护流水，可按宝宝和日期查看、添加或修改吃奶、便便、尿尿、睡眠等记录；“成长手册”标签在应用内打开现有完整网页功能。两者使用同一个账号和服务器数据。语音录入先取得麦克风权限，上传 m4a 到受登录保护的接口，识别文字由用户核对后才写入记录。

若在服务器的 `/etc/children/children.env` 设置 `OPENAI_API_KEY` 并重启 `children.service`，语音优先使用 `gpt-transcribe`；否则 iOS 自动使用 Apple 的中文语音识别。密钥只放服务器，不写进 iOS 工程。两种识别结果都先供家长核对。
