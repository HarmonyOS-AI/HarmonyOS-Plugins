import display from '@ohos.display';
import { window, UIContext } from '@kit.ArkUI';
import { Callback } from '@ohos.base';

/**
 * HoverStateUtil.ets —— 悬停态判定与折痕几何写入 AppStorage
 *
 * 官方 API：
 * - display.getFoldStatus() / display.getCurrentFoldCreaseRegion()
 * - display.getDefaultDisplaySync().orientation
 * - display.on/off('foldStatusChange') · window.on/off('windowSizeChange')
 *
 * 职责边界：本文件只负责**判定与状态写入**，不负责布局。
 * 分区怎么切、内容保护间距怎么加，见 CreaseAvoidance.ets 与
 * domains/fold-form.md「折痕避让」。
 *
 * 只处理**横折痕**（上下分区）。竖折痕设备的方向判定要走三级检测
 * （轴比 1.35 → 几何评分 0.22 → 方向锁定），见 domains/fold-form.md
 * 「折痕方向要三级判定」，本模板不含方向检测。
 *
 * 相对参考实现修正的四处（均对应 domains/fold-form.md 里已写明的约束）：
 * 1. 方向判定改用 display.Orientation 枚举，不再用裸数字 1/3。
 *    数值本身是对的（LANDSCAPE=1、LANDSCAPE_INVERTED=3），但裸数字读不出语义，
 *    后续维护者无法判断它是否还与 SDK 一致。
 * 2. 折痕厚度按屏幕对应维度的 35% 钳位，超限回退 8vp。与 CreaseAvoidance.ets
 *    同口径——少这道保险时，一次几何误算就让折痕带吃掉整个内容区（悬停态黑屏）。
 * 3. 拿不到折痕数据时回退到「屏幕 50% 分割 + 8vp 薄边估算」，
 *    不再硬编码 topHeight=300 / creaseHeight=24。那两个数字不对应任何设备的实测值，
 *    在小折叠上会把分界线推到屏幕外。
 * 4. 监听按引用注销。参考实现只 on 不 off，页面反复进出会累积监听；
 *    且裸 off('windowSizeChange') 会连带删掉别的组件注册的回调。
 *
 * 换算说明：px→vp 需要 UIContext（全局 px2vp 已废弃，且在多窗口/分屏下基准不对），
 * 所以本文件的换算函数要求调用方传入 UIContext。
 */

/** 折痕带占屏幕对应维度的上限；超过判定为几何数据异常。 */
const MAX_CREASE_RATIO: number = 0.35;
/** 异常或无数据时回退用的折痕物理短边估算值（vp）。 */
const FALLBACK_CREASE_VP: number = 8;

/**
 * 折痕厚度安全钳位：折痕带不应超过屏幕对应维度的 35%。
 * 超限说明几何数据异常，回退到折痕物理短边的估算值 8vp。
 */
function clampCreaseThickness(creaseHeightVp: number, screenDimensionVp: number): number {
  if (screenDimensionVp <= 0) {
    return creaseHeightVp;
  }
  const maxThickness: number = screenDimensionVp * MAX_CREASE_RATIO;
  if (creaseHeightVp > maxThickness) {
    return Math.min(creaseHeightVp, FALLBACK_CREASE_VP);
  }
  return creaseHeightVp;
}

/** 悬停态的第二个判定条件：必须是横屏。竖向半折不进悬停布局。 */
function isLandscapeOrientation(orientation: display.Orientation): boolean {
  return orientation === display.Orientation.LANDSCAPE
    || orientation === display.Orientation.LANDSCAPE_INVERTED;
}

function resetHoverState(): void {
  AppStorage.setOrCreate('isHover', false);
  AppStorage.setOrCreate('isHoverLandscape', false);
  AppStorage.setOrCreate('hoverTopHeight', 0);
  AppStorage.setOrCreate('hoverCreaseHeight', 0);
  AppStorage.setOrCreate('hoverHasCrease', false);
}

/**
 * 更新折叠屏悬停状态到 AppStorage。
 *
 * 写入的 key：
 * - isHover           折叠状态是否为 HALF_FOLDED
 * - isHoverLandscape  是否横屏。**悬停布局的判定是 isHover && isHoverLandscape 两个条件**
 * - hoverTopHeight    折痕上边界距根容器顶部的距离（vp）
 * - hoverCreaseHeight 折痕带厚度（vp，已钳位）
 * - hoverHasCrease    折痕几何是否来自真实数据；false 表示走了 50% 兜底
 *
 * 调用时机：
 * 1. 页面 aboutToAppear 时
 * 2. display.on('foldStatusChange') 触发时
 * 3. window.on('windowSizeChange') 触发时（屏幕旋转）
 *
 * @param uiContext 换算 px→vp 用。必须在 loadContent 回调之后才能取到。
 */
