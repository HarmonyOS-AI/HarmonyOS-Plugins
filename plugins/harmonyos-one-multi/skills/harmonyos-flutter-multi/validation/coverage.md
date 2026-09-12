<!--
Merged from flutter-pura-x-max-ux-20260731/coverage.md.
Role: coverage cross-check and out-of-scope boundaries; feeds known-risks.md.
Link mapping: references/purax/* -> ../references/purax/*; assets/* -> ../examples/hadss/*.
-->
# 覆盖对照与缺口说明

对照来源：Flutter 阔折叠实测用例、HarmonyOS 阔折叠最佳实践、Flutter 大屏/折叠指南、原 `flutter-purax-adaptation` 折展场景。

## 覆盖结论

| 集合 | 状态 |
| --- | --- |
| Flutter 测分主路径（登录叠字、横屏留白、弹窗截断、主页不可滑、相机未铺满、设置截断） | ✅ UX-01～06 |
| 安全区与顶栏补充（挖孔、筛选顶截断、登录遮挡、旋转后相机） | ✅ UX-01/05/07/08 |
| 阔折叠延伸（悬停、分屏、letterbox、外屏降密度、导航、WebView、连续性） | ✅ UX-09～15 |
| 进阶实测（空态、Row 溢出、轨迹卡、日历、语言列表、摄像头卡、Sheet 竞态、`.sc` 封顶） | ✅ UX-16～24 |
| 折展适配（悬停/折痕/断点/连续性/修 bug/信箱） | ✅ PX-01～06（`references/purax/`） |
| 本 skill 刻意不覆盖 | 见下方边界 |

**结论：** Flutter × 阔折叠 **UX 缺陷修复 + 折展/断点/hadss 适配** 主路径已统一覆盖；业务协议与纯 ArkUI/NDK 不在范围内。

## 场景对照表

| 实测/标准场景 | Skill ID | 是否满足 |
| --- | --- | --- |
| 外屏登录键盘字体重叠 | UX-01 | ✅ |
| 一键登录切手机登录/注册方式遮挡 | UX-01（+ UX-12） | ✅ |
| 内屏横屏两侧留白未全屏（内容限宽） | UX-02 | ✅ |
| 设备列表/排序弹窗截断 | UX-03 | ✅ |
| 主页添加设备截断且不可滑 | UX-04 | ✅ |
| 扫一扫相机未铺满 / 旋转后仍未铺满 | UX-05 | ✅ |
| 消息设置底部截断 | UX-06 | ✅ |
| Banner 挡挖孔 | UX-07 | ✅ |
| 筛选顶部截断 | UX-08 | ✅ |
| 悬停态上展示下操作 / 折痕避让 | UX-09 / PX-01 / PX-02 | ✅ |
| 分屏/悬浮窗过小截断 | UX-10 | ✅ |
| 系统兼容信箱蓝底 | UX-11 / PX-06 | ✅ |
| 外屏信息过载 | UX-12 | ✅ |
| 宽屏仍 BottomBar | UX-13 | ✅ |
| Flutter 内嵌 H5 挡安全区 | UX-14 | ✅ |
| 折展后滚动/输入丢失 | UX-15 / PX-04 | ✅ |
| 个人空态 / 搜索空态溢出 | UX-16 / UX-24 | ✅ |
| 地图设置 RIGHT OVERFLOW | UX-17 | ✅ |
| 历史轨迹条件卡盖地图 | UX-18 | ✅ |
| 日期范围日历溢出/字号反差 | UX-19 / UX-23 | ✅ |
| 语言页定高溢出 | UX-20 | ✅ |
| 摄像头卡 BOTTOM OVERFLOW | UX-21 | ✅ |
| DraggableScrollableSheet 断言偶现 | UX-22 | ✅ |
| 断点 / NavigationSplit / FolderStack | PX-03 | ✅ |
| 折展问题修复清单 | PX-05 | ✅ |
| hadss A + 原生 B 双方案 | references/purax + assets | ✅ |

## 可选增强（未单列 ID）

| 场景 | 建议 |
| --- | --- |
| 系统字体放大后外屏溢出 | 归入 UX-01/04 |
| Grid 列数不随宽度变化 | 并 UX-02 / PX-03 |
| FAB 挡底部手势条 | 并 UX-07 |
| 视频全屏未随窗口更新 | 并 UX-05/09 |
| 鼠标/键鼠焦点（2in1） | 非本 skill |
| 纯 ArkUI / Account Kit | `huawei-quick-login` / `hmos-multidevice-*` |
| 冻屏卡死 | `hmos-appfreeze-analysis` |
| 相机枚举/stride 花屏 | `hmos-multidevice-hardware-access` |

## 边界（不要用本 skill 硬套）

1. 非 Flutter（纯 ArkTS 页面）→ 多设备场景 skill  
2. 账号协议/后台取号错误 → 登录业务 skill  
3. 推送、蓝牙、设备配网协议本身 → 业务/硬件  
4. 视觉稿级「更好看」微调（无截断/遮挡）→ 非缺陷  
5. 仅改 Dart 却期望 Ability/`module.json5` 生效 → 须重装（工程规范已写）

## 与 flutter-purax-adaptation

原 skill 的 references / assets / test-cases **已并入**本目录：

- `references/purax/*`
- `assets/*`
- `test-cases/*`

Agent **优先加载本 skill**；`flutter-purax-adaptation` 仅作重定向/兼容副本。
