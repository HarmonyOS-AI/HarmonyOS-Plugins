/**
 * BreakpointEntryRegistration.ets
 *
 * BreakpointSystem 的唯一注册入口示例。把本例的生命周期代码合并进
 * windowStage.loadContent('pages/XXX') 实际加载的入口页；不要新增第二个入口页。
 *
 * 全工程所有其他页面只消费 BreakpointSystem.state。若扫描到多个同构的
 * BreakpointManager / BreakpointObserver / windowSizeChange 断点监听类，先迁移消费端，
 * 再删除重复实现，最终只保留 BreakpointSystem.ets 这一份状态事实源。
 */

import { common } from '@kit.AbilityKit';
import { BreakpointSystem } from './BreakpointSystem';

@Entry
@ComponentV2
struct BreakpointEntryRegistration {
  aboutToAppear(): void {
    // 入口页已由 loadContent 创建，此时可从宿主上下文取得当前 WindowStage。
    const uiContext = this.getUIContext();
    const hostContext = uiContext.getHostContext() as common.UIAbilityContext;
    const mainWindow = hostContext.windowStage.getMainWindowSync();
    BreakpointSystem.register(uiContext, mainWindow);
  }

  aboutToDisappear(): void {
    // 只与该入口页的唯一注册成对；普通业务页不得注销全局断点系统。
    BreakpointSystem.unregister();
  }

  build() {
    Column() {
      Text('应用入口内容')
    }
    .width('100%')
    .height('100%')
  }
}
