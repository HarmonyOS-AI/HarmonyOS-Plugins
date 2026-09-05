# Flutter OHOS 架构介绍

整合自 `flutter_samples/ohos/docs/02_architecture/README.md`。

## 概述

Flutter OHOS 的本质不是重新设计一套 Flutter 框架，而是在保留 Flutter Framework 与
Engine Core 主体能力的前提下，补齐 OpenHarmony 平台的宿主、渲染、输入、资源、生命周期
和无障碍适配层。

从代码归属看，主要由三部分组成：

- **Flutter 应用与 Framework**：开发者 Dart 业务代码，以及 Flutter 上层框架能力。
- **Flutter Engine 通用核心**：`Shell`、`Rasterizer`、`RuntimeController`、`Dart VM`、
  `Platform Channel` 等平台无关实现。
- **OpenHarmony 适配层**：ArkTS Embedding、NAPI 桥接和 Native Embedder，共同把 Flutter
  运行时接入 OpenHarmony 的 `UIAbility`、`WindowStage`、`XComponent`、`OH_NativeWindow`、
  `OH_NativeVSync`、`ResourceManager`、无障碍服务等系统能力。

OHOS 适配层目录：

- ArkTS Embedding：`engine/src/flutter/shell/platform/ohos/flutter_embedding/flutter/src/main/ets/`
- Native Embedder：`engine/src/flutter/shell/platform/ohos/`

## 整体架构

### 分层视图

```
L1 Flutter 应用层      Dart Application / Flutter Framework
L2 Flutter Engine Core Shell / RuntimeController / Animator / Rasterizer / Dart VM
L3 OpenHarmony Embedding
   ├ ArkTS Embedding    FlutterAbilityAndEntryDelegate / FlutterEngine / FlutterView
   ├ NAPI Bridge        FlutterNapi / PlatformViewOHOSNapi
   └ Native Embedder    OhosMain / OHOSShellHolder / PlatformViewOHOS / OHOSSurface / VsyncWaiterOHOS
L4 OpenHarmony System   UIAbility / WindowStage / XComponent / NativeWindow / NativeVSync / ResourceManager / Accessibility
```

- L1 负责业务与 Flutter 声明式 UI。
- L2 负责 Dart 运行时、帧调度和渲染核心。
- L3 负责把 Flutter 的平台抽象映射到 OHOS 宿主、窗口、输入、资源和系统服务。
- L4 提供 OpenHarmony 原生能力。

### 关键交互主线

1. 平台抽象主线：`Shell -> PlatformViewOHOS`
2. 帧调度主线：`Animator -> VsyncWaiterOHOS -> OH_NativeVSync`
3. 渲染提交主线：`Rasterizer -> OHOSSurface/OHOSContext -> OH_NativeWindow`
4. 平台消息主线：`RuntimeController -> PlatformMessageHandlerOHOS / FlutterNapi -> ArkTS 宿主`

### 按功能划分

| 层次 | 代表实现 | 主要职责 |
| --- | --- | --- |
| Flutter 应用代码 | 业务 Dart 代码 | 描述页面、状态、路由和业务逻辑 |
| Flutter Framework | Widgets、Rendering、Scheduler、Services | 构建 Widget/Element/RenderObject 树 |
| Flutter Engine 通用核心 | `Shell`、`Dart VM`、`RuntimeController`、`Rasterizer` | 承载 Dart 运行时、帧调度、场景构建与渲染提交 |
| OpenHarmony 适配代码 | ArkTS Embedding + NAPI + Native Embedder | 对接 Ability、XComponent、输入、纹理、VSync、无障碍、资源 |
| OpenHarmony OS 能力 | `UIAbility`、`WindowStage`、`OH_NativeWindow`、`OH_NativeVSync`、`ResourceManager` | 提供窗口、图形缓冲、显示时序、资源和系统服务 |

> Flutter OHOS 的平台差异主要集中在第四层（适配层），Framework 和 Engine Core 主体
> 仍遵循上游 Flutter 分层设计。

## 核心对象与职责

### ArkTS Embedding

