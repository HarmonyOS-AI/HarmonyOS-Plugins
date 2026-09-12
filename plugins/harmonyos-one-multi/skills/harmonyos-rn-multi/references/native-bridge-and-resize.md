# RNOH 原生桥接与 Fabric Resize

## 进入原生层的门禁

只有证据证明锁定 RN/RNOH 和已安装 Harmony 兼容库没有等价能力时，才新增桥接。普通布局只需要窗口宽高时不得创建原生模块。

| 需求 | 最小实现层 |
| --- | --- |
| React 能表达的布局、状态、交互 | RN JS |
| Host 没把窗口正确传播到 RN | RNOH Host |
| 系统快照、命令、非可视事件 | TurboModule |
| 嵌入 RN 的通用原生 UI 或 Surface | Fabric Native Component |

## 版本与 Codegen 闭环

1. 从 lockfile 确认 React Native、`react-native-harmony`、CLI、HAR、Codegen、目标 SDK/API 和相关库版本。
2. 检查 RN Core、当前 RNOH、已安装包的类型和 Harmony 实现，保存能力缺口证据。
3. 定义窄 TypeScript Spec，区分快照、命令、事件、错误、取消和可选字段；禁止万能 `invoke(any)`。
4. 使用工程锁定版本运行 Codegen，不修改生成物。
5. 按同版本模板实现 ArkTS/C-API/C++，并核对唯一 Package/Module/Component 注册与 Autolinking owner。
6. JS wrapper 提供明确的初始快照、事件/命令、typed error 与 unsubscribe。
7. listener、controller、Surface 和异步任务有 owner、epoch 与幂等释放。

`unknown/unsupported/denied/cancelled/busy/reclaimed` 等结果必须稳定可区分。API 名和生命周期以当前 SDK 类型、对应 tag 资料和实际构建为准。

## Fabric 五段几何证据

为同一组件实例、同一 resize epoch 记录：

| 段 | 证据 | 常见错误 |
| --- | --- | --- |
| 应用窗口 | width/height/sequence | Host 未传播或 owner 错 |
| RN wrapper | `onLayout` bounds、component id | 固定尺寸/过期 memo |
| native view | committed bounds | 未消费布局提交 |
| Surface/buffer | 实际绘制尺寸、像素、方向 | 只改 view 未 resize buffer |
| 输入事件 | 原始点、变换点、坐标系、epoch | 旧尺寸/旧逆变换 |

只有上游正确、下一段错误时才修改下一段。

## Resize 与状态策略

- 对相等宽高做短路或轻量合并，但不能吞掉连续拖拽的最终尺寸。
- 将最新 geometry 与 epoch 原子交给绘制和事件映射。
- 支持原位 resize 时保留组件与业务状态，只更新 view、Surface/buffer/viewport。
- 不能原位 resize 时受控重建：暂停输入/媒体 → 旧 epoch 失效 → 幂等释放 → 创建新资源 → 恢复允许状态 → 开放事件。
- 旧异步创建结果不得覆盖新实例；布局 props、内容 props 和控制 props 分别比较。
- wrapper 不用 width/breakpoint 作为整个原生组件 key；除非底层明确不能 resize 且状态恢复已有验证。

## 坐标与像素

在边界声明 RN layout units、ArkUI/view 坐标和 Surface buffer pixels。通用 UI 的缩放、旋转或裁切矩阵与触控逆变换必须成对；只改渲染会造成点击偏移。PixelRatio 只在明确的单位转换边界使用。

## 生命周期与验证

- mount/appear：有效 bounds 后创建，或明确复用 owner。
- update：仅处理变化字段，geometry 不重置业务状态。
- unmount/invalidate：先禁止新命令/回调，再注销、停止、释放、清引用。
- background/foreground：按组件能力暂停/重建，并重新核实 bounds。
- re-entry：不复用销毁 handle，不重复注册。

验证 TypeScript、bundle、Codegen、Autolinking/Package 注册、HAR/Hvigor，再覆盖手机、折展、旋转、分屏/自由窗拖拽、窄→宽→窄、前后台与重复进入。每个状态对账 bounds、画面、触控、事件次数、资源数和业务状态；缺运行证据时 `not_verified`。
