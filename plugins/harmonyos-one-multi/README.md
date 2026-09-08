# HarmonyOS 一多适配

`HarmonyOS-Plugins` 仓库中的独立插件 `harmonyos-one-multi`，包含五个 Skill。
提供 Claude Code、Codex、Qoder / Qoder CN、Cursor 清单、TRAE CN / TraeCode IDE 安装器，
以及 OpenCode V1/V2 入口；仓库打包命令还会生成 Qoder 插件 ZIP 和 TraeWork 单 Skill ZIP。
从 `hm-service-agent` 的 `skills/harmonyos-one-multi` 原样迁入，五个 Skill 的说明、知识、
脚本、代码资产和模板均保持原内容。

| Skill | 能力 |
| --- | --- |
| [harmonyos-workflow-multi](skills/harmonyos-workflow-multi/SKILL.md) | 工程与页面扫描、路由发现、分批 SPEC、高保真确认、任务账本、静态检查、设备验证取证和 HTML 报告。 |
| [harmonyos-ui-multi](skills/harmonyos-ui-multi/SKILL.md) | ArkUI 断点、响应式布局、窗口、安全区、键盘、折展悬停、方向、无障碍与高保真方案及代码资产。 |
| [harmonyos-camera-multi](skills/harmonyos-camera-multi/SKILL.md) | 相机能力探测、折叠切镜、Session 与输出流、旋转镜像、Surface、预览比例和 stride 问题。 |
| [hmos-multidevice-h5-layout](skills/hmos-multidevice-h5-layout/SKILL.md) | H5/WebView 响应式布局、动态 REM、媒体、安全区、键盘、动态窗口和 ArkTS-H5 联动；含扫描器与页面模板。 |
| [harmonyos-flutter-multi](skills/harmonyos-flutter-multi/SKILL.md) | Flutter 原生与 HADSS 两条路线、OHOS 宿主集成、折叠屏/Pura X、DPI、LTPO、代码示例与验收用例。 |

H5 的源目录名为 `harmonyos-h5-multi`，原 `SKILL.md` 标识为 `hmos-multidevice-h5-layout`。
迁移后使用原标识作为目录名，Skill 内容保持不变。

当前支持手机、折叠屏和平板，其他能力边界沿用各 Skill 原说明。插件所需知识与资产都在本目录内，
无需读取原仓库或安装其他 HarmonyOS Skill 插件。执行脚本需 Python 3 或 Node.js；构建、设备操作与
官方文档查询继续使用原流程规定的 `devecocli` 及相应 SDK、设备环境。

## 使用

通过仓库 marketplace 安装 `harmonyos-one-multi`，或将本目录作为本地插件交给宿主加载。
各宿主的安装方法见 [仓库安装说明](../../README.md#安装)，将示例插件 ID 换成 `harmonyos-one-multi`；
marketplace 标识仍为 `harmonyos-ai`。

| OpenCode 版本 | 入口 | npm 包 | 加载方式 |
| --- | --- | --- | --- |
| V1 | `opencode/plugin.js` | `@harmonyos-ai/harmonyos-one-multi` | 通过 `harmonyos_one_multi_skill` 工具按需加载。 |
| V2 | `opencode-v2/plugin.js` | `@harmonyos-ai/harmonyos-one-multi-v2` | 注册原生 Skill，卸载时释放注册。 |

npm 包需发布后才能通过包名安装；本地加载可使用上述入口。当前插件只声明 Skills，未附带 MCP 服务器。

局部问题直接使用相应领域 Skill；需要工程级分析、分批交付、验证和报告时使用 workflow。
需要把流程运行资源放入目标工程时，执行：

```bash
python3 <插件目录>/skills/harmonyos-workflow-multi/scripts/install-to-project.py <工程根>
```

安装器继续保留工程已有账本、证据和报告。

## 维护验证

原 `evals/` 文件完整保存在仓库的 `evals/plugins/harmonyos-one-multi/skills/`，不进入插件包。
运行器在临时目录重建原测试布局，执行未修改的原契约测试。维护时从仓库根目录运行：

```bash
npm run evals
npm run plugins:validate
```

只运行本插件的迁移完整性、独立加载和 npm 包内容检查：

```bash
node evals/plugins/harmonyos-one-multi/run.mjs
```

workflow、UI 和 camera 的契约测试由各自评测目录中的 `run.mjs` 执行，`npm run evals` 会一并运行。

迁移来源、完整的 230 个文件映射和 SHA-256 保存在
`evals/plugins/harmonyos-one-multi/migration-inventory.json`，迁移评测核对每个文件内容一致。
