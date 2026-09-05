# OHOS DisplayFeature 与避让区

`FlutterView.ets` 将系统、导航指示、系统手势和键盘避让区同步到 ViewportMetrics，Flutter 侧分别消费 `MediaQuery.padding/viewPadding/viewInsets`。cutout 可进入 `displayFeatures`；fold/hinge 是否可用取决于当前 Flutter OHOS 引擎版本，修改前检查实际实现。

若 fold/hinge 未下发，使用窄平台通道补充 FoldStatus 和 bounds。ArkTS 坐标转 Flutter 逻辑坐标时统一处理 density、窗口偏移和沉浸式区域，避免在业务页面重复转换。
