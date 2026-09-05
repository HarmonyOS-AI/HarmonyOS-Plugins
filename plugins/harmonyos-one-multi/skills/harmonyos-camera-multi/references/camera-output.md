# 相机旋转、拍照与录像输出

## 旋转的概念基线

搞不清这三个数，后面的公式全是猜：

| 概念 | 定义 | 值 |
|---|---|---|
| **镜头安装角** | 相机采集图像方向到设备自然方向的**顺时针**夹角 | 常见后置 90°、前置 270°，但业务代码必须读取设备信息或使用旋转接口 |
| 屏幕显示补偿角 | 等于屏幕旋转角度 | `display.rotation × 90` |
| 图像旋转角 | 镜头安装角 + 屏幕显示补偿角 | 推荐用接口取，别手算 |

前后摄的计算方向不同，但业务代码不要复制公式或硬编码安装角。实际开发使用
`getPreviewRotation` / `getPhotoRotation` / `getVideoRotation` 获取结果，公式只用于排查。

## 预览旋转与拍照旋转是两回事

| 用途 | 数据源 |
|---|---|
| **预览**旋转 | `getPreviewRotation()` / `display.rotation` |
| **拍照/录像**旋转 | **重力传感器** |

用 `display.rotation` 去定拍照方向会得到错误结果 —— 用户可能锁了屏幕方向，
但设备是斜着的。

`getPreviewRotation` / `setPreviewRotation` / `getPhotoRotation` / `getVideoRotation`
**都必须在 `session.commitConfig()` 之后**调用，提前调用抛 `SERVICE_FATAL_ERROR`。

`setPreviewRotation(rotation, isDisplayLocked)` 的第二个参数默认 `false`（跟随窗口旋转）；
传 `true` 表示只取镜头安装角、不跟窗口转。

录像方向另有一条链：`getVideoRotation(deviceDegree)` +
`avRecorder.updateRotation()`（必须在 `prepare` 之后的 `prepared` 状态调）。

### 重力角怎么取

`sensor.once(SensorId.GRAVITY)` 取一次重力数据算 `deviceDegree`。两条实践：

- **设备平放时重力数据无意义**（判据 `(x² + y²) × 3 < z²`），此时应**保留上一次的角度**，
  而不是算出一个随机方向
- 传感器数据要防抖平滑；`GRAVITY` 不可用时降级到 `ACCELEROMETER`

持握角度换算（候选知识；`GRAVITY` 无需权限声明）：

```typescript
degree = 90 - Math.round(Math.atan2(y, -x) / Math.PI * 180);  // 负值取模 360
```

按 degree 区间映射 `ImageRotation`，**前后摄映射不同**：

| degree 区间 | 后置 | 前置 |
|---|---|---|
| 0~30 或 300~360 | `ROTATION_0` | `ROTATION_0` |
| 30~120 | `ROTATION_90` | `ROTATION_270` |
| 120~210 | `ROTATION_180` | `ROTATION_180` |
| 210~300 | `ROTATION_270` | `ROTATION_90` |

拍照用 `photoOutput.capture({ rotation, mirror: isFront })`，录像把映射值写入
`AVMetadata.videoOrientation`（`avRecorder.updateRotation()` 须在 `prepared` 状态调用）。
公式只用于排查；业务代码仍优先用 `getPhotoRotation()` / `getVideoRotation()` 接口取值。

### 前摄自绘制归一化

当 **预览旋转角**（`getPreviewRotation` 的返回值，不是 `displayRotation`）
是 90° 或 270° 时：先加 180° 再旋转，然后水平翻转。
**只对前摄做**，后摄不适用。

### 镜像

```typescript
mirror: isFront && photoOutput.isMirrorSupported()
```

只判 `isMirrorSupported()` 会把后摄也开镜像。

**拍照/录像默认非镜像，需显式使能**：

- 普通照片以 `PhotoCaptureSetting.mirror` 属性为准；**动态照片/录像用 `enableMirror`**
  （对静态照片 `enableMirror(false)` 不生效）；
- **后置不支持镜像**（`isMirrorSupported=false`，强开会报错）；
- 录像镜像：`isMirrorSupported` 校验后 `enableMirror`，并联动
  `getVideoRotation` / `updateRotation` 更新旋转角；设备不支持时用 `rotate` 翻转预览
  XComponent + FFmpeg `hflip` 处理录像文件兜底。

