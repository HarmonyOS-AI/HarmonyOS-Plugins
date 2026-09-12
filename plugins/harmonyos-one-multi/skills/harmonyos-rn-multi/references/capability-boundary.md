# 输入代码层与能力边界

## 先判输入模式

在分析根因前建立源码与版本清单，并输出一种模式：

| 模式 | 可验证证据 | 不足时如何处理 |
| --- | --- | --- |
| `RN_ONLY` | `.tsx/.jsx/.js/.ts` React 组件、导航、状态、样式、RN 包配置 | 只改 RN；需要宿主/原生能力时生成交接项 |
| `HOST_ONLY` | Harmony 模块中的 `.ets`，且包含 RNApp、RNInstance、RNSurface、coordinator、窗口监听或宿主注册 | 只改宿主；需要 React 消费时生成 RN 交接项 |
| `NATIVE_ONLY` | TurboModule/Fabric Spec 对应实现、C-API/C++、原生 view/Surface、Package/Component 注册 | 只改已存在的原生链；缺 Spec/wrapper 时不虚构 |
| `HYBRID` | 上述至少两层源码及其生产/消费或注册关系均可定位 | 固定契约后联动审计；根因只在一层时允许另一层零修改 |
| `INSUFFICIENT` | 只有截图/日志/片段，缺入口、锁文件、调用方或写入点 | 不写补丁；列出所需源码、版本和运行证据 |

普通 `.ts` 不能自动归为 RN 或 ArkTS。按目录、导入、语法、package/build 配置与调用关系判断。第三方库构建产物只能证明当前安装内容，修改点仍应优先落在项目源文件或正式 patch 机制。

## 层级所有权

| 责任 | RN JS | RNOH Host | TurboModule/Fabric | 共享契约 |
| --- | --- | --- | --- | --- |
| 页面布局、派生单位与断点 | Flexbox、窗口 hook、rem/scale/token、结构呈现 | 不替 React 按设备选布局 | 不决定普通页面断点 | 无 |
| 应用窗口传播 | 消费 `Dimensions` | window → owning RNInstance/RNSurface | 不广播物理 display | 时间/instance/surface 标识仅用于诊断 |
| 导航与业务状态 | 唯一 owner | 容器生命周期，不建第二导航栈 | 接收声明状态、发用户 intent | key/事件/错误 |
| 系统快照/命令 | 消费并降级 | 统一系统 listener owner | 无 UI 用 TurboModule | capability、枚举、序列、unsubscribe |
| 原生 UI/Surface | wrapper、props、commands、events | 挂载与实例归属 | Fabric view、buffer、资源状态机 | bounds、单位、epoch |

## 各模式的修改规则

### `RN_ONLY`

- 可修改 React 组件、hooks、导航呈现、样式、RN 配置和已有原生 API 的消费代码。
- 函数组件优先用 `useWindowDimensions()`；`Dimensions.get('window')` 可即时读取，订阅必须由同一 owner 清理。
- 不假设未提供的 Host、TurboModule 或 Fabric 一定产生某事件/字段。
- 若完成依赖对端，交接项必须包含 owner、目标文件/注册点、契约、首次状态、清理和验收方法。

### `HOST_ONLY`

- 可修改 ArkTS RNOH 宿主、窗口 listener、RNInstance/RNSurface/coordinator 归属和现有 Package 注册。
- 只传播当前应用窗口到正确实例，不把物理 display 当 React layout window。
- 不虚构 React hook、DOM、route 或业务回调；不在 Host 复制 JS breakpoint。
- 多实例/子窗必须标识 owning window/instance/surface，销毁后不再回调。

### `NATIVE_ONLY`

- 先确认现有 Spec、生成物、实现、注册和 JS wrapper 的版本闭环。
- 只修改已存在契约允许的实现；契约需要变化但对端缺失时停止在本端可完成范围并输出原子交接。
- 原生 view 必须使用 RN 提交的 bounds；画面变换与输入逆变换成对更新。
- 不编辑 Codegen 生成物，不从另一版本模板拼装 API。

### `HYBRID`

1. 同时检查窗口传播链、React 布局链，以及命中场景的原生资源/事件链。
2. 写出当前与目标契约；字段、类型、单位、初始值、序列、错误或时序变化必须同步生产者和消费者。
3. 普通布局最终由 RN 当前 window 决定；原生只补充 RN 无法取得的系统语义或原生 UI。
4. 如果根因只在一层，其他层可以零代码变更，但要记录检查证据，不强造桥接。

## 源码与版本审计顺序

1. 找 workspace、JS 包管理器、Harmony 工程根、RN 入口和 Ability/宿主入口。
2. 读取 `package.json` 与实际 JS lockfile，记录 React Native、`react-native-harmony`、CLI、导航、安全区、手势、动画和原生 UI 库解析版本。
3. 读取 `oh-package*.json5`、`build-profile.json5`、Hvigor 配置、HAR 与目标 SDK/API。
4. RN 侧沿入口、导航、页面和 wrapper 定位 Dimensions、rem/rpx/scale/normalize、token/Context、父约束/scroll viewport、StyleSheet/memo、列表 geometry、RTL、transform/animation、Modal/Portal、状态 owner 与原生组件。
5. 若工程使用多设备布局包，记录真实包名、lockfile、已安装类型/HAR、breakpoint/inset provider 与注册路径；仓库 README 不能代替锁定版本证据。
6. Host 侧定位窗口 listener、coordinator、RNInstance/RNSurface 创建和销毁。
7. 通用原生 UI 侧定位 Spec、codegen config、生成物目录、实现、Package/Component 注册和 JS wrapper。
8. 搜索跨层事件/API/字段的全部生产、传输和消费点，确定首个错误链路与最小修改集合。

## 复杂跨层任务的内部记录

仅在跨层修改或交接时记录；简单单层任务不生成空表：

```yaml
input_mode: HYBRID
locked_versions:
  react_native: "<resolved>"
  rnoh: "<resolved>"
provided_layers: [rn, host, fabric]
editable_layers: [rn, host, fabric]
first_broken_link: "RN wrapper bounds -> Fabric native bounds"
cross_layer_contract:
  changed: true
  producer: "Fabric layout commit"
  consumer: "native Surface resize"
  fields: [componentId, width, height, epoch]
  units: "RN layout units at wrapper; buffer pixels at Surface boundary"
handoff_required: []
```

## 完成条件

- 输入模式与锁定版本都有文件/调用链证据。
- 修改没有越过 `editable_layers`，也没有把其他平台行为当 RNOH 证据。
- 应用窗口、Host、RN Dimensions、wrapper/native/Surface 几何在同一变化轮次可对账。
- 单端输入准确报告本端完成度与对端待办；双端契约在初始化、变化、错误和清理路径一致。
- 普通布局不依赖物理屏幕、机型、posture 或窗口 mode。
