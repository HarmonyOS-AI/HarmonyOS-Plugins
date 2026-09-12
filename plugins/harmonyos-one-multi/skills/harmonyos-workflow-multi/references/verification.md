# 一多适配验证、问题修复与结果写回

## 执行总览

严格按以下顺序串行执行：

```text
完成前置校验并确定 STOPPED / STATIC_ONLY / FULL 模式
→ 进入循环测试
→ ① 执行允许的测试层
→ ② 将证据和结果直接写入正式 evidence 与账本
→ ③ 关联问题并分析原因
→ ④ 在确认范围内修复
→ ⑤ 重建并重测
→ ⑥ 更新本轮结果并判断是否继续
→ 循环结束后写回遗留结果并进入报告
→ 若使用模拟器则关闭模拟器
```

按以下唯一序列推进：

```bash
python3 $OM/scripts/verification/preflight.py begin .
python3 $OM/scripts/verification/preflight.py record-multimodal . [--available --description "<模型实际看到的内容>"]
# next=wait-model-switch：按下文失败提示处理，仅文字提示，不调用选项卡
# next=ask-test-scope：展示一道双选题并等待用户选择
python3 $OM/scripts/verification/preflight.py record-test-scope . --choice <basic_and_multimodal|basic_only>
# 用户切换后明确继续多模态测试：先记录 basic_and_multimodal，再重新探测；通过后不重复询问
# 用户选择多模测试后：匹配设备会直接复用或启动
python3 $OM/scripts/verification/prepare-device.py .
# 仅在没有匹配设备且用户选择自动安装后执行
python3 $OM/scripts/verification/prepare-device.py . --auto-install
# 用户明确指定其他设备时可覆盖自动选择
python3 $OM/scripts/verification/prepare-device.py . --use-device "<identifier>"
python3 $OM/scripts/verification/prepare-device.py . --instance-name "<existing-instance>"
# 确定 STATIC_ONLY / FULL 后进入本轮检查；STATIC_ONLY 不启动设备
python3 $OM/scripts/verification/run-foundation.py . --round <1..5> \
  [--check-script $OM/scripts/verification/checks/ui/static-check.py]
```

任一步骤执行失败时，优先参考[多模态验证常见问题集合](./multimodal-common-issues.md)进行排查。

## 前置校验

