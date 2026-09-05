<!--
Merged from flutter-pura-x-max-ux-20260731/patterns.md.
Role: full P-* code fix patterns for UX-01..UX-24, shared by both implementation
tracks; routed from scenarios/ux-catalog.md and ux-fix-patterns.md of both tracks.
Link mapping: the "SKILL.md UX catalog" referenced below -> scenarios/ux-catalog.md;
assets/breakpoint_listener.dart and friends -> examples/hadss/.
-->
# Flutter × Pura X Max — 修复模式

按 `SKILL.md` 问题目录中的模式 ID 选用。示例可按项目 Widget 命名替换，保留结构约束。

## 共用断点

```dart
class FoldBreakpoints {
  static bool isShort(BuildContext c) => MediaQuery.sizeOf(c).height < 500;
  static bool isWide(BuildContext c) => MediaQuery.sizeOf(c).width >= 600;
  static bool isCompact(BuildContext c) =>
      MediaQuery.sizeOf(c).shortestSide < 600;
}
```

---

## P-SCROLL-FORM（UX-01 登录/表单叠字）

```dart
Scaffold(
  resizeToAvoidBottomInset: true,
  body: SafeArea(
    child: LayoutBuilder(
      builder: (context, constraints) {
        final short = constraints.maxHeight < 500;
        return SingleChildScrollView(
          padding: EdgeInsets.only(
            left: 16,
            right: 16,
            bottom: MediaQuery.viewInsetsOf(context).bottom + 16,
          ),
          child: ConstrainedBox(
            constraints: BoxConstraints(minHeight: constraints.maxHeight),
            child: IntrinsicHeight(
              child: Column(
                children: [
                  SizedBox(height: short ? 8 : 24),
                  // 标题：short 时缩小字号/隐藏副文案
                  // TextFields + 主按钮
                ],
              ),
            ),
          ),
        );
      },
    ),
  ),
);
```

**检查：** 勿关闭 `resizeToAvoidBottomInset`；勿固定登录区高度等于屏幕高。

---

## P-WIDE-FILL（UX-02 横屏两侧留白）

```dart
final width = MediaQuery.sizeOf(context).width;
final isWide = width >= 600;

// ❌ Center(child: SizedBox(width: 400, child: page))
// ✅ 宽屏分栏或全宽
Widget body = isWide
    ? Row(
        children: [
          SizedBox(width: width * 0.28, child: sideNav),
          Expanded(child: mainContent),
        ],
      )
    : mainContent;
```

**检查：** 主页/列表/设备页默认全宽；仅文章类单列可 `ConstrainedBox(maxWidth: 720)` 居中。

---

## P-SHEET-SCROLL（UX-03 弹窗/半屏截断）

```dart
showModalBottomSheet(
  context: context,
  isScrollControlled: true,
  builder: (context) {
    final h = MediaQuery.sizeOf(context).height;
    return ConstrainedBox(
      constraints: BoxConstraints(maxHeight: h * 0.9),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const ListTile(title: Text('标题')),
          Flexible(
            child: ListView.builder(
              itemCount: items.length,
              itemBuilder: (_, i) => items[i],
            ),
          ),
        ],
      ),
    );
  },
);
```

**检查：** Dialog / `showModalBottomSheet` / 自定义半屏均适用；内部禁止无滚动长 Column。

---

## P-HOME-SCROLL（UX-04 主页截断不可滑）

```dart
Scaffold(
  body: CustomScrollView(
    slivers: [
      SliverToBoxAdapter(child: header),
      // SliverGrid / SliverList 内容
      SliverToBoxAdapter(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: FilledButton(
            onPressed: onPrimaryAction,
            child: const Text('添加设备'),
          ),
        ),
      ),
      SliverPadding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.paddingOf(context).bottom + kBottomNavHeight,
        ),
      ),
    ],
  ),
);
```

**外屏增强（可选）：** 滚动时渐进隐藏 AppBar/Tab，释放矮屏高度。

---

## P-CAMERA-COVER（UX-05 相机/扫码未铺满）

