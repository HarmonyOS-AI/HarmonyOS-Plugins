/**
 * 折叠屏相机适配示例（候选知识）
 *
 * 演示 camera-fold.md 中「切镜重建实现机制」「折叠切镜」及
 * camera-capabilities.md 中「初始化生命周期」的可落地写法：
 * - 两个独立 Controller 的 XComponent 翻转重建；显式阶段状态机合并快速开合请求
 * - cameraManager.on('foldStatusChange') 回调的 supportedCameras 直接驱动设备选择
 * - cameraManager 回调只报告相机层终态；display 方案仅豁免 HALF_FOLDED ↔ EXPANDED
 * - requestedCameraPosition 保存用户意图；物理 cameraId 可变，但不得静默回退 cameras[0]
 * - 折展防拉伸：Profile 与 Surface 矩形锁同一基准比例（普通 4:3、阔折叠外屏 1:1）；
 *   窗口变化重算 Surface 矩形，形态终态重建时实时计算基准再筛 Profile
 * - release 顺序完整：stop → CameraInput close → PreviewOutput release → session release
 *
 * 接入业务前必须按目标形态重验：本示例按窗口 letterbox 动态计算 surface 矩形、
 * 按基准比例筛 Profile、仅接 PreviewOutput（未接 PhotoOutput/VideoOutput）。完整拍照/录像输出流见
 * camera-output.md「拍照与录像输出流」。
 */
import { camera } from '@kit.CameraKit';
import { BusinessError } from '@kit.BasicServicesKit';
import { abilityAccessCtrl } from '@kit.AbilityKit';
import { display, window } from '@kit.ArkUI';

const TAG = 'FoldScreenCameraAdaptationDemo ';

interface CameraReloadPlan {
  generation: number;
  requestedPosition: camera.CameraPosition;
  supportedCameras: Array<camera.CameraDevice>;
  targetCamera: camera.CameraDevice;
  previewProfile: camera.Profile;
}

enum CameraPlanState {
  BOOTSTRAP,
  READY,
  UNAVAILABLE,
  STABLE
}

enum CameraReloadPhase {
  IDLE,
  DEBOUNCING,
  AWAITING_ONLOAD,
  IN_PROGRESS
}

@Entry
@Component
struct Index {
  @State isShow: boolean = false;
  @State reloadXComponentFlag: boolean = false;
  @State switching: boolean = false;
  @State cameraUnavailable: boolean = false;
  @State captureEnabled: boolean = false;
  @StorageLink('foldStatus') foldStatus: number = 0;
  // 示例把现有业务唯一状态源命名为 isFront；接入时替换为项目实际 ViewModel/状态仓。
  @StorageLink('isFront') isFront: boolean = false;
  // 保存的是用户选择的位置语义，不是某个会随形态变化的物理 cameraId。
  @StorageLink('requestedCameraPosition') mCameraPosition: camera.CameraPosition =
    camera.CameraPosition.CAMERA_POSITION_BACK;
  private mXComponentControllerA: XComponentController = new XComponentController();
  private mXComponentControllerB: XComponentController = new XComponentController();
  private mXComponentOptionsA: XComponentOptions = {
    type: XComponentType.SURFACE,
    controller: this.mXComponentControllerA
  }
  private mXComponentOptionsB: XComponentOptions = {
    type: XComponentType.SURFACE,
    controller: this.mXComponentControllerB
  }
  private mSurfaceId: string = '';
  private mCameraManager: camera.CameraManager | undefined = undefined;
  // surface 矩形随窗口动态重算（computeSurfaceRect），初始值仅覆盖 onLoad 先于窗口查询完成的窗口。
  private surfaceRect: SurfaceRect = {
    surfaceWidth: 1080,
    surfaceHeight: 1920
  };
  private curCameraDevice: camera.CameraDevice | undefined = undefined;
  private mCameraInput: camera.CameraInput | undefined = undefined;
  private mPreviewOutput: camera.PreviewOutput | undefined = undefined;
  private mPhotoSession: camera.PhotoSession | undefined = undefined;
  // 折展防拉伸的基准比例：普通形态 4:3，阔折叠外屏 1:1。重建时实时刷新，不读缓存断点。
  private previewAspectRatio: number = 4 / 3;
  private mContext: Context | undefined = undefined;
  private pendingCameraPlan: CameraReloadPlan | undefined = undefined;
  private pendingPlanState: CameraPlanState = CameraPlanState.BOOTSTRAP;
  private reloadPhase: CameraReloadPhase = CameraReloadPhase.IDLE;
  private pendingSurfaceId: string = '';
  private reloadGeneration: number = 0;
  private reloadTimer: number = -1;
  private isComponentActive: boolean = false;
  private lastCommittedCameraId: string | undefined = undefined;
  // 本示例在多个同位置候选中选唯一 DEFAULT；实际项目应替换为已确认的镜头角色策略。
  private preferredCameraType: camera.CameraType = camera.CameraType.CAMERA_TYPE_DEFAULT;

