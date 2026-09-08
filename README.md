# HarmonyOS-Plugins

[HarmonyOS-AI/HarmonyOS-Plugins](https://github.com/HarmonyOS-AI/HarmonyOS-Plugins) 是面向 Claude Code、Codex、Qoder / Qoder CN、Cursor、TRAE CN / TraeCode IDE、TraeWork 和 OpenCode V1/V2 的 HarmonyOS 插件仓库。仓库根目录是 marketplace，每个 `plugins/<name>/` 子目录都是可独立安装、版本化和发布的插件组。

仓库名称为 `HarmonyOS-Plugins`，marketplace 标识仍为 `harmonyos-ai`；安装命令中的
`<plugin-id>@harmonyos-ai` 使用 marketplace 标识。当前包含两个插件组，共九个 Skill。

## 插件目录

### `harmonyos-dev-toolkit`

HarmonyOS / ArkTS 开发工具包，包含以下共享 Skills：

| Skill | 说明 |
| --- | --- |
| [arkts-rules](plugins/harmonyos-dev-toolkit/skills/arkts-rules/SKILL.md) | ArkTS 语言规则、编译约束和 TypeScript → ArkTS 迁移。 |
| [harmonyos-docs-lookup](plugins/harmonyos-dev-toolkit/skills/harmonyos-docs-lookup/SKILL.md) | 检索内置的 HarmonyOS 官方开发文档。 |
| [harmonyos-sdk-api-lookup](plugins/harmonyos-dev-toolkit/skills/harmonyos-sdk-api-lookup/SKILL.md) | 查询 SDK API、类型、权限和系统能力。 |
| [harmonyos-live-preview](plugins/harmonyos-dev-toolkit/skills/harmonyos-live-preview/SKILL.md) | 在浏览器中预览和交互 ArkUI 页面，支持多设备、自定义尺寸及运行时调整，无需启动 DevEco Studio；仍需本地 HarmonyOS 工具链。 |

原插件 ID `harmony-skills` 已更名为 `harmonyos-dev-toolkit`。升级时需要使用新 ID 重新安装。

### `harmonyos-one-multi`

[HarmonyOS 一多适配插件](plugins/harmonyos-one-multi/README.md)，从 `hm-service-agent` 原样迁移，
完整保留一多流程编排、ArkUI、相机、H5 和 Flutter 五个 Skill 的内容、运行脚本、模板与代码资产。
原评测保存在 `evals/plugins/harmonyos-one-multi/`，通过逐文件 SHA-256 校验迁移内容一致。
插件可独立安装，各宿主的安装方式与下方示例相同，插件 ID 使用 `harmonyos-one-multi`。

## 默认支持范围

创建插件时不需要传平台开关，所有插件组默认生成全部宿主适配文件。共享能力是 Skills
（含脚本、参考文档和资源）及可移植 MCP 配置；各宿主独有的 Hooks、Rules、Agents 不做跨平台转换。

| 宿主 | 默认交付方式 |
| --- | --- |
| Claude Code | `.claude-plugin/plugin.json` + marketplace |
| Codex | `.codex-plugin/plugin.json` + marketplace |
| Qoder / Qoder CN | `.qoder-plugin/plugin.json` + marketplace + 插件 ZIP；CLI 可从本地目录安装 |
| Cursor | `.cursor-plugin/plugin.json` + marketplace；可链接到本地插件目录 |
| TRAE CN / TraeCode IDE | 项目级 `.trae/skills/` 链接与 `.trae/mcp.json` 合并安装器 |
| TraeWork | 每个 Skill 独立 ZIP，根级 `SKILL.md`，保留脚本和资源 |
| OpenCode V1 | 原有 npm 包 + V1 工具/配置适配器 |
| OpenCode V2 | 独立 `-v2` npm 包 + 原生 Skill/MCP 注册入口 |

TraeCode CLI 的既有 Skills 文档说明其兼容 `.trae/skills/`；CLI 2.0 虽然提供 `/plugins`，
当前公开文档没有完整的第三方插件打包和技能发现规范。因此这里不承诺 CLI 2.0 原生插件包兼容。
TraeWork 的 ZIP 交付只包含 Skill，所需 MCP 需在客户端单独配置。

## 架构

```text
HarmonyOS-Plugins/
├── .agents/plugins/marketplace.json
├── .claude-plugin/marketplace.json
├── .qoder-plugin/marketplace.json
├── .cursor-plugin/marketplace.json
├── marketplace.config.json
├── plugins/<name>/
│   ├── plugin.config.json                 # 插件元数据唯一来源
│   ├── .codex-plugin/plugin.json          # 以下均由 sync 生成
│   ├── .claude-plugin/plugin.json
│   ├── .qoder-plugin/plugin.json
│   ├── .cursor-plugin/plugin.json
│   ├── package.json                       # OpenCode V1
│   ├── distribution/opencode-v2.package.json
│   ├── opencode/plugin.js
│   ├── opencode-v2/plugin.js
│   ├── runtime/                           # 两代 OpenCode 共用的内容加载/MCP 转换
│   ├── trae/install.mjs
│   └── skills/                            # 所有宿主复用原始内容
├── scripts/lib/artifacts.mjs              # sync 与 validate 共用的产物目录
├── scripts/templates/                     # 运行时与安装器模板
├── evals/                                 # 不进入发布包的评测
└── dist/                                  # 打包输出，不提交
```

OpenCode V1 保留按需加载工具；V2 向宿主原生 Skill 注册表注入名称、描述、正文和实际资源位置。
两者都保留已有同名 MCP 配置；V2 还保留已有同名 Skill。MCP 不支持的字段会明确报错，避免静默丢失配置。
当前两个插件组均只声明 Skills，未附带 MCP 服务器；MCP 生成、转换和安装能力供声明了
`components.mcpServers` 的插件使用。

## 安装

以下以 `harmonyos-dev-toolkit` 为例，`harmonyos-one-multi` 使用相同流程。
本地安装、开发和打包示例均从仓库根目录执行；先克隆仓库：

```bash
git clone https://github.com/HarmonyOS-AI/HarmonyOS-Plugins.git
cd HarmonyOS-Plugins
```

示例中的 `/absolute/path/to/HarmonyOS-Plugins` 替换为实际克隆路径；通过远程 marketplace
安装时无需先克隆仓库。依赖 SDK、模拟器或设备的 Skill 另需准备其说明中要求的工具链。

### Claude Code

```bash
claude plugin marketplace add HarmonyOS-AI/HarmonyOS-Plugins
claude plugin install harmonyos-dev-toolkit@harmonyos-ai
```

本地验证：

```bash
claude plugin validate plugins/harmonyos-dev-toolkit
claude --plugin-dir plugins/harmonyos-dev-toolkit
```

### Codex

```bash
codex plugin marketplace add HarmonyOS-AI/HarmonyOS-Plugins
codex plugin add harmonyos-dev-toolkit@harmonyos-ai
```

本地 marketplace：

```bash
codex plugin marketplace add /absolute/path/to/HarmonyOS-Plugins
codex plugin add harmonyos-dev-toolkit@harmonyos-ai
```

### Qoder CN

CLI 从本地插件目录安装：

```bash
qodercn plugins install ./plugins/harmonyos-dev-toolkit
```

Qoder CN 的插件上传入口导入 `npm run plugins:pack` 生成的
`dist/harmonyos-dev-toolkit-<version>/harmonyos-dev-toolkit-<version>.zip`，
其中 `<version>` 取自插件的 `plugin.config.json`。
ZIP 根目录直接包含 `.qoder-plugin/plugin.json`，无额外目录嵌套。
Agent SDK 可继续将 `plugins/harmonyos-dev-toolkit` 的绝对路径作为 local plugin path。

### Cursor

本地开发安装：

```bash
mkdir -p ~/.cursor/plugins/local
ln -s /absolute/path/to/HarmonyOS-Plugins/plugins/harmonyos-dev-toolkit \
  ~/.cursor/plugins/local/harmonyos-dev-toolkit
```

重载 Cursor 后，在 Customize 中检查 Skill 和 MCP。
团队市场可导入本仓库的 `.cursor-plugin/marketplace.json`；团队策略需允许本地插件导入。
公共 Cursor Marketplace 上架仍需提交审核，生成文件不等于已发布。

### TRAE CN / TraeCode IDE

使用 Node.js 运行插件自带的安装器，无需 npm 安装依赖：

```bash
node plugins/harmonyos-dev-toolkit/trae/install.mjs --project /absolute/path/to/project
```

安装器将完整 Skill 目录链接到目标项目的 `.trae/skills/`。有 MCP 时合并 `.trae/mcp.json`，
保留原有服务器和其他配置；遇到同名但不同配置的 MCP、或不同来源的 Skill，会在修改前报错。
重复运行同一安装命令不会重复安装。保留插件源目录，移动或删除源目录会使链接失效。

重新加载 TRAE CN 后检查技能列表；包含 MCP 时，在设置 > MCP 中开启项目级 MCP。
已有 CLI 的 `.trae/skills/` 兼容能力以具体版本为准；不要将其等同于 CLI 2.0 原生插件支持。

### TraeWork

先打包，在插件市场的技能页上传 `dist/<name>-<version>/trae-work/` 下各个 ZIP。
每个 ZIP 包含根级 `SKILL.md` 及该 Skill 的完整支持文件。需要本地 SDK/模拟器的技能应在具备工具链
的本地运行环境使用；上传技能不会安装 HarmonyOS SDK。MCP 连接按客户端入口单独配置。

### OpenCode V1

发布到 npm 后，在 `opencode.json` 的 `plugin` 数组中添加：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["@harmonyos-ai/harmonyos-dev-toolkit"]
}
```

本地开发先在仓库运行 `npm install`，再将插件文件链接到目标项目：

```bash
mkdir -p /path/to/project/.opencode/plugins
ln -s /absolute/path/to/HarmonyOS-Plugins/plugins/harmonyos-dev-toolkit/opencode/plugin.js \
  /path/to/project/.opencode/plugins/harmonyos-dev-toolkit.js
