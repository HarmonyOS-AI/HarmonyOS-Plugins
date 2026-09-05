# 分栏功能完整接入指南

本文档整合自 `flutter_samples/ohos/docs/04_development/Flutter分栏功能接入指导.md`，
并补充工程代码实现细节。

## 1. 功能说明

Flutter 分栏功能为应用提供横竖屏自适应的分栏布局：

| 屏幕状态 | 布局表现 |
|----------|----------|
| 横屏/宽屏 | 左右两侧同时显示，左侧主页 + 右侧详情页 |
| 竖屏/窄屏 | 单栏显示，智能切换主页或详情页 |
| 折叠屏展开 | 自动切换为分栏布局 |
| 折叠屏折叠 | 自动切换为单栏布局 |

**特点**：自动适应屏幕尺寸变化，无需应用代码修改；默认关闭，通过配置文件启用。

**支持范围**：基于 Navigator 的路由方式和基于 Router 的声明式路由方式（RouterDelegate、RouterConfig、go_router）。
Router 模式基于单 NavigatorState + 双 Overlay 实现，对上层透明。

## 2. 配置文件

**位置**：`ohos/entry/src/main/resources/rawfile/split_config.json`

```json
{
  "splitOptions": {
    "enableWideWindowSplit": false,
    "enableSquareWindowSplit": true,
    "homePage": "/",
    "fullScreenPages": ["/videoPlayer", "/imageViewer"],
    "enableReducedContainerSize": true,
    "supportLandscapeFullscreen": true
  }
}
```

### 配置项详解

#### enableWideWindowSplit

宽窗口分栏开关。触发条件：宽高均 > 600vp，宽高比 > 1.2，横屏状态。

#### enableSquareWindowSplit

方形屏幕分栏开关。触发条件：宽高均 > 600vp，宽高比和高宽比均 < 1.2。

#### homePage

主页路由名。**Router 模式（RouterDelegate、RouterConfig、go_router）不支持自动检测，必须填写。**

Navigator 模式下 homePage 为空时自动识别顺序：
1. MaterialApp/CupertinoApp 的 `home` 参数
2. `routes` 中的 `/home`、`/`、`/index`
3. `initialRoute` 指定的路由

**路由名匹配规则**：

```dart
// Navigator 模式 - home 参数
MaterialApp(home: const HomePage());  // homePage 配置为 HomePage 对应路由名

// Navigator 模式 - initialRoute + onGenerateRoute
MaterialApp(initialRoute: '/splash', onGenerateRoute: (settings) {
  if (settings.name == '/home') {
    return MaterialPageRoute(settings: settings, builder: (_) => HomePage());
  }
});  // homePage 配置为 '/home'

// Navigator 模式 - routes 路由表
MaterialApp(initialRoute: '/splash', routes: {
  '/home': (context) => const HomePage(),
});  // homePage 配置为 '/home'

// Router 模式 - Page.name
pages: [
  MaterialPage(name: '/home', child: HomePage()),
]  // homePage 配置为 '/home'

// go_router 模式 - GoRoute.name
GoRoute(path: '/home', name: '/home', builder: (_, __) => HomePage())
// homePage 配置为 '/home'，注意 name 与 fullScreenPages 须完全一致
```

#### fullScreenPages

强制全屏页面列表。进入时自动切换为单栏，退出后恢复分栏。

#### enableReducedContainerSize

分栏时 MediaQuery 返回的宽度值。`true`（默认）时宽度为屏幕宽度的一半，
`false` 时仍为实际屏幕宽度。

#### supportLandscapeFullscreen

横屏全屏触发。当页面通过 `SystemChrome.setPreferredOrientations` 强制横屏
（仅 landscapeLeft/landscapeRight），且此项为 `true` 时，自动禁用分栏切换全屏。

## 3. 路由转发执行流程

分栏功能将应用运行划分为两个阶段：