  private preFoldStatus: display.FoldStatus = this.getFoldStatus();
  // 监听折叠屏状态，可以使用cameraManager.on(type: 'foldStatusChange', callback: AsyncCallback<FoldStatusInfo>): void;
  // 也可以使用display.on(type: 'foldStatusChange', callback: Callback<FoldStatus>): void;
  private foldStatusCallback =
    (err: BusinessError, info: camera.FoldStatusInfo): void => this.registerFoldStatusChanged(err, info);
  private displayFoldStatusCallback =
    (foldStatus: display.FoldStatus): void => this.onDisplayFoldStatusChange(foldStatus);

  getFoldStatus(): display.FoldStatus {
    let curFoldStatus: display.FoldStatus = display.FoldStatus.FOLD_STATUS_UNKNOWN;
    try {
      curFoldStatus = display.getFoldStatus();
    } catch (error) {
      let err = error as BusinessError;
      console.info(`${TAG} getFoldStatus call failed, error: ${err.code}`);
    }
    return curFoldStatus;
  }

  registerFoldStatusChanged(err: BusinessError, foldStatusInfo: camera.FoldStatusInfo) {
    if (err !== undefined && err.code !== 0) {
      console.info(`${TAG} registerFoldStatusChanged call failed, error: ${err.code}`);
      return;
    }
    console.info(TAG + 'foldStatusChanged foldStatus: ' + foldStatusInfo.foldStatus);
    for (let i = 0; i < foldStatusInfo.supportedCameras.length; i++) {
      console.info(TAG +
        `foldStatusChanged camera[${i}]: ${foldStatusInfo.supportedCameras[i].cameraId},cameraPosition: ${foldStatusInfo.supportedCameras[i].cameraPosition}`);
    }
    // 形态状态与相机是否可重建是两件事；即使目标相机暂不可用，布局仍要进入新形态。
    AppStorage.setOrCreate<number>('foldStatus', foldStatusInfo.foldStatus);
    // 相机层回调已经给出当前终态的可用集合。直接使用该快照，避免再次查询产生时序窗口。
    if (!this.requestCameraReload(foldStatusInfo.supportedCameras)) {
      console.error(TAG + `Keep requested cameraPosition=${this.mCameraPosition}; no cross-position fallback.`);
      return;
    }
  }

  onDisplayFoldStatusChange(foldStatus: display.FoldStatus): void {
    console.info(TAG + `onDisplayFoldStatusChange foldStatus: ${foldStatus}`);
    if ((this.preFoldStatus === display.FoldStatus.FOLD_STATUS_HALF_FOLDED &&
      foldStatus === display.FoldStatus.FOLD_STATUS_EXPANDED) ||
      (this.preFoldStatus === display.FoldStatus.FOLD_STATUS_EXPANDED &&
        foldStatus === display.FoldStatus.FOLD_STATUS_HALF_FOLDED)) {
      this.preFoldStatus = foldStatus;
      return;
    }
    this.preFoldStatus = foldStatus;
    if (!this.mCameraManager) {
      return;
    }
    // foldStatus 变量用来控制显示XComponent组件。
    AppStorage.setOrCreate<number>('foldStatus', foldStatus);
    // display 回调不带 supportedCameras，由统一入口主动查询并处理异常。
    if (!this.requestCameraReload()) {
      console.error(TAG + `Keep requested cameraPosition=${this.mCameraPosition}; no cross-position fallback.`);
      return;
    }
  }

  requestPermissionsFn(): void {
    if (!this.mContext) {
      console.error(TAG + 'Context is unavailable.');
      return;
    }
    let atManager = abilityAccessCtrl.createAtManager();
    atManager.requestPermissionsFromUser(this.mContext, [
      'ohos.permission.CAMERA'
    ]).then((): void => {
      if (this.isComponentActive) {
        this.isShow = true;
      }
    }).catch((error: BusinessError): void => {
      console.error(`${TAG} requestPermissionsFromUser call failed, error: ${error.code}`);
    });
  }

  initContext(): void {
    let uiContext = this.getUIContext();
    this.mContext = uiContext.getHostContext();
  }

