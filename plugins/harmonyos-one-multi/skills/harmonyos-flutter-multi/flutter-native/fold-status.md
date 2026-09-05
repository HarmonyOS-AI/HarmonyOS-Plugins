# 原生 Flutter 折叠状态

优先读取 `MediaQuery.displayFeatures`，根据 `DisplayFeatureType.fold/hinge`、bounds 和 state 得到折痕区域与半开状态。若 OHOS 引擎版本未下发 fold/hinge，则通过 MethodChannel 获取当前值、EventChannel 监听变化。

统一输出 `flat`、`halfOpened`、`folded`、`unknown` 以及窗口坐标系中的 feature bounds。生命周期结束时取消流订阅；几何推算只作 `unknown` 状态的降级，不覆盖系统信号。
