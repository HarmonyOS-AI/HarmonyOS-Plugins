import { BreakpointSystem, BreakpointState, VerticalBreakpointEnum } from './BreakpointSystem';

/**
 * SplitNavTwoColumn.ets —— 双栏导航（Navigation.Auto）
 *
 * 三栏版本见 SplitNavThreeColumn.ets。拆两个文件是因为 ArkTS 规定
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

// ── 双栏：Navigation.Auto，零断点代码 ──────────────────────────────────

/**
 * 路由参数用类而不是裸 string。
 * navDestination 的 builder 第二参数类型是 object，`param as string` 编译不过
 * （object 与 string 不重叠）；传类实例才能安全向下转型。
 */
class NavItemParam {
  label: string;

  constructor(label: string) {
    this.label = label;
  }
}

@Entry
@Component
struct TwoColumnNavigationPage {
  private pathStack: NavPathStack = new NavPathStack();
  /** 双栏展开时右侧要落地的默认页面；Stack 模式下不推。 */
  private static readonly DETAIL_PAGE: string = 'splitNavDetail';

  @Builder
  private detailDestination(name: string, param: object) {
    NavDestination() {
      Column() {
        Text(`Detail: ${(param as NavItemParam).label}`)
      }
      .width('100%')
      .height('100%')
    }
    .title(name)
  }

  @Builder
  private listPane() {
    List() {
      ForEach(['A', 'B', 'C'], (item: string) => {
        ListItem() {
          Text(item).padding(16)
        }
        .onClick(() => {
          this.pathStack.pushPathByName(TwoColumnNavigationPage.DETAIL_PAGE, new NavItemParam(item));
        })
      }, (item: string) => item)
    }
    .width('100%')
    .layoutWeight(1)
  }

  build() {
    Navigation(this.pathStack) {
      this.listPane();
    }
    .title('Two Column')
    // Auto：系统按 600vp 自动切换。不需要 BreakpointSystem，也不需要 windowSizeChange。
    .mode(NavigationMode.Auto)
    // navBarWidth 不得超过窗口宽的一半，超了框架会降级成单栏
    .navBarWidth('50%')
    .navDestination(this.detailDestination)
    .onNavigationModeChange((mode: NavigationMode) => {
      if (mode === NavigationMode.Split) {
        // 双栏下右侧默认为空，必须推一个默认路由填上
        if (this.pathStack.size() === 0) {
          this.pathStack.pushPathByName(TwoColumnNavigationPage.DETAIL_PAGE, new NavItemParam('A'));
        }
      } else {
        // 切回单栏时清栈，否则用户停在详情页却看不到列表
        this.pathStack.clear();
      }
    })
  }
}
