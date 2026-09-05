# 折叠形态相机修复案例

## 目的

统一沉淀相机相关问题修复方法，所有修复场景使用同一结构输出：

- 问题描述
- 根因分析
- 通用修复方案

本文件只保留通用方案，不绑定特定页面、业务或产品案例。

## 使用方式

1. 先识别问题类型，定位到对应场景。
2. 按"问题描述 -> 根因分析 -> 通用修复方案"执行。
3. 修复后执行基本编译；设备运行与证据回写由调用方流程负责。

## 场景 1：折叠态切换后黑屏

### 问题描述

- 折叠屏设备在折叠/展开切换后，相机预览页面出现黑屏。
- 页面可见但 XComponent 无画面输出。

### 根因分析

- 折叠前选择的相机设备在折叠后不再可用（如外屏仅有前置相机）。
- 未监听 `foldStatusChange` 事件，或监听后未完整重建相机会话。
- 半折叠与展开之间的切换可能不需要重建相机，但未做过滤导致不必要的重建失败。

### 反例：未监听折叠状态变化

> 来源：`BlackScreen.ets`

```typescript
aboutToAppear(): void {
  this.requestCameraPermission();
  this.setupRotationListener();
  this.getCurrentFoldStatus();
}

setupFoldStatusListener(): void {
  display.on('foldStatusChange', (foldStatus: display.FoldStatus) => {
    this.currentFoldStatus = foldStatus;
    this.handleFoldStatusChange();
  });
}
```

**问题点**：`aboutToAppear` 中调用了 `setupRotationListener` 但未调用 `setupFoldStatusListener`，折叠状态变化后无法感知和响应。

### 反例：热启动未恢复相机

> 来源：`BlackScreen.ets`

```typescript
aboutToAppear(): void {
  this.requestCameraPermission();
  this.setupFoldStatusListener();
  this.setupRotationListener();
  this.getCurrentFoldStatus();
}
```

**问题点**：缺少 `onPageShow` 生命周期回调，页面热启动（从后台恢复）时不会重新初始化相机，导致黑屏。

### 正例：完整生命周期管理

> 来源：`CameraPhoto.ets`（GoodCase）

```typescript
onPageShow(): void {
  if (this.photoSession) {
    this.requestCameraReload(); // 热启动和折展共用唯一串行队列
  }
}

aboutToAppear(): void {
  this.requestCameraPermission();
  this.setupFoldStatusListener();
  this.setupRotationListener();
  this.getCurrentFoldStatus();
}

aboutToDisappear(): void {
  this.cameraActive = false;
  display.off('foldStatusChange', this.foldStatusCallback);
  display.off('change', this.displayChangeCallback);
  this.cameraReloadQueue.requestTeardown();
}
```

### 通用修复方案

- 在 `aboutToAppear` 中注册 `foldStatusChange` 监听。
- 在 `onPageShow` 中判断 `photoSession` 是否存在，若存在则请求统一重建队列恢复相机；不得绕过队列直调 `initCamera()`。
- 折叠状态变化时完整执行：消费回调 `supportedCameras` → 按原 `cameraPosition` 选中目标 → 释放旧会话 → 创建 CameraInput → 创建 PreviewOutput → 创建 Session → commitConfig → start。
- 使用 display 监听时，仅 `HALF_FOLDED ↔ EXPANDED` 可依据实测相机集合跳过；不要把豁免扩展到 `HALF_FOLDED ↔ FOLDED`。

## 场景 2：开合后相机设备未切换

### 问题描述

- 折叠屏折叠/展开后，相机仍使用旧设备（如外屏仍在使用后置相机）。
- 折叠态使用前置镜头，展开后画面意外变成后置，自拍语义和镜像状态不连续。
- 阔折叠外屏（如 PuraX）仅有前置相机，切换到外屏后后置相机查找失败。

### 根因分析

- 监听了 `foldStatusChange`，但回调中仅重新选择预览分辨率，未重新选择相机设备。
- 相机层回调虽然提供了 `supportedCameras`，实现却只记录日志，重建时再次查询，形成状态时序窗口。
- 相机选择逻辑未保持用户请求的 `cameraPosition`；目标位置未命中时静默使用 `cameras[0]`，而第一个设备可能是后置。
- 页面重建后前后置状态恢复默认值，`onPageShow` 按错误位置重新开流。

