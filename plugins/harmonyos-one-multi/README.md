# HarmonyOS 一多适配

`HarmonyOS-Plugins` 仓库中的独立插件 `harmonyos-one-multi`，包含六个 Skill。
提供 Claude Code、Codex、Qoder / Qoder CN、Cursor 清单、TRAE CN / TraeCode IDE 安装器，
以及 OpenCode V1/V2 入口；仓库打包命令还会生成 Qoder 插件 ZIP 和 TraeWork 单 Skill ZIP。
初始版本从 `hm-service-agent` 迁入；历史清单与哈希保留用于审计，当前版本继续维护。

| Skill | 能力 |
| --- | --- |
| [harmonyos-workflow-multi](skills/harmonyos-workflow-multi/SKILL.md) | 工程与页面扫描、路由发现、分批 SPEC、高保真确认、任务账本、静态检查、设备验证取证和 HTML 报告。 |
| [harmonyos-ui-multi](skills/harmonyos-ui-multi/SKILL.md) | ArkUI 断点、响应式布局、窗口、安全区、键盘、折展悬停、方向、无障碍与高保真方案及代码资产。 |
| [harmonyos-camera-multi](skills/harmonyos-camera-multi/SKILL.md) | 相机能力探测、折叠切镜、Session 与输出流、旋转镜像、Surface、预览比例和 stride 问题。 |
| [harmonyos-h5-multi](skills/harmonyos-h5-multi/SKILL.md) | H5/WebView 响应式布局、动态 REM、媒体、安全区、键盘、动态窗口和 ArkTS-H5 联动；含扫描器与页面模板。 |
| [harmonyos-flutter-multi](skills/harmonyos-flutter-multi/SKILL.md) | Flutter 原生与 HADSS 两条路线、OHOS 宿主集成、折叠屏/Pura X、DPI、LTPO、代码示例与验收用例。 |
| [harmonyos-rn-multi](skills/harmonyos-rn-multi/SKILL.md) | React Native for OpenHarmony 多设备布局：动态窗口与父约束、断点与动态样式、RTL、Modal/Portal、折叠连续性、安全区与官方自适应组件。 |

H5 的源目录名为 `harmonyos-h5-multi`，原 `SKILL.md` 标识为 `hmos-multidevice-h5-layout`。
迁移后使用原标识作为目录名。

当前支持手机、折叠屏和平板，其他能力边界沿用各 Skill 原说明。插件所需知识与资产都在本目录内，
无需读取原仓库或安装其他 HarmonyOS Skill 插件。执行脚本需 Python 3 或 Node.js；构建、设备操作与
官方文档查询继续使用原流程规定的 `devecocli` 及相应 SDK、设备环境。

## 质量分层

完整适配可设置基础可用（ready）、自适应优化（optimized）或场景增强（differentiated）目标。标准覆盖全部计划页面和形态，原本正常的能力也需验证；按证据逐级计算等级，缺设备、仅编译或局部修复不会自动达标。增强体验按业务选择专项，当前评级范围为手机、折叠屏和平板。

本插件定义统一的适配质量分级：workflow 的 [质量契约](skills/harmonyos-workflow-multi/references/quality-levels.md) 集中维护等级定义、达标规则、证据与报告；领域 Skill 只提供自身的验收要点，不重复定义分级。旧账本兼容并显示未评估。

## 使用

通过仓库 marketplace 安装 `harmonyos-one-multi`，或将本目录作为本地插件交给宿主加载。
各宿主的安装方法见 [仓库安装说明](https://github.com/HarmonyOS-AI/HarmonyOS-Plugins#安装)，将示例插件 ID 换成 `harmonyos-one-multi`；
marketplace 标识仍为 `harmonyos-ai`。

| OpenCode 版本 | 入口 | npm 包 | 加载方式 |
| --- | --- | --- | --- |
| V1 | `opencode/plugin.js` | `@harmonyos-ai/harmonyos-one-multi` | 通过 `harmonyos_one_multi_skill` 工具按需加载。 |
| V2 | `opencode-v2/plugin.js` | `@harmonyos-ai/harmonyos-one-multi-v2` | 注册原生 Skill，卸载时释放注册。 |

npm 包需发布后才能通过包名安装；本地加载可使用上述入口。当前插件只声明 Skills，未附带 MCP 服务器。

局部问题直接使用相应领域 Skill；需要工程级分析、分批交付、验证和报告时使用 workflow。
仅分析时直接读取插件资源并运行只读扫描，不安装 `.onemulti`；明确要求报告时只生成指定报告。完整交付复用当前授权、高保真和测试选择，遇到新增范围或实质方案变化再确认。

完整交付需要把流程运行资源放入目标工程时，执行：

```bash
python3 <插件目录>/skills/harmonyos-workflow-multi/scripts/install-to-project.py <工程根>
```

安装器继续保留工程已有账本、证据和报告。

## 维护验证

评测资源保存在仓库 `evals/plugins/harmonyos-one-multi/`，不进入插件包。日常检查不调用模型：

```bash
npm run evals
npm run plugins:validate
node evals/plugins/harmonyos-one-multi/run.mjs
```

除 `harmonyos-rn-multi` 外的五个 Skill 均有独立 `run.mjs`（RN Skill 暂无源侧评测）。确定性检查覆盖资源链接、独立加载、打包、扫描、schema v3 兼容、授权与偏好边界、证据和报告。文档中的特定句子或用例 ID 不再充当行为通过证明。

历史迁移审计使用冻结提交 `c7213b1b43d1d060f5e428d7278f1ba3db38ee3e`，比对保留的 230 个文件映射与 SHA-256；当前源码允许正常演进：

```bash
npm run evals:one-multi:history
```

显式执行真实 Agent 前后对比（需要已配置 OpenCode 1.18.29 与 bailian-blue/qwen3.8-max）：

```bash
npm run evals:one-multi:compare -- --output .eval-runs/one-multi/p1-final
```

共 20 个冻结场景 × 2 个版本 × 2 次运行，以及 40 次匿名配对评分。先迭代开发集可加 `--split development`；同目录再执行完整命令会复用相同版本的已有结果。源码变化必须换输出目录，旧失败记录保留。HTML、JSON、版本配置、冻结协议和原始轨迹均写入指定 `.eval-runs/` 目录。报告只有全部验收门槛通过才标记质量提升；测试桩不代表真实编译或设备通过。
