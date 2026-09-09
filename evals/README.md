# Skill 评测

`HarmonyOS-Plugins` 的 `evals/` 保存针对生产插件和 Skill 的版本化评测资产，但不属于任何插件安装包。
Skill 级目录镜像被测目标：

```text
evals/plugins/<plugin-name>/skills/<skill-name>/
├── eval.config.json
├── run.mjs
├── tests/
├── cases/       # 有声明式行为用例时创建
├── fixtures/    # 有最小输入工程或数据时创建
├── graders/     # 有独立评分逻辑时创建
└── expected/    # 只保存稳定、可审查的黄金结果
```

插件整体的评测放在 `evals/plugins/<plugin-name>/`，同样使用 `eval.config.json` 和 `run.mjs`。
当前注册了五个目标：

| 目标目录（相对 `evals/plugins/`） | 覆盖 |
| --- | --- |
| `harmonyos-test-toolkit/skills/harmonyos-live-preview/` | 驱动命令、多设备、桥接会话、尺寸解析与运行时 resize；详见 [live-preview 评测](plugins/harmonyos-test-toolkit/skills/harmonyos-live-preview/README.md)。 |
| `harmonyos-one-multi/` | 230 个迁移文件的 SHA-256、五个 Skill 标识、隔离目录中的 OpenCode V1 加载和 npm 包内容。 |
| `harmonyos-one-multi/skills/harmonyos-workflow-multi/` | 一多工作流 Python 契约测试。 |
| `harmonyos-one-multi/skills/harmonyos-ui-multi/` | ArkUI 一多适配 Python 契约测试。 |
| `harmonyos-one-multi/skills/harmonyos-camera-multi/` | 相机一多适配 Python 契约测试。 |

只创建实际需要的目录，不保留空目录。依赖方向固定为 `evals -> plugins`，生产 Skill 不得读取或调用
`evals/`。确定性断言优先于模型评分；涉及宿主安装行为的套件应从临时插件缓存运行，而不是依赖源码目录外的文件。

在仓库根目录安装 npm 依赖，并确保 Node.js 22+ 和 Python 3.12+（`python3`）可用后，
运行全部已注册评测：

```bash
npm run evals
```

`scripts/run-evals.mjs` 递归发现全部 `eval.config.json`，按路径排序后串行执行同目录的
`run.mjs`，任何目标失败即停止。新增评测只需按此约定放置配置和入口，无需修改根运行器。

单独运行某个目标：

```bash
npm run evals:live-preview
node evals/plugins/harmonyos-one-multi/run.mjs
node evals/plugins/harmonyos-one-multi/skills/harmonyos-workflow-multi/run.mjs
```

插件级运行器只执行本级配置声明的套件；使用 `npm run evals` 才会递归运行其下的 Skill 目标。
需要同时检查跨宿主适配器和生成清单时，运行 `npm run test:all`。

生成的模型输出、截图、日志、HTML 报告和临时工程写入 `.eval-runs/`、`.eval-cache/` 或系统临时目录，
不进入版本控制。
