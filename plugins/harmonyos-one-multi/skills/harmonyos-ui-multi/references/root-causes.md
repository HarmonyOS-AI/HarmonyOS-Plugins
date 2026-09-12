# 根因库

多设备适配缺陷的症状 → 根因 → 修法，去重后现 **63 条**。

## 怎么用

1. 用户口述症状 → 按症状列匹配，定位根因与修法
2. 修复后先执行基本编译；设备运行、截图判断和验证证据由调用方负责
3. 需要看可落地的修复代码或完整正反例时 → 对照 `cases/` 目录的案例库（按域分文件）：
   `cases/bug-fix-avoid-areas.md`（安全区避让 12 场景）、`cases/bug-fix-fold-form.md`（折展 8 场景）、
   `cases/bug-fix-orientation.md`（方向 9 案例）、`cases/bug-fix-size-layout.md`（尺寸布局 16 案例）。
   本表是根因索引，案例库是完整正反例代码——两者互补，不是替代。

不要通读本文。它是查表用的，一次只看命中的那几行。

---

## RC-size 布局与尺寸（22 条）

| ID | 症状 | 根因 | 修法 |
|---|---|---|---|
| **size-01** | 小方形屏（阔折叠外屏）主内容被挤压到几乎不可用 | 底部栏/标题栏用固定 `height`，或固定 `padding`/`margin`/包裹层高度占位；小屏上这些固定占位吃掉了大半屏高 | 按高度断点收起底部栏；固定占位改成随断点取值 |
| **size-02** | 内容超出父组件被截断，且滚不动 | 三种：① 主体没有 `Scroll` 承接；② 用 `Row`/`Column`/`Stack` + `ForEach` 渲染长列表；③ 外层 `maxHeight`/`sheetMaxHeight` 限死了高度 | 主体套 `Scroll`；长列表换 `List`/`LazyForEach`；去掉过紧的高度上限 |
| **size-03** | `AlphabetIndexer` 索引条在高度不足时挤成一团 | 设了 `.autoCollapse(false)`，高度不够也不折叠 | 删掉该设置或改 `true`，让系统按可用高度自动折叠 |
| **size-04** | Row/Column/Flex 子组件被截断，该省略的没省略、该完整的被压扁 | ① 都不设 `flexShrink`，全部参与等比收缩；② 容器缺主轴尺寸约束（Row 缺 `width`、Column 缺 `height`），`flexShrink` 根本不触发；③ 缺 `displayPriority`，超宽时截断而非按优先级隐藏；④ 已有 `displayPriority`，仍按宽度计算 `visibleCount` 并 `slice` / `filter`，两套显隐逻辑冲突；⑤ 误以为同优先级会从尾部逐项隐藏，因而错误弃用 `displayPriority` | 给必须完整的组件设 `flexShrink(0)`、可压缩的设 `1`；补容器主轴尺寸；按重要性隐藏时完整渲染子节点，只用 `displayPriority` 决定显隐，不再手算宽度和可见数量；同优先级子节点同时显隐，多个元素需要整体显隐时先封装为一个直接子组件再设置优先级（对 `Row`/`Column`/`Flex(单行)` 直接子节点生效，多行换行模式下不生效，子节点需 `flexShrink(0)`） |
| **size-05** | 图片在大屏被拉伸变形 | ① 只设 `width` 不设 `height`，大屏下按原图比例把高度也放大；② `width('100%')`+`height('100%')`+`ImageFit.Cover` 且容器高度是固定像素算出来的，Cover 强行拉伸裁剪；③ 直接用了 `ImageFit.Fill` | 用 `aspectRatio` 锁比例，或给高度加 `constraintSize` 上限；`Fill` 换 `Cover`/`Contain` |
| **size-06** | 用户调大"显示大小"后断点算错、布局跳档；退出自由多窗后断点不刷新 | 只监听 `windowSizeChange`。DPI 变化时窗口物理尺寸可能没变，`windowSizeChange` 根本不触发；就算触发了，回调里 `getWindowDensityInfo()` 拿到的也还是旧 DPI，px→vp 换算全错 | 断点一律取 `getWindowWidthBreakpoint()` 系统返回值，不要自己用 px 换算推断点；凡有 vp 参与判断的地方，`windowSizeChange` 与 **`systemDensityChange` 两个监听都要挂** |
| **size-07** | 启动页图标被截断、显示不全 | `module.json5` 的 `startWindowIcon` 用了超大尺寸图（**超过 256×256** 即被按上限裁切）；简易启动页按原始尺寸居中显示且**不缩放** | 换成 ≤256×256 的图标资源，别为单一机型全屏尺寸设计；需要复杂启动画面时改用增强启动页 `startWindow`（API 19+） |
| **size-08** | `constraintSize({maxWidth})` 完全不起作用，内容照样溢出 | 外层组件**没有显式宽度**——宽度由子内容撑开时 `maxWidth` 没有基准可约束。高发于 `@CustomDialog`、`bindContentCover` 的 `@Builder`、`promptAction.openCustomDialog` 的根组件（都不在有宽度约束的父容器内） | 给根组件补 `.width('100%')` 或 `layoutWeight`，再用 `constraintSize` 限上限 |
| **size-09** | 旋转后尺寸计算用了旧值 | `display.on('change')` 的回调参数只有 display id，不带宽高；回调里再 `getDefaultDisplaySync()` 时属性可能还没更新 | 尺寸变化一律听 `windowSizeChange` 并用回调参数，不在 display 回调里主动查 |
| **size-10** | 局部容器变窄了，`GridRow` 却不降列 | 断点参考系绑到了窗口宽度，而组件自身宽度才是要跟的量（**注意方向**：整页布局要 `WindowSize`，局部容器反而要 `ComponentSize`，两者不能一刀切） | 明确这段栅格跟谁：跟窗口用 `WindowSize`，跟自身用 `ComponentSize`，别混 |
| **size-11** | `Stack` 底部元素盖住主内容 | 用 `Stack` 当根容器 + `alignContent: BottomStart` 定位底部栏，层叠必然覆盖 | 根容器换 `Column`，底部栏作为兄弟节点；确需层叠时给主内容留出等高 padding |
| **size-13** | `Flex` + `SpaceBetween` 在小屏上上下区域重叠 | `SpaceBetween` 要求子内容总高 ≤ 容器高才能把子项推到两端；小屏上区超高后它直接失效 | 上区套 `Scroll` 或 `layoutWeight(1)`，别依赖 `SpaceBetween` 兜底 |
| **size-14** | Navigation 路由跳过去是空白页 | 目标页 `build()` 直接返回 `Column`，没有用 `NavDestination()` 包装——框架识别不了 | 目标页根容器必须是 `NavDestination` |
| **size-15** | 宽屏下内容区一片空白 | `Navigation` 包在分区容器**外面**了。Navigation 把直接子组件当 navBar 内容，分区容器整体被当成了 navBar，它的内容区自然无法独立显示 | 反过来：分区容器（`SideBarContainer`/`Tabs`）在外，`Navigation` 放进它的内容区 |
| **size-16** | 大屏两侧大片留白，内容缩在中间一条 | 容器宽度不随窗口伸展；或整页仍是单列堆叠，没有重复/分栏变体 | 先判页面类型再选模式：同质内容加列数、有主从关系走分栏、单列内容用 `GridCol` span+offset 限宽居中 |
| **size-17** | 横屏下元素均分比例错乱 | 元素宽度写死，没按断点重算数量与间距 | 用断点取值决定列数与 `space`，不要固定宽度硬排 |
| **size-18** | `Swiper` 在宽屏只显示一张且被拉满、多张紧贴无间距，或被 `maxWidth` 限宽后缩成中间一条两侧留白 | `displayCount` 默认 1；`itemSpace` 不设时多张之间没间距；`prevMargin`/`nextMargin` 只管视口边缘露出，**不是项间距**；把轮播当"一张图"加限宽是归类错误——轮播是同质内容的重复模式 | 五个属性一起按断点设：`displayCount` 1/2/3/3、`itemSpace` 0/12/16/16vp，并联动 `indicator`（多张可见时应关掉）、`prevMargin`、`nextMargin`；去掉 `Swiper` 自身的 `maxWidth`，防变形用 `ImageFit`/`aspectRatio` |
| **size-19** | 横屏弹窗的关闭按钮跑出屏幕 | 弹窗写死高度，横屏窗口高度不够 | 改 `bindSheet` + `detents`，或限制最大高度 `'90%'`；小方形屏上内容区还要套 `Scroll` |
| **size-20** | 扫码框太小/有白条；视频直播两侧黑边或被压缩 | `XComponent` 的 Surface 用了固定尺寸，不随窗口变化更新 | 扫码框用 `width('100%').aspectRatio(1)`；视频监听窗口尺寸变化后重设 Surface 尺寸，横屏保持 16:9 |
| **size-21** | 大屏/平板上 `GridRow` 一直停在 md 的列数，`GridCol` 的 `lg`/`xl` 的 `span` 完全不生效 | `GridRow.breakpoints.value` 被写成两个值（`['600vp','840vp']`），lg/xl 两档边界缺失、**永不触发**；或漏写 `GridRow.columns`，`span` 找不到分母、退化成按内容排布 | `value` 写完整四值 `['320vp','600vp','840vp','1440vp']`（每个元素必须带 vp 单位）；`columns` 显式声明各档总格数 `{ sm:12, md:12, lg:12, xl:12 }`（详见 `domains/size-layout.md`「GridRow 配置」） |
| **size-22** | LG 侧边 Tabs 的页签间距太小、视觉上挤在一起 | 切换 Tabs 容器方向和尺寸后，没有在自定义 `tabBar` 的页签项根节点设置上下边距 | 参考 `cases/bug-fix-size-layout.md` 的 LAYOUT-07，在 LG 下为每个页签项根节点同时设置 `top`、`bottom` margin；数值由模型结合实际布局判断并验证，保持 `BarMode.Scrollable` 处理溢出 |
| **size-23** | 宽屏（平板/折叠展开/宽预览）页面变成左半内容、右半一片空白 | `Navigation` 未显式设置 `.mode()`，而其默认值是 `NavigationMode.Auto`：窗口宽 ≥600vp 自动切 Split 双栏，右侧详情栏无路由而空白；手机宽度（<600vp）一直是 Stack，单设备工程从未暴露 | 分栏前提不满足时显式 `.mode(NavigationMode.Stack)` 固定单栏基线，大屏改用重复（增列）/缩进自适应；若用户确认采用分栏，用 `onNavigationModeChange` 在切到 Split 时推默认路由，避免右栏空白（详见 `domains/size-layout.md`「分栏布局要点」） |
| **size-24** | 平板（lg）上列表/卡片仍是 md 的两列密度，换更宽设备也不变 | 列数序列配成 md 与 lg 持平（如 `span` sm 12 / md 6 / lg 6 / xl 4），递增被推迟到 xl；xl 要求窗口 ≥1440vp，覆盖设备清单里没有任何设备到得了（最大约 1137vp，全在 lg） | 列数逐档递增（基线 1 → 1/2/3）；md→lg 持平仅在项数固定已排满、最小宽度限制等内容侧理由成立时允许，并把理由写入说明；交付前把各档配置换算成列数序列自查形状（见 `domains/size-layout.md`「列数递增原则」） |
| **size-25** | 自定义的 `GridRow` 断点值不生效：断点切换位置与默认一致、xl 档永不触发；窄窗口（<320vp）下卡片挤成 12 个一排；短列表（只有两三条）整体悬在视口中间而非顶部对齐 | ① `breakpoints.value` 含非法元素——格式必须是「数字+vp」，`'0'`/`'600'` 这类无单位值导致**整个数组静默回退默认** `['320vp','600vp','840vp']`（无 xl 档），编译运行都不报错；② 默认首值 320vp 使 xs 档 [0,320) 真实存在，`span` 对象未写 `xs` 时没有前档可继承、落到默认值 1；③ 滚动容器未撑满父容器或宿主主轴对齐非 Start，短列表被按内容尺寸居中放置 | ① 每个元素带 vp 单位的完整四值 `['320vp','600vp','840vp','1440vp']`；② `GridCol.span` 从 `xs` 显式给起（通常与 sm 基线一致）；③ 首选滚动容器撑满可用空间（`layoutWeight(1)`/`height('100%')`），其次父容器 `justifyContent(FlexAlign.Start)`；`Scroll` 加 `.alignSelf(ItemAlign.Start)` 实证有效但不通用，加完必须在目标形态验证顶部对齐（详见 `domains/size-layout.md`「GridRow 配置」） |

