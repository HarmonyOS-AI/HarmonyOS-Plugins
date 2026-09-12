# Skill 测试提示词

修改 description、输入模式、路由、禁止模式或资源索引后运行这些用例。检查 `RN-00`、可编辑层、首个错误链路、最少资源读取和完成声明。

## 应触发

1. “修改这个 RNOH 商品页，平板分屏时 Row 溢出。”期望 `RN_ONLY`，主场景 `RN-01`；从组件约束入手。
2. “FlatList 在展开屏要三列，并改成列表+详情双栏。”期望 `RN_ONLY`，主场景 `RN-02`；共享选中/路由状态并检查 item geometry。
3. “项目用 `rem = Dimensions.get('window').width / 375` 生成 fontSize 和间距，折叠展开后仍是外屏大小。”期望 `RN_ONLY`，主场景 `RN-03`；先证明 window 已更新，再修派生值、render 通知和 StyleSheet 消费链。
4. “Dimensions listener 已更新全局 `layoutScale`，但页面只有 reload 才变。”期望 `RN_ONLY`，主场景 `RN-03`；识别全局变量变化没有触发 React render。
5. “`useWindowDimensions` 已是新宽度，响应式库 runtime 也更新，但 active breakpoint 和 memoized styles 仍旧。”期望 `RN_ONLY`，主场景 `RN-03`；核对库 hook/subscription、memo deps 和组件 selector。
6. “外屏打开后展开，`useWindowDimensions` 自身仍是旧宽度；有 EntryAbility 和 RNSurface 源码。”期望 `HYBRID`，主场景 `RN-04`；沿 Host→RNInstance/RNSurface→Dimensions 找首错点。
7. “只有 ArkTS RNOH Host，请修多 RNInstance 的窗口尺寸广播。”期望 `HOST_ONLY`，主场景 `RN-04`；只改 owner/传播，输出 RN 验收交接。
8. “SafeAreaProvider 和 ArkUI Host 都加 bottom inset，键盘又把 Sheet 上抬两次。”期望 `HYBRID`，主场景 `RN-05`；先建所有权表。
9. “折叠后跳首页，代码给 NavigationContainer 设置 key={breakpoint}。”期望 `RN_ONLY`，主场景 `RN-06`；保持稳定根和 route state。
10. “折展后 FlatList 回到顶部；列数、可见 item key 和 getItemLayout 都已经核对，当前 RNOH release 有 contentOffset 修复。”期望主场景 `RN-08`，次场景 `RN-06`；先做最小复现和版本对照。
11. “window、layoutScale、Text props 和父 onLayout 都正确，但长文本仍按旧宽度换行。”期望主场景 `RN-08`；检查 TextMeasurer/锁定版本，不再叠 rem 补偿。
12. “RNSurface 和 wrapper 已变宽，通用 Fabric 卡片仍半屏且点击偏移。”期望 `HYBRID` 或 `NATIVE_ONLY`，主场景 `RN-07`；检查 native/Surface/坐标同一 epoch。
13. “升级 react-native-harmony 后通用 Fabric UI 的 Codegen 事件签名不一致。”期望 `HYBRID`，主场景 `RN-08`；核对完整版本闭环。
14. “`useWindowDimensions` 正确，但 Navigation 下的 ScrollView 高度是 0；给子节点加 `height: '100%'` 仍空白。”期望 `RN_ONLY`，主场景 `RN-09`；沿祖先 onLayout 找首个无界/零尺寸节点。
15. “阿拉伯语下抽屉仍从左侧进入，返回箭头、absolute right 和 translateX 方向都不对。”期望 `RN_ONLY`，主场景 `RN-10`；分开逻辑边、方向性图标和动画语义。
16. “展开屏动画中途 resize，onLayout 已是新双栏，但卡片 scale 后重叠，旧 completion 又把状态改回去。”期望 `RN_ONLY`，主场景 `RN-11`；区分 Yoga/视觉几何并用 epoch 清理旧动画。
17. “RN Modal 打开时折展仍用旧宽度，路由 replace 后 ArkUI Dialog 还在最上层。”期望 `HYBRID`，主场景 `RN-12`；确定唯一 overlay owner，并按锁定版本核对 Dialog 规格。
18. “项目要接入官方 RN 多设备组件的侧栏、栅格和 FoldSplitContainer，已有自建 breakpoint provider。”期望 `HYBRID` 或 `RN_ONLY`，主场景 `RN-13`、次场景 `RN-02/RN-06`；先核对包/HAR/版本并消除双 breakpoint source。
19. “`@hadss/react_native_breakpoints` 设置了 500/900 自定义阈值，HarmonyOS 真机仍按系统 xs/sm/md 切换；fallback 平台又按自定义值。”期望 `RN_ONLY` 或 `HYBRID`，主场景 `RN-13`、次场景 `RN-08`；识别原生 breakpoint index 与 JS 阈值分叉，不能继续叠第二个断点标签。
20. “页面和 Modal 都调用 `Avoid.addAvoidAreaListener`，关闭 Modal 后主页也收不到状态栏变化，padding 还是 px 直接写入 RN style。”期望 `HYBRID`，主场景 `RN-13`、次场景 `RN-05`；建立唯一 provider、px→layout unit 边界和多消费者 fan-out。
21. “想复制 adaptive-layout RC 的 GridRow 实现做响应式卡片流，要求支持 order、offset、超大 gutter 和嵌套容器。”期望 `RN_ONLY`，主场景 `RN-13`、次场景 `RN-02`；默认 `PATTERN_ONLY`，审计变量自引用、边界值、component onLayout 和 Yoga 公式后重写。
22. “已有 React Navigation，准备使用 NavigationSplitContainer.Screen 在平板保存选中页面。”期望 `RN_ONLY`，主场景 `RN-13`；拒绝第二份 route/selected owner，只复用 Stack/Split presentation 模型。
23. “普通折叠展开只需要列表变双栏，但方案引入 FoldSplit、orientation listener，并在卸载时 lockToPortrait。”期望 `RN_ONLY` 或 `HYBRID`，主场景 `RN-13`、次场景 `RN-02`；普通布局按 window，移除不必要 posture/方向副作用；只有真实半折/折痕才进入 `RN-06`。
24. “现有 breakpoint provider 已支持 base/md/lg；请让卡片字号、水平间距和图标尺寸随窗口档位变化。”期望 `RN_ONLY`，主场景 `RN-03`；复用唯一断点源和最小档兜底，以动态 style 覆盖静态 StyleSheet，不新增 rem 或第二套 provider。
25. “页面把 PixelRatio.get() 同时乘到 width、fontSize 和 padding，平板上整体异常放大。”期望 `RN_ONLY`，主场景 `RN-03`；布局值恢复为 RN layout units，PixelRatio 只保留在已确认的物理 px/资源边界。
26. “方案直接使用 375 基准宽、960 最大参考宽和 0.9～1.2 缩放范围，但项目里没有设计 token 或验收依据。”期望 `RN_ONLY`，主场景 `RN-03`；指出这些不是 RN/HarmonyOS 规范，删除魔法数字；缺少可追溯策略时不新建连续缩放。

