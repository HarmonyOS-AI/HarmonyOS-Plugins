import 'package:flutter/material.dart';
import 'package:hadss_avoid_area/hadss_avoid_area.dart';

/// FolderStack 铰链避让模板 — 视频播放器场景
/// 用法: 替换原有的 Stack 为 FolderStack，用 ValueKey 标记移到上半屏的组件
///
/// 半折叠时: 视频自动移到上半屏，控制栏留在下半屏
/// 非折叠时: 表现与普通 Stack 一致
class HingeSafePlayer extends StatelessWidget {
  final Widget videoPlayer;
  final Widget controlBar;

  const HingeSafePlayer({
    super.key,
    required this.videoPlayer,
    required this.controlBar,
  });

  @override
  Widget build(BuildContext context) {
    return FolderStack(
      upperItems: ['video_player'],
      children: [
        Container(
          key: const ValueKey('video_player'),
          child: videoPlayer,
        ),
        Positioned(
          bottom: 0,
          left: 0,
          right: 0,
          child: controlBar,
        ),
      ],
    );
  }
}