（size-12「分屏下布局错乱」已并入 RC-window 的 window-01，ID 不复用。）

---

## RC-window 窗口形态（6 条）

| ID | 症状 | 根因 | 修法 |
|---|---|---|---|
| **window-01** | 分屏下图片截断、文字挤压、组件遮挡 | 没按断点调整布局，也没设小窗口布局变体 | 分屏窗口宽度会落到 sm/md，按断点走已有的响应式分支即可——**分屏适配的本质是断点适配**，几何修法全在 RC-size |
| **window-02** | `startAbility` 后目标页全屏显示，分屏不生效 | ① 未传 `StartOptions` 或没指定 `windowMode`（不传就是全屏启动）；② `module.json5` 没声明 `"split"`，或写成不存在的 `"splitScreen"`；③ 用了不存在的 `WINDOW_MODE_FLOATING` 枚举 | `startAbility` 必传 `StartOptions`，`windowMode` 取 `WINDOW_MODE_SPLIT_PRIMARY`/`_SECONDARY`；`supportWindowMode` 补 `"split"` |
| **window-03** | 分屏已存在时再次启动数据不更新；或分屏页面接不到参数 | 目标 Ability 没实现 `onNewWant`（singleton 复用时不走 `onCreate`）；页面 `@Entry` 没声明 `useSharedStorage: true`，`@LocalStorageLink` 绑不上 | 实现 `onNewWant` 更新 `LocalStorage`；页面用 `@Entry({ useSharedStorage: true })` |
| **window-04** | 沉浸式页面进入悬浮窗后顶部按钮点不到 | 悬浮窗顶部有系统控制条，与隐藏了状态栏的应用 UI 重叠 | 监听 `windowStatusChange`，`FLOATING` 时取 `getWindowAvoidArea(TYPE_SYSTEM).topRect.height` 转 vp 作顶部 padding，其余形态归零 |
| **window-05** | 视频/游戏悬浮窗竖着显示、内容不全 | 悬浮窗默认竖向；只配了 `preferMultiWindowOrientation` 或只调了 API，两者必须成对 | `module.json5` 配 `"preferMultiWindowOrientation": "landscape_auto"`，并成对调 `enableLandscapeMultiWindow()` / `disableLandscapeMultiWindow()` |
| **window-06** | 自由窗口拖到很小后布局崩溃 | 没设窗口最小尺寸，窗口可被拖到断点体系覆盖不到的尺寸 | `module.json5` 设 `minWindowWidth`/`minWindowHeight`（vp），或运行时 `setWindowLimits()`；下限值要落在 sm 分支真实可用的范围内 |

