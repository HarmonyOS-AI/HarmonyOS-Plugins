# HADSS 安全区

折痕/窗口避让使用 `hadss_avoid_area`；状态栏、导航条、键盘等 Flutter 已能表达的区域继续使用 `SafeArea`/`MediaQuery`，不要为了统一而重复添加 padding。

为每类 avoid area 明确所有者。PlatformView/WebView 的 insets 仍需平台桥接，转 `ohos-platform/platform-view-and-channels.md`。