  initCameraManager(): void {
    if (!this.mContext) {
      console.error(TAG + 'Context is unavailable.');
      return;
    }
    try {
      this.mCameraManager = camera.getCameraManager(this.mContext);
    } catch (error) {
      let err = error as BusinessError;
      console.error(`${TAG} getCameraManager call failed, error: ${err.code}`);
    }
  }

  seedRequestedCameraPositionFromBusiness(): void {
    // 接入已有工程时，必须在注册 fold 监听前从现有 isFront/ViewModel/状态仓中恢复用户选择。
    // 这里的 BACK 只是全新冷启动的示例默认值，不能覆盖已经运行中的 FRONT 选择。
    this.mCameraPosition = this.isFront ? camera.CameraPosition.CAMERA_POSITION_FRONT :
      camera.CameraPosition.CAMERA_POSITION_BACK;
  }

  aboutToAppear(): void {
    console.info(TAG + 'aboutToAppear is called');
    this.isComponentActive = true;
    this.initContext();
    this.initCameraManager();
    this.seedRequestedCameraPositionFromBusiness();
    this.requestPermissionsFn();
    this.onFoldStatusChange();
  }

  async aboutToDisappear(): Promise<void> {
    // 先让所有尚未提交的异步重建失效，再释放页面资源。
    this.isComponentActive = false;
    this.offFoldStatusChange();
    this.reloadGeneration++;
    this.pendingCameraPlan = undefined;
    this.pendingPlanState = CameraPlanState.UNAVAILABLE;
    this.pendingSurfaceId = '';
    this.clearReloadTimer();
    this.captureEnabled = false;
    await this.releaseCamera();
  }

  async onPageShow(): Promise<void> {
    if (this.mSurfaceId.length > 0) {
      this.requestCameraReload();
    }
  }

  async releaseCamera(): Promise<void> {
    // 先同步摘下共享引用，避免退出、失败清理和重建对同一资源重复释放。
    let photoSession: camera.PhotoSession | undefined = this.mPhotoSession;
    let cameraInput: camera.CameraInput | undefined = this.mCameraInput;
    let previewOutput: camera.PreviewOutput | undefined = this.mPreviewOutput;
    this.mPhotoSession = undefined;
    this.mCameraInput = undefined;
    this.mPreviewOutput = undefined;
    this.curCameraDevice = undefined;

    // 停止当前会话。
    try {
      await photoSession?.stop();
    } catch (error) {
      let err = error as BusinessError;
      console.error(TAG + 'Failed to stop session, errorCode = ' + err.code);
    }

    // 释放相机输入流。
    try {
      await cameraInput?.close();
    } catch (error) {
      let err = error as BusinessError;
      console.error(TAG + 'Failed to close device, errorCode = ' + err.code);
    }

    // 释放预览输出流。
    try {
      await previewOutput?.release();
    } catch (error) {
      let err = error as BusinessError;
      console.error(TAG + 'Failed to release previewOutput, errorCode = ' + err.code);
    }

    // 释放会话。
    try {
      await photoSession?.release();
    } catch (error) {
      let err = error as BusinessError;
      console.error(TAG + 'Failed to release photoSession, errorCode = ' + err.code);
    }
  }

  onFoldStatusChange(): void {
    this.mCameraManager?.on('foldStatusChange', this.foldStatusCallback);
    // display.on('foldStatusChange', this.displayFoldStatusCallback);
  }

  offFoldStatusChange(): void {
    this.mCameraManager?.off('foldStatusChange', this.foldStatusCallback);
    // display.off('foldStatusChange', this.displayFoldStatusCallback);
  }

  findCameraForIntent(cameras: Array<camera.CameraDevice>, cameraPosition: camera.CameraPosition,
    connectionType: camera.ConnectionType = camera.ConnectionType.CAMERA_CONNECTION_BUILT_IN):
    camera.CameraDevice | undefined {
    let candidates: Array<camera.CameraDevice> = cameras.filter((cameraDevice: camera.CameraDevice) => {
      return cameraDevice.cameraPosition === cameraPosition && cameraDevice.connectionType === connectionType;
    });
    // 当前物理 ID 在新形态仍可用时优先保持，减少无意义换镜。
    let currentCamera: camera.CameraDevice | undefined = candidates.find((cameraDevice: camera.CameraDevice) => {
      return cameraDevice.cameraId === this.lastCommittedCameraId;
    });
    if (currentCamera) {
      return currentCamera;
    }
    if (candidates.length === 1) {
      return candidates[0];
    }
    if (candidates.length > 1) {
      console.error(TAG + `Multiple cameras match cameraPosition=${cameraPosition}; configure an explicit selector.`);
      return this.selectCameraByBusinessRole(candidates);
    }
    return undefined;
  }

