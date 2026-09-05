# 诊断证据

优先记录：逻辑窗口宽高与 density、MediaQuery padding/viewInsets/displayFeatures、断点与 FoldStatus、avoid area bounds、窗口模式、方向、相关日志和前后截图。

信箱问题额外获取 WMS/窗口模式/Ability 配置证据；布局问题记录约束链和触发溢出的 Widget；连续性问题记录切换前后锚点、输入和媒体时间。证据应能区分“系统没有给满窗口”与“Flutter 内容自己限窄”。
