import { KeyboardAvoidMode } from '@kit.ArkUI';

/**
 * KeyboardAvoidanceList.ets —— 软键盘避让（List 方案，推荐）
 *
 * Scroll 方案见 KeyboardAvoidanceScroll.ets。拆两个文件是因为 ArkTS 规定
 * 一个文件只能有一个 @Entry。
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

// ── 方案 A：List（推荐）—— 内置键盘避让，无需手写任何滚动逻辑 ────────────

@Entry
@Component
struct KeyboardAvoidanceListPage {
  @State private fields: string[] = ['姓名', '手机号', '邮箱', '地址', '备注'];
  @State private values: string[] = ['', '', '', '', ''];

  /** 进入页面时读到的窗口级模式，离开时原样还原。不硬编码还原值。 */
  private previousAvoidMode: KeyboardAvoidMode = KeyboardAvoidMode.OFFSET;

  aboutToAppear(): void {
    const uiContext = this.getUIContext();
    // 先存旧值，再改。这一步是"窗口级设置必须还原"的全部实现。
    this.previousAvoidMode = uiContext.getKeyboardAvoidMode();
    uiContext.setKeyboardAvoidMode(KeyboardAvoidMode.RESIZE);
  }

  aboutToDisappear(): void {
    // 还原成进入时的实际值，而不是某个假定的默认值
    this.getUIContext().setKeyboardAvoidMode(this.previousAvoidMode);
  }

  build() {
    Column() {
      Row() {
        Text('注册').fontSize(20)
        Blank()
        Button('完成')
          .onClick(() => {
            // 收起键盘用 clearFocus，不用 stopEditing
            this.getUIContext().getFocusController().clearFocus();
          })
      }
      .width('100%')
      .height(56)
      .padding({ left: 16, right: 16 })

      // List 自带键盘避让：不需要 avoidAreaChange 监听、不需要读 keyboardHeight、
      // 不需要 setTimeout 延迟滚动。
      List({ space: 12 }) {
        ForEach(this.fields, (field: string, index: number) => {
          ListItem() {
            Column({ space: 4 }) {
              Text(field).fontSize(14)
              TextInput({ placeholder: field, text: this.values[index] })
                .onChange((v: string) => {
                  this.values[index] = v;
                })
            }
            .alignItems(HorizontalAlign.Start)
            .width('100%')
          }
        }, (field: string) => field)
      }
      .width('100%')
      // RESIZE 只压缩百分比 / layoutWeight 表达的高度。
      // 这里用 layoutWeight(1) 而非固定高度，键盘弹起时才会真的被压缩。
      .layoutWeight(1)
      .padding({ left: 16, right: 16 })
    }
    .width('100%')
    .height('100%')
  }
}