### 旋转实现陷阱与替代方案

上面讲清了旋转的概念与映射。这里补实现层几个高频坑（候选知识，接入业务后按目标形态重验）。

**stale closure 陷阱**：注册时捕获的 rotation 是快照，回调触发时屏幕可能已再次旋转，值永远是旧的——必须在回调内重新读 `display.getDefaultDisplaySync().rotation`。

**全局清除陷阱**：`display.off('change')` 不传 callback 会清掉该事件下**所有**监听器（含其他组件的），是误删他人监听的高频坑。

```typescript
// ❌ stale closure
let rotation = display.getDefaultDisplaySync().rotation;
display.on('change', () => { this.mRotate = rotation * camera.ImageRotation.ROTATION_90; });  // 永远旧值

// ❌ 全局清除
display.off('change');  // 清掉所有组件的监听

// ✅ 正确：保存引用、回调内重读、精确 off
private onDisplayChange = (): void => {
  const newRotate = display.getDefaultDisplaySync().rotation * camera.ImageRotation.ROTATION_90;
  // ...
};
display.off('change', this.onDisplayChange);  // 防重复注册，先精确移除自身
display.on('change', this.onDisplayChange);
```

**先 setPreviewRotation 成功再更新状态的顺序约束**：`setPreviewRotation` 失败时不能更新 `mRotate` 和 XComponent 尺寸——否则 Surface 方向与 XComponent 方向不一致，画面错切。正确顺序：**先调用 `setPreviewRotation`（成功即返回），再更新 `mRotate`，最后调 `updateXComponentSize()`**。

```typescript
private onDisplayChange = (): void => {
  try {
    const newRotate = display.getDefaultDisplaySync().rotation * camera.ImageRotation.ROTATION_90;
    const previewRotation = this.previewOutput?.getPreviewRotation(newRotate);
    if (previewRotation === undefined) return;
    this.previewOutput?.setPreviewRotation(previewRotation, false);  // 先
    this.mRotate = newRotate;                                         // 再更新状态
    this.updateXComponentSize();                                      // 最后重算尺寸
  } catch (error) { /* log */ }
};
```

**bundleManager 异步取 targetVersion 后必须重算宽高**：判断旧平板（API 13 及以下）宽高逻辑相反需要 `targetVersion`，但它只能异步取——`getBundleInfoForSelf` 的 Promise 完成可能在 `aboutToAppear` 之后。**Promise resolve 后必须再调一次 `updateXComponentSize()`**，否则首次用 `targetVersion=0` 误判走错分支。

```typescript
aboutToAppear(): void {
  this.windowClass = AppStorage.get<window.WindowStage>('windowStage')!.getMainWindowSync();
  bundleManager.getBundleInfoForSelf(
    bundleManager.BundleFlag.GET_BUNDLE_INFO_WITH_APPLICATION
  ).then(data => {
    this.targetVersion = data.targetVersion;   // 50000013 = API 13
    this.updateXComponentSize();               // 关键：异步回来后重算
  }).catch(() => {});
  this.updateXComponentSize();                 // 首次（用 targetVersion=0 兜底）
}

private isLegacyTablet(): boolean {
  return deviceInfo.deviceType === 'tablet' && this.targetVersion <= 50000013;
}
```

**sensor.getSensorList 判 GRAVITY 降级 ACCELEROMETER**：取设备旋转角的完整实现要点——

1. `sensor.getSensorList()` 异步取设备传感器列表；
2. 含 `SensorId.GRAVITY` 则用 GRAVITY，否则降级到 `SensorId.ACCELEROMETER`；
3. `sensor.once(sensorId, cb)` 取一次数据；
4. `calcDegreeFromGravity`：设备接近水平时（`(x²+y²)×3 < z²`，约仰角 60°+）xy 分量太小 atan2 不稳定，返回 0°；
5. `getDeviceDegree` 失败返回 **-1**，调用方必须判 `< 0` 兜底为 0 再传入 `getPhotoRotation` / `getVideoRotation`，避免非法值进 SDK。