### 反例：仅更新预览流未重建相机设备

> 来源：`CameraNoSwitch.ets`

```typescript
async reinitCameraForFoldChange(): Promise<void> {
  if (this.cameraManager && this.cameraInput) {
    const cameras = this.cameraManager.getSupportedCameras();
    const currentCamera = cameras.find(cam => cam.cameraPosition === this.cameraPosition) || cameras[0];

    const cameraOutputCapability = this.cameraManager.getSupportedOutputCapability(
      currentCamera, camera.SceneMode.NORMAL_PHOTO
    );

    const newPreviewProfile = this.selectPreviewProfileForFold(
      cameraOutputCapability.previewProfiles, this.displayRatio
    );

    if (newPreviewProfile && this.previewOutput) {
      this.photoSession?.beginConfig();
      this.photoSession?.removeOutput(this.previewOutput);
      this.previewOutput = this.cameraManager.createPreviewOutput(newPreviewProfile, this.surfaceId);
      this.photoSession?.addOutput(this.previewOutput);
      await this.photoSession?.commitConfig();
      await this.photoSession?.start();
      this.updateSurfaceSize();
    }
  }
}
```

**问题点**：折叠状态变化后仅更新了 PreviewOutput，未释放旧的 CameraInput 和 Session 并重新选择相机设备。当折叠前的相机不再可用时，`getSupportedCameras()` 返回的列表中可能不包含旧相机。

### 反例：未命中目标位置后静默选择第一个设备

```typescript
let deviceIndex = cameras.findIndex((device: camera.CameraDevice) =>
  device.cameraPosition === this.requestedPosition);
if (deviceIndex === -1) {
  deviceIndex = 0; // cameras[0] 可能是 BACK，破坏前置连续性
}
```

**问题点**：防止数组越界不等于允许改变相机语义。跨 FRONT/BACK 的 fallback 必须是经确认的产品策略，并同步位置、镜像和控件状态。

### 正例：完整重建相机链路

> 来源：`CameraPhoto.ets`（GoodCase）

```typescript
async initCamera(supportedCameras?: Array<camera.CameraDevice>): Promise<boolean> {
  this.cameraManager = this.cameraManager ?? camera.getCameraManager(this.context);
  // cameraManager.foldStatusChange 已提供集合时直接消费该快照；display 方案才重新查询。
  const cameras = supportedCameras ?? this.cameraManager.getSupportedCameras();
  const targetCamera = this.selectCameraForIntent(
    cameras,
    this.requestedCameraPosition,
    camera.ConnectionType.CAMERA_CONNECTION_BUILT_IN,
    this.currentCameraDevice?.cameraId
  );

  if (!targetCamera) {
    // 保留 requestedCameraPosition；遮住预览、禁用拍摄，并串行释放可能失效的旧链。
    console.error(`Requested camera position is unavailable: ${this.requestedCameraPosition}`);
    await this.enqueueUnavailableTeardown();
    return false;
  }

  await this.releaseCamera();
  this.cameraInput = this.cameraManager.createCameraInput(targetCamera);
  await this.cameraInput.open();

  const cameraOutputCapability = this.cameraManager.getSupportedOutputCapability(
    targetCamera, camera.SceneMode.NORMAL_PHOTO
  );

  const previewProfile = this.selectPreviewProfileForFold(
    cameraOutputCapability.previewProfiles, this.displayRatio
  );
  this.previewWidth = previewProfile.size.width;
  this.previewHeight = previewProfile.size.height;

  this.previewOutput = this.cameraManager.createPreviewOutput(previewProfile, this.surfaceId);

  this.photoSession = this.cameraManager.createSession<camera.PhotoSession>(camera.SceneMode.NORMAL_PHOTO);
  this.photoSession.beginConfig();
  this.photoSession.addInput(this.cameraInput);
  this.photoSession.addOutput(this.previewOutput);
  await this.photoSession.commitConfig();
  await this.photoSession.start();
  this.currentCameraDevice = targetCamera; // start 成功后再提交实际 cameraId/position。
  this.updateSurfaceSize();
  return true;
}
```

### 通用修复方案

