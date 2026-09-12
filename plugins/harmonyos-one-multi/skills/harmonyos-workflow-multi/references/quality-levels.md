# 适配质量分层与证据契约

## 语义与范围

本插件定义三级适配质量体系，标准版本为 `one-multi-1`。本文件统一维护等级含义、适用范围、逐级达标规则与证据契约；各领域只维护自身的验收要点。

| 等级 | 体验目标 |
|---|---|
| 基础可用 `ready` | 在目标形态下可完成核心任务，窗口和形态变化后保持业务状态。 |
| 自适应优化 `optimized` | 在基础可用之上，使布局、导航和交互适合当前可用空间及输入方式。 |
| 场景增强 `differentiated` | 在自适应优化之上，利用设备能力改善明确的业务场景。 |

等级逐级满足，高级能力不能抵消基础缺陷。质量等级独立于验证手段 L1/L2/L3 和报告版式 `tier`。实现方式、尺寸阈值与运行行为按领域知识和当前工程核实。

完整一多适配未指定等级时，建议 optimized，并在本次范围/SPEC 中说明；用户要求局部修复或只分析时不自动配置评级、不安装运行目录。明确要求基础适配时选择 ready；明确选择增强体验才配置 differentiated。目标等级不代替具体结构方案确认，不因升档强制分栏、迁移框架或新增依赖。

本版评级支持 phone、tablet、foldable、foldable-expanded、foldable-folded。使用任务的实际目标形态，不自动扩展范围。PC/2in1 等超出范围应说明不支持。报告限定到登记的页面和形态，局部结论不能外推全应用。

## 标准目录与领域责任

可执行标准 ID、等级和适用性以 `scripts/onemulti/quality.py` 的 `CATALOG` 为准，不由 Agent 自行增删门槛。workflow 只保存跨框架的预期体验；根因、API 和修法按各领域的质量验收文件（`quality-acceptance.md`） 与原有知识路由提供。

| 等级 | 标准与计划内容 |
|---|---|
| ready | CORE-01 核心流程可用；STATE-01 形态变化状态连续；INPUT-01 输入/避让/基础外设；MEDIA-01 媒体或相机正确性 |
| optimized | 包含 ready；LAYOUT-01 布局重排；NAV-01 导航语义；OVERLAY-01 弹层；ACCESS-01 字体/焦点/适用键鼠体验 |
| differentiated | 包含前两级；按选择的专项加入 FOLD-01、CAMERA-01、DRAG-01、STYLUS-01 |

每个标准为 **页面 × 目标形态** 生成一项，`scenario` 必须展开该项的适用测试条件和预期结果：

- CORE：从登记路由进入，执行页面核心业务路径，覆盖正常、空态或错误态中与任务有关的状态。
- STATE：先输入/选择/滚动/播放，再窄→宽→窄、旋转或折→展→折，并执行至少一个适用的组合变化。记录变化前后业务状态，不用两张无交互截图证明连续性。
- LAYOUT/OVERLAY：窗口宽高、断点两侧、宽短窗口、键盘和嵌套父约束；说明为何增列、挪移、分栏或限宽符合内容语义。
- INPUT/ACCESS：分别检查基础输入及字体、可见焦点、核心键鼠操作；不支持的外设子项说明能力原因，不能把整个 ACCESS 标准排除。
- MEDIA 与增强专项：按领域矩阵列出实际输出、生命周期或姿态组合；需要真实硬件语义的检查不能由普通窗口缩放代替。

同一检查包含多个子场景时，所有适用子场景通过才记 passed；任何子场景失败记 failed，剩余缺证据记 not_verified。观察说明与日志/轨迹应逐项对应。已正常的能力同样进入质量计划，不创建虚假 Issue；发现缺口时关联现有 Issue 或在已授权范围内新增真实 Issue。

## 账本与命令

保留账本 schemaVersion=3，通过可选 `task.quality` 和 `batches[].qualityChecks` 扩展；旧账本无配置时为未评估。质量扩展使用独立 standardVersion。更新标准必须显式迁移、重新编制并验证，不能把旧通过结果自动升级。

第一步初始化任务后配置目标（命令不构建、不启动设备）：

```bash
python3 $OM/scripts/quality-assessment.py configure $OM --target optimized
# 只有明确选择相应业务增强时：
python3 $OM/scripts/quality-assessment.py configure $OM --target differentiated --enhancement fold-posture
```

configure 在目标变化时清除旧质量计划并重置相关批次的 SPEC 确认，保留历史证据；相同目标重复执行不改变计划。接续任务复用原配置，仅目标变化时重配。账本保存的配置为：