```

### OpenCode V2

本地开发先在仓库运行 `npm install`，然后将实际 V2 入口的绝对路径加入项目 `opencode.jsonc`：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugins": ["/absolute/path/to/HarmonyOS-Plugins/plugins/harmonyos-dev-toolkit/opencode-v2/plugin.js"]
}
```

V2 使用 `plugins`（复数）。请勿指向插件根目录的 V1 `package.json` 或 V1 入口。

发布独立 V2 包后，可使用官方 V2 文档中的命令：

```bash
opencode2 plugin add @harmonyos-ai/harmonyos-dev-toolkit-v2
```

V2 包导出 `{ id, setup }` 原生插件契约，直接注册 Skill 和 MCP，并在卸载时释放注册。
该契约已对照 `@opencode-ai/plugin@0.0.0-beta-19151`（`Plugin.define` 为恒等函数）；
不导入 V1 SDK，也不依赖浮动 beta SDK。尚需在具体 V2 客户端版本中验收，不能保证未来 beta API 不变。

## 打包分发

仓库维护与验证使用 Node.js 22+、npm 和 Python 3.12+。打包脚本和一多 Python 契约测试可用
`PYTHON` 指定 Python 命令；跨宿主归档测试直接调用 `python3`，也需保证该命令可用。

```bash
npm install
npm run plugins:pack                         # 默认打包所有插件、所有格式
npm run plugins:pack -- harmonyos-dev-toolkit # 只选择插件，仍输出所有格式
```

