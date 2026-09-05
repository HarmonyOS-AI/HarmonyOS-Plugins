# 相机输出与帧处理修复案例

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

## 场景 3：拍照后画面旋转

### 问题描述

- 拍摄完成后，照片的实际内容与预期方向不符，发生 90°、180° 或 270° 的旋转。
- 设备旋转后拍照，照片方向未跟随设备持握方向。

### 根因分析

- 拍照时未设置 `rotation` 参数，或 `capture()` 调用未传入 `PhotoCaptureSetting`。
- 未监听重力传感器数据，无法获取设备当前持握方向。
- 前后置相机的旋转角度计算公式不同（前置用减法，后置用加法），混淆导致角度错误。

### 反例：拍照未设置旋转角度

> 来源：`PhotoRotated.ets`

```typescript
Button('拍照')
  .onClick(() => {
    if (this.photoOutput) {
      this.photoOutput.capture();
    }
  })
```

**问题点**：直接调用 `capture()` 未传入 `PhotoCaptureSetting`，照片旋转角度使用默认值，与设备实际持握方向不一致。

### 正例：基于重力传感器的拍照旋转

> 来源：`CameraPhoto.ets`（GoodCase）

```typescript
getCalDegree(x: number, y: number, z: number): number {
  let degree: number = 0;
  if ((x * x + y * y) * 3 < z * z) {
    return degree;
  }
  degree = 90 - (Number)(Math.round(Math.atan2(y, -x) / Math.PI * 180));
  return degree >= 0 ? degree % 360 : degree % 360 + 360;
}

capture(): void {
  let rotation: number = 0;
  let isFront: boolean | undefined = AppStorage.get('isFront');
  try {
    sensor.once(sensor.SensorId.GRAVITY, (data: sensor.GravityResponse) => {
      if (Math.abs(data.z) > OVERLOOKING_GRAVITY_OF_Z_AXIS) {
        rotation = this.lastRotation;
      } else {
        let degree: number = this.getCalDegree(data.x, data.y, data.z);
        if ((degree >= 0 && degree <= 30) || degree >= 300) {
          rotation = camera.ImageRotation.ROTATION_0;
        } else if (degree > 30 && degree <= 120) {
          rotation = isFront
            ? camera.ImageRotation.ROTATION_270
            : camera.ImageRotation.ROTATION_90;
        } else if (degree > 120 && degree <= 210) {
          rotation = camera.ImageRotation.ROTATION_180;
        } else if (degree > 210 && degree <= 300) {
          rotation = isFront
            ? camera.ImageRotation.ROTATION_90
            : camera.ImageRotation.ROTATION_270;
        }
      }

      let setting: camera.PhotoCaptureSetting = {
        quality: camera.QualityLevel.QUALITY_LEVEL_HIGH,
        rotation: rotation,
        mirror: isFront
      }
      this.photoOutput?.capture(setting);
    })
  } catch (error) {
    let err = error as BusinessError;
    console.error('MultiDeviceCamera', `Capture failed. Code: ${err.code}, message: ${err.message}`);
  }
}
```

### 通用修复方案

- 在拍照时使用 `sensor.once(sensor.SensorId.GRAVITY, callback)` 获取当前重力数据。
- 通过 `getCalDegree()` 计算设备持握角度，区分前后置相机的旋转映射。
- 使用 `photoOutput.capture(setting)` 传入 `PhotoCaptureSetting`，包含 `rotation` 和 `mirror` 参数。
- 前置相机需额外设置 `mirror: true` 实现镜像效果。

## 场景 4：预览画面旋转/拉伸

### 问题描述

- 相机预览画面方向与设备持握方向不一致。
- 预览画面出现拉伸或压缩变形。
- 窗口旋转后预览画面未跟随更新。

### 根因分析

- XComponent `onLoad` 中未调用 `setXComponentSurfaceRotation({ lock: true })` 解锁 Surface 旋转。
- `setupRotationListener` 中监听了 `display.on('change')` 但回调仅打印日志，未重新计算预览旋转角度和 Surface 宽高比。
- 未在 `commitConfig` 后调用 `getPreviewRotation` 获取预览旋转角度，或未调用 `setPreviewRotation` 设置旋转。
- Surface 宽高比与预览流旋转后的宽高比不一致。
- 未在 `onAreaChange` 或 `windowSizeChange` 回调中重新设置预览旋转角度和 Surface 尺寸。

### 反例：未设置预览旋转

> 来源：`PreviewRotated.ets`

