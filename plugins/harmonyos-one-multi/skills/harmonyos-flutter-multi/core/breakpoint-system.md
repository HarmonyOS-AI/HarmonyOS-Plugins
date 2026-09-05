# 统一断点体系

| 断点 | 范围（逻辑像素/vp） |
| --- | --- |
| xs | `< 320` |
| sm | `320–599` |
| md | `600–839` |
| lg | `840–1439` |
| xl | `>= 1440` |

高度补充断点：`sm < 600`、`md 600–839`、`lg >= 840`。横屏键盘、外屏和悬浮小窗必须额外依据可用高度决策。工程应只有一个断点映射源，不在页面内散落阈值。

## 宽高比断点（弹幕等场景，基于 h/w 比值）

| 断点 | 宽高比 (h/w) |
| --- | --- |
| sm | `< 0.8`（横屏/扁宽） |
| md | `0.8 – 1.2`（近方形） |
| lg | `>= 1.2`（竖屏/窄长） |

## 设备类型分类（宽度 + 宽高比）

| 设备类型 | 宽度阈值 | 宽高比条件 | 默认列数 |
| --- | --- | --- | --- |
| mobile | `< 600` | 任意 | 1 |
| tablet | `600 – 1199` | 任意 | 3 |
| wide | `1200 – 1599` | 任意 | 4 |
| ultraWide | `>= 1600` | `> 2.0` | 4 |

## 通用断点-值映射模式

推荐 3 值映射 5 断点（与 ArkUI `WidthBreakpointType` 一致）：

```dart
static T getValue<T>(WidthBreakpoint bp, T smValue, T mdValue, T lgValue) {
  switch (bp) {
    case WidthBreakpoint.xs: return smValue;  // xs 与 sm 共享
    case WidthBreakpoint.sm: return smValue;
    case WidthBreakpoint.md: return mdValue;
    case WidthBreakpoint.lg: return lgValue;
    case WidthBreakpoint.xl: return lgValue;  // lg 与 xl 共享
  }
}
```

## 布局方向切换阈值速查

| 宽度阈值 | 布局切换 |
| --- | --- |
| 500vp | Row ↔ SingleChildScrollView |
| 600vp | 2列 ↔ 4列网格；是否显示侧边内容 |
| 660vp | 是否显示浮动内容 |
| 760vp | 横向分栏 ↔ 纵向堆叠 |
| 900vp | 页面内边距 16 ↔ 24 |
| aspectRatio >= 1.2 | 视频侧面板 ↔ 底部浮层 |

完整断点/DPI 策略详册见 [../references/dpi-guide.md](../references/dpi-guide.md)。