```dart
Scaffold(
  backgroundColor: Colors.black,
  body: LayoutBuilder(
    builder: (context, constraints) {
      return Stack(
        fit: StackFit.expand,
        children: [
          FittedBox(
            fit: BoxFit.cover,
            child: SizedBox(
              width: previewSize.width,
              height: previewSize.height,
              child: CameraPreview(controller),
            ),
          ),
          // 扫码框 / 关闭按钮叠层；勿用大块 SafeArea 包住整个 Preview
        ],
      );
    },
  ),
);
```

**检查：**

- **横→竖 / 竖→横必须重建：** 监听尺寸变化，清空缓存的 previewSize，重新 bind；否则出现「转回竖屏未铺满」。
- 勿用大块 `SafeArea` 包裹整个 `CameraPreview`。
- HarmonyOS 原生预览：旋转/折展后重建 Surface；外屏可能仅前置可用。

---

## P-SETTINGS-LIST（UX-06 设置页底部截断）

```dart
Scaffold(
  appBar: AppBar(title: const Text('设置')),
  body: ListView(
    children: [
      // SwitchListTile / ListTile ...
      SizedBox(height: MediaQuery.paddingOf(context).bottom + 24),
    ],
  ),
);
```

**检查：** 禁止长设置用不可滚 `Column`；横屏必测滚到底。

---

## P-SAFE-CUTOUT（UX-07 挖孔/状态栏遮挡）

原则：**背景可沉浸延伸；文字与可点控件必须避让。**

```dart
final pad = MediaQuery.paddingOf(context);
// 顶栏：外层吃 padding，内层固定内容高（避免 padding 挤掉文字）
Column(
  children: [
    Padding(
      padding: EdgeInsets.only(top: pad.top, left: pad.left, right: pad.right),
      child: SizedBox(
        height: 48,
        child: Row(children: [/* 返回 / 标题 */]),
      ),
    ),
    Expanded(child: content),
  ],
);
```

横屏挖孔常在左/右：四边都要看 `MediaQuery.padding`，不要只加 `top`。

若页面在 WebView/H5 内，原生须把 insets 注入 H5（`env(safe-area-inset-*)` + Bridge CSS 变量）。

---

## P-STICKY-TOP（UX-08 筛选/吸顶栏顶部截断）

```dart
// ❌ SizedBox(height: 44, child: Padding(padding: EdgeInsets.only(top: pad.top), ...))
// ✅ 外层吃安全区，内层固定内容高；横屏筛选项横向滚
Column(
  mainAxisSize: MainAxisSize.min,
  children: [
    SizedBox(height: MediaQuery.paddingOf(context).top),
    SizedBox(
      height: 44,
      child: ListView(
        scrollDirection: Axis.horizontal,
        children: chips,
      ),
    ),
  ],
);
```

---

## P-HOVER-SPLIT（UX-09 悬停态）

半折时：上（或折痕一侧）展示预览/视频，下（或较大侧）放操作控件；交互控件勿压在折痕。

```dart
final features = MediaQuery.displayFeaturesOf(context);
final hinge = features.where((f) => f.type == DisplayFeatureType.hinge);
// 有 hinge：用 CustomMultiChildLayout / 两个 Expanded 分区
// 无 Flutter hinge 数据时：MethodChannel 读 foldStatus == HALF_FOLDED + 窗口高宽比兜底
if (isHalfFolded) {
  return Column(
    children: [
      Expanded(flex: 1, child: previewPane),
      Expanded(flex: 1, child: controlsPane),
    ],
  );
}
```

视频/通话/拍摄类优先适配；普通列表页可降级为可滚动单栏。

---

## P-MULTIWINDOW（UX-10 分屏/悬浮窗）

按**当前窗口**高度处理，与外屏矮屏同一套滚动策略：

```dart
final h = MediaQuery.sizeOf(context).height;
final compactWindow = h < 500 || MediaQuery.sizeOf(context).width < 400;
// compactWindow → 强制可滚、隐藏次要模块、弹窗 maxHeight: h * 0.95
```

---

