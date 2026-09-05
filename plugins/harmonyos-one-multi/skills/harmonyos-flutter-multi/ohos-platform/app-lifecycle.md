# Flutter-OH 应用生命周期

整合自 `flutter_samples/ohos/docs/04_development/Flutter-OH应用生命周期.md`。

## 集成方式

| 集成方式 | 典型应用场景 | 宿主 | Flutter 入口 |
| -------- | -------- | ---- | ------------ |
| 独立 Flutter 应用 | `flutter create` 工程 | `EntryAbility extends FlutterAbility` | `FlutterAbility` 内部创建引擎 |
| Add-to-App | 既有鸿蒙 App 内嵌 Flutter 页 | `EntryAbility extends UIAbility` | 页面内 `new FlutterEntry(context)` |

## 生命周期时序概览

> 「生命周期」指从 FlutterApp 启动到 Flutter 首帧、页面可见性变化、前后台切换直至销毁的
> 原生回调链路。

### 独立 Flutter 应用（Standalone）

- **启动**：`onCreate` 注册 `FlutterManager`；`onWindowStageCreate` 加载首页并创建
  `FlutterEngine`；引擎创建完成后触发 `configureFlutterEngine`，再进入 Dart `main`。
- **前/后台切换**：`onForeground` / `onBackground`。
- **退出**：`onWindowStageDestroy` / `onDestroy` 释放窗口与引擎，注销 `FlutterManager`。

### Add-to-App

系统触发 ArkUI 组件生命周期后，开发者须在对应回调中**主动调用** `FlutterEntry` 同名方法：

- **加载 Flutter 页**：`aboutToAppear` 创建 `FlutterEngine`、`FlutterView`（期间触发
  `configureFlutterEngine`），经 `getFlutterView()` 提供 `viewId`；`onPageShow` 恢复渲染。
- **离开 Flutter 页**：`onPageHide` 暂停渲染；`aboutToDisappear` 销毁引擎与视图。

## 生命周期回调说明

> - 生命周期回调在主线程执行，仅执行轻量操作；耗时任务异步或交子线程。
> - 重写 `FlutterAbility` / `FlutterEntry` 生命周期方法时**必须调用 `super`**。
>   `onForeground`/`onBackground` 等**先**调 `super` 再执行开发者逻辑；
>   `onDestroy` **后**调 `super.onDestroy()`（super 会销毁引擎，须先完成数据保存与资源释放）。

### 独立 Flutter 应用

| 回调 | 触发时机 | 框架默认行为 | 开发者可扩展 |
| ---- | -------- | ------------ | ------------ |
| `onCreate()` | 首次创建 UIAbility 实例 | 注册 `FlutterManager` | 仅一次的启动逻辑 |
| `onWindowStageCreate()` | `WindowStage` 创建后、进入前台前 | 创建 `FlutterView`、`loadContent` 加载首页 | 重写 `pagePath()` 更换首页路径 |
| `onForeground()` | 切换至前台、UI 可见之前 | 恢复渲染 | 申请/恢复原生资源（如定位） |
| `onBackground()` | UI 完全不可见之后 | 暂停渲染 | 释放无用原生资源 |
| `onWindowStageDestroy()` | 实例销毁前，`WindowStage` 已销毁 | 注销 `WindowStage`、释放窗口资源 | 释放通过 `WindowStage` 获取的资源 |
| `onDestroy()` | UIAbility 实例销毁前（最后一个回调） | 销毁引擎与视图 | 保存数据、释放系统资源 |

示例：

```typescript
// EntryAbility.ets
import { AbilityConstant, Want } from '@kit.AbilityKit';
import { FlutterAbility } from '@ohos/flutter_ohos';

export default class EntryAbility extends FlutterAbility {
  pagePath(): string {
    return 'pages/CustomIndex'  // 默认 'pages/Index'，非生命周期回调
  }

  onCreate(want: Want, launchParam: AbilityConstant.LaunchParam): void {
    super.onCreate(want, launchParam)
    // 仅一次的启动逻辑，例如解析 Want 启动参数
  }

  onForeground(): void {
    super.onForeground()  // 先调 super
    // 申请/恢复资源，例如恢复定位、重新订阅传感器
  }

  onBackground(): void {
    super.onBackground()  // 先调 super
    // 释放 UI 不可见时无用的资源，勿执行耗时操作
  }

  onWindowStageDestroy(): void {
    super.onWindowStageDestroy()
    // 释放通过 WindowStage 获取的自定义资源
  }

  onDestroy(): void {
    // 保存用户数据、释放自定义原生资源
    super.onDestroy()  // 后调 super（super 销毁引擎）
  }
}
```

### Add-to-App

宿主 `UIAbility` 保持原生实现，须在 `onCreate` / `onWindowStageCreate` /
`onWindowStageDestroy` / `onDestroy` 中调用 `FlutterManager` 的 `push` / `pop`，
且 `loadContent` 加载**原生主导航**而非 Flutter 首页。

