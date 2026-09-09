# 安装与连接

## pip 安装

使用 Python 3.11–3.13，从 [PyPI](https://pypi.org/project/harmonyrun/) 安装。已有兼容环境时直接运行
`python -m pip install harmonyrun`；需要升级时加 `--upgrade`。

需要独立环境时，macOS / Linux 可执行：

```bash
python3.13 -m venv .venv-harmonyrun
source .venv-harmonyrun/bin/activate
python -m pip install harmonyrun
```

Windows PowerShell：

```powershell
py -3.13 -m venv .venv-harmonyrun
.\.venv-harmonyrun\Scripts\python.exe -m pip install harmonyrun
```

## 连接设备

```bash
hdc list targets
harmonyrun mcp doctor
```

设备不可见时检查开发者模式、USB 调试授权和连接。找不到 hdc 时，将 `HARMONYRUN_HDC_PATH`
设为工具链中 hdc 可执行文件的绝对路径；进一步排查用 `harmonyrun doctor -d SERIAL`。

## MCP 找不到命令

在安装环境运行 `python -c "import sys; print(sys.executable)"` 获取解释器路径，
将客户端的 HarmonyRun MCP 配置改为该绝对路径，然后重连：

```json
{
  "mcpServers": {
    "harmonyrun": {
      "command": "/absolute/path/to/python",
      "args": ["-m", "harmonyrun", "mcp", "serve"]
    }
  }
}
```

只导入 Skill 的客户端也可用此配置连接。让客户端启动 MCP 服务，单独在终端运行服务不会建立客户端连接。

## 运行自然语言任务与套件

复用 `~/.config/harmonyrun/config.yaml` 中的模型配置，或用 `-c /absolute/path/config.yaml`
指定配置文件。API Key 放在环境变量或用户 `.env` 中。
`run` 临时覆盖模型时，`--provider` 与 `--model` 要同时提供；`test` 通过配置文件设置模型。
