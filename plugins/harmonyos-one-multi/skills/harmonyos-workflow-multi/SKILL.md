---
name: harmonyos-workflow-multi
description: 判断 HarmonyOS 一多适配请求是直接修复、全量分析还是按预定流程交付。范围和预期明确的局部问题交给对应领域 Skill；用户要求分析页面集、目录、模块或全工程，或明确要求质量分层评估、工程扫描、分批 SPEC、高保真、完整验证与报告时使用本 Skill。流程负责编排，具体 UI、Camera、H5 修法来自独立领域 Skill。当前不编排 2in1/PC 适配。
---

# HarmonyOS 一多全流程

## 适用边界

本 Skill 是可选的工程级流程，不是所有一多问题的唯一入口。当用户只提出现象、目标页面和预期结果都明确的局部问题时，应直接使用命中的领域 Skill，不创建 `.onemulti`、批次或报告。

本 Skill 只定义范围、扫描、批次、确认、施工顺序、质量目标、验证证据和报告契约。不在这里推断断点、布局、Camera API 或 H5 CSS 修法。进入问题诊断、方案、施工和领域验证时，必须加载与当前问题匹配的独立领域 Skill。

当前支持手机、折叠屏和平板形态，不支持 2in1/PC。范围或冻结验证计划明确包含 2in1/PC 时，记录为当前不支持并停止对应项，不得映射成其他设备继续执行。

**待办约束：** 用户可见 Todo 固定为五项，与下文五步一一对应。前置准备、构建、扫描等不单列；多批次复用第二至第五项，仅更新批次标识和状态。

## 质量目标

完整适配或用户要求质量评估时，读取 [质量分层契约](references/quality-levels.md)，按基础可用、自适应优化、场景增强确定目标。完整适配未指定时建议自适应优化并在方案中说明；仅分析不配置运行目录，局部修复不扩成全量评级。等级只针对明确页面和形态，不能由修复项通过率推断。

## 前置准备

全部命令用 `$OM` 表示流程 Skill 根目录：

```bash
export OM=.onemulti  # 已安装到工程
export OM=.          # 直接在本 Skill 源目录工作
```

运行环境不能读取工程外文件时，执行：

```bash
python3 <workflow Skill源目录>/scripts/install-to-project.py <工程根>
```

安装器只复制流程资源到 `<工程根>/.onemulti/`，并保留已有账本、证据和报告。领域 Skill 不安装到 `.onemulti`。

## 接续任务