  selectCameraByBusinessRole(candidates: Array<camera.CameraDevice>): camera.CameraDevice | undefined {
    // 示例策略：选择唯一 DEFAULT；匹配仍不唯一时返回 undefined，不依赖数组顺序。
    let preferredCameras: Array<camera.CameraDevice> = candidates.filter((cameraDevice: camera.CameraDevice) => {
      return cameraDevice.cameraType === this.preferredCameraType;
    });
    if (preferredCameras.length === 1) {
      return preferredCameras[0];
    }
    console.info(TAG + `Ambiguous same-position candidate count=${candidates.length}, ` +
      `preferredType=${this.preferredCameraType}`);
    return undefined;
  }

  prepareCameraPlan(cameras: Array<camera.CameraDevice>, requestedPosition: camera.CameraPosition,
    connectionType: camera.ConnectionType, generation: number): CameraReloadPlan | undefined {
    if (!this.mCameraManager) {
      return undefined;
    }
    let cameraManager: camera.CameraManager = this.mCameraManager;
    // 筛 Profile 前实时刷新基准比例：不依赖 windowSizeChange 已更新缓存断点。
    this.refreshPreviewAspectRatio();
    try {
      let targetCamera: camera.CameraDevice | undefined =
        this.findCameraForIntent(cameras, requestedPosition, connectionType);
      if (!targetCamera) {
        return undefined;
      }
      let sceneModes: Array<camera.SceneMode> = cameraManager.getSupportedSceneModes(targetCamera);
      if (sceneModes.indexOf(camera.SceneMode.NORMAL_PHOTO) < 0) {
        console.error(TAG + 'photo mode not support');
        return undefined;
      }
      let cameraOutputCapability: camera.CameraOutputCapability =
        cameraManager.getSupportedOutputCapability(targetCamera, camera.SceneMode.NORMAL_PHOTO);
      let previewProfile: camera.Profile | undefined = this.getPreviewProfile(cameraOutputCapability);
      if (!previewProfile) {
        console.error(TAG + 'The resolution of the current preview stream is not supported.');
        return undefined;
      }
      return {
        generation: generation,
        requestedPosition: requestedPosition,
        supportedCameras: cameras,
        targetCamera: targetCamera,
        previewProfile: previewProfile
      };
    } catch (error) {
      let err = error as BusinessError;
      console.error(TAG + `Failed to prepare camera reload plan, errorCode=${err.code}`);
      return undefined;
    }
  }

  clearReloadTimer(): void {
    if (this.reloadTimer !== -1) {
      clearTimeout(this.reloadTimer);
      this.reloadTimer = -1;
    }
  }

  schedulePendingWork(delayMs: number = 150): void {
    if (this.reloadPhase === CameraReloadPhase.IN_PROGRESS ||
      this.reloadPhase === CameraReloadPhase.AWAITING_ONLOAD) {
      return;
    }
    this.clearReloadTimer();
    this.reloadPhase = CameraReloadPhase.DEBOUNCING;
    this.reloadTimer = setTimeout((): void => {
      this.reloadTimer = -1;
      if (!this.isComponentActive || this.reloadPhase !== CameraReloadPhase.DEBOUNCING) {
        return;
      }
      if (this.pendingPlanState === CameraPlanState.READY) {
        // flag 已翻转后进入独立阶段；onLoad 到达前的新请求只替换 latest plan，不再二次翻转。
        this.reloadPhase = CameraReloadPhase.AWAITING_ONLOAD;
        this.reloadXComponentFlag = !this.reloadXComponentFlag;
      } else if (this.pendingPlanState === CameraPlanState.UNAVAILABLE) {
        this.reloadPhase = CameraReloadPhase.IDLE;
        this.processCameraWork('').catch((error: BusinessError): void => {
          console.error(TAG + `Failed to teardown unavailable camera, errorCode=${error.code}`);
        });
      } else {
        this.reloadPhase = CameraReloadPhase.IDLE;
      }
    }, delayMs);
  }

