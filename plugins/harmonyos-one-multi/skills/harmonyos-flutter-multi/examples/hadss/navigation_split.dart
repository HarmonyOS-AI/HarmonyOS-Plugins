import 'package:flutter/material.dart';
import 'package:hadss_adaptive_layout/hadss_adaptive_layout.dart';

/// NavigationSplitContainer 列表-详情双栏模板 — 聊天 App 场景
/// 用法: NavigationSplitChatApp(navBar: 会话列表, content: 聊天详情)
///
/// < 600dp → 单栏 stack 模式（折叠态手机）
/// >= 600dp → 双栏 split 模式（展开态 / 平板）
class NavigationSplitChatApp extends StatefulWidget {
  final Widget Function(BuildContext context, String? selectedId) navBar;
  final Widget Function(BuildContext context, String? selectedId) content;
  final Widget emptyPlaceholder;

  const NavigationSplitChatApp({
    super.key,
    required this.navBar,
    required this.content,
    required this.emptyPlaceholder,
  });

  @override
  State<NavigationSplitChatApp> createState() => _NavigationSplitChatAppState();
}

class _NavigationSplitChatAppState extends State<NavigationSplitChatApp> {
  String? _selectedId;

  @override
  Widget build(BuildContext context) {
    return NavigationSplitContainer(
      mode: NavigationSplitMode.auto,
      navBarWidth: 320,
      minNavBarWidth: 260,
      maxNavBarWidth: 400,
      autoHideNavBar: true,
      navBar: widget.navBar(context, _selectedId),
      content: _selectedId != null
          ? widget.content(context, _selectedId)
          : widget.emptyPlaceholder,
    );
  }
}
