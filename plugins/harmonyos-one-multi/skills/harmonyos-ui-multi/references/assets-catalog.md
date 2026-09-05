# UI 代码资产目录

`assets/` 包含 24 个 ArkTS 示例。资产用于复用稳定写法，不是整套复制模板；先确认工程已有能力，再选择解决当前问题所需的最小文件。

## 当前验证状态

| 检查 | 结果 |
|---|---|
| API 22 最小工程编译 | 历史基线资产 0 ERROR；新增 Tabs、入口页注册与 displayPriority 价值分级资产待接入 DevEco 编译图复验 |
| 真实设备行为 | 未统一验证，接入业务后必须按目标形态重验 |

WARN 主要来自 `display.*` 等系统 API。复制到业务工程时，按项目异常处理约定补充 `try/catch` 和降级；不要因为资产能编译就省略运行态兜底。

## 资产选择

| 目录 | 文件 | 适用问题 |
|---|---|---|
| `size-layout/` | `BreakpointSystem.ets` | 标准 V2 断点实现：当前窗口初始化、尺寸/DPI 监听、可观察状态与同引用注销 |
| | `BreakpointEntryRegistration.ets` | 将标准断点系统合并进 loadContent 入口页的唯一注册/注销示例 |
| | `ResponsiveTabsExample.ets` | 普通页面 sm/md 底部栏与 lg/xl 左侧栏的完整 Tabs 结构示例；五属性双向恢复、不覆盖正文；LG 页签项上下 margin 参考 LAYOUT-07 |
| | `SystemBreakpointExample.ets` | V1/AppStorage 工程的系统断点消费示例；不得与 BreakpointSystem 并存 |
| | `WindowSizeChangeListener.ets` | 需要防抖且成对注销的窗口尺寸监听 |
| | `GridRowBreakpoints.ets`、`GridColOffset.ets`、`GridRowExample.ets` | 栅格断点、span/offset 限宽和完整页面示例 |
| | `SplitNavTwoColumn.ets` | 列表/详情双栏导航 |
| | `SplitNavThreeColumn.ets` | 侧栏 + 导航 + 内容三栏结构 |
| | `list-scroll-extension-avoid-truncation.ets` | 列表延伸避免内容截断 |
| | `row-displaypriority-truncation.ets` | 空间不足时按优先级隐藏 |
| | `row-displaypriority-value-graded.ets` | 按业务价值分级减少内容：命名权重常量、组容器整组显隐、关键项 `flexShrink(0)` |
| | `track-displaypriority-prefix.ets` | 顺序前缀型（进度条/流程条）逐项递减权重：断点可落档中间、末档项并入基础档同权、连接符 `min(前后权重)` 不残留孤立箭头 |
| | `row-flexshrink-text-ellipsis.ets` | 文本收缩和省略 |
| `window-form/` | `SplitScreenAbility.ets`、`SplitScreenMainPage.ets`、`SplitScreenDetailPage.ets` | 应用内分屏完整链路 |
| `fold-form/` | `CreaseAvoidance.ets` | 折痕几何读取与上下分区避让 |
| | `HoverStateUtil.ets` | 悬停状态、折痕几何和监听生命周期 |
| `avoid-area/` | `CutoutAvoidanceManager.ets` | 挖孔/系统栏四方向动态避让 |
| | `KeyboardAvoidanceList.ets` | List 页面软键盘避让，优先方案 |
| | `KeyboardAvoidanceScroll.ets` | 非 List 表单的 Scroll 避让 |
| `orientation/` | `OrientationDetector.ets` | 自然方向与主窗口方向监听；显式区分跟随桌面、尊重旋转锁和忽略旋转锁，不用于按 SM 断点推断设备形态 |

## 复用规则

1. `BreakpointSystem.ets` 与唯一入口注册是断点驱动布局的必备条件。工程已有正确实现时直接复用，不要并存第二套断点、窗口或监听体系；缺失时先补齐再继续页面修改。
2. 断点基础设施只在工程缺失时采用 `BreakpointSystem.ets`，并按 `BreakpointEntryRegistration.ets` 合并进 `loadContent` 加载的入口页；全工程只允许一个生产注册点。V1 工程可参考 `SystemBreakpointExample.ets` 的 AppStorage 消费方式，但不得并存两套监听。具体列数和布局仍按工程设计决定。
3. 复制资产后接入真实调用链再运行 `devecocli build`；未被 import 或注册的文件不算编译验证。
4. 监听器必须成对注册/注销，并使用相同回调引用。
5. 带 `@Entry` 的示例只用于理解和最小验证；接入业务时提取组件/逻辑，不新增无用入口页。
6. 公共资产修改要列出受影响页面，并对这些页面执行回归。

## 新增资产门槛

新增 `.ets` 前确认它解决的是重复出现的问题，而不是单工程特例。资产必须：

- 接入最小工程编译图并通过 `devecocli build`；
- 与域文档和已有资产不冲突；
- 在文件头说明使用边界和必要的释放/降级要求；
- 至少在一个真实目标形态或可复现样例上留下行为证据。
