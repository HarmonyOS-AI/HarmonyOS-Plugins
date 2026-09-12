# RNOH 多设备布局案例库

在已知症状与下列案例高度相似时读取。案例是定位起点，不是永久平台事实；先核对 lockfile、实际安装实现和目标设备，再决定修复。

## 使用方法

每个案例按以下顺序执行：

1. 证明上游 window/约束是否正确。
2. 收集案例要求的最小运行证据。
3. 用一个改动稳定开启或关闭现象。
4. 只修首个错误链路。
5. 执行 F2P 和手机基线 P2P。

## Case 1：Image 比容器宽或被横向裁剪

**症状**：折展、分屏或宽短窗口中，图片被裁成窄条、横向超出或加载后突然改变页面几何。

**先排除**：父容器无界、同时硬编码宽高、网络图片没有加载前几何、错误 `cover/contain` 语义。

**证据**：记录容器和 Image 的 `origBounds/bounds`、React style、加载前后尺寸和锁定 RNOH 版本。如果图片完整宽度由已确定高度乘 `aspectRatio` 得出并远大于容器，才进入 RNOH 行为分流。

**候选修复**：

- 让有界父 View 持有 `aspectRatio`，Image 使用 `width: '100%'`、`height: '100%'` 填充；
- 或在目标版本确认支持后，由 Image 的受约束宽度计算高度；
- 不把 `height: null` 等历史规避写成所有版本的通用要求。

**验收**：加载前后几何稳定；窄/宽/宽短窗口无横向裁剪；同一最终 window 结果一致。

## Case 2：FlatList 列数改变但布局错乱

**症状**：`numColumns` 已更新，已有 item 仍按旧列数排列、被裁剪或滚动位置跳变。

**先排除**：item width、gutter、`extraData`、`renderItem` 闭包、`getItemLayout`、裁剪配置和数据 key 未同步。

**证据**：记录 window、列数、item geometry、visible item key/index、局部 offset、contentSize 和 render 次数。

**候选修复**：若锁定版本确实需要重挂，只给 FlatList 呈现层使用由列数派生的 key；数据、筛选、选中项、route 和业务锚点留在稳定祖先。重挂后按业务 key 恢复可见锚点，不盲目恢复绝对 pixel offset。

**验收**：窄→宽→窄后列数和 item 宽度正确；选中项、分页、筛选和 route 不丢失；手机基线无额外重挂。

## Case 3：ScrollView 空白、不能滚动或底部不可达

**症状**：内容高度超过窗口但无法滚动；`height:'100%'` 或给叶子加 `flex:1` 后仍为空白。

**根因候选**：Navigation scene、page root 或 viewport 没有有界高度；`flex:1` 误放在 content container；固定高度/absolute footer 裁剪内容。

**证据**：沿 `window → RNSurface → RN root → navigation scene → page → viewport → content` 逐层记录 `onLayout`，找到第一处 0、旧值、无限增长或固定裁剪。

**修复方向**：建立有界 viewport；区分 ScrollView `style` 与 `contentContainerStyle`；需要内容至少填满时使用与当前结构匹配的 `flexGrow`，不要固化设备屏高。

**验收**：短内容、长内容、宽短窗口、大字体、键盘显示/隐藏均可达；底部操作不被覆盖。

## Case 4：Fold 状态不更新或半折判断错误

**症状**：folded/expanded/half-folded 切换后布局不变，或只有某一方向进入错误分支。

**先检查**：是否真的需要 posture；普通单双栏应只消费 application window。确需 Fold 时，检查初始快照、事件名、枚举类型、sequence 和 listener owner。

**高风险模式**：

- 字符串状态与数字常量直接比较；
- 只订阅事件、不读取初始快照；
- 多页面直接注册模块级单 callback；
- 一个页面卸载时关闭全局监听；
- 旧异步状态覆盖新 epoch。