  requestCameraReload(supportedCameras?: Array<camera.CameraDevice>): boolean {
    if (!this.mCameraManager || !this.isComponentActive) {
      return false;
    }
    // 每个形态事件都推进 generation；即使当前快照无目标，也必须让旧任务失效。
    this.reloadGeneration++;
    // 终态一到立即隔离旧链的用户可见/可拍能力；150ms 只合并“打开最新目标”的工作。
    this.captureEnabled = false;
    this.switching = true;
    let generation: number = this.reloadGeneration;
    let cameras: Array<camera.CameraDevice> = [];
    try {
      cameras = supportedCameras ?? this.mCameraManager.getSupportedCameras();
    } catch (error) {
      let err = error as BusinessError;
      console.error(TAG + `Failed to obtain supported cameras, errorCode=${err.code}`);
    }
    // 翻转 XComponent 前生成不可变计划，避免目标/Profile 可预见失败时先销毁旧 Surface。
    let plan: CameraReloadPlan | undefined = this.prepareCameraPlan(cameras, this.mCameraPosition,
      camera.ConnectionType.CAMERA_CONNECTION_BUILT_IN, generation);
    if (!plan) {
      this.pendingCameraPlan = undefined;
      this.pendingPlanState = CameraPlanState.UNAVAILABLE;
      this.switching = false;
      this.cameraUnavailable = true;
      if (this.reloadPhase === CameraReloadPhase.IDLE ||
        this.reloadPhase === CameraReloadPhase.DEBOUNCING) {
        this.schedulePendingWork();
      }
      return false;
    }
    this.pendingCameraPlan = plan;
    this.pendingPlanState = CameraPlanState.READY;
    this.cameraUnavailable = false;
    this.switching = true;
    // 真实 150ms 防抖；重复事件重置计时，重建中事件由 generation 合并。
    if (this.reloadPhase === CameraReloadPhase.IDLE ||
      this.reloadPhase === CameraReloadPhase.DEBOUNCING) {
      this.schedulePendingWork();
    }
    return true;
  }

  async loadXComponent(controller: XComponentController): Promise<void> {
    let surfaceId: string = controller.getXComponentSurfaceId();
    // 锁定 Surface 随系统旋转，方向由应用层控制；矩形按当前窗口 letterbox 拟合。
    controller.setXComponentSurfaceRotation({ lock: true });
    await this.applySurfaceRect(controller);
    console.info(TAG + `mCameraPosition: ${this.mCameraPosition}`)
    await this.processCameraWork(surfaceId);
  }

  async processCameraWork(surfaceId: string): Promise<void> {
    if (!this.isComponentActive) {
      return;
    }
    // 极端情况下第二个 Surface 在当前工作完成前到达：记录最新 Surface、使旧任务失效，稍后补建。
    if (this.reloadPhase === CameraReloadPhase.IN_PROGRESS) {
      if (surfaceId.length > 0) {
        this.pendingSurfaceId = surfaceId;
      }
      this.reloadGeneration++;
      let generation: number = this.reloadGeneration;
      if (this.pendingPlanState !== CameraPlanState.UNAVAILABLE && this.mCameraManager) {
        let cameras: Array<camera.CameraDevice> = [];
        try {
          cameras = this.pendingCameraPlan?.supportedCameras ?? this.mCameraManager.getSupportedCameras();
        } catch (error) {
          let err = error as BusinessError;
          console.error(TAG + `Failed to refresh duplicate Surface plan, errorCode=${err.code}`);
        }
        this.pendingCameraPlan = this.prepareCameraPlan(cameras, this.mCameraPosition,
          camera.ConnectionType.CAMERA_CONNECTION_BUILT_IN, generation);
        this.pendingPlanState = this.pendingCameraPlan ? CameraPlanState.READY : CameraPlanState.UNAVAILABLE;
      }
      return;
    }
    this.clearReloadTimer();
    if (surfaceId.length > 0) {
      this.mSurfaceId = surfaceId;
    }
    let generation: number = this.reloadGeneration;
    let plan: CameraReloadPlan | undefined = this.pendingCameraPlan;
    // 只有首次启动或已稳定后出现的新 Surface 可以主动查询；UNAVAILABLE 必须尊重最新回调快照。
    if (!plan && this.mCameraManager &&
      (this.pendingPlanState === CameraPlanState.BOOTSTRAP ||
        this.pendingPlanState === CameraPlanState.STABLE)) {
      if (this.pendingPlanState === CameraPlanState.STABLE) {
        this.reloadGeneration++;
        generation = this.reloadGeneration;
      }
      try {
        let cameras: Array<camera.CameraDevice> = this.mCameraManager.getSupportedCameras();
        plan = this.prepareCameraPlan(cameras, this.mCameraPosition,
          camera.ConnectionType.CAMERA_CONNECTION_BUILT_IN, generation);
      } catch (error) {
        let err = error as BusinessError;
        console.error(TAG + `Failed to prepare initial camera plan, errorCode=${err.code}`);
      }
      this.pendingCameraPlan = plan;
      this.pendingPlanState = plan ? CameraPlanState.READY : CameraPlanState.UNAVAILABLE;
    }
    this.reloadPhase = CameraReloadPhase.IN_PROGRESS;
    let initialized: boolean = false;
    try {
      if (this.pendingPlanState === CameraPlanState.READY && plan && surfaceId.length > 0) {
        initialized = await this.initCamera(this.mSurfaceId, plan);
        if (!initialized) {
          await this.releaseCamera();
        }
      } else if (this.pendingPlanState === CameraPlanState.UNAVAILABLE) {
        // 不只遮住预览：串行释放旧链，避免底层继续占用或被兜底到错误镜头。
        await this.releaseCamera();
      } else if (this.pendingPlanState === CameraPlanState.READY) {
        console.error(TAG + 'Camera reload plan or Surface is unavailable.');
        await this.releaseCamera();
      }
    } finally {
      this.reloadPhase = CameraReloadPhase.IDLE;
      if (!this.isComponentActive) {
        return;
      }
      if (this.pendingSurfaceId.length > 0) {
        let latestSurfaceId: string = this.pendingSurfaceId;
        this.pendingSurfaceId = '';
        await this.processCameraWork(latestSurfaceId);
      } else if (generation !== this.reloadGeneration) {
        this.schedulePendingWork();
      } else if (initialized) {
        this.pendingCameraPlan = undefined;
        this.pendingPlanState = CameraPlanState.STABLE;
        this.switching = false;
        this.cameraUnavailable = false;
        this.captureEnabled = true;
      } else {
        this.pendingCameraPlan = undefined;
        this.pendingPlanState = CameraPlanState.UNAVAILABLE;
        this.switching = false;
        this.cameraUnavailable = true;
        this.captureEnabled = false;
      }
    }
  }

