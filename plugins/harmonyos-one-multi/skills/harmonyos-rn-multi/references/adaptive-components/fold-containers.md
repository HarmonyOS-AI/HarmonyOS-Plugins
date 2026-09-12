# Fold 状态、折痕与容器接入

只有业务真正需要 half-folded/hover 或真实折痕时读取。普通 folded↔expanded 双栏变化继续由 application window 驱动。

## 版本审计

从 lockfile、实际 JS wrapper、HAR/ArkTS 实现和类型确认：

- `isFoldable`、当前状态快照和 listener；
- 外部状态是字符串、数字还是对象；
- Fold 容器内部枚举；
- crease rect 字段、坐标空间和单位；
- 是否为模块级单 callback；
- FoldSplit/FolderStack 的实际 public 名称和 props。

未知或新增状态统一映射为业务 `unknown`，不要在页面散落数字常量。

## Provider 契约

```ts
type FoldPosture = 'unknown' | 'folded' | 'expanded' | 'half-folded';

type FoldSnapshot = Readonly<{
  supported: boolean;
  posture: FoldPosture;
  creaseRects: readonly { x: number; y: number; width: number; height: number }[];
  sequence: number;
  unit: 'rn-layout-unit';
}>;
```

唯一 Provider 负责原始枚举归一、坐标映射、单位转换、初始快照、事件合并和多消费者分发。页面不调用全局 remove，也不因卸载改变其他页面方向策略。

## FoldSplit/FolderStack 采用规则

- 默认 `ADAPTER` 或 `PATTERN_ONLY`；
- 内部 absolute layout 需验证动态文本、滚动、短高度、RTL 和折痕方向；
- 容器是否占满应与 owning application window/RNSurface 对账，不使用物理 screen；
- 快速事件使用 sequence/epoch 保证 latest-wins；固定 50ms/300ms 只能作为特定实现的观测值，不是通用规则；
- presentation 改变不重置 route、列表锚点、表单或媒体业务状态。

## 验证

冷启动 folded/expanded、half-folded 进入退出、快速 fold→half→expanded、横竖方向、分屏/自由窗口、前后台、重复挂载和两个消费者。记录原始状态/rect、adapter 输出、window、breakpoint 和最终 onLayout；缺目标设备证据时写 `not_verified`。