```json
{"standardVersion":"one-multi-1","targetGrade":"optimized","enhancements":[]}
```

第二步生成完整矩阵，再由领域知识补全实际路由、测试场景与适用性，纳入同一次批次 SPEC 确认：

```bash
python3 $OM/scripts/quality-assessment.py template $OM --batch-id B01
python3 $OM/scripts/quality-assessment.py plan $OM --batch-id B01 --input quality-plan.json
```

template 只向 stdout 输出待填写输入，不安装或写入占位计划。plan 的输入为 `{"qualityChecks":[...]}`，每项保留生成的 checkId/criterionId/page/form，填写 routeId/scenario/applicability/reason。不删除检查项；无媒体业务等条件项可写 `applicability=not_applicable` 和具体 reason。CORE、STATE、LAYOUT、ACCESS 不允许整体排除。无设备、没运行、签名失败、时间不足都属于未验证。plan 内容变化会重置该批次的 SPEC 确认，复用既有确认环节，不新增确认流程。plan 成功后删除自行创建的临时输入，正式计划只保存在账本。

第四步复用现有测试授权和设备选择。只选基础测试时不开始运行评估，适用项自然保持未验证。允许运行时，先确认构建产物对应当前源码，完成安装，冻结质量验证上下文：

```bash
python3 $OM/scripts/quality-assessment.py begin $OM --batch-id B01
```

命令要求当前批次 executing、specConfirmed=true，返回 sessionId；此后按质量计划的实际路由和场景执行。它是证据登记入口，不会自行完成测试。用现有运行工具采集证据到 `$OM/evidence/`，再登记：

```bash
python3 $OM/scripts/quality-assessment.py record $OM --batch-id B01 --input quality-result.json
```

输入字段：sessionId、checkId、status（passed/failed/not_verified）、observation；passed/failed 还需 device、configuration（实际窗口、形态、方向、输入方式）、artifacts。artifact 为 `{"kind":"interaction_trace","path":"evidence/B01/continuity.log"}`，另支持 runtime_screenshot/runtime_log。除 LAYOUT-01/OVERLAY-01 外，运行结果至少包含运行日志或交互轨迹，单张截图不能证明状态或交互通过。使用 begin 和 template 的真实 ID，不编造。observation 描述实际步骤、状态变化及断言，缺设备时写 not_verified 和原因。

构建日志、静态扫描、设计稿、其他形态截图不能冒充运行证据。脚本校验路径、内容指纹、会话和范围关联，无法替代对记录真实性的判断；Agent 必须实际执行并检查证据。源码、路由或计划变化后重新 begin 并重测，不能用新会话给旧文件重新盖章。

无需修改且已经正常的页面可独立取证；本质量计划的执行边界不受 `changeStatus=modified` 过滤，但不能借此修复未经授权的新问题。新问题进入 SPEC 或待处理项。修复仍遵守已有次数与停止条件。

```bash
python3 $OM/scripts/quality-assessment.py assess $OM --batch-id B01
# 全任务范围，未编制的批次也计入缺口：
python3 $OM/scripts/quality-assessment.py assess $OM
```

## 评级与报告

- 标准覆盖固定为全部计划页面、目标形态和目标等级的门槛；漏项、重复、篡改 ID/范围在写入时被拒绝。
- 每一级全部适用项通过才逐级升级；失败与未验证分开统计，不使用平均分。
- differentiated 的每个选定专项至少要有一项真实通过，不能用全 N/A 升级。单形态缺少该专项时可只显示 optimized，全范围显示实际通过的专项。
- 证据只从 index.json 中当前检查的最新登记结果读取，登记较新的失败或未验证不会回退选择旧通过结果。
- 报告增加目标等级、已验证等级、形态覆盖、逐项缺口与证据 ID；独立于流程完成状态和修复测试结论。
- 为防止源码变更后仍显示旧等级，评级时只读计算工程文件哈希（排除 .onemulti、依赖和构建缓存）以及路由和证据文件哈希，不进行源码诊断或自动重测。不可读输入保守记未验证。
- 基于已登记的标准和范围报告结论。扫描不完整、动态页面未核实或核心业务路径未覆盖时，先完善范围，不宣称全应用达标。

旧账本、仅静态验证、只修复一项、单设备验证都不能自动变成完整质量达标。无缺陷的质量评估允许生成无 Issue 的批次报告；质量结论与既有修复流程结论分别展示。