| 核心对象 | 职责 |
| --- | --- |
| `FlutterAbilityAndEntryDelegate` | 串联 Ability 生命周期、引擎创建、视图创建、首轮 Dart 启动和页面显示/隐藏 |
| `FlutterEngineGroup` | 管理首引擎创建与后续 `spawn`，复用 VM 和共享资源 |
| `FlutterEngine` | 封装 `DartExecutor`、系统通道、插件注册、`FlutterRenderer`、`PlatformViewsController` |
| `FlutterView` | ArkTS 视图容器，负责 `XComponent` 绑定、Viewport 同步、键鼠输入、首帧监听、系统避让区同步 |
| `FlutterRenderer` | 纹理注册与外部纹理管理入口 |
| `PlatformViewsController` | 管理 ArkTS 原生视图嵌入、纹理模式与混合布局 |

### NAPI 桥接层

| 核心对象 | 职责 |
| --- | --- |
| `FlutterNapi` | ArkTS 对 Native 的总入口，负责初始化、attach、spawn、平台消息、viewport、纹理、无障碍和 `XComponent` 绑定 |
| `PlatformViewOHOSNapi` | C++ NAPI 导出层，接收 ArkTS 调用并转发给 `OHOSShellHolder` / `PlatformViewOHOS` |

### Native Embedder

| 核心对象 | 职责 |
| --- | --- |
| `OhosMain` | 解析 Shell Args，生成 `Settings`，选择渲染后端，完成引擎全局初始化 |
| `OHOSShellHolder` | 创建 `ThreadHost`、`Shell`、`PlatformViewOHOS`、注册图像解码器，管理引擎生命周期 |
| `PlatformViewOHOS` | 平台适配核心，负责 Surface、Viewport、Platform Message、纹理、输入、生命周期和无障碍桥接 |
| `XComponentAdapter` / `XComponentBase` | 管理多个 `XComponent` 实例及其 Surface/输入/无障碍回调 |
| `VsyncWaiterOHOS` | 对接 `OH_NativeVSync`，驱动 Flutter 帧调度，接入刷新率投票 |
| `OHOSSurface` / `OHOSContext` | 管理图形上下文、窗口表面、Swapchain / EGLSurface 与 GPU Surface |
| `OHOSAssetProvider` | 从 HAP 原始资源中提供 Flutter 资产 |
| `SemanticsBridge` | 维护 Flutter 语义树与 OpenHarmony 无障碍事件之间的映射 |

## 线程模型

### 线程组成

| 线程 | 主要来源 | 核心职责 |
| --- | --- | --- |
| ArkTS 主线程 | OpenHarmony 应用主线程 | `UIAbility`、`WindowStage`、`FlutterView`、ArkTS 插件、窗口事件、系统回调 |
| Platform Thread | 当前平台消息循环 | NAPI 回调落点、平台消息分发、部分宿主逻辑协同 |
| UI Thread | `OHOSShellHolder` 创建 | Dart Isolate 调度、动画帧生产、Framework Build/Layout/Paint |
| Raster Thread | `OHOSShellHolder` 创建 | GPU Surface 创建、场景栅格化、SwapBuffers / Present |
| IO Thread | `OHOSShellHolder` 创建 | 资源加载、图片解码、部分 VSync 投票和后台任务 |

### OHOS 线程适配特点

1. `OHOSShellHolder` 显式创建 `ThreadHost`（至少 Raster 和 IO；未启用
   `merged_platform_ui_thread` 时还单独创建 UI 线程）。
2. UI 和 Raster 线程设更高 QoS，优先级映射到 `QOS_USER_INTERACTIVE`。
3. `VsyncWaiterOHOS` 在 UI 线程注册 `OH_NativeVSync_RequestFrameWithMultiCallback`，
   VSync 回调到来后唤醒 Flutter UI 帧流程。
4. ArkTS 主线程不直接承担渲染任务，负责宿主 UI、生命周期和系统事件收集，经 NAPI 进入运行时。

## 启动流程

### 阶段一：Loader 与引擎全局初始化

1. ArkTS 侧 `FlutterInjector` 获取 `FlutterLoader` 和 `FlutterNapi`。
2. `FlutterLoader.startInitialization()` 加载 `FlutterApplicationInfo`，预取默认字体，
   Debug 模式复制 `kernel_blob.bin`、VM/isolate snapshot 到私有目录。
3. `FlutterLoader.ensureInitializationComplete()` 组装 Shell Args（ICU、资源缓存、
   Impeller 开关、AOT/JIT 资源路径）。
