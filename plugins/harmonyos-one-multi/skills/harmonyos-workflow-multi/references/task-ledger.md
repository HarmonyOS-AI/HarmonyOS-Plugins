# 一多适配任务与问题账本

`$OM/decisions.json` 是一多适配任务状态与结论的事实源，保持可读、可审查。截图、日志、命令、环境、归因和修复过程统一写入 `$OM/evidence/index.json` 及其引用的文件，避免把大段执行信息重复写入账本。

## 顶层结构

首次安装由 `scripts/install-to-project.py` 创建 `task=null` 的 schema v3 空账本。新任务在路由图和
批次计划就绪后，默认通过 `task-ledger.py bootstrap` 一次性写入 task、decisions、pages 和 batches；
命令先在内存中完成 Schema、路径、批次引用和 route-map 校验，成功后才写账本及与 `taskId` 对齐的
空 `$OM/evidence/index.json`。不要先用 `init` 写入指向尚不存在批次的 `currentBatch`。`init` 仅保留
给不具备完整计划的低层增量流程使用。

最终落盘结构示例：

```json
{
  "schemaVersion": 3,
  "task": {
    "taskId": "one-multi-20260802-001",
    "scope": ["entry/src/main/ets/pages/order/"],
    "targetForms": ["tablet", "foldable-expanded"],
    "confirmationMode": "batch",
    "routeMap": "output/route-map.json",
    "status": "planning",
    "currentBatch": "B01"
  },
  "decisions": [],
  "pages": {
    "entry/src/main/ets/pages/order/Index.ets": {
      "type": "page",
      "module": "entry",
      "dependencies": [],
      "batchId": "B01",
      "missingFromScan": false
    }
  },
  "batches": [{
    "batchId": "B01",
    "pages": ["entry/src/main/ets/pages/order/Index.ets"],
    "dependencies": [],
    "predecessors": [],
    "domains": ["size-layout"],
    "risk": "low",
    "status": "pending",
    "specConfirmed": false,
    "hifiRequired": false,
    "testConclusion": "not_run"
  }],
  "issues": []
}
```

顶层对象职责如下：

| 对象 | 职责 |
|---|---|
| `task` | 记录本次范围、目标形态、确认模式、路由图、整体状态和当前批次 |
| `decisions` | 保存用户确认与无法交互时的假设，不承担施工状态 |
| `pages` | 保存页面发现结果、类型、模块、公共依赖和所属批次 |
| `batches` | 保存批次范围、高保真要求、依赖、顺序、风险和执行状态 |
| `issues` | 保存问题清单型 SPEC、施工状态和精简验证结论 |

证据索引独立保存为 `$OM/evidence/index.json`。账本不保存 evidence 元数据、证据 ID 汇总、执行时间、命令输出、截图路径、归因过程或轮次记录。

`task.confirmationMode` 只取 `batch / aggregate`，在第一步批次计划展示后由用户选择：`batch` 表示第二步先生成当前批详细 SPEC 及要求的高保真，`aggregate` 表示第二步先生成全部批次详细 SPEC 和所有要求的批次高保真，再统一确认。它只控制方案生成和确认时机，不取消批次间的用户继续确认；两种模式都必须按依赖顺序完成“当前批施工 → 验证 → 批次报告 → 用户明确同意继续”后再开始下一批。单批任务使用 `batch`，无需询问模式。

`task.targetForms` 必须反映本次实际设备范围。用户只说“一多适配”而未限定设备时，默认写入 `phone / foldable / tablet`；用户明确只要求其中一种或两种时，只写明确范围，不自动追加其他设备。模块安装能力再按 `../harmonyos-ui-multi/references/module-device-types.md` 映射，不能把 `targetForms` 直接等同于固定的 `deviceTypes` 数组。

## 决策与路由图

`decisions` 只保存会影响后续页面或批次的范围、设备解释和结构选择。普通 SPEC 确认只更新
`batches[].specConfirmed`；仅当确认内容形成可复用选择时，才写入稳定 `decisionId`、`scope`、
`summary`、`by=user|assumed`、`reason`、`conflictsWith` 和 `createdAt`。

