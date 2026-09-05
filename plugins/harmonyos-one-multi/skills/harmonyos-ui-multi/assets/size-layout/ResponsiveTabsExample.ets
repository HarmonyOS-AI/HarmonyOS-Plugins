/**
 * ResponsiveTabsExample.ets
 *
 * 普通页面的响应式一级导航示例：
 *   - sm / md：底部横向 Tabs；
 *   - lg / xl：左侧纵向 Tabs；
 *   - 使用原生 Tabs 参与布局，不用 Stack + position 浮在内容上方；
 *   - 五个布局属性在两个方向都显式赋值，保证 lg → md → lg 可逆。
 *   - LG 侧边栏的每个页签项根节点必须加 top/bottom margin；实际工程案例见 LAYOUT-07。
 *
 * 使用前提：按 BreakpointEntryRegistration.ets，在 windowStage.loadContent(...) 加载的
 * 入口页 aboutToAppear() 注册 BreakpointSystem；其他页面不要重复注册。
 *
 * 本例选择 xl 继续使用侧边 Tabs。如果产品在 xl 升级为 SideBarContainer，
 * 应在页面结构层单独分支，不能让 md 继承侧边状态。
 */

import { BreakpointState, BreakpointSystem } from './BreakpointSystem';

@ComponentV2
export struct ResponsiveTabsExample {
  /** 持有 @ObservedV2 对象，断点的 @Trace 字段变化后触发本组件重绘。 */
  @Local private bpState: BreakpointState = BreakpointSystem.state;
  @Local private selectedIndex: number = 0;

  /** 底部导航指示条避让高度，由使用方从当前窗口避让区传入，默认不额外抬高。 */
  @Param bottomAvoidHeight: number = 0;

  private useSideTabs(): boolean {
    // 侧栏从 lg 开始；md 必须完整恢复为底部栏。
    return this.bpState.isLg || this.bpState.isXl;
  }

  @Builder
  private tabBarItem(icon: string, label: string, index: number) {
    Column({ space: 4 }) {
      Text(icon)
        .fontSize(24)
        .fontColor(this.selectedIndex === index ? '#0A59F7' : '#666666')
      Text(label)
        .fontSize(12)
        .fontColor(this.selectedIndex === index ? '#0A59F7' : '#666666')
    }
    .width('100%')
    .height(64)
    .justifyContent(FlexAlign.Center)
  }

  build() {
    Tabs({
      barPosition: this.useSideTabs() ? BarPosition.Start : BarPosition.End,
      index: this.selectedIndex
    }) {
      TabContent() {
        Column() {
          Text('首页内容')
        }
        .width('100%')
        .height('100%')
        .justifyContent(FlexAlign.Center)
      }
      .tabBar(this.tabBarItem('⌂', '首页', 0))

      TabContent() {
        Column() {
          Text('分类内容')
        }
        .width('100%')
        .height('100%')
        .justifyContent(FlexAlign.Center)
      }
      .tabBar(this.tabBarItem('▦', '分类', 1))

      TabContent() {
        Column() {
          Text('我的内容')
        }
        .width('100%')
        .height('100%')
        .justifyContent(FlexAlign.Center)
      }
      .tabBar(this.tabBarItem('♙', '我的', 2))
    }
    // 五属性必须一起双向赋值；不能只在 lg 分支设置而依赖 md 的初始值。
    .vertical(this.useSideTabs())
    .barWidth(this.useSideTabs() ? 96 : '100%')
    .barHeight(this.useSideTabs() ? '100%' : 56 + this.bottomAvoidHeight)
    .barMode(this.useSideTabs() ? BarMode.Scrollable : BarMode.Fixed)
    // 普通页面明确不重叠，正文由 Tabs 在侧栏之外布局。
    .barOverlap(false)
    .width('100%')
    .height('100%')
    .onChange((index: number) => {
      this.selectedIndex = index;
    })
  }
}
