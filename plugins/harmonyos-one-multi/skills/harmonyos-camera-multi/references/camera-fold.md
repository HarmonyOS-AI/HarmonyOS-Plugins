# 折叠形态与相机连续性

## 折叠切镜

### 什么时候要重建，什么时候不要

| 形态变化 | 处理 |
|---|---|
| 折叠 ↔ 展开（相机集合变了） | **完全重建**：release → 重新走完整生命周期 |
| 悬停 ↔ 展开 | **跳过重建** —— 这组转换返回的相机列表一致，重建只会闪烁甚至失败 |
| 悬停 ↔ 折叠 | 不做通用豁免；若使用 `display.on`，继续等待终态或依据实测列表决定，不能假定列表一致 |
| 前后置切换 | **完全重建**，不能在运行中的 session 上增量换 input/output（`session.removeInput` 会抛 `7400201`） |

重建时沿用工程现有 XComponent 和 Session 封装。先完成目标设备、Profile 和新 Surface 的预检，再释放旧链；单摄资源通常不能让新旧 Session 同时占用设备，需要视觉连续时用旧帧/切换遮罩覆盖这段串行重建窗口，除非运行时能力明确支持并发。不要引入只在示例工程成立的全局切换标记。

### 相机连续性不变量

折展适配保持的是“用户选择的相机位置”，不是某个固定 `cameraId`：

```text
requested cameraPosition: FRONT（跨形态保持）
折叠态实际设备: cameraId=C, cameraPosition=FRONT
展开态实际设备: cameraId=B, cameraPosition=FRONT
```

`requestedCameraPosition` 必须独立于 `currentCameraDevice`，并保存在能跨 XComponent/页面重建恢复的业务状态中。迁移已有页面时，在注册折叠监听前从现有 `isFront`/ViewModel 恢复它，不能用示例冷启动默认值覆盖正在使用的前置。另存 `lastCommittedCameraId` 作为选择提示，不随 Input/Session 释放清空。若同位置有多个候选，优先保持仍在新快照中的最后成功 ID；该 ID 已失效时使用已明确的镜头角色/类型选择器。只有一个同位置候选时才可直接选中，不能把数组顺序当作设备角色。

手工重建必须遵守以下顺序：

1. 从 `FoldStatusInfo.supportedCameras` 取得当前形态的设备快照；只有使用 `display.on` 时才调用 `getSupportedCameras()`。
2. 在释放旧链之前，按“请求的 `cameraPosition` + connectionType”查找目标设备。
3. 未命中时保留当前业务位置，进入 `UNAVAILABLE`：遮住预览、禁用拍摄并把旧链 release 排入同一串行队列；不得启动其他位置或默认选择 `cameras[0]`，再按已明确策略执行重试或降级。
4. 命中后再串行执行 release，并用新设备重新查询 Profile、创建 Input/Output/Session。
5. 每次形态事件（包括目标暂缺）都推进 generation，使旧异步任务失效；重建全程单通道执行，并在每个 `await` 后检查 generation。
6. `session.start()` 成功且 generation 仍为最新后，才提交当前 `cameraId`；日志同时记录 requestedPosition、旧/新 cameraId 和实际 position。

```typescript
function selectCameraForIntent(cameras: Array<camera.CameraDevice>,
  requestedPosition: camera.CameraPosition, connectionType: camera.ConnectionType,
  currentCameraId?: string, preferredType?: camera.CameraType): camera.CameraDevice | undefined {
  const candidates = cameras.filter((device: camera.CameraDevice) =>
    device.cameraPosition === requestedPosition && device.connectionType === connectionType);
  const current = candidates.find((device: camera.CameraDevice) => device.cameraId === currentCameraId);
  if (current) return current;
  if (candidates.length === 1) return candidates[0];
  if (preferredType !== undefined) {
    const typed = candidates.filter((device: camera.CameraDevice) => device.cameraType === preferredType);
    if (typed.length === 1) return typed[0];
  }
  return undefined; // 多候选仍有歧义：交给产品策略明确，不依赖数组顺序。
}
```

