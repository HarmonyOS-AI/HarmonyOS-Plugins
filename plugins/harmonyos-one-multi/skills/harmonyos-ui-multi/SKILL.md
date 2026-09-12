---
name: harmonyos-ui-multi
description: 提供 HarmonyOS ArkUI 一多适配知识，用于分析或直接诊断、修复明确的局部布局问题，包括断点与响应式布局、导航挪移、留白或遮挡、安全区与软键盘、折展与悬停、横竖屏等。当前覆盖手机、折叠屏和平板，不覆盖 2in1/PC。工程扫描、批次 SPEC、完整验证和报告不由本 Skill 编排。
---

# HarmonyOS 一多 UI 知识与问题处理

## 适用范围

本 Skill 提供 ArkUI 页面、组件、导航、窗口和屏幕形态适配知识。相机链路与 H5 DOM/CSS 问题由对应领域能力处理。

当前设备范围是手机、折叠屏和平板。明确要求 2in1/PC 的任务应说明当前不支持，不得套用平板或超宽窗口方案冒充完成。

用户要求分析时只输出诊断和建议；用户要求修复时，在明确文件范围内直接修改。

## 使用方式

只读取当前问题的目标页面、组件和直接依赖，再根据症状加载对应域文件和必要的根因、策略或资产。修复时沿用工程已有断点、窗口和状态管理，只改首个错误约束及其必要依赖。修改后只执行基本编译验证；静态规则、设备运行、多模态和证据管理不属于本 Skill。

## 官方文档核实

先依据工程源码和本 Skill 知识定位问题。只有 API 名称、签名、API Level 或系统行为不确定，现有知识未覆盖，或编译结果与知识冲突时，才使用 `devecocli docs search` 查找候选文档，并用 `devecocli docs read <documentId>` 读取命中文档全文。现象类问题优先全库检索，明确的 API 问题可限定 `--catalog harmonyos-references`。

搜索摘要只用于选择文档，不直接作为结论。官方文档核实事实，本 Skill 约束方案选择；API 可用性以当前工程 SDK 类型定义和实际编译为准，运行行为以设备证据为准。

## 知识路由

| 症状或变化 | 必读域文件 |
|---|---|
| 断点、增列、分栏、栅格、留白、Flex 溢出、Tabs/侧边导航 | `domains/size-layout.md` |
| 分屏、悬浮窗、自由窗口 | `domains/window-form.md` |
| 状态栏、导航条、挖孔、软键盘、沉浸式与安全区 | `domains/avoid-area.md` |
| 折叠、展开、悬停、折痕和连续性 | `domains/fold-form.md` |
| 横竖屏、旋转策略和方向语义 | `domains/orientation.md` |
| RTL、深浅色、字体缩放与无障碍 | `domains/global-adaptation.md` |

领域文件给出决策入口；需要详细根因时读 [root-causes.md](references/root-causes.md)，需要结构选型时读 [layout-strategies.md](references/layout-strategies.md)，需要设备尺寸时只查 [device-matrix.md](references/device-matrix.md) 相关行，需要复用代码时读 [assets-catalog.md](references/assets-catalog.md)。

## 实施约束

- 保留窄屏页面的信息顺序、交互、路由和业务状态。
- 按窗口或容器实际可用宽高决策，不用设备型号、物理分辨率或固定像素代替断点。
- 优先复用工程已有基础设施；不存在时才引入最小封装，禁止每页建一套窗口监听。
- 不把“居中限宽”当作所有宽屏页的默认方案；按内容语义在重复、挪移、分栏和必要缩进中选择。
- 不主动将 `NavigationMode.Stack` 改为 `Auto/Split`；只有用户明确要求，或工程已有分栏语义时才使用。
- 修改或重排组件时保留既有 `.id()` 值，避免破坏 UI 自动化用例。
- 高保真是方案的可视化，不冒充已实现效果。需要多设备视觉方案时读 [hifi-html.md](references/hifi-html.md)；输出位置、命名、状态和确认方式由调用方决定。

## 编译验证

修改后先执行工程自带构建，优先使用：

```bash
devecocli build
```

任务涉及 HAP/HAR/HSP 的目标设备声明时，再读 [module-device-types.md](references/module-device-types.md)。本 Skill 不启动设备、不执行多模态测试，也不维护验证证据；构建通过只表示代码可编译，运行和视觉结果仍为未验证。

## 质量分层

用户要求完整适配、质量评估或指定等级时，读取 [质量目标与领域验收](references/quality-levels.md)。沿用当前范围和实现路线，区分目标等级与证据已证明的等级；局部修复不自动启动全量评级。
