# 父约束、滚动视口与媒体几何

## 先定位哪一层失去边界

`useWindowDimensions()` 正确不代表页面拥有正确可用空间。按下面链路逐层记录 `onLayout`：

```text
application window
  → RNSurface / RN root
  → Navigation scene / page root
  → ScrollView 或 List viewport
  → content container
  → child / image / actions
```

第一处从正确宽高变成 `0`、旧值、无限增长或被固定值截断的祖先才是修复点。根 viewport 已错误时转 `RN-04`；根正确、子树失去约束时留在 `RN-09`。

## Flex 与百分比的边界条件

- RN 布局数字是 layout units，不是物理像素。固定值只用于语义上固定的组件，不用设计稿整屏宽高锁住页面。
- `flex` 子项只有在父级存在可分配空间时才能增长；父级宽高为 0 或沿链缺少 `flex` 时，给叶子加 `flex: 1` 无效。
- 百分比宽高依赖父级已确定尺寸。`height: '100%'` 不能自动为无界祖先创造高度。
- RN 的 `flexShrink` 默认是 `0`。Row 中文本/主体需要收缩时显式建立 grow/shrink 关系，同时保留操作区；`minWidth: 0` 按锁定版本验证。
- `position: 'absolute'` 的节点不参与正常流，不能靠它撑开父容器或为后续内容预留空间。

一个常见的有界页面骨架是：导航 scene 有尺寸、page root `flex: 1`、ScrollView/List 自身 `flex: 1`，padding 与最小内容高度放在 `contentContainerStyle`。不要机械复制；以实际导航和组件层级的 `onLayout` 证明每一层。

## ScrollView 与 List

- ScrollView 必须拥有有界高度。不能滚动或完全空白时，先检查所有祖先，而不是直接设置屏幕固定高度。
- `style` 控制 viewport；`contentContainerStyle` 控制内部内容。把 `flex: 1` 只放在 content container 可能把内容锁成一屏，需根据“内容至少填满”还是“内容自由增长”选择 `flexGrow`。
- 长数据优先使用 FlatList/SectionList。列数变化时同步审计 `extraData`、`renderItem`、`getItemLayout`、裁剪和业务锚点。
- 横向分页的 `snapToInterval`、page width 和初始 offset 必须由当前 viewport 派生，不能使用物理 screen 或启动宽度。
- 宽而短的横屏/自由窗口单独检查：标题、操作区和错误态都必须可达；必要时滚动，不用宽屏断点假定高度充足。

## 图片与媒体几何

- 网络图片和 data URI 没有可靠的本地静态尺寸时，显式提供容器几何；优先使用受约束宽度加 `aspectRatio`，避免同时硬编码随窗口变化的宽高。
- 明确业务语义后选择 `contain`（完整展示）或 `cover`（允许裁切）；`stretch` 可能改变源宽高比。
- PixelRatio 只用于请求匹配密度的资源或物理像素边界，显示盒仍使用 RN layout units。
- 骨架、加载失败和真实资源必须使用兼容几何，避免图片加载后造成断点抖动或列表测量缓存失效。

## 验证

至少记录窄/宽、宽短窗口、默认/大字体、内容不足/超长、图片加载前后，以及窄→宽→窄。每态保存 window、各级 `onLayout`、viewport/contentSize、可见业务锚点；相同最终窗口必须收敛到相同约束结果。

依据：

- React Native Height and Width：flex/百分比依赖具有有效尺寸的父级。<https://reactnative.dev/docs/height-and-width>
- React Native ScrollView：ScrollView 需要有界高度，父级链必须传递约束。<https://reactnative.dev/docs/scrollview>
- React Native Flexbox：RN 默认 `flexShrink: 0`，且与 Web Flexbox 存在默认值差异。<https://reactnative.dev/docs/flexbox>
- React Native Images：网络图片需要显式几何；Image resizeMode 决定保持比例、裁切或拉伸。<https://reactnative.dev/docs/images>

