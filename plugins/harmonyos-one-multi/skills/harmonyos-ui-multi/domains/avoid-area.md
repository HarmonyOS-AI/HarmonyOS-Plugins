# 域：安全区与键盘避让

覆盖状态栏/导航条/挖孔避让、沉浸式、软键盘避让。

## 症状 → 本文档

| 症状 | 查本文 |
|---|---|
| 全屏、占满整个屏幕、内容延伸到状态栏/导航条区域 | [沉浸式](#沉浸式) |
| 按钮被状态栏/导航条/挖孔盖住 | [避让的两种做法](#避让的两种做法) |
| 输入框被键盘遮挡 | [键盘避让](#键盘避让) |
| 自定义键盘（customKeyboard）右侧/底部留白、整体过高 | [自定义键盘布局（customKeyboard）](#自定义键盘布局customkeyboard) |
| 列表滚不到底、内容被压 | [padding 加在哪一层](#padding-加在哪一层) |
| 用了 `KeyboardAvoidMode.PAN`（静态规则 S5 会拦） | [两种模式，行为完全不同](#两种模式行为完全不同) |
| 偶发拿到过期避让区数值 | [别在任何其它回调里主动查](#别在任何其它回调里主动查) |

根因案例查 `../references/root-causes.md` 的 **RC-avoid** 段。

---

## 避让区是什么

官方定义：**"在避让区域内，应用窗口内容被遮挡且无法响应用户点击事件"**。

这句话就是判定口径 —— 可交互内容与避让区相交即缺陷，不需要主观判断。

五种类型（`AvoidAreaType`）：

| 值 | 类型 | 说明 |
|---|---|---|
| 0 | `TYPE_SYSTEM` | 状态栏等系统默认区域；悬浮窗下是三点控制栏。**它的 `bottomRect` 恒为 0** |
| 1 | `TYPE_CUTOUT` | 挖孔/刘海 |
| 2 | `TYPE_SYSTEM_GESTURE` | 侧边返回手势区 —— **官方注明当前所有设备均无此区域**，不必采集 |
| 3 | `TYPE_KEYBOARD` | 固定态软键盘 |
| 4 | `TYPE_NAVIGATION_INDICATOR` | 底部导航条 / 三键 |

`AvoidArea` 结构是四个 Rect：`leftRect` / `topRect` / `rightRect` / `bottomRect`。
其中 `visible` 字段**官方写明"无实际意义，暂不支持使用"**，不要读它。

**底部指示条必须单独取 `TYPE_NAVIGATION_INDICATOR`**：很多人以为
`TYPE_SYSTEM` 的 `bottomRect` 会给出指示条高度，实际它恒为 0，
按它算出来的底部 padding 永远是 0。

### 四方向的 padding 公式，一半人会写反

| 方向 | padding 计算 |
|---|---|
| 上 | `topRect.top + topRect.height` |
| 左 | `leftRect.left + leftRect.width` |
| **右** | **`屏幕宽 − rightRect.left`** |
| **下** | **`屏幕高 − bottomRect.top`** |

**左上用加法，右下用"屏幕尺寸减"**。右下方向直接拿 `rect.width`/`rect.height`
当 padding 是最常见的写法错误——横屏挖孔跑到右侧时立刻显形。

四方向检测只在游戏、全屏视频、AR 这类必须铺满全屏的场景才需要。
普通应用用 `expandSafeArea` 就够了。

---

## 避让的两种做法

### 1. 组件级：expandSafeArea

让**背景**延伸进避让区，**内容**留在安全区内。这是绝大多数场景的正确答案。

```typescript
Column() { /* 内容 */ }
  .expandSafeArea([SafeAreaType.SYSTEM], [SafeAreaEdge.TOP])
```

**`SafeAreaEdge` 的成员是 `TOP` / `BOTTOM` / `START` / `END`，不是 LEFT/RIGHT。**
华为 avoid-areas 的参考文档在这一点上写错了，照抄会编译不过。SDK 实证：

```bash
grep -n "enum SafeAreaEdge" -A 40 <SDK>/ets/component/common.d.ts
# → TOP = 0, BOTTOM = 1, START = 2, END = 3
```

两层定式：**外层 `expandSafeArea` 延伸背景 + 内层 padding 保内容**。

元素级判据很简单：**可交互元素不延伸，纯展示元素可以延伸**。
按钮、输入框延伸进避让区就是缺陷（被遮挡且点不到）；背景图、装饰色块延伸没问题。

### 2. 页面级沉浸：ignoreLayoutSafeArea + 容器自身 padding

要求**内容（不只背景）铺进底部导航条/状态栏区域**、且只对单个页面生效时，首选声明式：

```typescript
Column() { /* 页面内容 */ }
  .ignoreLayoutSafeArea([LayoutSafeAreaType.SYSTEM], [LayoutSafeAreaEdge.BOTTOM])
  .height(LayoutPolicy.matchParent)
  .padding({ bottom: this.avoidBottom })   // 避让高度经 avoidAreaChange 维护，'Npx' 字符串
```

延伸与避让在**同一节点同帧生效**，全屏/分屏/悬浮窗/横竖屏切换自动跟随，不需要进出页面
做任何事。`setWindowLayoutFullScreen(true)` 是**窗口级全局开关**：单页沉浸用它需要进出
页面开/关与状态恢复，且把避让高度串进 Tabs `barHeight` 这类**跨组件异步**状态链时，更新
不同步会让底栏沉进导航条（文本被遮挡、重叠断言失败）。单页场景优先本节的容器级方案；
窗口级开关只留给需要全局切换沉浸的场合（并遵守 `avoidAreaChange` 纪律）。

### 3. 取值级：getWindowAvoidArea + 动态 padding

需要精确控制时用。避让区高度单位是 **px**，绑到 padding 时用 `'Npx'` 字符串格式，
或先 `px2vp()` 转换再参与算术——**两种写法不能混**，拼出 `'100pxpx'` 是真实发生过的事故。

### 别在任何其它回调里主动查

这是本域最值钱的一条，覆盖三种不同的错误写法：

| 错误写法 | 后果 |
|---|---|
| 只在 `onWindowStageCreate` 读一次存进 `AppStorage` | 折叠/旋转后再不更新，标题栏与状态栏重叠 |
| 在 `windowSizeChange` 回调里调 `getWindowAvoidArea()` | 该回调早于系统 UI 布局完成，拿到旧值 |
| 在 `display.on('change')` 回调里调 `getWindowAvoidArea()` | 同上，表现为 padding 先跳一下再变正确 |

**统一结论：只信 `avoidAreaChange` 回调参数 `opts.area`，
不在任何其它回调里主动查询**。

任何使用 `setWindowLayoutFullScreen(true)` 的全屏页面都**必须**注册 `avoidAreaChange`，
否则设备状态变化后布局不会更新。

### padding 加在哪一层

加错层是背景色间隙与"列表滚不到底"的共同根因：

- 需要**延伸背景色**的那个子组件（如白色标题栏）自己加顶部 padding，
  加在外层灰色容器上会露出色差间隙
- 底部滚动避让加在 **`Scroll`/`List` 上**，加在外层 `Stack` 上只是把整体上推，
  滚到底时内容依然被指示条盖住

顺带两个容易混的概念：`bottomBarMarginBottom`（视觉间距）与
`bottomAvoidHeight`（导航条高度）是两回事，不要合并成一个变量。

### background 与 backgroundColor 不是一回事

- `background()` —— 背景**会**延伸进避让区
- `backgroundColor()` —— 背景**被裁**在安全区内

沉浸式效果做不出来时，先检查用的是哪个。

### 平板自由窗口的标题栏

`expandSafeArea()` 与 `ignoreLayoutSafeArea()` **对自由窗口标题栏无效**。
需要单独用 `setWindowDecorVisible(false)` + `setWindowDecorHeight()`。

---

## 键盘避让

### 两种模式，行为完全不同

`KeyboardAvoidMode` 的**全部**成员：`OFFSET` / `RESIZE` / `OFFSET_WITH_CARET` /
`RESIZE_WITH_CARET` / `NONE`。**没有 `PAN`**（静态规则 S5 会拦，那是 Android 的概念）。

| 模式 | 行为 | 谁被压缩 |
|---|---|---|
| `OFFSET`（默认） | 整个页面上推 | 无 |
| `RESIZE` | 窗口高度变小 | **只有百分比高度或 layoutWeight 的组件**；固定 vp/px 高度永不压缩 |
| `*_WITH_CARET` | 同上，但以**光标**位置为基准 | 输入框很高、光标在中部时用 |

`RESIZE` 模式的常见误解：以为设了 RESIZE 内容区就会自动缩。
实际上固定高度的内容区**不会**被压缩，只有百分比/layoutWeight 的才会。
底部栏用固定高度反而是对的（它需要保持完整）。

`setKeyboardAvoidMode()` **必须在 `loadContent` 回调之后调用**，之前调不生效。

`expandSafeArea([SafeAreaType.KEYBOARD])` **只在 OFFSET 模式下生效**，
RESIZE 模式下完全无效。

### 选 List 能少写三段代码

`List` **内置键盘避让**：键盘弹出时自动把焦点输入框滚进可见区。
`Scroll` 没有，要自己注册 `avoidAreaChange` + 判 `keyboardHeight` + `setTimeout` 延迟滚动。

用 `List` 的布局要点：标题栏放在 List **外面**不参与滚动，List 用 `layoutWeight(1)`
占满剩余空间，**底部按钮放进最后一个 ListItem**，配 `KeyboardAvoidMode.RESIZE`。

反过来，`RelativeContainer` + `alignRules` 的锚定布局在键盘弹起时**完全不会自动调整**，
表单页别用它做根容器。

### 全局默认值必须还原

`setKeyboardAvoidMode()` 是**窗口级**的，影响所有页面。
任何页面改了它，都必须在 `aboutToDisappear()` 中还原成全局默认值 ——
默认值要从 `AppStorage` 里读，**不能硬编码**（不同工程的默认值不同）。

### 收起键盘用 clearFocus

`stopEditing()` 只控制单个绑定的 TextInput；
`clearFocus()` 对所有输入场景有效，包括多输入框页面。

横屏下系统键盘的关闭区域可能超出屏幕，且失焦事件不触发——
横屏输入页要给一个显式的关闭按钮。

### 监听配对

`on('keyboardHeightChange')` 必须配 `off()`。
需要在键盘上方挂工具栏/表情面板/引用预览时才用它，普通避让不需要。

### 自定义键盘布局（customKeyboard）

`.customKeyboard(builder, { supportAvoidance: true })` 的键盘面板尺寸由 **builder 根组件**决定，
和系统键盘是两回事——它的留白/过高不是避让模式问题，是 builder 内部布局问题。

三个高发症状各有对症修法，不要混用：

| 症状 | 根因 | 修法 |
|---|---|---|
| 宽屏/展开态右侧大片留白 | 标题栏/按键硬编码 `width`（常是某机型外屏宽）+ 外层 `alignItems(HorizontalAlign.Start)` | 内容改 `width('100%')` 铺满，去掉左对齐（铺满是标准形态，不必询问） |
| 底部留白、按键没填满 | 按键区固定 `height`，根 `Column` 更高，`justifyContent` 默认 Start | 按键区固定高度改 `layoutWeight(1)` 填满剩余 |
| 整体过高/过矮 | 根组件写死 `height`，不随屏高变化 | 高度按屏高动态算：`display.getDefaultDisplaySync().height` 经 `px2vp()` 后取比例 |

要点：
- 面板宽度 = 根组件 `width('100%')`，展开态可达 ~711vp；内部内容也必须自适应或居中，否则宽屏右侧必然留白
- 屏高是 **px**，参与 vp 运算前先 `px2vp()`；比例由产品定（屏高 / 2、/ 3 等）
- `aboutToAppear` 取一次不随折展更新；要实时跟随需挂 `windowSizeChange` 重算
- 完整正反例见 `cases/bug-fix-avoid-areas.md` 场景13；根因索引见 `root-causes.md` 的 avoid-12

---

## 沉浸式

用户明确要求“全屏”“高度占满整个屏幕”“内容铺满物理屏幕”或延伸到状态栏/导航条区域时，
应采用沉浸式窗口布局；只给根组件设置 `height('100%')` 只能占满当前父容器或窗口内容区，
不能代替窗口级沉浸式配置。若需求只是占满父容器或系统安全内容区，则不应据此强制开启沉浸式。

```typescript
win.setWindowLayoutFullScreen(true);   // 内容延伸到状态栏/导航条下方
```

**必须先开这个再取避让区**，否则 `getWindowAvoidArea` 返回的系统栏高度可能与实际不一致。

开启后**内容避让由应用自己负责** —— 这正是安全区问题最高发的场景。
配套必须做的：

1. 关键内容用 `expandSafeArea` 或动态 padding 避开
2. 监听 `avoidAreaChange`，旋转/分屏/折叠后重算
3. 状态栏图标颜色跟随背景明暗（`setWindowSystemBarProperties`）

### 两个方案怎么选

| 方案 | 何时用 |
|---|---|
| 状态栏透明 + `expandSafeArea` | 只要背景铺满，内容自然留在安全区。不需要全屏布局，最省事 |
| `setWindowLayoutFullScreen` + 动态 padding | 需要精确控制避让高度，且折叠/旋转后要动态更新（视频页、聊天页、商品详情） |

### 浮层 TabBar 三件套

自定义底部栏浮在内容之上时，三个属性缺一不可：
`height('100%')` + `HitTestMode.Transparent`（让下方内容可点） + `margin` 避让指示条。

短视频这类沉浸场景还要额外做两件事：**隐藏 `Tabs` 默认栏**（默认 `barHeight: 56` 会占掉底部空间），
以及**去掉 `Stack` 外层的 padding**——外层 padding 只是把整体上推，那不是沉浸式。

### 滚动隐藏标题栏

列表上滑时标题栏渐隐、下滑时渐显，用 `Scroll` / `List` 的 `onScrollFrameBegin`
拿到本帧滚动增量，按**线性比例**换算标题栏高度与透明度，不要用"越过某个阈值就整块隐藏"
——后者在惯性滚动结束时会突然跳一下。

两个必做的兜底：

- **进度值要钳在 [0, 1]**，回弹与过度滚动会给出负值或超量值
- **断点切换时重置进度**。标题栏在 sm 和 lg 下高度不同，不重置会让新断点下的
  标题栏停在按旧高度算出的中间态

`onScrollFrameBegin` 的返回值会改变实际滚动量，**只读不改时要原样返回入参的 offset**，
否则会把列表滚动一起改掉。

---

## 什么时候直接用 HDS 组件

`@kit.UIDesignKit` 提供了一批已经做好避让与沉浸的组件，能省掉大量手写：

| 手写方案 | HDS 替代 | 最低版本 |
|---|---|---|
| 滚动隐藏标题栏（算偏移 + 动画 + 避让） | `HdsNavigation` 的 `dynamicHideTitleBar`，一行 | 5.1.0(18) |
| 底部页签避让指示条 + 模糊背景 | `HdsTabs` | 6.0.0(20) |
| 侧边栏分栏 | `HdsSideBar` / `HdsSideMenu` | 6.0.0(20) |
| 沉浸光感材质 | `hdsMaterial` | **6.1.0(23)** |
| 点光源 / 按压阴影等视效 | `hdsEffect` / `HdsVisualComponent` | 6.0.0(20) |

**版本门槛不是可选项**：`HdsTabs` 的悬浮样式与迷你栏（`miniBar`）要 6.1.0(23)；
`scrollEffectType` 里只有 `COMMON_BLUR` 是 5.1.0(18) 起，`TRANSITION_BLUR`
与 `GRADIENT_BLUR` 都要 6.0.0(20)。目标 API 低于门槛时选了这些能力，
不是降级而是直接不可用——**选型前先对一遍工程的 `compatibleSdkVersion`**。

三条硬约束，选型前必须确认：

- **地域仅中国大陆**（不含港澳台）
- **模拟器不支持沉浸视效**，要看效果得上真机
- `hdsMaterial` 沉浸光感**只支持手机和平板**，其它形态没有；
  用它之前先 `getSystemMaterialTypes()` 查当前设备支持哪些材质再降级

不满足这三条就老实手写，别指望 HDS 兜底。

---

## 排查顺序

看到内容被系统区域遮挡时：

1. 先分清是哪一类避让区 —— 状态栏、挖孔、键盘还是导航条
2. 若是 `keyboard` → 走[键盘避让](#键盘避让)，先确认避让模式
3. 若是 `system`/`navigation_indicator` → 检查是否开了沉浸式却没做避让；
   底部的话确认取的是 `TYPE_NAVIGATION_INDICATOR` 而不是 `TYPE_SYSTEM`
4. 若是 `cutout` → 挖孔位置随机型不同，必须用 API 取值，不能按某个机型硬编码；
   横屏时挖孔在侧边，检查右/下方向的公式有没有写反
5. 确认避让值是 **`avoidAreaChange` 回调参数**给的，而不是启动时读一次或别的回调里查的

---

## 完整案例

需要看可落地的修复代码或正向开发指引时：

- **bug 修复正反例**：`../references/cases/bug-fix-avoid-areas.md`（12 场景：状态栏遮挡、挖孔区、沉浸式底部、padding 错位、键盘截断、导航条遮挡、键盘遮挡、滚动隐藏标题栏、avoidAreaChange 时序旧值等）
- **开发场景最佳实践**：`../references/cases/scenario-avoid-areas.md`（6 场景：列表沉浸浏览、底部导航避让、短视频沉浸、挖孔适配、状态栏适配、键盘易操作）
