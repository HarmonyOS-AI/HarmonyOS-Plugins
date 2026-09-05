# HADSS 悬停布局

简单 Stack 场景优先 `FolderStack`，通过稳定 `ValueKey` 和 `upperItems` 指定进入上半区的内容；固定三态布局使用 `FoldSplitContainer` 的 folded/expanded/hover options；只有复杂编排才自定义。

展示区与操作区共享原业务状态。命中悬停时必须继续读取 [crease-avoidance.md](crease-avoidance.md)，确认铰链区域无内容和交互。
