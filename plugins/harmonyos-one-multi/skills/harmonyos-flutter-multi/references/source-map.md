# 来源迁移映射

| 来源 | 新位置 |
| --- | --- |
| `flutter-pura-x-max-ux-20260731/SKILL.md`、`patterns.md`、`checklist.md` | `scenarios/`、`flutter-native/ux-fix-patterns.md`、`validation/` |
| `flutter-purax-adaptation` 的 PX-01～PX-05、阶段字段 | `scenarios/foldable-catalog.md`、`core/output-contract.md` |
| 两个 Pura X skill 重复的 8 份 references | 去重后按能力拆入 `flutter-native/` 与 `hadss/`，不再整篇双方案混写 |
| `ohos-multi-device-adaptation/SKILL.md`、`scenes.md` | `core/`、`scenarios/multi-device-catalog.md` 与各实现目录 |
| 架构、生命周期、SplitView、Channel、LTPO | `ohos-platform/`，保留专项文档 |
| 原 Pura X 示例与测试 | `examples/hadss/`、`test-cases/` |

SCBCompatible 详册保留在 `ohos-platform/`。DPI 原文同时混有布局策略和框架扩展，已拆为通用断点、两条布局路线和平台 DPI 文档。

## 二次合并（源 skill 深水区详册回填）

路由层摘要之外的原文详册按"深读层"回填到 `references/` 与 `validation/`，文首 HTML 注释记录来源与链接映射：

| 来源 skill | 新位置 |
| --- | --- |
| `flutter-pura-x-max-ux-20260731/patterns.md` | `references/pura-x-patterns.md` |
| `flutter-purax-adaptation/references/` 8 篇 | `references/purax/`（含 pura-x-max-ux 侧 README） |
| `flutter-pura-x-max-ux-20260731/说明.md` | `references/pura-x-guide.md` |
| `ohos-multi-device-adaptation/scenes.md` | `references/scenes.md` |
| `ohos-multi-device-adaptation/references/dpi-guide.md` | `references/dpi-guide.md` |
| `flutter-pura-x-max-ux-20260731/checklist.md` | `validation/ux-px-checklist.md` |
| `flutter-pura-x-max-ux-20260731/coverage.md` | `validation/coverage.md` |

未回填项（已确认等价或本 skill 版本更新）：两侧 `test-cases/`（本 skill 已按互斥路线语义改写）、`assets/` 与 `examples/hadss/`（哈希一致）、SCBCompatible 双版本（`ohos-platform/` 为合并统一版）、其余 `ohos-multi-device-adaptation/references/`（与 `ohos-platform/` 同源同大小）。
