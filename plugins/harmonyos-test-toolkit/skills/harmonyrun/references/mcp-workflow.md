# 设备操作

使用客户端中 **HarmonyRun** 服务提供的工具，参数以实际工具定义为准。

```text
list_devices()
connect_device(serial="目标设备序列号")
open_app(bundle="目标应用包名")
get_ui_state()
```

`open_app` 使用 bundleName，可从工程 `AppScope/app.json5` 或设备观察中获取；每次会话连接一台设备。

## 定位与交互

- 优先用最新 `get_ui_state` 中的索引调用 `tap_element(index)`；导航、滚动或页面重排后重新定位。
- 需要视觉判断时调用 `get_screenshot(annotated=true)`；保存无标注证据用 `annotated=false`。
- 找不到语义节点时再用坐标操作。`tap`、`swipe`、`long_press` 使用当前屏幕的**像素坐标**。
- 输入时传当前输入框的 `element_index`，先聚焦再输入；`clear=true` 替换已有内容。
- 旋转或折叠后重新获取状态与截图，不复用旧坐标；不支持折叠的设备记为跳过。

```text
input_text(text="测试内容", element_index=当前输入框索引, clear=true)
get_ui_state()
get_recent_events()
```

## 验证与排障

操作后检查预期文案、控件值、前台应用或截图。`ok=true` 只表示动作调用完成，
`page_signature` 变化与否不能单独判断业务结果。异步页面可有界复查，重复操作无进展时重新定位或换策略。

弹窗、toast 或输入异常时查看 `get_recent_events()`；它返回 `{serial, events}`，读取后会消费事件。
结构看不清时用 `get_ui_state(raw=true)` 查看原始树；原始树没有可用于点击的索引，操作前回到普通视图定位。
若状态返回的 `structuredContent` 包在 `result` 中，读取内层对象。

结束时调用 `disconnect_device()` 释放会话。CLI 的 `harmonyrun disconnect` 不能代替它。
