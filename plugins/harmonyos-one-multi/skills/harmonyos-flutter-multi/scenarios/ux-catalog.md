# UX 场景目录

症状 → 根因 → 修复模式的完整映射。P-* 模式完整代码见 [../references/pura-x-patterns.md](../references/pura-x-patterns.md)；逐 ID 验收看 [../validation/ux-px-checklist.md](../validation/ux-px-checklist.md)。

| ID | 症状关键词 | 根因 | 模式 |
| --- | --- | --- | --- |
| UX-01 | 登录叠字、键盘挡输入 | 不可滚 Column + 键盘压缩 | `P-SCROLL-FORM` |
| UX-02 | 横屏两侧留白（窗口已满） | 内容 `maxWidth` 限宽 | `P-WIDE-FILL` |
| UX-03 | 设备列表/排序/加号弹窗截断 | sheet 无 ListView | `P-SHEET-SCROLL` |
| UX-04 | 主页截断、空态按钮被 Tab 挡 | Column 超高无滚 | `P-HOME-SCROLL` / `P-EMPTY-SCROLL` |
| UX-05 | 扫一扫/相机未铺满 | 定高或旋转未重建 | `P-CAMERA-COVER` |
| UX-06 | 消息设置/长设置截断 | Column+shrinkWrap | `P-SETTINGS-LIST` |
| UX-07 | Banner/顶栏挡挖孔 | 未避让 cutout | `P-SAFE-CUTOUT` |
| UX-08 | 筛选条顶截断 | 定高+safe 叠垫 | `P-STICKY-TOP` |
| UX-09 | 悬停错乱、压折痕 | 未分开展示/操作 | `P-HOVER-SPLIT` + PX-01/02 |
| UX-10 | 分屏截断 | 仍按整屏 | `P-MULTIWINDOW` |
| UX-11 | 蓝底信箱、三点把手 | `SCBCompatible` | `P-NO-LETTERBOX` |
| UX-12 | 外屏拥挤 | 直板机密度 | `P-OUTER-DENSE` |
| UX-13 | 宽屏仍底 Tab | 未 Rail/分栏 | `P-NAV-ADAPT` |
| UX-14 | WebView 挡挖孔 | insets 未下发 | `P-WEBVIEW-INSETS` |
| UX-15 | 折展丢滚动/输入 | 未保留状态 | `P-FOLD-CONTINUITY` + PX-04 |
| UX-16 | 空态插图溢出（主页/搜索） | 定高图+不可滚 | `P-EMPTY-SCROLL` |
| UX-17 | RIGHT OVERFLOW 固定宽 Row | 如 `150.sc*2` | `P-ROW-FLEX` |
| UX-18 | 轨迹条件卡盖住地图/tip | 贴底卡超屏高 | `P-MAP-SHEET-CAP` |
| UX-19 | 日期范围日历溢出/字号反差 | `.sc` 行高+不可滚 | `P-CALENDAR-SHEET` |
| UX-20 | 语言列表等定高溢出 | `length * N.sc` | `P-LIST-NO-FIXED-HEIGHT` |
| UX-21 | 摄像头卡 BOTTOM OVERFLOW | 预览定高 188.sc | `P-CARD-FLEX-PREVIEW` |
| UX-22 | DraggableScrollableSheet 断言偶现 | min>initial 竞态 | `P-DRAG-SHEET-CLAMP` |
| UX-23 | 弹层字号相对外层过小/过大 | 裸 design vs `.sc` | `P-SCALE-CAP` |
| UX-24 | 亚像素 OVERFLOW 0.00x | 浮点高度 | `P-EMPTY-SCROLL`（minH-1） |

## 优先级

滚动截断类 → 铺满/相机/信箱 → 安全区 → 折展结构（PX）→ 竞态类（UX-22）。

## UX-02 vs UX-11 分流

- 系统色渐变背景、三点把手或 WMS 有 `SCBCompatible` 证据 → **UX-11**，走 [../ohos-platform/scbcompatible-letterbox.md](../ohos-platform/scbcompatible-letterbox.md)。
- 窗口已铺满、仅内容被业务层限窄 → **UX-02**，走布局路线的 `P-WIDE-FILL`。

## 场景速查（症状 → 落点类型）

| 路径 | 命中 | 典型落点类型 |
| --- | --- | --- |
| 内屏横屏两侧蓝底 | UX-11 / PX-06 | `module.json5` / EntryAbility / 启动方向 |
| 主页摄像头卡溢出 | UX-21 | 列表卡片预览定高 |
| 消息 Tab 头区过高 | UX-04 类 | 消息头区 / 分类条高度 |
| 消息设置不可滑 | UX-06 | 设置页 Column |
| 语言切换溢出 | UX-20 | `length * itemH` 定高列表 |
| 历史轨迹条件卡盖地图 | UX-18 | 地图上半条件卡 |
| 日期范围日历溢出/字号 | UX-19 / UX-23 | 日历弹层 + 设计稿缩放 |
| 无设备空态 / 搜索空态 | UX-16 / UX-24 | 空态插图 + 不可滚 |
| 地图设置 RIGHT OVERFLOW | UX-17 | 固定宽 `.sc` 并排 Row |
| 轨迹返回偶现 Sheet 断言 | UX-22 | `DraggableScrollableSheet` ratio 竞态 |

验收至少覆盖窄高、窄矮、展开横屏、键盘弹出和动态窗口缩放。设备形态风险表（外屏矮高/内屏横屏/悬停/分屏）见 [../references/pura-x-guide.md](../references/pura-x-guide.md) 第 2 节。
