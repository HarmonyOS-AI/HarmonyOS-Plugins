# 原生 Flutter UX 修复模式

- 表单/设置/空态：改为可滚结构，保留最小高度而非锁死视口。
- Sheet/日历：`isScrollControlled`，内部可滚，最大高度钳制到约 `0.9H`。
- 地图条件卡：限制最大高度并保证地图仍可交互。
- 固定宽 Row：使用 `Expanded/Flexible` 和 `double.infinity`。
- 相机/视频卡：预览区使用剩余空间，尺寸变化后更新 surface。
- 设计缩放：弹层垂直尺寸限制 scale 上界；字体保持可访问性。
- `DraggableScrollableSheet`：每次更新保证 `min <= initial <= max`，无有效底部高度时跳过。
- 亚像素溢出：避免精确吃满浮点高度，给可滚内容留容差。

系统信箱不在此修复，转 `ohos-platform/scbcompatible-letterbox.md`。

各模式完整代码与反模式（P-SCROLL-FORM、P-WIDE-FILL 等）见 [../references/pura-x-patterns.md](../references/pura-x-patterns.md)；场景 ID 映射见 [../scenarios/ux-catalog.md](../scenarios/ux-catalog.md)。