4. `FlutterNapi.init()` 进入 Native，调用 `OhosMain::NativeInit()`，生成 `Settings`，
   确定渲染后端：`kSoftware` / `kOpenGLES`（Skia+GLES） / `kImpellerVulkan`。

### 阶段二：FlutterEngine 创建或复用

1. `FlutterAbilityAndEntryDelegate.setupFlutterEngine()` 决定缓存引擎/自定义引擎/
   缓存 `FlutterEngineGroup`/新建引擎组。
2. 首引擎通过 `FlutterEngineGroup.createAndRunEngineByOptions()` 创建：初始化
   `DartExecutor`、Renderer、系统通道、插件注册器；`FlutterNapi.attachToNative()`；
   Native 创建 `OHOSShellHolder`、`Shell`、`PlatformViewOHOS`。
3. 后续引擎通过 `spawn()` 创建，共享 VM 和部分底层资源，独立 Dart Isolate。

### 阶段三：FlutterView 与 XComponent 绑定

1. `FlutterAbilityAndEntryDelegate.createView()` 创建 `FlutterView`。
2. `FlutterView.attachToFlutterEngine()` 把 viewId 绑定到 `FlutterEngine`。
3. `FlutterNapi.xComponentAttachFlutterEngine()` 由 `XComponentAdapter` 关联
   `XComponent` 与 `shellHolderId`。
4. `XComponent` 的 `OnSurfaceCreated` 回调触发时，Native 拿到 `OH_NativeWindow`，
   调用 `PlatformViewOHOS::NotifyCreate()`。
5. `PlatformViewOHOS` 在 Raster 线程把 `OH_NativeWindow` 交给 `OHOSSurface`，
   完成 onscreen surface / swapchain 建立。

### 阶段四：首帧调度与显示

1. `Shell` 通过 `VsyncWaiterOHOS::AwaitVSync()` 等待 `OH_NativeVSync`。
2. VSync 到来后，UI 线程驱动 Framework Build/Layout/Paint，生成 LayerTree/DisplayList。
3. Raster 线程 `CreateRenderingSurface()`，`OHOSSurface` 创建 GPU Surface 并提交。
4. 图像通过 `OH_NativeWindow` 提交 `RenderService`。
5. 首帧完成后 Native `FlutterNapi.onFirstFrame()` 回调 ArkTS，再由
   `FlutterView.onFirstFrame()` 通知宿主。

## 渲染架构

### 渲染后端

- 软件渲染：兜底路径。
- Skia + OpenGL ES：传统 GPU 路径。
- Impeller + Vulkan：OHOS 重点优化路径，当前默认高性能路径。

`PlatformViewOHOS` 根据 `Settings.ohos_rendering_api` 构造：
`OhosContextGLSkia`+`OhosSurfaceGLSkia` / `OHOSContextVulkanImpeller`+`OHOSSurfaceVulkanImpeller`
/ `OHOSSurfaceSoftware`。

### 渲染提交链路

```
FlutterView → FlutterNapi(setViewportMetrics/updateSize/updateDensity)
  → PlatformViewOHOS(nativeSetViewportMetrics)
UI Thread → VsyncWaiterOHOS(AwaitVSync) → OH_NativeVSync(frame_time/target_time)
  → Build/Layout/Paint → submit LayerTree → Raster Thread
Raster → PlatformViewOHOS(CreateRenderingSurface) → OHOSSurface(CreateGPUSurface)
  → Draw/Submit → SwapBuffers/Present → OH_NativeWindow(queueBuffer) → RenderService
```

### OHOS 渲染适配特点

1. `FlutterView` 持续同步显示尺寸、像素密度、折叠屏特征、系统避让区、键盘区域、手势区域，
   汇总为 ViewportMetrics。
2. `PlatformViewOHOS` 缓存 `native_window`，支持 surface rebuild 和窗口变化后的上下文重建。
3. `OHOSSurfaceVulkanImpeller` 支持预热 `GPUSurface`，减少首帧前 Vulkan surface/swapchain
   冷启动成本。
4. `VsyncWaiterOHOS` 集成刷新率感知与投票机制，可与 LTPO 动态刷新率协同。

## 通信机制

### Dart 与 ArkTS/Native 的平台消息链路

