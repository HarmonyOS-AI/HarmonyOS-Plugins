# 已知风险

- 不同 Flutter OHOS 引擎版本对 fold/hinge DisplayFeature 的实现可能不同，必须检查当前源码或运行结果。
- HADSS API 与包版本可能变化，以工程 lockfile 和实际声明为准。
- 系统分栏对 Router/go_router、RouteSettings、弹窗 Navigator 和 replacement 行为有约束。
- 自由窗和窗口装饰能力受 HarmonyOS API 级别影响。
- 仅用模拟器几何不能证明真实折痕、挖孔、LTPO 和相机 surface 行为。
- DPI 自动缩放可能降低可读性与触控尺寸，应作为工程扩展而非默认修复。