画面从“自拍视角”变成“后摄视角”不能直接归因于系统切镜。先核对形态前后的实际
`cameraId`/`cameraPosition`：可能是应用命中了 `cameras[0]`、页面重建后位置状态恢复默认值，
也可能只是同一物理镜头相对新激活屏幕的朝向发生变化。

### 热启动必须恢复相机

只初始化 `aboutToAppear` 不够——页面从后台回前台（热启动）时相机可能已不可用，表现就是"返回后黑屏"。标准三件套（候选知识）：

```typescript
onPageShow(): void {
  if (this.photoSession) {
    this.requestCameraReload(); // 热启动也进入同一个串行队列，不能直调 initCamera
  }
}
aboutToAppear(): void {
  this.requestCameraPermission();
  this.setupFoldStatusListener();
  this.setupRotationListener();
  this.getCurrentFoldStatus();
}
aboutToDisappear(): void {
  this.cameraActive = false; // 先使旧 generation 失效
  display.off('foldStatusChange', this.foldStatusCallback);
  display.off('change', this.displayChangeCallback);
  this.cameraReloadQueue.requestTeardown();
}
```

### 两类已踩过的反例

1. **注册了监听但回调只更新状态、不重建**：`foldStatusChange` 回调里只改 `@State foldStatus`，设备集合变了却没重选设备——布局刷新了、相机没跟着变。
2. **折叠后只增量更新 PreviewOutput**：在运行中的 Session 上 `removeOutput` 旧 preview 再 `addOutput` 新 profile，不释放旧 CameraInput、不重选设备。折叠前选中的相机在新形态下可能已不在 `getSupportedCameras()` 列表里，增量更新必然失败。折叠状态变化一律走 `releaseCamera() → initCamera()` 完整重建。

### 屏幕比例变了要重选 profile

折叠设备开合会改变屏幕高宽比。折叠/展开终态需要按新的预览区域，从设备支持列表重新选择 profile；半折叠过渡态不要重复重建。`getConfigRatio()` 若只是业务封装，不要把它误当作 Camera Kit API。

### 折展防拉伸链路

上一节只覆盖了流这一端。折展后不拉伸的完整不变量是**帧比例与 Surface 矩形比例同源**：两端锁同一个基准比例，任何一端单独变都会拉伸或裁切。

```text
基准比例（业务确定，普通形态 4:3；阔折叠外屏 1:1）
  ├─ Profile 端：previewProfiles 里取宽高比 ≈ 基准的最大档
  └─ Surface 端：setXComponentSurfaceRect 把显示矩形按当前方向的显示比例 letterbox 拟合进窗口
```

