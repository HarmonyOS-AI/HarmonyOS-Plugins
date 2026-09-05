# 窗口与方向

`module.json5` 的 Ability `orientation` 是基础能力边界；若固定为 portrait/landscape，Flutter `SystemChrome.setPreferredOrientations` 不能突破。需要应用内切换时先设为支持自动旋转，并在离开临时锁定页面时恢复。

自由多窗检测按目标 API 使用系统能力。自由窗沉浸式不要直接套全屏窗口 API，应处理窗口装饰可见性与标题按钮安全区。窗口、方向或 Ability 配置变化必须通过重装或可靠的原生部署流程验证，不能只 hot reload。