所有新计划都先按 `$OM/references/route-map.md` 生成 `$OM/output/route-map.json`。符合局部分析路径条件时由 AI 生成局部路径，只覆盖本次目标对应页面的可达路径；工程扫描路径无论最终生成几个批次，都运行一次
`project-scan.py`，再核实候选页面和动态边并生成最终 JSON。`task.routeMap` 保存相对 `$OM` 的路径，`put-batch` 必须通过
`--route-map` 校验 JSON 结构、步骤及批次覆盖。已经由用户提供并冻结验证计划的恢复任务可复用工程内既有
路由输入，不重做范围、批次或 `verificationPlan`。

安装到目标工程时，路由文件固定放在 `<工程根>/.onemulti/output/route-map.json`，账本固定保存
`"routeMap": "output/route-map.json"`。`put-batch --route-map` 必须指向该文件；校验器按
`route-map.md` 检查 schemaVersion、路径、步骤、目标页面和批次覆盖。

## 批次和问题

批次至少记录 `batchId`、`pages`、`dependencies`、`risk`、`status` 和 `specConfirmed`。公共组件批必须排在依赖页面之前，不能把尚未确认的后续批次作为当前批的前置条件。

`batches[].hifiRequired` 是布尔值，默认 `false`；用户要求或选择高保真时，将对应批次设为 `true`，全部需要则全部设为 `true`。它只记录交付要求，不代表已生成或已确认；任务级不重复保存。生成与设备覆盖按 [高保真流程契约](hifi-delivery.md)，设备范围复用 `task.targetForms`。可用 `transition-batch` 单独更新 `{"batch":{"hifiRequired":true}}`，无需改变批次状态。

每个问题至少包含：

```json
{
  "issueId": "B01-UI-003",
  "batchId": "B01",
  "page": "OrderPage.ets",
  "component": "OrderSummary",
  "domain": "size-layout",
  "targetForms": ["tablet-landscape"],
  "problem": "窗口达到 md 后摘要区仍为单列，右侧出现大面积空白",
  "source": "task_analysis",
  "rootCause": "根容器固定宽度且没有断点分栏",
  "proposal": "复用现有 GridRow，在 md 及以上切换为 8/4 分栏",
  "plannedFiles": ["OrderPage.ets"],
  "verificationPlan": [
    {
      "form": "tablet-landscape",
      "checkId": "layout-md-split",
      "routeId": "R-B01-ORDER-SUMMARY",
      "check": "md+ 摘要区为 8/4 分栏且无截断"
    }
  ],
  "changeStatus": "modified",
  "verificationResults": [
    {
      "form": "tablet-landscape",
      "checkId": "layout-md-split",
      "status": "passed",
      "reason": null
    }
  ],
  "changedFiles": ["OrderPage.ets"],
  "changeSummary": "摘要区在 md+ 使用右侧 GridCol",
  "notChangedReason": null,
  "introducedByBatch": null
}
```

Issue 只维护一组施工状态：

| 状态 | 允许值 | 说明 |
|---|---|---|
| `changeStatus` | `pending / modified / not_modified / blocked` | 是否实际修改及原因 |

`source` 只取 `baseline / task_analysis / execution_found / batch_regression`。`introducedByBatch` 只在能明确归因到某批修改时填写；它为空不代表历史问题，历史问题必须由 `source=baseline` 判断。

`verificationPlan` 是本阶段验证项的唯一来源，每项使用稳定的 `form + checkId` 唯一标识，以 `routeId` 引用 `route-map.json` 中已存在且属于同批次的路径，并保存可读的 `check`。同一形态需要验证布局、交互和状态连续性时必须拆成多个计划项，不能只列一个形态名称。设备矩阵、通用回归建议和报告模板不得新增计划项；执行时不得改写已确认的 `form + checkId + routeId + check`。

`deferredRegressions` 记录第四步发现的跨批次潜在影响。每项只含 `page / batchId / reason / suggestedCheck`；目标页面必须属于其他批次。该字段不生成验证计划、结果或证据，不参与批次结论。

