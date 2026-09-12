---
name: harmonyos-rn-multi
description: 审查并修改 React Native for OpenHarmony（RNOH）应用的多设备 UI 布局，包括动态窗口、父约束与滚动、多设备资源差异化与动态样式（断点字体/间距、设计 token、自定义 rem/scale）、RTL、Transform/布局动画、Modal/Portal、折叠连续性、安全区、官方多设备布局组件，以及通用 Fabric 原生视图 resize。用户提到 RN/RNOH、平板/折叠屏/PC/分屏/自由窗口、尺寸或字号不刷新、内容溢出/空白/错位、RNSurface 不同步时使用；纯 ArkUI、纯 H5、相机内容链路、硬件键鼠/手写笔和非 HarmonyOS 的普通 React Native 任务不使用。
---

# HarmonyOS React Native 多设备适配

## 适用范围与所有权

处理现有 RNOH 工程中的 React/TypeScript、RNOH ArkTS 宿主、TurboModule、Fabric Native Component，以及确有必要的 HarmonyOS 原生能力代码。保留项目已有 RN/RNOH 版本、导航、状态管理、设计语言、构建方式、Codegen 和注册机制。

- **RN JS** 负责当前应用窗口内的 Flexbox、断点、设计 token 与动态样式、页面结构、导航呈现和业务状态。
- **RNOH Host** 负责把应用窗口变化传播到正确的 RNInstance/RNSurface，并管理宿主监听生命周期。
- **TurboModule** 只提供 RN 当前版本无法表达的非可视系统快照、命令或事件。
- **Fabric** 只承载必须嵌入 RN 的通用原生 UI，并消费 RN 布局提交。
- **共享契约** 负责事件名、字段、单位、序列、首次状态、错误和释放，不复制第二套断点或业务状态。

纯 ArkUI 页面、纯 H5/WebView 页面、相机预览/拍照/录像、硬件键鼠/触控板/手写笔、跨设备数据流转，以及与 HarmonyOS 无关的普通 RN 功能不属于本 skill。

## 强制前置审计

所有任务先执行 `RN-00`，完整读取 `references/capability-boundary.md`，根据实际文件、锁定版本、导入和调用链判定：

- `RN_ONLY`：只修改 JS/TS/TSX；缺少必要原生生产者时输出交接项。
- `HOST_ONLY`：只修改 RNOH ArkTS 宿主和窗口传播；不虚构 React 消费端。
- `NATIVE_ONLY`：只修改已有 TurboModule/Fabric/原生能力实现；不虚构 JS wrapper 或 Spec。
- `HYBRID`：至少两层源码与调用关系可定位；先固定跨层契约，再联动检查。
- `INSUFFICIENT`：源码、锁文件或调用链不足；只诊断并列出缺失材料。

`RN-00` 是前置审计，不计入主次场景。写代码前记录 `input_mode`、锁定版本证据、可编辑层、第一错误链路候选和缺失对端；发现新源码后重新判定。

## 核心判断框架

1. **沿尺寸、约束与呈现链找首错点**：按 `HarmonyOS window → RNOH Host/RNInstance/RNSurface → RN Dimensions → breakpoint/token/custom scale → parent constraints/scroll viewport → StyleSheet/component/list → Yoga/onLayout → transform/animation/portal → native view/Surface` 检查；上一段错误未修复时不在下一段叠补丁。
2. **先自适应，后响应式**：Flexbox 收缩、增长、换行、滚动或比例能解决时不加断点；信息结构、导航位置或列数变化时才使用断点。
3. **以应用窗口为准**：普通布局读取 `useWindowDimensions()` 或当前 `Dimensions.get('window')`。字体、间距、列数等离散值优先复用工程唯一的断点源；确需连续变化时，自定义 `rem/rpx/scale/normalize` 必须由最新 window 派生、限制变化范围并触发消费者重渲染。不要按物理屏幕、机型、设备类型、fold posture 或窗口 mode 枚举决定断点。
4. **保持稳定身份**：窗口变化不重建 React 根、NavigationContainer、Provider、Store、route、表单或原生组件业务状态。
5. **选择最小实现层**：遵循 `RN_JS → HOST → TURBO_MODULE → FABRIC`；当前版本已有能力时不新增原生桥接。
6. **版本证据优先**：以 lockfile、已安装类型/实现、对应 tag 文档和目标设备实测为准，不从 Android/iOS 或其他 RNOH 版本外推。
7. **把四类 scale 分开**：应用窗口比例、自定义设计单位、`fontScale`（用户文字偏好）和 `PixelRatio/scale`（像素密度）不能混用或重复相乘；尺寸、方向、折叠姿态和窗口模式也分别建模。