export function updateFoldStatusFromDisplay(uiContext: UIContext): void {
  let status: display.FoldStatus;
  try {
    status = display.getFoldStatus();
  } catch (e) {
    console.error('HoverStateUtil: getFoldStatus failed', e);
    resetHoverState();
    return;
  }

  if (status !== display.FoldStatus.FOLD_STATUS_HALF_FOLDED) {
    resetHoverState();
    AppStorage.setOrCreate('hoverLayoutDirty', true);
    return;
  }

  let topHeightVp: number = 0;
  let creaseHeightVp: number = 0;
  let hasCrease: boolean = false;
  let isHoverLandscape: boolean = false;
  let screenHeightVp: number = 0;

  try {
    const disp: display.Display = display.getDefaultDisplaySync();
    screenHeightVp = uiContext.px2vp(disp.height);
    isHoverLandscape = isLandscapeOrientation(disp.orientation);
  } catch (e) {
    console.error('HoverStateUtil: read display failed', e);
  }

  try {
    const region: display.FoldCreaseRegion = display.getCurrentFoldCreaseRegion();
    if (region && region.creaseRects && region.creaseRects.length > 0) {
      const rect = region.creaseRects[0];
      const rawTopVp: number = uiContext.px2vp(rect.top);
      const rawHeightVp: number = uiContext.px2vp(rect.height);
      topHeightVp = rawTopVp;
      creaseHeightVp = clampCreaseThickness(rawHeightVp, screenHeightVp);
      hasCrease = true;
    }
  } catch (e) {
    console.error('HoverStateUtil: getCurrentFoldCreaseRegion failed', e);
  }

  if (!hasCrease) {
    // 无折痕数据仍然进入悬停态：按屏幕 50% 分割 + 薄边估算兜底。
    // 上层可通过 hoverHasCrease=false 得知这不是真实折痕几何。
    creaseHeightVp = FALLBACK_CREASE_VP;
    topHeightVp = screenHeightVp > 0
      ? Math.max(0, screenHeightVp * 0.5 - creaseHeightVp * 0.5)
      : 0;
  }

  AppStorage.setOrCreate('isHover', true);
  AppStorage.setOrCreate('isHoverLandscape', isHoverLandscape);
  AppStorage.setOrCreate('hoverTopHeight', topHeightVp);
  AppStorage.setOrCreate('hoverCreaseHeight', creaseHeightVp);
  AppStorage.setOrCreate('hoverHasCrease', hasCrease);
  // 可选通用标记：上层可按需监听此标记触发布局重算。
  AppStorage.setOrCreate('hoverLayoutDirty', true);
}

/**
 * 悬停状态监听器。
 *
 * 用法（EntryAbility）：
 *   private hoverListener = new HoverStateListener();
 *
 *   onWindowStageCreate(windowStage: window.WindowStage): void {
 *     windowStage.loadContent('pages/Index', (err) => {
 *       if (err.code) { return; }
 *       // getUIContext 依赖 UIContent，必须在 loadContent 回调内取
 *       this.hoverListener.register(windowStage, windowStage.getMainWindowSync().getUIContext());
 *     });
 *   }
 *
 *   onWindowStageDestroy(): void {
 *     this.hoverListener.unregister();
 *   }
 */
export class HoverStateListener {
  private uiContext?: UIContext;
  private mainWindow?: window.Window;
  // 保存回调引用，注销时按引用移除；裸 off('事件名') 会删掉别的组件的监听。
  private sizeChangeCallback?: Callback<window.Size>;
  private foldStatusCallback?: Callback<display.FoldStatus>;

  register(windowStage: window.WindowStage, uiContext: UIContext): void {
    this.uiContext = uiContext;
    try {
      this.mainWindow = windowStage.getMainWindowSync();
    } catch (e) {
      console.error('HoverStateListener: getMainWindowSync failed', e);
      return;
    }

    updateFoldStatusFromDisplay(uiContext);

    this.sizeChangeCallback = (_size: window.Size) => {
      if (this.uiContext) {
        updateFoldStatusFromDisplay(this.uiContext);
      }
    };
    this.foldStatusCallback = (_status: display.FoldStatus) => {
      if (this.uiContext) {
        updateFoldStatusFromDisplay(this.uiContext);
      }
    };

    try {
      this.mainWindow.on('windowSizeChange', this.sizeChangeCallback);
      display.on('foldStatusChange', this.foldStatusCallback);
    } catch (e) {
      console.error('HoverStateListener: register failed', e);
    }
  }

  unregister(): void {
    try {
      if (this.mainWindow && this.sizeChangeCallback) {
        this.mainWindow.off('windowSizeChange', this.sizeChangeCallback);
      }
      if (this.foldStatusCallback) {
        display.off('foldStatusChange', this.foldStatusCallback);
      }
    } catch (e) {
      console.error('HoverStateListener: unregister failed', e);
    }
    this.sizeChangeCallback = undefined;
    this.foldStatusCallback = undefined;
    this.mainWindow = undefined;
    this.uiContext = undefined;
  }
}
