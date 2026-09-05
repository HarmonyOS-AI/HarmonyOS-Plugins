@Component
struct ArticleDetail {
  build() {
    NavDestination() {
      Text('article detail, reached via NavPathStack.pushPath, no @Entry at all')
    }
  }
}
