# LTPO 自适应刷新率指南

整合自 `flutter_samples/ohos/docs/04_development/如何使用LTPO功能.md`。

## 简介

LTPO 功能指屏幕动态帧率：屏幕刷新率设为"智能"时，应用可根据当前场景自动切换合适帧率。

Flutter 框架帧率现状：刷新率设为"智能"时与"高"一致——触摸屏幕 120 帧；手指离开后保持 3s 120 帧；
3s 无操作降至 60 帧。

> LTPO 特性依赖 OpenHarmony API 20，请在 API 20 及以上的 ROM 中验证。

## 适配场景

| 序号 | 场景           |
| ---- | -------------- |
| 1    | 自定义平移动画 |
| 2    | 转场平移动画   |
| 3    | 滚动列表抛滑   |
| 4    | 轮播图         |

## 适配依赖

| 顺序 | 依赖项          | 说明                                   |
| ---- | --------------- | -------------------------------------- |
| 1    | DevEco Studio   | IDE 工具，至少 6.0.0 Release（含 API 20）|
| 2    | flutter_flutter | 集成 LTPO 功能的 flutter sdk           |
| 3    | framesconfig.json | LTPO 配置文件                        |
| 4    | 系统版本        | 软件版本 ≥ 6.0.0.110（SP96C00E110R4P8）|

## LTPO 配置文件

### 配置项

| 子项    | 描述                                       | 类型     |
| ------- | ------------------------------------------ | -------- |
| SWITCH  | 动态帧率开关（0-关闭；1-开启）             | 整型     |
| TRANSLATE | 平移动画帧率映射表（不建议修改）         | 数组     |
| SCALE   | 缩放帧率映射表（当前未实现）               | 数组     |
| ROTATION | 旋转帧率映射表（当前未实现）              | 数组     |

### 帧率映射表（TRANSLATE）

| 序号 | 最低滑动速度 | 最高滑动速度 | 帧率 |
| ---- | ------------ | ------------ | ---- |
| 1    | 800          | 无限大       | 90   |
| 2    | 77           | 800          | 120  |
| 3    | 46           | 77           | 90   |
| 4    | 10           | 46           | 72   |
| 5    | 0            | 10           | 60   |

> 实际屏幕帧率由系统决策。

### 文件位置

`ohos/entry/src/main/resources/rawfile/framesconfig.json`（与 `flutter_assets` 同级目录）。

示例：

```json
{
  "SWITCH": 1,
  "TRANSLATE": [
    { "minVelocity": 77, "maxVelocity": 999999, "fps": 120 },
    { "minVelocity": 0, "maxVelocity": 10, "fps": 60 }
  ]
}
```

> 1. 默认使能。已存在的工程需切到 flutter 3.27+ 并手动拷贝 `framesconfig.json` 到
>    `ohos/entry/src/main/resources/rawfile`。
> 2. 默认映射挡位不推荐改动。

## 适配流程

1. 更新 DevEco Studio 至 6.0.0 Release（含 API 20）。
2. 使用适配了 LTPO 功能的 flutter_flutter 代码仓（3.27.5-ohos-1.0.2 及以上分支）。
3. `flutter doctor -v` 确认 flutter 路径与分支。
4. 确认 `framesconfig.json` 存在；已存在工程需手动拷贝。
5. 确认 `SWITCH` 为 1。

## 验证流程

1. 检查系统版本是否匹配要求（不匹配联系接口人推送系统版本）。
2. 联系接口人进行系统帧率策略云推（当前系统有帧率策略管控）。
3. 开启"智能"刷新：设置 > 显示和亮度 > 屏幕刷新率。
4. 开启"显示刷新频率"：设置 > 系统 > 开发者选项。左上角两数字：左侧为帧率挡位（期望帧率），右侧为实时帧率。
5. 打开应用中带 Flutter 滚动组件的页面。
6. 页面抛滑。
7. 观察帧率从 120fps → 90fps → 停止后 60fps。

## 常见问题

### 动画页面切后台，动画未暂停，屏幕刷新率未下降

**合理选择 TabController**：

- 无状态控件（StatelessWidget）搭配 `DefaultTabController`
- 有状态控件（StatefulWidget）搭配自定义 `TabController`（实现 `SingleTickerProviderStateMixin`）

```dart
class _TabsPageState extends State<TabsPage> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(vsync: this, length: 3);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }
}
```

**TabView 页签切换停止动画**：

在 `deactivate` 生命周期对 `AnimationController` 进行 `stop`。基于 `this.vsync` 的动画
重新进入页面后会自动播放，无须手动启动。

```dart
class _AnimationPageState extends State<AnimationPage>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void deactivate() {
    super.deactivate();
    _controller.stop();
  }

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(duration: Duration(seconds: 4), vsync: this)
      ..addListener(() => setState(() {}))
      ..repeat(reverse: true);
  }
}
```

## 参考资料

- 可变帧率简介：`https://gitcode.com/openharmony/docs/blob/master/zh-cn/application-dev/graphics/displaysync-overview.md`
- 基于 LTPO 的低功耗设计：`https://developer.huawei.com/consumer/cn/doc/best-practices/bpta-ltpo-description`
- NativeVSync 开发指导 (C/C++)：`https://gitcode.com/openharmony/docs/blob/master/zh-cn/application-dev/graphics/native-vsync-guidelines.md`
- NativeVsync 相关函数：`https://gitcode.com/openharmony/docs/blob/master/zh-cn/application-dev/reference/apis-arkgraphics2d/capi-native-vsync-h.md`
