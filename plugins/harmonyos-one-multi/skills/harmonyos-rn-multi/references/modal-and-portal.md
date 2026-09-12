# Modal、Portal 与覆盖层生命周期

## 先确定唯一覆盖层 owner

区分三类实现并画出 owner：

1. RN `Modal`；
2. 导航/UI 库的 Portal、Sheet、Popover；
3. RNOH Host/ArkUI Dialog 或子窗。

同一弹窗只由其中一层拥有显示状态、路由关闭、窗口 bounds、安全区和返回行为。不能让 RN state 与 ArkUI Dialog 各维护一份 `visible`，也不能由 Host 和页面重复添加 inset。

## 动态窗口几何

- 覆盖层使用当前 application window/实际容器，而不是物理 screen 或打开瞬间缓存的宽高。
- 内容以 `maxWidth/maxHeight`、可增长主体和可滚动内容适配窄、宽、宽短窗口；操作区参与正常布局，不用绝对定位压在长文本上。
- Portal 根和内容必须消费同一轮次 window/inset。弹窗打开期间折展、旋转或拖拽自由窗口时同步验证背景、遮罩、容器和命中区域。
- 关闭后释放 listener、timer、animation 和 native dialog；快速开关及路由切换不能由旧回调重新打开。

## 路由与 RNOH Dialog 差异

RNOH 历史 FAQ 说明过：某些版本中 RN Modal 映射 ArkUI Dialog，Dialog 位于 window 顶层，页面路由跳转不会自然替它关闭。处理时：

- 先查锁定 RNOH tag/FAQ/实现，不能把历史规格外推到所有版本。
- 产品语义要求“随页面消失”时，在 route blur/unmount 前由唯一 owner 主动关闭。
- 若必须属于页面层级、随页面裁剪和重排，评估使用页面内 View/Portal，而不是继续叠加 window-level Dialog。
- 不通过重建 NavigationContainer 清除 Modal。

## 验证

覆盖打开时窄→宽→窄、宽短窗口、长内容/大字体、安全区变化、路由 push/pop/replace、前后台、快速开关和重复进入。记录 overlay owner、route、window/inset、container onLayout、native dialog id 与释放次数。

依据：RNOH 使用类 FAQ 中关于 Modal 映射 ArkUI Dialog、路由后仍处于窗口顶层的说明。<https://gitee.com/openharmony-sig/ohos_react_native/blob/0.72.5-ohos-5.0-release/docs/zh-cn/faqs/%E4%BD%BF%E7%94%A8%E7%B1%BBFAQ.md>

