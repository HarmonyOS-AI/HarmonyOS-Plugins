# RTL 与逻辑布局

## 不把语言方向当设备方向

RTL 是内容与布局方向，不是横竖屏、折叠姿态或 `width > height`。用 `I18nManager.isRTL` 和应用实际语言状态观察方向；不要用 `row-reverse` 全局翻转页面，也不要让折展事件改变 RTL。

## 审计顺序

1. 列出导航、标题栏、卡片、表单、抽屉、浮动按钮、分页和动画中的水平语义。
2. 普通间距和锚点优先使用逻辑 `start/end` 语义；必须表达物理边缘时才使用 `left/right`，并写明原因。
3. 检查 `position: 'absolute'`、transform translate、抽屉进入方向和轮播偏移。这些不会自动获得正确业务语义。
4. 区分方向性图标与非方向性图标：返回箭头、前进箭头可镜像；播放、刷新、品牌标志通常不镜像。
5. 文本验证 `textAlign`、换行、数字/标点混排、长文案和大字体，不用固定高度维持基线。

`I18nManager.allowRTL/forceRTL` 的变化通常在下次应用启动完全生效，因此 RTL/LTR 必须分别冷启动验证，不能只在 Fast Refresh 中切换后下结论。

## 与 resize、SafeArea 和动画组合

- 在 LTR/RTL 下分别执行窄→宽→窄，确认 breakpoint 只改变结构，不重置语言方向。
- SafeArea 的物理 inset 与内容逻辑边不是同一概念。先读取实际 inset，再由具体布局决定放到 start/end 或物理边。
- 动画位移根据“进入/退出/前进/后退”的语义解析符号，不把固定 `translateX` 负值复制到 RTL。
- 抽屉或侧栏切换位置时保持 route、selectedId 和滚动锚点，不用 `key={isRTL}` 重建应用根。

## 验证

覆盖 LTR/RTL 冷启动、默认/大字体、长文本、窄/宽/宽短窗口、已打开抽屉与动画中 resize。记录逻辑边、最终 `onLayout`、transform 值和截图；同一方向与最终窗口结果必须确定。

依据：React Native I18nManager 说明 RTL 状态、左右交换和重启生效规则。<https://reactnative.dev/docs/i18nmanager>