## 不应处理

1. “普通 ArkUI GridRow 页面适配平板，没有 RN/RNOH。”属于 ArkUI 多设备技能。
2. “WebView 里的 Vue 页面 CSS REM 折叠后没更新。”属于 H5 多设备技能；RN 自定义 rem 才属于本 skill。
3. “RNOH 相机折展后预览黑屏、照片方向错误。”属于相机专项，不由本 UI 布局 skill 处理。
4. “PC 上 Tab 焦点顺序和鼠标右键不正确。”属于硬件输入专项。
5. “原生手写画布 pressure 丢失。”属于手写笔/画布专项。
6. “Android RN 页面在三星折叠屏上崩溃。”没有 HarmonyOS/RNOH 范围。
7. “实现 HarmonyOS 跨设备数据接续。”不属于本 skill 的响应式 UI 边界。

## 边界用例

1. 同时出现 `.ts` 与 `.ets`：按目录、导入、语法和调用链分类，不把普通 TS 自动算 ArkTS。
2. 只有截图和日志：`INSUFFICIENT`，列入口、锁文件、Host/Dimensions/token/style/onLayout 证据，不生成未验证补丁。
3. 提供 RN+Host+Fabric，但根因是 TSX 模块级 rem：`HYBRID`；只改 RN 派生层，记录其余链路无影响，不强造原生改动。
4. `Dimensions.get('window')` 在 render/事件中即时读取：不是自动错误；只有缓存或消费者不随变化更新才修。
5. `StyleSheet.create` 只含静态不变量：允许模块级；只有其中求值依赖可变 window/rem 时才迁移动态部分。
6. `Dimensions.addEventListener`：不是自动过时；hook 不适用且 subscription 有 owner/remove，并通过 state/store 通知消费者时允许。
7. `fontSize: token * layoutScale`：不自动判错；检查 Text 默认 fontScale 后是否符合可访问性。`width: token * fontScale` 才是明显的语义混用。
8. 用户指定某平板/折叠机：设备名只用于复现矩阵，布局仍按 application window。
9. UI 确需 half-fold/crease：允许 posture bridge，但不让它决定普通单双栏或 rem。
10. 业务代码与目标版本 release 有相似症状：先证明当前锁定版本和最小复现，不因历史修复标题直接归因框架。
11. 通用原生 UI wrapper bounds 正常、内部 Surface 陈旧：属于 `RN-07`；若组件是相机或手写画布则移交专项。
12. Build 通过但无目标设备：静态/构建通过，运行结论 `not_verified`。
13. `height: '100%'`：不是自动错误；只有父级无确定高度或 viewport/content owner 混乱时进入 `RN-09`。
14. `left/right`：物理边语义允许；普通内容锚点、抽屉和方向动画需验证 RTL，不能机械全量替换。
15. `transform`：纯视觉过渡允许；若目标是改变相邻布局或真实可用空间，必须更新 Yoga 布局而不是继续叠 transform。
16. 官方多设备组件已安装：仍需读取真实类型/版本；不重复实现，也不把旧 README 接口当当前 API。
17. adaptive-layout 某个组件满足当前视觉效果：不是自动允许 `DIRECT`；先按 `DIRECT/ADAPTER/PATTERN_ONLY/REJECT_BY_DEFAULT` 检查版本、受控状态、单位、依赖、owner 和生命周期。
18. avoid-area 与 safe-area-context 同时存在：不自动删除任一依赖；先证明 Host 窗口策略和实际 inset 来源，再确定唯一生产者与兼容 adapter。
19. 自定义断点在 Android/iOS 正常：不能外推 HarmonyOS 原生 breakpoint index 路径；必须在目标 RNOH 版本用非默认阈值实测。
20. Fold crease 数组有数值：不代表可直接布局；先确认坐标系和 px/layout unit，转换一次后再验证 absolute/Flex 布局。
21. 项目没有 rem/scale 体系，只需要三个断点的字号和间距：不要新建设计稿等比缩放；使用现有唯一 breakpoint source，或由 `useWindowDimensions` 集中派生离散 token。
22. 颜色和固定圆角位于模块级 `StyleSheet.create`：不是 `RN-03` 缺陷；只有依赖可变 window/breakpoint/token 的求值被冻结时才迁移动态部分。
23. 项目 design token 明确把 375 定义为基准宽：不能因为数值是 375 就判错；应检查来源、连续缩放是否为既定策略、上下限是否有验收依据，以及消费者是否响应 window。