```typescript
XComponent({
  id: 'cameraPreview',
  type: XComponentType.SURFACE,
  controller: this.xComponentController
}).onLoad(async () => {
  this.surfaceId = this.xComponentController.getXComponentSurfaceId();
  await this.initCamera();
})
```

**问题点**：`onLoad` 中未调用 `setXComponentSurfaceRotation` 解锁 Surface 旋转，也未设置预览旋转角度。

### 反例：未监听窗口变化

> 来源：`PreviewRotated.ets`

```typescript
setupRotationListener(): void {
  display.on('change', (rotation: number) => {
    console.info(TAG, `Rotation changed to: ${rotation * 90} degrees`);
  });
}
```

**问题点**：监听了 `display.on('change')` 但回调中仅打印日志，未重新计算和设置预览旋转角度。

### 正例：完整预览旋转适配

> 来源：`CameraPhoto.ets`（GoodCase）

```typescript
XComponent({
  id: 'cameraPreview',
  type: XComponentType.SURFACE,
  controller: this.xComponentController
}).onLoad(async () => {
  this.surfaceId = this.xComponentController.getXComponentSurfaceId();
  this.xComponentController.setXComponentSurfaceRotation({ lock: true });
  await this.initCamera();
})

updateSurfaceSize(): void {
  if (this.xComponentController && this.surfaceId) {
    let displayRotation: number = display.getDefaultDisplaySync().rotation * camera.ImageRotation.ROTATION_90;
    try {
      let previewRotation = this.previewOutput?.getPreviewRotation(displayRotation);
      if (previewRotation === 0 || previewRotation === 180) {
        this.xComponentController.setXComponentSurfaceRect({
          surfaceWidth: this.previewWidth,
          surfaceHeight: this.previewHeight
        });
      } else {
        this.xComponentController.setXComponentSurfaceRect({
          surfaceWidth: this.previewHeight,
          surfaceHeight: this.previewWidth
        });
      }
    } catch (error) {
      let err = error as BusinessError;
      console.error(`getPreviewRotation call failed. error code: ${err.code}`);
    }
  }
}
```

### 通用修复方案

- 在 XComponent `onLoad` 中调用 `setXComponentSurfaceRotation({ lock: true })` 解锁 Surface 旋转。
- 在 `commitConfig` 后调用 `getPreviewRotation(displayRotation)` 获取旋转角度，并调用 `setPreviewRotation` 设置。
- 监听窗口变化事件（通过 `onAreaChange`），在变化时重新计算 Surface 宽高比。
- Surface 宽高比计算规则：`display.rotation` 为 0°/180° 时 Surface 比例是预览比例的倒数；90°/270° 时与预览比例相同。
- 折展场景的完整链路（基准比例、letterbox 拟合、阔折叠外屏 1:1、双监听时序）见 `../camera-fold.md`「折展防拉伸链路」；重建时实时计算比例基准，不读 `windowSizeChange` 缓存的断点。

## 场景 5：录像/直播画面旋转

### 问题描述

- 录像开始后画面方向与设备持握方向不一致。
- 录像过程中旋转设备，录制画面方向未更新。

### 根因分析

- 录像开始时未获取当前重力传感器数据计算旋转角度。
- `AVMetadata.videoOrientation` 未设置或设置值不合理。
- 录像输出流与预览输出流分辨率宽高比不一致。

### 反例：录像未设置旋转角度

> 来源：`VideoRotated.ets`

