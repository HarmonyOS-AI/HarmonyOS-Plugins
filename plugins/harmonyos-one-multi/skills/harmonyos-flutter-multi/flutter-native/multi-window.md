# 原生 Flutter 多窗口

使用 `WidgetsBindingObserver.didChangeMetrics` 感知窗口变化，但布局仍由约束 rebuild 决定。缩放过程中不缓存物理屏尺寸；防抖只能用于昂贵资源重配，不能延迟关键布局。

平板自由窗的窗口装饰与沉浸式需要平台配合，进入 `ohos-platform/window-and-orientation.md`。覆盖最小窗、近方窗、宽窗、焦点切换和返回行为。