```typescript
async function getDeviceDegree(): Promise<number> {
  let sensors: sensor.Sensor[];
  try { sensors = await sensor.getSensorList(); }
  catch (error) { return -1; }
  const hasGravity = sensors.some(s => s.sensorId === sensor.SensorId.GRAVITY);
  const sensorId = hasGravity ? sensor.SensorId.GRAVITY : sensor.SensorId.ACCELEROMETER;
  return new Promise(resolve =>
    sensor.once(sensorId, (data) => resolve(calcDegreeFromGravity(data as sensor.GravityResponse)))
  );
}

const rawDegree = await getDeviceDegree();
const deviceDegree = rawDegree < 0 ? 0 : rawDegree;   // 兜底
```

> **待核实冲突**：本文「传感器权限映射」表标注 GRAVITY 无需权限；但相机旋转源案例代码注释写"GRAVITY 和 ACCELEROMETER 共用 `ohos.permission.ACCELEROMETER` 权限"。两份材料存在冲突，接入业务时以当前 SDK 文档与实际编译为准。

**XComponent.renderFit(RESIZE_COVER) 替代方案**：除手动算宽高外，可用 `XComponent.renderFit(RenderFit.RESIZE_COVER)` 实现居中裁剪，免去宽高计算。约束：API 18 之前 `renderFit` 仅支持 `RESIZE_FILL`，低版本工程误设 `RESIZE_COVER` 会渲染失败——按 `compatibleSdkVersion` 选择。

## 拍照与录像输出流

预览只是三条输出流之一。拍照/录像要单独建 `PhotoOutput` / `VideoOutput` 并正确接回调、走状态机，否则要么取不到数据，要么方向/帧率不对（候选知识，接入业务后按目标形态重验）。

### canAddOutput 门禁 + 双输出统一配置

预览 + 拍照两种输出必须在**同一次 `beginConfig → commitConfig` 之间**统一加入，不能临时在运行 Session 外拼接。提交前用 `canAddOutput` 做门禁，提前返回前必须释放已创建资源。

```typescript
session.beginConfig();
session.addInput(cameraInput);
if (!session.canAddOutput(previewOutput) || !session.canAddOutput(photoOutput)) {
  return;   // 提前返回前必须释放已创建资源
}
session.addOutput(previewOutput);
session.addOutput(photoOutput);
await session.commitConfig();
await session.start();
```

### PhotoOutput 完整回调链

1. 从当前 `CameraOutputCapability.photoProfiles` 选支持的 Profile（不可手造）；
2. `createPhotoOutput()` 创建并加入 Session；
3. 注册 `photoAvailable`，读取 `photo.main`（`image.Image`）；
4. `photoImage.getComponent(image.ComponentType.JPEG, cb)` 取 JPEG component，从 `component.byteBuffer` 取业务 buffer；保存媒体库走系统安全控件流程；
5. **buffer 处理完后必须 `photoImage.release()`，错误路径也要 release**——泄漏 Image 最终会让回调或 capture 停摆。

```typescript
photoOutput.on('photoAvailable', (error: BusinessError, photo: camera.Photo): void => {
  if (error || photo === undefined) return;
  const photoImage: image.Image = photo.main;
  photoImage.getComponent(image.ComponentType.JPEG,
    (err: BusinessError, component: image.Component): void => {
      try {
        if (!err && component) { /* 处理 component.byteBuffer */ }
      } finally {
        photoImage.release();   // 必须释放
      }
    });
});
```

`PhotoCaptureSetting.rotation` 由 `photoOutput.getPhotoRotation(deviceDegree)` 提供（`deviceDegree` 来自重力传感器，`getDeviceDegree` 返回 -1 时兜底为 0）。

### AVRecorder 录像状态机

录像方向与预览来源不同（重力传感器），状态机严格：

```
prepare()
  → state === 'prepared' 时调用 avRecorder.updateRotation(videoRotation)
    （videoRotation = videoOutput.getVideoRotation(deviceDegree)）
  → start()
```

**`updateRotation` 必须在 `prepare()` 之后、`start()` 之前，且 state 为 `prepared` 时调用**，其他时机无效。

