# 一多适配 HTML 报告

报告由 `$OM/scripts/render-report.py` 确定性生成。脚本只读取 `$OM/decisions.json` 与
`$OM/evidence/index.json`：前者提供范围、问题、实际修改和验证结果，后者提供环境、命令、
证据与执行过程。报告阶段不重新分析源码、不执行测试、不修改账本或 evidence，也不维护第二份
问题清单。相同输入重复生成时，统计、排序、结论和主体内容必须一致。

## 固定产物与命令

每个批次完成第四步后运行：

第四步的修复循环结束后即可生成报告，不要求验证全部通过；不是某一轮失败就跳过后续修复。渲染脚本自带账本与证据校验，不重复运行独立校验命令。未登记文件不用于报告，也不阻断生成。

```bash
python3 $OM/scripts/render-report.py $OM --batch-id <batchId>
```

输出 `$OM/adaptation-report-<batchId>.html`。全部批次进入 `completed/stopped` 后运行：

```bash
python3 $OM/scripts/render-report.py $OM --summary
```

输出 `$OM/adaptation-summary.html`，单批任务也必须生成。新任务不生成 Markdown 报告；已有
Markdown 只作为历史文件保留，不更新。HTML 使用 `$OM/assets/report/report-template.html`，
CSS 和已登记截图均内嵌，不依赖 CDN、网络字体、远程脚本或其他联网资源。

渲染成功后，脚本向 stdout 输出 `kind/tier/testConclusion/flowStatus/verificationState/output/counts`
JSON；`testConclusion` 仅用于写回账本，向用户展示时使用后两个状态。Agent 必须调用当前
环境提供的 HTML 预览能力交付页面；没有预览工具或调用失败时，明确说明并提供文件路径，不得只在
对话中复述结论。

## 页面内容与来源

| 区域 | 数据来源与展示规则 |
|---|---|
| 任务头部 | `task`、当前 `batch`、目标形态、报告档位和流程执行状态 |
| 指标卡 | `issues` 聚合的问题、已修改、验证项、未验证和实际修改文件去重数；整卡可点击并跳转到对应报告章节 |
| 适配概述 | 批次页面、公共依赖、风险及任务决策 |
| 本批修改 | 每个 Issue 用 `problem + rootCause` 表示修改前，用 `changeSummary + changedFiles` 表示修改后；`proposal` 只放在折叠详情中 |
| 验证矩阵 | `verificationPlan` 按 `form + checkId` 连接 `verificationResults` 和 evidence ID |
| 构建与执行 | 只汇总 L1 构建、L2 静态检查和运行态验证的最终结果；原始执行历史保留在 evidence，不在报告重复展示 |
| 未解决问题 | 本批 `failed/blocked` 的实际问题和稳定原因；不把仅缺运行证据的问题列为代码问题 |
| 待补充验证 | 按原因聚合 `not_verified` 检查项，使用数量和自然语言说明验证缺口，不展示内部 Issue ID |
| 历史问题 | `source=baseline` 的适配前问题 |
| 相关产物 | decisions、evidence，以及存在时的高保真 HTML；路由表属于内部流程输入，不在用户报告展示 |

“已修改/未修改”和“已验证/未验证”是两个独立维度。代码已修改但没有设备验证时必须显示
“已修改、未验证”，不能归为已完成或通过。`changedFiles` 必须去重后计数，禁止模型手工计数。

流程执行状态与验证状态也必须分开：批次报告成功生成表示本批流程“已完成”，不因缺少多模态或设备
证据而改成“未通过”。L1/L2 已通过且仅因用户跳过多模态而存在未验证项时，验证区显示
“基础验证通过”，并说明“未进行多模态验证（用户跳过）”；其他缺证据场景才显示“验证未完成”。
`batch.testConclusion=failed` 仍是内部聚合值，表示验证闭环没有通过，不作为页面的流程完成状态。

## 前后对比与截图

前后对比描述始终来自账本：修改前使用 `problem/rootCause`，修改后使用实际的
`changeSummary/changedFiles`，不得用尚未施工的 `proposal` 冒充完成效果。

截图只接受 `$OM/evidence/index.json` 中当前批次已登记、路径未越界且文件存在的
`type=screenshot` 产物，并按 `issueId + form + checkId` 关联为“验证截图”。报告将图片内嵌为
data URI。没有截图时完全隐藏图片区；报告阶段不得启动设备、补拍、复制工程其他截图，或把高保真
设计稿当成运行结果。现有 evidence 没有 before/after 角色，因此截图不宣称是严格的修改前后对照。
验证矩阵中的“证据”列只展示与具体 `issueId + form + checkId` 对账的 evidence ID；当前批次所有
验证项都没有此类证据时，隐藏整列，不显示空值占位。

## 结论与状态写回

当前批在报告生成前仍为 `executing/not_run`。渲染脚本必须从
`verificationPlan + verificationResults + evidence` 重新计算候选结论，不得提前读取
`batch.testConclusion` 作为输入：

- **通过**：最终基础检查通过，没有阻塞问题，所有已修改 Issue 的适用验证项均为 `passed`；
- **未通过**：存在 `failed`、应验证但 `not_verified`、基础检查失败、阻塞问题，或账本与 evidence 无法对账。

上述通过/未通过是写入 `batch.testConclusion` 的技术结论。用户可见报告不使用“最终结论：未通过”
概括整个任务，而是同时展示“流程已完成”和对应的验证状态。

输入无效、引用失效或 HTML 模板存在未替换占位符时，脚本必须失败且不得覆盖上一份有效报告。
已完成批次允许刷新，旧 `testConclusion` 不阻断重新计算。HTML 成功落盘后，Agent 才通过 `transition-batch` 将批次写为
`completed` 并把 stdout 的候选结论写入 `batch.testConclusion`。报告文件不是 evidence artifact，
不得写入 `$OM/evidence/index.json` 或触发重新测试。

## 报告档位

| 档位 | 条件 | 页面内容 |
|---|---|---|
| 精简 | 单批、≤3 页、无失败/未验证/历史阻塞 | 结论、概述、修改对比、验证矩阵和产物 |
| 标准 | 单批但不满足精简条件；或多批任务的单个批次 | 完整批次报告 |
| 完整 | 最终汇总报告 | 任务指标、全部批次卡片、总体结论、未完成项和批次报告链接 |

档位由脚本自动判断，不要求用户选择。存在 `deferredRegressions` 时，标准报告增加“跨批次潜在影响”，
列出页面、所属批次、原因和建议检查项，并明确要求用户验证；该章节不改变当前批次结论。

## 批次闭环与最终汇总

批次报告是批次闭环的一部分：当前批施工和验证结束后立即生成 HTML、写回批次终态并展示给用户。
只有用户在看到报告后明确同意继续，才能进入下一批；禁止先完成所有批次施工，再统一验证或补报告。

全部批次进入终态后生成最终汇总。汇总报告只做汇总聚合，不重跑测试、不修改批次结论；包括任务
状态、批次执行状态与链接、页面/问题/验证统计、累计实际文件数、未完成批次和遗留问题。任一批次
未通过、停止或没有有效批次报告时，整体结论均为未通过。
