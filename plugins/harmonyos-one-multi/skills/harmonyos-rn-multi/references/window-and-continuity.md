# 动态窗口、宿主、折叠与方向连续性

## 先分清三条时间线

| 时间线 | 负责内容 | 不能替代 |
| --- | --- | --- |
| 窗口几何 | 当前应用 window、RNSurface、RN Dimensions | 物理 display、设备类型 |
| 系统语义 | window mode、fold posture、crease、方向策略/实际旋转 | 普通布局断点 |
| 业务连续性 | route、选中项、表单、列表锚点和原生 UI 状态 | 由 key 重建恢复 |

普通折展、分屏、旋转和自由窗口只要表现为应用窗口尺寸变化，优先闭环几何链；只有半折 UI、折痕避让、180° 语义或系统窗口命令确有布局需要时才扩展语义契约。

## RNOH 宿主尺寸链

同一变化轮次记录完整 `ScaledSize`（width/height/scale/fontScale）和以下链路：

```text
HarmonyOS application window
  → owning window listener/coordinator
  → owning RNInstance/RNSurface
  → RN Dimensions window
  → React wrapper onLayout
```

- 先从 lockfile 确认 `react-native-harmony` 与 CLI 版本，再读取对应 tag 的 Host 模板/API；不要从其他版本复制完整初始化代码。
- 初始 window size 和后续 size change 都必须到达正确的 coordinator/instance；只转发应用窗口，不转发物理 display。
- 多实例、子窗或多个 Surface 按 owning window/instance/surface 分发，不能广播给所有 RNInstance。
- listener 与 window/coordinator/instance 生命周期一致；销毁后 callback 不访问已释放对象。
- 日志至少包含 timestamp/sequence、window、instance、surface、width、height 和来源，且不记录用户数据。

如果 Host/RN Dimensions 都正确而 rem/token/style 错，转 `RN-03`；派生值和 wrapper 正确而 native/Surface 错，转 `RN-07`。

## 窗口模式

布局继续消费 window 宽高。只有业务必须区分全屏/分屏/自由/悬浮语义，或请求系统窗口命令时，才评估 TurboModule。

状态契约包含稳定枚举、capability、命令可用性和 sequence；mode 事件可能早于 size，因此不要在 mode 回调中附带猜测的新尺寸。命令返回 typed result：`success/unsupported/denied/failed` 等，不能用“未抛异常”代表成功。

## 折叠连续性与 posture

NavigationContainer、Store、缓存和业务 controller 保持稳定；compact/expanded 只切换 presentation。列数变化时优先保存可见 item key/index 与局部 offset，而不是盲目恢复像素 offset。业务锚点和 geometry 都正确但折展后列表仍归零时，读取 `known-rnoh-layout-issues.md` 核对版本修复。

只有确需姿态/折痕时，最小快照包含：

- `supported/capability`；
- 版本稳定的 `posture/displayMode`，未知值映射 `unknown`；
- 可选 `creaseRects`，声明物理 px 或 RN layout units、相对 display 或 application window；
- `sequence/timestamp`。

订阅建立后再取一次快照，或用单调 sequence 合并，避免 getSnapshot 与 subscribe 之间丢事件。快速开合只允许最新 epoch 提交；旧异步初始化不得覆盖新窗口状态。非折叠/低版本降级为 `supported=false`，普通页面仍按 window 工作。

半折/hover 若可用纯 RN 表达，保持一个页面并重排上下区域。只有需要系统原生 hover 容器或 RN 缺失 posture 时才分别评估 Fabric/TurboModule；相机/视频专项不在本 skill 内扩展。

## 方向

以下值使用不同字段和类型：

- request strategy：页面向系统请求的方向策略；
- current orientation：当前窗口横竖语义；
- hardware/display rotation：0/90/180/270 等实际旋转；

页面覆盖方向时保存旧策略并以 owner token 恢复，防止快速进出或嵌套路由中旧页面覆盖新页面。宽高不变的 180° 旋转不会可靠触发 Dimensions；UI 确需旋转语义时使用锁定版本真实提供的 display 事件。请求已受理不等于窗口已完成旋转。相机内容方向另行处理。

## 验证矩阵

- 冷启动的初始 window 与首次 Dimensions。
- 手机旋转、外屏↔内屏、快速反复折展、半折进入/退出。
- 分屏和自由窗口连续拖拽、最小窗口、mode 与 size 错序。
- 窄→宽→窄、前后台、重复进入、多 RNInstance/子窗口。
- route、表单、列表锚点、焦点、媒体状态不重置；window、派生 token 和最终 onLayout 在同轮次收敛；listener/回调数不累积。

静态代码和编译只能证明链路存在；缺目标形态下的同轮次 window/Dimensions/bounds 或语义事件证据时标记 `not_verified`。
