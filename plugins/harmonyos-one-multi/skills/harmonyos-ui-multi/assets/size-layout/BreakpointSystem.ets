/**
 * BreakpointSystem.ets —— 断点系统的**唯一**标准实现
 *
 * 多份参考实现各有优缺点，收编时合并为这一套（见 references/assets-catalog.md）：
 *   - 横向断点以 UIContext.getWindowWidthBreakpoint() 为事实源；
 *   - 窗口变化采用 SystemBreakpointManager 的 windowSizeChange 思路；
 *   - 回调注册/注销采用 BreakpointUtils 的同引用写法；
 *   - 状态采用 @ObservedV2 + @Trace，由消费组件通过 @Local 引用。
 *   - 不收：example/BreakpointUtils.ets（4 档、无初始同步、AppStorageV2，与标准版互斥）
 *   - 不收：BreakpointConstants.ets（把 320/600/840/1440 写成常量，
 *           违反"阈值不可硬编码"——官方注明阈值可被产品化调整）
 *   - 不收：BreakpointObserver.ets（与本文件同职责，且用裸 off 注销，
 *           会连带移除别的组件在同一事件上的监听）
 *   - 并入：BreakpointType<T> 泛型取值工具（见文件末尾）
 *
 * **相对参考实现修正的缺陷**：不再用物理屏幕 display.width 初始化窗口断点；
 * 不再匿名注册后裸 off；纵向断点按真实窗口的 height / width 计算，并随窗口尺寸与 DPI 更新。
 *
 * 使用纪律：
 *   1. 在 windowStage.loadContent(...) 实际加载的入口页 aboutToAppear() 中取得
 *      mainWindow 和 UIContext 后 register()；在该入口页 aboutToDisappear() 中
 *      unregister()。业务页、NavDestination 和 Router 推入页不得注册。
 *   2. @ComponentV2 通过 `@Local bpState = BreakpointSystem.state` 消费；
 *      直接保存 getter 结果或用普通变量不会响应 lg → md → lg。
 *   3. register() 幂等；重复调用只刷新，不叠加监听。
 */

import { window } from '@kit.ArkUI';

// ========= 横向断点：按窗口宽度 vp =========
export enum BreakpointTypeEnum {
  XS = 'xs',  // [0, 320)vp     — 超小窗口
  SM = 'sm',  // [320, 600)vp   — 直板机竖屏、折叠外屏
  MD = 'md',  // [600, 840)vp   — 折叠内屏展开、小平板竖屏
  LG = 'lg',  // [840, 1440)vp  — 平板横屏、三折展开
  XL = 'xl',  // [1440, +∞)vp   — 超宽窗口
}

// ========= 纵向断点：按**高宽比**（height / width） =========
export enum VerticalBreakpointEnum {
  SM = 'sm',  // 高宽比 < 0.8      — 横向窗口（平板横屏等）
  MD = 'md',  // [0.8, 1.2)        — 方屏 / 近方屏（Pura X 外屏、Mate X 展开态）
  LG = 'lg',  // ≥ 1.2             — 纵向窗口（直板机竖屏、折叠态）
}

// ========= 状态容器 =========
@ObservedV2
export class BreakpointState {
  @Trace value: BreakpointTypeEnum = BreakpointTypeEnum.SM;
  @Trace vertical: VerticalBreakpointEnum = VerticalBreakpointEnum.LG;

  get isXs(): boolean { return this.value === BreakpointTypeEnum.XS; }
  get isSm(): boolean { return this.value === BreakpointTypeEnum.SM; }
  get isMd(): boolean { return this.value === BreakpointTypeEnum.MD; }
  get isLg(): boolean { return this.value === BreakpointTypeEnum.LG; }
  get isXl(): boolean { return this.value === BreakpointTypeEnum.XL; }

  /**
   * md 及以上。**这不等于 isLg** —— 折叠屏展开态是 md，
   * 放得下双列列表但放不下侧边栏。"要不要多列"用 isWide，
   * "要不要侧边栏"用 isLg，混用会让展开态挤成一团。
   */
  get isWide(): boolean {
    return this.value === BreakpointTypeEnum.MD
      || this.value === BreakpointTypeEnum.LG
      || this.value === BreakpointTypeEnum.XL;
  }

  /** 近方屏（阔折叠外屏、部分展开态）。按"竖屏"假设写的布局在这里会失效。 */
  get isSquare(): boolean { return this.vertical === VerticalBreakpointEnum.MD; }
}

const globalBreakpointState = new BreakpointState();

// ========= 断点系统 =========
export class BreakpointSystem {
  private static uiContext: UIContext | null = null;
  private static mainWindow: window.Window | null = null;
  private static registered: boolean = false;
  private static densityListening: boolean = false;

  private static readonly windowSizeChangeCallback = (_size: window.Size): void => {
    BreakpointSystem.refresh();
  };

  private static readonly systemDensityChangeCallback = (_density: number): void => {
    BreakpointSystem.refresh();
  };

  static readonly state: BreakpointState = globalBreakpointState;

  /** 在 loadContent 加载的入口页 aboutToAppear() 调用；重复调用不会叠加监听。 */
  static register(uiContext: UIContext, mainWindow: window.Window): void {
    if (BreakpointSystem.registered) {
      // 已注册时继续使用原窗口与原回调；覆盖字段会导致旧窗口监听无法注销。
      BreakpointSystem.refresh();
      return;
    }

    BreakpointSystem.uiContext = uiContext;
    BreakpointSystem.mainWindow = mainWindow;
    mainWindow.on('windowSizeChange', BreakpointSystem.windowSizeChangeCallback);
    if (canIUse('SystemCapability.Window.SessionManager')) {
      mainWindow.on('systemDensityChange', BreakpointSystem.systemDensityChangeCallback);
      BreakpointSystem.densityListening = true;
    }
    BreakpointSystem.registered = true;
    BreakpointSystem.refresh();
  }

