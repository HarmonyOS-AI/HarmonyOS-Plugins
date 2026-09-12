# SideBar 与 NavigationSplit 采用指南

只在工程已经使用或明确评估官方社区分栏组件时读取。普通双栏优先使用现有 React Navigation 和纯 RN presentation。

## 所有权

- React Navigation 保持 route registry、active route 和返回栈唯一 owner。
- 页面或 Store 保持 `selectedId` 唯一 owner。
- SideBar/NavigationSplit 只拥有 presentation、受控显隐和可选拖动宽度。
- 不让 `NavigationSplitContainer.Screen` 建第二份页面栈或选中状态。

## 候选模式

- SideBar：`Embed`、`Overlay`、`Auto`；
- NavigationSplit：`Stack`、`Split`、`Auto`；
- 主列表/详情同时呈现；
- 分隔线拖动和受控侧栏宽度。

具体枚举、prop 和默认阈值必须从实际包类型读取。不要把历史示例中的 600vp、固定 sidebar width 或深路径 import 当作当前版本契约。

## 模式切换

模式由组件实际 container width 和内容最小约束决定，例如：

```text
availableWidth
vs
minNavigationWidth + divider + minContentWidth
```

受控 prop 的 effect/memo 依赖必须包含容器尺寸、mode、显隐、宽度范围和项目 token。用户主动关闭侧栏后的选择是否跨 resize 保留，需要由产品语义明确。

## 验证

- Stack↔Split、Overlay↔Embed、窄→宽→窄；
- 拖动最小/最大宽度和中途 resize；
- route、selectedId、返回栈和列表位置连续；
- LTR/RTL、键盘焦点和屏幕阅读器；
- 两个并发实例不会共享错误的模块级状态；
- 不通过重挂 NavigationContainer 恢复布局。
