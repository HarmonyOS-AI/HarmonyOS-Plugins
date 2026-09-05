<!--
Merged from flutter-pura-x-max-ux-20260731/references/purax/README.md.
Role: directory guide for the purax deep-dive set; see note above for standing rules.
-->
# PuraX 折展参考索引（自 flutter-purax-adaptation 并入）

主入口仍为上级 [SKILL.md].../SKILL.md) 的 **PX-01～06**。本目录为详读材料。

| 文件 | 对应 | 内容 |
| --- | --- | --- |
| [official_adaptation_guide.md].official_adaptation_guide.md) | 总览 | 官方/工程适配总览、hadss 引入 |
| [fold_status_detection.md].fold_status_detection.md) | 监听 | FoldStatus / AvoidArea |
| [hover_state_interaction.md].hover_state_interaction.md) | PX-01 | 悬停分屏、FolderStack |
| [crease_avoidance.md].crease_avoidance.md) | PX-02 | 折痕/铰链避让 |
| [breakpoint_layout.md].breakpoint_layout.md) | PX-03 | 断点、Grid、NavigationSplit |
| [fold_continuity.md].fold_continuity.md) | PX-04 | 开合连续性（≈ UX-15） |
| [bug_fix_cases.md].bug_fix_cases.md) | PX-05 | 折展问题修复清单 |
| [scbcompatible_letterbox.md].scbcompatible_letterbox.md) | PX-06 | SCBCompatible 信箱（≈ UX-11） |
| [scenario_development_cases.md].scenario_development_cases.md) | DEV | 场景开发案例 |

示例 Dart：`../../assets/`（`folder_stack_example.dart`、`navigation_split_example.dart`、`breakpoint_listener.dart`）。  
用例 JSON：`../../test-cases/`。
