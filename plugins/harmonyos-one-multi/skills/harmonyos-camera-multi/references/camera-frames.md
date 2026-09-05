# 预览帧与 stride 处理

## 预览帧 stride 花屏

仅用 XComponent 展示预览不需要管 stride；**通过 `ImageReceiver` 的 `imageArrival` 取每帧做二次处理**（二维码/人脸识别、送显 PixelMap）时才涉及。

### 概念与判断

| 概念 | 说明 |
|---|---|
| stride | 图像一行在内存中实际占用的字节数，因内存对齐通常大于 `width` |
| `rowStride` | 帧数据的实际 stride，来自 `image.Component.rowStride`，**因平台而异，不可硬编码** |
| 花屏原因 | 按 `width × height` 解析时，把每行末尾 `stride − width` 个无效填充字节当成了像素，导致行偏移、画面堆叠 |

**排查提示**：预览帧 buffer 解析后出现花屏堆叠状，先查 `rowStride` 是否等于 `width`。

### 两种修法

| 方案 | 做法 | 适用 |
|---|---|---|
| **buffer 逐行拷贝** | 按行从 byteBuffer 拷贝有效像素（每行前 `width` 字节）到新 buffer，再按 `width × height` 建 PixelMap | 需要精确像素数据或二次加工 |
| **cropSync 裁剪** | 先按 `stride × height` 建 PixelMap，再 `cropSync({ x: 0, y: 0, size: { width, height } })` 裁掉填充 | 快速修复、直接送显 |

两种方案都要先判 `stride === width`，相等时直接用 `component.byteBuffer`，不拷贝。

### 约束（缺一条都会复现或泄漏）

- **`rowStride` 运行时获取，禁止硬编码**——同一份代码跑在不同平台，stride 值不同；
- NV21 格式总字节数为 `width × height × 1.5`，逐行拷贝要处理 `height × 1.5` 行（前 `height` 行 Y、后 `height/2` 行 VU 交错），不是 `height` 行；
- 每次 `readNextImage` 取帧后必须 `nextImage.release()`，否则帧资源泄漏；
- `cropSync` 可能抛异常，必须 `try/catch` 捕获 `BusinessError`，失败时保留旧 PixelMap 并释放新建的。

### 验证清单

- [ ] `stride === width` 时直接建 PixelMap 正常；
- [ ] `stride ≠ width` 时两种修法都能正确去除无效像素、无花屏；
- [ ] 每次取帧后都调用了 `nextImage.release()`；
- [ ] 已记录目标平台实测 stride 值。

### 帧格式映射表

`nextImage.format` 由创建预览流时的 `CameraFormat` 决定；转 PixelMap 时按它选
`PixelMapFormat` 和单位像素字节数，**不能固定写死一种**：

| CameraFormat 值 | nextImage.format | PixelMapFormat | 单位像素字节数 | 适用输出流 |
|---|---|---|---|---|
| `CAMERA_FORMAT_YUV_420_SP` | 25 | `image.PixelMapFormat.NV21` | 1.5 | 预览流、视频流（NORMAL_VIDEO） |
| `CAMERA_FORMAT_YCBCR_P010` | 35 | `image.PixelMapFormat.YCBCR_P010` | 3 | 预览流、视频流 |
| `CAMERA_FORMAT_YCRCB_P010` | 36 | `image.PixelMapFormat.YCRCB_P010` | 3 | 预览流、视频流 |

P010 格式单位像素字节数取 1.5 会缓冲区越界（`createPixelMap` 时 SIGSEGV 闪退）；
普通录像选到 P010（2002）VideoProfile 会录出损坏文件——**普通录像选 YUV_420_SP（1003），
P010 必须走 HDR 录像**（配 `isHdr=true`）。

同族两个坑：

- **两次进入预览流要固定同一格式的 Profile**：首次进入用 2002、重进用 1003，而转换代码
  固定按 NV21 处理，表现为"首次花屏、重进正常"；
- **ImageReceiver 单路即可无感拍照**（不展示预览界面）：定时器 + `canIProcess` 节流，
  **跳过的帧必须 `nextImage.release()`**，否则帧队列阻塞导致后续取帧失败。

---

