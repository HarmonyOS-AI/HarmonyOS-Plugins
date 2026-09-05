<!--
Merged from flutter-purax-adaptation/references/ (identical copy also existed in
flutter-pura-x-max-ux-20260731/references/purax/).
Role: deep-dive reference material for foldable scenes PX-01..PX-05; read on demand
via scenarios/foldable-catalog.md. Internal relative links stay valid inside purax/.
Per references/index.md this material is reference-only and never overrides SKILL.md.
-->
# 开合连续性保障指南

## 目标

确保 Flutter 应用在 PuraX 折叠/展开过程中保持滚动位置、输入内容、媒体播放进度的连续性。

## 核心原则

- **采用断点驱动布局刷新，而非直接监听 foldStatus 驱动**：使用 `BreakpointManager` 的断点变化作为布局刷新的统一入口
- **折展逻辑与业务状态分离**：折展适配不得改写业务显示状态机
- **明确恢复链路触发时机**：禁止基于过期视口恢复

## 场景 1：列表滚动位置保持

折展可能导致 GridView/ListView 重建，需要通过记录可见项索引来恢复位置。

### 策略

1. 在断点变化前记录当前滚动到的第一个可见项索引
2. 断点变化后使用 `ScrollController.jumpTo()` 或 `animateTo()` 恢复
3. 注意折展后列数可能变化，需要重新计算偏移

```dart
int _savedIndex = 0;
bool _needsScrollRestore = false;

void _onBreakpointChanged(BreakpointData data) {
  // 保存当前滚动位置
  _savedIndex = (_scrollController.offset / _itemHeight).round();
  _needsScrollRestore = true;

  setState(() { /* 更新布局 */ });
}

void _restoreScrollIfNeeded() {
  if (!_needsScrollRestore) return;
  WidgetsBinding.instance.addPostFrameCallback((_) {
    final targetOffset = _savedIndex * _newItemHeight;
    _scrollController.jumpTo(
      targetOffset.clamp(0.0, _scrollController.position.maxScrollExtent),
    );
    _needsScrollRestore = false;
  });
}
```

## 场景 2：输入内容保持

折展时避免输入框内容丢失，通常因为 Widget 重建导致 `TextEditingController` 状态丢失。

### 策略

- 将 `TextEditingController` 放在 `State` 中而非 `build()` 中创建
- 折展重建时保留对同一个 Controller 的引用
- 不要让 Controller 随 Widget 重建而销毁

## 场景 3：视频播放进度保持

### 策略

1. 折展前快照进度和播放状态
2. 折展后双触发恢复（onPrepared 事件 + 定时器兜底）
3. 抑制 autoplay 抢跑

```dart
double _savedPosition = 0;
bool _wasPlaying = false;

void _onBreakpointChanging() {
  _savedPosition = _videoController.value.position.inSeconds.toDouble();
  _wasPlaying = _videoController.value.isPlaying;
}

void _onBreakpointChanged(BreakpointData data) {
  setState(() { /* 重建布局 */ });
  _restoreVideoState();
}

void _restoreVideoState() {
  WidgetsBinding.instance.addPostFrameCallback((_) {
    _videoController.seekTo(Duration(seconds: _savedPosition.toInt()));
    if (_wasPlaying) {
      _videoController.play();
    }
  });
}
```

## 场景 4：图片画质保持

折展后图片需要按新窗口尺寸重新加载适配分辨率。

### 策略

- 网络图片通过 URL 参数切换分辨率
- 本地图片使用 `cacheWidth` / `cacheHeight` 动态调整
- 折展后通过断点变化触发重新加载

## 验证清单

- 折叠/展开后滚动位置不偏移
- 输入框内容不丢失
- 视频播放进度一致，暂停/播放状态正确
- 图片无模糊或变形
- 未引入额外操作步骤
