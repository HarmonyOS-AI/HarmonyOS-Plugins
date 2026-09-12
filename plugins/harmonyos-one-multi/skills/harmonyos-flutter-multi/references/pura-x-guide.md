<!--
Merged from flutter-pura-x-max-ux-20260731/ShuoMing.md (human-facing guide,
Chinese filename kept as pura-x-guide.md for portability).
Role: long-form human documentation of the original UX skill: principles, per-ID
case walkthroughs, workflow and Q&A. The old skill name flutter-pura-x-max-ux and
its flat layout descriptions are historical; routing always defers to SKILL.md.
Link mapping: patterns.md -> ./pura-x-patterns.md; checklist.md -> ../validation/ux-px-checklist.md;
references/purax/* -> ./purax/*; assets/* -> ../examples/hadss/*.
-->
# Flutter × Pura X Max UX + 折展适配 Skill 详细说明

| 项 | 内容 |
| --- | --- |
| Skill 名称 | `flutter-pura-x-max-ux` |
| 文档日期 | 2026-07-31 |
| 能力范围 | **UX 缺陷修复（UX-01～24）** + **折展适配（PX-01～06 / hadss 双方案）** |
| 适用范围 | 任意 Flutter 应用（含 HarmonyOS / OpenHarmony Flutter） |
| 目标设备 | 华为 Pura X / Pura X Max 及同类阔折叠、分屏/悬浮窗 |
| 读者 | 人（产品/开发/测试）与 Agent；Agent 执行以 `SKILL.md` 为准 |

常见安装位置：

| 位置 | 路径示例 |
| --- | --- |
| Cursor 用户级 | `~/.cursor/skills/flutter-pura-x-max-ux/` |
| 项目级 | `<仓库>/.cursor/skills/flutter-pura-x-max-ux/` |
| 备份包 | `~/Downloads/flutter-pura-x-max-ux-20260731/` |

---

## 1. 是什么、解决什么问题

本 Skill 是一套给 **Cursor / DevEco Code / Claude Code 等 Agent** 使用的规范包，用于在 **阔折叠（尤其 Pura X / Pura X Max）** 上，对 Flutter 应用做：

1. **UX 缺陷诊断与修复**  
   截断、溢出、键盘重叠、两侧留白/蓝底信箱、相机未铺满、空态被挡、日历弹层溢出、地图条件卡过高、固定宽 Row 溢出、`DraggableScrollableSheet` 断言等。

2. **折展形态适配**  
   FoldStatus 监听、悬停态分屏、折痕/铰链避让、断点响应式（Grid / NavigationSplit）、开合连续性、hadss 与原生 Flutter **双方案**。

它把原先两套能力合成统一入口：

| 来源 | 并入后 |
| --- | --- |
| 早期 `flutter-pura-x-max-ux` | UX-01～24 + `patterns.md` 修复模式 |
| 原 `flutter-purax-adaptation` | PX-01～06 + `references/purax/` + `assets/` + `test-cases/` |

**一句话：** 遇到「Flutter + 鸿蒙折叠屏 / 外屏矮 / 内屏横屏 / 悬停 / 蓝底 / OVERFLOW」时，优先用本 Skill。

---

## 2. 核心原则（必须遵守）

1. **不按机型名硬编码**  
   禁止 `if (device == 'PuraXMax')`。一律用 `MediaQuery` / `LayoutBuilder` / 断点（xs～xl）。

2. **先分流再动手**  
   - **UX-11 / PX-06**：系统兼容信箱（蓝/紫渐变底、三点把手、`SCBCompatible`）→ 先改窗口声明 / Ability，再谈布局。  
   - **UX-02**：窗口已经铺满，只是内容被 `maxWidth` 限窄 → 改 Flutter 全宽/分栏。  
   - **PX-01～05**：悬停、折痕、断点、连续性、折展 bug。

3. **折展给双方案**  
   - **方案 A**：`hadss_adaptive_layout` / `hadss_avoid_area`（有依赖时优先）  
   - **方案 B**：原生 `MediaQuery` + 自研断点 / FolderStack 等价实现  

4. **悬停必联动折痕**  
   命中悬停分屏（PX-01）时，折痕避让（PX-02）默认一并考虑。

5. **热重载边界**  
   只改 Dart 布局多数可用 `r`/`R`；改 `module.json5` / EntryAbility / 窗口模式必须 **卸载重装或提高 versionCode**。

---

## 3. 目录结构与各文件职责

```
flutter-pura-x-max-ux/
├── SKILL.md                 # Agent 主入口：触发条件、工作流、UX/PX 目录、工程规范
├── patterns.md              # 每个 UX-ID 对应的 P-* 代码修复模式 + 反模式
├── checklist.md             # 外屏/内屏/横屏/悬停验收矩阵（可贴进 PR）
├── coverage.md              # 覆盖对照、边界、与旧 skill 关系
├── 说明.md                  # 本文件（给人看的详细说明）
├── assets/                  # 可参考 Dart 示例
│   ├── breakpoint_listener.dart
│   ├── folder_stack_example.dart
│   └── navigation_split_example.dart
├── test-cases/              # 烟雾 / 场景 / 真实故障用例 JSON
│   ├── smoke/
│   ├── scene-functional/
│   └── real-world/
└── references/
    ├── ux11-scbcompatible-letterbox.md   # UX-11 详册（WMS 取证与修复顺序）
    └── purax/                            # 折展详读材料
        ├── README.md
        ├── official_adaptation_guide.md
        ├── fold_status_detection.md
        ├── hover_state_interaction.md
        ├── crease_avoidance.md
        ├── breakpoint_layout.md
        ├── fold_continuity.md
        ├── bug_fix_cases.md
        ├── scbcompatible_letterbox.md    # PX-06 短版
        └── scenario_development_cases.md
```

| 文件 | 谁读 | 作用 |
| --- | --- | --- |
| `SKILL.md` | Agent（自动或点名） | 何时启用、怎么分流、改什么、怎么验收 |
| `patterns.md` | Agent | 可复制的 Flutter 结构约束 |
| `checklist.md` | Agent / 测试 | 回归勾选 |
| `coverage.md` | 维护者 | 覆盖是否够、什么不该用本 skill |
| `说明.md` | 人 | 安装、能力全景、用法、边界 |
| `references/ux11-…` | Agent / 开发 | 蓝底信箱专项 |
| `references/purax/` | Agent / 开发 | 悬停/折痕/断点/连续性详解 |
| `assets/` | 开发 | 示例代码 |
| `test-cases/` | 评测 / 维护 | 路由与输出字段预期 |

---

## 4. 何时会被触发

### 4.1 自动匹配（靠 `SKILL.md` 的 description）

Agent 识别到以下信号之一时，应加载本 Skill：

**设备 / 形态**

- Pura X、Pura X Max、阔折叠、外屏 / 内屏  
- 折叠 / 展开 / 悬停、分屏 / 悬浮窗  

**技术栈**

- Flutter、HarmonyOS Flutter、OpenHarmony Flutter  

**症状关键词**

- 截断、无法滑动、字体重叠、两侧留白 / 蓝底、未铺满  
- `BOTTOM OVERFLOW` / `RIGHT OVERFLOW`、日历溢出、空态被 Tab 挡  
- 弹层盖地图、`DraggableScrollableSheet` 断言、字号反差过大  
- `SCBCompatible`、三点把手、兼容信箱  

**适配关键词**

- FoldStatus、折痕、断点、`BreakpointManager`  
- `hadss_adaptive_layout`、`hadss_avoid_area`  
- FolderStack、NavigationSplit、开合连续性  

### 4.2 显式点名（推荐）

```text
请使用 flutter-pura-x-max-ux，分析并修复内屏横屏两侧蓝底问题。
```

```text
外屏登录弹键盘字体重叠，按 flutter-pura-x-max-ux 的 UX-01 修复，并给出验收项。
```

```text
按 flutter-pura-x-max-ux 的 PX-01/02，做悬停态分屏并避让折痕（hadss + 原生双方案）。
```

```text
用 flutter-pura-x-max-ux 扫一遍本工程阔折叠 UX 风险，列出命中的 UX-ID / PX-ID。
```

---

## 5. Agent 工作流（执行顺序）

```
1. 分流：系统信箱(UX-11/PX-06) vs Flutter 布局 vs 折展(PX-01～05)
2. 命中 UX / PX 目录
3. 应用 patterns.md 的 P-*；折展细节读 references/purax/*
4. 扫一遍「工程级规范」
5. 输出中文：根因 + 改动点 + checklist 验收矩阵
```

**建议修复优先级：**

```text
滚动截断类（01/03/04/06/08/10/16/18/19/20）
  → 铺满 / 相机 / 信箱（02/05/11）
  → 安全区（07/14）
  → 折展结构（09/12/13/15 + PX）
  → 竞态与尺度（22/23/24）
```

**输出模板（Agent 应对齐）：**

```markdown
## 结论
- 命中：UX-xx / PX-xx
- 根因：…
- 修复落点：`path/to/file`

## 改动要点
1. …

## 验收
| 形态 | 用例 | 通过标准 |
```

---

## 6. 设备形态与风险

| 形态 | 特征 | 主要 UX 风险 |
| --- | --- | --- |
| 外屏（折叠） | 高度短 | 键盘叠字、空态溢出、按钮被底 Tab 挡、信息过载 |
| 内屏竖屏 | 更宽 | 无意义限宽导致留白 |
| 内屏横屏 | 极宽、更矮 | 弹层盖地图、日历溢出、头区过高、设计稿缩放放大 |
| 悬停 | 折痕分区 | 跨折痕点击、未分开展示/操作区 |
| 分屏 / 悬浮 | 窗口变小 | 与外屏同类截断 |
| 折展 / 旋转 | 尺寸突变 | 相机未重建、滚动/输入丢失、Sheet 比例竞态 |

### 断点参考（工程内请统一）

```dart
final s = MediaQuery.sizeOf(context);
final short = s.height < 700 || s.width > s.height; // 矮高或横屏（弹层/空态/地图卡）
final isShortH = s.height < 500;                    // 更严：外屏/极矮窗
final isWide = s.width >= 600;
```

- `500`：偏「极矮」表单 / 密度。  
- `700`：覆盖内屏横屏仍偏矮的常见窗。  
- **同一控件不要混用两套阈值标准。**

### 设计稿缩放（`.sc` 一类）

若全局 `designScale = min(w, h) / 375`：内屏横屏短边仍可能把尺寸放大到 1.5+。  
弹层 / 日历 / 固定 `150.sc` 并排宽度必须 **限幅** 或改 **`Expanded`**（见 UX-17 / UX-23）。

---

## 7. 问题目录详解（UX-01～24）

> 代码结构以 `patterns.md` 同名 `P-*` 为准；验收以 `checklist.md` 为准。  
> 下表为速查；**§7.2 起为每条详细说明**（症状 / 根因 / 修法 / 验收 / 延伸阅读）。

### 7.1 速查总表

| ID | 典型现象 | 根因摘要 | 修复模式 |
| --- | --- | --- | --- |
| UX-01 | 登录/表单叠字、键盘挡输入 | 不可滚 Column + 键盘压缩视口 | `P-SCROLL-FORM` |
| UX-02 | 横屏两侧留白（窗口已满） | 内容 `maxWidth` / 定宽居中 | `P-WIDE-FILL` |
| UX-03 | 列表/排序/加号弹窗截断 | sheet 内长 Column 无滚动 | `P-SHEET-SCROLL` |
| UX-04 | 主页截断、主按钮不可达 | 主体 Column 超高不可滚 | `P-HOME-SCROLL` |
| UX-05 | 扫一扫/相机未铺满 | 定高/AspectRatio 或旋转未重建 | `P-CAMERA-COVER` |
| UX-06 | 消息设置/长设置底部截断 | Column + shrinkWrap 不可延伸 | `P-SETTINGS-LIST` |
| UX-07 | Banner/顶栏挡挖孔 | 未消费 `MediaQuery.padding` | `P-SAFE-CUTOUT` |
| UX-08 | 筛选/吸顶栏顶部截断 | 定高内再叠 `padding.top` | `P-STICKY-TOP` |
| UX-09 | 悬停错乱、控件压折痕 | 未分开展示/操作区 | `P-HOVER-SPLIT` + PX-01/02 |
| UX-10 | 分屏/悬浮窗截断 | 仍按整屏高度排版 | `P-MULTIWINDOW` |
| UX-11 | 蓝底信箱、三点把手 | 系统 `SCBCompatible` 兼容窗 | `P-NO-LETTERBOX` |
| UX-12 | 外屏拥挤、主操作被挤 | 直板机信息密度照搬 | `P-OUTER-DENSE` |
| UX-13 | 宽屏仍底部 Tab | 未切 Rail/分栏 | `P-NAV-ADAPT` |
| UX-14 | WebView/H5 挡挖孔 | insets 未下发到 H5 | `P-WEBVIEW-INSETS` |
| UX-15 | 折展丢滚动/输入 | 整树切换导致 State 丢失 | `P-FOLD-CONTINUITY` |
| UX-16 | 空态插图溢出、CTA 被挡 | 定高插图 + 外层不可滚 | `P-EMPTY-SCROLL` |
| UX-17 | RIGHT OVERFLOW 固定宽 Row | 如 `150.sc * 2` 超窗宽 | `P-ROW-FLEX` |
| UX-18 | 轨迹条件卡盖住地图/tip | 贴地图上卡无 maxHeight | `P-MAP-SHEET-CAP` |
| UX-19 | 日期范围日历溢出 | 弹层行高过大且不可滚 | `P-CALENDAR-SHEET` |
| UX-20 | 语言等列表定高溢出 | 外层 `length * N.sc` | `P-LIST-NO-FIXED-HEIGHT` |
| UX-21 | 摄像头卡 BOTTOM OVERFLOW | 预览区固定高度（如 188.sc） | `P-CARD-FLEX-PREVIEW` |
| UX-22 | DraggableScrollableSheet 断言 | `min > initial` 一帧竞态 | `P-DRAG-SHEET-CLAMP` |
| UX-23 | 弹层字号相对外层反差过大 | 弹层裸用全量 designScale | `P-SCALE-CAP` |
| UX-24 | `OVERFLOWED BY 0.00x` | 浮点 minHeight 亚像素 | `P-EMPTY-SCROLL` |

**修复优先级：** 滚动截断 → 铺满/相机/信箱 → 安全区 → 折展结构 → 竞态与尺度（22/23/24）。

### 7.2 UX-02 vs UX-11（最易混淆，先读）

| 信号 | 判定 | 处理 |
| --- | --- | --- |
| 左右是**系统色渐变/模糊墙纸**、有**三点把手**、WMS 有 `SCBCompatible` 且应用窗窄 | **UX-11 / PX-06** | 改 `module.json5` / 窗口模式 / EntryAbility；详册 `ohos-platform/scbcompatible-letterbox.md` |
| 窗口已全宽，仅**内容**居中窄列 | **UX-02** | 去无意义 `maxWidth`，主内容 `Expanded`（`P-WIDE-FILL`） |

两者可叠加：先退出信箱（UX-11），再修内容限宽（UX-02）。

---

### 7.3 UX-01～06（主路径：登录 / 留白 / 弹窗 / 主页 / 相机 / 设置）

#### UX-01 登录/表单叠字、键盘挡输入

| 项 | 内容 |
| --- | --- |
| **症状** | 外屏或矮窗弹出键盘后，标题与输入框重叠；主按钮被挡不可见；无法滚到输入区 |
| **根因** | 主体用不可滚 `Column` 撑满；或关闭了 `resizeToAvoidBottomInset`；登录区高度锁死为屏高 |
| **修法** | `Scaffold(resizeToAvoidBottomInset: true)` + `SafeArea` + `SingleChildScrollView`；`viewInsets.bottom` 做底垫；矮高时缩小标题间距 |
| **模式** | `P-SCROLL-FORM` |
| **验收** | 外屏弹键盘：无字体重叠；输入框与主按钮可见可点 |
| **易错** | 仅包一层 `SafeArea` 仍不可滚；把整页高度写成 `MediaQuery.size.height` |

#### UX-02 横屏两侧留白（窗口已满）

| 项 | 内容 |
| --- | --- |
| **症状** | 内屏横屏主页/列表左右大块留白，但应用窗口本身已铺满屏幕（无系统蓝底） |
| **根因** | `Center` + `SizedBox(width: 375/400)` 或 `ConstrainedBox(maxWidth: …)` 无意义限宽 |
| **修法** | 宽屏主内容 `Expanded` 全宽；需要侧栏时用 `Row(侧栏 + Expanded(主区))`；仅长文可读类可限宽居中 |
| **模式** | `P-WIDE-FILL` |
| **验收** | 内屏横屏（已确认非 UX-11）：无明显无意义双侧留白 |
| **易错** | 把系统信箱当成 UX-02 去改 Flutter 限宽（应先做 WMS） |

#### UX-03 弹窗/半屏列表截断

| 项 | 内容 |
| --- | --- |
| **症状** | 加号菜单、设备列表、排序等 bottom sheet 底部项半截或不可见 |
| **根因** | `showModalBottomSheet` 内长 `Column` 无 `ListView`/`Flexible`；未 `isScrollControlled` |
| **修法** | `isScrollControlled: true`；外层 `maxHeight: 0.9 * H`；标题钉住 + `Flexible(child: ListView…)` |
| **模式** | `P-SHEET-SCROLL` |
| **验收** | 内容完整；可滚到底；无半截列表项 |
| **易错** | Dialog 同样适用；勿只改 `isScrollControlled` 却仍用不可滚长 Column |

#### UX-04 主页截断、无法滑动

| 项 | 内容 |
| --- | --- |
| **症状** | 主页「添加设备」等主操作被裁或挤到屏外；页面滑不动 |
| **根因** | 头图 + 多块模块用不可滚 `Column` 超出视口；底 Tab 再占高度 |
| **修法** | `CustomScrollView` / `ListView`；底垫 `padding.bottom + kBottomNav`；可选矮高隐藏次要模块 |
| **模式** | `P-HOME-SCROLL`（空态见 UX-16） |
| **验收** | 主按钮完整可见或可滚出；页可滑动 |
| **易错** | 只缩小字号不改为可滚，外屏仍会截断 |

#### UX-05 扫一扫/相机未铺满

| 项 | 内容 |
| --- | --- |
| **症状** | 预览四周黑边/未铺满；横→竖或竖→横后仍未铺满 |
| **根因** | `AspectRatio(16/9)` 居中；大块 `SafeArea` 包住 Preview；旋转后沿用缓存 previewSize |
| **修法** | `Stack` + `FittedBox(BoxFit.cover)` 铺满当前窗口；尺寸变化清空缓存并重建绑定；控件叠层避让即可，勿整页 SafeArea 包预览 |
| **模式** | `P-CAMERA-COVER` |
| **验收** | 竖/横均铺满；旋转后仍铺满无大块黑边 |
| **易错** | 只改 fit 不重建 Surface；折展后仍用旧尺寸 |

#### UX-06 消息设置/长设置底部截断

| 项 | 内容 |
| --- | --- |
| **症状** | 设置页底部开关/入口不可见；横屏更明显；「看得见却滑不动」 |
| **根因** | 长列表写在不可滚 `Column` 或错误 `shrinkWrap` 嵌套 |
| **修法** | `Scaffold` body 用 `ListView`；底垫安全区；分组用 `ListTile`/`SwitchListTile` |
| **模式** | `P-SETTINGS-LIST` |
| **验收** | 底部项可见或可滚出；横屏不截断 |
| **易错** | 外层已 `ListView` 内层再套不可滚固定高 Column |

---

### 7.4 UX-07～15（安全区 / 形态结构 / 信箱 / 连续性）

#### UX-07 Banner/顶栏挡挖孔

| 项 | 内容 |
| --- | --- |
| **症状** | 顶图/沉浸页标题或返回键进入状态栏挖孔；横屏时左右也被挡 |
| **根因** | 背景沉浸延伸后，文字/可点控件未加 `MediaQuery.padding` |
| **修法** | 背景可延伸；外层吃 `padding`，内层固定内容高（勿在定高内再叠 top）；横屏看左/右 inset |
| **模式** | `P-SAFE-CUTOUT` |
| **验收** | 标题与返回不进挖孔；横屏左右亦不挡 |
| **易错** | `SizedBox(height: 44)` 内再 `Padding(top: pad.top)` 把文字挤没 |

#### UX-08 筛选/吸顶栏顶部截断

| 项 | 内容 |
| --- | --- |
| **症状** | 横屏筛选条、吸顶 chips 顶字被裁 |
| **根因** | 定高容器内叠加 safe padding，内容区被挤扁 |
| **修法** | 外层先 `SizedBox(height: pad.top)`，内层再定高 44；chips 横向 `ListView` |
| **模式** | `P-STICKY-TOP` |
| **验收** | 顶栏文字完整；chips 可横滑 |
| **易错** | 与 UX-07 同类：padding 叠在定高内部 |

#### UX-09 悬停错乱、控件压折痕

| 项 | 内容 |
| --- | --- |
| **症状** | 半折时视频/拍摄页控件压在铰链上；上下内容错位 |
| **根因** | 未按 FoldStatus / displayFeatures 分开展示区与操作区 |
| **修法** | 上（或一侧）预览、下（或较大侧）操作；联动 **PX-02** 折痕避让；可用 FolderStack（hadss）或双 `Expanded` |
| **模式** | `P-HOVER-SPLIT`；详读 `references/purax/hover_state_interaction.md` |
| **验收** | 展示与操作分区；控件不在折痕上 |
| **易错** | 普通列表页也可降级为单栏可滚，不必强行分屏 |

#### UX-10 分屏/悬浮窗截断

| 项 | 内容 |
| --- | --- |
| **症状** | 分屏或悬浮小窗内主按钮不可达、页不可滚 |
| **根因** | 仍按整屏高度写死布局 |
| **修法** | 按**当前窗口** `size`：`h < 500` 或 `w < 400` 视为 compact，强制可滚、弹窗 `maxHeight: 0.95 * h` |
| **模式** | `P-MULTIWINDOW` |
| **验收** | 主按钮可达；页可滚 |
| **易错** | 用屏幕物理分辨率而非 `MediaQuery.sizeOf` |

#### UX-11 蓝底信箱、三点把手

| 项 | 内容 |
| --- | --- |
| **症状** | 内屏展开横屏两侧蓝/紫渐变；内容成竖条；顶栏三点把手 |
| **根因** | 系统兼容显示 `SCBCompatible`；常叠加仅 `phone`、方向被映射为 `LOCKED`、脏安装 |
| **修法** | WMS 取证 → `deviceTypes` 含 tablet、`supportWindowMode: ["fullscreen"]` → Ability `setSupportedWindowModes` → 全屏/maximize/必要时 resize → **重装**验收 |
| **模式** | `P-NO-LETTERBOX`；详册 `ohos-platform/scbcompatible-letterbox.md`；短版 PX-06 |
| **验收** | 无系统蓝底；本应用窗宽 ≈ 屏宽；无窄窗 + `SCBCompatible` 组合 |
| **易错** | 只 hot reload；只改 Flutter `maxWidth`；认为 maximize 一定退出兼容 |

#### UX-12 外屏拥挤

| 项 | 内容 |
| --- | --- |
| **症状** | 外屏主页 Banner/次要入口过多，主操作难找或被挤出 |
| **根因** | 直板机信息密度直接搬到矮屏 |
| **修法** | `isShort` 时隐藏营销区、缩小间距、主操作置顶；可选滚动隐藏 AppBar/底栏 |
| **模式** | `P-OUTER-DENSE` |
| **验收** | 主操作可见；次要信息可收起 |
| **易错** | 用机型名分支代替高度断点 |

#### UX-13 宽屏仍底部 Tab

| 项 | 内容 |
| --- | --- |
| **症状** | 内屏横屏导航仍挤在底部 Tab，内容区过矮 |
| **根因** | 未按宽度切换 `NavigationRail` / 分栏 |
| **修法** | `width >= 600`：`Row(NavigationRail + Expanded(body))`；窄屏保留 BottomBar |
| **模式** | `P-NAV-ADAPT`；亦可对照 PX-03 NavigationSplit |
| **验收** | 宽屏为 Rail/分栏，非挤在底部 Tab |
| **易错** | 仅横竖屏切换、不看宽度（分屏宽也可能不够） |

#### UX-14 WebView/H5 挡挖孔

| 项 | 内容 |
| --- | --- |
| **症状** | Flutter 内嵌 H5 顶栏/按钮进入挖孔或底手势条 |
| **根因** | 原生/Flutter 未把 insets 注入 H5；窗口变化未重推 |
| **修法** | 把 `padding` 写成 CSS 变量并 `dispatchEvent`；H5 使用 `env(safe-area-inset-*)` + 变量；avoid 变化时重推 |
| **模式** | `P-WEBVIEW-INSETS` |
| **验收** | H5 顶栏/按钮不进挖孔 |
| **易错** | 只设一次、折展后不更新 |

#### UX-15 折展丢滚动/输入

| 项 | 内容 |
| --- | --- |
| **症状** | 外屏↔内屏后列表滚回顶、输入清空、播放进度跳变 |
| **根因** | 顶层 `OrientationBuilder` 整树切换；折展时 dispose 业务 State |
| **修法** | 同一 State，子树按约束切换布局；保留路由栈、Controller、滚动偏移、播放进度；相机仅重建预览 |
| **模式** | `P-FOLD-CONTINUITY`；详读 `references/purax/fold_continuity.md`（≈ PX-04） |
| **验收** | 折展后滚动位置与输入内容保留；无额外操作步骤 |
| **易错** | 为适配折展重建整个 Bloc/Provider |

---

### 7.5 UX-16～24（进阶：空态 / 溢出 / 地图卡 / 日历 / Sheet / 尺度）

#### UX-16 空态插图溢出、CTA 被 Tab 挡

| 项 | 内容 |
| --- | --- |
| **症状** | 无设备/搜索空态插图过大，主按钮被底 Tab 挡住或整页溢出 |
| **根因** | 定高插图 + 不可滚 Column；未预留底导航高度 |
| **修法** | `SingleChildScrollView` + 矮高缩小插图；底垫 `padding.bottom + kBottomNav` |
| **模式** | `P-EMPTY-SCROLL` |
| **验收** | 插图与 CTA 完整；可滚；不被 Tab 挡 |
| **易错** | 只缩插图仍不可滚，横屏仍可能溢出 |

#### UX-17 固定宽 Row RIGHT OVERFLOW

| 项 | 内容 |
| --- | --- |
| **症状** | 黄黑条 `RIGHT OVERFLOWED BY xx pixels`；双入口图并排挤出 |
| **根因** | `Row` 内多个固定 `N.sc` 宽，设计稿缩放放大后超过窗宽 |
| **修法** | 子项改 `Expanded`，图片 `width: double.infinity` + `BoxFit.contain` |
| **模式** | `P-ROW-FLEX` |
| **验收** | 无 RIGHT OVERFLOW；窄宽窗均铺满可用宽 |
| **易错** | 只减小 `N.sc` 常数，横屏缩放一变仍溢出 |

#### UX-18 轨迹/地图条件卡盖住地图

| 项 | 内容 |
| --- | --- |
| **症状** | 历史轨迹等「上半条件卡」过高，盖住地图 tip 或底部半屏卡 |
| **根因** | 贴地图上的卡片无 `maxHeight`；中间筛选项不可滚 |
| **修法** | `maxHeight ≈ 0.55～0.78 * H`（矮高取低）；头/CTA 钉住，中间 `Flexible + Scroll` |
| **模式** | `P-MAP-SHEET-CAP` |
| **验收** | 不盖死 tip/地图；查询按钮可见 |
| **易错** | 与底 `DraggableScrollableSheet` 并存时只改一边 |

#### UX-19 日期范围日历弹层溢出

| 项 | 内容 |
| --- | --- |
| **症状** | 选日期范围时日历格/确认栏溢出或不可达 |
| **根因** | 弹层内日历行高按 `.sc` 放大且整体不可滚 |
| **修法** | `isScrollControlled` + `maxHeight: 0.9 * H`；标题/确认钉住，日历区可滚；行高配合 UX-23 封顶 |
| **模式** | `P-CALENDAR-SHEET` |
| **验收** | 可滚；无日历格溢出；确认栏可达 |
| **易错** | 只改字号不改可滚结构 |

#### UX-20 定高列表溢出（语言/选项等）

| 项 | 内容 |
| --- | --- |
| **症状** | 语言切换等页出现 BOTTOM OVERFLOW；或列表被裁 |
| **根因** | 外层 `SizedBox(height: items.length * N.sc)` 把高度写死 |
| **修法** | 外层 `Expanded` / 弹层 `Flexible` + `ListView.builder`；勿按条数乘行高定死父高 |
| **模式** | `P-LIST-NO-FIXED-HEIGHT` |
| **验收** | 无定高溢出；可滚到底 |
| **易错** | `shrinkWrap: true` 的 ListView 放在不可滚父级里 |

#### UX-21 摄像头卡 BOTTOM OVERFLOW

| 项 | 内容 |
| --- | --- |
| **症状** | 设备列表摄像头卡片黄黑条 BOTTOM OVERFLOW |
| **根因** | 头区 + 固定预览高（如 188.sc）+ 底栏，矮高/横屏总高超父约束；或 `itemExtent` 写死 |
| **修法** | 去掉不合理 `itemExtent`；头区矮高压缩；预览 `Expanded` 吃剩余高 |
| **模式** | `P-CARD-FLEX-PREVIEW` |
| **验收** | 无 BOTTOM OVERFLOW；预览区随卡高自适应 |
| **易错** | 只减小 188 常数，横屏缩放后仍可能爆 |

#### UX-22 DraggableScrollableSheet 断言偶现

| 项 | 内容 |
| --- | --- |
| **症状** | 从轨迹子页返回等操作后偶现崩溃：`minChildSize <= initialChildSize` |
| **根因** | 折展/返回后一帧内 `bottomHeight` 未就绪，写入的 min/initial/max 乱序 |
| **修法** | 更新前强制 `min ≤ initial ≤ max` 且均 clamp 到 0～1；高度为 0 时跳过本次 setState |
| **模式** | `P-DRAG-SHEET-CLAMP` |
| **验收** | 子页返回、折展后无该断言崩溃 |
| **易错** | 只 try/catch 断言而不 clamp；忽略高度为 0 的帧 |

#### UX-23 弹层字号相对外层反差过大

| 项 | 内容 |
| --- | --- |
| **症状** | 日历/sheet 内文字相对外层过小或过大；行高撑爆弹层 |
| **根因** | 全局 `designScale = min(w,h)/375` 在横屏短边仍 ≥1.5，弹层裸用全量缩放 |
| **修法** | 弹层内垂直尺寸用 `min(designScale, 1.12～1.28)` 封顶；外层页面可继续用原缩放 |
| **模式** | `P-SCALE-CAP` |
| **验收** | 弹层与外层字号无过大反差；行高不撑爆 |
| **易错** | 全局改小 scale 导致外层页面偏小 |

#### UX-24 亚像素 OVERFLOW 0.00x

| 项 | 内容 |
| --- | --- |
| **症状** | 日志/`OVERFLOWED BY 0.00x pixels`（视觉几乎看不出） |
| **根因** | `ConstrainedBox(minHeight: constraints.maxHeight)` 与滚动子树浮点误差 |
| **修法** | `minHeight: constraints.maxHeight - 1`（在 `P-EMPTY-SCROLL` 中一并处理） |
| **模式** | `P-EMPTY-SCROLL` |
| **验收** | 无 `0.00x` 溢出报告 |
| **易错** | 为消警告随意 `clipBehavior` 掩盖真实截断 |

---

## 8. PX 场景目录详解（PX-01～06）

> 折展场景提供 **方案 A（hadss）+ 方案 B（原生 Flutter）**。  
> 决策顺序：监听 FoldStatus → 悬停则 **PX-01 + PX-02** → 断点 **PX-03** → 连续性 **PX-04** → 信箱 **PX-06** → 其它偏差 **PX-05**。

### 8.1 速查总表

| ID | 场景 | 详读 |
| --- | --- | --- |
| PX-01 | 悬停态分屏、内外屏比例、FolderStack | `references/purax/hover_state_interaction.md`、`examples/hadss/folder_stack.dart` |
| PX-02 | 铰链/折痕避让 | `references/purax/crease_avoidance.md` |
| PX-03 | 断点响应式、NavigationSplit | `references/purax/breakpoint_layout.md`、`examples/hadss/navigation_split.dart` |
| PX-04 | 开合连续性（≈ UX-15） | `references/purax/fold_continuity.md` |
| PX-05 | 折展问题修复清单 | `references/purax/bug_fix_cases.md` |
| PX-06 | SCBCompatible 信箱（≈ UX-11） | `references/purax/scbcompatible_letterbox.md`（短版）；详册见 UX-11 |

### 8.2 各场景详细说明

#### PX-01 悬停态分屏

| 项 | 内容 |
| --- | --- |
| **场景** | 设备半折（悬停）：视频/通话/拍摄等需上展示、下操作或按折痕分区 |
| **目标** | 展示区与操作区分离；内外屏比例差异有策略 |
| **方案 A** | hadss `FolderStack` / FoldSplit 等（见官方与 `examples/hadss/folder_stack.dart`） |
| **方案 B** | `FoldStatus` / `displayFeatures` + `Column` 双 `Expanded` 分区 |
| **联动** | **必须同时考虑 PX-02**（控件勿压折痕） |
| **验收** | 半折时分区正确；控件不在铰链上 |
| **对应 UX** | UX-09 |

#### PX-02 铰链/折痕避让

| 项 | 内容 |
| --- | --- |
| **场景** | 交互控件、关键入口、关键行横跨折痕，难以点击或视觉断裂 |
| **目标** | 内容与可点区域避开铰链/折痕带 |
| **方案 A** | `hadss_avoid_area` / AvoidAreaApi 获取避让区 |
| **方案 B** | `MediaQuery.displayFeatures` 中 `hinge`/`cutout` 做 padding 或分栏空隙 |
| **验收** | 折痕区域无关键按钮/关键；布局有明确避让 |
| **对应 UX** | UX-09（联动） |

#### PX-03 断点响应式 / NavigationSplit

| 项 | 内容 |
| --- | --- |
| **场景** | 展开后仍单栏；Grid 列数不随宽变；列表-详情未双栏 |
| **目标** | 按 xs/sm/md/lg/xl（或宽度断点）切换列数、分栏、NavigationSplit |
| **方案 A** | `BreakpointManager`（hadss_adaptive_layout） |
| **方案 B** | `LayoutBuilder` / 自研监听（`examples/hadss/breakpoint_listener.dart`）+ `NavigationSplit` 等价（`examples/hadss/navigation_split.dart`） |
| **验收** | 断点变化时列数/分栏正确；展开后列表+详情可并排（业务需要时） |
| **对应 UX** | UX-02 / UX-13 可叠加 |

#### PX-04 开合连续性

| 项 | 内容 |
| --- | --- |
| **场景** | 折叠↔展开后滚动跳动、输入丢失、播放进度漂移、需用户重做步骤 |
| **目标** | 无额外步骤；状态连续 |
| **要点** | 与 UX-15 相同：保留 Controller/路由/进度；勿整树切换销毁 State |
| **验收** | 同 UX-15；开合后可立即继续操作 |
| **详读** | `references/purax/fold_continuity.md` |

#### PX-05 折展问题修复清单

| 项 | 内容 |
| --- | --- |
| **场景** | 已确认的折展行为偏差：状态监听缺失、外屏识别错误、断点不刷新等 |
| **用法** | 对照 `references/purax/bug_fix_cases.md` 逐项排查，输出 `problem_profile` / `fix_plan` |
| **验收** | 清单内相关项回归通过 |
| **说明** | 偏「修复阶段」路由；具体子问题可能再落到 PX-01～04 或 UX-\* |

#### PX-06 系统兼容信箱

| 项 | 内容 |
| --- | --- |
| **场景** | 同 UX-11：蓝底、竖条窗、三点把手、`SCBCompatible` |
| **用法** | 与 UX-11 同一套 WMS → 声明 → Ability → 重装流程；短版见 `scbcompatible_letterbox.md` |
| **验收** | 同 UX-11 |
| **说明** | PX 编号便于折展工作流路由；**详册以 UX-11 文档为准** |

### 8.3 双方案选用

| 条件 | 建议 |
| --- | --- |
| 工程已引入 / 可引入 hadss | **方案 A** 为主，方案 B 作对照说明 |
| 未引入 hadss | 同时给出 A（含依赖引入）与 B（可直接落地） |
| 仅修 UX 截断、不涉及悬停/断点组件 | 可只走 UX `P-*`，不必强行套 PX |

总览：`references/purax/official_adaptation_guide.md`。

---

## 9. 场景速查（症状 → 落点类型）

| 症状 | 命中 | 典型落点类型 |
| --- | --- | --- |
| 内屏横屏两侧蓝底 | UX-11 / PX-06 | `module.json5` / EntryAbility / 启动方向 |
| 主页摄像头卡溢出 | UX-21 | 列表卡片预览定高 |
| 消息 Tab 头区过高 | UX-04 类 | 消息头区 / 分类条高度 |
| 消息设置不可滑 | UX-06 | 设置页不可滚 Column |
| 语言切换溢出 | UX-20 | `length * itemH` 定高列表 |
| 历史轨迹条件卡盖地图 | UX-18 | 地图上半条件卡 |
| 日期范围日历溢出/字号 | UX-19 / UX-23 | 日历弹层 + 设计稿缩放 |
| 无设备/搜索空态 | UX-16 / UX-24 | 空态插图 + 不可滚 |
| 地图设置 RIGHT OVERFLOW | UX-17 | 固定宽 `.sc` 并排 Row |
| 轨迹返回偶现 Sheet 断言 | UX-22 | Sheet ratio 未 clamp |

具体代码结构见 `patterns.md` 中同名 `P-*`。

---

## 10. 工程级规范（接入任意 App 建议全局扫）

1. 可能超高的页面必须可滚动（List / CustomScroll / SingleChildScroll）。  
2. 禁止主体锁死为视口高度且不可延伸。  
3. 保持 `resizeToAvoidBottomInset: true`。  
4. 弹窗：`isScrollControlled` + 内部可滚 + `maxHeight ≈ 0.9 * H`。  
5. 地图上半条件卡：`maxHeight` 约 `0.55～0.78 * H`，留出地图可视带。  
6. 固定宽 `.sc` 并排 → `Expanded` + `width: double.infinity`。  
7. 弹层垂直尺寸对设计稿缩放：`min(designScale, 1.12～1.28)` 封顶。  
8. `DraggableScrollableSheet`：更新前强制 `min ≤ initial ≤ max`；高度为 0 时跳过。  
9. 空态可滚；勿用 `length * itemH` 定死外层高度。  
10. 摄像头/媒体卡：预览区 `Expanded`，勿与头区抢固定高度。  
11. 宽屏主内容铺满；避免无意义 `maxWidth`。  
12. OHOS：避免三向 `setPreferredOrientations` 映射为 `LOCKED`；`module.json5` 变更须重装。  
13. 热重载只覆盖纯 Dart；原生窗口配置必须重装验证。  
14. 断点优先（xs/sm/md/lg/xl），忌硬编码机型。

---

## 11. 如何安装与同步

### 11.1 Cursor（用户级）

```bash
cp -R /path/to/flutter-pura-x-max-ux ~/.cursor/skills/
```

新开 Agent 会话后即可通过描述问题或点名 Skill 使用。

### 11.2 项目级（随仓库共享）

```bash
mkdir -p <项目根>/.cursor/skills
cp -R flutter-pura-x-max-ux <项目根>/.cursor/skills/
```

### 11.3 多 Agent 同步示例

```bash
SRC=~/.cursor/skills/flutter-pura-x-max-ux

# DevEco Code（改完需重启 deveco）
mkdir -p ~/.config/deveco/skills
cp -R "$SRC" ~/.config/deveco/skills/

# Claude Code
mkdir -p ~/.claude/skills
cp -R "$SRC" ~/.claude/skills/

# CodeBuddy
mkdir -p ~/.codebuddy/skills
cp -R "$SRC" ~/.codebuddy/skills/
```

| Agent | 用户级目录 | 备注 |
| --- | --- | --- |
| Cursor | `~/.cursor/skills/` | description 可自动匹配 |
| DevEco Code | `~/.config/deveco/skills/` | 需重启 |
| Claude Code | `~/.claude/skills/` | 同 SKILL.md 体系 |
| CodeBuddy | `~/.codebuddy/skills/` | 亦可项目级 |

不支持自动发现时：把 `SKILL.md` + `patterns.md` 贴进对话，或在 `AGENTS.md` 中引用本目录。

---

## 12. 与其它 Skill 的边界

| 问题类型 | 应使用 |
| --- | --- |
| Flutter 阔折叠 UX + 折展 / 断点 / hadss | **本 skill（首选）** |
| 旧名 `flutter-purax-adaptation` | 兼容重定向；内容已在本 skill 的 `references/purax/` |
| 纯 ArkUI 多设备适配 | `hmos-multidevice-*` |
| 华为一键登录业务对接 | `huawei-quick-login` |
| 冻屏 / 卡死日志 | `hmos-appfreeze-analysis` |
| 相机枚举 / stride 花屏（偏原生） | `hmos-multidevice-hardware-access` |
| Flutter OH 编译失败 | `flutter-ohos-build` |

**不要用本 skill 硬套：**

- 非 Flutter（纯 ArkTS）页面布局  
- 账号协议 / 后台取号错误  
- 推送、蓝牙、配网协议本身  
- 无截断/遮挡的纯视觉微调  

---

## 13. 覆盖完备性（摘要）

| 集合 | 状态 |
| --- | --- |
| 登录/留白/弹窗/主页/相机/设置 | ✅ UX-01～06 |
| 挖孔/筛选/旋转相机 | ✅ UX-07/08/05 |
| 悬停/分屏/信箱/导航/WebView/连续性 | ✅ UX-09～15 |
| 空态/Row/地图卡/日历/定高列表/摄像头卡/Sheet/尺度 | ✅ UX-16～24 |
| 折展 PX + hadss 双方案 | ✅ PX-01～06 |

细节对照见 `coverage.md`。

---

## 14. 验收怎么做

打开 `checklist.md`，至少覆盖：

- [ ] 外屏竖屏  
- [ ] 内屏竖屏  
- [ ] 内屏横屏  
- [ ] 外屏 ↔ 内屏切换后状态保留  
- [ ] 横 ↔ 竖（含相机）  
- [ ] 悬停（若业务有视频/拍摄）  
- [ ] UX-11：WMS 本应用窗宽 ≈ 屏宽，无窄窗 + `SCBCompatible`  

证据建议：外屏键盘截图、内屏横屏铺满截图、WMS 摘录、空态可滚截图、设置页滚到底截图。

---

## 15. 维护建议

1. 新测出的阔折叠 UX：先归入现有 UX/PX；不能则新增 ID，并同步改 `patterns.md`、`checklist.md`、`coverage.md`、本说明。  
2. `SKILL.md` 保持精简；大段示例只放 `patterns.md` / `references/purax`。  
3. 断点阈值（500 / 600 / 700）工程内统一。  
4. 修改 Skill 后新开 Agent 会话验证发现；DevEco Code 需重启。  
5. 多处安装时用 §11 命令同步，避免版本漂移。  
6. 文档与示例中 **不写具体业务应用名 / 包名**；WMS 示例用「本应用 / YourApp」。

---

## 16. 快速索引

| 我想… | 打开 |
| --- | --- |
| 让 Agent 按规范修问题 | `SKILL.md` |
| 找可复制的 Flutter 改法 | `patterns.md` |
| 写测试 / 验收用例 | `checklist.md` |
| 查 UX/PX 问题目录详解（症状/根因/修法/验收） | `说明.md` §7～§8 |
| 蓝底信箱专项 | `ohos-platform/scbcompatible-letterbox.md` |
| 悬停 / 折痕 / 断点详解 | `references/purax/` |
| 示例代码 | `assets/` |
| 路由评测用例 | `test-cases/` |
| 给人看的完整说明 | **本文件 `说明.md`** |