  isReloadStale(generation: number): boolean {
    return !this.isComponentActive || generation !== this.reloadGeneration;
  }

  // 时序防御：比例基准在生成重建计划时实时计算，不依赖 windowSizeChange 先更新缓存断点。
  refreshPreviewAspectRatio(): void {
    let uiContext: UIContext = this.getUIContext();
    let widthBp: WidthBreakpoint = uiContext.getWindowWidthBreakpoint();
    let heightBp: HeightBreakpoint = uiContext.getWindowHeightBreakpoint();
    // 阔折叠外屏是方屏：基准 1:1；其余形态 4:3。
    this.previewAspectRatio =
      (widthBp === WidthBreakpoint.WIDTH_SM && heightBp === HeightBreakpoint.HEIGHT_MD) ? 1 : 4 / 3;
  }

  async getWindowRect(): Promise<window.Rect> {
    try {
      let mainWindow: window.Window = await window.getLastWindow(this.mContext!);
      return mainWindow.getWindowProperties().windowRect;
    } catch (error) {
      let err = error as BusinessError;
      console.error(`${TAG} getLastWindow call failed, error: ${err.code}`);
      let displayData = display.getDefaultDisplaySync();
      return { left: 0, top: 0, width: displayData.width, height: displayData.height };
    }
  }

  // 以窗口为容器做 letterbox 拟合：Surface 比例 0°/180° 为基准的倒数、90°/270° 与基准一致，余量留黑边。
  computeSurfaceRect(windowRect: window.Rect): SurfaceRect {
    this.refreshPreviewAspectRatio();
    let rect: SurfaceRect = {
      surfaceWidth: windowRect.width,
      surfaceHeight: windowRect.height
    };
    let uiContext: UIContext = this.getUIContext();
    let widthBp: WidthBreakpoint = uiContext.getWindowWidthBreakpoint();
    let heightBp: HeightBreakpoint = uiContext.getWindowHeightBreakpoint();
    if (widthBp === WidthBreakpoint.WIDTH_SM && heightBp === HeightBreakpoint.HEIGHT_MD) {
      // 方屏外屏基准 1:1，Surface 直接铺满全屏，不做 letterbox。
      return rect;
    }
    let rotationDeg: number = display.getDefaultDisplaySync().rotation * 90;
    if (rotationDeg === 0 || rotationDeg === 180) {
      if (windowRect.height * 3 / 4 > windowRect.width) {
        rect.surfaceHeight = windowRect.width / 3 * 4;
      } else {
        rect.surfaceWidth = windowRect.height / 4 * 3;
      }
    } else {
      if (windowRect.width * 3 / 4 > windowRect.height) {
        rect.surfaceWidth = windowRect.height / 3 * 4;
      } else {
        rect.surfaceHeight = windowRect.width / 4 * 3;
      }
    }
    return rect;
  }

