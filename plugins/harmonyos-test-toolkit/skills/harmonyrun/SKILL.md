---
name: harmonyrun
description: Use HarmonyRun to test HarmonyOS / OpenHarmony apps on devices or emulators, reproduce UI issues, run test suites, and generate Hypium regression tests. 适用于鸿蒙设备 UI 操作、自动化测试及 HarmonyRun 安装排障。页面浏览器预览使用 harmonyos-live-preview。
---

# HarmonyRun UI 测试

## 准备

优先使用 PyPI 发布版。未安装时通过 pip 安装；仅在用户指定时使用源码版。

```bash
python -m pip install harmonyrun
harmonyrun --help
harmonyrun devices
```

需要兼容的 Python、hdc 和已开启调试的设备。命令不在 PATH 时使用安装环境的
`python -m harmonyrun`。安装、MCP 连接或模型配置有问题时读 [安装与连接](references/setup.md)。

## 执行

| 任务 | 做法 |
| --- | --- |
| 检查页面、点击输入、逐步复现问题 | 使用 HarmonyRun MCP，读 [设备操作](references/mcp-workflow.md) |
| 让 HarmonyRun 完成自然语言目标 | 使用 `harmonyrun run`，读 [运行测试](references/cli-testing.md) |
| 编写并运行测试套件、查看报告 | 使用 `harmonyrun test` / `view`，从 [套件示例](assets/smoke-suite.json) 开始，读 [运行测试](references/cli-testing.md) |
| 生成 Hypium 回归或使用远程设备 | 读 [运行测试](references/cli-testing.md) 中的对应段落 |

MCP 交互无需另外配置模型；`run` / `test` 需要 HarmonyRun 的模型配置和 API Key。
参数以已安装命令的帮助及工具定义为准；新增子命令先在 `--help` 的命令列表中确认。

使用用户指定的设备与应用包名，同一设备按顺序操作。根据实际 UI、截图和本次报告验证预期结果，
交付通过、失败、跳过项及证据位置；没有设备或尚未执行的用例说明为未运行。
