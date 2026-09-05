# HADSS 路线的 UX 修复模式

- 页面结构仍用 Flutter 可滚容器修复截断；HADSS 只提供断点、栅格和避让信号。
- 固定宽 Row 改为 `GridRow/GridCol` 或 Flutter 弹性布局，按父容器断点分配 span。
- 宽屏导航使用 `NavigationSplitContainer`/`SideBarContainer`，外屏保持紧凑导航。
- 悬停的相机、视频、地图控制区用 `FolderStack` 或 `FoldSplitContainer`，并验证折痕区域为空。
- Sheet、日历、地图卡和设置列表仍需最大高度钳制与内部滚动。
- Sheet 比例竞态、设计缩放和亚像素溢出在 Widget 层修复，不能用断点切换掩盖。

系统兼容信箱直接转 OHOS 平台专项。

各模式完整代码与反模式（P-SCROLL-FORM、P-WIDE-FILL 等）见 [../references/pura-x-patterns.md](../references/pura-x-patterns.md)；场景 ID 映射见 [../scenarios/ux-catalog.md](../scenarios/ux-catalog.md)。