  async applySurfaceRect(controller: XComponentController): Promise<void> {
    let windowRect: window.Rect = await this.getWindowRect();
    this.surfaceRect = this.computeSurfaceRect(windowRect);
    controller.setXComponentSurfaceRect(this.surfaceRect);
  }

  getPreviewProfile(cameraOutputCapability: camera.CameraOutputCapability): camera.Profile | undefined {
    let previewProfiles = cameraOutputCapability.previewProfiles;
    if (previewProfiles.length < 1) {
      return undefined;
    }
    // 按基准比例筛最大档（比值差 ≤ 0.1），不按固定分辨率精确匹配，也不按组件宽高筛。
    let resProfile: camera.Profile | undefined = undefined;
    let maxWidth: number = 0;
    for (let i: number = 0; i < previewProfiles.length; i++) {
      if (Math.abs(previewProfiles[i].size.width / previewProfiles[i].size.height - this.previewAspectRatio) <= 0.1 &&
        previewProfiles[i].size.width > maxWidth) {
        maxWidth = previewProfiles[i].size.width;
        resProfile = previewProfiles[i];
      }
    }
    return resProfile;
  }

  async initCamera(surfaceId: string, plan: CameraReloadPlan): Promise<boolean> {
    // 创建CameraManager对象。
    if (!this.mCameraManager || surfaceId.length === 0) {
      console.error(TAG + 'camera.getCameraManager error');
      return false;
    }

    let cameraArray: Array<camera.CameraDevice> = plan.supportedCameras;
    let cameraPosition: camera.CameraPosition = plan.requestedPosition;
    let targetCamera: camera.CameraDevice = plan.targetCamera;
    let previewProfile: camera.Profile = plan.previewProfile;
    let generation: number = plan.generation;

    for (let index = 0; index < cameraArray.length; index++) {
      console.info(TAG + 'cameraId : ' + cameraArray[index].cameraId); // 获取相机ID。
      console.info(TAG + 'cameraPosition : ' + cameraArray[index].cameraPosition); // 获取相机位置。
      console.info(TAG + 'cameraType : ' + cameraArray[index].cameraType); // 获取相机类型。
      console.info(TAG + 'connectionType : ' + cameraArray[index].connectionType); // 获取相机连接类型。
    }

    if (this.isReloadStale(generation)) {
      return false;
    }

    let oldCameraId: string = this.curCameraDevice?.cameraId ?? this.lastCommittedCameraId ?? 'none';
    await this.releaseCamera();
    if (this.isReloadStale(generation)) {
      return false;
    }

    // 创建相机输入流。
    try {
      this.mCameraInput = this.mCameraManager.createCameraInput(targetCamera);
    } catch (error) {
      let err = error as BusinessError;
      console.error(TAG + 'Failed to createCameraInput errorCode = ' + err.code);
    }
    if (this.mCameraInput === undefined) {
      return false;
    }

    // 打开相机。
    try {
      await this.mCameraInput.open();
    } catch (error) {
      let err = error as BusinessError;
      console.error(TAG + 'Failed to open device, errorCode = ' + err.code);
      await this.releaseCamera();
      return false;
    }
    if (this.isReloadStale(generation)) {
      await this.releaseCamera();
      return false;
    }

    // 创建预览输出流,其中参数 surfaceId 参考上文 XComponent 组件，预览流为XComponent组件提供的surface。
    try {
      this.mPreviewOutput = this.mCameraManager.createPreviewOutput(previewProfile, surfaceId);
    } catch (error) {
      let err = error as BusinessError;
      console.error(TAG + `Failed to create the PreviewOutput instance. error code: ${err.code}`);
    }
    if (!this.mPreviewOutput) {
      await this.releaseCamera();
      return false;
    }

    // 创建会话。
    try {
      let session = this.mCameraManager.createSession(camera.SceneMode.NORMAL_PHOTO);
      if (!session) {
        await this.releaseCamera();
        return false;
      }
      this.mPhotoSession = session as camera.PhotoSession;
    } catch (error) {
      let err = error as BusinessError;
      console.error(TAG + 'Failed to create the session instance. errorCode = ' + err.code);
    }

    if (!this.mPhotoSession) {
      await this.releaseCamera();
      return false;
    }

    // 开始配置会话。
    try {
      this.mPhotoSession.beginConfig();
    } catch (error) {
      let err = error as BusinessError;
      console.error(TAG + 'Failed to beginConfig. errorCode = ' + err.code);
      await this.releaseCamera();
      return false;
    }

    // 向会话中添加相机输入流。
    try {
      this.mPhotoSession.addInput(this.mCameraInput);
    } catch (error) {
      let err = error as BusinessError;
      console.error(TAG + 'Failed to addInput. errorCode = ' + err.code);
      await this.releaseCamera();
      return false;
    }

    // 向会话中添加预览输出流。
    try {
      this.mPhotoSession.addOutput(this.mPreviewOutput);
    } catch (error) {
      let err = error as BusinessError;
      console.error(TAG + 'Failed to addOutput(previewOutput). errorCode = ' + err.code);
      await this.releaseCamera();
      return false;
    }

    // 提交会话配置。
    try {
      await this.mPhotoSession.commitConfig();
    } catch (error) {
      let err = error as BusinessError;
      console.error(TAG + 'Failed to commit session configuration, errorCode = ' + err.code);
      await this.releaseCamera();
      return false;
    }
    if (this.isReloadStale(generation)) {
      await this.releaseCamera();
      return false;
    }

    // 启动会话。
    try {
      await this.mPhotoSession.start()
    } catch (error) {
      let err = error as BusinessError;
      console.error(TAG + 'Failed to start session. errorCode = ' + err.code);
      await this.releaseCamera();
      return false;
    }
    if (this.isReloadStale(generation)) {
      // 新形态已到达时，旧 generation 即使 start 成功也不得提交设备状态。
      await this.releaseCamera();
      return false;
    }
    // 只有新 Session 启动成功后才提交实际设备，保证业务位置状态与画面一致。
    this.curCameraDevice = targetCamera;
    this.lastCommittedCameraId = targetCamera.cameraId;
    console.info(TAG + `Camera continuity requestedPosition=${cameraPosition}, oldCameraId=${oldCameraId}, ` +
      `newCameraId=${targetCamera.cameraId}, actualPosition=${targetCamera.cameraPosition}`);
    return true;
  }