```typescript
async prepareVideo(videoProfile: camera.VideoProfile, rotation: number): Promise<camera.VideoOutput | undefined> {
  if (this.videoFile) {
    let avMetadata: media.AVMetadata = {
      videoOrientation: rotation.toString(),
    }
    this.recordSurfaceId = await this.getVideoSurfaceId({
      videoSourceType: media.VideoSourceType.VIDEO_SOURCE_TYPE_SURFACE_YUV,
      profile: {
        fileFormat: media.ContainerFormatType.CFT_MPEG_4,
        videoBitrate: 100000,
        videoCodec: media.CodecMimeType.VIDEO_AVC,
        videoFrameWidth: videoProfile.size.width,
        videoFrameHeight: videoProfile.size.height,
        videoFrameRate: this.cameraPosition === camera.CameraPosition.CAMERA_POSITION_BACK ? 60 : 30,
      },
      url: `fd://${this.videoFile.fd}`,
      metadata: avMetadata
    })
  }
  return
}
```

**问题点**：`prepareVideo` 接收 `rotation` 参数但该参数来自 `this.sensorRotation`，而 `sensorRotation` 在 `setupRotationListener` 中为空实现，未被正确赋值。

### 正例：录像前获取重力传感器角度

> 来源：`CameraVideo.ets`（GoodCase）

```typescript
async startVideo(): Promise<void> {
  sensor.once(sensor.SensorId.GRAVITY, async (data: sensor.GravityResponse) => {
    let isFront = this.cameraPosition === camera.CameraPosition.CAMERA_POSITION_FRONT;
    if (Math.abs(data.z) > OVERLOOKING_GRAVITY_OF_Z_AXIS) {
      this.sensorRotation = this.lastRotation;
    } else {
      let degree: number = this.getCalDegree(data.x, data.y, data.z);
      if ((degree >= 0 && degree <= 30) || degree >= 300) {
        this.sensorRotation = isFront
          ? camera.ImageRotation.ROTATION_270
          : camera.ImageRotation.ROTATION_90;
      } else if (degree > 30 && degree <= 120) {
        this.sensorRotation = isFront
          ? camera.ImageRotation.ROTATION_180
          : camera.ImageRotation.ROTATION_180;
      }
    }
    await this.prepareVideo(this.videoProfile!, this.sensorRotation);
  });
}
```

### 通用修复方案

- 录像开始前使用 `sensor.once(sensor.SensorId.GRAVITY)` 获取当前重力数据。
- 计算设备持握角度，区分前后置相机映射到正确的 `ImageRotation` 值。
- 将旋转角度传入 `AVMetadata.videoOrientation`（合理值为 0、90、180、270）。
- 预览流与录像输出流的分辨率宽高比必须保持一致。

## 场景 6：预览画面花屏堆叠

### 问题描述

- 通过 ImageReceiver 获取预览帧数据后送显，画面出现花屏堆叠状。
- 花屏表现为图像行偏移、内容错位。

### 根因分析

- stride（图像一行在内存中实际占用字节数）通常因内存对齐大于 width。
- 直接按 `width × height` 读取图像数据，将无效填充字节当作有效像素，导致行偏移。
- stride 值因平台而异，不可硬编码。

### 反例：未处理 stride

```typescript
imageReceiver.on('imageArrival', () => {
  imageReceiver.readNextImage((err, image) => {
    let component = image.getComponent(image.ComponentType.JPEG, (err, component) => {
      let pixelMap = image.createPixelMap(component.byteBuffer, {
        size: { width: 1080, height: 1080 }
      });
      this.stridePixel = pixelMap;
    });
  });
});
```

**问题点**：直接使用 `component.byteBuffer` 创建 PixelMap，未检查 `rowStride` 是否与 `width` 一致。

### 正例一：拷贝有效像素到新 buffer

```typescript
imageReceiver.on('imageArrival', () => {
  imageReceiver.readNextImage((err, image) => {
    let component = image.getComponent(image.ComponentType.JPEG, (err, component) => {
      let width = component.size.width;
      let height = component.size.height;
      let stride = component.rowStride;

      if (stride === width) {
        let pixelMap = image.createPixelMap(component.byteBuffer, {
          size: { width: width, height: height }
        });
        this.stridePixel = pixelMap;
      } else {
        let srcArr = new Uint8Array(component.byteBuffer);
        let dstArr = new Uint8Array(width * height);
        for (let row = 0; row < height; row++) {
          let srcOffset = row * stride;
          let dstOffset = row * width;
          for (let col = 0; col < width; col++) {
            dstArr[dstOffset + col] = srcArr[srcOffset + col];
          }
        }
        let pixelMap = image.createPixelMap(dstArr.buffer, {
          size: { width: width, height: height }
        });
        this.stridePixel = pixelMap;
      }
    });
  });
});
```

### 正例二：使用 cropSync 裁剪

```typescript
if (stride !== width) {
  let pixelMap = image.createPixelMap(component.byteBuffer, {
    size: { width: stride, height: height }
  });
  pixelMap.cropSync({ x: 0, y: 0, size: { width: width, height: height } });
  this.stridePixel = pixelMap;
}
```

### 通用修复方案

- 通过 `component.rowStride` 获取实际 stride 值（运行时获取，不可硬编码）。
- stride = width 时可直接使用；stride ≠ width 时需去除无效像素。
- 方案一（buffer 拷贝）：逐行拷贝有效像素到新 buffer，用 `width × height` 创建 PixelMap。适用于需要精确像素数据的场景。
- 方案二（cropSync）：按 `stride × height` 创建 PixelMap，调用 `cropSync()` 裁剪多余像素。适用于快速修复场景。