| 阶段 | 条件 | 左侧显示 | 右侧显示 | 路由跳转行为 |
|------|------|----------|----------|--------------|
| 阶段1 | 主页未显示 | 目标页面（开屏页/登录页等） | 占位页 | 左侧 Overlay 显示 |
| 阶段2 | 主页已显示 | 主页 | 详情页或占位页 | 右侧 Overlay 显示 |

**关键点**：只有主页显示后，详情页才会分配到右侧。路由历史在单一 NavigatorState 中统一维护。

## 4. 路由方案兼容性

| 方案 | 路由方式 | 兼容性 | 限制 |
|------|---------|--------|------|
| 1 | Navigator + initialRoute + onGenerateRoute | ✅ 完全兼容 | 推荐使用 |
| 2 | Navigator + initialRoute + routes | ✅ 完全兼容 | 支持开屏页流程 |
| 3 | Navigator + home + onGenerateRoute | ⚠️ 部分兼容 | 不支持开屏页/登录页流程 |
| 4 | Navigator + home + routes | ⚠️ 部分兼容 | 不支持开屏页/登录页流程 |
| 5 | CupertinoApp 同方案1-4 | ✅ 完全兼容 | — |
| 6 | Router + RouterDelegate + pages | ✅ 已支持 | — |
| 7 | Router + RouterConfig | ✅ 已支持 | 需设置 RootBackButtonDispatcher |
| 8 | Router + go_router | ✅ 已支持 | 建议充分验证 |

## 5. 路由 API 使用限制

### Route settings 参数

**必须保留 `settings` 参数**，否则无法识别主页/全屏页：

```dart
// ✅ 推荐：pushNamed
Navigator.pushNamed(context, '/detail');

// ✅ 推荐：onGenerateRoute 中保留 settings
onGenerateRoute: (settings) => MaterialPageRoute(
  settings: settings,  // 关键
  builder: (_) => DetailPage(),
);

// ✅ 推荐：手动设置 RouteSettings
Navigator.push(context, MaterialPageRoute(
  settings: RouteSettings(name: '/detail'),
  builder: (_) => DetailPage(),
));

// ❌ 避免：不设置 settings
Navigator.push(context, MaterialPageRoute(
  builder: (_) => DetailPage(),  // 无法识别路由名
));
```

### 路由 API 行为

| API | 阶段1行为 | 阶段2行为 |
|-----|-----------|-----------|
| `push(Route)` | 左侧推入 | 右侧推入 |
| `pushNamed(String)` | 左侧推入 | 右侧推入 |
| `pushReplacement` | 左侧替换 | 从主页发起时降级为普通 push |
| `pushAndRemoveUntil` | 左侧推入并清栈 | 从主页发起时降级为普通 push |
| `pop()` | 弹窗→右侧→左侧 | 弹窗→右侧→左侧 |
| `canPop()` | 右侧优先检查 | 右侧优先检查 |

> `pushReplacement`/`pushAndRemoveUntil` 从主页发起时，因主页不可替换，SDK 降级为普通 push。

### 不支持的模式

```dart
// ❌ 不支持：三元表达式判断主页
MaterialApp(home: isLoggedIn ? HomePage() : LoginPage());

// ✅ 正确：使用 initialRoute + 路由表
MaterialApp(
  initialRoute: isLoggedIn ? '/home' : '/login',
  routes: {
    '/login': (context) => LoginPage(),
    '/home': (context) => HomePage(),
  },
);
```

## 6. 弹窗处理

分栏模式下 PopupRoute 自动显示在有内容的一侧，SDK 自动添加同步遮罩层。

**关键注意**：`showModalBottomSheet`、`showMenu`、`showSearch` 等 API 默认 `useRootNavigator: false`，
分栏场景下需显式设置为 `true`：

```dart
// ❌ 分栏下蒙层不正确
showModalBottomSheet(context: context, builder: (context) => SheetContent());

// ✅ 需显式设置 useRootNavigator: true
showModalBottomSheet(
  context: context,
  useRootNavigator: true,  // 关键
  builder: (context) => SheetContent(),
);
```

