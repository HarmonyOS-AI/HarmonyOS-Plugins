import 'package:flutter/widgets.dart';

class AdaptiveListDetail extends StatelessWidget {
  const AdaptiveListDetail({
    super.key,
    required this.list,
    required this.detail,
    required this.showDetail,
  });

  final Widget list;
  final Widget detail;
  final bool showDetail;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, constraints) {
      if (constraints.maxWidth < 600) return showDetail ? detail : list;
      return Row(children: [SizedBox(width: 320, child: list), Expanded(child: detail)]);
    });
  }
}