整个任务只选择一台典型设备并在各批次复用。若 `verificationPlan` 包含直板机基线，而选定设备为
折叠屏，可在同一设备的折叠态执行该计划项；结果仍按原计划键写回，实际设备、折叠态及判定方法
只记录到 evidence，不能把计划描述改成“折叠屏基线”。

`verificationResults` 按“问题 × 形态 × 检查项”保存最终结论，每项必须且只能包含 `form`、`checkId`、`status`、`reason`。`form + checkId` 必须命中一个计划项；可读检查内容只保留在 `verificationPlan.check`，不复制到结果。`passed` 的 `reason` 为 `null`，`failed/not_verified/not_applicable` 必须填写简短、稳定的原因码或一句话原因。时间、证据引用和判断详情从 evidence 索引按 `issueId + form + checkId` 查询。

问题级验证结论不落盘，读取时由完整计划与精简结果聚合。`not_modified` 且没有验证结果时直接派生为不适用；其他问题存在 `failed` 则为失败，任一计划项缺少结果或存在 `not_verified` 则为未验证，全部适用计划项通过则为通过，全部计划项不适用则为不适用。额外、重复、字段超集或无法匹配计划的结果均使账本校验失败。

`not_modified` 或 `blocked` 必须填写 `notChangedReason`；`failed` 或 `not_verified` 必须说明失败/缺失原因。能明确归因到本批修改且可在确认范围内修复的问题继续验证修复循环；达到停止条件后，遗留问题再转人工，不因首轮失败直接结束。

## 任务、批次与证据状态

| 字段和值 | 含义 |
|---|---|
| `task.status`: `planning / executing / completed` | 由脚本根据全部批次状态自动聚合，Agent 不直接写入 |
| `batch.status=pending` | 批次已建立，正在生成 SPEC 或等待整批确认 |
| `batch.status=executing` | 整批已确认，正在施工、验证或生成报告 |
| `batch.status=completed` | 本批报告已生成，批次正常结束 |
| `batch.status=stopped` | 本批被跳过、阻塞或提前终止 |
| `batch.testConclusion`: `not_run / passed / failed` | 与执行进度分开保存的测试结论 |

执行状态和测试结论分开：批次执行完但存在失败项时，`status=completed`、`testConclusion=failed`。任务测试结论不落盘，需要时由全部批次实时聚合。

`task.status` 的聚合规则只有三条：没有批次或全部批次为 `pending` 时是 `planning`；只要任务已开始且仍有批次未终止，就是 `executing`；全部批次均为 `completed/stopped` 时是 `completed`。这里的 `completed` 仅表示任务流程已经收口，不代表测试通过；被停止的范围和失败结论仍从批次及报告读取。`bootstrap`、`put-batch` 和 `transition-batch` 会自动刷新该字段，`set-task` 不接受 `status`。

`$OM/evidence/index.json` 使用 verification 文档定义的 schema v3。每个条目至少包含稳定 `evidenceId`、`type`、`round`、`links`，并选择结构化 `data` 或直接 `path`。L3 evidence 的 `links` 必须包含 `issueId + form + checkId`。`passed` 需要与检查内容相符的可靠 evidence，可使用命令、日志、截图或 `component_tree`，不强制截图或截图与组件树配对。报告脚本检查关联键和已登记文件存在性；未登记文件不参与结论。

同一执行事实只保存一次：环境和命令结果写入索引条目，轮次过程写入索引；报告只做汇总，不复制完整日志或逐步操作记录。

聚合规则：

- 问题闭环：`modified + passed`，或填写 `notChangedReason` 后由账本派生的 `not_modified + not_applicable`；`not_modified` 不生成验证结果和证据；
- 页面完成：该页全部适用问题闭环，且目标形态覆盖完成；
- 批次完成：问题都进入终态；只有最终构建通过且无 `failed/not_verified/blocked` 必处理问题时，测试结论才通过；
- 任务完成：全部计划批次进入终态；任一批次测试未通过，任务测试结论未通过。

