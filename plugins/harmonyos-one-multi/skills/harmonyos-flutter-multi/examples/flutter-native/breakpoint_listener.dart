import 'package:flutter/widgets.dart';

enum WidthClass { xs, sm, md, lg, xl }

WidthClass widthClass(double width) => switch (width) {
      < 320 => WidthClass.xs,
      < 600 => WidthClass.sm,
      < 840 => WidthClass.md,
      < 1440 => WidthClass.lg,
      _ => WidthClass.xl,
    };

class BreakpointBuilder extends StatelessWidget {
  const BreakpointBuilder({super.key, required this.builder});

  final Widget Function(BuildContext context, WidthClass widthClass) builder;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) =>
          builder(context, widthClass(constraints.maxWidth)),
    );
  }
}