## 禁止模式

- 禁止永久缓存模块加载时的窗口宽高，或用 `Dimensions.get('screen')`、`Platform.isPad/isTV`、机型和物理 display 尺寸驱动布局。
- 禁止在模块顶层计算一次 `rem/rpx/layoutScale/normalize` 后让 `StyleSheet.create` 永久持有；只改变全局变量而不触发 React render 同样无效。
- 禁止把项目自定义“根字号/rem”当作 RN 的系统 `fontScale`，或把 `fontScale`/PixelRatio 乘到页面宽高、断点和整套间距。
- 禁止为修复文字溢出而全局关闭 `allowFontScaling`；先区分设计单位缩放、系统文字缩放、容器约束和锁定 RNOH 文本测量行为。
- 禁止用 `PixelRatio` 缩放页面、断点、字体或整套间距；它只处理密度、资源清晰度和明确的物理像素换算。
- 禁止用 `key={width}`、`key={breakpoint}`、随机 key 或重建 RNInstance/RNSurface 代替 resize。
- 禁止让 ArkTS/Fabric 维护第二份导航、选中项、表单或通用原生 UI 业务状态。
- 禁止在未读取锁定 Spec、Codegen、注册和实现时虚构 RNOH API、prop、事件或生命周期。
- 禁止手改 Codegen 生成物；Spec 变化后使用工程锁定工具重建并核对注册。
- 禁止把静态扫描、截图或编译成功当成目标设备行为已验证；缺少关键设备/事件/画面证据时写 `not_verified`。
- 禁止为了普通单双栏、折展或分屏布局新增 posture/window-mode TurboModule。
- 禁止用无边界的百分比高度、只改 `contentContainerStyle` 或任意固定屏高掩盖父约束链断裂；ScrollView/List viewport 必须来自有界祖先。
- 禁止把 `left/right`、`row-reverse` 或负 translate 当作通用 RTL 适配；方向、逻辑边、方向性图标和动画位移分别处理。
- 禁止假定 `transform` 会改变 Yoga 占位或相邻组件布局，也禁止让 Native Driver 驱动宽高/Flexbox 等布局属性。
- 禁止让 RN Modal、第三方 Portal 和 ArkUI Dialog 同时拥有同一覆盖层；路由、窗口、安全区和关闭生命周期必须有唯一 owner。
- 禁止仅因存在官方多设备组件库就替换项目已有布局体系；先核对锁定版本、平台支持、依赖和单一 breakpoint/inset source。
- 禁止把 `rn_multidevice_layout_scenepkg` 的 RC 组件、README 深路径 import 或示例代码直接当作生产模板；按 `RN-13` 将能力分为 `DIRECT`、`ADAPTER`、`PATTERN_ONLY`、`REJECT_BY_DEFAULT`，并以实际安装源码/HAR 为准。
- 禁止同时运行项目 breakpoint provider、独立 breakpoints Manager 和 adaptive-layout 内置断点；自定义断点还必须证明 HarmonyOS 原生路径与 JS fallback 使用同一阈值和高度语义。
- 禁止把 HarmonyOS avoid-area/fold crease 的物理 px 直接写入 RN style，或由多个页面各自换算；单位转换、初始快照、事件 fan-out 和清理由唯一 adapter/provider 持有。
- 禁止让第三方 NavigationSplit/Fold/avoid-area 的模块级单监听或内部页面状态成为第二个全局 owner；现有 React Navigation、方向策略、inset 和 listener 生命周期保持唯一来源。

