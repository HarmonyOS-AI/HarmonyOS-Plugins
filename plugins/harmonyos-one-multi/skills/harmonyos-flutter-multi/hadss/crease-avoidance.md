# HADSS 折痕避让

能由 `FolderStack` 自动分区时不重复手算铰链。自定义布局通过 `AvoidAreaApi.getWindowAvoidArea()` 获取区域，并用 listener 在折叠、方向、沉浸式和窗口变化后刷新。

若需坐标转换，只在容器边界统一完成。验证关键控件不相交、分界锚定真实边界，并检查外屏/展开/半开之间没有残留 padding。
