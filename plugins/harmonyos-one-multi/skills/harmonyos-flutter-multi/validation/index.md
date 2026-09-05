# 验证索引

1. 从 [acceptance-matrix.md](acceptance-matrix.md) 选择覆盖形态，并对照 [ux-px-checklist.md](ux-px-checklist.md) 按 UX/PX ID 逐项验收。
2. 按 [diagnostic-evidence.md](diagnostic-evidence.md) 留存能证明根因和修复的证据。
3. 执行 [regression-checklist.md](regression-checklist.md)。
4. 在 [known-risks.md](known-risks.md) 中确认未覆盖项并明确残余风险；范围与缺口对照见 [coverage.md](coverage.md)。

只改 Dart 时运行格式化、静态检查和相关测试；改 OHOS 宿主、配置或插件时还要重新构建、安装并做真机/模拟器验证。
