# 相机能力、权限与生命周期

## 能力检测是两套机制，不是一套

**多设备下这两步都要做，只做一步必然在某类设备上崩：**

| 机制 | 判什么 | 例子 |
|---|---|---|
| `canIUse('SystemCapability.xxx')` | **设备类型间**的能力差异 | 手表没有相机 SysCap |
| `isXxxAvailable()` / `isXxxSupported()` 能力查询接口 | **同类型不同型号**的差异 | 同是手机，有的没有长焦 |

完整调用链：`canIUse` → 能力查询 → 业务调用。
没有能力查询接口时，用**错误码兜底**——`801` 就是"能力不支持"，
所有可能触发它的调用都要 `try/catch`，不能让它冒到用户面前。

单设备工程（`deviceTypes` 只有一个）可以跳过 `canIUse`；一多工程不行。

**SysCap 字符串不能凭记忆拼**——它是设备级的，不细分到具体硬件，
`SystemCapability.Multimedia.Camera.Core.Front` 这种写法不存在，
拼错后 `canIUse` 恒返回 `false`，静默走进降级分支且毫无报错。
SysCap 字符串必须通过 SDK `device-define`、官方文档或 `devecocli docs` 核对。

### 并集/交集规则（多设备场景的关键）

`module.json5` 的 `deviceTypes` 配置多个设备类型时，工程可用的 SysCap 集合是这些类型的**并集**。
凡是落在"并集内、但不在交集内"的能力（例如 `deviceTypes` 声明了 phone/tablet，而某 API 只支持
phone），**必须**用 `canIUse` 逐设备校验，否则在不支持的设备类型上直接崩溃。

能力检测的兜底顺序：

1. `canIUse(SysCap)` —— 判设备类型间差异；
2. 能力查询接口（`isXxxAvailable()` / `isXxxSupported()`）—— 判同类型不同型号差异；
3. **错误码 801**（能力不支持）—— 没有查询接口时，同步接口必须 `try/catch` 兜底，不能让它冒到用户面前。

### 硬件动态变化用监听，不用轮询

相机设备会热插拔、折叠切换后设备集合会变。不要靠定时轮询，用：

```typescript
cameraManager.on('cameraStatus', (_err, info) => {
  // info.camera.cameraId / info.status（相机上线/下线/可用变化）
  // 需要时在这里重选设备并重建 Session
});
```

### 传感器权限映射（拍照/录像旋转依赖的重力）

| 传感器 | 权限名 | 级别 | 运行时请求 |
|---|---|---|---|
| 重力 `GRAVITY` | **无需权限** | — | 否 |
| 加速度 `ACCELEROMETER` | `ohos.permission.ACCELEROMETER` | system_grant | 否 |
| 陀螺仪 `GYROSCOPE` | `ohos.permission.GYROSCOPE` | system_grant | 否 |
| 计步 `PEDOMETER` | `ohos.permission.ACTIVITY_MOTION` | **user_grant** | **是** |
| 心率 `HEART_RATE` | `ohos.permission.READ_HEALTH_DATA` | **user_grant** | **是** |

拍照/录像用的 `GRAVITY` 不需要权限声明；`system_grant` 只需在 `module.json5` 的
`requestPermissions` 声明，`user_grant` 还要运行时 `requestPermissionsFromUser()`。
订阅/取消必须成对调用（`on`/`off`），传感器数据按 `SensorId` 枚举值引用，不要手写数字。

### 相机与录像的权限清单（user_grant，都要运行时申请）

| 权限 | 场景 | 级别 |
|---|---|---|
| `ohos.permission.CAMERA` | 拍照、预览、录像 | user_grant |
| `ohos.permission.MICROPHONE` | **仅录像（视频含音频轨）需要** | user_grant |

**录像最常见的漏项是只申请 CAMERA 不申请 MICROPHONE**：AVRecorder `prepare()` 会直接失败，
错误码 201（Permission denied）。不涉及音频录制时才可省略 MICROPHONE。两个权限都要在
`module.json5` 声明（含 reason 和 usedScene）并运行时成对申请。

### 授权时序与失败处理

