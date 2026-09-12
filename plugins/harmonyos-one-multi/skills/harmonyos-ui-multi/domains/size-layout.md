# 域：布局与窗口尺寸

覆盖断点、响应式结构切换、组件自适应、窗口尺寸监听、平行视界、资源限定词。
本域的变化信号是**窗口宽高跨断点阈值**；窗口形态（分屏/悬浮窗/自由多窗）的
声明、状态监听与形态特有交互在 `window-form.md`。

## 症状 → 本文档

在设备上看到什么，就查哪一节：

| 症状 | 查本文 |
|---|---|
| 内容画到窗口外 | [固定尺寸的三种替代](#固定尺寸的三种替代) |
| 元素挤压压盖 | [空间不足时的取舍顺序](#空间不足时的取舍顺序) |
| 文字显示不全 | [文本容器约束](#文本容器约束) |
| 换了设备布局没变 | [断点没生效的四种原因](#断点没生效的四种原因) |
| 平板上内容缩在中间一条 | [四种响应式模式选型](#四种响应式模式选型) |
| 窗口变了容器没变 | [固定尺寸的三种替代](#固定尺寸的三种替代) |
| 一张图吃掉大半屏 | [媒体尺寸约束](#媒体尺寸约束) |
| 轮播/横幅在宽屏仍单张显示或被限宽居中 | [轮播属于重复模式](#重复布局要点) |
| 内容被推到一边 / 侧栏太宽 | [断点 UX 规格数值](#断点-ux-规格数值) |
| 宽屏出现左右分栏、右侧一片空白 | [分栏布局要点](#分栏布局要点) |
| LG 侧边 Tabs 全部挤在一起 | [挪移与缩进要点](#挪移与缩进要点) |
| 用户要求均分布局 / 等间距排列 | [均分布局优先 SpaceEvenly](#均分布局优先-spaceevenly) |
| 大屏文字异常放大 | 静态规则 S16 会拦，按规则给的建议改 |
| 分屏不生效 / 悬浮窗控制条遮挡 / 窗口拖不动 | 形态问题，走 `window-form.md` |

根因案例查 `../references/root-causes.md` 的 **RC-size** 段。

---

## 先认形态，再定断点

不要凭空设断点区间。横向断点（窗口宽度）与纵向断点（窗口高宽比）组合出常见屏幕形态，
每种都要有对应的布局设计——漏掉一种就会在某类设备上翻车：

| 形态 | 典型设备 | 横向 | 纵向 |
|---|---|---|---|
| 大屏横屏 | 平板、三折三屏态、大阔折展开 | lg | sm |
| 大屏竖屏 | 平板竖屏、三折三屏态竖屏 | md | lg |
| 大方形屏 | Mate X 展开、Mate XT 双屏 M 态 | md | md |
| 直板机竖屏 | Mate 60、各类折叠屏的折叠态 | sm | lg |
| 直板机横屏 | 直板机横屏、折叠屏横屏 | md | sm |
| **小方形屏** | **Pura X 外屏（阔折叠折叠态）** | **sm** | **md** |
| 圆形屏 | 智能手表（超出一多范围） | xs | sm |

选型规则：

- 布局差异只由宽度决定（列表/详情） → **只用横向断点**，覆盖 sm/md/lg 三档
- 导航位置、内容排列随窗口形状变 → **横向 + 纵向断点组合**

**小方形屏是最容易漏的一种**：横向 sm 但纵向 md，很多按"手机竖屏"假设写的布局
（底部页签占固定高度、顶部大标题栏）在它上面会把主内容挤没。具体尺寸见
`../references/device-matrix.md`。

---

## 四种响应式模式选型

大屏空间怎么用，只有四种基本答案。**先判类型再选组件**，反过来必错。

| 模式 | 什么时候用 | 组件 | 关键属性 |
|---|---|---|---|
| **重复** | 同质内容随空间增减列数（列表、宫格、瀑布流、轮播横幅都属此类） | `List` / `WaterFlow` / `Grid` / `Swiper` | `lanes` / `columnsTemplate` / `displayCount` |
| **分栏** | **前提最严格**：用户需求明确要分栏，或原代码已有 `.mode(NavigationMode.Auto/Split)`（见「分栏布局要点」）；命中前提后才看"不同类别内容需要同屏并列" | `Navigation` / `SideBarContainer` | `mode` / `showSideBar` |
| **挪移** | 同一组内容改变排列方向 | `GridRow/GridCol` / `Tabs` | `span` / `barPosition`+`vertical` |
| **缩进** | 正文、窄表单等需要控制行长/操作宽度的局部单列内容区 | `GridCol` | `span` + `offset` |

判断顺序：内容是否同质（列表、宫格、**轮播横幅**——几张静态枚举的 banner 与 `ForEach` 数据驱动的轮播是同一类东西） → 是否有主从关系 → 是否只是方向变化 → 是否有明确的阅读行长或表单宽度约束。最后一项不成立时不要用缩进兜底；保持全宽并继续分析页面语义，不能把手机单列简单居中后结束。注意"有主从关系"只是分栏的必要条件而非充分条件：未过「分栏布局要点」的前提门槛时，用重复、缩进兜底，不引入分栏。

### 断点 UX 规格数值

官方给的规格值，**别自己编默认值**（xl 未单列时与 lg 一致）：

| 场景 | 属性 | sm | md | lg |
|---|---|---|---|---|
| 列表 | `lanes` | 1 | 2 | 3 |
| 列表 | `space` 行间距 | 8vp | 12vp | 16vp |
| 列表 | 列间距 | — | 12vp | 12vp |
| 瀑布流 | `columnsTemplate` | 基线 N | N+1 | N+2 |
| 轮播 | `displayCount` | 1 | 2 | 3 |
| 轮播 | `prevMargin`/`nextMargin` | 0 | 12vp | 64vp |
| 轮播 | `indicator` | 圆点 | false | false |
| 网格 | `columnsTemplate` | 2 | 3 | 4 |
| 侧边栏 | `SideBarContainerType` | Overlay | Embed | Embed |
| 侧边栏 | `sideBarWidth` | 80% | 50% | **40%** |
| 侧边栏 | `showSideBar` | false | true | true |
| 单/双栏 | Navigation `mode` | Stack | Split | Split |
| 单/双栏 | `navBarWidth` | — | 50% | 50% |
| 三分栏 | `sideBarWidth` | 80% | 50% | **20%** |
| 三分栏 | `navBarWidth` | — | 50% | 30% |
| 三分栏 | `showSideBar` | false | false | true |

**列数递增原则**：上表的列数是通用参考值，实际必须以**原始设计基线**为起点递增。
原设计 1 列瀑布流 → 1/2/3，不是照抄 2/3/4。照抄会让大屏挤得比设计意图密一倍。

递增管的是**整条序列的形状**，不只管起点。把 `lanes` / `columnsTemplate` /
`GridCol span` 换算成各档列数后逐档自查：

1. **逐档单调不减，默认每档 +1**，直到继续增列会低于卡片最小可读宽度为止。
2. **md→lg 持平必须有内容侧理由**（项数固定且已排满、继续增列低于最小宽度），
   没有理由的持平等于把 lg 的 240vp 宽度增量白白浪费。持平的合理位置在尾部
   xl（规格默认 xl 与 lg 一致），不在中间档。
3. **把递增推迟到 xl 是最隐蔽的漏配**：xl 要求窗口 ≥1440vp，覆盖设备清单里
   没有任何设备到得了（平板横屏最大约 1137vp，全在 lg，见
   [device-matrix.md](../references/device-matrix.md)）。"sm 1 / md 2 / lg 2 / xl 3"
   意味着所有真实平板上永远显示 2 列——xl 的配置形同虚设。

lg 的 `sideBarWidth` 上限 40% 与质量检查 `QC-08` 一致。
**「单/双栏」「三分栏」行的数值只在分栏已被判定采用后才适用**——它们是分栏的规格值，不是分栏的采用依据；断点到达 md/lg 本身不构成启用 Split 的理由，采用前提见「分栏布局要点」第一条。

### 重复布局要点

- **轮播/横幅是重复模式，不是"一张图"的媒体问题**：`Swiper` 宽屏适配的第一手段是
  `displayCount` 按断点取规格值（sm 1 / md 2 / lg 3）。`displayCount` 用 number 时，
  子组件自动均分 Swiper 主轴宽度（减去 `itemSpace`），子项写 `width('100%')` 即可，
  不要为多张显示逐项写固定宽度。
- **不要给 `Swiper` 套 `maxWidth` 限宽来"适配轮播"**：限宽只防单张拉伸，宽屏上轮播
  缩成中间一条、两侧留白，一张都没多显示，等于放弃了重复模式的空间利用——这与
  "缩进不能包住媒体"是同一条规则。图片变形用 `ImageFit` / `aspectRatio` 解决；
  限宽只可能来自所在内容区（如详情页正文）的整体策略，不是轮播自身的适配手段。
- `List` 用 `ForEach`/`LazyForEach` 渲染的同质列表才加 `lanes`；表单行、混合内容块**不要**加。
- `lanes >= 2` 时 `divider` 必须设为 `undefined`，否则多列间分割线错位。
- `WaterFlow` 改 `columnsTemplate` 默认触发整树重挂载，用 `WaterFlowLayoutMode.SLIDING_WINDOW` 避免；
  `FlowItem` 必须 `.width('100%')`，否则内容溢出。
- `Swiper` 的 `displayCount > 1` 时必须设正的 `itemSpace`；`prevMargin`/`nextMargin`
  只控制视口边缘露出，**不是项间距**。多张可见时 `indicator` 要关掉。
- `Swiper.onChange` 拿到的是最左索引，最右索引要自己算 `index + displayCount - 1`。

### 分栏布局要点

- **采用分栏的前提很严格，必须命中以下任一条**：
  1. 用户需求明确提出分栏（如"大屏左右分栏""详情页在右栏打开"）；
  2. 原代码已存在 `.mode(NavigationMode.Auto)` 或 `.mode(NavigationMode.Split)`，本次适配只做参数与体验优化。
  两条都不满足时**保持 Stack 基线**，大屏用重复（增列）、缩进（限宽）做自适应，不得主动引入分栏；
  "内容有主从关系""同类应用大屏惯例""断点达到 md/lg""规格表 md/lg 写着 Split"都不能单独作为分栏依据。
- **未写 `.mode()` 不等于 Stack 基线**：`Navigation` 的默认值是 `NavigationMode.Auto`——窗口宽 ≥600vp 时**自动切 Split 双栏**，首页内容被压进左侧 navBar、右侧详情栏因无路由而一片空白。手机工程（<600vp 一直走 Stack）从未暴露该行为，适配平板/折叠展开/宽预览时才浮现。因此分栏前提不满足时，"保持 Stack 基线"必须**显式写 `.mode(NavigationMode.Stack)`**；核查既有工程时不能只在源码里搜 `.mode(`——"未显式设置"本身就是隐式 Auto，同样会在宽屏分栏。  
- 分栏确定后，实现上优先 `NavigationMode.Auto`：系统在 ≥600vp 自动 Split、<600vp 回退 Stack，**不需要**自己写断点监听。
- 只有需要自定义阈值、运行时动态切换（如聊天全屏回退）、或各断点 `navBarWidth` 不同时，才手写断点分支。
- 双栏下右侧默认为空：用 `onNavigationModeChange` 在切到 Split 时推默认路由，切回 Stack 时清 `pathStack`。
- `navBarWidth` 不能超过窗口宽的一半，否则框架降级为单栏。
- **嵌套顺序是死规矩**：`Navigation` 与任何自带分区能力的容器
  （`SideBarContainer` / `Tabs` / 自定义分栏 `Row`）组合时，**分区容器在外、Navigation 在内**。
  反过来 Navigation 会把整个分区容器当作 navBar 内容，宽屏下内容区一片空白。
- `SideBarContainer` 必须**恰好两个**直接子节点（侧边栏在前、主内容在后），多一个少一个都会运行时报错。
- 折叠内屏竖屏要当心：`Split` 只看宽度，内屏竖屏宽度够但高度不足，分栏会挤成一团 ——
  分栏条件应同时看横纵断点。

### GridRow 配置：value 与 columns 必须配齐

写 `GridCol` 做栅格布局，`GridRow` 自身两个字段必须同时给全，**少一个栅格就退化、断点对不上号**——这是栅格适配里最高发的写法错误：

1. **`breakpoints.value` 必须是完整四值数组** `['320vp', '600vp', '840vp', '1440vp']`，**不能截断**。数组里有几个值，就只有那几档断点：只写 `['600vp', '840vp']` 时只有 xs/sm/md 三档，lg / xl 两档**永不触发**，`GridCol` 里给 `lg`、`xl` 设的 `span` 静默失效，大屏一直停在 md 的列数。

   **每个元素必须是「数字+vp」格式**（官方约束）。`'0'`、`'600'` 这类无单位值是**非法值**——不是只废掉一个元素，而是**整个数组按默认值处理**，回退成 `['320vp', '600vp', '840vp']`：xl 档随之消失，自定义边界全部静默丢失，编译和运行都不报错。排查口诀：改了 `value` 但断点行为跟没改一样，先检查有没有无单位元素。

   ❌ `value: ['0', '600vp', '840vp', '1440vp']` —— `'0'` 非法，整体回退默认，xl 档消失
   ❌ `value: ['600vp', '840vp']` —— 只有三档（xs/sm/md），lg 以上不分档
   ✅ `value: ['320vp', '600vp', '840vp', '1440vp']` —— xs/sm/md/lg/xl 五档齐

2. **`columns` 必须显式声明各档总栅格数** `{ sm: 12, md: 12, lg: 12, xl: 12 }`。`GridCol.span` 是「占 `columns` 里的几份」，**没有 `columns` 就没有分母**，`span: 2` 算不出实际宽度、退化成按内容排布。不写时走系统默认（sm 4 / md 8 / lg 12），与多数设计稿的 12 栅格基线对不上。

完整写法（两个字段缺一不可）：

```typescript
GridRow({
  breakpoints: {
    value: ['320vp', '600vp', '840vp', '1440vp'], // 四个边界写全，每个元素必须带 vp 单位
    reference: BreakpointsReference.WindowSize,
  },
  columns: { sm: 12, md: 12, lg: 12, xl: 12 }, // 显式声明各档总栅格数
  gutter: { x: Constants.PADDING_S },
}) {
  GridCol({ span: { xs: 3, sm: 3, md: 3, lg: 2 } }) { /* ... */ }
}
```

`value` 管「有几档、边界在哪」，`columns` 管「每档总共多少格」。`GridCol.span` 只有两者齐备时才按 `span / columns` 算出正确宽度。

3. **首值 `320vp` 意味着 xs 档 [0, 320vp) 真实存在**——分屏半屏、悬浮窗窄窗口会落进来。
   官方规则：`span` 按 xs→sm→md→lg→xl 顺序**继承**，未设置的档位从前一档取值；**xs 没有前档**，
   缺省时落到组件默认值 1（占 1/12 宽，一排挤 12 个卡片）。所以 `span` 对象从 `xs` 显式给起
   （通常与 sm 基线一致），不要只写 sm/md/lg/xl。
4. **短列表必须顶部对齐**：列表内容从顶部起始排布是正确形态——项数少时（如只有两三条）
   整体悬在视口中间肯定是错的。排查按来源走，不套固定属性：
   - 首选让滚动容器**撑满可用空间**（`layoutWeight(1)` 或 `height('100%')`）——容器满高后
     没有剩余空间可居中，内容自然从顶部排；
   - 仍被居中时，改**父容器** `justifyContent(FlexAlign.Start)`；
   - 对 `Scroll` 实证可用 `.alignSelf(ItemAlign.Start)` 钉住，但它生效与否取决于宿主容器
     类型与轴向，**不能当作对 List/GridRow 等一切列表容器通用的配方**，加完必须在目标形态
     上验证确已顶部对齐。

### 挪移与缩进要点

- `Tabs` 在 lg 断点要**五个属性一起改**：`barPosition`、`vertical`、`barWidth`、`barHeight`、`barMode`。
  只改一部分会出现"导航条到了侧边但还是 56vp 高"这种错位。
  sm/md 必须完整恢复为 `End / false / '100%' / 56vp(+导航条高度) / Fixed`；lg 使用
  `Start / true / 96vp / '100%' / Scrollable`。侧边条件不得用 `isWide`，因为它包含 md。
  xl 要继续侧边 Tabs 还是升级为 `SideBarContainer` 属于独立结构决策；不得让 md 继承侧边状态。
  普通页面使用原生 `Tabs` 让侧栏参与布局；`Stack + position` 的浮层 SideTabBar 只用于已确认的
  沉浸式媒体场景，普通页面使用会遮挡内容。
  切成侧边导航后每项必须**图标 + 文字**（12fp，文字在图标下方），禁止只留图标。
  切换到 LG 侧边栏时，每个自定义 `tabBar` Builder 的**页签项根节点必须同时设置 `top` 和 `bottom` margin**。
  margin 数值由模型结合页签内容尺寸、侧栏可用高度和期望的视觉间距判断，并在 LG 下验证；
  可以直接使用判断后的数值，不要求目标工程预先存在对应资源或设计 token。
  侧边栏仍使用 `BarMode.Scrollable` 兜底内容溢出。
  系统避让区高度只用于安全区补偿，不得复用为通用页签间距 token。
  真实项目写法参考 [`LAYOUT-07 日历应用侧边 Tabs`](../references/cases/bug-fix-size-layout.md#layout-07-日历应用侧边-tabs-页签间距过小)：
  案例代码原样保留 `tabBuilder` 根节点的上下 `margin`；实现其他项目时由模型根据实际布局判断取值，
  不机械照抄案例数值。
  普通页面需要完整实现时，直接复用
  [`ResponsiveTabsExample.ets`](../assets/size-layout/ResponsiveTabsExample.ets)；不要从沉浸式视频案例复制浮动导航骨架。
- 缩进只作用于正文、窄表单等**局部内容区**，不能包住页面根容器、标题栏、导航、背景、媒体、列表和操作区；普通列表/信息流应优先增列、延伸或分栏。
- **收窄居中的对象是核心内容区，不是整个页面**：标题栏（标题 + 返回箭头）永远不进
  限宽层，必须留在 `GridRow` 之外保持全宽原位——返回箭头仍贴左上角，标题不随断点缩进。
  把标题栏一起包进 `GridCol` 的 span+offset，大屏上连标题带内容缩成中间一条，
  看起来就像屏幕变小了，而不是内容区被合理收窄。正确结构：标题栏在 `GridRow` 外，
  `GridRow > GridCol > Scroll` 只包核心内容；Navigation 页面把 `GridRow > GridCol`
  放在 NavDestination 内容区，标题栏由 NavDestination 自身渲染、天然不受限宽影响。
  自查症状：**切到大屏断点后标题和返回箭头跟着居中缩进＝限宽层范围包错，包成了整页**。
- **限宽层与滚动容器的位置决定收窄的是谁**：只要收窄对象是**整个可滚动内容区**（如大屏
  单列太宽、控制阅读行长而收窄居中），限宽层必须
  **包住滚动容器本身**——`GridRow > GridCol > Scroll`，span/offset 按断点收窄 Scroll。
  把 GridRow 放进 Scroll 内部（`Scroll > GridRow > GridCol > 内容`）只能收窄**内容**，
  Scroll 容器仍全宽贴边、两侧留白为 0，滚动条与组件树外层测量（UI 自动化按容器 bounds
  断言）读到的都是全宽。自查症状：**收窄后滚动条仍贴屏幕边缘＝限宽层放错了位置**。
  只有页面内某个局部内容区需要限宽时才用内层结构，且不动页面级滚动容器。
- **收窄档位要算比例自查**：选完 `span` 后逐档计算各档收窄比例（width = span / columns），
  不要只凭“比全宽小”就交差。常用基线：SM 接近全宽、**MD 约 75%**（8 栅格 6/8、
  12 栅格 9/12）、**LG 约 67%**（8/12）——即系统默认 4/8/12 栅格下 span 4/6/8 的标准
  “收窄居中”配比。“收窄”应比上一档至少收一档（≥15%），12 栅格下 MD 用 span 10
  （约 83%）属于几乎没收窄的常见失档；把各档预期比例写入验证计划。
- 确认需要缩进后，用 `GridCol` 的 `span` + `offset`（12 栅格中 span 8 / offset 2）。
  **不要**用随断点变化的 `constraintSize maxWidth`——断点边界会跳变。
- 不得仅因多个页面都需要局部限宽就自行创建公共 `ContentWidthLimit` 类组件。公共封装必须先在代表页验证，并作为结构方案确认；未经确认时按已确认页面最小修改，不向全工程扩散。
- `GridCol` 的 `span + offset` 不能超过该断点下 `GridRow.columns` 的总数。
- **`GridCol` 里套可滚动组件时**（`List`/`Scroll`/`WaterFlow`），内部必须用
  `.layoutWeight(1)` 而**不是** `.height('100%')`——后者会把系统状态栏区域算进去导致溢出，
  且 GridCol 自身没有明确高度约束时 `layoutWeight` 根本不生效。

---

## 七种自适应能力

同一断点内组件如何弹性变化。与响应式（跨断点结构切换）是两个层次，常嵌套使用。

| 能力 | 属性 | 陷阱 |
|---|---|---|
| 拉伸 | `layoutWeight` / `Blank` | 与显式宽高在主轴上**互斥**，同设时显式值被忽略 |
| 均分 | 间距均分首选 `justifyContent(FlexAlign.SpaceEvenly)`；尺寸均分用 `layoutWeight` / `flexGrow` / 百分比 | `SpaceBetween` 要求子内容总高 ≤ 容器高，超了直接失效并重叠 |
| 占比 | 百分比宽高 | 父容器必须有确定宽度 |
| 缩放 | `aspectRatio` | 各断点应给**不同**值（sm 4:3 / lg 16:9），全断点同值是错的 |
| 延伸 | `List` / `Scroll` | — |
| 隐藏 | `displayPriority` | 只对 `Row`/`Column` 的**直接子节点**生效；且**只在 Flex 单行模式下生效**，`Column` 与多行换行模式下无效 |
| 折行 | `FlexWrap` | — |

### 均分布局优先 SpaceEvenly

用户提到"均分布局""等间距排列"时，默认要的是**间距均分**：在容器主轴上设
`.justifyContent(FlexAlign.SpaceEvenly)`，让布局引擎把剩余空间均分成
「子项之间 + 两端」完全相等的空隙。间距由各断点下的实际剩余空间实时决定，
sm 到 lg 自动变化，不写死任何数值。

```typescript
Row() {
  // 若干操作项
}
.width('100%')
.justifyContent(FlexAlign.SpaceEvenly) // 项间与两端空隙全部相等，跨断点自动适应
```

### `displayPriority` 独占可见数量决策

已经为单行 `Row` / `Flex` 的直接子节点设置 `displayPriority` 时，必须把完整数据集交给
`ForEach`，由布局引擎根据每个子节点的实际测量尺寸和优先级决定显示或隐藏。容器只需提供明确的
主轴约束（例如 `.width('100%')`）；**不要**再监听窗口或组件宽度，不要计算
`availableWidth / itemWidth`、`visibleCount` / `maxVisibleCount`，也不要用 `slice` / `filter`
预先裁掉子节点。手动数量控制会与 `displayPriority` 形成两个显隐事实源，并在文字长度、字体缩放、
间距、内边距或数据变化时产生错误结果。

`displayPriority` 按优先级分组显隐：值越大越优先显示，落在同一区间 `[x, x + 1)` 的值视为
同一优先级；**同一优先级的子节点同时显示或隐藏，不会再按排列位置从尾部逐项隐藏**。不要把示例中
“靠后的节点被隐藏”误写成框架的同优先级规则——只有显式给靠后节点分配了更低优先级时，位置才会
与隐藏顺序相关。

需要多个元素作为一个整体显隐时，先将它们封装成一个语义完整的直接子组件，再把
`displayPriority` 设置在组容器上。相同优先级本身保证同时显隐，封装则用于明确组件树中的原子边界。
不能以“同优先级会从尾部逐项隐藏”为由排除 `displayPriority`。

`displayPriority` 的触发前提是容器**主轴空间有界且内容可能溢出**。把设置了权重的
内容区包进 `Scroll` 后，内容高度无界，空间永远“够用”，优先级隐藏**永不触发**——
需要按价值隐藏的区域必须保持有界容器（页面/卡片高度受视口或半屏约束），需要滚动的
内容放进 `Scroll`，两者不能作用于同一内容区。这是“设了权重却始终不隐藏”的第一根因。

按业务价值分级减少内容（窗口变窄时关键信息保留、次要信息逐级隐藏）是 `displayPriority`
的标准场景：权重用**命名常量**表达价值层级（关键 > 高 > 中 > 低），同一层级共用同一权重；
多个同价值小项封装为组容器整组显隐；必须完整显示的关键项配 `flexShrink(0)`。完整业务写法
参考 [`row-displaypriority-value-graded.ets`](../assets/size-layout/row-displaypriority-value-graded.ets)。

**优先级链规格的解析**：需求用 `A > B >= C >= D > E` 这类链表达显隐优先级时，`>` 分隔
严格层级，`>=` 连接同一显隐组——**连续 `>=` 段不论多长都是一个等价组**，整组共用同一
权重；组数 = `>` 出现次数 + 1。解析后自检：按 `>` 切段、数一遍组数与最长 `>=` 段的
成员数，**不要按固定两两分段**——把 23 项的连续 `>=` 尾段切成 11 个双元组是真实事故：
组内被赋不同权重，部分隐藏时同组成员显隐状态不一致。

价值分级的**权重粒度必须与断点位置匹配**。档位共用权重时，每个目标形态的断点只能落在
档边界，适合信息行、工具条这类按档整体取舍的组件。进度条、流程条、步骤条、面包屑这类
**顺序前缀型**组件——任意宽度下可见集必须是业务顺序的连续前缀，而某目标形态的截断点
往往落在档中间——必须给同档内各项分配**逐项递减的独立权重**：

1. 先按各目标形态的容器宽度预算（子项测量宽 + 间距 + 连接符）估算每个形态能显示到哪
   一项，权重方案要能精确复现这些断点；价值档位是排序输入，不是分组输出，不要照抄
   档位字面分组。把每个形态**预期显示到哪一项**写入验证计划，作为施工后自检断点。
2. 按业务顺序给各项赋单调递减权重（如 `权重 = 序列长度 - 下标`）；最宽形态截断点之后的
   项**与更低档合并同权**——同一权重是“整组同时隐藏”的分组手段，让放不下的末档项随
   基础档整组隐藏，比让它独占一档更稳。
3. 相邻节点之间的连接符（箭头、连线）权重取 `min(前后节点权重)`：任一端隐藏，连接符
   同步隐藏，不残留孤立箭头。
4. 权重交付必须**静态可核验**：要么在每个数据构造点显式传命名常量/字面量，要么在组件
   渲染时用纯函数按 id 现算（如 `visibilityWeightForNode(item.id)`）。不要用
   **构造函数默认参数调用函数**这类间接层算权重——默认值在运行时被字段初始化器或
   数据构造抹平成同一个值时，所有子节点落进同一优先级组，引擎**无组可隐藏，一个都不藏**，
   且编译与静态检查全程不报错。排障口诀：设了权重却“全部显示”，先确认运行时各节点
   权重确实互不相同（默认参数、字段初始化器覆盖、反序列化丢字段是三大抹平来源）。

完整业务写法参考 [`track-displaypriority-prefix.ets`](../assets/size-layout/track-displaypriority-prefix.ets)。

只有产品语义明确要求“固定显示 N 个”或需要把溢出项聚合进“更多”入口时，才采用手动分组/计数；
这是另一种方案，此时不要再让 `displayPriority` 承担数量决策。两种方案必须二选一。

`flexShrink` 的三个生效前提：容器有主轴尺寸约束（`Row` 要 `width`、`Column` 要 `height`）、
子组件显式声明、必须完整显示的那个设 `flexShrink(0)`。
三者缺一，收缩就会均摊到所有子组件上，"该压的没压、不该压的被压扁"。

**`layoutWeight` 挑父容器，`flexGrow` 不挑**：

| 父容器 | `layoutWeight` | 分配剩余空间该用 |
|---|---|---|
| `Row` / `Column` | 生效 | `layoutWeight` |
| `Flex` | **不生效** | `flexGrow` |
| `Stack` / `Grid` | 不生效 | 百分比 / `columnsTemplate` |

在 `Flex` 里写 `layoutWeight` 是静默失效——不报错、不警告，组件就是按内容宽度排布。
`Flex` 下用 `flexGrow`（父 > 子时分配剩余）与 `flexShrink`（父 < 子时收缩）这一对。

### 半屏/分屏压缩：弹性 Blank 替代固定大间距

分屏（高度减半）、悬浮窗把窗口压小后，固定的大间距——顶部内边距上百 vp、
元素间距几十 vp 这类常量——**不可压缩**，会直接把底部关键内容（协议勾选、操作按钮）
挤出视口，页面即使可滚动也表现为“滚不到底”。修法：非关键的大间距替换为**弹性 Blank**：

```typescript
// 空间充足时撑开占位，不足时收缩到 minHeight；上下限取设计稿的安全间距范围
Blank().layoutWeight(1).constraintSize({ minHeight: 16, maxHeight: 96 })
```

配合要点：

- 弹性 Blank 同时保住父容器的**有界语义**，使 `displayPriority` 在半屏下能正常触发；
- 需要同时滚动和隐藏的页面，把“按价值隐藏”约束在有界区域（如品牌区），
  长文案放 `Scroll`，分层处理；
- 改造前**盘点所有内容高度可能超过半屏的页面**（登录、协议/隐私声明、表单等），
  逐页替换固定间距，不要只修一个页面就收工。

### 固定尺寸的三种替代

内容画到窗口外、或窗口变了容器没跟着变，按这个顺序试：

1. `'100%'` —— 撑满父容器，最简单
2. `layoutWeight(1)` —— 按权重分配剩余空间；**父容器必须有确定宽度**，否则没有"剩余空间"可分
3. `GridCol span` —— 按栅格占比，跨断点最稳

窗口可能变得很窄时（折叠切换），给 `layoutWeight` 的组件加 `constraintSize` 兜底，
防止算出零或负尺寸。

**`constraintSize` 有个前提常被忽略**：它只能约束**已有宽度基准**的组件。
根组件没有 `width`、没有父容器给宽、也没有 `layoutWeight` 时，宽度由内容撑开，
`maxWidth` 完全不起作用。弹窗与浮层的根组件（`@CustomDialog`、`bindContentCover`
的 `@Builder`、`promptAction.openCustomDialog`）正是这种情况。

### 空间不足时的取舍顺序

元素互相压盖说明容器塞不下了。按代价从低到高：

1. **折行**（`FlexWrap`）—— 信息不丢
2. **按优先级隐藏**（`displayPriority`）—— 丢次要信息
3. **改多列/分栏结构** —— 改动大但最彻底
4. 缩小元素 —— 最后手段，容易让触控目标小到点不中

### 文本容器约束

文字显示不全说明文本被容器裁掉了：

- 给文本加 `flexShrink(1)` + 显式 `textOverflow` —— 至少让省略号是设计的而不是意外的
- 或改多行显示（`maxLines` + `textOverflow`）
- 或在该断点下换结构（单行改两行、横排改竖排）

**承载文字的容器不要给固定高度。** 大屏字体异常有三个根因，按排查顺序：

1. **`lpx` 单位**——按屏幕宽度等比缩放，宽屏下同样的数字对应更大的显示尺寸。
   头号原因，静态规则 S16 能查出来。
2. **系统超大字号（`fontSizeScale`）**——用户在系统设置里开了超大字号，
   应用未做任何限制时缩放系数被无条件应用。大屏本来就宽松，放大后更容易顶破容器。
   在 `onConfigurationUpdate` 里读 `Configuration.fontSizeScale` 并按业务上限钳位。
3. **`px` 单位**——物理像素，不随密度和系统字号缩放，不同密度屏上视觉大小不一致。

单位口径：**文字用 `fp`**（随系统字体缩放），**尺寸用 `vp`**（随屏幕密度缩放）。
前两条都会让文字变高，固定高度的容器一定被顶破——这是同一类故障的两个入口。

### 媒体尺寸约束

图片/视频吃掉太多屏高时，上架规格给的上限：
信息流 40%、内容区全宽 50%、详情页与沉浸式 60%（详见 `../references/quality-checklist.md`）。

- 用 `constraintSize({ maxHeight: '50%' })` 之类的**比例上限**，不要给图片写死高度
- 只设 `width` 不设 `height` 时，大屏会按原图比例把高度一起放大——必须配 `aspectRatio` 或高度上限
- `width('100%') + height('100%') + ImageFit.Cover` 且容器高度是固定像素算出来的，
  会被 Cover 强行拉伸裁剪
- `ImageFit.Fill` 在任何多设备场景下都是错的，换 `Cover` 或 `Contain`

---

## 断点系统

### 优先用系统断点

工程还没有断点体系时，直接用 `UIContext.getWindowWidthBreakpoint()` /
`getWindowHeightBreakpoint()`，不要自己造一套。已有体系的工程，**修复场景尊重原有实现**，
只在整体重构时才建议换。

### 五个前置条件，缺一断点就是死的

1. **只在 `windowStage.loadContent(...)` 实际加载的入口页 `aboutToAppear()` 调用
   `BreakpointSystem.register(uiContext, mainWindow)`**。入口页已完成创建，可从宿主
   `UIAbilityContext.windowStage.getMainWindowSync()` 取得当前窗口；业务页不得重复注册。
2. **`@StorageProp` 的数据源必须在组件外部注册**。`@StorageProp` 是只读绑定，
   `AppStorage` 里没有这个 key 或从不刷新时，组件永远用声明时的默认值，布局固定在初始状态。
3. **禁止用 `get` 计算属性从断点派生状态**。框架只追踪 `@StorageProp` 本身的变化，
   不会因为 `get` 的返回值变了就重渲染。要派生状态就用 `@State` + `@Watch` 显式同步，
   并在 `aboutToAppear` 里调一次回调初始化。
4. **断点类型两侧一致**。`getWindowWidthBreakpoint()` 返回 `WidthBreakpoint` 枚举，
   写进 `AppStorage` 后消费侧的类型与比较方式必须一致，不能一边存枚举一边按字符串比。
5. **V2 消费端必须建立观察关系**。使用标准资产时写
   `@Local bpState: BreakpointState = BreakpointSystem.state`；不要把 `isLg` 结果缓存进普通 boolean，
   也不要在 `build()` 外读取一次后长期复用，否则监听类已更新但页面不会重绘。

### 全工程只保留一个断点状态源

这是断点驱动页面的必备条件。修改 `span`、`lanes`、Tabs 位置或分栏前，先复用或补齐统一断点系统，再继续页面代码。

修改前搜索所有 `getWindowWidthBreakpoint()`、`windowSizeChange`、`BreakpointManager`、
`BreakpointObserver` 和 `BreakpointSystem.register()`。若多个页面包含同构监听逻辑，不要继续逐页修补：

1. 统一保留 `BreakpointSystem.ets`，删除或迁移其他同职责断点类；
2. 按 [`BreakpointEntryRegistration.ets`](../assets/size-layout/BreakpointEntryRegistration.ets)
   只在 `loadContent` 实际加载的入口页 `aboutToAppear()` 注册一次；
3. 所有 V2 页面只用 `@Local bpState: BreakpointState = BreakpointSystem.state` 消费；
4. 只在同一入口页 `aboutToDisappear()` 注销；其他页面进退不得注册或注销全局断点监听；
5. 合并完成后重新搜索，`BreakpointSystem.register()` 的生产代码调用点必须恰好一个。

修改完成时确认标准断点资产已接入实际 import/调用链、V2 消费端建立观察关系，并运行
`devecocli build`。仅复制示例文件但没有注册不算完成；构建环境不可用或构建失败时如实标记未验证。

工程已有一套行为正确且被广泛使用的断点基础设施时，统一到工程原实现，不额外并存
`BreakpointSystem`；“统一”指单一事实源，不是无条件替换成熟基础设施。

### 断点回调必须双向完整

每个断点值都要明确对应一个确定的 UI 状态。**只处理"需要变化"的那一侧、
依赖初始值的隐式正确性，是断点类缺陷的主要来源**——从 lg 切回 sm 时状态回不去。

写完对着断点 × 状态画一张矩阵，**不允许有空白格**。

### 断点没生效的四种原因

断点变了但布局没变，按这个顺序排查：

1. **参考系错**：`GridRow.breakpoints.reference` 用了 `ComponentSize`，
   它以组件自身宽度为准，忽略分屏窗口宽度 → 改 `WindowSize`。
   **反向场景**：局部容器变窄时希望栅格降列，那才该用 `ComponentSize` —— 想清楚这段栅格跟谁
2. **断点值数组被截断或含非法值**：`value` 只写 `['600vp','840vp']` 两值时 lg/xl 两档**永不触发**、对应 `GridCol span` 静默失效；**任一元素无 vp 单位（如 `'0'`）会让整个数组回退默认** `['320vp','600vp','840vp']`，xl 档随之消失。必须是每个元素带单位的完整四值 `['320vp','600vp','840vp','1440vp']`（详见上文「GridRow 配置」）
3. **状态变量没有装饰器**：驱动布局的变量必须是 `@State` / `@StorageProp`，
   普通变量不触发重渲染
4. **注册或销毁位置错**：`BreakpointSystem.register(uiContext, mainWindow)` 必须在
   `windowStage.loadContent(...)` 加载的入口页 `aboutToAppear()` 调用一次，`unregister()`
   放在该入口页 `aboutToDisappear()`；普通业务页面不得管理全局断点生命周期

### 阈值不可硬编码

官方文档明确："个别设备可根据需求通过产品化配置调整断点阈值"。
一律用 `UIContext.getWindowWidthBreakpoint()` 的返回值。
`px2vp(w) >= 600` 这类写法没有工具会拦，只能自己盯。

**还有一个更隐蔽的理由**：`px2vp()` 依赖 DPI。用户调大"显示大小"后 DPI 升高，
同样的物理像素换算出更少的 vp——Mate 60 Pro 实测 DPI 480→630 时最小边从 390vp 跌到 320vp。
凡是用 vp 算出来的阈值判断，都会在改过显示大小的设备上失效。

### 布局切换用 Visibility 而非 if/else

`if/else` 会销毁并重建组件，断点切换时闪烁，还会丢失组件内部状态
（滚动位置、输入内容）——后者正是形态切换后状态丢失的常见来源。

---

## 窗口监听

- 注册在 `loadContent` 加载的入口页 `aboutToAppear()`；从宿主 `UIAbilityContext.windowStage`
  获取当前主窗口，并使用入口页的 `getUIContext()`。
- 必须配对 `off()`，否则页面反复进出监听累积。
  **`off()` 要传与 `on()` 相同的回调引用** —— 匿名函数每次求值都是新引用，注销不掉；
  裸 `off('事件名')` 又会把别的组件注册的监听一起删掉。先把回调存成字段再注册。
- 防抖 100~200ms，避免拖拽自由窗口时高频重排。

### 监听的分工

尺寸类监听归本域；窗口形态监听（`windowStatusChange` / `windowStatusDidChange`）
在 `window-form.md`「两个状态监听」，注册/注销纪律通用。

| 事件 | 何时用 | 坑 |
|---|---|---|
| `windowSizeChange` | 需要新尺寸 | **180° 旋转不触发**（宽高没变），要配 `display.on('change')` |
| `systemDensityChange` | DPI 变了 | 尺寸可能没变，`windowSizeChange` 不触发，但 vp 换算全变了 |

`systemDensityChange` 最容易被漏掉，因为它不改窗口尺寸：用户在系统设置里调「显示大小」、
或退出自由多窗时 DPI 会变，同样的物理像素换算出不同的 vp。**只监听 `windowSizeChange`
的工程在这两种场景下断点是错的**，理由见下面「阈值不可硬编码」里的 DPI 实测数据。
凡是用 vp 参与判断的地方，两个监听都要挂。

`px2vp` 在 API 18+ 用 `uiContext.px2vp(px)` 实例方法，全局函数版已废弃。
转换结果建议显式标 `: number`，否则 ArkTS 可能报 `any`。

---

## 应用内分屏

已移至 `window-form.md`「应用内分屏」（链路四步、`splitRatio`、幻觉点清单与三件套资产）。
留在这里的只有一条本域视角的结论：分屏窗口宽度会落到 sm/md 断点，已有的响应式分支
能直接吃下——**分屏适配的本质是断点适配**，不需要为分屏另写一套布局。

---

## 平行视界（EasyGo）

用户明确提到"平行视界"/"EasyGo"，或需求是"不改代码就要分栏"时用它。
需要按断点动态改结构、或分栏比例随内容变时，走 `Navigation` 手写分栏。

- 只能配在 **entry 模块**，配置后应用级生效。
- `routerSplitOptions` 与 `navigationSplitOptions` **不能同时存在**于同一配置块（静态规则 S13）。
- 开启后不能混用 Router 与 Navigation 两种路由框架。
- `relatedPage` 只支持静态页面，不能传动态参数。
- 自由多窗模式下平行视界不生效。
- `NavDestination.preferredOrientation` 在平行视界下失效，改用 `window.setPreferredOrientation`。

### 四个高频配置错误

1. **展开态不分栏**：折叠展开后屏幕接近方形，只配 `wideWindowMode`（要求高/宽 ≤ 1.2）
   命中不了，**必须同时配 `squareWindowMode`**。这是"配了但不生效"的头号原因。
2. **分屏后丢分栏**：`navigationSplitOptions`/`routerSplitOptions` 必须带
   `"enableInSplitScreen": true`（API 26），否则分屏后回退成 Stack 全屏。
3. **比例字符串格式**：`wideSplit`/`squareSplit` 的 `ratio` 写作 `"2 | 1"`，
   **竖线前后各要一个空格**，少一个就不生效。
4. **多个 Navigation 时不绑定**：模块内有多个 `Navigation` 时必须用
   `homeNavigationId` + `Navigation.id()` 显式绑定，否则系统不知道该对谁分栏。

标 API 26 的字段在低版本设备上配置后不生效且系统会报错，注意目标 API 版本。

分栏后 UI 截断：开 `enableReducedContainerSize`（lpx 基准、断点、windowRect 三者同时减半），
或按自适应布局改造。该开关在退出分栏时自动失效。

### 两种分栏模式：`mode`

`mode` 决定左右两栏的行为，**是 number 不是字符串**（API 26）：

| `mode` | 名称 | 行为 |
|---|---|---|
| `0` | 购物模式 | 左右两栏都能发起路由跳转，右侧内容可迁移到左侧 |
| `1` | 导航模式 | 左侧固定为主页，跳转只发生在右侧 |

两个模式各有一个"开小口子"的字段，**互为反向、不能配反**：

- `pagePairs`（仅 `mode: 1`）：在导航模式里指定若干页面对走购物行为。
  `[{ "from": "Index", "to": "DetailPage" }]`，`"*"` 表示任意页面。
- `transPages`（仅 `mode: 0`）：在购物模式里指定若干页面走导航行为（新页直接替换右侧）。
  `["ProfilePage"]`。

配反了不会报错，只是那条规则永远不命中——`mode: 1` 下配 `transPages` 等于没配。

### 页面标识取什么值，取决于路由框架

`homePage` / `relatedPage` / `fullScreenPages` / `pagePairs` / `transPages` 这五个字段
都是页面标识，**同一个字段在两种路由下取值完全不同**：

| 路由框架 | 取值 | 例 |
|---|---|---|
| Router | `main_pages.json` 里注册的完整路径 | `"pages/DetailPage"` |
| Navigation | `NavDestination` 的 `name` 属性值，**不是路由路径** | `"DetailPage"` |

`homePage` 在 Navigation 下多一个特例：可以填 `"navBar"`，表示用 Navigation 自身的
导航栏区域作为左栏。其余四个字段没有这个特例。

### 分割线颜色 `splitDividerColor`

`{ "light": "#FFE5E5E5", "dark": "#FF303030" }`，八位十六进制 `#AARRGGBB`，
**AA 是透明度且不能省**——写成六位的 `#E5E5E5` 不生效。API 26。

### 分设备差异化配置

顶层按设备类型分段，`common` 提供基础值，具体设备段与之**合并**（不是替换）并覆盖同名字段：

```json
{
  "common":  { "displayModeOptions": { "wideWindowMode": "navigationSplit",
                 "navigationSplitOptions": { "homePage": "navBar", "relatedPage": "DetailPage" } } },
  "tablet":  { "displayModeOptions": {
                 "navigationSplitOptions": { "enableReducedContainerSize": true } } }
}
```

优先级：`phone` / `tablet` 均高于 `common`。只想给平板开某个开关时，
不要把整段配置复制一遍——只写差异项，其余从 `common` 继承。

---

## 资源限定词

同一份代码在不同设备上取不同的图片、尺寸、字符串，靠资源目录而不是代码分支。

- **所有自定义资源必须在 `base` 目录定义默认值**。限定词目录只放差异项，
  base 缺了会在没有匹配目录的设备上运行时异常。
- 只对真正需要差异化的资源建限定词目录，不要为每个设备复制一整套。
- 优先用系统资源 `$r('sys.type.id')`——它自动适配深浅色与设备类型，省掉一批自定义。
- `rawfile` **不参与**限定词匹配，放进去的文件所有设备拿到的都是同一份。
- 引用方式：应用资源 `$r('app.type.name')`，系统资源 `$r('sys.type.resource_id')`。

限定词目录的具体命名规则查官方文档，**不要凭记忆拼目录名**——
`tablet-dark-xxldpi` 这类组合写错一个片段就静默不匹配，退回 base，问题极难定位。

---

## 完整案例

需要看可落地的修复代码时：`../references/cases/bug-fix-size-layout.md`（16 案例，按 SIZE/LAYOUT 分类带 ID：内容截断(SIZE-01~09)、挤压、GridRow 降列(LAYOUT-01)、Stack 遮挡(LAYOUT-02)、分屏图片截断(LAYOUT-03)、Flex 小屏重叠(LAYOUT-04)、Navigation 路由空白(LAYOUT-05/06)、侧边 Tabs 间距(LAYOUT-07)，每个含根因分析与多方案对照）。