  build() {
    if (this.isShow) {
      Stack() {
        if (this.reloadXComponentFlag) {
          XComponent(this.mXComponentOptionsA)
            .onLoad(async () => {
              await this.loadXComponent(this.mXComponentControllerA);
            })
            .width('100%')
            .height('100%')
        } else {
          XComponent(this.mXComponentOptionsB)
            .onLoad(async () => {
              await this.loadXComponent(this.mXComponentControllerB);
            })
            .width('100%')
            .height('100%')
        }
        Text('切换相机')
          .size({ width: 80, height: 48 })
          .position({ x: 1, y: 1 })
          .backgroundColor(Color.White)
          .textAlign(TextAlign.Center)
          .borderRadius(24)
          .onClick(() => {
            if (!this.mCameraManager) {
              return;
            }
            let nextPosition: camera.CameraPosition =
              this.mCameraPosition === camera.CameraPosition.CAMERA_POSITION_BACK ?
              camera.CameraPosition.CAMERA_POSITION_FRONT : camera.CameraPosition.CAMERA_POSITION_BACK;
            let cameras: Array<camera.CameraDevice> = [];
            try {
              cameras = this.mCameraManager.getSupportedCameras();
            } catch (error) {
              let err = error as BusinessError;
              console.error(TAG + `Failed to obtain supported cameras, errorCode=${err.code}`);
              return;
            }
            if (!this.findCameraForIntent(cameras, nextPosition)) {
              console.error(TAG + `Requested cameraPosition=${nextPosition} is unavailable; keep current preview.`);
              return;
            }
            this.mCameraPosition = nextPosition;
            this.isFront = nextPosition === camera.CameraPosition.CAMERA_POSITION_FRONT;
            this.requestCameraReload(cameras);
          })
          .enabled(this.captureEnabled && !this.switching && !this.cameraUnavailable)
        if (this.cameraUnavailable) {
          Column() {
            Text('当前形态没有可用的目标相机')
              .fontColor(Color.White)
              .fontSize(16)
          }
          .width('100%')
          .height('100%')
          .justifyContent(FlexAlign.Center)
          .backgroundColor(Color.Black)
        } else if (this.switching) {
          Column() {
            LoadingProgress().width(48).height(48)
          }
          .width('100%')
          .height('100%')
          .justifyContent(FlexAlign.Center)
          .backgroundColor(Color.Black)
        }
      }
      .size({ width: '100%', height: '100%' })
      .backgroundColor(Color.Black)
    }
  }
}
