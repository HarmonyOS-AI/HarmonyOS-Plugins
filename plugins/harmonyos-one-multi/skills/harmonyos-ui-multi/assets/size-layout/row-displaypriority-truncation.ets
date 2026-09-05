/**
 * 案例对照：Row 容器内标签截断 vs displayPriority 按需展示
 *
 * 场景：一组横向排列的标签，宽度不足时预期按优先级隐藏而非截断
 * 根因：缺少 .displayPriority() 导致子组件被截断，容器缺少 .width('100%') 导致约束不生效
 *
 * 下面分别是正确案例（goodcase）和错误案例（badcase）
 */

// ==================== 正确案例（goodcase）====================
// 关键点：完整遍历 tags + 同优先级分组 + Row 设置 .width('100%')
// 不监听或手算容器宽度，不维护 visibleCount，也不通过 slice/filter 预裁剪 tags；
// 子组件的实际测量尺寸和显隐数量全部交给 displayPriority 所在的布局流程。
// 相邻两个标签使用同一优先级：宽度不足时，同组标签同时显隐，不会在组内从尾部逐项隐藏。
// 位置与顺序只有在代码显式给靠后的组分配更低优先级时才相关，并非 displayPriority 的同级规则。

@Entry
@Component
struct RowPriorityGoodCase {
  @State selectedIndex: number = 0
  private tags: string[] = ['推荐', '科技', '财经', '娱乐', '体育', '教育', '健康', '旅游', '美食', '音乐']

  build() {
    Column() {
      Row({ space: 12 }) {
        ForEach(this.tags, (tag: string, index: number) => {
          Text(tag)
            .displayPriority(Math.floor((this.tags.length - 1 - index) / 2) + 1)
            // 关键：值越大越优先显示；相邻两个标签同级，因此同时显示或隐藏
            .fontSize(14)
            .fontColor(this.selectedIndex === index ? '#FFFFFF' : '#333333')
            .backgroundColor(this.selectedIndex === index ? '#007DFF' : '#F1F3F5')
            .borderRadius(16)
            .padding({ left: 16, right: 16, top: 8, bottom: 8 })
            .onClick(() => {
              this.selectedIndex = index
            })
        }, (tag: string, index: number) => `${index}_${tag}`)
      }
      .width('100%') // 关键：容器宽度占满，displayPriority 才能正确触发
      .padding({ left: 16, right: 16 })
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Start)
    .padding({ top: 20 })
  }
}

// ==================== 错误案例（badcase）====================
// 问题：displayPriority 被注释掉，Row 的 .width('100%') 也被注释掉
// 效果：宽度不足时标签被截断，右侧内容消失在屏幕外

// 反例仅作对照，不注册为页面：一个文件只能有一个 @Entry
@Component
struct RowPriorityBadCase {
  @State selectedIndex: number = 0
  private tags: string[] = ['推荐', '科技', '财经', '娱乐', '体育']

  build() {
    Column() {
      Row({ space: 12 }) {
        ForEach(this.tags, (tag: string, index: number) => {
          Text(tag)
            // .displayPriority(Math.floor((this.tags.length - 1 - index) / 2) + 1)
            // 问题：缺少 displayPriority
            .fontSize(14)
            .fontColor(this.selectedIndex === index ? '#FFFFFF' : '#333333')
            .backgroundColor(this.selectedIndex === index ? '#007DFF' : '#F1F3F5')
            .borderRadius(16)
            .padding({ left: 16, right: 16, top: 8, bottom: 8 })
            .onClick(() => {
              this.selectedIndex = index
            })
        }, (tag: string, index: number) => `${index}_${tag}`)
      }
      // .width('100%') // 问题：缺少容器宽度约束
      .padding({ left: 16, right: 16 })
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Start)
    .padding({ top: 20 })
  }
}