1. **先定基准比例**：普通形态常用 4:3；阔折叠外屏是方屏（`WIDTH_SM + HEIGHT_MD` 断点组合），基准取 1:1 且 Surface 直接铺满全屏、不做 letterbox。
2. **Profile 按比例筛**：从 `previewProfiles` 筛宽高比等于基准的最大档（比值差 ≤ 0.1，见[预览区尺寸](camera-preview-ui.md#预览区尺寸)），不要按组件具体宽高精确筛。筛不到匹配基准的档位时，回退到 `previewProfiles` **列表首档**（设备默认推荐档）并按该档实际比例 letterbox；**不要盲目回退最高分辨率**——不少设备的最高档是 16:9 裁切模式，视野明显收窄，用户观感是"焦距变大"。
3. **Surface 矩形 letterbox 拟合**：XComponent 组件可以铺满窗口，但显式 `setXComponentSurfaceRect`（单位 px）把实际显示矩形收敛成当前方向下的显示比例——`display.rotation` 为 0°/180° 时 Surface 比例是基准比例的**倒数**，90°/270° 时与基准一致（即场景 4 的比例规则）。以窗口为容器取短板一支：竖屏下 `windowHeight × 3/4 > windowWidth` 时 `surfaceHeight = windowWidth / 3 × 4`，否则 `surfaceWidth = windowHeight / 4 × 3`；横屏两支对调。余量留给组件黑色背景（letterbox），不要把矩形硬拉成窗口比例；折展改变窗口高宽比后必须重算。
4. **双监听各管一摊，落回同一份窗口状态**：`windowSizeChange` 只重算 Surface 矩形——**基准比例发生变化时除外，必须走第 7 条的重建兜底**；`foldStatusChange` 完整重建并重选 Profile，重建内部在 `commitConfig()` 前再设一次 Surface 矩形，保证新流和新矩形基于同一份窗口尺寸。
5. **时序耦合的防御**：重建若读取 `windowSizeChange` 维护的缓存断点（如 `widthBp`），就隐含依赖"窗口事件先于形态事件到达"这一未被承诺的顺序。防御写法是重建时**实时计算**基准（现取 `getWindowWidthBreakpoint()` / `getWindowHeightBreakpoint()`，或直接用当前 `windowRect` 宽高推导），不要读缓存断点。
6. **实时计算也读得到旧窗口：终态重建要有"窗口稳定"门槛**（camera-13）。相机层 `foldStatusChange`（携带 `supportedCameras` 的那个）在系统切换显示**之前**到达，回调时刻 `windowRect`、断点和 `display.rotation` 都是旧形态的值——实时接口此刻返回的同样是旧值。**固定时长防抖（100–200ms）不构成窗口稳定判据**：折叠屏窗口迁移叠加方向策略生效可达数百毫秒，防抖结束后重读仍是旧值时，"重读→与建流时尺寸比对"会以"一致"放行，门槛形同虚设。可靠门槛二选一（可叠加）：
   - 把**流的创建**推迟到该形态的 `windowSizeChange` 到达之后（形态事件先消费 `supportedCameras` 快照完成设备选择与遮罩，窗口尺寸事件到达后再按新窗口重算基准、生成 Profile 并建流）；
   - 在 `windowSizeChange` 回调里做基准比对兜底（第 7 条），即使门槛失手也能在窗口事件到达时纠正。
7. **基准比例变化必须重建流，"只重算矩形"有边界**（camera-13/14）。第 4 条的前提是基准比例不变；折展使基准在 4:3↔1:1 之间切换时，运行中的流还是旧基准的 Profile，重算矩形救不回来。可执行判定：建流成功后**记录建流时刻的形态基准**（形态基准的取值，走了 fallback 时连同实际档位比例一起记）；`windowSizeChange` 回调实时重算基准，与记录值**不同 → 走完整 `release → init` 重建队列**（generation 照常推进、防抖合并），**相同 → 才允许只重算矩形**。没有这层兜底，第 6 条的门槛一旦失手，旧基准的流会一直留在新形态里：后置表现为裁切基准流的窄视野（观感"焦距变大"），无匹配档的前置表现为 fallback 档的窄条 letterbox（宽度不铺满）。

验证时在同一时刻记录三项：Profile `size`、Surface 矩形、窗口尺寸。前两者的显示宽高比必须一致；与窗口比例可以不等，差值就是 letterbox 黑边。可落地的 fit 计算与实时基准计算见 `assets/CameraFoldable.ets` 的 `computeSurfaceRect` / `refreshPreviewAspectRatio`。

### 折展后的窗口方向策略

折展后"画面不旋转、保持横屏"不是相机流的问题，而是**窗口方向策略**的问题，但它会级联成相机症状：窗口方向冻结 → `display.rotation` 不变 → `getPreviewRotation`/`setPreviewRotation` 与 letterbox 拟合全部按错误方向计算，最终呈现"不旋转 + 拉伸 + 两侧黑边"的复合症状。排查折展拉伸时先确认窗口方向已按新形态正确切换，再查流与矩形。

1. **枚举选型**（相机侧使用以下最小规则）：

   | 形态（以窗口最小边 vp 判定，实时 `px2vp` 计算） | 枚举 |
   |---|---|
   | 最小边 < 600vp（手机/折叠外屏 sm） | `PORTRAIT` |
   | 最小边 ≥ 600vp（md/lg，折叠展开、平板） | `AUTO_ROTATION_RESTRICTED`（跟随传感器四向，受旋转锁控制） |
   | 半折叠（MD 断点且横屏） | `LANDSCAPE`（进入时锁定） |

   **`UNSPECIFIED` 不是"跟随系统旋转"，也不是任何策略的通用恢复值**：它表示"未定义、由系统判定"，折展后系统常维持当前方向，用户把设备竖过来也不会旋转。退出半折叠/到达展开终态时若 `widthBp !== WIDTH_SM`，要主动恢复 `AUTO_ROTATION_RESTRICTED`。

2. **重估时机由 `windowSizeChange` 驱动**：方向策略在窗口尺寸稳定后重估才有意义；`foldStatusChange` 回调时刻 `windowRect` 还是旧形态的值，此时按尺寸选枚举会选错（与第 6 条同一时序陷阱）。

3. **去重缓存的边界**：用 `lastOrientation` 之类的本地缓存跳过重复设置时，缓存命中的前提是"已设置且仍生效"。折展过程中系统可能重置窗口方向状态，异步 `setPreferredOrientation` 也可能失败——**只有设置成功（promise resolve）才更新缓存，失败立即失效**；或在折展终态无条件重设。先记缓存再异步设置、失败不回滚的写法，会让方向永久冻结在折展前的方向。

4. **方向变化后的相机端联动**：方向策略生效导致窗口旋转时，`display.rotation` 变化要走 `display.on('change')` → `setPreviewRotation` + 重算 Surface 矩形（见[旋转的概念基线](camera-output.md#旋转的概念基线)），`windowSizeChange` 负责重估方向策略与矩形；两条监听都要落回同一份实时窗口状态。

可落地的参考模式——方向策略在 Ability 侧随 `windowSizeChange`（窗口已稳定）重估并按设置结果维护去重，半折叠锁横屏与退出恢复在页面 `foldStatusChange` 内处理：

```typescript
// Ability 侧：窗口尺寸稳定后重估方向；只有设置成功才认缓存
private lastApplied?: window.Orientation;

updateOrientation(): void {
  let rect: window.Rect = this.mainWindow.getWindowProperties().windowRect;
  let uiContext: UIContext = this.mainWindow.getUIContext();
  let minEdgeVp: number = Math.min(uiContext.px2vp(rect.width), uiContext.px2vp(rect.height));
  let orientation: window.Orientation =
    minEdgeVp >= 600 ? window.Orientation.AUTO_ROTATION_RESTRICTED : window.Orientation.PORTRAIT;
  if (orientation === this.lastApplied) {
    return;
  }
  this.mainWindow.setPreferredOrientation(orientation).then(() => {
    this.lastApplied = orientation; // 设置成功才更新；失败不记，下次重设
  }).catch((error: BusinessError) => {
    this.lastApplied = undefined;
  });
}

// 页面 foldStatusChange：半折叠锁横屏；退出半折叠恢复自动旋转并重算矩形
if (foldStatus === display.FoldStatus.FOLD_STATUS_HALF_FOLDED
  && this.curWidthBp === WidthBreakpoint.WIDTH_MD && isLandscape(display)) {
  this.mainWindow.setPreferredOrientation(window.Orientation.LANDSCAPE);
  // 半折叠 Surface 矩形按折痕上半屏计算
} else {
  if (this.curWidthBp !== WidthBreakpoint.WIDTH_SM) {
    this.mainWindow.setPreferredOrientation(window.Orientation.AUTO_ROTATION_RESTRICTED); // 终态无条件恢复
  }
  if (this.halfFoldedActive) { /* 退出半折叠：按新形态重算 Surface 矩形/基准重建 */ }
}
```

悬停态（半折叠）在相机侧只涉及以上方向策略、重建豁免和上半屏 Surface 矩形。悬停态 UI 上下分区、布局容器和折痕避让不属于本文范围；调用方采用 `FolderStack` 时，相机预览通常 `.enableAnimation(false)`，避免尺寸过渡连续触发 Surface 矩形重算。

### 切镜重建实现机制

上面的概念讲了"什么时候要重建"。这里补**怎么重建才不留残影、不抖**（候选知识，接入业务后按目标形态重验）。

**双实例翻转防残影**：Session 不能在运行中增量换设备（`removeInput` 抛 `7400201`），不能靠"换 input"切镜。可靠路径是**翻转一个 `reloadXComponentFlag`，触发新 XComponent 实例挂载**——`if/else` 各用独立 Controller，`onLoad` 只把新 Surface 交给唯一重建队列；队列消费已预生成的 latest plan 后完成 release/init。不要在 `onLoad` 直调 `initCamera()`。

```typescript
@State reloadXComponentFlag: boolean = false;
private controllerA: XComponentController = new XComponentController();
private controllerB: XComponentController = new XComponentController();

build() {
  Stack() {
    if (this.reloadXComponentFlag) {
      XComponent({ type: XComponentType.SURFACE, controller: this.controllerA })
        .onLoad(() => this.cameraReloadQueue.onSurfaceReady(
          this.controllerA.getXComponentSurfaceId()))
    } else {
      XComponent({ type: XComponentType.SURFACE, controller: this.controllerB })
        .onLoad(() => this.cameraReloadQueue.onSurfaceReady(
          this.controllerB.getXComponentSurfaceId()))
    }
    // 叠加控件层放在 if/else 之外（见下）
  }
}
```

完整的 `BOOTSTRAP/READY/UNAVAILABLE` 计划状态、`IDLE/DEBOUNCING/AWAITING_ONLOAD/IN_PROGRESS` 阶段和 Surface version 处理见 `assets/CameraFoldable.ets`，不要把上面的结构片段当成可绕过队列的初始化入口。

**过渡态遮罩与控件层解耦**：叠加控件（快门、模式条、变焦滑块）**必须放在双实例 `if/else` 之外的同级 `Stack` 层**，使其独立于实例切换——否则翻转窗口期内控件会悬空或停留在上一相机布局。过渡态用 `switching` 标记盖一层半透明遮罩遮挡用户操作；新 Session `start()` 成功的回调里撤掉遮罩并刷新布局状态。

```typescript
onReloadRequested(): void { this.switching = true; this.captureEnabled = false; }
onLatestSessionStarted(): void { this.switching = false; this.captureEnabled = true; }

// 在 Stack 内、双实例 if/else 之后（同级，不在分支内）：
Column() { /* 模式条 + Blank + 快门 */ }
  .width('100%').height('100%')
  .padding({ top: this.safeInsetTop, bottom: this.safeInsetBottom })

if (this.switching) {
  Column() { LoadingProgress().width(48).height(48) }
    .width('100%').height('100%').justifyContent(FlexAlign.Center)
    .backgroundColor(Color.Black) // 终态到达后不能再露出旧链的错误帧
}
```

**两种 foldStatusChange 监听方案**：

| 方案 | 注册 | 回调签名 | supportedCameras | 何时用 |
|---|---|---|---|---|
| `cameraManager.on('foldStatusChange', cb)` | 相机层 | `(err, foldStatusInfo: camera.FoldStatusInfo)` | **回调直接带 `foldStatusInfo.supportedCameras`**，必须把该快照传入重建，不能只打印后再次查询 | **推荐**——只报告相机层终态，适合相机切镜 |
| `display.on('foldStatusChange', cb)` | display 层 | `(status: display.FoldStatus)` | 不带，需自行 `getSupportedCameras()` | 仅当 display 已被业务监听时 |

两种方案选一种并成对解绑，不要混用。相机层 `camera.FoldStatus` 只包含
`NON_FOLDABLE`、`EXPANDED`、`FOLDED`，回调已提供终态设备集合，不需要处理
`HALF_FOLDED`。`display.on` 方案的精确豁免判定仅限
`HALF_FOLDED ↔ EXPANDED`；**不要扩展到 `HALF_FOLDED ↔ FOLDED` 也跳过**。

**重建串行化与防抖**：

- **重建必须串行化**：用工程唯一的串行门禁（如 `cameraReloadQueue.request(cameras)`），快速开合时禁止多次并发 release/init。
- **generation 丢弃**：每次形态事件都推进 generation，目标位置暂缺也不能例外；旧任务在每个异步边界后检查，失效后只做必要清理，不得提交 `curCameraDevice`、撤销遮罩或覆盖当前 Session。
- **高频事件 debounce 100–200ms**：折叠/旋转过程连续触发，`setTimeout` 防抖后再触发 ArkUI 重渲染，避免抖动期反复重排。
- **先隔离再防抖**：终态回调到达就用不透明遮罩隐藏旧预览并禁用 capture/record；100–200ms 只合并“打开最新目标”的工作，不能让旧链继续对用户可见或可拍。
- **区分阶段**：至少区分 `IDLE / DEBOUNCING / AWAITING_ONLOAD / IN_PROGRESS`；flag 已翻转、等待 `onLoad` 时新请求只替换 latest plan，不能再安排一次翻转。
- **区分无计划原因**：首次启动才允许无计划时主动查询；最新回调明确无目标时进入 `UNAVAILABLE`，迟到 `onLoad` 不得重新查询覆盖，并在串行队列中 release 旧链、禁用 capture。
- **Surface 也要版本化**：双实例使用独立 Controller；重复 `onLoad` 到达时保存最新 Surface、推进 generation，并在当前工作结束后补建，不能只覆盖成员 `surfaceId`。
- **注销必须传回调引用**：`cameraManager.off('foldStatusChange', cb)` / `display.off('change', cb)`；不带 callback 的 `display.off('change')` 会误删该事件下所有监听（含其他组件的）。

**断点旋转策略**：sm 断点（手机竖屏）不旋转，布局只按竖屏一套设计；md/lg 断点（窗口最小维度 ≥ 600vp）支持旋转，叠加控件必须同时考虑横竖屏两套排列。折叠检测用 `display.isFoldable()`，不要用 `deviceInfo.deviceType`（折叠设备返回 `'phone'`）。

### 系统自动切镜

折叠屏上系统可自动切到当前可用前置镜头（输入设备切换、会话配置、参数接续全自动）。该能力只在多个前置镜头之间切换，**不会自动执行 FRONT ↔ BACK**。出现前置变后置时优先排查应用的默认状态和 `cameras[0]` fallback。它适合**简单前置相机 UX**（如人脸识别）；需要明确镜头选择、复杂拍照/录像的场景必须走业务控制的设备变更流程。**与上面的手工重建二选一，不可同时开启**。

能力门禁三件套：

| API | 用途 |
|---|---|
| `session.isAutoDeviceSwitchSupported()` | **能力门禁**，返回 false 直接放弃，不开启 |
| `session.enableAutoDeviceSwitch(true)` | 开启（先注册回调再开启） |
| `session.on('autoDeviceSwitchStatusChange', cb)` | 监听切换结果，回调签名 `(error, status: camera.AutoDeviceSwitchStatus)` |

```typescript
private enableFoldAutoSwitch(session: camera.PhotoSession): void {
  if (!session.isAutoDeviceSwitchSupported()) return;        // 能力门禁
  session.on('autoDeviceSwitchStatusChange', this.autoSwitchCallback);
  session.enableAutoDeviceSwitch(true);
}

private autoSwitchCallback = (error: BusinessError, status: camera.AutoDeviceSwitchStatus): void => {
  if (error !== undefined && error.code !== 0) return;
  if (status.isDeviceCapabilityChanged) {
    // 切换已完成：重新查询 zoom 等能力并刷新已有 UX（不加新 UI）
  }
};
```

**切换窗口期硬约束**：切换发起到 `autoDeviceSwitchStatusChange` 报告完成期间，**禁止调用任何 session API**——`beginConfig`/`addOutput`/`removeInput`/`capture` 等一律禁调。`isDeviceCapabilityChanged === true` 时只重新查询依赖能力（如 zoom 范围）并更新现有控件值，**不新增 UI**。

**Surface 旋转锁定**：`xComponentController.setXComponentSurfaceRotation({ lock: true })` 在 Surface 几何配置阶段调用，把 Surface 旋转锁定，由应用层自己控旋转角；动态随屏旋转的场景交给 `getPreviewRotation` / `setPreviewRotation`，不要在本处重复实现方向算法。

```typescript
private configureSurface(widthPx: number, heightPx: number): string | undefined {
  const surfaceId = this.xComponentController.getXComponentSurfaceId();
  if (surfaceId.length === 0 || widthPx <= 0 || heightPx <= 0) return undefined;
  this.xComponentController.setXComponentSurfaceRect({ surfaceWidth: widthPx, surfaceHeight: heightPx });
  this.xComponentController.setXComponentSurfaceRotation({ lock: true });
  return surfaceId;
}
```
