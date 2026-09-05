/**
 * 拆分说明：参考示例 SplitScreenExample.ets 把 UIAbility 与两个 @Entry 页面塞进同一个文件，
 * 而 ArkTS 规定「一个文件只能有一个 @Entry」——原文件无法编译。
 * 收编时按职责拆成三个文件，内容未改。
 */

import { window } from '@kit.ArkUI';

@Entry
@Component
struct SplitScreenDetailPage {

  build() {
    Column() {
      ForEach([1, 2, 3], (index: number) => {
        Image($r('app.media.background'))
          .height(200)
          .aspectRatio(1)
      })
    }
    .height('100%')
    .width('100%')
    .justifyContent(FlexAlign.SpaceBetween)
  }
}
