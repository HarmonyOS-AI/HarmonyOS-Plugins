# RNOH 官方社区多设备布局组件选型

## 何时读取

仅在以下情况读取：工程已经依赖官方社区多设备组件；用户明确要求评估/接入；或现有项目重复实现了需要统一的断点、显隐、侧栏、分栏、栅格、折叠容器或避让区域能力。普通 Row 溢出、一个页面的简单断点仍优先用 RN Flexbox、`useWindowDimensions()` 和项目现有 tokens。

## 专项 API 资料路由

只读取实际候选能力对应的文件：

| 候选能力 | 专项资料 |
| --- | --- |
| BreakpointManager、响应值 Hook、自定义阈值 | `adaptive-components/breakpoints-api.md` |
| Grid、span/offset/order/gutter、DisplayPriority | `adaptive-components/grid-and-display-priority.md` |
| SideBar、NavigationSplit、Stack/Split presentation | `adaptive-components/sidebar-and-navigation.md` |
| system/cutout/navigation-indicator 避让区域 | `adaptive-components/avoid-area-api.md` |
| Fold 状态、折痕、FoldSplit/FolderStack | `adaptive-components/fold-containers.md` |

专项文件提供接入检查和稳定业务契约，不替代本文件的四级采用结论。

## 能力边界

官方社区 `rn_multidevice_layout_scenepkg` 公开资料包含：

- `react_native_breakpoints`：横向/纵向 breakpoint、Manager 和响应值 Hook；
- `react_native_adaptive_layout`：显隐、侧栏、分栏、栅格、FoldStack/FoldSplitContainer；
- `react_native_avoid_area`：system、cutout、system gesture、keyboard、navigation indicator 区域及变化监听；
- 另有视频与统一输入包，但本 skill 不读取或接入这些非 UI 布局专项；键盘类型仍按 `RN-05` 的唯一避让 owner 处理，不因 avoid-area 包扩大输入专项范围。

这些能力是候选实现，不是强制依赖。仓库和包名经历过迁移/演进，必须以工程 lockfile、实际安装的 JS/TS、HAR、Codegen 产物、目标 RNOH 分支和设备实测为准，不从旧 README 复制安装命令或深路径 import。

## 已审计发布物基线

2026-08-31 对发布物源码完成过一次基线审计：

- `@hadss/react_native_breakpoints@1.0.6`；
- `@hadss/react_native_adaptive_layout@1.0.0-rc.2`；
- `@hadss/react_native_avoid_area@1.0.0-rc.1`。

该基线只说明这些版本已发现的行为，不代表后续版本仍相同。遇到其他版本必须重新检查实际源码和类型，不能把本节当成永久版本结论。

## 四级采用结论

| 能力 | 默认级别 | 决策 |
| --- | --- | --- |
| breakpoint Hook、订阅、响应值向小断点回退 | `ADAPTER` | 可封装在项目 breakpoint provider 后；先证明自定义阈值、单位和事件在目标版本一致 |
| Grid 的 columns/span/offset/order/gutter 模型 | `PATTERN_ONLY` | 借鉴属性和容器断点模型；当前审计版本不作为默认直接依赖 |
| DisplayPriority 显隐模型 | `PATTERN_ONLY` | 借鉴业务优先级；按真实 `onLayout`/内容尺寸重写 |
| SideBar 的 Embed/Overlay/Auto | `PATTERN_ONLY` 或 `ADAPTER` | 复用前验证受控状态、容器宽度、动画依赖和 RTL |
| Navigation 的 Stack/Split/Auto | `PATTERN_ONLY` | 只切换 presentation；现有 React Navigation 保持 route 唯一 owner |
| avoid-area 快照和事件契约 | `ADAPTER` | 应用级唯一 provider 持有监听并完成 px→RN layout unit 转换 |
| Fold 状态和折痕区域 | `ADAPTER` | 仅半折/悬停/折痕需要；普通单双栏仍按当前 window |
| 整体直接引入 adaptive-layout | `REJECT_BY_DEFAULT` | RC 或未完成目标版本验证时不整库替换现有布局体系 |

`DIRECT` 只允许用于锁定版本已匹配、无重复 owner、目标场景测试通过且项目接受该依赖维护成本的组件。`ADAPTER` 表示业务代码不得直接散落包 API；`PATTERN_ONLY` 表示只借鉴状态或属性模型，不复制实现；`REJECT_BY_DEFAULT` 需要项目级证据才能例外。

## 断点实现规则

