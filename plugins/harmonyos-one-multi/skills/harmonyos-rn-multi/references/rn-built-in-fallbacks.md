# 纯 React Native 多设备方案选型

用户不希望新增依赖、项目尚未证明需要官方社区组件，或第三方 Harmony 实现与锁定版本不兼容时读取。默认优先复用项目已有导航、token、provider 和组件体系。

## 选型矩阵

| 需求 | 纯 RN 方案 | 能力边界 |
| --- | --- | --- |
| 当前窗口 | `useWindowDimensions()` | Host 未传播时无法自行修复 |
| 页面断点 | 当前 window 的纯函数 + hook | 不提供原生系统 breakpoint 语义 |
| 组件断点 | 容器 `onLayout` + 局部 state | 注意回调抖动和嵌套容器 |
| 宽屏居中 | `width:'100%'` + `maxWidth` + `alignSelf:'center'` | 不改变信息结构 |
| 单栏/双栏 | 共享状态、按 breakpoint 切 presentation | 不重挂 NavigationContainer |
| 多列列表 | `numColumns` + item geometry | 某些版本可能需要只重挂列表层 |
| 内容显隐 | 条件渲染、overflow 菜单、折行 | 关键操作必须保持可达 |
| 图片比例 | 有界父容器 + `aspectRatio` + `contain/cover` | 需验证锁定 RNOH 测量行为 |
| 安全区 | 项目已验证的 safe-area provider | 精确 Harmony AvoidArea 可能需 adapter |
| 普通表单键盘 | window resize + ScrollView，或经验证的 KAV | 不与 Sheet/Host 策略重复 |
| 沉浸背景 | absolute 背景 + 单一内容 inset owner | 原生全屏开关仍由 Host 配置 |
| RTL | `I18nManager` + 逻辑 start/end | transform/方向性图标需单独处理 |
| 布局动画 | React state + LayoutAnimation；视觉动画用 transform/opacity | 以锁定 RNOH 支持为准 |
| 普通折展 | application window 驱动重排 | 无法表达真实半折或折痕 |

## 纯 RN breakpoint

阈值来自项目 token 或内容断裂点，不是设备类型：

```tsx
type Breakpoint = 'compact' | 'medium' | 'expanded';

function resolveBreakpoint(width: number): Breakpoint {
  if (width >= PROJECT_BREAKPOINTS.expanded) return 'expanded';
  if (width >= PROJECT_BREAKPOINTS.medium) return 'medium';
  return 'compact';
}

function useBreakpoint(): Breakpoint {
  const { width } = useWindowDimensions();
  return useMemo(() => resolveBreakpoint(width), [width]);
}
```

同一个应用只保留一个权威断点源。项目已有 provider 时不要再创建第二套 hook。

## 单栏与双栏

保持 route、selectedId、表单和数据 owner 稳定，只切换视觉呈现：

```tsx
const expanded = breakpoint === 'expanded';

return (
  <View style={[styles.root, expanded && styles.row]}>
    <ListPane selectedId={selectedId} onSelect={setSelectedId} />
    {expanded ? <DetailPane id={selectedId} /> : null}
  </View>
);
```

紧凑模式的详情可以由同一导航栈呈现；不要为宽屏另建 route registry 或第二份选中状态。

## 多列列表

列数变化时同步更新 item 宽度、间距、`extraData`、`getItemLayout` 和可见锚点。若目标版本需要列表重挂，只重挂 FlatList 呈现层：

```tsx
<FlatList
  key={`columns-${columns}`}
  data={items}
  numColumns={columns}
  extraData={columns}
  renderItem={renderItem}
/>
```

`items`、筛选、selectedId 和 route 不应存放在被重挂的列表内部。

## 何时升级到 Adapter 或原生能力

满足任一条件时再进入 RN-13/RN-07：

- 业务明确需要半折姿态或真实折痕几何；
- 需要精确区分 HarmonyOS system/cutout/navigation indicator 区域；
- Host 没有把 application window 传播到正确 RNSurface；
- 通用原生 UI 的 wrapper 正确但 native view/Surface 未 resize；
- 多页面需要统一、经过版本验证的 breakpoint/inset/fold 契约。

升级前记录锁定版本、现有 owner、缺失能力、预期维护成本和无依赖回退路径。