- 优先使用 `cameraManager.on('foldStatusChange')` 返回的 `supportedCameras`，把集合快照传入串行重建；不要只打印后再次查询。
- 把用户请求的 `cameraPosition` 与当前设备分开持久化，避免 XComponent/页面重建恢复默认值；物理 `cameraId` 可随形态变化，实际 `cameraPosition` 不得静默变化。
- 先从新集合选中目标，再执行完整 `releaseCamera()` → `initCamera()`；未命中时保留位置意图，遮罩并串行释放旧链后受控重试/提示，不默认使用 `cameras[0]`。
- 同位置多个候选时优先仍可用的当前 ID，否则按已明确的镜头角色/类型选择；不得依赖列表第一个元素。
- 每次形态事件都推进 generation；旧任务在异步边界检查是否过期，过期后只清理、不提交设备状态，快速开合只执行最新终态。
- 显式区分首次 `BOOTSTRAP`、计划就绪和 `UNAVAILABLE`；最新快照无目标时迟到 `onLoad` 不得再查询旧列表，并把旧链 release 作为同一串行队列中的工作项。
- 防抖要区分“计时中”和“已翻转等待 onLoad”，两个 XComponent 使用独立 Controller，Surface 变更也纳入 generation。
- 终态回调一到就用不透明遮罩隔离旧预览并禁用拍照/录像；防抖只合并打开最新目标，不能让旧链在窗口期继续对用户可见或可拍。
- 记录 requestedPosition、旧/新 cameraId、实际 position 和 supportedCameras，区分应用 fallback、系统自动前摄切换与“同一镜头相对新屏幕朝向变化”。

## 场景 7：阔折叠外屏后置相机不可用

### 问题描述

- 在阔折叠外屏上选择后置相机失败。
- 相机初始化抛出异常或预览黑屏。

### 根因分析

- 阔折叠外屏（如 PuraX）仅有前置相机。
- 相机选择逻辑未考虑目标位置相机不存在的情况。

### 通用修复方案

- 选择相机时使用 `findIndex` 查找目标位置相机。
- 已有预览或用户主动切镜时，若目标位置不存在则保持当前相机不变，并反馈不可用。
- 首次启动时只有产品策略明确允许“任意可用相机”才可选择其他位置；选择后必须同步实际 `cameraPosition`、镜像和控件状态。
- 折展切镜不得用 `cameras[0]` 作为通用 fallback，应保持原位置意图并等待当前形态对应的物理镜头。

## 场景 8：折展后画面不旋转、拉伸且有黑边（方向冻结复合症状）

> 阔折叠机型（内外屏比例不同、外屏接近方屏）折展路径的典型复合症状：折叠态（外屏）→ 展开态（内屏）后画面保持横屏不旋转，横向画面内容被拉伸，且两侧留黑边未占满。三个症状是同一根因链的三级表现。

### 问题描述

- 折叠→展开后窗口仍保持横屏，把设备竖过来也不旋转（方向冻结）。
- 预览内容相对窗口被拉伸/压扁，重算 Surface 矩形也不恢复。
- 画面两侧（或上下）留黑边，未按新形态占满。
- 折叠态（外屏）横屏使用时一切正常，只有展开后异常。

### 根因分析（复合，按因果顺序）

1. **方向策略枚举错误**：展开态（窗口最小边 ≥ 600vp）把方向设成 `window.Orientation.UNSPECIFIED`，期望"跟随系统旋转"。`UNSPECIFIED` 是"未定义、由系统判定"，不跟随传感器；展开瞬间窗口保持横屏后不再旋转。正确枚举是 `AUTO_ROTATION_RESTRICTED`。
2. **去重缓存把恢复设置吃掉**：本地 `lastOrientation` 与目标值相同就跳过 `setPreferredOrientation`。折展时系统可能重置窗口方向状态、异步设置也可能失败，缓存命中≠仍然生效；先记缓存再异步设置且失败不回滚，方向就永久冻结在折展前。
3. **重建早于窗口稳定 + 基准变化不重建流**：`foldStatusChange` 回调时刻 `windowRect`/断点/`display.rotation` 还是外屏的值，重建的流按外屏基准（阔折叠外屏 `WIDTH_SM + HEIGHT_MD` → 1:1）选 Profile；窗口随后变成内屏比例，`windowSizeChange` 只重算 Surface 矩形（按新基准 4:3 letterbox）而不重建流——流 1:1、矩形 4:3，两端失配即拉伸。
4. **黑边是方向冻结 + letterbox 的几何结果**：窗口保持横屏时，矩形按 4:3 基准在横窗口内 letterbox 拟合，宽度方向必然留黑边。方向恢复竖屏后黑边只剩上下（设计的 letterbox 余量），症状随之消失大半。