每个 `dist/<name>-<version>/` 包含：

- `plugin/`：可直接安装的共享插件目录，含全部宿主清单和 TRAE 安装器。
- `<name>-<version>.zip`：Qoder CN 导入包，包含完整插件内容。
- `trae-work/*.zip`：每个 Skill 一个导入包；MCP-only 插件没有 Skill ZIP。
- 两个 `.tgz`：OpenCode V1 和独立 `-v2` npm 包。
- `opencode-v2/`：替换为 V2 package.json 的自包含目录，可用于本地加载和发布。
- `artifacts.json`：各宿主对应产物的索引。

打包仅生成本地文件，不上传市场或发布 npm。重复打包会替换同名、同版本的输出目录。
插件源代码只维护一份，发布包按需复制；包内排除 node_modules 和开发缓存。

## Skill 评测

生产插件与评测同仓版本化，但保持独立安装边界。生产内容只放在 `plugins/<plugin>/`；针对特定
Skill 的用例、fixture 和 grader 放在镜像路径 `evals/plugins/<plugin>/skills/<skill>/`。评测可以
依赖生产 Skill，生产 Skill 不得反向依赖 `evals/`。

当前有五个评测目标：live-preview、一多插件迁移与独立加载，以及一多 workflow、UI、camera
三个 Skill 的契约测试。可以单独运行 live-preview，也可以运行全部目标：

