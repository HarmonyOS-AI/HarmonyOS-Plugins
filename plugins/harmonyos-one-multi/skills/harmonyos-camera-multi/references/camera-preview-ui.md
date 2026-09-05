# 预览区域与叠加控件

## 预览区尺寸

- `XComponent` 的宽高必须在**每次 `windowSizeChange`** 重算，静态尺寸会在旋转后变形
- **Surface 宽高比按 `display.rotation` 与镜头安装角的差值判断**：
  差值为 0°/180° 与 90°/270° 两种情况下宽高**要不要交换**是相反的，
  搞反了画面就是压扁或拉伸
- **平板且 `targetAPIVersion < 14` 时交换逻辑与常规相反**（真实设备坑，候选知识）：
  常规逻辑 90°/270° 时 `width = 比例 × 窗口高`、`height = 窗口高`，0°/180° 时
  `width = 窗口宽`、`height = 比例 × 窗口宽`；平板 + 低 targetVersion 上这两支**互换**。
  同一份代码不改分支，在平板上预览必然拉伸。判断用的 `targetVersion` 要
  `bundleManager.getBundleInfoForSelf()` 异步获取（`50000013` 即 API 13），
  获取完成后**必须重算一次宽高**——它在 `aboutToAppear` 之后才回来
- 显式调 `setXComponentSurfaceRect` 传实际显示尺寸，不要隐式依赖 XComponent 尺寸
- 折展开合场景与 [折展防拉伸链路](camera-fold.md#折展防拉伸链路) 一起读：窗口尺寸变化只重算 Surface 矩形，形态终态还要按新基准重选 Profile
- `windowClass` 在 `aboutToAppear` 里通过 `AppStorage` 取，不要在字段初始化器里取 ——
  组件挂载前 `getUIContext()` 不可靠

### 常见尺寸缺陷

- **画面拉长/压缩 = 帧宽高比与 Surface 宽高比不一致**：按 Profile 比例设计组件
  （16:9 / 4:3 / 1:1），或用 `setXComponentSurfaceRect` 解耦组件与 Surface；筛选 Profile
  时**只比较宽高比（差值 ≤ 0.1），不要按组件具体宽高精确筛**——切分辨率宽高比会改变
  视角裁剪；
- **预览左侧黑边**：`setXComponentSurfaceRect` 的 `offsetX`/`offsetY` 设了非 0 值
  （如 20），该区域露出组件黑色背景——置 0；
- **取景视角小**：XComponent 未铺满屏幕，或 Surface 宽高**大于**组件宽高只显示局部，
  用 `setXComponentSurfaceRect` 对齐预览分辨率比例；
- **折叠屏展开态黑屏**：API 18 之前 `renderFit` 仅支持 `RESIZE_FILL`，低版本工程误设
  `RESIZE_COVER` 会渲染失败——按 `compatibleSdkVersion` 选择。

## 叠加控件

快门、模式栏、变焦滑块这类压在预览之上的控件：

1. **必须与 XComponent 在同一个 `Stack` 内**，用响应式定位
   （`Blank` / `layoutWeight` / `width('100%')` / `justifyContent` / `aspectRatio`），
   **绝不能用绝对 px 偏移** —— 预览区的框会随形态、旋转、分屏改变，固定坐标必然错位
2. **预览区框一变就要重排控件**（形态切换、旋转、分屏、前后置 profile 比例变化）
3. **必须避让系统安全区**：`expandSafeArea`（背景填充）+ `getWindowAvoidArea`/
   `avoidAreaChange`（内容内缩）。快门键压在导航条下是这一域的高频问题

### 叠加控件 API 速查

上面三步是原则。这里给可落地的 API 全集（候选知识，接入业务后按目标形态重验）。

**安全区 API 全集**：

| API / 属性 | 归属 | 用途 |
|---|---|---|
| `expandSafeArea(edges?, enable?)` | 通用属性 | 组件**背景**延伸到安全区外（沉浸式），常用于 XComponent 预览层 |
| `window.getLastWindow(ctx)` → `win.getWindowAvoidArea(type)` | window | 取指定 `AvoidAreaType` 的避让矩形（px），内容层据此 `padding` 内缩 |
| `win.on('avoidAreaChange', cb)` | window | 安全区变化（键盘弹出、横竖屏系统栏高度变）时回调，重算内缩 |

`expandSafeArea` 参数：`edges` 取 `Edge.TOP`/`BOTTOM`/`LEFT`/`RIGHT`/`ALL`；`enable` 对应边是否开启。预览层常用 `.expandSafeArea(true, true)`（宽高都延伸）。

**AvoidAreaType 四枚举**：

| 枚举值 | 含义 | 叠加控件是否常避让 |
|---|---|---|
| `TYPE_SYSTEM` | 状态栏等系统区域 | 是 |
| `TYPE_NAVIGATION_INDICATOR` | 底部导航指示条 | 是 |
| `TYPE_CUTOUT` | 挖孔 / 刘海 | 是 |
| `TYPE_KEYBOARD` | 软键盘 | 按需 |

`getWindowAvoidArea` 返回的 `AvoidArea` 含 `topRect`/`bottomRect`/`leftRect`/`rightRect`，每个 `{ left, top, width, height }`（px）。内容内缩时用 `px2vp` 转 vp 再设 `padding`。**常见组合**：顶部取 `TYPE_SYSTEM` 与 `TYPE_CUTOUT` 的最大值；底部取 `TYPE_NAVIGATION_INDICATOR`；横屏左右常避让 `TYPE_CUTOUT`。

**响应式属性速查**：

| 属性 / 组件 | 用途 | 相机叠加场景 |
|---|---|---|
| `Stack` | 层叠容器，后入元素在上 | XComponent（底层）+ 叠加控件层（上层）同 Stack |
| `Blank()` | 弹性空白占位 | 顶部模式条与底部快门之间撑开，随容器高度自适应 |
| `layoutWeight(number)` | 按权重分配剩余空间 | 多控件区按比例分高/宽 |
| `width('100%')` / `height('100%')` | 百分比尺寸 | 控件层铺满 Stack，随预览区缩放 |
| `aspectRatio(ratio)` | 固定宽高比 | 快门按钮保持圆形不受容器形变 |
| `justifyContent(FlexAlign)` | 主轴对齐 | `Center` / `SpaceEvenly` / `SpaceBetween` 排列模式按钮 |
| `alignItems(...)` | 交叉轴对齐 | 控件交叉方向居中 |
| `padding({top,bottom,left,right})` | 内边距 | 内容内缩安全区（值来自 getWindowAvoidArea） |

`FlexAlign` 常用值：`Start` / `Center` / `End` / `SpaceBetween`（两端贴边中间均分）/ `SpaceAround`（每元素两侧等距）/ `SpaceEvenly`（所有间距含两端均等）。

## 旋转监听要成对

**`windowSizeChange` 在 180° 旋转时不触发**（宽高没变）。
只监听它会让控件在半圈旋转后停在旧布局。

必须同时监听：

```typescript
win.on('windowSizeChange', cb1);
display.on('change', cb2);
```

注销时 **必须传保存的回调引用**：`display.off('change')` 不带回调会移除
该事件上所有监听，包括其他组件的。

---