## 评分点

- 首先输出 `input_mode` 与锁定版本证据；`RN-00` 不作为主场景。
- 单端模式不越界；交接项有 owner、契约、时序、清理和验收。
- 沿 window→Host→Dimensions→breakpoint/token/custom scale→parent constraints/viewport→StyleSheet/component/list→Yoga/onLayout→transform/portal→native/Surface 找首个错误链路。
- window 陈旧与派生 token 陈旧分开归因；原始 width 正确时不修改 Host。
- 自定义 layoutScale、系统 fontScale 与 PixelRatio 分开，不双重缩放、不全局关闭字体缩放掩盖问题。
- 离散字体、间距、图标、列数和布局方向优先复用唯一 breakpoint source；连续 scale 仅用于已有设计单位体系并限制范围，不凭示例新增依赖、阈值或 rem。
- 连续缩放的 `baseWidth`、`minScale`、`maxScale` 必须可追溯到项目设计 token/规范和目标窗口验收；不得把 375、960、0.9、1.2 等示例数字当作平台规范。
- 普通布局不使用物理 screen、设备类型、posture 或 window mode；宽而短窗口同时检查 height。
- 不用 reload、width/breakpoint key 或重建 RN root 修动态样式；导航、表单和列表业务状态连续。
- 框架/版本归因必须有锁定版本、最小复现、对应 tag/release 和目标设备证据。
- 原生 UI 扩展经过版本、Spec、Codegen、实现、注册、wrapper 和释放闭环。
- 父约束、RTL、动画 endpoint/epoch、overlay owner 与官方组件依赖按命中场景验证，不用固定屏高、全局 row-reverse、translate 补偿或重复 provider 掩盖问题。
- `RN-13` 能给出四级采用结论；识别断点原生/JS 语义分叉、RC Grid/显隐/分栏风险、avoid/fold px 单位和模块级单 listener，并用 adapter/provider 保持 breakpoint、inset、fold 与 navigation 单一 owner。
- 手机基线、两种冷启动方向、折→展→折、断点临界值、分屏/自由窗、前后台和重复进入完成回归；缺证据明确 `not_verified`。

## 扫描器回归片段

修改 `scripts/scan-rn-adaptation.mjs` 后，至少用最小 TSX fixture 验证以下配对。每个正例必须出现对应 rule id，反例不得因关键字相邻而误报：

| 范围 | 应报警 | 不应报警 |
|---|---|---|
| Image | Image 自身 `width: '100%'` + `aspectRatio` | 外层 View 持有比例，Image `absoluteFill` |
| FlatList | 动态 `numColumns` 且无列表层 `key` | 动态列数 + 只重挂 FlatList 的 presentation key |
| List/Scroll | `getItemLayout` 缓存启动 Dimensions；ScrollView 用物理屏高 | geometry 随 width/columns 重算；有界父链 + `contentContainerStyle.flexGrow` |
| Fold | 只注册 listener、不读初值/不清理；状态与裸数字比较 | 唯一 provider 先订阅、再取快照、同引用清理、adapter 归一化 |
| Avoid | listener 无清理；读取区域无单位边界；与 KAV 双 owner | 唯一 provider、版本已核验的单次单位转换、单一键盘策略 |
| 方向 | listener 无 remove；锁定后无恢复 | 同 handler 清理；退出时恢复进入前策略 |