```bash
npm run evals:live-preview
npm run evals
```

运行器递归发现 `evals/` 下的 `eval.config.json`，按路径排序并串行执行同目录的 `run.mjs`，
任一目标失败即停止。目录规范和当前目标见 [评测说明](evals/README.md)。

评测配置、用例和 grader 应提交版本控制；`.eval-runs/`、`.eval-cache/` 和生成报告属于运行产物，
默认不提交。真实 HarmonyOS 工具链产生的工程与构建缓存继续放在被忽略的 `.skill-workspaces/`。

## 创建新的插件组

新插件组必须带至少一个 Skill 或一份 MCP 配置，脚手架不会生成空插件或 TODO 占位内容。

```bash
npm run plugins:create -- my-plugin \
  --display-name "My Plugin" \
  --description "A focused HarmonyOS workflow plugin." \
  --skill /absolute/path/to/my-skill
```

可以重复传入 `--skill`，也可以使用 `--mcp /absolute/path/to/.mcp.json`。脚手架会创建插件目录，并默认同步全部宿主清单、适配器和四个 marketplace。新插件无需额外的平台参数。

修改 `plugin.config.json` 后重新生成：

```bash
npm run plugins:sync
```

修改 `marketplace.config.json` 或 `scripts/templates/` 后也需运行同步命令；生成的清单和适配器
应随源配置一起提交。`plugins:pack` 会先同步全部插件，再打包选中的插件。

## 验证

```bash
npm run test:all
```

`test:all` 依次执行以下检查，也可单独运行：

| 命令 | 实际检查范围 |
| --- | --- |
| `npm test` | `scripts/tests/*.test.mjs`：配置与 marketplace、Skills-only / MCP-only / 混合插件创建、OpenCode V1/V2 加载、TRAE 安装与冲突处理、实际 ZIP/tgz 内容。 |
| `npm run evals` | `evals/` 下全部已注册目标，包括 Skill 行为与契约测试、一多迁移内容 SHA-256 校验及独立插件加载。 |
| `npm run plugins:validate` | 插件名与目录、版本格式、生成清单与适配器同步状态、marketplace 路径、Skill 入口与元数据、MCP JSON 及 V1/V2 内容加载。 |

安装了 Claude Code 时，可补充运行 `claude plugin validate plugins/harmonyos-dev-toolkit`。

## 官方规范与验收边界

规范核对日期：2026-09-05。

- [Qoder CN 插件](https://docs.qoder.cn/qoder-plugins)、[CLI 插件参考](https://docs.qoder.cn/cli/plugins-reference)
- [Cursor 插件参考](https://prod.cursor.com/docs/reference/plugins)
- [TRAE CN Skills](https://docs.trae.cn/ide_skills)、[项目级 MCP](https://docs.trae.cn/ide_add-mcp-servers)
- [TraeWork Skills 导入](https://docs.trae.cn/work_skills)、[TraeCode CLI 2.0 扩展](https://docs.trae.cn/cli_tools-and-extensions)
- [OpenCode V1 插件](https://opencode.ai/docs/plugins/)、[V2 插件 API](https://opencode.ai/v2/docs/build/plugins)

自动测试覆盖生成、内容加载契约、安装器和发布包。Cursor/Qoder/TRAE GUI 的市场导入、
Skill 自动触发及 OpenCode V2 完整客户端会话仍需在相应客户端中验收。