`task-ledger.py validate` 只校验 Schema、字段取值、页面/批次/问题引用和路由关联；`validate-state.py`
用于按需排查证据索引、计划结果对应关系和已登记文件。两者不判断当前应该处于哪个流程阶段，
也不阻止 Agent 按本 Skill 更新状态。批次页面仍必须回指同一 `batchId`，问题页面必须属于问题批次，
每个验证路由必须实际到达问题的 `page` 或 `affectedPages`；恰好命中页面账本的
`affectedPages/plannedFiles/changedFiles` 也必须绑定该批次。`pending → executing → completed`、
终止时进入 `stopped` 等顺序属于 Skill 流程规则，由 Agent 按五步执行。

批次状态与确认由 Agent 按用户意图维护；验证入口、证据写回、补充回归和报告刷新不因 `completed` 或未处于 `executing` 而拒绝执行。

## 页面记录

`pages` 只保存页面发现与批次归属事实，不保存也不展示独立的页面执行状态。需要按页面展示进度或生成报告时，
直接汇总该页面关联 `issues` 的确认、施工和验证结果，不再生成或写回页面状态标签。

页面重扫时增量合并：新增页直接追加；消失页使用 `missingFromScan=true` 和 `missingReason` 标记待确认；
源码摘要变化后，相关问题的旧验证结论失效。

## 写入顺序与恢复

1. 确认范围并完成基线、页面和路由分析后，生成 `$OM/output/route-map.json`，再只根据页面、公共依赖、顺序和风险生成 `batches`，通过 `bootstrap` 一次性写入 task、决策、页面和批次；本步不生成 `issues` 或具体修法。
2. 展示批次计划；多批任务由用户选择先生成第一批详细 SPEC，或先生成全部批次详细 SPEC，并写入 `task.confirmationMode`。
3. 进入第二步后，对选定批次进行具体问题分析，一次性写入该批 `issues`；该问题清单就是 SPEC。读取并按用户要求更新 `hifiRequired`，完成本次确认范围内要求的 HTML 后一并交付；确认后更新 `batch.specConfirmed`，当前批同时进入 `executing`。
4. 每组修改后立即写 `changeStatus`、实际文件和摘要；施工中发现的新问题可继续使用 `put-issues` 追加到当前批次，再按其实际处理结果回写。
5. 每轮验证后用一次 `record-batch` 原子更新 `$OM/evidence/index.json` 和账本中的逐项结果；轮次产物按批次位于 `evidence/<batchId>/round-N/`。
6. 修复循环结束后写回最终结果和遗留原因，失败或未验证不阻断收尾；不创建或搬运临时 evidence 会话文件。
7. 通过 `render-report.py` 校验输入并生成或刷新 `$OM/adaptation-report-<batchId>.html`；生成成功后才将批次写为 `completed` 并展示 HTML 预览。只有用户明确同意继续，才切换 `task.currentBatch`。
8. 全部批次进入 `completed/stopped` 后，从最新账本生成 `$OM/adaptation-summary.html`，即使只有一个批次也生成；完成后保留账本、证据和报告，供后续查询或继续处理。

两次写入均采用“同目录临时文件 → JSON 解析与关联校验 → 原子替换”：先完成 evidence 索引，再写账本结论。任一步失败都保留上一个有效版本及临时文件。恢复任务时从 `task.currentBatch`、`batch.status`、`changeStatus` 和 evidence 索引继续，不重复施工已通过项。

写入命令和报告脚本自带校验，无需每次额外执行；需要排查数据问题时可运行：

```bash
python3 $OM/scripts/validate-state.py .               # 排查账本、索引及已登记文件
```

校验器检查 Schema、字段取值、计划与结果关联、证据引用和文件存在性，不要求测试全部通过。Agent 不直接
拼接局部 JSON 后覆盖整个文件；所有写入采用同目录临时文件，经写入命令校验后再原子替换。数据写入失败时
保留原文件并停止本次写入。

## 接续与新任务

任务完成后的后续请求由 Agent 结合原范围、Issue 和用户意图判断，不因 `completed` 拒绝继续：