---

## RC-avoid 安全区与键盘（12 条）

| ID | 症状 | 根因 | 修法 |
|---|---|---|---|
| **avoid-01** | 顶部标题栏被状态栏压住 | 没动态取状态栏高度，或直接硬编码了一个值——状态栏高度 32~48vp 因设备而异 | 取 `TYPE_SYSTEM` 的 `topRect.height` 作为顶部 padding，并监听 `avoidAreaChange` 持续更新 |
| **avoid-02** | 挖孔遮住内容或点不动 | 用了 `ignoreLayoutSafeArea()` 全屏后就没再避让；横屏时挖孔跑到左右两侧，只处理顶部不够 | 取 `TYPE_CUTOUT` 四个方向分别处理。**左上用加、右下用"屏幕尺寸减"**，这一步最容易写反 |
| **avoid-03** | 底部按钮被导航指示器盖住 | 开了 `setWindowLayoutFullScreen(true)` 但没取 `TYPE_NAVIGATION_INDICATOR`；或底部栏用固定 `margin-bottom` 硬凑 | 取 `TYPE_NAVIGATION_INDICATOR` 的 `bottomRect.height` 做底部 padding。注意 **`TYPE_SYSTEM` 的 bottomRect 恒为 0**，指示条必须单独查 |
| **avoid-04** | 状态栏与标题栏之间有色差间隙；列表滚不到底 | padding 加错了层：顶部 padding 加在外层容器上而不是需要延伸背景色的标题栏上；底部 padding 加在外层 `Stack` 上而不是 `Scroll` 上 | 需要延伸背景色的那个子组件自己加 padding；滚动避让加在 `Scroll` 上 |
| **avoid-05** | 折叠/展开后标题栏与状态栏重叠 | 只在 `onWindowStageCreate` 里读了一次避让区存进 `AppStorage`，之后再没刷新过 | 注册 `avoidAreaChange` 持续更新。**只读一次是最常见的写法错误** |
| **avoid-06** | 折叠/旋转后 padding 先跳一下再变正确 | 在 `windowSizeChange` 或 `display.on('change')` 回调里**主动调** `getWindowAvoidArea()`——这两个回调都早于系统 UI 布局更新完成，拿到的是旧值 | **只信 `avoidAreaChange` 回调参数**，不在任何其它回调里主动查询（覆盖三个同源案例） |
| **avoid-07** | 键盘弹起后输入框/底部工具栏被遮挡 | ① `RelativeContainer` + `alignRules` 锚定布局，键盘弹起时不会自动调整；② 没设 `KeyboardAvoidMode.RESIZE`，默认模式不压缩可视区；③ 内容区固定高度且不可滚 | `setKeyboardAvoidMode(RESIZE)`（必须在 `loadContent` 回调后调），布局换 `Column` + `Scroll` |
| **avoid-08** | 竖折态键盘拉起后引用视图被截断 | 竖折屏高本就有限，键盘再占掉底部，引用视图空间被压没 | 按高度断点降级引用视图（缩行数或改单行摘要），别让它和输入框抢固定空间 |
| **avoid-09** | 键盘弹起时底部工具栏内部比例失调 | 给整个底部工具栏设了 `constraintSize({maxHeight})`，引用视图与输入框共享这块固定空间 | 约束加到引用视图上，输入框保持自然高度 |
| **avoid-10** | 短视频/沉浸式页面底部没有真正沉浸 | `Tabs` 默认栏（`barHeight: 56`）占了底部空间；`padding({bottom})` 加在 `Stack` 外层只是把整体上推，不是沉浸 | 隐藏 Tabs 默认栏、去掉外层 padding，只给底部**交互元素**加自定义栏高 padding |
| **avoid-11** | 横屏时输入法关不掉 | 横屏下系统键盘的关闭区域超出屏幕，失焦事件也没触发 | 横屏时给 `TextInput` 旁加显式关闭按钮，调 `inputMethod.getController().stopInputSession()` |
| **avoid-12** | 自定义键盘（`.customKeyboard(builder)`）在宽屏/展开态右侧大片留白，或底部留白、整体过高 | builder 内硬编码了设备宽度（如 `width(459)`，常是某机型外屏宽）且外层 `alignItems(HorizontalAlign.Start)` → 宽屏面板（展开态可达 ~711vp）右侧空一大块；按键区固定 `height` 没填满根 `Column` → 底部空隙；根组件写死 `height` 不随屏高变化 → 整体过高/过矮。手机态面板更窄（内容被裁/填满）所以右侧留白只在宽屏暴露 | 三个症状各对症，不要混用：右侧留白→内容改 `width('100%')` 铺满并去掉左对齐（铺满是自定义键盘的标准形态，直接做即可，不必询问用户）；底部留白→按键区固定高度改 `layoutWeight(1)` 填满剩余高度；整体过高→键盘高度按屏高动态算（`display.getDefaultDisplaySync().height` 经 `px2vp()` 后取比例，如屏高/2），不要写死。完整正反例见 `cases/bug-fix-avoid-areas.md` 场景13 |