```typescript
// EntryAbility.ets（Add-to-App 宿主 UIAbility）
import { UIAbility, AbilityConstant, Want } from '@kit.AbilityKit';
import { window } from '@kit.ArkUI';
import { ExclusiveAppComponent, FlutterManager } from '@ohos/flutter_ohos';

export default class EntryAbility extends UIAbility implements ExclusiveAppComponent<UIAbility> {
  detachFromFlutterEngine(): void {}
  getAppComponent(): UIAbility { return this; }

  onCreate(want: Want, launchParam: AbilityConstant.LaunchParam): void {
    FlutterManager.getInstance().pushUIAbility(this);
  }

  onWindowStageCreate(windowStage: window.WindowStage): void {
    FlutterManager.getInstance().pushWindowStage(this, windowStage);
    windowStage.loadContent('pages/MainPage');
  }

  onWindowStageDestroy(): void {
    FlutterManager.getInstance().popWindowStage(this);
  }

  onDestroy(): void {
    FlutterManager.getInstance().popUIAbility(this);
  }
}
```

> `pushUIAbility`/`popUIAbility` 与 `pushWindowStage`/`popWindowStage` **必须成对调用**；
> 遗漏 `pop` 会导致后续页面 `viewId` 绑定异常、插件上下文解析错误。

#### 宿主前后台与 FlutterEntry

Add-to-App 存在**两套生命周期**：宿主 `UIAbility` 的 `onForeground`/`onBackground` 处理
Ability 级原生资源；Flutter 引擎渲染启停由 ArkUI 页面的 `onPageShow`/`onPageHide` 驱动，
**二者不自动桥接**。

| ArkUI 组件回调 | 触发时机 | 开发者须调用 | 效果 |
| -------------- | -------- | ------------ | ---- |
| `aboutToAppear()` | 组件即将挂载 | `flutterEntry.aboutToAppear()` | 创建引擎与视图（回调 `configureFlutterEngine`） |
| `onPageShow()` | 页面可见（含 Navigation `onShown`） | `flutterEntry.onPageShow()` | 恢复渲染 |
| `onPageHide()` | 页面被遮挡或离开（含 `onHidden`） | `flutterEntry.onPageHide()` | 暂停渲染 |
| `aboutToDisappear()` | 组件即将卸载（Navigation 可为 `onDisAppear`） | `flutterEntry.aboutToDisappear()` | 销毁引擎与视图 |

使用 `Navigation` 时，须在 `onShown` / `onHidden` / `onDisAppear` 等路由回调中同步调用
上表对应方法。

```typescript
// FlutterRoutePage.ets
import { FlutterPage, FlutterView } from '@ohos/flutter_ohos';
import MyFlutterEntry from '../entry/MyFlutterEntry';

@Component
export struct FlutterRoutePage {
  private flutterEntry?: MyFlutterEntry;
  private flutterView?: FlutterView;

  aboutToAppear(): void {
    this.flutterEntry = new MyFlutterEntry(getContext(this));
    this.flutterEntry.aboutToAppear();
    this.flutterView = this.flutterEntry.getFlutterView();
  }

  onPageShow(): void { this.flutterEntry?.onPageShow(); }
  onPageHide(): void { this.flutterEntry?.onPageHide(); }

  aboutToDisappear(): void {
    this.flutterEntry?.aboutToDisappear();
    this.flutterEntry = undefined;
    this.flutterView = undefined;
  }

  build() {
    Column() { FlutterPage({ viewId: this.flutterView?.getId() }) }
    .width('100%').height('100%')
  }
}
```

> **Engine 与 FlutterView 绑定**：**同一 `FlutterEngine` 在活跃态下只能 attach 一个
> `FlutterView`**。Add-to-App 多页面导航共享同一 Engine 时，须在离开页面时 detach 当前
> `FlutterView`（如 `aboutToDisappear`/`onPageHide` 中 `flutterView.detachFromFlutterEngine()`），
> 进入新页面后再 attach 新的 `FlutterView`（如 `aboutToAppear`/`onPageShow` 中
> `flutterView.attachToFlutterEngine(engine)`）。**切换页面前必须先 detach 再 attach**，
> 否则可能黑屏、画面重叠或 Engine 状态错误。各页面独立创建 `FlutterEntry` 时框架自动管理
> attach/detach；共享 Engine 时须自行保证约束。

## 引擎配置（configureFlutterEngine）

`configureFlutterEngine()` 是 Flutter Embedding 的**引擎初始化钩子**（非 UIAbility/ArkUI
生命周期回调）。框架在 `FlutterEngine` 创建完成、Dart `main` 执行之前调用（每引擎一次），
供应用注册插件或做引擎级配置。两种集成方式均通过子类重写，**须调用 `super`**。

### 独立 Flutter 应用

```typescript
import { FlutterAbility, FlutterEngine } from '@ohos/flutter_ohos';
import { GeneratedPluginRegistrant } from '../plugins/GeneratedPluginRegistrant';

export default class EntryAbility extends FlutterAbility {
  configureFlutterEngine(flutterEngine: FlutterEngine) {
    super.configureFlutterEngine(flutterEngine)
    GeneratedPluginRegistrant.registerWith(flutterEngine)
  }
}
```

### Add-to-App

```typescript
import { FlutterEngine, FlutterEntry } from '@ohos/flutter_ohos';
import { GeneratedPluginRegistrant } from '../plugins/GeneratedPluginRegistrant';

export default class MyFlutterEntry extends FlutterEntry {
  configureFlutterEngine(flutterEngine: FlutterEngine): void {
    super.configureFlutterEngine(flutterEngine)
    GeneratedPluginRegistrant.registerWith(flutterEngine)
  }
}
```
