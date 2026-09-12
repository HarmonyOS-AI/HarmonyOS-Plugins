# RNOH 多设备问题排查

## 先收集同轮次证据

在正常与异常窗口分别记录：锁定 RN/RNOH/HAR/CLI 版本、Harmony application window、RN `window/screen/scale/fontScale`、自定义 rem/rpx/layoutScale/breakpoint、关键 StyleSheet/props/onLayout、列表锚点、RNSurface、native view、Surface/buffer、事件 sequence/epoch、route/业务状态和资源数。

比较同一个 resize epoch；把不同时间的 window、Dimensions 和 Surface 日志拼在一起会制造假根因。

## RN 内容溢出或截断

1. 从最先越界的子项向父级检查固定 width/height、不可收缩 Row、绝对定位、错误比例和只容纳一行的高度。
2. 记录大字体、长文本、加载/空/错误态，不先用 `numberOfLines` 隐藏问题。
3. 检查断点是否来自当前 window，而不是 `screen`、设备类型、PixelRatio 或启动缓存。
4. 临时移除一个约束验证现象能稳定开启/关闭，再修改根约束。

## ScrollView 空白、不能滚动或百分比失效

1. 从 application window 到 RN root、Navigation scene、page、viewport、content 逐级记录 `onLayout`。
2. 第一处高度为 0、仍是旧值或无限增长时停止向叶子加样式，读取 `layout-constraints-and-scroll.md`。
3. 区分 ScrollView `style` 的 viewport 和 `contentContainerStyle` 的内容；检查 `flex: 1`/`flexGrow` 是否放错 owner。
4. 临时用明确的小范围父高度反证约束链；不要把设备屏高固化为最终修复。

## Dimensions 或整页尺寸不更新

1. 确认 Harmony application window 已变化，记录 owning window/instance/surface。
2. 对比 Host coordinator/RNInstance/RNSurface 与 RN `Dimensions` 是否同轮次更新。
3. 检查模块级 `Dimensions.get` 缓存、错误 subscription owner、重复 listener 和过期闭包。
4. 多实例时确认事件没有广播错 instance，也没有被销毁 callback 消费。
5. 不用页面 style 或 key 掩盖 Host 传播错误。

## window 已更新但 rem/fontSize/页面比例不更新

1. 确认 `useWindowDimensions` 的 width/height 已变化；没有变化回到上一节。
2. 搜索 `rem/rpx/scale/normalize/wp/hp/designWidth/screenWidth` 的定义和所有消费者。
3. 检查它是否在模块顶层求值，或只修改全局单例而没有 state/hook/Context 通知。
4. 检查 `StyleSheet.create`、`useMemo/useCallback`、React.memo comparator、FlatList `renderItem/getItemLayout/extraData` 是否捕获旧值或缺依赖。
5. 分开记录 `layoutScale`、系统 `fontScale` 和 PixelRatio；检查双重缩放或用 fontScale 驱动非文字布局。
6. 临时将最终 style 动态绑定当前 width，若现象可开关，根因在派生/消费链而非 Host。
7. 读取 `dynamic-scaling-and-styles.md`，把派生公式改为当前 window 的纯函数并让消费者响应，不通过 reload/force remount 生效。

## 断点或第三方响应式库状态陈旧

1. 同时记录库 runtime window、active breakpoint/token 和组件 render 次数。
2. runtime window 正确但 breakpoint 错：检查断点表、输入使用 screen/window、库版本与订阅时序。
3. breakpoint 正确但组件不更新：检查 hook/selector/Context value、memo comparator 和静态 StyleSheet。
4. 非 hook 静态 responsive helper 在模块级求值时通常不会随折展重算；先查该库官方 API，不自行修改 node_modules。

## 原生 view 半屏、黑边或触控错位

1. 对账 window → wrapper → native view → Surface/buffer → input coordinates 五段。
2. wrapper 错先修 RN；wrapper 正确、native 错才修 Fabric commit；view 正确、buffer 错才 resize/rebuild Surface。
3. 画面矩阵与触控逆变换成对检查，明确 layout units 与 pixels。
4. 快速 resize 中用 epoch 验证旧异步结果没有覆盖新资源。

## 折展/旋转后状态丢失

1. 搜索 width/breakpoint/posture 参与的 key 和互斥根树。
2. 审计依赖 window/breakpoint 的 effect 是否初始化数据、清空状态、导航或创建资源。
3. 确认 NavigationContainer/Store/controller 位于稳定层。
4. 区分普通 window resize 与确需 posture/rotation 语义的业务；删除无必要桥接分支。

## RTL、transform 或动画只在目标窗口错位

1. 分别冷启动 LTR/RTL，记录逻辑边、绝对定位、方向性图标和 translate 符号；RTL 不由宽高或姿态推断。
2. 同时记录 Yoga style/onLayout 和 transform/animated value，确认问题发生在布局几何还是视觉几何。
3. resize 中记录 animation epoch、旧新端点和 completion callback；旧回调覆盖新状态时先修 owner/清理。
4. React/Yoga 数据正确而最终 view 仍错误时才转 `RN-08` 做 RNOH 版本分流。

## Modal/Portal 路由后残留或尺寸陈旧

1. 标记 RN Modal、UI 库 Portal/Sheet、ArkUI Dialog 三层谁拥有 visible、route close、window、inset 和释放。
2. 弹窗打开时执行窄→宽→窄并记录 Portal root/content `onLayout`；只在打开瞬间计算一次几何属于 `RN-12`。
3. 核对锁定 RNOH FAQ/实现是否为 window-level Dialog；需要随页面消失时由唯一 owner 在 route 生命周期关闭。
4. 不通过重建 NavigationContainer 或重复消费 SafeArea 清理弹窗。

## 业务链正确但 Text/List/SafeArea 仍异常

1. 把问题缩小到原生 RN 组件的最小页面，保留锁定版本和目标设备。
2. 证明 window、派生 token、props、onLayout/业务锚点均正确。
3. 读取 `known-rnoh-layout-issues.md`，在对应 tag/release/源码中找同版本证据。
4. 优先验证兼容线内升级；临时关闭裁剪、移除 getItemLayout 或调整文本约束只作反证，不能无条件固化。
5. 没有版本对照和真机复现时标记 `not_verified`，不把症状直接命名为框架 bug。

## 原生模块编译或运行失败

1. 核对 lockfile、HAR、CLI、Codegen 和目标 SDK 是否同一兼容线。
2. 沿 Spec → config → generated → implementation → registration → wrapper 搜索名称、字段与事件。
3. 检查旧生成物、重复 Package、Autolinking 与手工注册冲突。
4. 编译通过后仍需验证 initial state、event、command、error、unsubscribe 和 invalidate。

## 根因确认标准

只有单一约束、传播点、契约或 UI 状态入口能稳定开启/关闭现象，并解释为何只在目标窗口或布局路径出现，才列为根因。扫描器告警、设备名、截图和发生时间只能作为线索。

提交前保留：输入模式、锁定版本、首个错误链路、修改文件、手机对照、临界值/目标窗口、动态往返、构建结果、UI 运行证据、未验证项和残余风险。
