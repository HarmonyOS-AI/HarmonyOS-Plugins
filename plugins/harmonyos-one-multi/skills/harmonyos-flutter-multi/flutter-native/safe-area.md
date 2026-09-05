# 原生 Flutter 安全区

普通页面使用 `SafeArea`；需要精细控制时读取 `MediaQuery.padding`、`viewPadding` 和 `viewInsets`。全屏媒体只关闭需要沉浸的边，并为退出按钮保留可点击安全区。

PlatformView/WebView 必须将 insets 显式下发给嵌入内容。不要同时使用 `SafeArea` 和等值手工 padding；键盘高度不属于永久底部安全区。
