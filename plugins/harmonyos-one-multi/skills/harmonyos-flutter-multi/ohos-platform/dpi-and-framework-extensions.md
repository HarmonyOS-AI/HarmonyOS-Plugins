# DPI 与框架扩展

优先使用 Flutter 逻辑像素、约束和断点解决适配。`flutter/displaymetrics` 自定义 DPI、按 URI 缩放和 `AdaptiveDpiColumn` 属于 Flutter OHOS 框架扩展，只有工程确实包含相应实现时才使用。

自动 DPI 降级不应掩盖 Debug/Profile 溢出；Release 若启用，应限制最小缩放、仅处理有界顶层 Column，并保留关闭开关。字体可访问性、触控目标和 PlatformView 坐标必须单独验证。

完整断点体系、十大适配策略与 `AdaptiveDpiColumn` 详册见 [../references/dpi-guide.md](../references/dpi-guide.md)。