### 反例：UNSPECIFIED + 去重跳过

```typescript
updateOrientation(): void {
  let rect: window.Rect = this.mainWindow.getWindowProperties().windowRect;
  let minEdgeVp: number = Math.min(rect.width, rect.height) / densityPixels;
  let orientation: window.Orientation =
    minEdgeVp >= 600 ? window.Orientation.UNSPECIFIED : window.Orientation.PORTRAIT; // 错：UNSPECIFIED 不跟随传感器
  if (orientation === this.lastApplied) {
    return; // 错：折展后系统可能重置方向状态，缓存命中不等于仍然生效
  }
  this.lastApplied = orientation; // 错：先记缓存，异步失败不回滚
  this.mainWindow.setPreferredOrientation(orientation);
}
```

**问题点**：三处叠加后，折叠态（外屏横屏）→ 展开的路径上没有任何一次有效的方向设置：fold 回调时窗口还是旧尺寸算出同值被去重跳过；`windowSizeChange` 时目标值仍等于缓存再次跳过；即使设置，`UNSPECIFIED` 也不会让窗口跟随传感器旋回竖屏。

### 正例：AUTO_ROTATION_RESTRICTED + 结果驱动的去重 + 窗口稳定后重估

```typescript
// 方向随 windowSizeChange（窗口已稳定）重估，按设置结果维护去重缓存
private lastApplied?: window.Orientation;

updateOrientation(): void {
  let rect: window.Rect = this.mainWindow.getWindowProperties().windowRect;
  let minEdgeVp: number = Math.min(this.uiContext.px2vp(rect.width), this.uiContext.px2vp(rect.height));
  let orientation: window.Orientation =
    minEdgeVp >= 600 ? window.Orientation.AUTO_ROTATION_RESTRICTED : window.Orientation.PORTRAIT;
  this.mainWindow.setPreferredOrientation(orientation).then(() => {
    this.lastApplied = orientation; // 只有设置成功才更新缓存
  }).catch((error: BusinessError) => {
    this.lastApplied = undefined; // 失败立即失效，下次重设
  });
}

// 页面 foldStatusChange：退出半折叠/展开终态恢复自动旋转，矩形按新基准处理
if (this.curWidthBp !== WidthBreakpoint.WIDTH_SM) {
  this.mainWindow.setPreferredOrientation(window.Orientation.AUTO_ROTATION_RESTRICTED); // 终态无条件恢复
}
```

配套要求：重建流前重读当前窗口（防抖结束后比对），基准比例变化（4:3↔1:1）时走完整重建重选 Profile，见 `../camera-fold.md`「折展防拉伸链路」第 6、7 条。

### 通用修复方案

- 展开态/平板（最小边 ≥ 600vp）用 `AUTO_ROTATION_RESTRICTED`，sm 锁 `PORTRAIT`；`UNSPECIFIED` 不是通用恢复值。
- 方向策略在 `windowSizeChange`（窗口尺寸已稳定）重估；`foldStatusChange` 时刻窗口还是旧值，不作为方向选型依据。
- 去重缓存以 `setPreferredOrientation` 的 promise 结果维护：成功才更新、失败即失效；折展终态可无条件重设。
- 半折叠（MD 断点且横屏）锁 `LANDSCAPE`；退出半折叠时若 `widthBp !== WIDTH_SM` 恢复 `AUTO_ROTATION_RESTRICTED`，并按新形态重算 Surface 矩形。
- 折展终态重建以窗口稳定为门槛；基准比例变化必须重建流，见 `../camera-fold.md`「折展防拉伸链路」。
- 验证顺序：先确认窗口方向随设备姿态正确旋转（hilog/旋转角度），再验证流与矩形基准同源，最后看黑边是否只剩 letterbox 设计余量。