  static unregister(): void {
    if (!BreakpointSystem.registered || !BreakpointSystem.mainWindow) {
      return;
    }
    BreakpointSystem.mainWindow.off('windowSizeChange', BreakpointSystem.windowSizeChangeCallback);
    if (BreakpointSystem.densityListening) {
      BreakpointSystem.mainWindow.off('systemDensityChange', BreakpointSystem.systemDensityChangeCallback);
    }
    BreakpointSystem.uiContext = null;
    BreakpointSystem.mainWindow = null;
    BreakpointSystem.registered = false;
    BreakpointSystem.densityListening = false;
  }

  /** 每次从当前窗口重新读取，不缓存宽度，也不使用物理屏幕尺寸。 */
  private static refresh(): void {
    const uiContext = BreakpointSystem.uiContext;
    const mainWindow = BreakpointSystem.mainWindow;
    if (!uiContext || !mainWindow) {
      return;
    }

    globalBreakpointState.value = BreakpointSystem.fromSystemBreakpoint(
      uiContext.getWindowWidthBreakpoint()
    );

    const rect = mainWindow.getWindowProperties().windowRect;
    const widthVp = uiContext.px2vp(rect.width);
    const heightVp = uiContext.px2vp(rect.height);
    BreakpointSystem.updateVerticalBreakpoint(widthVp, heightVp);
  }

  private static fromSystemBreakpoint(breakpoint: WidthBreakpoint): BreakpointTypeEnum {
    switch (breakpoint) {
      case WidthBreakpoint.WIDTH_XL:
        return BreakpointTypeEnum.XL;
      case WidthBreakpoint.WIDTH_LG:
        return BreakpointTypeEnum.LG;
      case WidthBreakpoint.WIDTH_MD:
        return BreakpointTypeEnum.MD;
      default:
        // 系统 WidthBreakpoint 最小档为 WIDTH_SM；XS 仅保留给已有自定义断点工程兼容。
        return BreakpointTypeEnum.SM;
    }
  }

  /**
   * 纵向断点按**高宽比**分档。
   *
   * 修正记录：参考实现写的是 `widthVp / heightVp`，方向反了——
   * 直板机 374×827 按高宽比是 2.21 → lg（官方口径），按宽高比是 0.45 → sm。
   * 全套设备矩阵（references/device-matrix.md）与官方 8 种屏幕形态分类
   * 都以高宽比为准。
   */
  private static updateVerticalBreakpoint(widthVp: number, heightVp: number): void {
    if (widthVp <= 0) {
      return;
    }
    const aspect: number = heightVp / widthVp;
    if (aspect >= 1.2) {
      globalBreakpointState.vertical = VerticalBreakpointEnum.LG;
    } else if (aspect >= 0.8) {
      globalBreakpointState.vertical = VerticalBreakpointEnum.MD;
    } else {
      globalBreakpointState.vertical = VerticalBreakpointEnum.SM;
    }
  }
}

/**
 * 按断点取值的泛型工具（并入自参考实现 BreakpointType.ets）。
 *
 * 省掉满屏的三元嵌套：
 *   const lanes = new BreakpointType<number>(1, 2, 3).getValue(BreakpointSystem.state.value)
 *   const gutter = new BreakpointType<number>(12, 16, 24).getValue(BreakpointSystem.state.value)
 *
 * 未给的档位向下回退（xl 缺省用 lg，lg 缺省用 md，md 缺省用 sm），
 * 因此只在真正需要差异的档位上传值即可。
 */
export class BreakpointType<T> {
  private xs?: T;
  private sm: T;
  private md?: T;
  private lg?: T;
  private xl?: T;

  constructor(sm: T, md?: T, lg?: T, xl?: T, xs?: T) {
    this.sm = sm;
    this.md = md;
    this.lg = lg;
    this.xl = xl;
    this.xs = xs;
  }

  /**
   * 按**系统断点**取值。工程用 `UIContext.getWindowWidthBreakpoint()` 时走这个。
   * 系统断点没有 xs 档，最小档即 WIDTH_SM。
   */
  getValueOfSystem(breakpoint: WidthBreakpoint): T {
    switch (breakpoint) {
      case WidthBreakpoint.WIDTH_XL:
        return this.xl ?? this.lg ?? this.md ?? this.sm;
      case WidthBreakpoint.WIDTH_LG:
        return this.lg ?? this.md ?? this.sm;
      case WidthBreakpoint.WIDTH_MD:
        return this.md ?? this.sm;
      default:
        return this.sm;
    }
  }

  /** 按本文件的 mediaquery 断点取值。 */
  getValue(breakpoint: BreakpointTypeEnum): T {
    switch (breakpoint) {
      case BreakpointTypeEnum.XL:
        return this.xl ?? this.lg ?? this.md ?? this.sm;
      case BreakpointTypeEnum.LG:
        return this.lg ?? this.md ?? this.sm;
      case BreakpointTypeEnum.MD:
        return this.md ?? this.sm;
      case BreakpointTypeEnum.XS:
        return this.xs ?? this.sm;
      default:
        return this.sm;
    }
  }
}