**`List` 与 `Scroll` 的差别值得单独记**：`List` 自带键盘避让，`Scroll` 要手写三件套。
选型时选 `List` 能少写三段代码。

---

## RC-fold 折展与悬停（10 条）

| ID | 症状 | 根因 | 修法 |
|---|---|---|---|
| **fold-01** | 悬停态布局完全没生效 | ① 没注册 `foldStatusChange`/`foldDisplayModeChange`；② 注册了但 `build()` 里没有悬停分支；③ **只用 `pageWidth >= 600` 判多栏**——宽度识别不出悬停态 | 悬停判定必须是**折叠状态 + 横屏**两个条件；布局分支单独拆出来 |
| **fold-02** | 方向反复切换或偶发反向 | `onAreaChange`、`foldStatusChange`、`foldDisplayModeChange` 多个回调都调 `setPreferredOrientation`，互相覆盖；且切换无延迟保护 | 方向决策收敛到**单一入口**；切换加 120/220ms 延迟调度 + 去重；退出悬停不要立刻解锁 |
| **fold-03** | 竖折痕设备左右折叠时没按语义转 90° | 方向决策依赖当前 `rootWidth/rootHeight` 比较，而旋转过程中轴会互换，比较结果不稳定 | 方向绑**折痕轴**而不是视口宽高比 |
| **fold-04** | 固定竖折痕设备被误判成横折痕 | 折痕轴只做了一次 `width/height` 比较；旋转过程中坐标转换结果不稳定 | 三级检测：轴比初筛 → 几何评分 → 方向锁定；已知固定折痕轴的设备不因旋转改判 |
| **fold-05** | 折痕避让位置偏了，或内容压在折痕上 | ① 用固定 50% 切分而不读 `getCurrentFoldCreaseRegion()`；② 折痕是**全局坐标**，直接拿来算页面布局；③ 把 `16/40vp` 当成了分区边界锚点 | 读真实折痕几何，扣掉根节点 `globalPosition` 偏移再用；**16/40vp 是内容与折痕之间的安全间距，不是分界线位置** |
| **fold-06** | 悬停态黑屏，布局只剩 `Blank` | 折痕轴误判叠加折痕厚度算错，避让区吃掉了整个内容区 | 折痕厚度做上限钳位（超过屏高 35% 视为异常值） |
| **fold-07** | 折叠/展开后跳回首页、滚动位置丢失、输入被清空、视频进度重置 | ① 形态切换触发 Ability 重建，`module.json5` 的 `configuration` 没声明自处理 `screenSize`/`orientation`；② 没有跨形态快照机制；③ 恢复只挂在单一触发点；④ `autoPlay(true)` 抢跑覆盖了业务的暂停态 | `configuration` 加 `"screenSize"` `"orientation"`，改由 `onConfigurationUpdate` 通知；快照用 `foldStatusChange`、布局用断点；恢复任务加序列号防旧回调，且必须可重入 |
| **fold-08** | 页面反复进出后回调重复触发、状态串态 | `display.on`/`window.on` 没和页面生命周期成对回收；临时方向锁离场未清理 | `aboutToDisappear` 里逐个 `off()`，且**必须传回调引用**——裸 `off('event')` 会连别的组件的监听一起摘掉 |
| **fold-09** | 切换内外屏后 UI 还是切换前的尺寸；展开后内容只占半屏 | 没监听窗口尺寸变化，断点没更新；或多个页面重复注册、注销导致状态源失效 | `BreakpointSystem.register()` 只在 `loadContent` 加载的入口页 `aboutToAppear()` 注册一次，V2 业务页用 `@Local` 引用统一状态；入口页 `aboutToDisappear()` 注销 |
| **fold-10** | 外屏图标按钮和内屏一样大，外屏显得拥挤 | 布局没区分内外屏尺寸，内屏的大尺寸元素直接搬到小方形外屏 | 按**换算后的 vp 宽度**判紧凑模式（阈值 `COMPACT_MAX_VP = 350`，见 `domains/fold-form.md`），不要只凭折叠状态，也不要拿某台设备的实测值当阈值；折叠状态变化时重算 |

