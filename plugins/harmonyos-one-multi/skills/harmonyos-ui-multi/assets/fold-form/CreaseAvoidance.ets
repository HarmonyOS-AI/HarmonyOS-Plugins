import display from '@ohos.display';

/**
 * CreaseAvoidance.ets —— 按真实折痕几何做上下分区
 *
 * 官方 API 模板：
 * - display.getCurrentFoldCreaseRegion()
 * - display.convertGlobalToRelativeCoordinate(...)
 * - display.on/off('foldStatusChange', ...)
 *
 * 用法说明：
 * - rootGlobalYVp 需要接入页面根容器的全局 Y 偏移，避免分界线整体偏移。
 * - 只处理**横折痕**（上下分区）。竖折痕设备与近方形设备的方向判定见
 *   domains/fold-form.md「折痕方向要三级判定」，本模板不含方向检测。
 *
 * 相对参考实现补齐的三处（均对应 domains/fold-form.md 里已写明的约束）：
 * 1. 坐标换算用 uiContext.px2vp()，不是全局 px2vp()——折痕坐标属于窗口坐标系，
 *    全局函数在多窗口/分屏下换算基准不对。
 * 2. 折痕厚度按屏幕对应维度的 35% 钳位，超限回退 8vp。少这道保险时，
 *    一次几何误算就会让折痕带吃掉整个内容区，表现为悬停态黑屏。
 * 3. 上下分区各留内容保护间距（上 16vp / 下 40vp）。这两个值加在分区**内部**，
 *    分界线仍以折痕真实边界为准——把它们当分界线偏移量是最高频的理解错误。
 */
@Entry
@Component
struct CreaseAvoidanceExample {
  // 折痕带占屏幕对应维度的上限；超过判定为几何数据异常。
  private static readonly MAX_CREASE_RATIO: number = 0.35;
  // 异常时回退用的折痕物理短边估算值（vp）。
  private static readonly FALLBACK_CREASE_VP: number = 8;
  // 内容保护间距：加在分区**内部**，不移动分界线。
  private static readonly UPPER_CONTENT_GAP_VP: number = 16;
  private static readonly LOWER_CONTENT_GAP_VP: number = 40;

  @State private rootHeightVp: number = 0;
  @State private splitLineVp: number = 0;
  @State private creaseHeightVp: number = 0;
  @State private hasCrease: boolean = false;

  // 页面根容器在全局坐标中的 Y 偏移（单位 vp）。
  // 实际接入时请在容器挂载后按工程方式更新该值。
  private rootGlobalYVp: number = 0;
  private foldStatusCallback?: (status: display.FoldStatus) => void;

  aboutToAppear() {
    this.recalculateCreaseBand();
    this.foldStatusCallback = () => {
      this.recalculateCreaseBand();
    };
    display.on('foldStatusChange', this.foldStatusCallback);
  }

  aboutToDisappear() {
    if (this.foldStatusCallback) {
      display.off('foldStatusChange', this.foldStatusCallback);
    }
  }

  private recalculateCreaseBand(): void {
    const region = display.getCurrentFoldCreaseRegion();
    if (!region || !region.creaseRects || region.creaseRects.length === 0) {
      // 拿不到折痕数据时按窗口中线兜底，并把 hasCrease 置为 false，
      // 供上层在需要时标注“未按真实折痕”。
      this.hasCrease = false;
      this.creaseHeightVp = 0;
      this.splitLineVp = this.rootHeightVp > 0 ? this.rootHeightVp * 0.5 : 0;
      return;
    }

    const rect = region.creaseRects[0];
    const p1 = display.convertGlobalToRelativeCoordinate({ x: rect.left, y: rect.top }, region.displayId);
    const p2 = display.convertGlobalToRelativeCoordinate(
      { x: rect.left + rect.width, y: rect.top + rect.height },
      region.displayId
    );

    // 折痕坐标是 px 且属于窗口坐标系，必须走 UIContext 的 px2vp。
    const uiContext = this.getUIContext();
    const mappedTopVp = uiContext.px2vp(Math.min(p1.position.y, p2.position.y));
    const mappedBottomVp = uiContext.px2vp(Math.max(p1.position.y, p2.position.y));
    const topInRootVp = mappedTopVp - this.rootGlobalYVp;

    const rawHeightVp = Math.max(0, mappedBottomVp - mappedTopVp);
    this.creaseHeightVp = this.clampCreaseThickness(rawHeightVp, this.rootHeightVp);
    this.splitLineVp = topInRootVp + this.creaseHeightVp * 0.5;
    this.hasCrease = true;
  }

  /**
   * 折痕厚度安全钳位：折痕带不应超过屏幕对应维度的 35%。
   * 超限说明几何数据异常，回退到折痕物理短边的估算值 8vp。
   */
  private clampCreaseThickness(creaseHeightVp: number, screenDimensionVp: number): number {
    if (screenDimensionVp <= 0) {
      return creaseHeightVp;
    }
    const maxThickness = screenDimensionVp * CreaseAvoidanceExample.MAX_CREASE_RATIO;
    if (creaseHeightVp > maxThickness) {
      return Math.min(creaseHeightVp, CreaseAvoidanceExample.FALLBACK_CREASE_VP);
    }
    return creaseHeightVp;
  }

  @Builder
  private topArea() {
    Column() {
      Text('Upper Content')
    }
    .width('100%')
    .height('100%')
  }

  @Builder
  private bottomArea() {
    Column() {
      Text('Lower Actions')
    }
    .width('100%')
    .height('100%')
  }

  private upperHeightVp(): number {
    return Math.max(0, this.splitLineVp - this.creaseHeightVp * 0.5);
  }

  private lowerHeightVp(): number {
    return Math.max(0, this.rootHeightVp - this.upperHeightVp() - this.creaseHeightVp);
  }

  build() {
    Column() {
      // build() 内只能写 UI 语法，不能写 const/let 语句（arkts 10905209）。
      // 计算下沉为方法，由 UI 调用。
      if (this.hasCrease && this.splitLineVp > 0 && this.rootHeightVp > 0) {
        // 分区高度按折痕真实边界算；16/40vp 以 padding 形式加在分区内部，
        // 不参与分界线计算——移动分界线会让整个分区错位。
        Column() {
          this.topArea();
        }
        .height(`${this.upperHeightVp()}vp`)
        .padding({ bottom: `${CreaseAvoidanceExample.UPPER_CONTENT_GAP_VP}vp` })

        Row()
          .width('100%')
          .height(`${this.creaseHeightVp}vp`)
          .backgroundColor('#E8E8E8')

        Column() {
          this.bottomArea();
        }
        .height(`${this.lowerHeightVp()}vp`)
        .padding({ top: `${CreaseAvoidanceExample.LOWER_CONTENT_GAP_VP}vp` })
      } else {
        // 无折痕信息时的兜底布局
        Column() {
          this.topArea();
        }
        .layoutWeight(1)

        Column() {
          this.bottomArea();
        }
        .layoutWeight(1)
      }
    }
    .width('100%')
    .height('100%')
    .onAreaChange((_, area) => {
      this.rootHeightVp = Number(area.height);
      this.recalculateCreaseBand();
    })
  }
}
