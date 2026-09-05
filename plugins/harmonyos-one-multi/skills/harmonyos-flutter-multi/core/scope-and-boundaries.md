# 范围与边界

适用于 Flutter 应用在 HarmonyOS/OpenHarmony 的手机、折叠屏、平板和多窗口适配，包括响应式布局、分栏、折叠/悬停、折痕避让、安全区、键盘、方向、PlatformView、DPI、LTPO 和 Pura X 类阔折叠 UX。当前不支持 2in1/PC。

不用于与设备或窗口无关的普通 Widget、状态管理和业务逻辑问题，也不替代纯 ArkUI 一多、构建发布或性能分析专项。

`scenarios/` 只描述问题与验收；`flutter-native/` 和 `hadss/` 分别给出实现；`ohos-platform/` 承载两条路线共用的 OHOS 宿主、窗口和框架能力。