**修复方向**：在唯一 adapter 中把原生状态规范化为稳定的业务枚举；订阅建立后补读快照或按单调 sequence 合并；向多个消费者 fan-out；未知值映射 `unknown`。

**验收**：冷启动 folded/expanded、快速 fold→half→expanded、前后台和两个并发消费者；卸载一个消费者不影响另一个。

## Case 5：折痕位置偏移或内容跨折痕

**症状**：分界线不在折痕处，避让距离按密度倍数放大，分屏/自由窗口下偏移。

**根因候选**：原始 rect 单位或坐标空间未声明；display 坐标直接用于 application window；页面重复 PixelRatio 转换。

**证据**：从实际包/HAR 确认 API 返回字段和单位；记录原始 rect、PixelRatio、窗口原点、adapter 输出和最终 onLayout。不同 Fold/Avoid API 不得仅凭名称假定单位一致。

**修复方向**：在唯一 adapter 边界转换为 RN layout units，并把 rect 映射到 owning application window；页面只消费已规范化值。

**验收**：横竖方向、分屏、自由窗口、folded/half/expanded 和快速切换；同一 rect 只转换一次。

## Case 6：安全区重复或 Avoid 更新丢失

**症状**：顶部/底部出现双倍空白；Modal 关闭后主页不再更新；折展后 inset 仍是旧值。

**根因候选**：Host、SafeAreaProvider、avoid-area provider 和页面 padding 同时消费；模块级单 listener 被页面覆盖或移除；原始 px 直接进入 style。

**证据**：为 top/right/bottom/left 建 owner 表，记录 Host 是否裁剪 RNSurface、provider 输出、页面 padding、原始和转换单位、listener 数量。

**修复方向**：保留一个系统 inset 生产者和一个明确消费策略；若使用 avoid-area 包，由应用级唯一 provider 持有初始快照、事件、单位转换和幂等释放。

**验收**：两个并发消费者、Modal 打开/关闭、沉浸/非沉浸、旋转、折展和前后台；listener 数回到基线。

## Case 7：键盘遮挡或页面被双重上抬

**症状**：输入框被键盘盖住，或页面位移显著大于窗口高度变化；键盘关闭后仍残留 padding/transform。

**根因候选**：Host resize、TextInput 自动避让、KeyboardAvoidingView、Sheet 和 Avoid `TYPE_KEYBOARD` 同时生效。

**证据**：记录 keyboard show/hide、window height、输入框 bounds、键盘顶部、Sheet/页面 transform 和 bottom padding。先识别当前 RNOH/Host 的真实窗口策略。

**修复方向**：每个页面选择一个主键盘 owner；普通表单优先有界可滚动内容，Sheet 由 Sheet 自己处理，聊天页由消息区和 composer 的共同 owner 处理。

**验收**：顶部/中部/底部输入框、连续切换焦点、键盘显示/隐藏、旋转、折展、Modal/Sheet 和前后台；不累计位移。

## Case 8：方向请求退出后未恢复

**症状**：视频/阅读页面退出后仍保持横屏；快速进出页面时旧页面覆盖新页面方向策略；180° 变化没有业务更新。

**先区分**：页面请求策略、当前窗口方向和硬件/display rotation 是三个字段。普通布局不能依赖方向锁定替代响应式适配。

**修复方向**：由唯一方向 owner 保存进入前策略并使用 owner token/epoch 恢复；订阅用相同引用清理；只有业务真正依赖 180° 语义时才接入锁定版本提供的 rotation 事件。

**验收**：正常退出、路由 replace、快速进入退出、嵌套路由、分屏/自由窗口和 180°；旧 callback 不提交最终策略。

## 案例结论边界

- 配置级问题可以用源码和局部运行证据闭环，不强制全量 dump。
- Yoga/父约束/裁剪问题需要 bounds 或 onLayout 证据。
- Host/Fabric 问题需要跨层同 epoch 证据。
- 框架版本问题需要最小复现和锁定版本对照。
- 只有截图、扫描告警或相似历史案例时，不得声明根因或已修复。
