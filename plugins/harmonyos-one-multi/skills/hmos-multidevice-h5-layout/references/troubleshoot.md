# H5 响应式问题排查

## 先收集可比较数据

在正常与异常窗口分别记录：`innerWidth/innerHeight`、`visualViewport`、目标元素 `getBoundingClientRect()`、父容器宽度、`scrollWidth/clientWidth`、命中的 media/container query 和关键 computed style。

## 横向滚动或截断

1. 找到 `scrollWidth > clientWidth` 的第一个容器，而不是先隐藏 body overflow。
2. 检查固定宽度、`min-width`、`white-space: nowrap`、绝对定位和负 margin。
3. 检查 Flex/Grid 子项是否缺少 `min-width: 0` 或 `minmax(0, 1fr)`。
4. 检查图片、video、canvas、table、代码块和 iframe 的固有宽度。

## 宽屏留白或内容过度拉伸

1. 区分正文行长、列表信息密度与页面结构，不把所有区域统一拉满。
2. 检查整页 `max-width` 是否错误限制了需要扩展的列表或分栏区域。
3. 正文保留舒适行长，重复内容增加列数，导航/详情按信息层级分栏。
4. 检查断点规则是否被后续同等或更高 specificity 选择器覆盖。

## 横屏短高度内容不可操作

1. 统计固定顶部、底部和粘性区域的总高度。
2. 检查 `height: 100vh` + `overflow: hidden`、固定 hero 或弹窗高度。
3. 为横屏短高度减少装饰和间距，让核心区域自然滚动。
4. 不要把 `orientation: landscape` 等同于“大屏”；同时验证实际宽度。

## resize、旋转或分屏后不更新

1. 搜索加载阶段缓存的 `innerWidth`、`screen.width` 和一次性 class。
2. 搜索动态 REM 根字号写入；若存在，读取 `rem-responsive.md` 检查初始化公式、监听器注册和宽高守卫。
3. 纯视觉变化改回 CSS；业务状态使用与 CSS 一致的 media query。
4. 组件受局部容器约束时使用 container query 或 ResizeObserver，不监听整个 window。
5. 检查 SPA 重挂后的重复监听、旧闭包和未取消的动画帧。

## 根因确认标准

只有当单一约束或规则能稳定开启/关闭现象，并能解释为何只在特定宽高出现，才列为根因。扫描器告警、设备名称和问题发生时间只能作为线索。

## 修复证据

提交前保留：根因、修改文件、断点依据、窄屏对照、临界值结果、目标窗口结果、动态 resize 结果、构建/测试结果和残余风险。
