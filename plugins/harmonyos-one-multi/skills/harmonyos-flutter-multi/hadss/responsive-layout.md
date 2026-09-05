# HADSS 响应式布局

- 重复布局：`GridRow` + `GridCol`，按断点配置 columns、span、offset、order。
- 内容优先级：使用 `DisplayPriorityBox` 或等效 HADSS 能力渐进显隐。
- 挪移布局：断点驱动 `Flex` 方向与元素顺序。
- 侧栏：`SideBarContainer(type: auto)`，为窄窗定义收起行为。

断点切换时保留子组件 key 与 Controller。大屏缩进只应用于适合阅读的内容，地图、视频和网格不应被统一限窄。
