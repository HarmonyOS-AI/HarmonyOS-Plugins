# 输出契约

输出 `primary_scene`、必要的 `secondary_scenes`、`implementation_track`、有证据支撑的根因、代码与依赖落点、生命周期回收点、验证矩阵和残余风险。需求阶段补充设备范围与能力边界；修复阶段补充回归观察项；验证阶段给出截图、日志或测试结果。

## 阶段标签与字段

| 阶段 | 标签 | 关注点 |
| --- | --- | --- |
| 需求分析设计 | `REQ` | 设备形态、折展状态、断点策略、显示职责 |
| 开发 | `DEV` | 状态监听、分屏布局、断点适配、铰链规避、连续性、生命周期回收 |
| 问题修复 | `FIX` | 折展偏差、断点失配、状态不同步、铰链跨越、连续性断档 |
| 功能验证 | `VAL` | 断点证据、方向证据、铰链避让截图、连续性行为回归 |

各阶段补充字段：

- 路由字段（所有阶段）：`active_phases`、`primary_phase`、`primary_scene`、`secondary_scenes`、`resources_used`
- `REQ`：`device_constraints`、`capability_boundary`、`acceptance_focus`
- `DEV`：`code_touchpoints`、`reuse_resources`、`implementation_notes`、`integration_risks`
- `FIX`：`problem_profile`、`root_cause_hypothesis`、`fix_plan`、`regression_watchlist`
- `VAL`：`verification_matrix`、`evidence_requirements`、`pass_criteria`、`residual_risks`

工程级硬约束见 [engineering-rules.md](engineering-rules.md)。
