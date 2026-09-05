import 'package:flutter/widgets.dart';

class HingeSplit extends StatelessWidget {
  const HingeSplit({
    super.key,
    required this.leading,
    required this.trailing,
    required this.hingeExtent,
    this.vertical = true,
  });

  final Widget leading;
  final Widget trailing;
  final double hingeExtent;
  final bool vertical;

  @override
  Widget build(BuildContext context) {
    final children = <Widget>[
      Expanded(child: leading),
      SizedBox(
        width: vertical ? 0 : hingeExtent,
        height: vertical ? hingeExtent : 0,
      ),
      Expanded(child: trailing),
    ];
    return Flex(direction: vertical ? Axis.vertical : Axis.horizontal, children: children);
  }
}
