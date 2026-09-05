# HADSS 开合连续性

HADSS 只驱动布局壳，Controller、路由和媒体状态保持在布局壳之外。BreakpointManager 与 AvoidAreaApi 可能连续发出变化，恢复动作需等待最终约束稳定并取消过期任务。

列表锚点、输入草稿、媒体进度和图片分辨率的保持要求与业务无关；验证时覆盖 folded→halfOpened→expanded 及反向路径。
