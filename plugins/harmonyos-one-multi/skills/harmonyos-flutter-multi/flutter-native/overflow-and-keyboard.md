# 原生 Flutter 溢出与键盘

键盘避让只能由一层负责：默认让外层 `Scaffold.resizeToAvoidBottomInset` 处理；只有关闭它时才手工加 `viewInsets.bottom`。

横屏键盘导致高度极小时，外层用 `CustomScrollView` + `SliverFillRemaining`，让说明区可滚走；内容区用 `LayoutBuilder` + `SingleChildScrollView` + `ConstrainedBox(minHeight: maxHeight)` + `IntrinsicHeight`，配合 `Column` 中的 `Expanded`，实现空间足够时填满、不足时整体可滚。

禁止嵌套 Scaffold 的固定 `bottomNavigationBar`、条数乘固定高度的列表，以及同时由 Scaffold 和 AnimatedPadding 重复避让。
