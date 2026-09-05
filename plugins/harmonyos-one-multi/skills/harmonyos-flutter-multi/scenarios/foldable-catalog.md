# 折叠屏场景目录

| ID | 场景 | 强制联动 | 详读（references/purax/） |
| --- | --- | --- | --- |
| PX-01 | 悬停态展示区/操作区分屏 | PX-02 | [hover_state_interaction.md](../references/purax/hover_state_interaction.md)、[folder_stack_example → ../examples/hadss/folder_stack.dart](../examples/hadss/folder_stack.dart) |
| PX-02 | 铰链/折痕区域避让 | 状态与区域变化监听 | [crease_avoidance.md](../references/purax/crease_avoidance.md) |
| PX-03 | 断点响应式、导航和网格 | 统一断点源 | [breakpoint_layout.md](../references/purax/breakpoint_layout.md)、[navigation_split_example → ../examples/hadss/navigation_split.dart](../examples/hadss/navigation_split.dart) |
| PX-04 | 开合连续性 | State、滚动、输入、媒体恢复 | [fold_continuity.md](../references/purax/fold_continuity.md) |
| PX-05 | 既有折展问题修复 | 监听→几何→布局→回收→回归 | [bug_fix_cases.md](../references/purax/bug_fix_cases.md) |
| PX-06 | 系统兼容信箱 | UX-11、OHOS 平台专项 | [scbcompatible_letterbox.md](../references/purax/scbcompatible_letterbox.md)、[../ohos-platform/scbcompatible-letterbox.md](../ohos-platform/scbcompatible-letterbox.md) |

统一前置入口：折叠状态与断点检测读 [fold_status_detection.md](../references/purax/fold_status_detection.md)；官方指导与端到端案例读 [official_adaptation_guide.md](../references/purax/official_adaptation_guide.md)、[scenario_development_cases.md](../references/purax/scenario_development_cases.md)。

方向决策优先级：业务需求 > 系统折叠信号 > 几何推算。折展只改变布局职责，不改写业务状态机。关键内容和交互不得落在折痕区域。

## 意图信号（命中判定）

- PX-01：悬停态、halfFolded、上下分屏、上展示下操作、FolderStack、FoldSplitContainer、内外屏比例、外屏识别、窗口模式、沉浸式避让。
- PX-02：折痕、铰链、遮挡、avoid area、AvoidAreaApi、内容被劈开、控制栏被截断、内容跨铰链。
- PX-03：响应式、断点、BreakpointManager、栅格、GridRow/GridCol、分栏、NavigationSplit、SideBarContainer、单栏双栏、硬编码列数。
- PX-04：折叠后状态丢失、操作步骤增加、滚动偏移、输入丢失、图片模糊、播放进度不一致。
- PX-05：悬停态错乱、断点适配偏差、铰链跨越、连续性断档、生命周期回收、直板机混淆。

## 场景决策树

1. 涉及折叠状态检测（FoldStatus、AvoidAreaApi、FolderStack、FoldSplitContainer）→ 读 fold_status_detection.md，继续 2。
2. 涉及悬停态分屏或多形态适配 → 命中 PX-01，自动联动 PX-02，继续 3。
3. 涉及铰链/折痕避让 → 命中 PX-02（已被 2 联动则跳过），继续 4。
4. 涉及断点响应式适配 → 命中 PX-03，继续 5。
5. 涉及开合连续性 → 命中 PX-04，继续 6。
6. 需要折展问题修复 → 命中 PX-05；否则结束。

修复顺序统一为：监听入口 → 几何/状态 → 布局/交互 → 生命周期回收 → 回归验证。视频进度折展恢复用双触发（onPrepared + 定时器兜底）；图片按新窗口尺寸重载。
