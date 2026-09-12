# 输入代码层与能力边界

## 先判输入模式

在分析布局根因前，先建立源码清单并输出一种模式：

| 模式 | 可验证证据 | 不足时如何处理 |
| --- | --- | --- |
| `H5_ONLY` | `.html`、样式文件、Web JS/TS、Vue/React/Svelte 组件、Web 构建入口 | 只改 Web；需要原生能力时生成 ArkTS 交接项 |
| `ARKTS_ONLY` | `.ets`、HarmonyOS 模块配置、ArkTS Web 组件/控制器、窗口监听或桥接注册 | 只改 ArkTS；需要 DOM/REM 消费时生成 H5 交接项 |
| `HYBRID` | 上述两类源码及其调用关系均可定位 | 联动审计；跨层契约变化同步修改两端 |
| `INSUFFICIENT` | 没有相关源码，或片段不足以定位写入点/调用点 | 不写补丁；列出需要补充的入口、调用方和验证信息 |

不要把普通 `.ts` 自动认作 ArkTS。只有文件位于 HarmonyOS 模块，或包含 ArkTS 组件语法、HarmonyOS Kit 导入、`Web`/控制器等明确上下文时，才将其归为 ArkTS 侧。

## 层级所有权

| 责任 | H5 | ArkTS | 共享契约 |
| --- | --- | --- | --- |
| Web 组件外部布局 | 不控制 ArkUI 父容器 | 设置 Web 组件及父容器的尺寸、约束和可用区域 | 必要时提供容器变化信号 |
| H5 内部布局与断点 | CSS、DOM、容器和阅读顺序 | 不按设备替 H5 选择内部页面布局 | 无 |
| REM | 读取 `documentElement.clientWidth`，计算并写根字号 | 最多发送“窗口已变化”信号 | 触发时序，不共享两套 REM 公式 |
| 响应式媒体 | 根据 DOM slot、DPR、媒体条件选择候选并控制裁切 | 不按设备替网页选择图片/视频 | 仅资源 URL/鉴权确需原生时共享数据契约 |
| Web 可见尺寸 | viewport、container、`resize`/`ResizeObserver` | 不把物理屏幕尺寸强灌为 CSS 尺寸 | 可携带诊断元数据 |
| 系统语义 | 消费确有业务需要的数据 | 折叠状态、窗口生命周期、系统事件 | 事件名、字段、版本与序号 |
| 生命周期 | listener ready、页面卸载与状态恢复 | Web 组件创建、页面加载、桥接注册 | 首次状态、重连和错误策略 |

## 各模式的修改规则

### `H5_ONLY`

- 可修改 HTML、CSS、Web JS/TS、框架组件和必要 Web 构建配置。
- 优先使用 Web 标准尺寸信号；已有原生事件的消费代码可修，但不得假设未提供的 ArkTS 一定会发送某字段。
- 如果完成依赖原生侧，输出 `handoff_required`：生产者位置、事件/API 名、必需字段、触发时机和验收方式。
- 完成状态写成“Web 侧已完成；原生生产端待接入”，不得写“问题已完全修复”。

### `ARKTS_ONLY`

- 可修改 `.ets`、相关 HarmonyOS 配置、Web 组件/控制器、窗口监听和现有桥接实现。
- 检查 Web 组件及其 ArkUI 父容器是否使用了过时、固定或无法随窗口更新的尺寸约束；外部容器布局问题可以在 ArkTS 侧独立闭环。
- 复用项目已有桥接，不凭空创造 `window.someFunction`、DOM 节点或前端事件总线。
- ArkTS 负责稳定传递信号，不负责决定 CSS 断点或计算 H5 根字号。
- 输出 H5 交接项，注明消费入口、如何读取当前 viewport、幂等更新和卸载要求。

### `HYBRID`

1. 同时检查“窗口 → ArkUI 父容器 → Web 组件”的外部尺寸链，以及“系统/窗口事件 → ArkTS 生产者 → 桥接 → H5 消费者 → DOM/CSS/REM”的事件链。
2. 写出当前契约与目标契约，再修改代码；字段重命名、类型变化或时序变化必须同步两端。
3. H5 用自身 layout viewport 完成最终布局计算；ArkTS 数据只补充 Web 不可获得的语义。
4. 处理首次状态：H5 未就绪时由原生保留最新状态，或 H5 就绪后主动拉取；沿用项目已有机制。
5. 如果根因证明只在一层，另一层可以零代码变更，但必须记录检查证据并验证契约未受影响。这仍属于联动处理，不是强行制造无意义改动。

## 源码审计顺序

1. 列出相关文件并按 H5、ArkTS、共享配置分类；确认输入模式和可编辑层。
2. Web 侧从构建/路由入口沿组件树定位布局、样式、REM 写入者和事件消费者。
3. ArkTS 侧从 Web 组件和控制器定位窗口监听、桥接注册、页面加载与事件生产者。
4. 搜索事件/API 名和载荷字段的所有生产与消费点，避免只改一处。
5. 记录首个错误约束，以及它属于布局、尺寸同步、桥接丢失还是生命周期时序。
6. 修改前确定最小文件集合和两端各自的验证命令。

## 复杂跨层任务的内部记录

需要跨层修改或交接时记录；简单单层修复不必生成空字段：

```yaml
input_mode: HYBRID
provided_layers: [h5, arkts]
editable_layers: [h5, arkts]
missing_counterpart: []
cross_layer_contract:
  changed: true
  producer: "ArkTS screen-change handler"
  consumer: "H5 onScreenChange listener"
  event_or_api: [onScreenChange]
  payload: [reason, sequence]
  timing: "listener ready 后发送首次状态；变化事件仅作重测量信号"
handoff_required: []
```

单端模式如果完成依赖对端，必须让 `missing_counterpart` 和 `handoff_required` 非空；如果纯 H5 或纯 ArkTS 修改已经闭环，则保持交接项为空，并写明对端为何不需要参与的证据。

## 完成条件

- 模式判定有文件或代码证据，未凭设备名猜测。
- 修改没有越过 `editable_layers`。
- ArkTS Web 组件外部约束能随目标窗口更新；H5 内部布局仍由 viewport/容器驱动，不由型号或物理屏幕驱动。
- 单端输入准确报告本端完成度和对端待办。
- 双端输入的事件名、字段、类型、初始化、变更与清理路径一致。
