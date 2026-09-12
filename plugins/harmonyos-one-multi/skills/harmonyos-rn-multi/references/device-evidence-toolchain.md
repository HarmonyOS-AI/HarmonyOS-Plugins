# RNOH 多设备运行证据采集工具链

仅在问题需要目标设备、动态窗口或原生几何证据时读取。静态配置问题不要求为了流程完整而强行连接设备；没有设备时保留可执行命令并将运行结果标为 `not_verified`。

## 证据目标

一次采集必须回答“首个错误链路在哪里”，而不是只保存截图。为同一窗口变化轮次记录：

```text
timestamp / sequence / epoch
HarmonyOS application window bounds
owning RNInstance / RNSurface
RN Dimensions {width, height, scale, fontScale}
breakpoint / layoutScale / token
关键 wrapper onLayout
native view / Surface bounds（相关时）
route / selected item / scroll anchor
inset / crease 原始值、单位和转换后值（相关时）
```

不要把不同时间点的 window、Dimensions、onLayout 和 Surface 日志拼成一条因果链。

## 连接和页面确认

先确认 `hdc` 来自目标 DevEco SDK，再检查设备：

```bash
hdc list targets
hdc shell "aa dump -l"
```

记录设备标识、应用 bundleName、前台 Ability 和目标窗口形态。执行 dump 前必须确认应用已经停留在目标页面；优先选择页面独有标题、按钮文案、testID/nativeID 或组件组合作为页面指纹。

## 获取应用窗口

```bash
hdc shell "hidumper -s WindowManagerService -a '-a'"
```

从目标 bundle/mission 对应记录中提取 WindowId 和 WindowRect。WindowRect 通常是物理像素；它用于与 Host/Surface 对账，不能直接作为 RN style。

多窗口、多 RNInstance 或子窗口场景必须记录 owning window、instance 和 surface，避免把一个窗口的变化广播给所有 RN 根。

## 组件树与布局 dump

### hidumper inspector

```bash
hdc shell "hidumper -s WindowManagerService -a '-w {windowId} -inspector'"
```

适合检查节点属性、局部尺寸和组件层级。部分坐标相对父节点，不能单独用于判断是否超出整个窗口。

可按需要使用：

| 选项 | 用途 |
| --- | --- |
| `-element` | 元素树 |
| `-render` | 渲染树 |
| `-inspector` | 布局和属性 |
| `-frontend` | 页面路径和组件概况 |
| `-navigation` | 导航状态 |

### uitest dumpLayout

```bash
hdc shell "uitest dumpLayout -b {bundleName} -p /data/local/tmp/rnoh-layout.json"
hdc file recv /data/local/tmp/rnoh-layout.json {localPath}
```

`dumpLayout` 常见字段：

| 字段 | 含义 |
| --- | --- |
| `bounds` | 裁剪后的可见绝对区域，通常为物理 px |
| `origBounds` | 未裁剪的完整布局区域 |
| `type` / `text` / `id` | 页面和节点定位 |
| `clip` / `visible` | 裁剪和可见状态 |
| `clickable` / `scrollable` | 交互与滚动能力 |

先在 JSON 中搜索页面指纹。未命中时重新导航和 dump，不分析错误页面。

## 常见证据判定

### 截断和溢出

当目标节点 `origBounds` 大于 `bounds` 时，说明节点被祖先或窗口裁剪。继续向上找第一处宽高变为旧值、零、无界或固定值的祖先；不要直接在叶子增加任意尺寸。

### ScrollView/List

同时记录 viewport bounds、contentSize、滚动能力和可见 item key/index。内容高于 viewport 但不能滚动时检查祖先约束和 `style`/`contentContainerStyle` owner。列数变化时，绝对 pixel offset 不能单独证明业务位置连续。

### Image/媒体

比较容器和媒体的 `origBounds`、加载前后几何和 `resizeMode`。媒体宽度由高度和 `aspectRatio` 反推而远大于容器时，先形成锁定版本最小复现，再选择父容器持有比例或其他版本适用的约束方案。

### SafeArea/Avoid/Fold

分别记录原始 rect、来源 API、单位、转换后 layout unit 和最终 padding/absolute bounds。只允许在原生到 RN adapter 边界转换一次，不能通过视觉截图猜单位。

### Fabric 原生视图

按同一 epoch 对账：

```text
window → RN wrapper → native view → Surface/buffer → input coordinates
```

wrapper 正确、native view 错才进入 Fabric；view 正确、buffer 错才 resize/rebuild Surface；画面变换和触控逆变换必须成对验证。

## 可重复的交互

```bash
hdc shell "uitest uiInput click {x} {y}"
hdc shell "uitest uiInput swipe {fromX} {fromY} {toX} {toY} {velocity}"
hdc shell "uitest uiInput keyEvent Back"
```

自动交互只用于稳定到达同一页面和状态。不要把坐标脚本本身当作业务断言；每次操作后仍需用页面指纹和状态字段确认结果。

## 修复前后流程

1. 固定锁定版本、设备、窗口起始状态和页面指纹。
2. 采集异常状态的同轮次 window、Dimensions、派生值和 bounds。
3. 用一个最小约束、listener、memo、provider 或契约开关稳定开启/关闭现象。
4. 应用最小修复，保留相同到达路径。
5. 重新采集并对比首错点，而不是只比较最终截图。
6. 执行窄→宽→窄、宽→窄→宽、快速 resize、前后台和重复进入。
7. 分开报告静态、构建和运行证据；未执行的目标形态写 `not_verified`。

## 采集记录模板

```markdown
### Evidence epoch <id>

- Device / OS / SDK:
- RN / RNOH / CLI / HAR:
- Route and page fingerprint:
- Window mode and WindowRect:
- RN Dimensions:
- Derived breakpoint/scale/token:
- Wrapper/native/Surface bounds:
- Scroll anchor or business state:
- Insets/crease and units:
- First correct link:
- First broken link:
- Artifact paths:
```
