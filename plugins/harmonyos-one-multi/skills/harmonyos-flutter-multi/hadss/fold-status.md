# HADSS 折叠状态

使用 `AvoidAreaApi` 获取 FoldStatus 与当前窗口避让区，并监听变化；布局断点由 `BreakpointManager` 提供。二者是不同信号：FoldStatus 决定形态语义，断点决定可用布局，避免用任一信号完全替代另一信号。

对外统一输出稳定的业务无关模型，页面不直接散落 HADSS 枚举判断。监听注册、窗口切换和销毁必须成对处理。
