# HADSS 路线的溢出与键盘

HADSS 负责断点与避让区，不替代 Flutter 的滚动和键盘布局。继续使用 `Scaffold.resizeToAvoidBottomInset`、`CustomScrollView`、`SliverFillRemaining` 和受约束的可滚内容；键盘避让只能由一层负责。

短高窗口同时消费 BreakpointManager 的宽高断点，不仅依据宽度。AvoidAreaApi 提供的折痕/系统区域与 `MediaQuery.viewInsets` 分开处理，禁止把键盘高度重复加入 HADSS 避让 padding。