## 场景 9：折展后画面视野变窄或变窄条（旧基准流固化）

> 折叠态→展开态后的两种典型表现，同一根因：后置画面视野变窄（观感"焦距变大"）；前置画面变成窄竖条、宽度未铺满窗口。此时方向、拉伸往往都已正确，唯独流本身不对。

### 问题描述

- 折叠→展开后，后置预览视野比折叠态明显变窄，同距离物体显示更大（"焦距被拉大"）。
- 折叠→展开后，前置预览呈窄竖条，宽度明显小于窗口，左右留黑边，像切到了"竖屏拍摄模式"。
- `windowSizeChange` 后重算 Surface 矩形也不改善——因为矩形与流是同源的，错的是流。

### 根因分析

1. **重建流的时机早于窗口稳定**：重建由相机层 `foldStatusChange`（`supportedCameras` 快照）驱动，该事件在系统切换显示之前到达；即使防抖 100–200ms 后重读断点/窗口，折叠屏窗口迁移叠加方向策略生效常需数百毫秒，读到的仍是外屏旧值——形态基准仍判为 1:1。
2. **窗口稳定后无基准比对兜底**：`windowSizeChange` 回调只按已提交流的实际比例重算 Surface 矩形（几何上不拉伸），从不比较"当前形态基准"与"建流时的基准"，旧基准的流一直留在新形态里。
3. **fallback 放大症状**：内屏摄像头常无 1:1 档，筛不到基准档时若回退"最高分辨率"，可能选中 16:9 裁切档——视野进一步收窄（后置观感"焦距变大"）；16:9 流经预览旋转配竖窗口后呈 9:16 窄条（前置"宽度未铺满"）。1:1 档本身也是 sensor 裁切，FOV 本就比 4:3 全幅窄，大屏上放大显示后观感更明显。

### 反例：固定防抖当稳定门槛 + 只重算矩形

```typescript
// 防抖回调里"重读刷新"——若窗口迁移未完成，读到旧断点，基准仍是外屏 1:1
setTimeout(() => {
  this.pendingPlan = this.buildPlan(snapshot); // 内部按当前断点定基准，此刻仍是旧值
  this.flipSurfaceFlag();
}, 150); // 错：固定时长不是窗口稳定判据

// windowSizeChange 回调：只重算矩形，永不纠正流
onWindowResized(): void {
  this.applySurfaceRect(); // 错：无"实时基准 vs 建流基准"比对，旧基准流固化
}
```

### 正例：建流记录基准 + 窗口事件兜底比对 + 首档 fallback

```typescript
// 建流成功后记录建流时刻的形态基准（走了 fallback 连同实际档位比例一起记）
this.committedBaseline = this.formBaseline;       // 4/3 或 1
this.committedStreamRatio = profile.size.width / profile.size.height;

// windowSizeChange 回调：先比对基准，再决定重算矩形还是重建流
onWindowResized(): void {
  this.refreshFormBaseline();                     // 实时按当前窗口/断点重算
  if (this.formBaseline !== this.committedBaseline) {
    this.requestCameraReload();                   // 基准变了：走完整重建队列
    return;
  }
  this.applySurfaceRect();                        // 基准没变：纯尺寸变化才只算矩形
}

// 筛不到基准档：回退列表首档（默认推荐档），不盲选最高分辨率
let profile = this.pickByRatio(baseline) ?? previewProfiles[0];
```

### 通用修复方案

- 流的创建以窗口稳定为准：推迟到该形态 `windowSizeChange` 到达之后，或在 `windowSizeChange` 回调里比对"实时基准 vs 建流基准"兜底重建；固定时长防抖只用于合并事件，不作为稳定判据。
- 建流成功时记录建流基准与实际流比例；基准比对不同才重建，相同才允许只重算矩形。
- 筛不到基准比例档位时回退 `previewProfiles` 列表首档并按实际比例 letterbox，禁止盲选最高分辨率（16:9 裁切档收窄视野）。
- 验证时记录：建流时刻的窗口尺寸与基准、`windowSizeChange` 到达时刻的窗口与基准、当前 Profile `size`——三者能拼出"流是否按稳定后的窗口创建"的完整证据链。
