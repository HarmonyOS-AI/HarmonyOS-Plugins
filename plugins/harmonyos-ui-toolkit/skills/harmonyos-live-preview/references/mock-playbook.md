# 预览 mock 实战手册

页面起不来时怎么最快看到画面。所有配方都在真实多模块工程（`entry` + `commons/*` HAR + `features/*`）
上实测过，附了验证命令；没实测通过的写明了"不支持"。

机制背景（引擎白名单、`@Preview` 装饰器、官方文档出处）见
[preview-coverage.md](preview-coverage.md)；本文只讲**怎么做**。

## 先分类，再选招

别一上来就写 mock。先拿到证据，判断属于哪一类——不同类别的解法完全不同，用错了白费功夫。

```bash
DRIVE="node ${CLAUDE_PLUGIN_ROOT}/skills/harmonyos-live-preview/scripts/drive.mjs"
$DRIVE wait --for-rebuild     # exit 1 = 构建失败，读报错行
$DRIVE tree --depth 6         # 只有 `root  rect=(?)  no-rect` = 构建成功但运行时炸了
```

运行时炸了就开引擎日志重跑，**报错原文才是分类依据**：

```bash
PREVIEW_ENGINE_LOG=1 node .../preview.mjs --project . --port 8088 > /tmp/pv.log 2>&1 &
grep -iE "Throw error|TypeError|Cannot read|load hsp failed|LoadPage" /tmp/pv.log \
  | grep -viE "RSRenderNodeDrawable|TraceTool|create error manager" | head
```

