# 原生路线接入

无需新增布局依赖。先建立工程级 `WindowClass`/断点映射，集中封装 `LayoutBuilder`、`MediaQuery` 和可选 Platform Channel。页面只消费语义化状态，不直接判断设备型号或散落阈值。

若 Flutter OHOS 当前版本不能稳定提供 fold/hinge `DisplayFeature`，仅为折叠状态与区域补充小型 EventChannel；不要因此把整套布局逻辑移到 ArkTS。
