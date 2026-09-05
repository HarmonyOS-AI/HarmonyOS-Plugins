@Component struct Good {
  aboutToAppear() {
    this.win.on('avoidAreaChange', (opts) => { this.top = opts.area.topRect.height })
    display.on('foldStatusChange', (s) => { this.fold = s })
  }
  aboutToDisappear() {
    this.win.off('avoidAreaChange', this.areaCb)
    display.off('foldStatusChange', this.foldCb)
  }
  build() {
    GridRow({ breakpoints: { value: ['320vp','600vp','840vp','1440vp'],
                             reference: BreakpointsReference.WindowSize } }) {
      GridCol({ span: { sm: 12, lg: 8 }, offset: { lg: 2 } }) {
        Text('ok').fontSize(16)
      }
    }
  }
}
