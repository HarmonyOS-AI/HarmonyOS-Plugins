# HADSS 多窗口

用 BreakpointManager 响应窗口类别变化，用 AvoidAreaApi 响应避让区与形态变化。避免在 listener 中重复维护一套尺寸状态；需要重配相机、视频等昂贵资源时，基于稳定后的窗口信息执行。

自由窗装饰、沉浸式和系统窗口 API 转 `ohos-platform/window-and-orientation.md`。
