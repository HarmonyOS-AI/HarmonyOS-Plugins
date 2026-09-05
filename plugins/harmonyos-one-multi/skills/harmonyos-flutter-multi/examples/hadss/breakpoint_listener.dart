import 'package:flutter/material.dart';
import 'package:hadss_adaptive_layout/hadss_adaptive_layout.dart';

/// 断点驱动的动态列数 GridView 模板
/// 用法: AdaptiveGrid(cards: yourCardList)
class AdaptiveGrid extends StatefulWidget {
  final List<Widget> cards;
  const AdaptiveGrid({super.key, required this.cards});

  @override
  State<AdaptiveGrid> createState() => _AdaptiveGridState();
}

class _AdaptiveGridState extends State<AdaptiveGrid> {
  int _crossAxisCount = 2;

  @override
  void initState() {
    super.initState();
    _crossAxisCount = _mapBreakpointToColumns(
      BreakpointManager.instance.currentBreakpoint.widthBreakpoint,
    );
    BreakpointManager.instance.addListener(_onBreakpointChanged);
  }

  @override
  void dispose() {
    BreakpointManager.instance.removeListener(_onBreakpointChanged);
    super.dispose();
  }

  void _onBreakpointChanged(BreakpointData data) {
    final count = _mapBreakpointToColumns(data.widthBreakpoint);
    if (count != _crossAxisCount) {
      setState(() => _crossAxisCount = count);
    }
  }

  int _mapBreakpointToColumns(WidthBreakpoint bp) {
    switch (bp) {
      case WidthBreakpoint.xs: return 1;
      case WidthBreakpoint.sm: return 2;
      case WidthBreakpoint.md: return 3;
      case WidthBreakpoint.lg: return 4;
      case WidthBreakpoint.xl: return 5;
    }
  }

  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: _crossAxisCount,
        childAspectRatio: 0.75,
      ),
      itemBuilder: (ctx, i) => widget.cards[i],
      itemCount: widget.cards.length,
    );
  }
}