## P-NO-LETTERBOX（UX-11 展开黑边 / 蓝底信箱）

**先分流：** 系统蓝/紫渐变底 + 三点把手 / WMS 有 `SCBCompatible` → 本模式；窗口已满仅内容窄 → `P-WIDE-FILL`。

完整命令与分层修复见 [references/ux11-scbcompatible-letterbox.md](../ohos-platform/scbcompatible-letterbox.md)。

### Flutter 方向（必要但不充分）

```dart
// ❌ 全局仅 portraitUp，或 OH 上 portraitUp+L+R → bitmask 0x0B → Orientation.LOCKED
// ✅ OHOS：启动可不调用 setPreferredOrientations；其它平台可四向（含 portraitDown）
// ✅ 单页临时锁定，dispose 后 OHOS 恢复建议 no-op，交给原生 follow_desktop / auto_rotation
```

### OHOS 窗口（主路径）

1. `module.json5`：`deviceTypes` 含 `tablet`；`supportWindowMode: ["fullscreen"]`（无需分屏时）
2. `windowStage.setSupportedWindowModes([FULL_SCREEN])`
3. `setWindowLayoutFullScreen(true)` + `resetAspectRatio` + `maximize(ENTER_IMMERSIVE)`
4. 仍 letterbox → `resize(屏宽, 屏高)`；折展后延迟重试
5. **卸载重装**或提高 `versionCode`；用 WMS 验收应用宽≈屏宽

### 验收

```bash
hdc shell "hidumper -s WindowManagerService -a '-a'"  # 本应用窗宽 vs 屏宽；SCBCompatible
```

---

## P-OUTER-DENSE（UX-12 外屏降密度）

```dart
if (FoldBreakpoints.isShort(context)) {
  // 隐藏营销 Banner / 次要入口；缩小间距；主操作置顶
  // 可选：滚动时隐藏 AppBar + BottomNav
}
```

---

## P-NAV-ADAPT（UX-13 导航自适应）

```dart
final wide = FoldBreakpoints.isWide(context);
return wide
    ? Row(children: [
        NavigationRail(...),
        const VerticalDivider(width: 1),
        Expanded(child: body),
      ])
    : Scaffold(body: body, bottomNavigationBar: bottomNav);
```

---

## P-WEBVIEW-INSETS（UX-14 WebView 安全区）

```dart
final pad = MediaQuery.paddingOf(context);
webController.runJavaScript('''
  document.documentElement.style.setProperty('--ohos-inset-top','${pad.top}px');
  document.documentElement.style.setProperty('--ohos-inset-bottom','${pad.bottom}px');
  document.documentElement.style.setProperty('--ohos-inset-left','${pad.left}px');
  document.documentElement.style.setProperty('--ohos-inset-right','${pad.right}px');
  window.dispatchEvent(new Event('ohos-insets'));
''');
// 窗口/avoid 变化时重推；H5 用 env(safe-area-inset-*) + var(--ohos-inset-*)
```

---

## P-FOLD-CONTINUITY（UX-15 开合连续性）

- 折展时保留：路由栈、表单 TextEditingController、列表 ScrollController 偏移、播放进度。
- 避免因 `OrientationBuilder` 整树切换导致 State 丢失；用同一 State、子树按约束切换布局。
- 相机页：尺寸变了重建预览，但不要无故 dispose 业务 Bloc/Provider。
- 详读：[references/purax/fold_continuity.md](./purax/fold_continuity.md)

---

## P-EMPTY-SCROLL（UX-16 / UX-24 空态溢出 / 亚像素）

无设备主页、搜索无结果等：插图 + 文案 + CTA 常超出矮高视口或被底 Tab 挡住。

