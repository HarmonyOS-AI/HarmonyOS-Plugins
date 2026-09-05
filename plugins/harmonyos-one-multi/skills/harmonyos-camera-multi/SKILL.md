---
name: harmonyos-camera-multi
description: 提供 HarmonyOS 多设备相机适配知识，用于分析或直接诊断、修复明确的局部相机问题，包括能力探测、前后摄与折叠切镜、Session 和输出流、旋转镜像、预览比例、Surface、stride 花屏及相机控件布局。当前覆盖手机、折叠屏和平板，不覆盖 2in1/PC。工程扫描、批次 SPEC、设备验证和报告不由本 Skill 编排。
---

# HarmonyOS 相机多设备适配

用户要求分析时只给出诊断和建议；用户要求修复时，在明确范围内直接修改并定向验证。

## 遵守边界

本 Skill 负责相机能力、设备、会话、输出流、旋转、预览和相机界面内的叠加控件。普通业务页面的断点、分栏、折痕避让和通用窗口布局不属于本 Skill；悬停态任务只处理相机链路、方向恢复和 Surface 区域，不提供页面上下分区方案。

当前设备范围是手机、折叠屏和平板。明确要求 2in1/PC 相机适配时说明当前不支持，不得把这类设备的能力假设或测试矩阵套到平板上。

编译和官方文档查询优先使用 `devecocli`。设备运行、截图和证据管理不属于本 Skill。

## 官方文档核实

先依据工程源码和本 Skill 知识定位问题。只有 API 名称、签名、API Level 或系统行为不确定，现有知识未覆盖，或编译结果与知识冲突时，才使用 `devecocli docs search` 查找候选文档，并用 `devecocli docs read <documentId>` 读取命中文档全文。现象类问题优先全库检索，明确的 API 问题可限定 `--catalog harmonyos-references`。

搜索摘要只用于选择文档，不直接作为结论。官方文档核实事实，本 Skill 约束方案选择；API 可用性以当前工程 SDK 类型定义和实际编译为准，运行行为以设备证据为准。

## 知识入口

### 诊断输入与能力边界

确认目标设备和形态（含任务是否要求悬停/半折叠形态适配）、最低 API Level、涉及的相机模式、前后置路径、复现步骤、现有相机封装，以及哪些业务行为必须保持。相机设备、位置、Profile 和形态切换后的可用集合以运行时能力查询结果为准，不根据机型名称推断。只有用户明确询问某一机型的公开规格，或需要制定目标设备测试矩阵时，才读取 `references/device-capabilities.md`；该文档只提供规格与测试范围参考，不能替代 `getSupportedCameras()`、输出能力查询及 `foldStatusChange` 返回的 `supportedCameras`。本 Skill 的验证边界是编译级验证，不包含模拟器或真机运行验证，开工时向用户说明这一边界。

把用户选择的 `cameraPosition`（FRONT/BACK）视为跨形态业务意图，并与当前物理设备分开持久化，不能因 XComponent 或页面重建恢复成默认值。接入已有相机页时，必须在注册折叠监听前从现有 `isFront`/ViewModel/状态仓恢复该值；示例默认 BACK 只适用于全新冷启动。折叠开合后物理 `cameraId` 可以变化，但不得静默切到另一侧。相机层 `foldStatusChange` 已返回 `supportedCameras` 时优先使用该快照完成选择，不得只打印后再次查询；目标位置暂不可用时保留的是位置意图，不是旧硬件链：立即遮住旧预览、禁用拍摄，并在同一队列中释放可能已失效的旧链，再进入受控重试或明确降级。只有用户明确指定或工程已有的产品策略才允许跨位置 fallback，禁止默认回退 `cameras[0]`。若同一位置存在多个候选，优先仍可用的最后成功 ID；否则必须采用已明确的镜头角色/类型策略，不能依赖数组顺序。

```bash
devecocli build
```

编译失败时先区分历史失败和本次问题。结合源码和错误码定位，不凭截图猜 Session 状态。

参考资料按问题渐进加载，**默认不得全文读取**。先读取下表的主文件；需要可落地正反例时再读对应案例。症状无法归类时，先查 `references/camera-root-causes.md`，不要遍历所有资料。

| 问题信号 | 主文件 | 按需案例 |
|---|---|---|
| 能力缺失、801、权限、生命周期、前后摄不可用 | `references/camera-capabilities.md` | `references/cases/camera-fold-cases.md` 场景 7 |
| 折展黑屏、切镜、热启动、拉伸、方向冻结、视野变窄 | `references/camera-fold.md` | `references/cases/camera-fold-cases.md` |
| 预览/照片/录像方向、镜像、输出回调、录像状态机、帧率 | `references/camera-output.md` | `references/cases/camera-output-cases.md` 场景 3–5 |
| ImageReceiver 花屏、行偏移、stride 或帧格式错位 | `references/camera-frames.md` | `references/cases/camera-output-cases.md` 场景 6 |
| XComponent 比例、Surface 尺寸、快门或模式栏位置 | `references/camera-preview-ui.md` | 无 |

