# 原生 Flutter 分栏

窄窗保持单 Navigator 的列表→详情导航；宽窗在同一页面同时显示列表和详情，并保存当前选中项。可用 Router/go_router 的 shell 路由或自有双栏容器，但必须保留 `RouteSettings`、深链和返回语义。

从宽窗缩到窄窗时，当前详情应成为可返回页面；从窄窗扩到宽窗时，将当前详情映射为右栏选中项。弹窗明确选择根 Navigator 或局部 Navigator。