**一条贯穿性的规矩**：布局用断点驱动，`foldStatus` 只用来做快照与焦点恢复。
用 `foldStatusChange` 直接驱动布局会拿到还没更新的窗口尺寸，导致两次重排与闪烁。

---

## RC-orient 方向与旋转（9 条）

| ID | 症状 | 根因 | 修法 |
|---|---|---|---|
| **orient-01** | 折叠屏展开态横屏用着用着被强制竖屏 | 用 `deviceInfo.deviceType === 'phone'` 判手机后锁竖屏——**折叠屏的 deviceType 也返回 `'phone'`** | 用 `display.isFoldable()` 区分折叠设备；或直接按断点/窗口最小边判，不按设备类型判 |
| **orient-02** | Tabs + Swiper 的短视频页方向锁死或错乱 | ① `Tabs` 懒创建导致 `aboutToAppear` 只触发一次；② `Swiper.onChange` 里重复锁方向；③ 没区分设备类型 | 方向控制放 `Tabs.onChange`，不放子组件生命周期 |
| **orient-03** | 分屏/悬浮窗下 `setPreferredOrientation` 不生效 | 系统在分屏、悬浮窗、自由多窗下**忽略**应用旋转策略。调用不报错但无效，是系统级行为，绕不过去 | 先判窗口模式；这些模式下不要依赖方向锁，改用布局适配 |
| **orient-04** | 视频/直播页退出后方向没恢复，或折叠展开后返回首页被强制竖屏 | `setPreferredOrientation` 是窗口级状态；未恢复策略，或把进入时的 `display.rotation` 物理方向快照翻译成固定方向恢复，折叠开合后快照已过期 | 进入时保存 `getPreferredOrientation()` 的**策略枚举**并在退出时恢复；全局策略按 `window-rotation-policy.md` 与产品需求选择，不在案例中硬编码。`UNSPECIFIED(0)` 仅在原策略确实为 0 时恢复，不作通用重置值 |
| **orient-05** | 折叠开合时布局闪烁两次 | 在 `foldStatusChange` 里更新布局，但此刻窗口尺寸还没变；随后 `windowSizeChange` 又算一遍 | 布局响应式一律听 `windowSizeChange`/断点，`foldStatusChange` 不用于布局 |
| **orient-06** | 调大"显示大小"后应用被强制竖屏 | 官方最佳实践推荐的 `348vp` 阈值判断依赖 `px2vp()`，而 DPI 一变换算结果就变。**Mate 60 Pro 实测：DPI 480→630，最小边 vp 从 390 跌到 320**，跌破阈值 | 阈值改用**物理像素**判定（约 520px 并留余量），或改用系统断点返回值。这条推翻了官方示例代码 |
| **orient-08** | 折叠内屏竖屏下 Navigation 分栏挤成一团 | `Split` 只看**宽度**：内屏竖屏宽度够（Mate X5 约 2204px）就触发分栏，但真正不够的是高度 | 分栏条件同时看宽高断点，竖屏内屏回退单栏 |
| **orient-09** | 横屏仍按竖屏比例居中，大量空白；横屏页面滚不动 | 没定义横向断点变体；`List`/`Scroll` 没设高度，父容器高度被内容撑开，手势识别不了 | 补横屏布局分支；`List` 给 `height('100%')` 或 `layoutWeight(1)` |
| **orient-10** | 横竖屏切换白屏 / ANR / 掉帧 | 旋转触发全量重建，或布局计算阻塞主线程 | 耗时初始化移到 `taskpool`；旋转前后内容不变的子组件加 `@Component({freezeWhenInactive: true})` |

