# HarmonyOS-Plugins

为 AI 编程助手提供鸿蒙开发能力，帮助你编写 ArkTS、构建调试应用、测试与验证应用，以及适配手机、平板和折叠屏。
支持 Claude Code、Codex、Qoder / Qoder CN、Cursor、TRAE CN、TraeWork 和 OpenCode。

## 选择插件

按需要安装，可以组合使用。

| 插件 | 适合做什么 |
| --- | --- |
| `harmonyos-dev-toolkit` | 编写和修复 ArkTS、查询官方文档、构建运行应用、排查设备日志。 |
| `harmonyos-test-toolkit` | 验证页面布局与交互、复现问题并确认修复、执行设备测试与自动化回归。 |
| `harmonyos-one-multi` | 为手机、平板和折叠屏适配 ArkUI、相机、H5 与 Flutter 界面。 |

### 开发工具

- [arkts-rules](plugins/harmonyos-dev-toolkit/skills/arkts-rules/SKILL.md)：编写符合 ArkTS 约束的代码，处理编译错误与 TypeScript 迁移。
- [deveco-cli](plugins/harmonyos-dev-toolkit/skills/deveco-cli/SKILL.md)：创建工程、构建运行、管理设备和模拟器、查看日志。
- 官方文档查询：搜索华为开发者文档，查找 API 用法。

构建和调试需要本机安装 DevEco CLI 与 HarmonyOS 工具链；官方文档查询需要网络连接。

### 测试与验证

围绕应用改动提供验证：检查视觉与交互结果、复现设备问题、执行回归测试，并保留截图和报告作为依据。

- [harmonyos-live-preview](plugins/harmonyos-test-toolkit/skills/harmonyos-live-preview/SKILL.md)：通过页面预览验证不同屏幕尺寸下的布局和交互，检查改动后的视觉结果。
- [harmonyrun](plugins/harmonyos-test-toolkit/skills/harmonyrun/SKILL.md)：在真机或模拟器上复现问题并验证修复，运行自动化用例与 Hypium 回归测试，输出测试报告。

预览需要本地 HarmonyOS 工具链，支持 macOS / Linux。设备测试需要 hdc、已开启调试的设备和
[HarmonyRun](https://pypi.org/project/harmonyrun/)，可通过 pip 安装：

```bash
python -m pip install harmonyrun
```

通过 AI 助手逐步操作设备无需额外配置模型；让 HarmonyRun 自动运行自然语言任务或套件，需要配置模型和 API Key。
安装或设备连接有问题时，见 [安装与连接](plugins/harmonyos-test-toolkit/skills/harmonyrun/references/setup.md)。

### 一多适配工具

| Skill | 适配场景 |
| --- | --- |
| [harmonyos-workflow-multi](plugins/harmonyos-one-multi/skills/harmonyos-workflow-multi/SKILL.md) | 分析工程的适配问题，分批修改并验证。 |
| [harmonyos-ui-multi](plugins/harmonyos-one-multi/skills/harmonyos-ui-multi/SKILL.md) | ArkUI 响应式布局、窗口、安全区、键盘和折叠屏。 |
| [harmonyos-camera-multi](plugins/harmonyos-one-multi/skills/harmonyos-camera-multi/SKILL.md) | 相机预览比例、旋转、折叠和切镜。 |
| [hmos-multidevice-h5-layout](plugins/harmonyos-one-multi/skills/hmos-multidevice-h5-layout/SKILL.md) | H5 / WebView 页面在不同屏幕与窗口下的布局。 |
| [harmonyos-flutter-multi](plugins/harmonyos-one-multi/skills/harmonyos-flutter-multi/SKILL.md) | Flutter 鸿蒙应用的屏幕与折叠适配。 |

## 安装

以下以 `harmonyos-dev-toolkit` 为例。安装测试验证或一多适配工具时，将命令中的插件名替换为
`harmonyos-test-toolkit` 或 `harmonyos-one-multi`。

### Claude Code

```bash
claude plugin marketplace add HarmonyOS-AI/HarmonyOS-Plugins
claude plugin install harmonyos-dev-toolkit@harmonyos-ai
```

### Codex

```bash
codex plugin marketplace add HarmonyOS-AI/HarmonyOS-Plugins
codex plugin add harmonyos-dev-toolkit@harmonyos-ai
```

### 其他客户端

下面的安装方式需要先将仓库下载到本机：

```bash
git clone https://github.com/HarmonyOS-AI/HarmonyOS-Plugins.git
cd HarmonyOS-Plugins
```

将示例中的 `/absolute/path/to/HarmonyOS-Plugins` 替换为实际下载路径，项目路径替换为你的应用工程。
安装后保留仓库目录。

#### Qoder CN

```bash
qodercn plugins install ./plugins/harmonyos-dev-toolkit
```

使用 ZIP 导入时，按下方“获取导入包”生成插件包，再在客户端的插件导入入口选择它。

#### Cursor

macOS / Linux 本地安装：

```bash
mkdir -p ~/.cursor/plugins/local
ln -s /absolute/path/to/HarmonyOS-Plugins/plugins/harmonyos-dev-toolkit \
  ~/.cursor/plugins/local/harmonyos-dev-toolkit
```

重载 Cursor，在 Customize 中确认插件可用。

#### TRAE CN / TraeCode IDE

```bash
node plugins/harmonyos-dev-toolkit/trae/install.mjs --project /absolute/path/to/project
```

重新加载客户端；需要文档查询或设备控制时，在设置 > MCP 中开启项目级 MCP。

#### TraeWork

按下方“获取导入包”生成 Skill ZIP，在插件市场的技能页逐个上传。文档查询或设备控制所需的 MCP
连接在客户端单独配置；依赖 SDK 和设备的任务需在具备这些环境的本机执行。

#### OpenCode

先在仓库中运行 `npm install`，再按你使用的 OpenCode 版本配置。

V1：将插件链接到应用工程：

```bash
mkdir -p /path/to/project/.opencode/plugins
ln -s /absolute/path/to/HarmonyOS-Plugins/plugins/harmonyos-dev-toolkit/opencode/plugin.js \
  /path/to/project/.opencode/plugins/harmonyos-dev-toolkit.js
```

V2：将插件路径加入应用工程的 `opencode.jsonc`，保留已有配置：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugins": ["/absolute/path/to/HarmonyOS-Plugins/plugins/harmonyos-dev-toolkit/opencode-v2/plugin.js"]
}
```

#### 获取导入包

需要 Node.js 22+、npm 和 Python 3。在仓库目录执行：

```bash
npm install
npm run plugins:pack -- harmonyos-dev-toolkit
```

到 `dist/` 中找到对应插件目录：根目录的 ZIP 用于 Qoder CN，`trae-work/` 下的 ZIP 用于 TraeWork。

## 开始使用

安装后重新加载客户端，打开你的鸿蒙工程，直接描述任务。例如：

| 你想做什么 | 可以这样说 |
| --- | --- |
| 修复编译错误 | “检查这个页面的 ArkTS 编译错误并修复。” |
| 查询 API | “查一下这个相机 API 的官方用法和使用条件。” |
| 验证布局 | “检查当前页面在手机和平板尺寸下的布局，标出内容截断和交互异常。” |
| 验证修复 | “用 HarmonyRun 在手机上复现搜索页的问题，修改后重复测试并确认修复。” |
| 运行回归 | “为登录流程编写测试用例并在模拟器上执行，给我失败截图和报告。” |
| 做一多适配 | “检查这个页面在折叠屏展开后布局是否合理，并完成适配。” |

也可以直接指定 Skill，例如：“使用 `$harmonyrun` 测试当前应用”。
