<!--
Merged from flutter-purax-adaptation/references/ (identical copy also existed in
flutter-pura-x-max-ux-20260731/references/purax/).
Role: deep-dive reference material for foldable scenes PX-01..PX-05; read on demand
via scenarios/foldable-catalog.md. Internal relative links stay valid inside purax/.
Per references/index.md this material is reference-only and never overrides SKILL.md.
-->
# 铰链/折痕区域避让指南

## 目标

在 Flutter PuraX 折叠设备上，确保关键内容和交互不被铰链遮挡。

## 常用 API

### AvoidAreaApi

```dart
import 'package:hadss_avoid_area/hadss_avoid_area.dart';

// 获取窗口各方向的安全区域
final avoidArea = await AvoidAreaApi.getWindowAvoidArea();

// 监听安全区域变化（折叠状态变化、键盘弹出等）
AvoidAreaApi.addAvoidAreaListener((AvoidArea avoidArea) {
  // 根据 avoidArea 调整布局
});
```

### AvoidAreaType 枚举

| 类型 | 说明 |
|------|------|
| `system` | 系统状态栏、导航栏区域 |
| `cutout` | 异形屏挖孔、刘海区域 |
| `systemGesture` | 系统手势区域 |
| `keyboard` | 软键盘占据区域 |
| `navigationIndicator` | 导航指示条区域 |

## 方案选择

| 场景 | 推荐方案 | 铰链避让方式 |
|------|---------|------------|
| 视频播放器（简单交互） | FolderStack | 自动 |
| 固定分栏场景 | FoldSplitContainer | 自动 |
| 复杂页面 | 自定义实现（AvoidAreaApi 手动获取） | 手动 |

## 方案一：FolderStack 自动避让

FolderStack 自动处理铰链避让，只需指定 `upperItems`：

```dart
FolderStack(
  upperItems: ['video_player'],
  children: [
    Container(
      key: const ValueKey('video_player'),
      child: VideoPlayer(_controller),
    ),
    Positioned(
      bottom: 0,
      child: ControlBar(),  // 自动避开铰链
    ),
  ],
)
```

## 方案二：自定义实现

当自定义实现时，需要手动获取铰链信息并计算避让：

```dart
import 'package:hadss_avoid_area/hadss_avoid_area.dart';

class HingeAwarePage extends StatefulWidget {
  @override
  State<HingeAwarePage> createState() => _HingeAwarePageState();
}

class _HingeAwarePageState extends State<HingeAwarePage> {
  bool _isHalfFolded = false;
  double _hingePosition = 0;

  @override
  void initState() {
    super.initState();
    _checkFoldStatus();
    AvoidAreaApi.addAvoidAreaListener(_onAvoidAreaChanged);
  }

  Future<void> _checkFoldStatus() async {
    final area = await AvoidAreaApi.getWindowAvoidArea();
    _updateLayout(area);
  }

  void _onAvoidAreaChanged(AvoidArea area) {
    _updateLayout(area);
  }

  void _updateLayout(AvoidArea area) {
    setState(() {
      // 根据 avoidArea 判断是否处于半折叠态
      // 计算铰链位置，调整 _hingePosition
    });
  }

  @override
  void dispose() {
    AvoidAreaApi.removeAvoidAreaListener(_onAvoidAreaChanged);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return _isHalfFolded
        ? Column(
            children: [
              SizedBox(
                height: _hingePosition,
                child: ContentWidget(),
              ),
              // 铰链间隙
              Expanded(
                child: ControlWidget(),
              ),
            ],
          )
        : Stack(
            children: [
              ContentWidget(),
              Positioned(bottom: 0, child: ControlWidget()),
            ],
          );
  }
}
```

## 关键要点

| 要点 | 说明 |
|------|------|
| **优先使用 FolderStack** | 简单场景自动避让，无需手动计算 |
| **自定义实现必须处理坐标映射** | 铰链信息的坐标需要转换到页面坐标系 |
| **监听生命周期** | `dispose()` 中必须取消监听 |
| **避让区不影响折叠/展开态** | 仅在半折叠态启用避让，其他态保持原有布局 |

## 常见问题

| 问题现象 | 可能原因 | 排查方向 |
|---------|---------|---------|
| 控制栏被铰链截断 | 使用 Stack + Positioned 固定底部位置 | 改用 FolderStack 或手动判断半折叠态 |
| 弹窗被铰链劈开 | 未做半折叠态适配 | 半折叠时调整弹窗位置或内容布局 |
| 铰链区域误入交互控件 | 未标记 upperItems | 检查 FolderStack 的 upperItems 配置 |