1. 普通页面首先使用 `useWindowDimensions()` 或由它驱动的项目 provider；组件内部响应式布局可使用组件 `onLayout` 宽度。不要以 `screen`、设备类型或 fold status 代替 application window。
2. 项目已有 breakpoint provider 时不得再并行创建包内 Manager。独立 breakpoints 包、adaptive-layout 内置断点和项目 tokens 只能选择一个权威断点源；其他层只做值映射。
3. 自定义 `setBreakpoints()` 必须在应用初始化或 provider 配置阶段执行一次，不在组件 render 中反复修改全局断点表。
4. 审计过的 breakpoints HarmonyOS 原生路径通过 ArkUI window breakpoint index 映射固定名称，自定义 JS 阈值不一定参与该路径。接入前用非默认阈值在临界值前后实测；失败时改为当前 window 的纯 JS 计算，不能声称“已支持自定义断点”。
5. 审计版本的高度断点语义不统一：HarmonyOS 原生路径读取 window height breakpoint，JS fallback 按 `height / width` 宽高比计算。业务必须明确需要的是高度还是宽高比，并只保留一种语义。
6. 全局 Manager 的监听由应用 provider 持有。页面只能 unsubscribe 自己的 callback，不调用会终止全局 Dimensions 监听的 `destroy()`；重复挂载后仍要能接收更新。
7. 断点只决定信息结构、列数或 navigation presentation；rem/scale/fontSize 仍由最新 window 派生并触发 React render，不能只更新 breakpoint label。

## 显隐、栅格、侧栏和分栏规则

### DisplayPriority

- 空间是否足够必须来自真实容器和子项测量；不能只解析静态 `style.width/height`，因为文本、动态 children、字体缩放、图片固有尺寸、margin 和换行都会改变实际占用。
- `children`、容器尺寸、方向、gap、padding、字体和影响测量的状态改变后重新计算。
- 同优先级组可整体显隐，但关键操作不能仅因空间不足变得不可达；必要时改为 overflow 菜单、折行或滚动。
- 额外 wrapper 会改变 Flex、语义和无障碍树时，不复制原组件结构。

### Grid

- 可以采用 `columns/span/offset/order/gutter` 与 window/component reference 模型，但必须验证负数、零、越界 span/offset、响应式 order、超大 gutter、RTL、空 children 和嵌套容器。
- 审计的 adaptive-layout RC 源码中 `order` 计算存在变量自引用风险，且对非法 span/offset 的约束不完整；未在目标版本证明修复时只借鉴模型。
- component reference 必须由组件自己的 `onLayout` 驱动；保留调用方 `onLayout` 时组合回调，不能让 props spread 覆盖内部测量。
- 不复制依赖浮点魔数的 Yoga 宽度补偿。先用稳定的总列数、gutter 数量和容器可用宽度建立可解释公式，并验证换行边界。

### SideBar 与 NavigationSplit

- 模式切换使用组件实际 container width 和 `minSideBarWidth + minContentWidth + divider` 等内容约束，不用物理 screen、硬编码设备类别或仅用启动 window。
- `showSideBar`、mode、宽度范围等受控 prop 在运行时变化必须同步；effect/memo 依赖包括所有参与计算的 prop、容器尺寸和 design token。
- 现有 React Navigation、route registry、active route 和返回栈保持唯一 owner。不得让 `NavigationSplitContainer.Screen` 再维护第二份选中页面或返回状态。
- 拖动宽度、Overlay/Embed 切换、RTL、焦点/无障碍、窄→宽→窄后的用户显隐选择都必须验证；不能用重挂 NavigationContainer 复位。
- 引入 SideBar 前核对 Reanimated、Orientation 等 peer dependency 和目标 RNOH 兼容线；只为普通双栏不增加无关原生依赖。

## 避让区域规则

1. 建立 owner 表：RNOH Host、`react-native-safe-area-context`、avoid-area 包、页面 padding、Modal/Portal 中只能有一个 inset 生产者和一个明确消费策略。
2. HarmonyOS `AvoidArea` Rect 的单位必须从锁定包类型/实现和设备证据确认；RN style 数值是布局单位。需要转换时只在原生→RN adapter 边界执行一次，并在契约字段标明原始/目标单位，禁止页面各自猜测或重复转换。
3. 应用级 provider 完成“同步初始快照→注册变化监听→按 type 合并→发布 React state→幂等释放”。页面不直接反复调用原生 listener。
4. 审计版本的 JS wrapper 使用模块级单 subscription，remove 还可能影响同事件的其他消费者；未证明目标版本支持多订阅前只允许一个 provider owner。
5. system、cutout、navigation indicator 不能机械相加；按四边取符合当前窗口策略的有效区域，并结合是否沉浸式判断。隐藏或零区域应正确回落。
6. 本 UI skill 不使用 `TYPE_KEYBOARD` 代替已有键盘策略；软键盘仍按 `RN-05` 判断，避免窗口 resize、KeyboardAvoidingView 与 avoid-area 三重避让。

## Fold 与折痕规则