先读取已有 `$OM/decisions.json`。任务未完成时从当前进度继续；`task.status=completed` 时，由 Agent 判断本次请求是原任务的修正、补测或方案调整，还是新的独立任务：延续任务保留产物并刷新相关批次状态；新任务先清理旧任务产物，再从第一步开始。具体命令按 [任务账本](references/task-ledger.md#接续与新任务)。仅查询或解释不改状态，无法判断时先询问，不自行清理。

## 五步闭环

### 1. 确认范围并生成批次计划

确认代码范围、目标设备/形态和排除项，执行 `devecocli build` 记录适配前基线。按 [页面发现](references/page-inventory.md) 执行：

```bash
python3 $OM/scripts/project-scan.py . --json
```

核实候选页面和动态路由，按 [路由表契约](references/route-map.md) 生成 `$OM/output/route-map.json`，再依页面依赖、公共组件和风险划分批次。本步只确定范围与计划，不生成具体 Issue 或修法。

本步不为具体修法检索官方文档。任务初始化后按质量契约配置目标；接续任务复用已有质量配置。

按 [任务账本](references/task-ledger.md) 使用 `bootstrap` 初始化 `$OM/decisions.json`；用户已要求高保真时，将对应批次的 `hifiRequired` 写为 `true`。多批任务询问用户先生成第一批 SPEC，还是先生成全部 SPEC；单批任务直接进入第二步。

### 2. 逐批生成并确认 SPEC

按确认模式为当前批或全部批次加载命中的领域 Skill，由领域知识确定现象、证据、根因、方案、计划文件和验证方法。写入 `decisions.json` 的各批 `issues` 就是修复 SPEC，不生成第二份 PRD/SPEC。启用质量评估时，同时生成完整 `qualityChecks`，覆盖原本正常与待修复的能力；具体场景和适用性纳入同一次 SPEC 确认。

这是官方文档检索的主要阶段：当领域 Skill 判断 API、版本、系统行为或知识缺口需要核实时，按该领域 Skill 的规则执行 `devecocli docs search/read`；不得用搜索摘要替代领域诊断。

展示 SPEC 前先读 [高保真流程契约](references/hifi-delivery.md) 及账本：`batch.hifiRequired=true` 时直接生成 HTML，设备覆盖读取 `task.targetForms`，不得按批自行缩减。尚未要求高保真且不是极小改动时，在同一次交互中提供预览或直接施工选项，选择预览后写回该批要求。`aggregate` 模式先生成全部 SPEC 和所有要求的批次 HTML，再统一确认；不得用 SPEC 已确认代替高保真交付，也不得连续询问预览和施工。

未获得整批确认前不得进入施工。

### 3. 按已确认 Issue 施工

以当前批次确认的 Issue、允许文件和目标形态为边界，加载对应领域 Skill 完成修改。流程 Skill 不自行生成 UI/Camera/H5 修法。每个 Issue 施工后立即回写 `changeStatus`、实际文件和变更摘要。

只有实际编译暴露 API 不兼容或文档事实冲突时，才在本步补充检索并核实全文；不得借此扩大已确认范围。

当前批已有高保真时，SPEC 控制修改范围和方案，HTML 控制已确认的布局、比例、位置和组件状态。

施工结束后按 [工具说明](references/tooling.md) 记录构建和适用检查结果；检查失败不阻断进入第四步，由验证阶段判断修复或记录限制。

### 4. 验证、修复并回写证据

完整读取 [验证流程](references/verification.md)，只执行已确认 `verificationPlan` 与可选 `qualityChecks` 中的形态、路由和检查项。质量检查不受已修改 Issue 过滤，具体执行与取证按质量契约；仅基础测试时不得填写运行通过。构建、静态检查、设备运行、多模态、证据和结果写回均由流程 Skill 执行；具体问题的验收标准来自对应领域知识。

只修复有证据表明由本批修改引起的问题，每批最多 5 轮；连续两轮无新增证据或根因进展时停止。可修复问题继续下一轮，不因首轮失败直接收尾。验证通过、无可继续自动修复项或达到停止条件后，记录遗留问题并进入报告；无法形成可靠证据时记为未验证，不得用编译成功代替运行或视觉结论。

验证失败且根因不明确时，可按领域 Skill 规则查询官方 FAQ 或最佳实践；报告阶段不再检索文档。

### 5. 生成批次报告与最终汇总

验证循环结束后，按 [报告规则](references/reporting.md) 生成 HTML；失败和未验证结果不阻断报告生成。脚本自带输入校验，无需重复执行校验命令：

```bash
python3 $OM/scripts/render-report.py $OM --batch-id <batchId>
```

批次报告展示后，只有用户明确同意继续才进入下一批；此时不得提前生成汇总报告。全部批次进入终态后，再单独执行：

```bash
python3 $OM/scripts/render-report.py $OM --summary
```

单批任务也在批次报告完成后生成汇总报告。汇总只聚合已有结果，不重跑测试。

## 资源路由

- 页面与路由扫描：[page-inventory.md](references/page-inventory.md)、[route-map.md](references/route-map.md)。
- 质量目标、标准覆盖和评级：[quality-levels.md](references/quality-levels.md)。
- 账本与状态：[task-ledger.md](references/task-ledger.md)。
- 高保真编排：[hifi-delivery.md](references/hifi-delivery.md)。
- 验证与证据：[verification.md](references/verification.md)、[multimodal-common-issues.md](references/multimodal-common-issues.md)。
- 报告：[reporting.md](references/reporting.md)。
- 工具边界：[tooling.md](references/tooling.md)。

## 不可破坏的边界

- 不在 workflow 中复制领域根因、修法、API 矩阵或代码资产。
- 不要求领域 Skill 引用 workflow 的目录、脚本、账本或报告。
- 全流程中只由 workflow 管理 `.onemulti`、批次、用户确认、证据和报告。
- 子 Agent 不是本流程的必要依赖。
