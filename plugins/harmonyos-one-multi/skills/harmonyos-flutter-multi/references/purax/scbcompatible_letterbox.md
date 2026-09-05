<!--
Merged from flutter-pura-x-max-ux-20260731/references/purax/scbcompatible_letterbox.md.
Role: PX-06 short-form digest of the SCBCompatible letterbox; the full manual is
ohos-platform/scbcompatible-letterbox.md (authoritative).
-->
# PX-06 内屏横屏系统兼容信箱（SCBCompatible）

> Flutter × 鸿蒙阔折叠：两侧蓝底/紫渐变、竖条窗口、三点把手。  
> 详细步骤与命令见同目录姊妹文档逻辑，并与 `flutter-pura-x-max-ux` UX-11 手册对齐。

## 问题描述

Pura X Max（及同类阔折叠）**内屏展开横屏**时，应用未铺满，左右系统兼容底；WMS 可见应用窗宽远小于屏宽，并伴随 `SCBCompatible` 层。

## 根因分析

1. **主因**：系统兼容显示（信箱/柱箱），非 Flutter `maxWidth`。  
2. **加重因素**：仅 `phone`、方向被 Flutter 映射为 `LOCKED`、自由多窗/`split`+`floating`、脏安装导致配置未更新。  
3. **已证伪**：单独 `setWindowLayoutFullScreen` / 无参或沉浸 `maximize` / `resize` 在部分机型上**不足以**退出 `SCBCompatible`。

## 通用修复方案

### A. 声明与窗口模式（优先）

- `deviceTypes`: `["phone","tablet"]`
- `supportWindowMode`: **`["fullscreen"]` only**（业务不要分屏时）
- 运行时：`windowStage.setSupportedWindowModes([FULL_SCREEN])`
- 去掉易导向自由多窗的 `preferMultiWindowOrientation` / 过紧 ratio（按项目评估）

### B. 运行时强制铺满

- `setWindowLayoutFullScreen(true)`
- `resetAspectRatio()`
- `maximize(MaximizePresentation.ENTER_IMMERSIVE)`
- 仍 letterbox：`resize(display.width, display.height)`
- `windowSizeChange` / `foldStatusChange` 后延迟重试

### C. 方向（OH Flutter）

- 避免 `portraitUp+landscapeLeft+Right` → OH `LOCKED`
- OHOS 启动可不设 `SystemChrome` 方向；恢复勿乱写空列表 `UNSPECIFIED`

### D. 安装验收

- **卸载再装**或提高 `versionCode`
- WMS：`应用宽 ≈ 屏宽`，无窄窗 + `SCBCompatible` 组合
- `bm dump` 与 HAP 内 `module.json` 一致

## 方案对照

| 方案 | 内容 | 何时用 |
| --- | --- | --- |
| A（推荐） | 仅 fullscreen + `setSupportedWindowModes` + 沉浸 maximize | 系统蓝底 / SCBCompatible |
| B | hadss 断点布局 | 窗口已满后的信息密度 / 分栏 |
| 原生 Flutter 限宽修复 | 去 `maxWidth` 居中 | 仅 UX-02（窗口已满） |

## 验证

```bash
hdc shell "hidumper -s WindowManagerService -a '-a'"   # 本应用窗宽 vs 屏宽；SCBCompatible
hdc shell "bm dump -n <bundle>"                        # versionCode / supportWindowMode
```