```dart
LayoutBuilder(
  builder: (context, constraints) {
    final short = constraints.maxHeight < 700 ||
        MediaQuery.sizeOf(context).width > MediaQuery.sizeOf(context).height;
    final artH = short ? 120.0 : 200.0;
    return SingleChildScrollView(
      // 亚像素：minHeight 用 constraints.maxHeight - 1，避免 OVERFLOWED BY 0.00x pixels
      child: ConstrainedBox(
        constraints: BoxConstraints(minHeight: constraints.maxHeight - 1),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            SizedBox(height: artH, child: art),
            text,
            SizedBox(height: short ? 12 : 24),
            // CTA：矮高时缩小按钮高度；底部留 Tab/手势条
            SizedBox(height: MediaQuery.paddingOf(context).bottom + kBottomNav),
          ],
        ),
      ),
    );
  },
);
```

**检查：** 勿固定大插图高度且外层不可滚；企业空态若另有布局可保留，个人/通用空态优先本模式。

---

## P-ROW-FLEX（UX-17 固定宽 Row RIGHT OVERFLOW）

```dart
// ❌ Row(children: [Image(width: 150.sc), Image(width: 150.sc)])  // 短边 .sc 放大后溢出
// ✅
Row(
  children: [
    Expanded(child: Image.asset(..., width: double.infinity, fit: BoxFit.contain)),
    SizedBox(width: gap),
    Expanded(child: Image.asset(..., width: double.infinity, fit: BoxFit.contain)),
  ],
);
```

**典型场景：** 地图/设置页双入口图 `150.sc * 2` 并排。

---

## P-MAP-SHEET-CAP（UX-18 地图上半条件卡过高）

贴在地图上的「历史轨迹」时间条件卡等：矮高横屏会盖住地图 tip 与半屏底卡。

```dart
final h = MediaQuery.sizeOf(context).height;
final short = h < 700 || MediaQuery.sizeOf(context).width > h;
final maxCard = h * (short ? 0.58 : 0.78);

ConstrainedBox(
  constraints: BoxConstraints(maxHeight: maxCard),
  child: Column(
    mainAxisSize: MainAxisSize.min,
    children: [
      tipOrHeader, // 钉住
      Flexible(
        child: SingleChildScrollView(child: middleFilters),
      ),
      ctaRow, // 钉住「查询」等
    ],
  ),
);
```

**检查：** 与底 `DraggableScrollableSheet` 并存时，上卡必须留出地图可视带。

---

## P-CALENDAR-SHEET（UX-19 日期范围日历弹层）

```dart
final h = MediaQuery.sizeOf(context).height;
showModalBottomSheet(
  context: context,
  isScrollControlled: true,
  builder: (ctx) => ConstrainedBox(
    constraints: BoxConstraints(maxHeight: h * 0.9),
    child: Column(
      children: [
        titleBar,
        Expanded(
          child: SingleChildScrollView(
            child: calendarGrid, // 行高见 P-SCALE-CAP
          ),
        ),
        confirmBar,
      ],
    ),
  ),
);
```

---

## P-LIST-NO-FIXED-HEIGHT（UX-20 定高列表溢出）

```dart
// ❌ SizedBox(height: items.length * 60.sc, child: ListView(...))
// ✅ 外层 Expanded / 弹层 Flexible + ListView；或 shrinkWrap 仅在已可滚父级内
Expanded(child: ListView.builder(itemCount: items.length, itemBuilder: ...));
```

**典型场景：** 语言/选项列表外层 `length * 60.sc` 定高。

---

## P-CARD-FLEX-PREVIEW（UX-21 摄像头卡预览定高溢出）

列表项内：头区 + 固定 `188.sc` 预览 + 底栏，外屏/横屏易 BOTTOM OVERFLOW。

```dart
// ❌ Column(children: [header, SizedBox(height: 188.sc, child: preview), footer])
// ✅ 去掉 itemExtent；预览吃剩余高
Column(
  children: [
    compactHeader, // 矮高压缩 padding/字号
    Expanded(child: preview),
    footer,
  ],
);
```

---

## P-DRAG-SHEET-CLAMP（UX-22 DraggableScrollableSheet 断言）

```dart
// 更新 min/initial/max 前必须满足：
double clampRatios(double min, double initial, double max) {
  min = min.clamp(0.0, 1.0);
  max = max.clamp(0.0, 1.0);
  if (min > max) {
    final t = min;
    min = max;
    max = t;
  }
  initial = initial.clamp(min, max);
  return initial;
}

// bottomHeight == 0 / 布局未完成时：跳过本次 setState，勿写入非法 ratio
// 折展、从子页返回后 MediaQuery 一帧竞态：常见于地图底卡 Sheet
```

