# Flutter OHOS One-Multi Adaptation

该 skill 将 Flutter 鸿蒙一多、阔折叠 UX 与 Pura X 折展知识统一为一个可渐进读取的方案。根入口只负责路由；场景定义、Flutter 原生实现、HADSS 实现和 OHOS 平台能力分别维护。

```text
harmonyos-flutter-multi/
├── SKILL.md
├── core/
├── scenarios/
├── flutter-native/
├── hadss/
├── ohos-platform/
├── validation/
├── examples/
├── test-cases/
└── references/          # 深读层：pura-x-patterns / purax/ / scenes / dpi-guide / pura-x-guide
```

每个一级知识目录均提供 `index.md`。标准路径为 `SKILL.md → core → scenarios → flutter-native|hadss → ohos-platform（按需）→ validation`。两条实现路线采用并列文件层级，不在同一个实现文件中混写。

路由层只保留摘要与决策要点；源 skill 的原文详册（P-* 完整代码、折展详册、16 场景指南、DPI 策略、按 ID 验收清单）回填在 `references/` 与 `validation/` 作为深读层，见 [references/source-map.md](references/source-map.md)。
