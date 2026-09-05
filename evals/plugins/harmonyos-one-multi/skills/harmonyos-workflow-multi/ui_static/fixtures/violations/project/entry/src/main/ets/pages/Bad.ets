@Component struct Bad {
  aboutToAppear() {
    this.ctx.setKeyboardAvoidMode(KeyboardAvoidMode.PAN)
    this.win.on('avoidAreaChange', (opts) => {
      const area = this.win.getWindowAvoidArea(window.AvoidAreaType.TYPE_SYSTEM)
      this.top = area.topRect.height
    })
    display.on('foldStatusChange', (s) => { this.fold = s })
  }
  aboutToDisappear() {
    display.off('foldStatusChange')
  }
  build() {
    Column() {
      Text('x').layoutWeight(1)
        .width('100%')
      List() { }.lanes(2).divider({ strokeWidth: 1 })
      Column() { }.constraintSize({ maxWidth: this.isLg ? 840 : '100%' })
      Text('角标').fontSize(6)
      Text('标题').fontSize('32lpx')
      if (this.isHalfFold) {
        FolderStack({ upperItems: ['a'] }) { }
      }
    }
  }
}