1. 普通折→展、分屏和自由窗只要能由 application window 表达，就不引入 Fold module。只有半折/悬停布局、真实折痕避让或产品明确要求 posture 时使用。
2. HarmonyOS 折痕 Rect 的单位和坐标空间依赖实际 API/版本；进入 RN 前由 adapter 映射到 owning application window 的唯一布局单位。不得未经证明就把原生 top/height 用于 RN absolute position。
3. Fold listener 必须支持多个消费者或由单一 provider fan-out。禁止模块级单 callback 被后注册者覆盖，禁止一个页面卸载时关闭全局原生监听。
4. 保存原始 Dimensions/Orientation/Fold callback 或 subscription，并用相同引用幂等移除。组件卸载不得全局 `lockToPortrait()` 或改变其他页面方向策略。
5. FoldSplit/FolderStack 使用 absolute layout 前验证动态内容、滚动、字体缩放、短高度窗口、折痕横纵方向和快速折→半折→展事件；普通内容优先 Flex/Grid。

## 选型流程

1. 记录 RN、RNOH、CLI、HAR、组件包、peer dependencies 与 HarmonyOS SDK 锁定版本。
2. 检查 breakpoint/inset/fold/navigation provider；同一数据只保留一个权威 source，并画出快照、事件、单位和清理链。
3. 从实际安装包而非网页摘要验证 public exports、深路径 import、平台实现、Autolink/Codegen/HAR 注册、API/设备版本门槛和 listener 实现。
4. 按四级采用结论对比项目最小 RN 实现。只有复用收益、跨页面一致性或原生折痕/避让能力明显时引入依赖。
5. 通过项目 tokens/provider/adapter 暴露稳定接口；业务页面不感知包版本、原生 breakpoint index、物理 px 或 listener 生命周期。
6. 若缺少 package/HAR、类型、对端注册、目标设备或动态窗口证据，输出具体交接项并标记 `not_verified`，不虚构接口或验证结果。

## 与其他场景组合

- breakpoint、侧栏、分栏、栅格仍按 `RN-02` 判断信息结构；派生 rem/fontSize 陈旧时组合 `RN-03`。
- fold 容器只有真正需要半折或折痕语义时与 `RN-06` 组合；普通展开单双栏仍按 window。
- avoid-area 与 `RN-05` 组合，并与 safe-area-context/Host inset 建唯一 owner 表。
- 包的 JS 行为与声明不一致、HAR/Codegen/peer dependency 不兼容时组合 `RN-08`；不因为“官方社区组件”跳过最小复现。

## 准入验证矩阵

- 断点：默认与非默认阈值的前一档/临界值/后一档；折→展→折；分屏和自由窗连续拖拽；window 与 component reference；最终相同宽度得到相同结果。
- 设计单位：断点切换同一轮记录 window、breakpoint、layoutScale/rem、fontSize/style 和 onLayout，证明没有只更新标签而样式陈旧。
- 显隐/Grid：动态 children、长文本和大字体；span/offset/order 边界；大 gutter；RTL；嵌套窄容器；关键操作始终可达。
- SideBar/分栏：受控 prop 更新、拖动、Overlay↔Embed、Stack↔Split、导航/选中/滚动状态连续、窄→宽→窄。
- 避让：沉浸/非沉浸、状态栏/挖孔/底部导航显隐、旋转、折展、分屏/悬浮窗；核对原生 px、adapter 输出和最终 padding，证明无双 inset。
- 生命周期：至少两个并发消费者、重复挂载卸载、前后台、热更新和路由返回；一个消费者卸载不影响另一个，监听计数回到基线。
- Fold：仅适用时验证 folded/half-folded/expanded、横竖方向、折痕单位和快速事件；组件退出后方向策略不被改变。
- 兼容性：无依赖降级路径（产品需要时）、手机基线、目标 RNOH 真机，以及 Android/iOS 行为声明（跨平台项目）。分别报告源码、类型、构建和运行证据；缺真机路径写 `not_verified`。

## 依据

- 官方社区多设备布局组件仓库。<https://gitcode.com/CPF-RN/rn_multidevice_layout_scenepkg>
- `@hadss/react_native_breakpoints` 发布物。<https://www.npmjs.com/package/@hadss/react_native_breakpoints>
- `@hadss/react_native_adaptive_layout` 发布物。<https://www.npmjs.com/package/@hadss/react_native_adaptive_layout>
- `@hadss/react_native_avoid_area` 发布物。<https://www.npmjs.com/package/@hadss/react_native_avoid_area>
- React Native `Dimensions`：foldable/window 尺寸会变化，React 组件优先使用 `useWindowDimensions()`。<https://reactnative.dev/docs/dimensions>
- HarmonyOS 沉浸式窗口：避让区域变化监听和 px→vp 使用。<https://developer.huawei.com/consumer/cn/doc/doccenter-capabilities/immersive-window-feature>
- HarmonyOS 折痕示例：折痕 Rect 转换为 vp 后参与布局。<https://developer.huawei.com/consumer/cn/doc/best-practices-V14/multi-video-app-V14>
