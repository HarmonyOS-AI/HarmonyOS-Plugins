# 多设备 Recipe 索引

这些文件是复制后按项目架构改造的资产，不是必须采用的框架。先读取对应场景 reference，确认项目没有更合适的现有封装，再选择最小 recipe。

| Recipe | 场景 | 用途 | 接入前确认 |
| --- | --- | --- | --- |
| `BreakpointProvider.tsx` | RN-02/RN-03 | 唯一纯 RN breakpoint source | 替换示例阈值；不得与现有 Manager 并行 |
| `FoldGeometryProvider.tsx` | RN-06/RN-13 | 注入式唯一 Fold listener、枚举和单位归一 | 实现锁定版本 FoldPort |
| `AvoidAreaProvider.tsx` | RN-05/RN-13 | 注入式唯一 Avoid listener 和多消费者 fan-out | 明确原始单位、坐标空间和 Host inset |
| `ResponsiveImage.tsx` | RN-01/RN-08 | 父容器持有比例，稳定媒体几何 | 验证目标版本、contain/cover 语义 |
| `ResponsiveFlatList.tsx` | RN-02/RN-08 | 列数变化只重挂呈现层 | 业务状态、筛选和锚点外提 |
| `BoundedScrollPage.tsx` | RN-09 | 有界 viewport 和自然增长内容 | 与实际导航 scene 约束对账 |
| `WindowEvidenceProbe.tsx` | RN-03/RN-04/RN-07 | 采集同轮次 Dimensions 与 wrapper bounds | 仅诊断期使用，不能当最终验证 |
| `AdaptiveNavigationPresentation.tsx` | RN-02/RN-13 | 单栏/双栏只切 presentation | route/selectedId 保持唯一 owner |
| `SafeAreaOwnedPage.tsx` | RN-05 | 背景延伸与内容 inset 分层 | 根部已有 SafeAreaProvider |
| `KeyboardAwareForm.tsx` | RN-05 | 有界滚动表单和单一键盘策略 | behavior/offset 由项目实测提供 |

## 使用规则

1. 不整目录覆盖项目现有实现。
2. Provider 类 recipe 在应用稳定层只挂载一次。
3. `FoldPort`/`AvoidAreaPort` 必须由实际安装包或已有原生 wrapper 实现，禁止根据 recipe 虚构 API。
4. 示例阈值、比例、宽度和 offset 都是调用方参数，不是平台标准。
5. 完成后运行项目 TypeScript、bundle、HAR/Hvigor 和目标设备路径；缺运行证据写 `not_verified`。