Flutter 断言：`minChildSize <= initialChildSize`。偶现即可按本模式加固。

---

## P-SCALE-CAP（UX-23 `.sc` 弹层尺度封顶）

若全局 `designScale = min(w,h)/375`（或同类 `.sc`）：内屏横屏短边仍可能 scale≥1.5，弹层相对外层字号反差过大或行高撑爆。

```dart
double cappedSc(double design, double designScale) {
  final s = designScale.clamp(0.0, 1.20); // 弹层可用 1.12～1.28
  return design * s;
}
// 日历行高、sheet 内 padding 优先 cappedSc；外层页面可继续用裸 designScale
```

---

## 折展扩展（PX，详读 references/purax）

| 模式/场景 | 入口 |
| --- | --- |
| 悬停分屏 PX-01 | `P-HOVER-SPLIT` + [hover_state_interaction.md](./purax/hover_state_interaction.md) + [assets/folder_stack_example.dart](assets/folder_stack_example.dart) |
| 折痕避让 PX-02 | [crease_avoidance.md](./purax/crease_avoidance.md) |
| 断点布局 PX-03 | [breakpoint_layout.md](./purax/breakpoint_layout.md) + [assets/breakpoint_listener.dart](assets/breakpoint_listener.dart) |
| 开合连续 PX-04 | `P-FOLD-CONTINUITY` + [fold_continuity.md](./purax/fold_continuity.md) |
| 折展修 bug PX-05 | [bug_fix_cases.md](./purax/bug_fix_cases.md) |
| 信箱 PX-06 | `P-NO-LETTERBOX` + [scbcompatible_letterbox.md](./purax/scbcompatible_letterbox.md) |

始终提供 **方案 A（hadss）** 与 **方案 B（原生 MediaQuery/断点）**；见 [official_adaptation_guide.md](./purax/official_adaptation_guide.md)。

---

## 反模式速查

| 反模式 | 后果 | 改为 |
| --- | --- | --- |
| `Column` + 无滚动撑满多块内容 | 外屏/横屏截断 | Scroll/List/CustomScrollView |
| `SizedBox(width: 375)` 或 `maxWidth: 400` 居中 | 内屏横屏双侧留白 | 宽屏 Expanded 全宽 |
| `CameraPreview` + `AspectRatio(16/9)` 居中 | 未铺满 | cover + 全窗口 |
| 固定 `height` 顶栏再加 `padding.top` | 顶栏文字截断 | 外层 padding + 内层定高 |
| `resizeToAvoidBottomInset: false` | 登录叠字 | 保持 true + 可滚 |
| `OrientationBuilder` 顶层切整 app | 分屏/折叠误判、状态丢失 | `sizeOf` / `LayoutBuilder` |
| 全局锁定竖屏 | 展开黑边 letterbox | 允许旋转或按页临时锁定 |
| 交互控件画在 hinge/折痕上 | 悬停态难点击 | 分区避让 displayFeatures |
| WebView 沉浸但不推 insets | H5 挡挖孔 | P-WEBVIEW-INSETS |
| 空态大插图 + 不可滚 | 按钮被 Tab 挡 | P-EMPTY-SCROLL |
| `N.sc * 2` 并排定宽 | RIGHT OVERFLOW | P-ROW-FLEX |
| 地图条件卡无 maxHeight | 盖住地图/tip | P-MAP-SHEET-CAP |
| `length * itemH` 定外高 | 列表溢出 | P-LIST-NO-FIXED-HEIGHT |
| 卡片内预览定高 188.sc | BOTTOM OVERFLOW | P-CARD-FLEX-PREVIEW |
| Sheet ratio 未 clamp | min>initial 断言 | P-DRAG-SHEET-CLAMP |
| 弹层裸用全量 `.sc` | 字号反差/行高爆 | P-SCALE-CAP |
