# 工程级规范

来自 Pura X 阔折叠实测沉淀，两条实现路线共用；违反任何一条都可能重新引入 UX-01～24 类缺陷。

1. 可能超高的内容必须可滚：`ListView` / `CustomScrollView` / `SingleChildScrollView`。
2. 禁止主体锁死视口高度且不可延伸。
3. 表单页保持 `resizeToAvoidBottomInset: true`。
4. 弹窗：`isScrollControlled` + 内部可滚 + `maxHeight ≈ 0.9 * H`。
5. 地图上半屏条件卡：`maxHeight` 留给地图（约 `0.55～0.78 * H`）。
6. 固定宽 `.sc` 并排改为 `Expanded` + `width: double.infinity`。
7. 设计稿缩放（`min(w,h)/375` 类 `.sc`）用于弹层垂直尺寸时封顶：`min(designScale, 1.12～1.28)`；横屏短边可能把缩放推到 1.5+，必须限幅或改 `Expanded`。
8. `DraggableScrollableSheet`：更新 ratio 前强制 `min <= initial <= max`；`bottomHeight == 0` 时跳过。
9. 空态页面可滚；勿用 `length * itemH` 定死外层高度。
10. 摄像头/卡片：预览区 `Expanded`，勿与头区抢固定高度。
11. 宽屏主内容铺满；避免无意义 `maxWidth`（文章类单列可 `ConstrainedBox(maxWidth: 720)` 居中）。
12. OHOS：勿三向 `setPreferredOrientations` → `LOCKED`；`module.json5` 变更须重装或提升 `versionCode`。
13. 热重载边界：只改 Dart 布局多数可用 `r`/`R`；原生 Ability / `module.json5` / 窗口模式必须重装验证。
14. 断点优先（xs/sm/md/lg/xl），忌硬编码机型名；同工程统一矮高判据（如 500 与 700 两档），勿对同一控件混用两套标准。

各模式完整代码见 [../references/pura-x-patterns.md](../references/pura-x-patterns.md)。
