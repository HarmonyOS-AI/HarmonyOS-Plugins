@Entry @Component struct Index {
  build() {
    GridRow({ breakpoints: { value: ['320vp', '600vp', '840vp'],
                             reference: BreakpointsReference.ComponentSize } }) {
      GridCol({ span: { sm: 4 } }) { Text('hi') }
    }
    .onBreakpointChange((bp: string) => { console.log(bp) })
  }
  isWide(): boolean { return px2vp(this.winWidth) >= 600 }
}
