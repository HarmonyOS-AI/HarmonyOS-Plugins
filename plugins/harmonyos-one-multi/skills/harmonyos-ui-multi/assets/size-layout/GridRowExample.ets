/**
 * GridRowExample.ets
 * GridRow 响应式栅格布局示例
 */

// 参考示例这里 import 了 BreakpointConstants（把 320/600/840/1440 写死成常量）。
// 那个文件按收编裁决未采纳——阈值硬编码违反官方"断点可被产品化调整"的说明。
// 断点一律从 BreakpointSystem 读。
import { BreakpointSystem, BreakpointTypeEnum } from './BreakpointSystem';

@Entry
@ComponentV2
struct GridRowExample {
  @Local currentBreakpoint: BreakpointTypeEnum = BreakpointSystem.state.value;

  build() {
    Column() {
      // 标题
      Text('响应式栅格布局')
        .fontSize(24)
        .fontWeight(FontWeight.Bold)
        .margin({ bottom: 16 })

      // 基础栅格布局
      GridRow({
        columns: {
          sm: 4,
          md: 8,
          lg: 12
        },
        gutter: {
          x: 16,
          y: 16
        }
      }) {
        // 卡片1 - 响应式列宽
        GridCol({
          span: {
            sm: 4,  // sm: 占满4列
            md: 4,  // md: 占4列(一半)
            lg: 3   // lg: 占3列(1/4)
          }
        }) {
          this.CardComponent('卡片1', '#FF4D4D')
        }

        // 卡片2
        GridCol({
          span: {
            sm: 4,
            md: 4,
            lg: 3
          }
        }) {
          this.CardComponent('卡片2', '#FF9500')
        }

        // 卡片3
        GridCol({
          span: {
            sm: 4,
            md: 4,
            lg: 3
          }
        }) {
          this.CardComponent('卡片3', '#34C759')
        }

        // 卡片4 - 大屏独占一半宽度
        GridCol({
          span: {
            sm: 4,
            md: 8,  // md: 占满8列
            lg: 6   // lg: 占6列(一半)
          }
        }) {
          this.CardComponent('卡片4 (大屏宽)', '#007AFF')
        }

        // 卡片5 - 使用偏移
        GridCol({
          span: {
            sm: 4,
            md: 4,
            lg: 4
          },
          offset: {
            sm: 0,
            md: 0,
            lg: 2  // lg: 向右偏移2列
          }
        }) {
          this.CardComponent('卡片5 (居中)', '#5856D6')
        }
      }
      .width('100%')
      .padding(16)

      // 当前断点显示
      Text(`当前断点: ${this.currentBreakpoint}`)
        .fontSize(14)
        .fontColor('#999')
        .margin({ top: 16 })
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F5F5F5')
  }

  @Builder
  CardComponent(title: string, color: string) {
    Column() {
      Text(title)
        .fontSize(18)
        .fontWeight(FontWeight.Medium)
        .fontColor(Color.White)

      Text('响应式卡片内容')
        .fontSize(14)
        .fontColor(Color.White)
        .opacity(0.8)
        .margin({ top: 8 })
    }
    .width('100%')
    .height(120)
    .backgroundColor(color)
    .borderRadius(12)
    .justifyContent(FlexAlign.Center)
    .padding(16)
  }
}