## 场景路由

完成 `RN-00` 后，根据首个错误约束选择一个主场景；只有存在独立关联根因时才增加次场景。只读取命中场景的资源。

| 场景                        | 命中条件                                                                                     | 必读资源                                                                            | 不要读取                           |
| ------------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------------ |
| `RN-01` 组件自适应             | Row/Flex 子项溢出、文本截断、图片/视频拉伸、固定尺寸                                                          | `references/responsive-layout.md`                                               | 原生桥接专章，除非 JS bounds 已正确        |
| `RN-02` 页面响应式             | 列表增列、主从栏、Tab/侧栏切换、宽屏留白                                                                   | `references/responsive-layout.md`                                               | 原生 UI 专章，除非 wrapper bounds 已正确 |
| `RN-03` 多设备资源差异化与动态样式     | 断点字体/间距/图标/组件尺寸、自定义 rem/rpx/scale/normalize、折展后 StyleSheet/动画端点不更新                         | `references/dynamic-scaling-and-styles.md`                                      | Host 专章，除非原始 Dimensions 也陈旧    |
| `RN-04` 动态窗口与宿主           | `useWindowDimensions` 本身不更新、RNSurface 半屏、多实例 owner、分屏/自由窗错序                              | `references/window-and-continuity.md`                                           | RN-03 专章，除非原始 window 已正确但下游陈旧     |
| `RN-05` 安全区与键盘            | 状态栏/挖孔/导航条遮挡、双 inset、输入框或操作栏被键盘遮挡/双重上抬                                                   | `references/safe-area-and-keyboard.md`                                          | 方向专章，除非有独立旋转问题                 |
| `RN-06` 折叠、方向与连续性         | 开合跳首页、列表位置丢失、快速折展竞态、半折/折痕、页面方向请求、180° 状态                                                 | `references/window-and-continuity.md`                                           | 普通布局无需姿态桥接                     |
| `RN-07` 原生 UI 与桥接         | 通用 Fabric view/Surface resize、UI 触控坐标错位、TurboModule/Fabric 选型、Codegen/注册                 | `references/native-bridge-and-resize.md`                                        | 相机、画布和输入设备专项不处理                |
| `RN-08` 版本与已知行为           | RN/RNOH/HAR/CLI/UI 库不一致，或 Text/Scroll/List/SafeArea/Modal/Transform/Animation 在业务链正确后仍异常 | `references/compatibility-matrix.md` + `references/known-rnoh-layout-issues.md` | 未形成最小复现时不先归因框架                 |
| `RN-09` 父约束与滚动视口          | `flex`/百分比子项为 0、ScrollView 空白/不能滚动、宽短窗口操作不可达、网络图片无稳定几何                                   | `references/layout-constraints-and-scroll.md`                                   | Host 专章，除非根 viewport 本身已错误     |
| `RN-10` RTL 与逻辑布局         | 阿拉伯语/希伯来语下左右错位、抽屉/绝对定位/箭头/动画方向错误                                                         | `references/rtl-and-logical-layout.md`                                          | 不用设备方向代替语言方向                   |
| `RN-11` Transform 与布局动画   | transform 后重叠、onLayout 与视觉位置不一致、resize 中动画跳变/终点陈旧、Native Driver 布局属性无效                   | `references/transform-and-layout-animation.md`                                  | 业务尺寸链未证明正确前不归因 RNOH            |
| `RN-12` Modal、Portal 与覆盖层 | 路由后弹窗残留、弹窗仍按旧窗口、重复安全区、RN Modal/Portal/ArkUI Dialog 层级冲突                                  | `references/modal-and-portal.md`                                                | 普通页面重排不使用覆盖层方案                 |
| `RN-13` RNOH 官方多设备组件      | 工程已使用或明确评估断点、显隐、侧栏、分栏、栅格、FoldStack/FoldSplit/避让区域组件                                      | `references/rnoh-adaptive-components.md`                                        | 未确认依赖与目标版本时不直接引入               |