## 7. 返回手势

系统返回键/手势由 SDK 自动处理，优先级：
1. 弹窗正在显示 → 关闭弹窗
2. 右侧 Overlay 有可 pop 路由 → 右侧 pop
3. 左侧 Overlay 有可 pop 路由 → 左侧 pop
4. 两侧都不可 pop → 退出应用

## 8. 屏幕旋转/折叠屏

SDK 自动监听屏幕变化，路由栈和状态完整保留：

| 场景 | 自动行为 |
|------|----------|
| 竖屏 → 横屏 | 单栏 → 分栏 |
| 横屏 → 竖屏 | 分栏 → 单栏 |
| 折叠屏展开 | 单栏 → 分栏 |
| 折叠屏折叠 | 分栏 → 单栏 |

## 9. 常见问题排查

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 分栏不生效 | 配置未启用 | `enableWideWindowSplit: true` |
| 主页识别错误 | homePage 配置错误 | 按 homePage 配置说明设置 |
| 详情页不转发 | settings 缺失 | 保留 RouteSettings 参数 |
| 全屏页面仍分栏 | fullScreenPages 未配置 | 添加路由名到配置列表 |
| RouterConfig 返回键退出应用 | 未设置 RootBackButtonDispatcher | `RouterConfig(backButtonDispatcher: RootBackButtonButtonDispatcher())` |
| 弹窗蒙层不显示 | useRootNavigator 未设置 | 显式 `useRootNavigator: true` |
| GoRouter 全屏页不生效 | GoRoute.name 不匹配 | 确保 name 与 fullScreenPages 完全一致 |
| pushReplacement 行为异常 | 主页不可替换 | 已知行为，降级为普通 push |

## 10. 工程代码实现

### Dart 层

| 文件 | 职责 |
|------|------|
| `packages/flutter/lib/src/widgets/split_view_config.dart` | 配置单例，解析 split_config.json |
| `packages/flutter/lib/src/widgets/split_view_manager.dart` | 分栏状态管理（ChangeNotifier） |
| `packages/flutter/lib/src/widgets/split_view_navigator_policy.dart` | Navigator 分栏策略（Overlay 分配、pop 拦截、清栈、MirrorBarrier 焦点恢复） |
| `packages/flutter/lib/src/services/split_view_config_loader.dart` | SystemChannel 接收引擎推送的配置 |
| `packages/flutter/lib/src/services/orientation_change_notifier.dart` | 桥接 SystemChrome 与 SplitViewManager |
| `packages/flutter/lib/src/widgets/app.dart` | ohos 平台初始化分栏配置 |
| `packages/flutter/lib/src/widgets/navigator.dart` | 分栏策略集成点 |
| `packages/flutter/lib/src/widgets/media_query.dart` | `enableSplitView` 字段，分栏时 size 宽度减半 |

### ETS 层

| 文件 | 职责 |
|------|------|
| `engine/.../systemchannels/SplitViewConfigSystemChannel.ets` | 引擎主动推送配置（读取 rawfile/split_config.json + app 图标 base64） |
| `engine/.../plugin/splitview/SplitViewConfigPlugin.ets` | 备用 MethodChannel 方案 |
| `engine/.../embedding/engine/FlutterEngine.ets` | 初始化 SplitViewConfigSystemChannel |
| `engine/.../embedding/ohos/FlutterAbilityAndEntryDelegate.ets` | Dart 启动后立即推送配置 |

### 分栏激活条件

`_checkScreenSizeAndSetSplitScreen()` 逻辑：
- 仅 `TargetPlatform.ohos` 生效
- 逻辑宽高均 ≥ 600vp（`splitScreenWidthThreshold = 600`）
- 宽高比 ≤ 1.2 → `enableSquareWindowSplit`
- 宽高比 > 1.2 且横屏 → `enableWideWindowSplit`