```
Dart Platform Channel
  → Engine PlatformMessage
  → PlatformMessageHandlerOHOS
  → FlutterNapi / ArkTS handler
  → ArkTS plugin or system service
```

反向链路：ArkTS 调用 `FlutterNapi.dispatchPlatformMessage()` 或
`dispatchEmptyPlatformMessage()`，经 `PlatformViewOHOSNapi` 转发到
`PlatformViewOHOS::DispatchPlatformMessage()`，再送回 Dart。

### 系统通道

`FlutterEngine` 初始化时创建：`LifecycleChannel`、`NavigationChannel`、`TextInputChannel`、
`PlatformChannel`、`SystemChannel`、`LocalizationChannel`、`AccessibilityChannel`、
`SettingsChannel`、`DisplayMetricsChannel`、`NativeVsyncChannel`。

OHOS 宿主借此把生命周期、路由、键盘、系统设置、刷新率、本地化和无障碍注入 Framework。

## 输入、平台视图与纹理

### 输入事件

链路以 `XComponent` 为源头：

```
OH_NativeXComponent callback → XComponentBase → OhosTouchProcessor
  → PointerDataPacket → PlatformViewOHOS → Flutter Engine
```

- 触摸：转换为 Flutter `PointerDataPacket`
- 鼠标：按键、移动、离开、滚轮
- 轴事件：API 15+ 使用原生轴事件处理滚动
- 键盘：ArkTS 侧 `KeyboardManager`、`TextInputPlugin` 和系统通道协同

`OhosTouchProcessor` 对 OpenHarmony 某些重复 down/up 事件做了过滤，避免多指手势状态异常。

### 平台视图

ArkTS 侧 `PlatformViewsController` 主导，偏向"ArkUI 视图编排 + Flutter 纹理/布局协同"。
负责创建/销毁、尺寸/偏移管理、`PlatformViewWrapper`、纹理模式对接、ArkTS 原生节点挂入。

### 外接纹理

Native 侧 `OHOSExternalTexture` 统一抽象，按后端拆分 `OHOSExternalTextureGL` /
`OHOSExternalTextureGL`。典型场景：视频、相机、PixelMap、NativeImage。ArkTS 侧通过
`FlutterRenderer` 注册纹理，Native 创建生产者窗口、接收帧可用回调驱动重绘。

## 生命周期、资源与无障碍

### 生命周期同步

`FlutterAbilityAndEntryDelegate` 根据 `onShow`、`onHide`、`onPaused`、`onResumed`、
窗口焦点变化等事件，通过 `LifecycleChannel` 向 Flutter 下发生命周期状态。
Native 侧 `PlatformViewOHOS` 监听 `flutter/lifecycle` 平台消息，执行本地 GPU 资源回收。

### 资源管理

1. `OHOSAssetProvider` 直接从 HAP raw assets 提供 Flutter 资源。
2. `OHOSImageGenerator` 接入 OpenHarmony 图像解码，优先硬解码。
3. `PlatformViewOHOS` 生命周期切换时支持 GPU reclaim：前台恢复 `kRestore`，
   后台/隐藏/分离 `kAggressive`。

### 无障碍

- ArkTS 侧监听系统无障碍开关变化，通过 `FlutterNapi.accessibilityStateChange()` 下发。
- Native 侧 `SemanticsBridge` 维护 Flutter 语义树。
- `XComponentBase` 注册 `ArkUI_AccessibilityProvider`。
- API 15+ `MultiInstanceXCompAccessibility` 支持多 `XComponent` 实例。

## 架构特征总结

1. **适配层边界清晰**：Framework 和 Engine Core 保持通用，OHOS 差异集中在 ArkTS Embedding、NAPI、Native Embedder。
2. **宿主模型贴合 OpenHarmony**：以 `UIAbility + WindowStage + XComponent` 为宿主容器。
3. **渲染链路明确**：`FlutterView` 负责宿主窗口与 viewport，`PlatformViewOHOS`+`OHOSSurface`+`OHOSContext` 完成 GPU 提交。
4. **多引擎能力完整**：`FlutterEngineGroup`、`spawn()`、`preDraw()` 和预热机制。
5. **平台能力融合较深**：输入、刷新率投票、外部纹理、折叠屏特征、系统避让区和无障碍都已纳入。
