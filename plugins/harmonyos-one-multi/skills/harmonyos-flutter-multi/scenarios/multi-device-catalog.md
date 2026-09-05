# 一多场景目录

16 场景速查（详册见 [../references/scenes.md](../references/scenes.md)）：

| 场景 | 核心能力 | 关键断点逻辑 |
| --- | --- | --- |
| 分栏 | 内置 SplitView / go_router + ShellRoute | >= 600vp 分栏，< 600 单栏 |
| 区域避让 | SafeArea + MediaQuery.padding | 按设备类型避让不同区域 |
| 弹出框 | showDialog + MediaQuery | sm/md/lg/xl 弹窗尺寸递增 |
| 模态弹窗 | 自定义模态 + 拖拽档位 | 悬停态高度 40% 避让折痕 |
| 弹幕 | BreakpointManager | 轨道数/字号/速度按断点递增 |
| 瀑布流 | MasonryGridView + 断点列数 | xs:1, sm:2, md:3, lg/xl:4 |
| 网格布局 | GridRow + GridCol | sm:2, md:4, lg:6, xl:8 列 |
| 图文混排 | Row/Column + Expanded(flex) | < md 上下堆叠，>= md 左右分栏 |
| 自由多窗 | 窗口监听 + setWindowDecorVisible | lg/xl 左侧竖标签，sm/md 底栏 |
| 背景氛围 | LayoutBuilder + BoxFit | 父容器宽度自适应 |
| 功能交互挂件 | SafeArea + SystemChrome + MethodChannel | 组件尺寸按断点递增 |
| 导航&指南针 | OhosView + MethodChannel + 传感器 | 网格/罗盘直径按断点递增 |
| 人脸识别 | MethodChannel + VisionKit | 固定布局，小屏间距调整 |
| 扫一扫 | mobile_scanner + image_picker | 按钮尺寸按断点递增 |
| 视频通话 | OhosView(XComponent) + PiP | 小窗位置按断点自适应 |

本目录内路由：

- 分栏/导航：`navigation-split.md`
- 重复布局/网格/瀑布流：`responsive-layout.md`
- 模态、键盘与区域避让：`safe-area.md`、`overflow-and-keyboard.md`
- 自由窗：`multi-window.md`
- 地图、相机、视频、传感器：`ohos-platform/platform-view-and-channels.md`

网格卡片文字被裁剪属固定 `childAspectRatio` 问题，按单元格宽度动态计算，见 [../references/scenes.md](../references/scenes.md) 网格布局场景与 [../references/dpi-guide.md](../references/dpi-guide.md) 十大适配策略。

业务 SDK 不由本 skill 规定；这里只处理容器、窗口和平台桥接。