已完成任务的补测先按 [接续与新任务](./task-ledger.md#接续与新任务) 刷新相关批次状态，再执行 `begin`；不因原状态为 `completed` 转人工验证。

开始前须满足：

- `$OM/decisions.json` 完整、合法且已包含确认后的任务、批次、问题和 `verificationPlan`；
- `devecocli` 已安装、已配置并可调用，所有直接或间接调用 `devecocli` 的命令必须在沙箱外执行。

前置校验只产生以下三种执行模式。

| 条件                                                         | 模式          | 动作                                          |
| ------------------------------------------------------------ | ------------- | --------------------------------------------- |
| 无法从既有账本确定当前批次或修改边界                         | `STOPPED`     | 停止测试；保留错误和原账本                    |
| 用户明确只选基础测试或设备准备只允许基础测试 | `STATIC_ONLY` | 保留 L1/L2 结果并处理可修复问题；依赖 L3 的计划项写 `not_verified` |
| 多模态、用户授权和一台典型设备均已就绪     | `FULL`        | 执行基础检查与可执行的 L3；修复后重测                 |

### 1. 建立当前批次验证边界

执行 `preflight.py begin .`，校验待验证问题、修改范围和账本指定的当前批次路由，并冻结本轮验证边界。施工期检查缺失或失败不阻断进入验证，在本步补跑或修复；源码变化需要重建时直接执行，不退回第三步。

修复验证边界仅包含 `changeStatus=modified` 的问题。启用质量评估时，另按 [质量契约](quality-levels.md) 执行已确认的 `qualityChecks`，其范围覆盖批次内未修改但评级必需的能力；复用测试授权，不借评级扩大修复范围。

- `stage=boundary_failed`：进入 `STOPPED`。
- `stage=route_failed`：进入 `STATIC_ONLY`，L3 计划项写 `reason=route_table_invalid`。
- `next=record-multimodal`：进入多模态探测。

发现其他批次页面受本批组件影响时，执行：

```bash
python3 $OM/scripts/task-ledger.py add-deferred-regression $OM/decisions.json <issueId> --input - <<'JSON'
{"page":"<页面路径>","batchId":"<所属批次>","reason":"<影响原因>","suggestedCheck":"<建议检查项>"}
JSON
```

#### 禁止行为

* 不允许读取业务源码，手工复查账本、evidence 或路由表。
* 不允许执行其他批次页面的导航、截图和回归。

### 2. 探测多模态能力

在准备设备前，确认当前模型能够读取图片：

1. 确认 `$OM/assets/verification/startIcon.png` 存在。
2. 调用宿主的图片读取或附件能力，把该文件作为图片输入发送给当前模型，要求：
   `请获取并描述这张图片的可见内容、结构和主要颜色。`
3. 宿主成功提交图片，且模型准确描述可见内容，才算通过。
4. 识别成功时运行 `record-multimodal --available --description "<实际描述>"`；识别失败时运行不带 `--available` 的 `record-multimodal`。

首次探测成功时，`record-multimodal` 根据冻结计划项数量计算预计时间，并返回：

```json
{
  "mode": "STOPPED",
  "stage": "test_scope_confirmation_required",
  "next": "ask-test-scope",
  "testScopeEstimateMinutes": 7
}
```

探测失败返回 `next=wait-model-switch`。**不得调用询问工具或选项卡**，使用以下文字提示：

> 当前模型未通过图片理解探测，请选择后续测试方式：
>
> 1. **仅基础测试（默认方案）**：保留构建和静态检查结果，多模态测试标记为未验证，继续生成报告。请回复“仅基础测试”。
> 2. **继续多模态测试**：请先切换到支持图片理解的模型，再回复“切换完，继续执行多模态测试”。

用户选择仅基础测试，或当前任务已明确授权“默认同意、不等待”时，执行 `record-test-scope --choice basic_only`，保留 L1/L2 结果，将 L3 标记为未验证；基础检查若有可修复问题，仍按下文循环处理，结束后生成报告。否则必须以文字回复结束当前轮，等待用户选择或切换模型。

等待期间保留当前批次与已有 L1/L2 结果，不准备设备、不自动重试，也不视为用户跳过测试。用户切换后明确继续，先执行 `record-test-scope --choice basic_and_multimodal` 记录其授权，再重新读取探测图片并执行 `record-multimodal`；通过后直接进入步骤 4，不重复询问，再次失败则仍按上述失败分支处理。

首次探测成功则继续步骤 3。

### 3. 通过 ask 卡片确认测试范围

多模态探测通过后，根据探测结果使用 `record-multimodal` 返回的 `testScopeEstimateMinutes` 调用 `AskQuestion`

```json
{
  "title": "确认测试范围",
  "questions": [
    {
      "id": "multimodal_test_scope",
      "prompt": "该适配场景涉及多模态交互测试，从确认后到测试与设备清理完成估计还需约 {{testScopeEstimateMinutes}} 分钟。此处仅为预估，以测试实际运行时间为准。请确认测试环节是否包含多模交互测试？",
      "options": [
        {
          "id": "basic_and_multimodal",
          "label": "确认执行基础测试与多模交互测试"
        },
        {
          "id": "basic_only",
          "label": "不执行多模交互测试，仅执行基础测试"
        }
      ]
    }
  ]
}
```

- 选择 `basic_and_multimodal`：继续步骤 4–5。
- 选择 `basic_only`：进入 `STATIC_ONLY`，不准备设备，所有依赖 L3 的计划项写
  `status=not_verified`、`reason=multimodal_declined_by_user`。

此处 `mode=STATIC_ONLY` 只表示设备尚未绑定，不表示用户选择失败；成功绑定唯一设备后才进入 `FULL`。

### 4. 发现并复用设备

先运行不带选项的 `prepare-device.py`。它从 `verificationPlan` 推导目标形态，并按以下顺序选择一台匹配设备：

1. 已连接的匹配真机；
2. 已连接的匹配模拟器；
3. 已安装的匹配模拟器，优先运行中的实例。

匹配结果已经确定时直接绑定设备；已安装但未运行的模拟器直接启动并绑定，不再询问用户。用户明确指定设备时，才使用 `--use-device` 或 `--instance-name` 覆盖自动选择。

没有匹配设备时，脚本返回 `next=ask-install`。此时只询问一次：选择“自动安装推荐模拟器”“我先手动安装”或“只做基础测试”。手动安装完成后重新运行默认命令；自动安装使用 `--auto-install`。用户确认安装方式前不得下载镜像或创建模拟器。

### 5. 复用或自动安装唯一设备

设备类型从当前批次 `verificationPlan` 推导：

| 主要适配目标           | 候选模拟器类型                                              |
| ---------------------- | ----------------------------------------------------------- |
| 普通手机适配           | `phone`                                                     |
| 折叠、展开或悬停       | `foldable`、`widefold`、`triplefold` 中与目标形态匹配的一种 |
| 平板布局或平板自由多窗 | `tablet`                                                    |

同时需要折叠屏和平板形态时，优先选择 `triplefold`；明确要求适配阔折叠时，选择 `widefold`。

计划包含直板机基线且选中折叠屏时，用同一设备的折叠态验证，证据记录设备、折叠状态和窗口尺寸。

匹配设备存在时直接复用；模拟器未运行时启动该实例。只有没有匹配设备且用户选择自动安装后，脚本才检查模拟器 License，并按“本地镜像 → 下载镜像 → 创建实例 → 启动连接”执行；License 未接受时展示协议并等待用户确认，不得自动接受。

#### 失败处理

- 用户选择只做基础测试：进入 `STATIC_ONLY`，L3 写 `not_verified`。
- 没有设备能够覆盖主要计划项：保留枚举结果，等待用户安装或进入 `STATIC_ONLY`。
- 唯一设备只能覆盖部分计划项：其余项目写 `not_verified`、`reason=representative_device_unavailable`。
- 设备失效：只恢复同一设备；失败后回到步骤 5，不增加第二台设备。
- 安装、启动或连接失败：保留真实错误，让用户选择重试、手动安装或只做基础测试。

## 循环测试

除 `STOPPED` 外，每批最多执行 5 轮：

```text
执行测试 → 记录证据和结果 → 分析原因 → 修复 → 重测 → 更新结果并判断是否继续
```

### 1. 执行允许的测试层

每轮从 `run-foundation.py` 入口执行。首轮可复用本批同源码且已通过的 L1/L2；缺失、失败或源码变化时自动补跑，不作为流程门禁。`STATIC_ONLY` 不执行 L3；`FULL` 在构建成功后执行 L3，静态检查失败本身不禁止设备验证。修复后第 2–5 轮重跑基础检查与受影响的 L3 项。

| 层级 | 执行内容 | 通过标准 | 结果证据 |
|---|---|---|---|
| L1 构建 | 本批修改涉及 HSP 时，先执行 `devecocli build --modules <修改过的 HSP 模块名...>`，再执行 `devecocli build`；模块识别由 `run-foundation.py` 完成 | 所有构建命令退出码为 0，构建和类型检查通过，并生成预期产物 | 命令、退出码、日志、产物路径或失败摘要 |
| L2 静态检查 | 执行流程内与当前问题匹配的静态检查脚本；没有适用脚本时记为不适用 | 已执行脚本成功且无阻断级结果，或明确记录不适用原因 | 脚本路径、参数、退出码、输出、规则 ID、文件位置或不适用原因 |
| L3 设备运行验证 | 将构建产物安装到选定设备并启动入口 Ability；根据 `verificationPlan.routeId` 从已冻结 JSON 路由表读取有序步骤，逐步进入目标页面，构造计划要求的形态和状态，采集截图并对照 `check` 判定 | 安装和启动成功，应用处于可交互状态且无启动崩溃；所有路径步骤及中间页面断言通过，目标页面可达，截图和计划内交互结果符合预期 | 设备信息、命令、退出码、进程状态、运行日志或失败摘要，以及 `form + checkId + routeId`、实际步骤、失败 stepId、页面及形态信息、截图、交互结果和判断依据 |

相机问题执行 L3 时，额外按 [相机运行验证矩阵](domain-verification/camera.md) 覆盖计划内的设备形态、方向、输出流和生命周期；未进入当前 `verificationPlan` 的组合不得临时扩充。

#### L3 设备运行验证执行原则

##### 安装包类型提示

多模态测试安装构建产物时，先枚举本次应用依赖的全部 HAP（`.hap`）和 HSP（`.hsp`）：

- 没有 HSP 时，默认安装并启动可运行的入口 HAP。
- 存在 HSP 时，推荐使用以下安装方式；将示例产物名替换为本轮实际构建出的签名 HSP/HAP，并对每个依赖包各执行一次 `hdc file send`：

```bash
hdc shell mkdir data/local/tmp/install_dir
hdc file send library-default-signed.hsp "data/local/tmp/install_dir"
hdc file send entry-default-signed.hap "data/local/tmp/install_dir"
hdc shell bm install -p "data/local/tmp/install_dir"
hdc shell rm -rf data/local/tmp/install_dir
```

##### 真机签名确认门禁

选中的唯一设备为真机时，首次执行 `devecocli run` 命令明确报告工程未配置签名、产物未签名或真机不能安装 unsigned HAP：

1. 立即中断验证并提示用户：当前真机无法安装未签名产物，请先在 DevEco Studio 或工程配置中完成可用于该真机的签名。
   等待用户选择期间，不为任何 L3 计划项写入 `failed/not_verified`，并保持已绑定真机、`stage=device_ready` 和当前轮次不变。
2. 向用户提供明确选择：
   1. **已完成签名配置，继续验证**
   2. **暂不配置签名，停止真机验证**
   3. **其他**
3. 选择 1：在同一真机、同一轮次重新执行 `devecocli run`；若仍返回签名错误，继续保持中断并再次提示。
4. 选择 2：将依赖该真机运行的 L3 计划项写为 `status=not_verified`、`reason=real_device_signing_unavailable`。

##### 图像采集和结果判定

* 直接使用以下有效命令。`<screenshot-path>` 文件名至少包含轮次、`issueId`、`form` 和`checkId`：

  ```bash
  devecocli run --module "<module>" --device "<name-or-serial>"
  devecocli emulator fold single --target "<instance-name-or-serial>"
  devecocli emulator fold double --target "<instance-name-or-serial>"
  devecocli emulator fold triple --target "<instance-name-or-serial>"
  devecocli ui screenshot --device "<name-or-serial>" --path "$OM/evidence/<batchId>/round-<N>/<screenshot-path>.png"
  ```

* 当需要点击带文字的控件时，直接执行：

  ```bash
  devecocli ui click --help
  devecocli ui layout --help
  ```

  获取布局并查找目标文字,优先按节点 id 点击，否则按 bounds 中心坐标点击。

* 测试计划出现不同的路由路径，例如从Tab1进入L2页面后，下一个测试项需要返回首页点击Tab2，不点击返回按钮，重新推送工程从首页执行。

* 测试步骤出现模拟器旋转时，需要重新推送工程。

* 测试设备为真机折叠屏时，可以在当前断点测试项全部结束后提醒用户折叠/展开设备以覆盖更多测试项。

* 只执行 `verificationPlan` 要求的形态命令，执行过程中只登记判断结果。**失败原因分析、源码读取和代码修改在当前轮次全部结束后执行**。

* 多模态能力探测通过后，优先使用图片完成判断；只有图片无法判断时，再在沙箱外获取当前页面的完整组件树辅助判断。

  ```bash
  devecocli ui layout --format json --mode full --depth 0 > "$OM/evidence/<batchId>/round-<N>/<name>-component-tree.json"
  ```

  结合组件类型、文本、可见状态和 `bounds` 判断，并将文件登记为 `type=component_tree`。组件树与截图使用相同的 `issueId + form + checkId`。

* 完成本轮全部 L3 计划项后，用一次 `record-batch` 原子登记本轮全部截图、可选组件树和逐项结果。
  本轮基础检查和适用 L3 项均通过时结束验证；存在 `failed / not_verified` 时，统一读取未通过证据并分析是否可修复。没有修改代码时不重复执行基础检查命令；可修复时继续下一轮，不直接生成报告。源码仍按下一节的最小读取规则处理。

### 2. 记录证据和结果

命令和环境事实直接写 `$OM/evidence/index.json`，轮次产物按批次写入`$OM/evidence/<batchId>/round-N/`。
每轮通过一次 `record-batch` 从 stdin 原子登记证据并更新对应账本结果：

```bash
python3 $OM/scripts/verification/evidence-session.py record-batch . --input - <<'JSON'
{
  "round": 1,
  "commands": [{"argv": ["devecocli", "emulator", "fold", "double"], "exitCode": 0, "links": [{"issueId": "B01-UI-001", "form": "foldable", "checkId": "waterflow-md"}]}],
  "artifacts": [{"type": "screenshot", "path": "evidence/B01/round-1/B01-UI-001-foldable-waterflow-md.png", "links": [{"issueId": "B01-UI-001", "form": "foldable", "checkId": "waterflow-md"}]}],
  "results": [{"issueId": "B01-UI-001", "form": "foldable", "checkId": "waterflow-md", "status": "passed"}]
}
JSON
```

顶层 `round` 统一提供当前批次内的轮次；新产物的路径必须与当前 `batchId`一致。命令不记录工程根 `cwd`，成功命令不记录 `stdout/stderr`，失败时才保留必要的`reason/stdout/stderr`。结果的 `reason` 只在非 `passed` 时填写。结果允许逐项增量写入，循环结束后补齐未执行项及原因，报告脚本负责最终对账。

#### evidence 索引格式

每条 evidence 只含 `evidenceId/type/round/links` 及 `data` 或 `path`。

第 1 轮结束后，账本逐项结果与 `verificationPlan` 一一对应。执行过程中可按 `issueId + form + checkId` 增量写入；每个计划项最终仅有一个结果。后续轮次只更新重测项，其他结果保持不变。

### 3. 关联问题并分析失败原因

先只用失败证据、命令诊断、日志、`changeSummary` 和冻结计划完成初步归因。

仅当失败可能由当前批修改引入、现有证据不足以定位根因且存在自动修复可能时，才读取失败项关联的最小文件集：该 issue 的 `changedFiles`，必要时补充直接命中的 `plannedFiles` 和一层已登记公共依赖。

历史基线、环境、范围外或需要业务决策的问题转人工处理，相关计划项保留 `failed` 或`not_verified` 状态。

##### 禁止行为

* 不允许全量扫描源码，不读取其他批次、其他页面或与失败项无直接依赖的文件。

### 4. 在确认范围内修复

修改范围限于已确认问题的计划文件和已登记的公共依赖。扩大范围前须更新 SPEC 并获得确认。修复知识、资产和案例来自当前问题命中的独立领域 Skill。

### 5. 重建并重测

重测只处理上一轮 `failed`，以及因可修复的前置层失败而 `not_verified` 的校验点。

修复后依次重跑 L1、L2 和可执行的 L3。构建或安装失败时，记录错误并将依赖该产物的 L3 项记为未验证；仍分析能否修复并继续下一轮。静态检查失败不一律停止 L3。L3 仅重跑与修改点及受影响公共依赖对应的计划项并重新采集截图；已通过且不受影响的 L3 计划项不重跑。

保留修复前后的证据，并以重测结果更新对应 issue 的 `verificationResults`。问题级验证结论始终按完整计划实时聚合，不额外写入 `verifyStatus`。

### 6. 更新结果并判断是否继续

本轮结束时用一次 `record-batch` 写入证据和逐项结果，并聚合本轮状态。

有本批范围内可自动修复的问题时继续下一轮，不因某轮失败直接结束验证。全部通过、无可继续自动修复项、同一失败连续两轮没有新增证据或根因进展，或第 5 轮结束时退出；失败和未验证结果如实保留，不要求全绿才能收尾。

## 结束验证并写回结果

循环结束后，用 `record-batch` 写回最终结果；无法执行的计划项标记未验证并说明原因。随后进入第五步，报告脚本检查输入结构和引用，不以检查全部通过作为收尾条件。未登记的额外文件不作为证据，也不阻断报告。

### 关闭模拟器

无论测试通过、未通过或状态校验失败，测试流程结束后都执行最终设备清理。若本轮使用的是模拟器，在账本和证据写回完成后，直接在沙箱外执行：

```bash
devecocli emulator stop "<instance-name-or-serial>"
```

退出时保留执行模式、失败证据、已执行轮次、停止原因和未解决问题。
