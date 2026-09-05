# HADSS 断点检测

使用 `BreakpointManager.instance.currentBreakpoint` 获取初值并注册 listener。将 HADSS 的宽高断点映射为工程语义值，确保 listener 只在值变化时刷新，并在 `dispose` 中移除。

组件级布局仍要尊重父约束：若 HADSS 支持 component-size reference，优先使用；不要把全窗断点错误用于嵌套窄栏。
