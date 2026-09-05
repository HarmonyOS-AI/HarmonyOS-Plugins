# 原生 Flutter 开合连续性

保持同一业务 State，只切换布局壳。`TextEditingController`、`ScrollController`、选中项和播放器 Controller 不应创建在断点分支内部。

- 列表：优先使用稳定 item key/锚点；尺寸稳定后恢复位置。
- 输入：Controller 和 FocusNode 跨布局复用。
- 媒体：记录进度与播放态，在新 surface prepared 后恢复并设置一次超时兜底。
- 图片/相机：按新 viewport 更新分辨率或预览，不重置业务流程。

取消旧尺寸下排队的恢复任务，避免竞态覆盖新状态。