只有症状跨多个输出流、日志无法区分 Session/Profile/Surface 根因，或首次修复验证失败时才扩大读取；仍按相邻主题逐个补读，不得一次加载全部参考资料。折展后“不旋转”先查窗口方向策略，“视野变窄”先查建流基准；悬停态页面分区不在本 Skill 中处理。

### 根因检查维度

逐项检查：

1. SysCap、运行时能力查询、权限声明和错误码降级（`canIUse` 并集/交集规则，801 兜底；录像需 CAMERA + MICROPHONE 成对申请）；
2. CameraInput、Output、Session 的创建、提交、启动和释放顺序；
3. `cameraPosition` 意图连续性、形态前后 `cameraId` 变化、前后置缺失与折叠切镜（热启动恢复、完整重建、禁止静默跨位置 fallback）；
4. Preview、Photo、Video 的旋转与镜像；
5. Profile、Surface、窗口尺寸、屏幕比例和窗口方向策略（sm 锁竖屏、md/lg 用 `AUTO_ROTATION_RESTRICTED` 而非 `UNSPECIFIED`、半折叠锁横屏与退出恢复、方向随 `windowSizeChange` 重估且去重以设置结果为准、折展终态重建的窗口稳定门槛与基准比例变化重建）；
6. ImageReceiver 取帧时 `rowStride` 与 `width` 的比对与无效像素去除；
7. 相机叠加控件、快门和模式栏在目标形态下的位置；悬停/半折叠任务中，本 Skill 只检查悬停方向锁定与退出恢复、Surface 区域和悬停↔展开的相机链路；
8. 原手机相机流程的回归风险。

诊断结论至少说明页面/组件、目标形态、现象、证据、根因、修法和验证方法。涉及产品策略选择时再向用户确认。

### 修复约束

- 尊重现有相机封装，只补确认的缺口；
- 相机设备和 Profile 来自能力查询，不硬编码 cameraId，不手工拼不受支持的 Profile；
- 折展重建优先消费 `FoldStatusInfo.supportedCameras`，先确认目标 `cameraPosition` 存在，再释放旧链；目标缺失时进入 UNAVAILABLE teardown，不得默认选 `cameras[0]`；
- 翻转 XComponent 前预生成目标设备/Profile 计划；用 `IDLE/DEBOUNCING/AWAITING_ONLOAD/IN_PROGRESS` 区分阶段，每个形态事件都推进 generation，100–200ms 防抖且全链路单通道执行，旧 generation 不得提交设备或 Session 状态；
- “首次尚未查询”与“最新快照明确无目标”必须是不同状态；后者禁止迟到的 `onLoad` 再查询覆盖，并串行释放旧链、禁用拍摄；
- 重建会话前释放旧资源，监听注册和注销使用同一回调引用；
- 分开处理预览、拍照、录像和页面显示角度；
- 不顺手修复范围外的历史问题。

### 验证边界

验证是编译级的，动作只有一个：

```bash
devecocli build
```

默认只执行编译级验证，不主动拉起模拟器或真机。逐问题核对选设备、Profile、Surface 和方向链路是否按方案落到代码；运行态相机画面仍需真机或适用模拟器验证，缺少条件时明确标记未验证。

编译失败时先区分历史失败和本次问题，只修复能够归因到本次改动的问题，完成“编译—修复—重编译”；连续无进展或需要业务决策时停止修改，报告阻塞原因和已确认事实。

### 返回内容

简要返回根因、修改文件、变更摘要、构建结果、已验证项、未验证项和遗留风险。编译通过只证明代码可构建，不代表画面、折展、旋转或拍照结果已经通过运行验证。

## 能力边界

本 Skill 覆盖 stride 花屏、SysCap、热启动恢复、折叠切镜、折展防拉伸、PhotoOutput、AVRecorder 基础状态机、旋转和叠加控件。设备公开规格只用于确定测试范围，不能替代运行时能力查询。

RTC 远端旋转协商、多摄并发、高阶 Scene Mode、高级编码参数和 NDK 相机接口不属于通用处理范围。命中这些问题时按 [能力边界](references/camera-capabilities.md#能力边界)核对 SDK、业务链路和设备条件，不直接套用单路 ArkTS 相机方案。
