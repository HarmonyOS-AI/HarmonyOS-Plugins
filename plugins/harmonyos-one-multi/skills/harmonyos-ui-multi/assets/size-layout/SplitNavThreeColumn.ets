import { BreakpointSystem, BreakpointState, VerticalBreakpointEnum } from './BreakpointSystem';

/**
 * SplitNavThreeColumn.ets —— 三栏导航（SideBarContainer + Navigation）
 *
 * 双栏版本见 SplitNavTwoColumn.ets。拆两个文件是因为 ArkTS 规定
 * 一个文件只能有一个 @Entry。
 *
 * 对应 domains/size-layout.md「分栏布局要点」。那一节的六条约束在这里逐条落地：
 *
 * 1. 优先 NavigationMode.Auto —— 系统在 ≥600vp 自动 Split、<600vp 回退 Stack，
 *    不需要自己写断点监听。双栏示例因此一行断点代码都没有。
 * 2. onNavigationModeChange：切到 Split 时推默认路由，切回 Stack 时清栈。
 *    不做这件事的表现是宽屏右侧内容区一片空白。
 * 3. navBarWidth 不超过窗口宽的一半，否则框架降级为单栏。
 * 4. 三栏的嵌套顺序是死规矩：SideBarContainer 在外、Navigation 在内。
 *    反过来 Navigation 会把整个 SideBarContainer 当作 navBar 内容。
 * 5. SideBarContainer 必须恰好两个直接子节点（侧边栏在前、主内容在后）。
 * 6. 侧边栏的开启条件同时看横纵断点 —— 用 isLg 而非 isWide：
 *    折叠屏展开态是 md，放得下双列列表但放不下侧边栏。
 *
 * 断点一律走 BreakpointSystem（本 skill 唯一标准实现），不自造。
 * 注意 BreakpointTypeEnum 是**字符串枚举**，不能用 >= 比大小，
 * 判档一律用 BreakpointState 的 isSm/isMd/isLg/isXl/isWide/isSquare 取值器。
 *
 * 前置：按 BreakpointEntryRegistration.ets 在 loadContent 加载的入口页
 * aboutToAppear() 全应用注册一次；其他页面只消费状态。
 */

// ── 三栏：SideBarContainer 在外、Navigation 在内 ────────────────────────

/**
 * 路由参数用类而不是裸 string。
 * navDestination 的 builder 第二参数类型是 object，`param as string` 编译不过
 * （object 与 string 不重叠）；传类实例才能安全向下转型。
 */
class NavContentParam {
  label: string;

  constructor(label: string) {
    this.label = label;
  }
}

// 必须是 @ComponentV2：BreakpointSystem.state 是 @ObservedV2 类，
// V1 的 @State 不允许持有它（10905348）。
@Entry
@ComponentV2
struct ThreeColumnNavigationPage {
  private pathStack: NavPathStack = new NavPathStack();
  private static readonly CONTENT_PAGE: string = 'splitNavContent';

  /**
   * 持有 @ObservedV2 单例本身，**不拷贝它的值**，且不加任何状态装饰器。
   *
   * - 不能加 @State：V1 装饰器不允许持有 @ObservedV2 类（10905348）
   * - 不要写成 `@Local x = BreakpointSystem.state.value`：那是拷了一份快照，
   *   断点变化时不会重渲染
   * - 也不要用 `get` 计算属性派生断点状态（domains/size-layout.md 前置条件 3）
   *
   * 响应式来自 value / vertical 上的 @Trace —— 在 build() 的求值链上读到它们
   * 就建立了依赖，这个字段只是通往它们的引用。
   */
  private bp: BreakpointState = BreakpointSystem.state;

  // 这里**故意不调** BreakpointSystem.register()：按 BreakpointSystem.ets 的使用纪律，
  // register() 全应用只调一次、且必须在 windowStage.loadContent() 加载的入口页
  // aboutToAppear() 中。本页是被路由进来的业务页，不得重复注册；在本页
  // aboutToDisappear() 里 unregister 还会把栈底页的断点一起停掉。

  /**
   * 侧边栏开启条件：宽度到 lg，且不是纵向窗口。
   *
   * 用 isLg 而不是 isWide —— 折叠屏展开态是 md，宽度放不下侧边栏。
   * 再排除纵向窗口（vertical === LG）：平板竖屏宽度可能到 md/lg 但高度不足，
   * 三栏会挤成一团。这就是「分栏条件同时看横纵断点」。
   */
  private shouldShowSideBar(): boolean {
    return (this.bp.isLg || this.bp.isXl) && this.bp.vertical !== VerticalBreakpointEnum.LG;
  }

  /** 单侧边栏不超过窗口宽度的 40%（QC-08）。三栏时取 20%，给中间栏留空间。 */
  private sideBarWidthPercent(): string {
    return this.bp.isXl ? '15%' : '20%';
  }

  @Builder
  private contentDestination(name: string, param: object) {
    NavDestination() {
      Column() {
        Text(`Content: ${(param as NavContentParam).label}`)
      }
      .width('100%')
      .height('100%')
    }
    .title(name)
  }

  @Builder
  private sideBarPane() {
    Column() {
      Text('Side Menu').padding(16)
    }
    .width('100%')
    .height('100%')
  }

  @Builder
  private middleList() {
    List() {
      ForEach(['1', '2', '3'], (item: string) => {
        ListItem() {
          Text(`Item ${item}`).padding(16)
        }
        .onClick(() => {
          this.pathStack.pushPathByName(ThreeColumnNavigationPage.CONTENT_PAGE, new NavContentParam(item));
        })
      }, (item: string) => item)
    }
    // 分栏容器里套可滚动组件用 layoutWeight(1)，不是 height('100%')
    .width('100%')
    .layoutWeight(1)
  }

  build() {
    // 嵌套顺序：SideBarContainer 在外，Navigation 在它的第二个子节点里。
    // 写反的表现是宽屏下内容区一片空白（root-causes size-15）。
    SideBarContainer(
      this.bp.isWide ? SideBarContainerType.Embed : SideBarContainerType.Overlay
    ) {
      // 子节点 1：侧边栏
      this.sideBarPane();

      // 子节点 2：主内容。SideBarContainer 必须**恰好两个**直接子节点，
      // 多一个少一个都会运行时报错——所以这里用一个 Navigation 收口。
      Navigation(this.pathStack) {
        this.middleList();
      }
      .title('Middle')
      .mode(NavigationMode.Auto)
      .navBarWidth('40%')
      .navDestination(this.contentDestination)
      .onNavigationModeChange((mode: NavigationMode) => {
        if (mode === NavigationMode.Split) {
          if (this.pathStack.size() === 0) {
            this.pathStack.pushPathByName(ThreeColumnNavigationPage.CONTENT_PAGE, new NavContentParam('1'));
          }
        } else {
          this.pathStack.clear();
        }
      })
    }
    .showSideBar(this.shouldShowSideBar())
    .sideBarWidth(this.sideBarWidthPercent())
    .width('100%')
    .height('100%')
  }
}
