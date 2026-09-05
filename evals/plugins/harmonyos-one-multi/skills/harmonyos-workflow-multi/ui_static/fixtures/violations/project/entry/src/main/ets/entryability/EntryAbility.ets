export default class EntryAbility extends UIAbility {
  onWindowStageCreate(windowStage: window.WindowStage): void {
    BreakpointSystem.register(this.context.getUIContext())
    windowStage.loadContent('pages/Index')
  }
}
