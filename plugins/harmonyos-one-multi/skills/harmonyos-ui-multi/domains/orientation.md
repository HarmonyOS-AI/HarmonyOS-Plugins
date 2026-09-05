# 域：方向与旋转

覆盖横竖屏策略、方向语义、旋转后的布局同步、视频类横竖屏。

选择 `window.Orientation` 时，先读取 Skill 内的
[窗口旋转策略参考](../references/window-rotation-policy.md)。该参考提供离线语义快照；需要更新或
发现冲突时，再以其中记录的 HarmonyOS 官方来源为准。

## 症状 → 本文档

| 症状 | 查本文 |
|---|---|
| 首页/应用级“跟随系统、受系统开关控制”旋转策略选型 | 见下文「先判断：跟随桌面型需求，还是自定义分叉」 |
| 旋转后布局没跟着变 | [旋转不等于断点变化](#旋转不等于断点变化) |
| 旋转后页面重置 | 见 `fold-form.md` 的开合连续性，机制相同 |
| 横屏后组件没变宽 | 见 `size-layout.md` |
| 改了显示大小后判断失效 | [遗留 348vp 业务判据与它的坑](#遗留-348vp-业务判据与它的坑) |

根因案例查 `../references/root-causes.md` 的 **RC-orient** 段。

---

## 先定一条元规则：修复场景尊重原有方案

工程里的方向适配大体两种写法：**基于 `deviceType` + 折叠状态**（厂商实际最常用），
和**基于断点/窗口最小边**（从零适配时更优）。

**修 bug 时在原方案上补，不要顺手换方案。** 开发者可能有定制的业务需求或历史兼容
考虑，换方案会把一个局部缺陷变成一次全局回归。只有从零适配或对方主动要求重构时，
才推荐换成断点方案。

---

## 三个"方向"值语义不同，不能互换

这是本域最容易出错的地方：

| 值 | 类型 | 含义 |
|---|---|---|
| `window.Orientation` | **可设置的策略** | 应用**希望**的方向（`setPreferredOrientation` 的入参） |
| `display.orientation` | **只读的当前状态** | 系统**当前**的方向 |
| `display.rotation` | **硬件角度** 0-3 | 屏幕相对自然方向转了几个 90° |

它们之间**没有直接映射关系**。用其中一个的值去填另一个的语义槽位是常见 bug。

判断"现在是横屏还是竖屏"应该看窗口宽高关系或断点，不要读 rotation 反推。
`setPreferredOrientation` 改变的是屏幕显示方向，会连带应用、桌面、状态栏、控制中心等可见
系统元素以及后台元素一起旋转，不是只旋转当前页面。`display.orientation` 只适合辅助 sensor/
相机方向修正，不应作为窗口布局适配依据。

### rotation = 0 不一定是竖屏

| 设备形态 | rotation=0 的含义 |
|---|---|
| 直板机 / 折叠态 / 三折 F、M 态 / 平板 | `PORTRAIT` |
| **三折叠 G 态** | **`LANDSCAPE_INVERTED`（反向横屏）** |

三折 G 态的自然方向是横屏，且因摄像头物理位置在反向一侧，rotation=0 对应的是
**反向**横屏。把 rotation=0 当竖屏处理，在这台设备上一切都是反的。

---

## 旋转策略选型：先查文档

遇到需要确定 `window.Orientation` 的需求时，必须先查
`../references/window-rotation-policy.md`，再根据允许方向、是否跟随传感器、是否受系统旋转锁
控制、设备形态与窗口场景选择枚举。输出选择结果时说明枚举名称、值和参考依据。

不要在主域文档中把某段自然语言需求固定绑定到某个枚举；参考与官方来源冲突时以官方来源为准。
`module.json5` 的 `orientation` 与运行时 `setPreferredOrientation()` 使用同一组策略语义。
首页/入口全局旋转策略配置在 **`entry/src/main/module.json5`** 中。

**`SM` 是窗口断点，不是设备类型或折叠形态。** 把 “SM” 当作设备时，先拆分窗口宽度要求
与设备形态要求，再依据文档选型，不能只凭断点名称确定旋转枚举。

### 先判断：跟随桌面型需求，还是自定义分叉

“直板竖屏、折叠展开/悬停/平板自由旋转、受系统开关控制”——凡首页/应用级旋转策略的
行为目标是这个形态，先逐形态对照 `FOLLOW_DESKTOP` 的桌面行为，全部一致就不要写任何运行时分叉：

| 形态 | FOLLOW_DESKTOP 下应用的行为（= 桌面行为） |
|---|---|
| 直板机 / 折叠态 / 外屏 | 桌面固定竖屏 → 应用保持竖屏 |
| 折叠屏展开 / 悬停 | 桌面随传感器旋转 → 应用跟随，受控制中心旋转锁控制 |
| 平板 | 桌面四向旋转 → 应用跟随，受旋转锁控制 |

“受系统开关（旋转锁）控制”+“设备形态决定能不能转”正是 FOLLOW_DESKTOP 的指纹。需求与
上表逐形态一致时，策略就是 `FOLLOW_DESKTOP(17)`，并且**声明在入口 module.json5 的
ability 节点**（多 product 工程为 `products/<product>/src/main/module.json5`），不要在页面里
调用 `setPreferredOrientation`：

```json5
"abilities": [
  {
    "orientation": "follow_desktop",
    "supportWindowMode": ["fullscreen", "splitScreen", "floating"]
    // ...
  }
]
```

声明式配置启动即生效，`getPreferredOrientation()` 读到的就是 `FOLLOW_DESKTOP`，各形态行为
由系统分别判定。若再在首页运行时 `setPreferredOrientation(PORTRAIT / AUTO_ROTATION_RESTRICTED)`
做设备分叉，声明会被覆盖：策略值变成 1/8，形态间行为也与桌面脱钩——这是“跟随系统”需求
最常见的错误实现，识别特征就是自己写 `isFoldable()` + 折叠状态 + 屏幕长边阈值去判“大屏”，
而系统本来就会按形态判定。工程已有方向基础设施（方向预设表、配置式选型接口一类）时优先复用，
不重写设备判定。

只有需求在某些形态上**与桌面行为不一致**（例如折叠态也要求可旋转、或某形态要固定方向
不随锁），才需要运行时枚举分叉，见下文“按设备形态选择方向策略”。

### setPreferredOrientation 的适用边界

**只影响主窗口。** 主窗口全屏且策略不满足当前方向时，前台调用通常会立即触发旋转；主窗口
不是全屏时，调用可以成功但不会立即改变显示方向，回到全屏后系统才重新依据该策略调整。

以下场景不能把“接口调用成功”当作“已经旋转”：

| 场景 | 方向控制 | 该怎么适配 |
|---|---|---|
| 分屏 / 智慧多窗悬浮窗 | 系统忽略策略，可能强制按竖屏方向布局；退出后重新评估 | `windowSizeChange` + 断点 |
| 自由多窗 | 系统强制小窗，设置策略不触发旋转；退出后重新评估 | 同上 |
| 多任务 / 应用后台 | 当前场景下不触发旋转，回到可生效场景后重新评估 | 同上 |
| 子窗口 | 不生效 | 同上 |
| TV 等无传感器设备 | 旋转策略可调用但实际方向不变 | — |

**在这些模式下不要依赖方向锁，改用布局适配。** 这条能省掉大量"为什么设了没反应"的排查。

### 每页改方向必须还原

页面级方向设置是**窗口级全局副作用**：某页设了横屏，不还原的话后续所有页面都是横屏，
页面跳转也不会自动恢复。

进入临时页面前保存的是 `getPreferredOrientation()` 返回的**策略枚举**，退出时恢复该策略；
不能保存 `display.rotation` / `display.orientation` 的物理方向快照后再翻译成固定
`PORTRAIT` / `LANDSCAPE`。折叠开合会让物理方向快照过期，恢复进入前保存的策略才能让系统
按当前形态重新判定。

还原值不能硬编码成 `UNSPECIFIED`：不同工程的全局策略不同。只有进入前策略确实是
`UNSPECIFIED(0)` 时才恢复 0。这与键盘避让模式的处理方式一致（见 `avoid-area.md`）。

---

## 遗留 348vp 业务判据与它的坑

部分遗留实现用 `min(width, height) > 348vp` 猜设备是否支持旋转。这个条件最多是特定业务
策略的粗筛，**不能决定桌面旋转能力，也不能替代文档中的旋转策略选型**。
设备尺寸统一查 `../references/device-matrix.md`，这里只保留判据结论：

| 设备 | 最小边 > 348 | 默认支持旋转 |
|---|---|---|
| 直板机 | 是 | 否 |
| Pura X 内屏 | 是 | 否 |
| **Pura X 外屏** | **否** | 否 |
| Pura X Max 内屏 | 是 | **是** |
| Pura X Max 外屏 | 是 | 否 |
| Mate X6/X7 内屏 | 是 | 否 |
| **Mate X6/X7 外屏** | **否** | 否 |
| 三折 F 态 | 是（仅剩 2vp 余量） | 否 |
| 三折 M 态 | 是 | 否 |
| 三折 G 态 | 是 | **是** |
| 平板 | 是 | **是** |

即便沿用这套遗留判据，**超过 348vp 也不是充分条件**：Pura X 内屏过线，默认仍不旋转。
不能根据过线结果反推设备或桌面一定支持旋转。

**更要命的是这个阈值本身会失效**：`px2vp()` 依赖 DPI，用户调大"显示大小"后
DPI 升高，同样的物理像素换算出更少的 vp。Mate 60 Pro 实测 DPI 480→630 时
最小边从 390vp 跌到 320vp，直接跌破 348——应用被强制竖屏。

**修法：阈值改用物理像素判定**（约 520px 并留余量），或干脆改用系统断点返回值。
这一条推翻了官方最佳实践里的示例代码。

### 显式业务确需按窗口分支时，改用断点组合

仅当产品明确要求“某些窗口区间固定竖屏、其他区间自动旋转”，或者修复既有动态分支时，
才用断点表达。断点返回值由系统计算，不受 `px2vp()` 的 DPI 漂移影响，因此比 348vp 稳：

```typescript
const shouldRotate =
  (widthBp === 'md' && heightBp !== 'sm') ||
  (widthBp === 'lg' && heightBp === 'sm');

win.setPreferredOrientation(
  shouldRotate ? window.Orientation.AUTO_ROTATION_RESTRICTED : window.Orientation.PORTRAIT
);
```

对照上表看这个判据的取舍：`md` 且非扁（折叠内屏、小平板竖屏）允许转；
`lg` 且扁（平板横屏）允许转；`sm` 一律不转（直板机与各种外屏）。
用 `AUTO_ROTATION_RESTRICTED` 而不是 `AUTO_ROTATION`，是为了尊重用户的系统旋转锁开关。

---

## 旋转不等于断点变化

旋转会改变窗口宽高，**但不一定跨断点**。例如平板从 1137×711 转到 711×1137，
横向断点可能从 lg 变成 md，也可能都落在 lg 内。

因此：

- **布局响应要挂在断点上**，不是挂在"旋转事件"上
- 判断布局该不该变，看的是断点值本身（`getWindowWidthBreakpoint()`），不是旋转事件

反过来，有些变化不改变断点但需要响应（如高宽比翻转影响 `aspectRatio` 选择），
这类要看**纵向断点**（高宽比分档）而非横向断点。

### 三种监听方式的能力边界

| 方式 | 能拿到 | 局限 |
|---|---|---|
| `display.on('change')` | rotation / orientation | 回调参数**只有 display id**，宽高要自己查，且查到的可能是旧值 |
| `windowSizeChange` | 新的窗口宽高 | **180° 旋转不触发**（宽高没变） |
| 媒体查询 | 横/竖 | 只能二分，拿不到具体数值 |

180° 旋转是个盲区：宽高没变，`windowSizeChange` 不触发，依赖它做重排的
绝对定位元素会停在旧布局。**必须同时监听
`display.on('change')`**，注销时传保存的回调引用。

`window.getLastWindow` 与 `display.on('change')` 都有延迟——需要准确尺寸时
以 `windowSizeChange` 的回调参数为准。

---

## 按设备形态选择方向策略（自定义分叉兜底）

本节只服务**自定义分叉**：需求在某些形态上的行为与 FOLLOW_DESKTOP 的桌面行为不一致，
或页面级临时策略需要自行选枚举时，才按本节分叉。凡行为目标等价于“跟随系统/受系统
开关控制”的首页级需求，先走上文“先判断：跟随桌面型需求，还是自定义分叉”的逐形态对照，不要用本节实现——本节
产出的 `AUTO_ROTATION_RESTRICTED` / `USER_ROTATION_PORTRAIT` 分叉会覆盖声明式策略，
`getPreferredOrientation()` 读到 1/8/13 而不是 17。

确需分叉（“大屏可自由旋转、小屏先竖屏”且与桌面行为不一致）时，**必须先区分
折叠与非折叠设备**，否则平板会被误判成小屏强制竖屏。

### `getFoldStatus()` 的语义边界

`display.getFoldStatus()` 是**专为可折叠设备设计**的接口，返回枚举 `FoldStatus`：

| 枚举 | 值 | 含义 |
|---|---|---|
| `FOLD_STATUS_UNKNOWN` | 0 | 状态无法确定，或**设备本身不可折叠** |
| `FOLD_STATUS_EXPANDED` | 1 | 折叠屏完全展开 |
| `FOLD_STATUS_FOLDED` | 2 | 折叠屏完全折叠 |
| `FOLD_STATUS_HALF_FOLDED` | 3 | 半折叠（悬停态） |

**关键陷阱**：平板、直板手机等**非折叠设备**上，`getFoldStatus()` 返回
`FOLD_STATUS_UNKNOWN(0)`，**不能依赖它区分"平板"与"直板手机"**。典型错误：

```typescript
// ❌ 错误：平板 getFoldStatus() 返回 UNKNOWN，被误判为"小屏竖屏"
if (display.getFoldStatus() === display.FoldStatus.FOLD_STATUS_EXPANDED ||
  display.getFoldStatus() === display.FoldStatus.FOLD_STATUS_HALF_FOLDED) {
  win.setPreferredOrientation(window.Orientation.AUTO_ROTATION);
} else {
  win.setPreferredOrientation(window.Orientation.USER_ROTATION_PORTRAIT); // ← 平板也走到这里
}
```

### 正确判断"大屏可自由旋转"形态

平板（非折叠大屏）与折叠屏展开/悬停态都支持自由旋转，判断需先分流：

```typescript
// 是否为折叠屏展开态或悬停态
function isExpandedOrHalfFolded(): boolean {
  const st = display.getFoldStatus();
  return st === display.FoldStatus.FOLD_STATUS_EXPANDED ||
    st === display.FoldStatus.FOLD_STATUS_HALF_FOLDED;
}

// 是否为平板/大屏设备（示例只作现有设备分类缺失时的降级；优先复用工程已有设备类型能力）
function isTabletDevice(): boolean {
  if (display.isFoldable()) {
    return false;
  }
  const d = display.getDefaultDisplaySync();
  // 用长边避免把 711×1137vp 的竖屏平板因当前 width < 840vp 误判成手机。
  return Math.max(d.width, d.height) / d.densityPixels >= 840;
}

// 播放页方向策略：大屏可自由旋转，直板机先竖屏再随传感器
function applyPlayPageOrientation(): void {
  if (isExpandedOrHalfFolded() || isTabletDevice()) {
    win.setPreferredOrientation(window.Orientation.AUTO_ROTATION);
  } else {
    win.setPreferredOrientation(window.Orientation.USER_ROTATION_PORTRAIT);
  }
}
```

注意 `isFoldable()` 优先于宽度判断：折叠屏的 `getDefaultDisplaySync().width`
可能是展开态宽度，直接按宽度判会把折叠屏也归进平板分支——先排除折叠设备再比宽度。

### 常见运行时动作

| 场景 | 推荐取值 | 说明 |
|---|---|---|
| 大屏可旋转且尊重系统旋转锁 | `AUTO_ROTATION_RESTRICTED` | 四向自动旋转，旋转锁打开后固定在系统允许的锁定方向 |
| 大屏始终可旋转，不受系统旋转锁影响 | `AUTO_ROTATION` | 四向自动旋转；只有产品明确要求忽略旋转锁时使用 |
| 直板小屏进入视频播放页 | `USER_ROTATION_PORTRAIT` | 先竖屏展示，随后允许随传感器旋转（横屏可全屏） |
| 全屏按钮主动横屏 | `USER_ROTATION_LANDSCAPE` | 先转横屏，之后按传感器、旋转锁和系统允许方向自动旋转 |
| 退出播放页还原 | 进入前保存的策略 | 恢复 `getPreferredOrientation()` 的结果 |

**横竖屏联动全屏**：进入页面时**先读一次当前 `windowRect` 同步初始全屏状态**，再挂
`window.on('windowSizeChange')` 监听后续变化——事件只在尺寸变化时触发，平板横屏进入
播放页时窗口尺寸不变、事件不会来，只挂监听会一直停在竖屏布局。初始同步与变化监听必须
用同一判据、同一同步函数（`width > height` 即横屏）：

```typescript
// aboutToAppear：入场先同步一次，再挂监听；回调保存引用，aboutToDisappear 成对 off
syncFullScreenBySize(width: number, height: number): void {
  const landscape = this.getUIContext().px2vp(width) > this.getUIContext().px2vp(height);
  if (landscape !== this.isLayoutFullScreen) {
    this.isLayoutFullScreen = landscape;
    this.setFullScreen(landscape);
  }
}
const rect = win.getWindowProperties().windowRect;
this.syncFullScreenBySize(rect.width, rect.height);
this.sizeCallback = (size: window.Size) => this.syncFullScreenBySize(size.width, size.height);
win.on('windowSizeChange', this.sizeCallback);
```

平板横屏进入播放页时应直接横屏全屏播放，靠的就是入场同步，不是等第一次旋转。判据用
窗口宽高，不要用 `display.rotation` / `display.orientation` 反推（见上文三值语义）。

---

## 视频类横竖屏

短视频/长视频的方向策略比普通页面复杂：要根据**屏幕区间 × 视频宽高比**决定。

| 屏幕区间 | 视频类型 | 策略 |
|---|---|---|
| 小屏竖屏 / 中屏横屏 | 横向视频（全屏） | `USER_ROTATION_LANDSCAPE` / `_INVERTED` |
| 小屏竖屏 / 中屏横屏 | 竖向视频（全屏） | `PORTRAIT` |
| 中屏竖屏及以上 | 任意 | `AUTO_ROTATION_UNSPECIFIED` |

用 `USER_ROTATION_*` 而不是固定方向，是为了让用户手动转还能生效。

官方有现成的三方库 **`@hadss/adaptive_video`**（`AdaptiveRotation` /
`AdaptiveImmersion` / `ScreenModeNotifier`），自适应旋转与沉浸都封好了，
比手写一套稳。

`Tabs` + `Swiper` 的短视频页有两个专属坑：`Tabs` 懒创建导致 `aboutToAppear`
只触发一次，方向控制要放 **`Tabs.onChange`**，不要放子组件生命周期；
`Swiper.onChange` 里重复锁方向会互相覆盖。

### 横竖屏切换的性能

旋转会触发全量重建。三条优化：

- 旋转前后内容不变的子组件加 `@Component({ freezeWhenInactive: true })`
- 图片开 `autoResize`
- 耗时初始化移到 `taskpool`，别阻塞主线程（否则表现为白屏 / ANR）

---

## 调试

```bash
hdc shell hidumper -s DisplayManagerService -a "-a"    # 看当前 rotation
hdc shell uitest uiInput keyEvent 2055                 # KEYCODE_ROTATE_90
```

测试用例里可用 `driver.setDisplayRotation(DisplayRotation.ROTATION_90)`。
模拟器上更干净的方式是 `Emulator -instance <名字> -rotation left|right`。

---

## 排查顺序

旋转后布局不对时：

1. 先确认**断点是否真的变了** —— 在页面里打一条 `getWindowWidthBreakpoint()` 的日志，
   没变就不该期待断点驱动的布局变化
2. 断点变了但布局没变 → 走 `size-layout.md` 的
   [断点没生效的四种原因](size-layout.md#断点没生效的四种原因)
3. 断点没变但确实该响应 → 检查是否该用纵向断点（高宽比）而非横向断点
4. 只有 180° 旋转出问题 → 缺 `display.on('change')` 监听
5. 方向策略设了没反应 → 先看是不是分屏/悬浮窗/自由窗口，这些场景系统直接忽略
6. 只在某些设备上不转 → 对照上面的设备旋转能力表，再确认用户有没有改过显示大小

---

## 完整案例

需要看可落地的修复代码时：`../references/cases/bug-fix-orientation.md`（9 案例：折叠展开方向被强制锁、Tabs+Swiper 方向锁定 bug、分屏旋转失效、全屏退出方向未恢复、开合闪烁、显示大小缩放断点错误、XComponent 预览旋转错乱黑屏、Navigation 分栏拥挤、切屏后自动转竖屏）。