基础流程无法形成可证伪根因时读取 `references/troubleshoot.md`。修改真实工程前可运行：

```bash
node scripts/scan-rn-adaptation.mjs <工程根目录>
```

扫描器只提供输入模式候选和启发式线索。退出码 `1` 表示发现高风险项，不表示脚本执行失败；根因仍以源码调用链、锁定版本、同轮次 bounds/事件和复现实验为准。

修改扫描规则后运行 `node scripts/test-scan-rules.mjs`，确认 Image、列表、Fold、Avoid 和方向清理规则的正例仍可命中；再对 `assets/recipes/` 自扫描，避免推荐 recipe 引入已知风险模式。

按问题补充读取以下资源，不要把它们变成所有任务的固定前置：

- 需要真机、动态窗口、裁剪或跨层几何证据时，读取 `references/device-evidence-toolchain.md`。
- 症状命中 Image、FlatList、ScrollView、Fold、折痕、Avoid、安全区、键盘或方向恢复案例时，读取 `references/rnoh-layout-casebook.md`。
- 用户不接受新增依赖，或 RN-13 评估结论不是 `DIRECT` 时，读取 `references/rn-built-in-fallbacks.md`。
- 需要复制一个最小实现骨架时，读取 `references/recipe-index.md`，只选与主场景匹配的 asset。
- RN-13 只读取 `references/adaptive-components/` 下与实际候选能力对应的 API 文档，不预加载全部组件资料。

## 新适配流程

1. **建立源码与版本地图**：定位 RN 入口、导航、页面、样式、宿主、RNInstance/RNSurface、原生扩展、Spec/Codegen/注册和真实锁定版本。
2. **记录手机基线**：记录结构、路由、状态 owner、滚动/焦点、窗口与 wrapper bounds、关键原生资源和核心操作。
3. **寻找断裂点**：连续改变应用窗口宽高，沿尺寸、约束与呈现链比较同一轮次数据，区分 Host 未传播、派生值陈旧、祖先无界、列表/测量缓存、RTL 逻辑边、transform/动画、覆盖层、原生 view 未 resize 和版本行为。
4. **读取专项资源**：选择主场景后完整读取对应 reference；需要运行证据、已知案例、纯 RN 回退或 recipe 时再读取对应补充资源，不预加载无关领域。
5. **实施最小适配**：先修上游约束，再增加必要的布局、宿主传播或跨层契约；保持导航、业务和原生资源身份连续。使用 asset 时只复制所需文件，并替换示例阈值、port 和 owner。
6. **执行回归**：验证手机、目标窗口、临界状态、折→展→折与窄→宽→窄、前后台和重复进入；记录每态 window、派生 scale/token、关键 computed style/onLayout 和列表锚点，按改动补充安全区、软键盘或通用原生 UI 路径。

## 问题定位流程

1. **收集可比较证据**：记录正常/异常状态的 window/screen、RN Dimensions、breakpoint/token/custom scale、关键 StyleSheet/props/onLayout、列表锚点、RNSurface、wrapper/native/Surface bounds、事件序列、版本和相关 UI/业务状态。
2. **定位首个错误链路**：从最终异常向上游逐段反查，找到“上一段正确、下一段错误”的边界；原始 width 已更新而 rem/style 未更新属于 RN 派生层，不归因 Host。
3. **做最小反证**：隔离一个尺寸约束、监听、memo/key、桥接字段或状态机入口，确认它能稳定开启/关闭现象。
4. **修复根因**：修改最小文件集合；跨层变化同步检查 Spec、Codegen、注册、首次状态、序列、错误、坐标单位和清理。
5. **验证并清理**：删除临时诊断代码，确认相同最终窗口得到相同结果，无需重启 React 根或丢失业务状态。

