/**
 * 拆分说明：参考示例 SplitScreenExample.ets 把 UIAbility 与两个 @Entry 页面塞进同一个文件，
 * 而 ArkTS 规定「一个文件只能有一个 @Entry」——原文件无法编译。
 * 收编时按职责拆成三个文件，内容未改。
 */

import { window } from '@kit.ArkUI';

@Entry
@Component
struct SplitScreenMainPage {
  @StorageLink('WidthBreakpoint') currentWidthBreakpoint: WidthBreakpoint = WidthBreakpoint.WIDTH_SM;
  @StorageLink('HeightBreakpoint') currentHeightBreakpoint: HeightBreakpoint = HeightBreakpoint.HEIGHT_SM;

  build() {
    Column() {
      ForEach([1, 2, 3], (index: number) => {
        Image($r('app.media.background'))
          .height(this.currentWidthBreakpoint === WidthBreakpoint.WIDTH_SM  &&
            (this.currentHeightBreakpoint === HeightBreakpoint.HEIGHT_SM  ||
              this.currentHeightBreakpoint === HeightBreakpoint.HEIGHT_MD) ? 50 : 200)
          .aspectRatio(1)
      })
    }
    .height('100%')
    .width('100%')
    .justifyContent(FlexAlign.SpaceBetween)
  }
}

// ==================== 错误案例（badcase）====================
// 问题：图片设置了固定大小
// 效果：小窗下图片维持原大小，导致显示不全被截断
