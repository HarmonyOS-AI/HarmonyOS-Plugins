# 安全区与软键盘避让

## 安全区所有权

先建立每个方向的所有权表：

| 方向 | 系统 inset | ArkUI Host 已应用 | RN provider 值 | RN 页面应用 | 最终 owner |
| --- | ---: | ---: | ---: | ---: | --- |
| top |  |  |  |  |  |
| right |  |  |  |  |  |
| bottom |  |  |  |  |  |
| left |  |  |  |  |  |

如果 Host 已把 RNSurface 限制在安全区，RN 通常不再对同方向应用系统 inset；如果 Surface 全屏延伸，则由 RN provider/页面或 Host 内层中的一个 owner 消费。背景可以铺满窗口，关键内容与交互不能被系统区域遮挡。

- SafeAreaProvider 覆盖需要 inset 的导航与 Portal 根。
- `initialWindowMetrics` 只改善首帧，不能替代后续动态更新。
- 多 RN root/RNSurface 分别确认 metrics 来源和更新 owner。
- 底部栏、Sheet、Modal 和页面不能重复消费同一 bottom inset。
- 安全区库的 Harmony 实现、Autolinking 与更新行为以锁定版本为准。

## 键盘策略

每个页面只选一个主策略：

| 页面 | 常见主策略 | 关键验收 |
| --- | --- | --- |
| 普通表单 | window resize + 可滚动内容 | 当前输入框和提交区可达 |
| 底部 Sheet | Sheet 自己响应键盘 | 页面背景不再二次上抬 |
| 聊天页 | 消息区收缩 + composer 跟随 | 列表锚点稳定 |
| 全屏编辑 | KeyboardAvoidingView 或 Host 策略之一 | header/offset 动态正确 |

不要固定所有页面使用同一个 `behavior`；先记录锁定版本和 Host 的实际窗口策略。观测 keyboard show/hide、window height、TextInput bounds、键盘顶部以及页面 transform/padding。如果页面位移大于窗口高度变化，通常存在重复避让。

## 焦点与身份

- 保持 TextInput React identity；断点只重排容器，不给输入框或祖先使用 width/breakpoint key。
- 让内容可滚动，避免焦点进入不可滚动的固定高度区域。
- 自定义滚动不要与系统自动滚入可视区竞争；先证明默认路径不足。
- 键盘关闭、切换焦点、旋转和分屏后不累计 padding/transform。
- 某些 RNOH 版本可能存在 KeyboardAvoidingView 与 TextInput 自动避让叠加；从锁定版本 release/FAQ/实现和真机确认，不把历史问题永久化。
- 所有权、window 和页面 padding 已正确但 SafeArea/KAV 仍异常时，读取 `known-rnoh-layout-issues.md` 做版本分流；历史修复只能作为检索入口，不能代替当前版本最小复现。

## 验证

- 有/无系统 inset、四个方向特殊区域、沉浸背景与关键操作。
- 页面顶部/中部/底部、Modal/Sheet、长表单中的输入框。
- 键盘显示/隐藏、连续切换焦点、旋转、折展、分屏、前后台。
- RN Surface bounds、provider inset、页面 padding 和键盘位移能解释最终位置。
- 手机基线无多余 padding；没有真实键盘与目标窗口证据时标记 `not_verified`。
