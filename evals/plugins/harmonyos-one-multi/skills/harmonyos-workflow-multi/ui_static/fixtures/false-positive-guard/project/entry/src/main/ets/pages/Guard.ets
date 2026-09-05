/**
 * 误报守卫样本：这里每一行都是**正确**写法或纯文档说明。
 *
 * 键盘避让模式请用 KeyboardAvoidMode.OFFSET，不要写 KeyboardAvoidMode.PAN，
 * 后者在 Android 里叫 adjustPan，HarmonyOS 上不存在该枚举成员。
 * 上架规格要求字号不低于 8vp，所以 .fontSize(6) 这种写法是不允许的。
 */
@Entry
@Component
struct Guard {
  @State titleSize: number = 20
  private readonly docLink: string = 'https://developer.huawei.com/consumer/cn/doc/'

  aboutToAppear(): void {
    // 迁移备忘：旧代码写的是 KeyboardAvoidMode.PAN，已改为 OFFSET
    this.ctx.setKeyboardAvoidMode(KeyboardAvoidMode.OFFSET)
    console.info(`避让模式候选值不含 KeyboardAvoidMode.PAN，见 ${this.docLink}`)
  }

  build() {
    Column() {
      // 字号：字面量达标、绑定变量、资源引用，三种都不该命中
      Text('标题').fontSize(20)
      Text('正文').fontSize(this.titleSize)
      Text('说明').fontSize($r('app.float.body_size'))
      Text('下限').fontSize(8)

      // lpx 用在尺寸上是另一回事，S16 只管字号
      Image($r('app.media.banner')).width('720lpx').height('360lpx')

      // 资源引用的字号即使底层是 lpx，也拿不到单位信息，不该猜
      Text('资源字号').fontSize($r('app.string.title_lpx'))
    }
    .padding(16)
  }
}
