# harmonyos-live-preview 评测

这些评测覆盖 `plugins/harmonyos-ui-toolkit/skills/harmonyos-live-preview` 的确定性行为。
`tests/mock-bridge.mjs` 模拟桥接层 HTTP 接口，并复用生产代码中的 `input.mjs` 和
`device-profile.mjs`，因此不需要 HarmonyOS 工具链。测试由 `run.mjs` 串行执行，避免固定端口冲突。

| 脚本 | 覆盖 |
|---|---|
| `tests/test-drive.mjs` | `drive.mjs` 全部命令（对 mock bridge） |
| `tests/test-multidevice.mjs` | `--device` 定向、`shot --all`、多设备状态 |
| `tests/test-bridge-real.mjs` | 真实 `bridge.mjs` + WebSocket 假引擎：per-device session、重连 generation |
| `tests/test-resize.mjs` | 自定义尺寸：规格解析、几何校验、设备配置生成和 `drive.mjs resize` |

运行全部评测：

```bash
npm run evals:live-preview
```

`eval.config.json` 记录被测插件、Skill 和套件入口。需要真实工具链的端到端验证（自定义启动尺寸改变帧几何、
运行时 resize 收敛、重建后尺寸被重放）仍使用 `.skill-workspaces/harmonyos-live-preview/PreviewProbe/`
本地工程手动执行。该工程含构建缓存，不属于版本化评测资产。