---

## RC-font 字体与图标（4 条）

| ID | 症状 | 根因 | 修法 |
|---|---|---|---|
| **font-01** | 大屏/展开态字体图标异常放大 | **`lpx` 单位**——它按屏幕宽度等比缩放，宽屏下同样的数字对应更大的显示尺寸。这是大屏字体变大的头号原因 | 字号用 `fp`、尺寸用 `vp`；需要随断点变化时按断点取值，别让单位替你做缩放 |
| **font-02** | 不同密度屏幕上视觉大小不一致 | 用 `px` 做字体或尺寸——物理像素不随密度和系统字号缩放 | 全部换 `fp`/`vp`。排查：`grep -rn --include="*.ets" "'[1-9][0-9]*px'"` |
| **font-03** | 字号小到看不清，上架被打回 | 手机、折叠屏或平板字号低于 8vp 基线 | 至少 8vp，正文推荐 12vp 以上 |
| **font-04** | 用户开了系统超大字号后，大屏上文字撑破容器、按钮串行 | 没有限制 `Configuration.fontSizeScale`，系统缩放系数被无条件放大到布局上；大屏本来就宽松，放大后更容易顶破固定高度的容器 | 在 `onConfigurationUpdate` 里读 `fontSizeScale` 并按业务上限钳位；承载文字的容器不要给固定高度，让它能随字号长高 |

`display.getDefaultDisplaySync().width` 返回的是 **px 不是 vp**，
与 vp 阈值比较前必须先 `px2vp()`。这个坑同时坑到字体与紧凑布局两处。

---