```typescript
async function applyVideoRotation(
  videoOutput: camera.VideoOutput, deviceDegree: number, avRecorder: media.AVRecorder
): Promise<void> {
  try {
    const videoRotation = videoOutput.getVideoRotation(deviceDegree);
    if (avRecorder.state === 'prepared') {
      await avRecorder.updateRotation(videoRotation);
    }
  } catch (error) { /* log */ }
}
```

VideoProfile 选型需保证分辨率宽高比与预览一致、帧率不超设备上限（否则黑屏，如 Mate X6 不支持 60fps）。

### 帧事件监听与诊断日志清单

预览流加入 Session 后监听 `frameStart`、`frameEnd`、`error`。每次启动和形态变化至少记录：

```text
requested cameraPosition / selected cameraId / selected cameraPosition / cameraOrientation
foldStatus / supported cameraId+cameraPosition list / old→new cameraId
sceneMode
window width x height
preview display rect width x height
surface width x height
profile format / width x height
display.rotation
frameStart / frameEnd / PreviewOutput error
```

排查时全部打日志的事件清单：`frameStart` / `frameEnd` / `PreviewOutput error` / `CameraInput error` / `session error` / `cameraStatus`。

### 资源释放顺序（重建/退出前必走）

```
session.stop
  → PreviewOutput / PhotoOutput release
  → CameraInput close
  → session release
  → listener off
  → references = undefined
```

所有步骤**分别 try/catch**，前一步失败不跳过后续清理。

### 色彩与白平衡

- **强光拍照偏白 / 切摄像头后偏色 = 未开白平衡 + 未设置色彩空间**：默认 SDR 在强光、
  切换场景易偏色。`setWhiteBalanceMode` 开启白平衡（可配 `setWhiteBalance`），强光下用
  `setExposureBias` 减少曝光补偿；`setColorSpace` 设置色彩空间（支持 P3/HDR 时选广色域）；
- **照片模糊磨皮无质感 = 未启用 HDR Vivid**：`commitConfig` 前 `getSupportedColorSpaces`
  校验后 `setColorSpace(DISPLAY_P3)` 启用 HDR Vivid 拍照；
- **闪光灯先判支持性**：前置无闪光灯（`hasFlash` / `isFlashModeSupported` 均 false），
  直接 `setFlashMode` 报 7400102 闪退——前置隐藏/置灰闪光灯按钮，设置前判断支持性并 `try/catch`。

## 折叠屏无损出图

折叠屏上镜头安装角会随形态变化。不处理的话系统要靠裁剪来对齐方向，**损失 FOV**。

以下三步仅适用于 API 22 及以上，缺一不可：

1. `cameraInput.isPhysicalCameraOrientationVariable()` —— 该设备安装角是否可变
2. `cameraInput.getPhysicalCameraOrientation()` —— 取当前形态下的真实安装角
3. `cameraInput.usePhysicalCameraOrientation(true)` —— 启用无损出图

最低 API Level 低于 22 时不调用这些接口，继续使用系统默认出图路径。API 22+ 调用失败可能返回 **7400102**，必须退回默认出图，不能让相机因此无法启动。

---

## 帧率与功耗

- **录 60fps 必须选 [60,60] 的 VideoOutput profile**：`frameRateRange` 与录制目标一致；
  选了范围覆盖但非精确的 profile 实际只有 30fps；系统默认按范围内最大帧率出帧，
  动态设置后保持最大帧率属预期行为；
- **预览+录像两路流帧率必须一致**：不一致时系统丢高帧率流的帧做同步，实际帧率减半；
- **`setFrameRate` 先查后设**：重复设置当前已生效的相同帧率报 7400101（无效调用）、
  帧率不在支持列表报 7400110——设置前用 `getActiveFrameRate` 判同跳过、
  `getSupportedFrameRates` 查范围；
- **录像黑屏先查帧率规格**：部分设备（如 Mate X6）不支持 60fps，选了不支持的规格直接
  黑屏；用 `getSupportedOutputCapability` 查支持值，VideoOutput 分辨率与 AVRecorderProfile
  一致、帧率不超设备上限；
- **降功耗**：默认 30FPS 功耗高，业务允许时调到 25FPS 左右；用 DevEco Profiler 且断开
  USB 测试（DevEco Testing 工具本身消耗资源）。

---