## 完成门槛

- 手机窄屏的路由、结构、触摸、滚动、状态和视觉无退化。
- 目标窗口与断点临界状态无重叠、截断、错误裁切、半屏 Surface 或触控错位。
- 折展、旋转、分屏、自由窗口和窄→宽→窄后无需重建 React 根，业务状态连续。
- 同一最终 window 得到相同的 breakpoint、设计 token、自定义设计单位和关键布局值；`fontScale` 与 PixelRatio 不被误当页面缩放输入。
- 接入官方社区多设备包时，非默认断点在原生/JS 路径结果一致，px→RN layout unit 只转换一次；两个并发消费者中任一卸载不会使另一方停止更新。
- ScrollView/List 拥有可解释的有界 viewport；RTL 冷启动、resize 中动画和已打开覆盖层在相同最终窗口得到确定结果。
- 修改未越过输入模式允许层级；缺失对端有可执行交接项。
- 新增 listener、subscription、Surface 和异步任务有明确 owner，并在卸载/invalidate 时幂等释放。
- Spec、Codegen、实现、Package/Component 注册和 JS wrapper（如涉及）来自同一锁定兼容线。
- 静态检查、构建与运行验证分开报告；没有真实目标路径证据的项目标为 `not_verified`。

## 交付内容

最终答复简洁说明：

1. `input_mode`、锁定版本和文件/调用链证据。
2. 主场景、首个错误链路和修改文件。
3. 实施内容以及静态、构建、运行验证结果。
4. 必要的对端交接、`not_verified` 和残余风险；没有则省略。

不要输出空字段堆砌的内部账本，也不要把“流程完成”表述为“目标设备验证通过”。

## 支持资源

- `references/capability-boundary.md`：所有任务首先完整读取。
- 场景 reference：仅按路由表读取。
- `references/troubleshoot.md`：基础定位无法形成可证伪根因时读取。
- `references/known-rnoh-layout-issues.md`：只有业务尺寸、父约束与呈现链正确但 Text/Scroll/List/SafeArea/Modal/Transform/Animation 等仍异常，或版本升级/降级相关时读取。
- `references/rnoh-adaptive-components.md`：仅在工程已使用或用户明确评估官方多设备布局组件时读取，不作为普通 Flexbox 的默认依赖。
- `references/adaptive-components/`：RN-13 下按候选能力读取的 Breakpoint、Grid/DisplayPriority、SideBar/Navigation、AvoidArea 和 Fold 容器 API 审计资料。
- `references/device-evidence-toolchain.md`：需要目标设备、dump、动态窗口或跨层 bounds 证据时读取。
- `references/rnoh-layout-casebook.md`：Image、FlatList、ScrollView、Fold、Avoid、键盘和方向问题与案例高度相似时读取。
- `references/rn-built-in-fallbacks.md`：不新增依赖或第三方能力未通过准入时读取。
- `references/recipe-index.md`：需要复制最小页面、列表、媒体、证据探针或唯一 Provider 骨架时读取。
- `references/test-prompts.md`：修改 description、输入模式、路由、禁止模式或资源索引后，用于回归触发和决策行为。
- `assets/responsive-shell/`：新建普通响应式 RN 页面且项目没有更合适封装时复制并按现有架构改造；其中 `useDesignUnits.ts` 展示可响应 window 的设计单位，不要照搬示例阈值，也不要覆盖已有导航、主题或 breakpoint 实现。
- `assets/recipes/`：10 个按场景选择的 TSX recipe；Fold/Avoid 通过注入式 port 隔离包版本，业务代码不得据此虚构原生 API。
- `scripts/test-scan-rules.mjs`：扫描器专项回归，使用临时 fixture 验证新增规则并自动清理。
