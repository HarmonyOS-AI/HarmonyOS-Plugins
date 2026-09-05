<!--
Merged from flutter-purax-adaptation/references/ (identical copy also existed in
flutter-pura-x-max-ux-20260731/references/purax/).
Role: deep-dive reference material for foldable scenes PX-01..PX-05; read on demand
via scenarios/foldable-catalog.md. Internal relative links stay valid inside purax/.
Per references/index.md this material is reference-only and never overrides SKILL.md.
-->
# 场景开发案例集

## 案例 1：聊天 App 列表-详情双栏适配

### 需求
折叠态（手机竖屏）全屏聊天 → 展开态（PuraX 展开）左侧会话列表 + 右侧聊天内容

### 方案（hadss 库）

```dart
import 'package:hadss_adaptive_layout/hadss_adaptive_layout.dart';

class ChatHomePage extends StatefulWidget {
  @override
  State<ChatHomePage> createState() => _ChatHomePageState();
}

class _ChatHomePageState extends State<ChatHomePage> {
  String? _selectedId;

  @override
  Widget build(BuildContext context) {
    return NavigationSplitContainer(
      mode: NavigationSplitMode.auto,
      navBarWidth: 320,
      navBar: ConversationList(
        selectedId: _selectedId,
        onSelect: (id) => setState(() => _selectedId = id),
      ),
      content: _selectedId != null
          ? ChatDetail(chatId: _selectedId!)
          : const EmptyPlaceholder(),
    );
  }
}
```

**说明：**
- `< 600dp` → 单栏 stack：点击会话 push 到聊天详情
- `≥ 600dp` → 双栏 split：左侧固定 320dp 列表，右侧聊天内容

### 原生 Flutter 方案

```dart
LayoutBuilder(
  builder: (context, constraints) {
    if (constraints.maxWidth >= 600) {
      return Row(
        children: [
          SizedBox(width: 320, child: ConversationList(...)),
          Expanded(child: ChatDetail(...)),
        ],
      );
    }
    return _selectedId != null
        ? ChatDetail(chatId: _selectedId!)
        : ConversationList(...);
  },
)
```

---

## 案例 2：视频播放器铰链避让

### 需求
PuraX 半折叠时，视频移到上半屏，控制栏留在下半屏（铰链不遮挡按钮）

### 方案（FolderStack）

```dart
import 'package:hadss_avoid_area/hadss_avoid_area.dart';

FolderStack(
  upperItems: ['video_player'],
  children: [
    Container(
      key: const ValueKey('video_player'),
      child: VideoPlayer(_controller),
    ),
    Positioned(bottom: 0, child: ControlBar()),
  ],
)
```

---

## 案例 3：商品列表 GridView 断点适配

### 需求
竖屏 2 列 → 横屏 3-4 列 → 平板 4-5 列

### 方案

```dart
class ProductGrid extends StatefulWidget {
  @override
  State<ProductGrid> createState() => _ProductGridState();
}

class _ProductGridState extends State<ProductGrid> {
  int _cols = 2;

  @override
  void initState() {
    super.initState();
    _cols = _getCols(BreakpointManager.instance.currentBreakpoint.widthBreakpoint);
    BreakpointManager.instance.addListener(_onBpChanged);
  }

  void _onBpChanged(BreakpointData d) {
    setState(() => _cols = _getCols(d.widthBreakpoint));
  }

  int _getCols(WidthBreakpoint bp) {
    switch (bp) {
      case WidthBreakpoint.xs: return 1;
      case WidthBreakpoint.sm: return 2;
      case WidthBreakpoint.md: return 3;
      case WidthBreakpoint.lg: return 4;
      case WidthBreakpoint.xl: return 5;
    }
  }

  @override
  void dispose() {
    BreakpointManager.instance.removeListener(_onBpChanged);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: _cols,
      ),
      itemBuilder: (ctx, i) => ProductCard(products[i]),
    );
  }
}
```

---

## 案例 4：管理后台侧边栏导航

### 需求
宽屏时固定侧边栏，窄屏时变为抽屉式导航

### 方案（SideBarContainer）

```dart
import 'package:hadss_adaptive_layout/hadss_adaptive_layout.dart';

SideBarContainer(
  type: SideBarContainerType.auto,
  sideBar: NavigationMenu(
    items: menuItems,
    onSelect: (page) => setState(() => _currentPage = page),
  ),
  content: _currentPage,
)
```

**说明：**
- `SideBarContainerType.auto` 自动在宽屏（embed）和窄屏（overlay）间切换

---

## 案例 5：PuraX 外屏沉浸式适配

### 需求
PuraX 外屏为 1:1 方屏（~326x326dp），空间有限。需要在滚动浏览时隐藏标题栏和 Tab 栏释放空间。

### 策略

- 使用 `BreakpointManager` 判断是否为外屏（width=sm + height=md）
- 在 `ScrollController` 中监听滚动方向
- 上滑时渐进缩小/隐藏标题栏和 Tab 栏
- 下滑时恢复

### 配套 hadss 库

- `hadss_adaptive_layout`：断点判断
- `hadss_avoid_area`：安全区域获取（状态栏高度 + 导航指示条高度）

---

## 关键可复用模式

| 模式 | 适用场景 | 核心组件 | 参考案例 |
|------|---------|---------|---------|
| 列表-详情双栏 | 聊天、邮件、笔记 | NavigationSplitContainer | 案例 1 |
| 铰链避让 | 视频、全屏内容 | FolderStack | 案例 2 |
| 断点适配网格 | 商品、图片列表 | BreakpointManager | 案例 3 |
| 侧边栏导航 | 管理后台、设置 | SideBarContainer | 案例 4 |
| 小方屏沉浸 | PuraX 外屏浏览 | ScrollController + 断点 | 案例 5 |
