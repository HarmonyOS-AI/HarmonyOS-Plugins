<!--
Merged from flutter-purax-adaptation/references/ (identical copy also existed in
flutter-pura-x-max-ux-20260731/references/purax/).
Role: deep-dive reference material for foldable scenes PX-01..PX-05; read on demand
via scenarios/foldable-catalog.md. Internal relative links stay valid inside purax/.
Per references/index.md this material is reference-only and never overrides SKILL.md.
-->
# 悬停态分屏适配指南

## 目标

在 Flutter PuraX 折叠设备悬停态下实现分屏布局，将展示区与操作区分离。

## 方案选择

| | FolderStack | FoldSplitContainer | 自定义实现 |
| --- | --- | --- | --- |
| 适用场景 | 视频全屏播放等交互少的场景 | 固定主次分栏场景（如游戏画面+操作区） | 页面布局复杂或需要自定义触发条件 |
| 铰链避让 | 自动 | 自动 | 需手动通过 AvoidAreaApi 获取 |
| 自定义布局 | 支持 | 不支持（固定二分栏/三分栏） | 支持 |
| 开发难度 | 简单 | 简单 | 困难 |
| 来源包 | hadss_avoid_area | hadss_avoid_area | hadss_avoid_area / 自建 |

## 方案一：FolderStack（推荐，适用于大多数场景）

`FolderStack` 继承自 `Stack`，通过 `upperItems` 指定需要移到上半屏的子组件（通过 `ValueKey` 匹配），其他组件自动堆叠在下半屏，铰链区域自动避让。

### 基本用法

```dart
import 'package:hadss_avoid_area/hadss_avoid_area.dart';

FolderStack(
  upperItems: ['video_player'],
  children: [
    Container(
      key: const ValueKey('video_player'),
      child: VideoPlayer(_controller),
    ),
    Positioned(
      bottom: 0,
      child: ControlBar(),
    ),
  ],
)
```

### 关键说明

1. `upperItems` 中的字符串必须与子组件的 `ValueKey<String>` 值匹配
2. 当设备非半折叠时，`FolderStack` 退化为普通 `Stack`，布局不受影响
3. 半折叠时，匹配 `upperItems` 的组件被放入上半屏，其余放入下半屏
4. 铰链区域自动避让

## 方案二：FoldSplitContainer（适用于固定分栏场景）

`FoldSplitContainer` 在展开/折叠/半折叠三种状态下分别配置布局：

```dart
import 'package:hadss_avoid_area/hadss_avoid_area.dart';

FoldSplitContainer(
  primary: VideoPlayer(_controller),
  secondary: ControlBar(),
  foldedLayoutOptions: FoldedRegionLayoutOptions(
    regionCount: 1,
  ),
  expandedLayoutOptions: ExpandedRegionLayoutOptions(
    regionCount: 1,
  ),
  hoverModeLayoutOptions: HoverModeRegionLayoutOptions(
    regionCount: 2,
    extraRegionPosition: ExtraRegionPosition.bottom,
  ),
)
```

### 布局配置参数

| 参数 | 所属配置 | 说明 |
| --- | --- | --- |
| `regionCount` | 折叠/展开/悬停 | 显示几个区域（1-3） |
| `splitRatio` | 区域间比例 | 如 0.5 表示各占 50% |
| `extraRegionPosition` | 悬停态 | 额外区域位置（top/bottom） |

## 方案三：自定义实现

当 FolderStack 和 FoldSplitContainer 无法满足需求时，手动监听折叠状态并自行分配布局。

### 实现步骤

1. 通过 `AvoidAreaApi.addAvoidAreaListener` 监听折叠状态变化
2. 根据状态切换 UI 布局（show/hide 控制区、调整 `Positioned` 等）
3. 在 `dispose()` 中取消监听

```dart
@override
void initState() {
  super.initState();
  AvoidAreaApi.addAvoidAreaListener(_onAvoidAreaChanged);
}

void _onAvoidAreaChanged(AvoidArea area) {
  // 根据 area 的折叠状态切换布局
  setState(() {
    _isHalfFolded = /* 判断半折叠逻辑 */;
  });
}

@override
void dispose() {
  AvoidAreaApi.removeAvoidAreaListener(_onAvoidAreaChanged);
  super.dispose();
}

@override
Widget build(BuildContext context) {
  if (_isHalfFolded) {
    return Column(
      children: [
        Expanded(child: VideoPlayer(_controller)),  // 上半屏
        ControlBar(),  // 下半屏
      ],
    );
  }
  return Stack(
    children: [
      VideoPlayer(_controller),
      Positioned(bottom: 0, child: ControlBar()),
    ],
  );
}
```

## PuraX 特殊考量

- **外屏限制**：PuraX 外屏为 1:1 方屏，仅支持全屏模式，不支持分屏。应隐藏状态栏和导航栏，将空间释放给内容区。
- **外屏小方屏沉浸式浏览**：滚动浏览时应渐进隐藏标题栏和 Tab 栏以释放空间，滚动回顶时恢复。