- **初次授权后必须重新初始化相机**：XComponent 的 `onSurfaceCreated` 早于授权弹窗，
  权限回来时初始化已完成但 Surface 通道未就绪，表现为"首次授权后预览无图、重启才正常"。
  授权回调里按 `dialogShownResults[0] === true && authResults[0] === 0` 判定"初次授权"
  并重新初始化（`dialogShownResults=false` 表示权限已设置过，无需重初始化）；
- **权限失败会断掉初始化链**：无权限时 `createCameraInput` 抛异常，后续 `photoOutput`
  等对象为空——输出流调用前判空 + `try/catch`，权限失败走降级 UI 而不是继续执行
  （否则点拍照直接 jscrash）。

---

## 错误码速查

> 以下错误码归纳自现有案例与排查经验，**以实际运行日志和 SDK 文档为准**；同一错误码在不同版本可能对应不同消息，排查时先看日志里的 message 再对号。

| 错误码 | 触发场景 | 处理 |
|---|---|---|
| `201` | 权限校验失败：未声明或未运行时授予（典型：录像只申请了 CAMERA、漏了麦克风权限） | 检查 `module.json5` 声明与运行时授权；录像必须 CAMERA + MICROPHONE 成对申请 |
| `801` | 能力不支持（同步接口调用） | `try/catch` 兜底并走降级路径，不能让它冒到用户面前 |
| `401` / `7400101` | `surfaceId` 为空或未生成就创建 PreviewOutput | `surfaceId` 必须在 `XComponent.onLoad` 内取，且用前判空 |
| `7400107` / `7400103` | 初始化顺序错（跳步或换序） | 严格按 [初始化生命周期](#初始化生命周期顺序错就报错) 的顺序执行 |
| `7400201` | 未释放旧会话直接重建；在运行中的 Session 上 `removeInput`/`removeOutput` 增量改；preconfig 的 Type+Ratio 组合不支持 | 先 `releaseCamera()` 再完整重建，前后置切换/折展切换一律重建；preconfig 前先 `canPreconfig` 校验，不支持走常规初始化兜底 |
| `7400102` | API 22+ 无损出图接口调用失败（设备不支持可变安装角等）；前置无闪光灯直接 `setFlashMode`；连续两次 `capture` 未串行 | 退回系统默认出图路径，不能因此让相机无法启动；闪光灯先判支持性；连拍用 `captureReady` 串行 |
| `7400109` | 相机设备被占用/抢占（前一次流未释放即重开同一摄像头，或他应用占用） | 创建前完整释放（`stop → close → release`）；黑屏排查时排在权限之后、时序之前 |
| `7400110` | 帧率不在当前预览流支持列表（如设备仅支持 [1,30] 与 [60,60]） | 设置前用 `getSupportedFrameRates` 查范围，用 `getActiveFrameRate` 判同跳过 |

---

## 初始化生命周期（顺序错就报错）

创建新链必须遵守下面的顺序；已有预览做切镜/折展重建时，先用新形态快照完成目标和能力预检，再进入 release 与创建阶段：

```
getCameraManager → 取得当前形态 supportedCameras 快照
  → 按 requested cameraPosition 选设备（不是硬编码 cameraId）
  → 确认 getSupportedSceneModes 含 NORMAL_PHOTO
  → getSupportedOutputCapability 取 previewProfile（绝不手工构造 Profile）
  → 已有旧链时 releaseCamera
  → createCameraInput + open
  → createPreviewOutput(profile, surfaceId)
  → createSession → beginConfig → addInput → addOutput → commitConfig → start
```

三个必须守的点：

1. **先选中并预检目标，再 release；release 完成前不能创建新链**。这样既避免目标缺失时提前黑屏，也避免新旧会话并存导致 `7400201`。
2. **profile 只能从 `previewProfiles` 里选**，手工拼一个不被支持的 Profile 必然失败。
3. **`surfaceId` 必须在 `XComponent.onLoad` 内取**，且用前确认非空 ——
   空的或尚未生成的 surfaceId 会让 `createPreviewOutput` 抛 `401`/`7400101`，表现为黑屏。

### 前后台与生命周期

- **快速切换要防重入**：`onPageShow`/`onPageHide` 里申请/释放相机资源的异步函数必须
  `await` 串行化，否则快速切换会重复释放，报 7400201；
- **拍照后不要立刻停会话**：等拍照回调触发后再延时 `stop()`，过早停止会收不到回调或取不到数据；
- **退后台/熄屏录制被系统强制停止**（隐私保护机制，不可绕过）：监听
  `applicationStateChange`，`onApplicationBackground` 主动停录释放、
  `onApplicationForeground` 重启恢复；不要尝试"维持后台录制"。

### 对焦与拍摄时序

- **扫码后立即拍照模糊 = `capture` 早于对焦完成**：连续自动对焦（CAF）下先设
  `FOCUS_MODE_AUTO` + `setFocusPoint`（码中心），监听 `focusStateChange` 的
  SCAN → FOCUSED 转换完成后再 `capture`；
- **连续拍照要串行**：第二次 `capture` 无法保证第一次已执行完毕，两次同时执行报
  7400102 / `Capture failed error:13`——注册 `on('captureReady')` 监听上次完成再拍，
  连拍结束取消监听。

## 前后置判断

用 `CameraDevice.cameraPosition`（`CameraPosition` 枚举），**不是 `cameraType`** ——
后者表示镜头类型（广角/超广角/长焦/深感），**根本没有 FRONT/BACK 枚举值**，
写成 `cameraType === CAMERA_TYPE_FRONT` 的条件永远不成立。

**后置摄像头可能不存在**：阔折叠外屏可能没有。不能对
`undefined` 调 `createCameraInput`，也不能把“防越界”写成无条件回退 `cameras[0]`：

| 场景 | 目标位置不存在时的处理 |
|---|---|
| 已有预览，用户点击切换前/后置 | 保持当前相机和位置状态不变，提示目标不可用 |
| 折展形态切换 | 保持原 `cameraPosition` 意图，使用形态回调的可用集合重选对应物理 ID；暂未出现目标时遮住预览、禁用拍摄，并串行释放可能已失效的旧链，进入受控重试/错误态 |
| 首次启动且默认位置不存在 | 只有产品策略明确允许“任意可用相机”时才选择其他位置，并同步 `cameraPosition`、镜像和控件状态；否则走不可用降级 |

任何跨 FRONT/BACK 的 fallback 都是产品行为，不是通用安全兜底。

**切换前后置后必须用新摄像头重选 Profile**：前后置的支持列表不同（如后置的 640×360
拍照 Profile 不在前置列表），沿用旧摄像头的 Profile 会 `CanAddOutput check failed`、
预览卡住——切镜后重新走 `getSupportedOutputCapability` 选 Profile 再创建输出流。

## 能力边界

下表区分本 Skill 可直接处理的能力和不属于通用处理范围的能力。超出范围时先核对 SDK 类型定义、业务源码和设备条件，不直接套用单路 Session、基础旋转或普通录像处理链。

| 能力 | 状态 | 说明 |
|---|---|---|
| 切镜双实例翻转 / 过渡态遮罩 / 自动切镜 | 本 Skill 覆盖 | 见[折叠形态与相机连续性](camera-fold.md) |
| 拍照 PhotoOutput 回调链 / 双输出统一配置 | 本 Skill 覆盖 | 见[相机旋转、拍照与录像输出](camera-output.md) |
| 录像 AVRecorder 状态机（旋转方向） | 本 Skill 覆盖 | 同上，覆盖 prepare→updateRotation→start |
| 视频通话多端旋转矩阵同步送远端 | 不在通用范围 | 涉及 RTC、编码链路与对端协商 |
| 多摄并发 / 双路独立控制 | 不在通用范围 | 需查询并发能力、资源限制与 Session 组合 |
| 高阶 Scene Mode（人像 / 夜景 / 专业 / 全景） | 不在通用范围 | 需按目标 SceneMode 查询设备支持和参数范围 |
| CameraKit 录像高级编码参数（码率/关键帧/HDR 元数据） | 不在通用范围 | 需联合录像与编码接口确认参数和容器约束 |
| C/C++ 原生相机接口（NDK 层） | 不在通用范围 | 需按 NDK API、线程模型、Surface 和资源生命周期处理 |
