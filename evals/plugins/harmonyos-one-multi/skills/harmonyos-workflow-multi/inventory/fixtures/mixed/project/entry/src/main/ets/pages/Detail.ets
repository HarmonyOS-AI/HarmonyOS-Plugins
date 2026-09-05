@Entry @Component struct Detail {
  build() {
    NavDestination() {
      Text('detail, pushed via NavPathStack, not in main_pages.json')
    }
  }
}
