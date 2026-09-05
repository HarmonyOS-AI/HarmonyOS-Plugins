# 域：窗口形态

覆盖全屏/分屏/悬浮窗/自由多窗的配置声明、窗口状态监听、应用内分屏和
形态特有的避让。本域的变化信号是 **`windowStatusType` 枚举变化**。

## 症状 → 本文档

| 症状 | 查本文 |
|---|---|
| `startAbility` 后目标页全屏显示，没分屏 | [应用内分屏](#应用内分屏) |
| 分屏已存在，再次启动数据不更新 | [应用内分屏](#应用内分屏) |
| 沉浸式页面进悬浮窗后顶部按钮点不到 | [悬浮窗顶部避让](#悬浮窗顶部避让) |
| 视频悬浮窗竖着显示、内容不全 | [横向悬浮窗](#横向悬浮窗) |
| 自由窗口拖到很小后布局崩溃 | [窗口尺寸下限](#窗口尺寸下限) |
| 状态回调里读到旧的窗口尺寸 | [两个状态监听，回调时机不同](#两个状态监听回调时机不同) |
| 自定义标题栏拖不动窗口 / 拖动不跟手 | [拖拽热区](#拖拽热区) |
| 分屏/小窗下内容截断、滚不动 | 布局问题，走 `size-layout.md`（见下方界碑） |

根因案例查 `../references/root-causes.md` 的 **RC-window** 段。

---

## 域界碑：分屏适配的本质是断点适配

分屏/悬浮窗把窗口压小后，宽度会落到 sm/md 断点——**已有的响应式分支直接吃下，
不需要为分屏另写一套布局**。内容截断、图片变形、组件挤压这类几何问题归
`size-layout.md`；本域只管形态本身的事：**声明、状态监听、形态特有的避让与交互**。

判断问题归属只看一件事：修法要不要区分 `windowStatusType`。要区分（悬浮窗控制条
避让、横向悬浮窗、拖拽热区）归本域；不用区分（换个宽度就复现）归 size-layout。

---

## 形态总览

`window.WindowStatusType` 五个值：

| 枚举 | 值 | 说明 |
|---|---|---|
| `FULL_SCREEN` | 1 | 全屏 |
| `MAXIMIZE` | 2 | 最大化 |
| `MINIMIZE` | 3 | 最小化 |
| `FLOATING` | 4 | 自由悬浮窗口 |
| `SPLIT_SCREEN` | 5 | 分屏 |

| 设备 | 分屏 | 自由多窗 | 悬浮窗 | 形态特有的坑 |
|---|:---:|:---:|:---:|---|
| 直板机 / 折叠屏 | ✅ 上下 | ❌ | ✅ | 分屏高度减半；悬浮窗等比缩放 |
| 平板 | ✅ | ✅ | ✅ | 进自由多窗后强制横屏；DPI 会变（`systemDensityChange`，见 size-layout） |

**`FLOATING` 一个值两种语义**：平板开启自由多窗时代表自由多窗，
关闭时代表悬浮窗。按形态写逻辑时别假设 `FLOATING` 只有一种视觉形态。

---

## 配置声明

`module.json5` 的 `abilities` 下：

```json5
{
  "supportWindowMode": ["fullscreen", "split", "floating"],
  "minWindowWidth": 320,
  "minWindowHeight": 480
}
```

- `supportWindowMode` 合法值是 **`"fullscreen"` / `"split"` / `"floating"`**，
  没有 `"splitScreen"`（高频幻觉点，编译才报错）。
- 不声明 `"split"`，`startAbility` 传了分屏 `windowMode` 也不生效。

### 窗口尺寸下限

自由窗口能被拖到任意小，不设下限就是让用户亲手拖出布局崩溃：

- 静态：`minWindowWidth` / `minWindowHeight`（vp）；
- 运行时：`win.setWindowLimits({ minWidth, minHeight, maxWidth, maxHeight })`，
  与静态配置可共存，取更严格的一侧。

下限值要和断点体系对齐——下限设 320vp 意味着 sm 分支必须真的能用，
验证自由窗口时要覆盖目标宽度和工程允许的最窄窗口。

---

## 两个状态监听，回调时机不同

| 事件 | 起始 | 回调时机 | 用途 |
|---|---|---|---|
| `windowStatusChange` | API 11 | 状态变化立即回调，**Rect 未必更新** | 只需知道形态类型变了 |
| `windowStatusDidChange` | API 20 | 状态变化**且 Rect 更新完成后** | 回调里要立刻读新尺寸 |

- 在 `windowStatusChange` 里读 `windowRect` 是本域第一坑：拿到的是旧尺寸。
  要么换 `windowStatusDidChange`（用前 `canIUse('SystemCapability.Window.SessionManager')`），
  要么状态归状态、尺寸交给 `windowSizeChange`。
- 当前状态用 `getWindowStatus()`（API 12+）同步查，别缓存自己猜。
- 注册/注销纪律与 size-layout「窗口监听」一节完全相同：`loadContent` 回调内注册、
  保存回调引用按引用 `off()`、经 `AppStorage` 分发给页面，不要每个组件各挂一份。
  尺寸类监听（`windowSizeChange` / `systemDensityChange`）的分工也在那一节。
- **销毁回调里的窗口操作必须 try/catch 兜底**：窗口原生对象可能先于
  `onWindowStageDestroy`/`onDestroy` 被系统回收，此时对 window 调 `off` 等接口会抛
  `This window state is abnormal. Window is nullptr`，未捕获异常**直接崩溃整个进程**
  （表现为 App died，faultlog 见 jscrash）。兜底后仍按引用成对注销并置空引用。

---

## 应用内分屏

与平行视界是**两套不同机制**，别混：分屏是启动第二个 UIAbility，各自有独立窗口和
生命周期；平行视界是同一个 Ability 内的分栏配置（见 `size-layout.md`「平行视界」）。
需要两个窗口独立并行操作（如比价、对照编辑）才用分屏。平行视界与 `Navigation`
分栏各自有严格采用前提（见 `size-layout.md`「平行视界」与「分栏布局要点」），
未命中前提时保持单栏，不要因为"大屏"就默认上分栏。

链路四步：

1. `module.json5` 里声明**至少两个 UIAbility**，且 `supportWindowMode` 含 `"split"`；
   目标 Ability 用 `launchType: "singleton"`，后续调用才走 `onNewWant` 而不是再建实例
2. `startAbility` 时必须传 `StartOptions` 并指定 `windowMode`，不传就是全屏启动；
   枚举是 `WINDOW_MODE_SPLIT_PRIMARY` / `WINDOW_MODE_SPLIT_SECONDARY`，
   **没有 `WINDOW_MODE_FLOATING`**（幻觉点，悬浮窗不从这里启动）
3. 目标 Ability 用 `Want.parameters` → `LocalStorage` → `loadContent(path, storage)` 传参；
   页面侧 `@Entry({ useSharedStorage: true })` 才能接到共享 storage
4. **`onNewWant` 必须实现**，否则分屏已存在时后续 `startAbility` 不会更新数据

- `splitRatio`（`window.SplitRatioPreference`）控制主副屏比例，**API 26 起**，低版本不生效。
- 目标页外层 `Navigation` 加 `.hideTitleBar(true)`，否则与 `NavDestination`
  双标题栏叠出一条空白。
- 分屏后两侧内容相同 = 两个 UIAbility 加载了同一个页面，检查各自 `loadContent` 的路径。
- **入口必须做宽度阈值门控**：分屏是宽窗口能力，发起入口在窗口宽度（`onSizeChange`
  实测值）**≥ 600vp** 或分屏已激活时显示，窄窗口隐藏。窄窗口能力入口无条件渲染会直接
  回归基线——基线窄窗口的操作区本无此入口，新增即改变既有布局与计数；不要按设备类型
  或断点名称猜，取页面实际窗口宽度判断。**不得以“功能不可达”为由豁免门控**：需求描述
  入口能力不等于要求所有窗口形态可见——窄窗口隐藏后宽窗口/折叠展开/平板仍完全可达，
  只有用户明确要求窄窗口也显示时才例外，且例外必须记录用户原话。

全链路现成资产：`$OM/assets/window-form/` 的 `SplitScreenAbility` /
`SplitScreenMainPage` / `SplitScreenDetailPage` 三件套。

---

## 悬浮窗与自由多窗

### 悬浮窗顶部避让

沉浸式页面（隐藏状态栏）进入悬浮窗后，系统在窗口顶部叠一条控制条，
与应用 UI 重叠，顶部按钮点不到。修法：`FLOATING` 状态下把控制条高度让出来——

```typescript
win.on('windowStatusChange', (status: window.WindowStatusType) => {
  if (status === window.WindowStatusType.FLOATING) {
    this.topPadding = this.getUIContext().px2vp(
      win.getWindowAvoidArea(window.AvoidAreaType.TYPE_SYSTEM).topRect.height)
  } else {
    this.topPadding = 0   // 全屏/分屏不需要这份额外避让
  }
})
```

这是**形态相关避让**，所以收在本域；常规安全区避让（状态栏/挖孔/键盘）的
两种做法与 padding 加在哪一层，都在 `avoid-area.md`，口径以它为准。

动手前**先验证基线**：目标页面在悬浮窗内本就可点（基线已满足避让）时，不要重建它的
避让链路——基线已通过的行为被改动回归，是悬浮窗适配最常见的事故。只对确实被控制条
挡住的沉浸式页面按上例补避让。修改共享窗口工具类（WindowUtils 一类）的避让行为、或
新增**全局 `windowStatusChange` 监听**并在回调里重刷避让区，属于**基础设施级**变更，
会影响所有页面的既有布局，修改前必须先说明影响面；页面级 padding 首选经已有的
避让区分发机制消费，而不是重算一遍。

### 横向悬浮窗

视频/游戏类应用的悬浮窗默认竖向显示。要横向，**两处必须成对配置**，缺一不生效：

1. `module.json5`：`"preferMultiWindowOrientation": "landscape_auto"`（仅横屏应用配）
2. 运行时：进入页面 `enableLandscapeMultiWindow()`、离开 `disableLandscapeMultiWindow()`

---

## 真实形态检查清单

截图看不出交互问题，这些必须真机逐项过：

- [ ] 手机/折叠屏上下分屏：高度减半后内容可滚动、无截断
- [ ] 平板悬浮窗：等比缩放后布局正常，弹窗按钮可点击
- [ ] 沉浸式页面进悬浮窗：顶部控制条下方内容可点击
- [ ] 自由窗口拖到 `minWindowWidth` 最小值：布局正常收缩，不崩溃
- [ ] 横屏视频悬浮窗：横向显示，内容不截断
- [ ] 形态间快速切换（全屏↔分屏↔悬浮）：无崩溃、无监听泄漏（销毁时已 `off()`）

定向验证至少覆盖目标窗口、一个临界宽度和窄屏基线，并检查窗口往返切换后的布局与状态。