| 症状 | 类别 | 选招 |
|---|---|---|
| 组件树只有一个空 `Navigation`；日志有 `Builder function is empty` / `navigation route is invalid` | **F 具名路由解析不出 Builder**（**最高频**） | [§绕开具名路由](#绕开具名路由)——harness 直接调目标页的 Builder |
| `Cannot read property XXX of undefined`，XXX 是 `windowStage`/`getMainWindowSync`/`abilityInfo` 等 | **A 页面直接摸 UIAbility/窗口** | [§防御式改写](#防御式改写)（改动最小）；初始化逻辑写在 Ability 生命周期里的用 `--ability-mode` |
| 页面渲染出骨架但内容空/一直"加载中" | **B 数据层拿不到数据** | [§模块 mock](#模块-mock)（本地文件 / 依赖模块 / 系统模块） |
| 某个组件位置空白，其余正常 | **C 白名单外组件** | 无解，[§harness](#harness-包装页) 里把它替换成占位 |
| `@Link`/`@Consume`/`@ObjectLink` 相关报错 | **D 缺父级提供者** | [§harness](#harness-包装页)（官方也推荐这个，不推荐属性级 mock） |
| 构建就失败 | **E 构建期问题** | 按 ArkTS 报错行修，跟预览无关 |

多个真实模板工程的实测分布里：**F 类最高频**，且常与 A 类叠加——现代模板的 entry 页面
基本都是"空 `Navigation` 壳 + 具名路由跳真正的首页"，这个架构在 Previewer 下必然白屏。E 类里有
相当一部分是模板仓库自身的 bug（import 大小写、HSP 资源 ID 冲突、第三方 SDK 类型不匹配），跟预览
无关，先修了才谈得上预览。

## 绕开具名路由

**症状**：构建成功、`hasFrame:true`，但组件树只有一个空 `Navigation`，截图纯白。开
`PREVIEW_ENGINE_LOG=1` 能看到（`AceNavigation` tag）：

```
[js_navigation_stack.cpp] Builder function is empty
[js_navigation_stack.cpp] navigation route is invalid
[js_navigation_stack.cpp] can't find target destination by index, create empty node
```

**根因**：页面走的是 `module.json5` 的 `"routerMap": "$profile:router_map"` + `NavPathStack`
`pushPathByName('XXX')` 这种**声明式具名路由**。它要由系统按 bundle 解析各 HAP/HSP 模块的
`router_map.json` 才能拿到 builder，Previewer 沙箱没有真实 bundle 安装上下文，于是按名字查不到
builder，直接建空节点。**`--ability-mode` 救不了**（实测：异常日志干净了，树还是空的——只看"报错
消失了没"会误判）。

**解法**：harness 直接调目标页的 Builder，绕开整个路由查找。目标页和它的 builder 函数名
`router_map.json` 里就写着，直接照抄：

```json5
// entry/src/main/resources/base/profile/router_map.json
{ "routerMap": [
  { "name": "Main", "pageSourceFile": "src/main/ets/pages/Main.ets", "buildFunction": "MainBuilder" },
] }
```

```ts
// entry/src/main/ets/pages/PreviewHarness.ets —— 11 行，实测一轮编译通过
import { MainBuilder } from './Main';

@Entry
@ComponentV2
struct PreviewHarness {
  build() {
    Column() {
      MainBuilder()
    }.width('100%').height('100%')
  }
}
```

注册进 `main_pages.json` 后 `--page pages/PreviewHarness` 预览。实测效果：从"空 Navigation 白屏"
变成完整首页（`Tabs` → 各 `TabContent` → 真实业务组件 → 底部导航），不用动任何业务代码。

`@Entry` 的 `build()` **根节点必须是容器组件**，所以哪怕只挂一个自定义组件也要用 `Column()` 包一层，
否则报 `10905210 ... the 'build' method can have only one root node, which must be a container component`。

### 二级/三级页面

同一招直接适用于详情页、设置页这些深层页面——实测多个深层页面均能渲染出来，**通常一轮编译就过**；
一个工程只要一个 harness 文件（十几行）+ `main_pages.json` 一行，同工程内换页面只改 harness 的
import，不再有额外成本。四件事要注意：

**1. 路由表往往不在 entry，文件名还有两种拼写。** entry 自己的表常常是空的或只有开屏页，真正的
二三级页在各 `features/*`、`components/*` HAR 包**各自的** profile 里；文件名 `route_map.json`
（单数）和 `router_map.json`（复数）都有，只按一种去 `find` 会误判成"这工程没有具名路由"：

```bash
grep -rn "routerMap" --include="module.json5" . | grep -v oh_modules      # 先看各模块声明了哪个 profile
find . \( -name "route_map.json" -o -name "router_map.json" \) -not -path "*/oh_modules/*"
```

还有一类工程**没有声明式路由表**，用手搓的 `RouterTable.ets`（`Map<RouterMap, WrappedBuilder>`）。
这种直接读那个文件找 Builder 从哪 import。

**2. 跨模块 import 走包名。** 被预览模块的 `oh_modules/<包名>` 是指向该模块目录的 symlink，所以按
"包名 + 包内相对路径"导入最省心，不用数点号：

```ts
import { AlmanacViewBuilder } from 'almanac/src/main/ets/pages/AlmanacView';
```

如果目标 builder **没有从模块的 `Index.ets` 导出**（很常见——`route_map.json` 里注册了但对外不可见），
要么用上面这种深路径导入，要么在那个模块的 `Index.ets` 补一行 `export`。

**3. "参数"几乎从来不是函数参数，是全局状态。** 实测的深层页面里，`XxxBuilder()` **清一色零参**，
真正的数据通路是 `RouterModule.getNavParam()` / 模块级 `NavPathStack` 单例 / `AppStorageV2` /
`PersistenceV2` 这类全局 store，页面在 `aboutToAppear` 里去读。所以 harness 要做的是**渲染前先把
store 灌好**，而不是造字面量传给 builder。**必须先读一遍目标页的 `aboutToAppear()`，否则猜不到数据
从哪来。**

路由参数型（`NavPathStack` 单例 / `RouterModule`）——伪造一次导航：

```ts
@Entry
@ComponentV2
struct PreviewHarness {
  aboutToAppear(): void {
    const stack: NavPathStack = new NavPathStack();
    const mockParams: FundLoanParams = { type: LoanType.Commercial, rate: 4.2, year: 30, cost: 100 };
    stack.pushPathByName(RouterMap.RESULT, mockParams);
    setPathStack(stack);                 // 页面模块导出的 setter
  }
  build() {
    Column() { CalculationResultBuilder() }.width('100%').height('100%')
  }
}
```

不灌就在渲染前崩（单例是 `undefined`）。`RouterModule` 那套则是 `RouterModule.push({ url, param })`
预先写进去，页面里的 `getNavParam({url})` 就能反查到。

全局 store 型（`AppStorageV2` / `PersistenceV2`）——connect 同一个 key 直接写：

```ts
aboutToAppear(): void {
  const user: UserInfoModel = PersistenceV2.connect(UserInfoModel, () => new UserInfoModel())!;
  user.nickName = '张三';
  user.personalDesc = '预览用假数据';
}
```

页面读的是同一个单例，不用改页面一行代码。这两类都**不需要 hamock**——实测的深层页面里没有一个
真的用上模块 mock，因为模板的详情页数据要么硬编码、要么本地算、要么就在这类全局 store 里。

**查参数链路是深层页面最大的时间开销**：写 harness 和编译只占小头，大头是读若干源文件
搞清"数据从哪来、Builder 有没有对外导出"。

**4. 形参类型是 `Object` 时，字面量会被拦。** `pushPathByName(name, param)` 的第二个形参类型是宽泛的
`Object`，直接塞字面量报 `10605038 arkts-no-untyped-obj-literals`。先赋给一个具名 interface/class 的
变量再传（上面代码里的 `mockParams`）。

判断能不能用 `{...}` 字面量，看的是**目标类型有没有自定义构造函数 / `readonly` 字段 / 方法**，
跟它是 `interface` 还是 `class` 无关——只有属性初始化器的 `class` 照样能用字面量初始化。

反过来，**属性全是箭头函数的"方法集合"对象，哪怕显式标注了 interface 类型也照样被拦**（mock 一个
API 单例时最容易撞上）。改成 `class` 实例即可——通常真实源码里那个 `XxxApis` 单例本来就是 class，
照抄它的写法最省事。

**5. 页面在 `NavDestination.onReady()` 里读参数时，`Column()` 包法不够。** `onReady` 只有在
NavDestination 由**真正的 `Navigation`** 管理时才触发；直接挂在 `Column` 下它压根不跑，表现是页面
结构渲染出来了、数据却始终是空的（一直转圈），比白屏更迷惑人。这时 harness 要自己搭一个最小
`Navigation`——注意 `.navDestination()` 挂的是**你自己写的 `@Builder`**，纯函数回调，不经过系统解析
`route_map.json`，所以不会踩上面的具名路由问题：

```ts
@Entry
@ComponentV2
struct PreviewHarness {
  pageStack: NavPathStack = new NavPathStack();

  @Builder
  pageMap(name: string) {
    if (name === 'ImagePreview') { ImagePreviewBuilder() }
  }

  aboutToAppear(): void {
    const param: ImagePreviewParam = { imageList: ['data:image/png;base64,…'], index: 0 };
    this.pageStack.pushPathByName('ImagePreview', param);
  }

  build() {
    Navigation(this.pageStack) {}
      .navDestination(this.pageMap)
      .hideTitleBar(true)
  }
}
```

判断用哪种包法：目标页读参数用 `aboutToAppear` → `Column()` 就够；用 `onReady(ctx => ctx.pathInfo.param)`
→ 必须上面这种 `Navigation` 版。

## 防御式改写

A 类的根因是固定的：**页面模式下不跑 UIAbility，`getHostContext()` 拿到的 context 上没有
`windowStage`**。成员初始化阶段就抛异常，整页 build 不出来——`@MockSetup` 也救不了（它在
`aboutToAppear` 前跑，而成员初始化更早）。

实测：一个三 Tab 首页（`Navigation` + `Tabs` + 三个 feature 模块的 builder）从白屏到完整渲染，
只改了 3 行：

```ts
// 改前：预览必炸
private windowStage: window.WindowStage = this.context.windowStage;
private windowClass: window.Window = this.windowStage.getMainWindowSync();
// …
this.windowClass.setWindowSystemBarProperties({ statusBarContentColor: '#000000' })

// 改后：预览正常，真机行为不变
private windowStage: window.WindowStage | undefined = this.context?.windowStage;
private windowClass: window.Window | undefined = this.windowStage?.getMainWindowSync();
// …
this.windowClass?.setWindowSystemBarProperties({ statusBarContentColor: '#000000' })
```

**可推广的写法**：凡是 `context` / `windowStage` / `windowClass` / `AbilityContext` 上取值并链式
调用的，一律声明成 `| undefined` + `?.`。真机上这些值都在，可选链不改变行为；预览里则从"抛异常整页
白屏"降级成"这一处不生效"。这是唯一能同时服务预览和生产的改法，优先于 harness。
业务代码常见的变体还有 `AppStorage.get('windowStage') as window.WindowStage` 后直接 `.on(...)`
——同样是取出 `undefined` 就调方法，同样用 `?.` 兜住。

**另一种形态：初始化逻辑被放在 Ability 生命周期里。** 例如路由表注册
`RouterTable.routerInit()` 只在 `EntryAbility.onCreate` 调用，页面模式压根不跑那段代码，于是
`getBuilder(name)` 返回 `undefined`、`.builder()` 抛异常，页面渲染半路中断。这类**加
`--ability-mode` 就好**，0 文件改动：

```bash
node .../preview.mjs --project . --ability-mode
```

判断依据：报错发生在"某个注册表/单例取不到东西"，而不是"context 本身是 undefined"。

**`--ability-mode` 是把双刃剑，别当万能先手**，实测两种反效果：

- 治标不治本：让异常日志变干净，却治不了 F 类的空路由。**加完必须再看一次 `tree`**，只看日志会
  误判成已修好。
- 反而更糟：Ability 自己的 `onCreate` 也会撞上预览器没实现的 AbilityKit 常量（实测
  `AbilityConstant.ContinueState` 是 `undefined`，`ContinueState.INACTIVE` 直接抛，业务代码没
  try/catch 就把整个 ability 生命周期卡死在 `loadContent` 之前，帧数归零——比页面模式还差）。

## 模块 mock

官方 Hamock 机制，**本 skill 已经打通**（DevEco 才写的 `.preview/config/buildConfig.json` 由
`preview.mjs` 每次构建后自动补齐；缺它时症状是 `load hsp failed, hsp name:<module>` + 白屏）。

### 前置

被预览模块（通常是 `entry`）的 `oh-package.json5`：

```json5
"devDependencies": { "@ohos/hamock": "1.0.0" }
```

然后 `ohpm install --all`。启动预览时日志出现 `mock: wired src/mock/mock-config.json5 for module
"entry"` 就说明接上了。

### 铁律：mock 只写在被预览的模块里

`PreviewArkTS` **只处理被预览模块的 `src/mock/mock-config.json5`**。写在 `commons/*`、`features/*`
这些依赖模块里的 mock 配置会被**完全忽略**（实测：子模块 mock 配置不产生任何产物，页面照旧显示原值）。
要替换依赖模块的实现，也得在 `entry/src/mock/` 下写，用包名做 key（见下）。

### 三种 key 写法

`entry/src/mock/mock-config.json5`：

```json5
{
  // 1) 依赖模块（HAR/HSP）——key 是 oh-package.json5 里的包名
  "commonlib": { "source": "src/mock/CommonLib.mock.ets" },
  // 2) 系统模块——key 是模块名
  "@ohos.measure": { "source": "src/mock/MeasureText.mock.ets" },
  // 3) 本模块内的文件——key 是相对 src/main/ets/ 的路径，**必须带 .ets 后缀**
  "utils/PreviewProbe.ets": { "source": "src/mock/module/utils/PreviewProbe.mock.ets" },
}
```

`source` 一律是相对**模块根目录**的路径。一个目标只能映射一份 mock。

### 三种 mock 实现写法

**依赖模块**——`export *` 透传原模块，再用具名导出覆盖要换掉的那几个。这是代价最低的写法，
不需要重新实现整个模块的 API：

```ts
// entry/src/mock/CommonLib.mock.ets
import { UserInfoModel } from 'commonlib';

export * from 'commonlib';        // 其余 API 原样透传

export class AccountUtil {        // 只覆盖这一个
  public static getUserInfo(): UserInfoModel {
    const user: UserInfoModel = new UserInfoModel();
    user.name = 'HAR_MOCKED_USER';
    return user;
  }
}
```

mock 文件里 `import 'commonlib'` **不会**递归指向自己——编译器会把它重定向到 `.origin` 条目。

**接口层用命名空间导出时**（`export * as HttpRequestApi from './HttpRequestApi'`，模板工程里的网络
模块几乎都这么写），mock 侧用一个静态方法类顶替，调用方写法完全不变——这是把整条网络链路（含
`@ohos/axios`、拦截器、真实域名）一次性摘掉的最省事办法，比逐个 mock 底层 HTTP 划算得多：

```ts
// entry/src/mock/Network.mock.ets
export * from 'network';

class HttpRequestApiMock {
  static async getHmSystem(): Promise<string> { return 'NET_MOCKED_RESP'; }
}
export { HttpRequestApiMock as HttpRequestApi };
```

前提是被预览模块的 `oh-package.json5` 里有这个包的依赖（`"network": "file:../commons/network"`）；
业务代码经由 `features/*` 间接依赖它时，entry 自己没声明就 import 不到，补一条再
`ohpm install --all`。

**这类 mock 只拦得住"外部按包名 import"的调用点，拦不住包内部的相对路径互调。** 例如 mock 掉
`network` 的 `ProductApis`，包里 `ProductApis` 自己 `import { BaseApi } from './BaseApi'` 的那条路径
仍然走原实现——替换发生在 import 说明符层面，包内相对路径的 import 根本不经过包名。判断方法：开
`PREVIEW_ENGINE_LOG=1` 看报错栈里的文件路径，**如果还指向原始实现**（`phone|common|1.0.0|…/BaseApi.ts:180`
这种），说明拦截点挂错了——要往上找"哪个类是从外部按包名 import 进来的"，在那一层 mock，而不是死磕
实际执行 IO 的底层函数。

**系统模块**——用 `extends` 继承原类再覆写，未覆写的方法保持原行为：

```ts
// entry/src/mock/MeasureText.mock.ets
import measure from '@ohos.measure';

class MockMeasureText extends measure {
  static measureText(): number { return 12345; }
}
export default MockMeasureText;
```

**本模块文件**——默认导出用 `extends`，具名导出用 `export { xMock as x }`：

```ts
// entry/src/mock/module/utils/PreviewProbe.mock.ets
import PreviewProbe from '../../../main/ets/utils/PreviewProbe';

class PreviewProbeMock extends PreviewProbe {
  static label(): string { return 'MOCKED_TEXT'; }
}
export const probeFnMock = (): string => 'MOCKED_FN';
export { probeFnMock as probeFn };
export default PreviewProbeMock;
```

### 最值钱的一个 mock：把启动拦截页跳过去

很多 App 首页前面挡着隐私协议页 / 引导页，判据是 `preferences` 里的一个布尔值——预览器里
`preferences` 是空的，于是永远被判成"没同意"，跳去隐私页；而隐私页的 UI 往往靠
`PromptAction.openCustomDialog()` 这类全屏自定义弹窗异步打开，**预览器里既不报错也不出画面**，
表现就是纯白 + 空 `Navigation`，极难从日志看出问题。

mock 掉那个判据一行就够，首页立刻能进：

```ts
// products/phone/src/mock/module/viewmodels/IndexVM.mock.ets
import IndexVMOrigin from '../../../main/ets/viewmodels/IndexVM';

class IndexVMMock extends IndexVMOrigin {
  isAgreePrivacy(): boolean { return true; }
}
export { IndexVMMock as IndexVM };
```

```json5
{ "viewmodels/IndexVM.ets": { "source": "src/mock/module/viewmodels/IndexVM.mock.ets" } }
```

实测这一招让 `Navigation` 成功 push 到真实首页并走完 `onAppear/onShown/onActive`。同一思路适用于
任何"开关型"拦截：登录态、新手引导、AB 实验开关、版本更新弹窗。

### 验证 mock 真的生效

别靠"看起来对了"——给 mock 值一个独特文案，用组件树断言：

```bash
$DRIVE find "MOCKED_TEXT"     # 找不到 exit 1
```

## `@MockSetup`

组件内部属性/方法的打桩，在 `aboutToAppear` **之前**执行，只在预览生效：

```ts
import { MockSetup } from '@ohos/hamock';

@Component
struct Person {
  @Prop species: string = '';
  @MockSetup mockInit() { this.species = 'primates'; }
}
```

也能配合 `MockKit` 给方法按入参打桩：

```ts
@MockSetup mockInit() {
  const mocker: MockKit = new MockKit();
  const f: Object = mocker.mockFunc(this, this.loadList);
  when(f)('hot').afterReturn(MOCK_LIST);
}
```

用不了的情况：`readonly` 和 `@ObjectLink` 属性；**成员初始化时就抛异常的场景**（`@MockSetup` 跑得
比它晚，见 A 类）；`@Link`/`@Consume`/`@Prop`/`@BuilderParam` 这类需要父组件提供值的——官方和实测
都建议改用 harness。

## harness 包装页

D 类（缺父级提供者）、C 类（组件不支持）、以及"只想单独看某个组件"时用。原理是绕开真实入口页
和它背后的取数链路，自己当父组件喂字面量 mock。

```ts
// entry/src/main/ets/pages/PreviewHarness.ets —— 仅用于预览，不属于真正的导航图
import { ProfileCard, UserVO } from '../components/ProfileCard';

@Entry
@Component
struct PreviewHarness {
  @State user: UserVO = { name: 'Ada Lovelace', followers: 128 };

  build() {
    Column() {
      ProfileCard({ user: this.user, onFollow: () => console.info('preview: follow tapped') })
    }.width('100%').height('100%')
  }
}
```

三个必须做的动作：

1. **注册进 pages 配置**（`entry/src/main/resources/base/profile/main_pages.json` 的 `src` 数组）
   ——`--page` 只认配置里的路由。
2. 用 `--page pages/PreviewHarness` 启动预览。
3. 验证完**删掉或排除出正式构建**——它是普通 `@Entry`，留着会被打进正式包。

ArkTS 的坑：`{...}` 字面量只能初始化没有自定义构造函数/`readonly` 字段/方法的类型。`interface`
天然可以；带构造函数的 `class` 必须 `new UserVO(...)`，否则直接死在 `arkts-no-obj-literals-as-types`,
什么都渲染不出来。

## 组合起来用

真实的复杂页面通常不止一类问题（实测里 F+A、A+E 叠加都很常见）。推荐顺序：

1. **E 类先清**——构建都不过，后面全是空谈。注意有些是模板仓库自己的 bug（import 大小写、HSP 资源
   ID 冲突、第三方 SDK 类型不匹配），跟预览无关。
2. **看组件树形状分流**：只有一个空 `Navigation` → 十有八九是 F 类，直接上 harness 调 Builder，
   最省事；有骨架但报 `xxx of undefined` → A 类，防御式改写或 `--ability-mode`。
3. **骨架起来之后再谈数据**——哪块空/一直"加载中"就 mock 哪条链路（B 类），接口层整包 mock 通常
   比逐个 mock 底层 HTTP 划算。
4. **局部实在起不来**（C/D 类）——才为那个组件单独写 harness。

每一步都用 `$DRIVE wait --for-rebuild` + `$DRIVE tree` / `$DRIVE find "<特征文案>"` 闭环验证。
**判定以 `tree` 为准，`shot` 只做佐证**：构建失败时画面会保留上一帧正常内容；反过来一次性帧
（`--no-watch`）可能截在资源还没加载完的时刻，看着是白的、其实组件树已经完整。

数据要经过 `await`（网络、mock 延迟、文件读）才落地的页面，**"树结构完整"不等于"数据到位"**——
先 `find` 一个只有真数据才会出现的文案，命中了再截图。