- **延续任务**：保留原产物，用 `set-task` 定位相关 `currentBatch`，通过 `transition-batch` 将待处理批次改为 `executing`、`testConclusion=not_run`，脚本同步刷新 `task.status`。方案需调整时改为 `pending`、`specConfirmed=false`，回到第二步确认。仅补测则保留 SPEC 与施工结果，从第四步 `preflight.py begin` 重新检查当前代码证据、模型和设备；结束后刷新批次及汇总报告。
- **新任务**：先告知将清理旧任务产物，再执行下面的 `reset`；然后重新扫描、生成路由与计划，用 `bootstrap` 创建新账本。不要先生成新产物再清理，也不要回退上次已修改的业务代码。
- 仅查询不修改状态；意图不明确时先询问，不能猜测后删除。

```bash
python3 $OM/scripts/task-ledger.py reset $OM/decisions.json
```

`reset` 仅接受工程内的 `.onemulti/decisions.json`：删除该目录内的账本、证据、报告、输出和临时文件，保留 `SKILL.md`、`scripts/`、`references/`、`assets/` 及 Git 元数据；不清理工程其他目录，不创建备份，删除不可恢复。

## 账本命令

所有常规账本更新使用 `$OM/scripts/task-ledger.py`；复杂输入临时写入 `$OM/evidence/tmp/` 并通过
`--input` 传入，也可用 `--input -` 从标准输入读取。`$OM/output/` 只存正式产物，禁止保存
`issues*.json`、`issue-*.json` 等账本副本或状态补丁；问题输入成功写入后立即删除：

新任务优先只执行一次标准初始化：

```bash
python3 $OM/scripts/task-ledger.py bootstrap $OM/decisions.json \
  --input bootstrap.json --route-map $OM/output/route-map.json
```

恢复或增量更新既有任务时使用下列命令：

```bash
python3 $OM/scripts/task-ledger.py validate $OM/decisions.json
python3 $OM/scripts/task-ledger.py put-decision $OM/decisions.json --input decision.json
python3 $OM/scripts/task-ledger.py merge-pages $OM/decisions.json --input page-inventory.json --full-scan
python3 $OM/scripts/task-ledger.py put-batch $OM/decisions.json --input batches.json \
  --route-map $OM/output/route-map.json
python3 $OM/scripts/task-ledger.py put-issues $OM/decisions.json --batch-id B01 \
  --input $OM/evidence/tmp/issues.json
python3 $OM/scripts/task-ledger.py transition-issue $OM/decisions.json B01-UI-001 \
  --input $OM/evidence/tmp/issue-patch.json
python3 $OM/scripts/task-ledger.py add-deferred-regression $OM/decisions.json B01-UI-001 \
  --input $OM/evidence/tmp/deferred-regression.json
python3 $OM/scripts/task-ledger.py put-verification $OM/decisions.json B01-UI-001 --input result.json
```

每个接受 `--input` 的子命令都在 `--help` 末尾提供“可复制 JSON 示例”，包括完整包装键、必填字段和
状态更新主路径。先复制示例再替换业务值，不再通过搜索脚本源码猜测输入结构。

`put-verification` 只接受 `form`、`checkId`、`status`、`reason` 四字段。第四步由 `record-batch`
事务更新 evidence 和这些精简结果；证据条目始终写入 `$OM/evidence/index.json`，不得通过账本命令
塞回 `decisions.json`。

## 非交互模式

无法向用户确认时，只处理明确范围，必要选择通过 `put-decision` 写入 `decisions` 且 `by=assumed`。结构方案可以采用影响最小、可逆且沿用现有工程的选项，但不能把 `assumed` 写成 `user`。无法完成真实形态验证时，问题保持 `not_verified`，任务结论为未通过。当前批报告生成后如果无法获取用户明确的继续确认，必须停止，不得通过 `by=assumed`、汇总 SPEC 确认或任务自动化要求替代批次间确认。

## 可选质量扩展

完整质量评估使用 `task.quality`（standardVersion/targetGrade/enhancements）和 `batches[].qualityChecks`（完整页面×形态×标准计划），详细字段与专用原子写入命令见 [质量契约](quality-levels.md)。不添加虚假 Issue，也不把运行结果和证据元数据复制进账本。schema v3 旧数据保持有效，无扩展时为未评估；变更目标需显式重编计划，历史证据不自动迁移。
