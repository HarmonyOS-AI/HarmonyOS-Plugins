# Grid 与 DisplayPriority 采用指南

仅在工程已安装相关包，或需要借鉴官方社区组件的模型时读取。默认采用等级为 `PATTERN_ONLY`，除非锁定版本和目标设备已通过准入验证。

## Grid 模型

可以借鉴：

- 总列数 `columns`；
- 子项 `span/offset/order`；
- 横纵 `gutter`；
- window reference 与 component reference；
- 断点值向更小断点回退。

不能直接复制：

- RC 版本内部 Yoga 补偿公式；
- 未验证的响应式 `order` 实现；
- 对负数、零、越界 span/offset 没有明确行为的代码；
- 由物理 screen 驱动的 component grid。

component reference 必须由容器自身 `onLayout` 驱动。组件内部需要测量时要组合调用方的 `onLayout`，不能让 props spread 覆盖内部回调。

## DisplayPriority 模型

空间是否足够应来自实际容器和 children 测量，不从静态 `style.width` 推断。以下变化后需要重新计算：

- 容器宽高；
- children 数量和文本；
- fontScale、字体和本地化；
- gap、padding、方向和业务状态。

同优先级组件可以成组显隐，但提交、返回、删除等关键操作必须通过折行、滚动或 overflow menu 保持可达。

## 采用检查

| 检查项 | 通过条件 |
| --- | --- |
| public API | 导入来自包公开入口，不使用 `/src` 深路径 |
| breakpoint | 与项目唯一 source 对齐 |
| component width | 嵌套窄容器使用自身 onLayout |
| 边界值 | 覆盖负数、0、越界 span/offset、超大 gutter |
| 状态 | 列数变化不丢 selectedId、route、scroll anchor |
| RTL/a11y | 顺序、逻辑边和无障碍树可解释 |
| 版本 | 类型、JS、HAR 和运行设备属于同一兼容线 |

## 验证矩阵

动态 children、长文本、大字体、LTR/RTL、嵌套容器、空列表、断点临界值、窄→宽→窄。Grid 最终宽度必须能由容器可用宽度、列数和 gutter 公式解释。
