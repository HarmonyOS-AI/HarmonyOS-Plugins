import { KeyboardAvoidMode } from '@kit.ArkUI';

/**
 * KeyboardAvoidanceScroll.ets —— 软键盘避让（Scroll 方案，需手写三件套）
 *
 * 能选 List 就选 List，见 KeyboardAvoidanceList.ets。拆两个文件是因为
 * ArkTS 规定一个文件只能有一个 @Entry。
 *
 * 对应 domains/avoid-area.md「键盘避让」。那一节的四条约束在这里逐条落地：
 *
 * 1. setKeyboardAvoidMode() 是**窗口级**设置，不是页面级。改过它的页面必须在
 *    aboutToDisappear 里还原，**还原值从进入时读到的实际值来，不硬编码**
 *    —— 硬编码成 OFFSET 会把别的页面设的模式覆盖掉。
 * 2. RESIZE 只压缩用**百分比或 layoutWeight** 表达高度的组件。固定 vp/px 高度的
 *    组件永远不会被压缩，表现为"设了 RESIZE 但输入框还是被盖住"。
 * 3. List 自带键盘避让；Scroll 要手写三件套（延迟 + scrollEdge + keyboardHeight>0 判断）。
 *    能选 List 就选 List，少写三段代码。
 * 4. 收起键盘用 clearFocus() 而不是 stopEditing()：clearFocus 走的是焦点系统，
 *    对所有输入类组件一致；stopEditing 只作用于单个组件实例。
 *
 * expandSafeArea([SafeAreaType.KEYBOARD]) **只在 OFFSET 模式下生效**，
 * RESIZE 模式下无效 —— 两者不要一起用。
 *
 * 前置：setKeyboardAvoidMode 必须在 windowStage.loadContent() 回调**之后**调用，
 * 在它之前调用不生效（UIContent 还没建立）。本文件在页面 aboutToAppear 里调，
 * 页面已挂载即满足该前提。
 */

// ── 方案 B：Scroll —— 必须手写三件套 ──────────────────────────────────

@Entry
@Component
struct KeyboardAvoidanceScrollPage {
  @State private note: string = '';
  /** 由 avoidAreaChange 写入；三件套的第三件依赖它 > 0 才滚动。 */
  @State private keyboardHeightVp: number = 0;

  private scroller: Scroller = new Scroller();
  private previousAvoidMode: KeyboardAvoidMode = KeyboardAvoidMode.OFFSET;

  aboutToAppear(): void {
    const uiContext = this.getUIContext();
    this.previousAvoidMode = uiContext.getKeyboardAvoidMode();
    uiContext.setKeyboardAvoidMode(KeyboardAvoidMode.RESIZE);
  }

  aboutToDisappear(): void {
    this.getUIContext().setKeyboardAvoidMode(this.previousAvoidMode);
  }

  /**
   * Scroll 方案的三件套：
   *   ① setTimeout 延迟 —— 键盘动画结束前滚动会滚到错误位置
   *   ② scrollEdge(Edge.Bottom) —— 把焦点区滚进可视区
   *   ③ 仅在 keyboardHeightVp > 0 时滚 —— 键盘收起时也滚会把内容顶到底部
   * 三件缺一，表现都是"输入框还是被盖住"或"莫名滚到底"。
   */
  private scrollToFocusedInput(): void {
    if (this.keyboardHeightVp <= 0) {
      return;
    }
    setTimeout(() => {
      this.scroller.scrollEdge(Edge.Bottom);
    }, 100);
  }

  build() {
    Column() {
      Scroll(this.scroller) {
        Column({ space: 12 }) {
          Text('长表单').fontSize(20)
          ForEach(['标题', '摘要', '正文'], (field: string) => {
            TextInput({ placeholder: field })
              .onFocus(() => {
                this.scrollToFocusedInput();
              })
          }, (field: string) => field)
          TextArea({ placeholder: '备注', text: this.note })
            .height(120)
            .onChange((v: string) => {
              this.note = v;
            })
            .onFocus(() => {
              this.scrollToFocusedInput();
            })
        }
        .width('100%')
        .padding(16)
      }
      .width('100%')
      // 同样用 layoutWeight，RESIZE 才压得动
      .layoutWeight(1)
      // 键盘高度由外部（EntryAbility 的 avoidAreaChange，TYPE_KEYBOARD）
      // 写进 AppStorage 后同步到这里；本文件不重复实现避让区监听，
      // 那部分见 CutoutAvoidanceManager.ets 与 domains/avoid-area.md。
      .onAreaChange(() => {
        this.keyboardHeightVp = AppStorage.get<number>('keyboardHeightVp') ?? 0;
      })
    }
    .width('100%')
    .height('100%')
  }
}
