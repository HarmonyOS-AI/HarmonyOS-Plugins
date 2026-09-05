# 窗口旋转策略参考

这是 `window.Orientation` 的离线语义快照，用于选型和回归，不用于固化某句提示词的答案。

- 官方来源：[窗口旋转](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/window-rotation)
- 同步日期：2026-08-22
- 冲突规则：本参考与官方来源冲突时，以官方来源为准并更新本参考及其评测。

## 选型维度

选择枚举前同时确认：

- 需求是否只是“与桌面一致”：先按 `FOLLOW_DESKTOP` 逐形态对照桌面行为（见“容易混淆的边界”），
  一致就直接选它，不再进入其他枚举选型。
- 允许的显示方向：固定单向、仅横向、仅竖向或四向。
- 是否跟随传感器，以及调用时是否需要立即转到指定方向。
- 是否受控制中心旋转锁控制。
- 设备形态是否会改变系统允许的方向。
- 主窗口是否全屏；分屏、悬浮窗、自由多窗等场景可能忽略旋转策略。

## 18 个 Orientation 枚举

| 类别 | 枚举 | 值 | 语义 |
|---|---|---:|---|
| 其他 | `UNSPECIFIED` | 0 | 未定义方向模式，由系统判定；未配置且运行时未设置时的默认策略 |
| 固定 | `PORTRAIT` | 1 | 固定竖屏 |
| 固定 | `LANDSCAPE` | 2 | 固定横屏 |
| 固定 | `PORTRAIT_INVERTED` | 3 | 固定反向竖屏 |
| 固定 | `LANDSCAPE_INVERTED` | 4 | 固定反向横屏 |
| 自动 | `AUTO_ROTATION` | 5 | 跟随传感器四向自动旋转，不受控制中心旋转锁限制 |
| 自动 | `AUTO_ROTATION_PORTRAIT` | 6 | 跟随传感器，仅在竖屏与反向竖屏间自动旋转 |
| 自动 | `AUTO_ROTATION_LANDSCAPE` | 7 | 跟随传感器，仅在横屏与反向横屏间自动旋转 |
| 自动 | `AUTO_ROTATION_RESTRICTED` | 8 | 跟随传感器四向自动旋转，受控制中心旋转锁控制 |
| 自动 | `AUTO_ROTATION_PORTRAIT_RESTRICTED` | 9 | 仅在两个竖向方向间自动旋转，受控制中心旋转锁控制 |
| 自动 | `AUTO_ROTATION_LANDSCAPE_RESTRICTED` | 10 | 仅在两个横向方向间自动旋转，受控制中心旋转锁控制 |
| 其他 | `LOCKED` | 11 | 锁定模式；被其他应用拉起时通常保持前一个应用的方向，不等于永久锁定当前角度 |
| 自动 | `AUTO_ROTATION_UNSPECIFIED` | 12 | 自动旋转且受旋转锁控制，可旋转方向由系统和产品形态判定 |
| 临时 | `USER_ROTATION_PORTRAIT` | 13 | 调用时先转到竖屏，之后按传感器、旋转锁和系统允许方向自动旋转 |
| 临时 | `USER_ROTATION_LANDSCAPE` | 14 | 调用时先转到横屏，之后按传感器、旋转锁和系统允许方向自动旋转 |
| 临时 | `USER_ROTATION_PORTRAIT_INVERTED` | 15 | 调用时先转到反向竖屏，之后按传感器、旋转锁和系统允许方向自动旋转 |
| 临时 | `USER_ROTATION_LANDSCAPE_INVERTED` | 16 | 调用时先转到反向横屏，之后按传感器、旋转锁和系统允许方向自动旋转 |
| 其他 | `FOLLOW_DESKTOP` | 17 | 跟随当前设备桌面的旋转模式 |

## 容易混淆的边界

- `AUTO_ROTATION_RESTRICTED(8)` 始终允许四向自动旋转，只是受旋转锁控制。
- `AUTO_ROTATION_UNSPECIFIED(12)` 的允许方向还受产品形态判定：旋转锁关闭时，直板机或类直板
  形态通常为三向，平板或类平板形态通常为四向。
- 旋转锁打开时，8 和 12 在直板机或类直板形态都不能锁定在横屏；平板或类平板形态可以。
- `USER_ROTATION_*` 会先临时转到指定方向，之后再按传感器、旋转锁和系统允许方向运行。
- `USER_ROTATION_PORTRAIT_INVERTED(15)` 在直板机或类直板形态不能临时转到反向竖屏。
- `UNSPECIFIED(0)` 不是任何其他策略的同义词，也不是通用恢复值。
- `FOLLOW_DESKTOP(17)` 的选型方法是**逐形态对照桌面**：直板机、折叠态与外屏的桌面固定竖屏；
  折叠展开、悬停与平板的桌面随传感器旋转且受旋转锁控制。需求目标是各形态行为与桌面一致时
  选 `FOLLOW_DESKTOP`，在入口 `module.json5` 的
  ability 上声明 `"orientation": "follow_desktop"`（启动即生效，`getPreferredOrientation()`
  读到 17），不要在首页运行时 `setPreferredOrientation` 分叉覆盖。仅当某些形态的要求与桌面
  不一致时才改用运行时枚举分叉；不能不做对照就凭提示词关键词直接套用或直接排除。

## 接口行为限制

- 旋转策略针对主窗口生效；主窗口全屏时通常立即重新评估方向。
- 主窗口非全屏时，设置策略可以成功但不会立即改变方向，回到全屏后再生效。
- 分屏、智慧多窗悬浮窗、多任务、应用后台、自由多窗等场景可能忽略策略；调用成功不代表已旋转。
- TV 等无传感器设备可以调用接口，但实际方向不会变化。
- `module.json5` 的 `orientation` 与运行时 `setPreferredOrientation()` 使用相同的策略语义。
