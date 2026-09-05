/**
 * GridCol span/offset 原语示例，不是整页适配模板。
 * 仅用于需要控制阅读行长或表单操作宽度的局部内容区；不要包页面根节点，
 * 也不要据此创建并批量套用全工程公共限宽组件。
 * 例外：决定对整个可滚动内容区收窄居中时，GridRow/GridCol 必须包住滚动容器本身
 * （GridRow > GridCol > Scroll），不要把 GridRow 放进 Scroll 内部——那只能收窄内容，
 * 滚动容器仍全宽贴边。
 * 无论哪种用法，标题栏（标题 + 返回箭头）都不进限宽层：收窄的是核心内容区，
 * 标题栏保持全宽原位；标题跟着居中缩进＝整页被收窄，看起来就像屏幕变小。
 */
@Entry
@Component
struct GridColOffset {
  build() {
    Column() {
      GridRow({ columns: 12 }) {
        // 第一个元素: 占4列,无偏移
        GridCol({ span: 4, offset: 0 }) {
          Text('元素1').backgroundColor(Color.Pink).width('100%')
        }

        // 第二个元素: 占4列,偏移2列
        GridCol({ span: 4, offset: 2 }) {
          Text('元素2').backgroundColor('#87CEEB').width('100%')
        }

        // 第三个元素: 占4列,无偏移
        GridCol({ span: 4, offset: 0 }) {
          Text('元素3').backgroundColor(Color.Orange).width('100%')
        }
      }
      .width('100%')
      .height(100)

      // 响应式offset
      GridRow({ columns: 12 }) {
        GridCol({
          span: { sm: 6, md: 4, lg: 3 },
          offset: { sm: 0, md: 2, lg: 1 }  // 不同断点下的偏移
        }) {
          Text('响应式偏移').backgroundColor(Color.Green).width('100%')
        }
      }
      .width('100%')
      .height(50)
    }
  }
}
