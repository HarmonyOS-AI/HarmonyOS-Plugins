# 原生 Flutter 响应式布局

- 重复布局：`GridView`、`SliverGridDelegateWithMaxCrossAxisExtent` 或按断点改变列数。
- 挪移布局：`Flex(direction:)` 在 Column/Row 间切换。
- 导航：窄窗 `NavigationBar`，宽窗 `NavigationRail` 或自定义侧栏。
- 缩进布局：只对阅读/表单正文使用有业务依据的 `maxWidth`，不要限制地图、网格和主容器。
- 网格卡片按实际单元格宽度动态计算 `childAspectRatio`，正文高度按字号、行高、行数和 padding 估算。

布局分支尽量复用同一 State 与 Controller；不要让两个完全不同的页面树分别持有业务状态。
