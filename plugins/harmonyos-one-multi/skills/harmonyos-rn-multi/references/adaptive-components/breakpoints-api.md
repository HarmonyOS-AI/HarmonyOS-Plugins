# Breakpoint API 审计与接入

仅在工程已安装或明确评估 `@hadss/react_native_breakpoints` / `@hadss/react_native_adaptive_layout` 时读取。以下名称来自已审计发布物线索，最终以 lockfile、实际 public exports、类型和 Harmony 实现为准。

## 接入前证据

记录：

- RN、RNOH、CLI、Harmony SDK/API；
- npm 包解析版本、HAR 和 peer dependencies；
- 项目现有 breakpoint provider；
- JS fallback 与 Harmony 原生路径各自的输入和阈值；
- listener owner、初始值和清理方式。

## 候选能力

已知发布物可能包含：

- `BreakpointManager`；
- `useBreakpointValue<T>()`；
- `useHeightBreakpointValue<T>()`；
- `setBreakpoints()` / `setHeightBreakpoints()`；
- adaptive-layout 聚合包的 re-export。

不要根据此列表虚构导入；先检查 `node_modules`/包内容中的入口和 `.d.ts`。

## 采用规则

1. 项目已有 provider 时默认使用 `ADAPTER`，不让页面同时消费 Manager 和项目 token。
2. 只保留一个权威 breakpoint source；adaptive-layout 内置、独立 breakpoints Manager、项目 hook 三者不能并行裁决布局。
3. 当前断点缺值时，确认实际实现的回退顺序；业务 adapter 应提供明确最终 fallback。
4. 自定义阈值只配置一次，不在组件 render 中更新全局表。
5. 用非默认阈值验证 Harmony 原生路径和 JS fallback。若原生路径只返回系统 index 而忽略自定义阈值，改用当前 application window 的纯 JS 计算。
6. 高度断点必须明确表示真实高度还是宽高比；两条平台路径语义不一致时拒绝直接暴露给业务。
7. 页面只能取消自己的订阅，不调用会销毁全局 Dimensions listener 的 Manager 生命周期 API。

## Adapter 契约建议

```ts
type AppBreakpoint = 'compact' | 'medium' | 'expanded';

type BreakpointSnapshot = Readonly<{
  value: AppBreakpoint;
  width: number;
  height: number;
  source: 'project' | 'hadss' | 'window-fallback';
}>;
```

业务页面只消费稳定的 `AppBreakpoint`，不感知 `xs/sm/md/lg/xl`、原生 breakpoint index 或包版本。

## 验证

- 默认和非默认阈值的前 1/临界值/后 1；
- 冷启动窄/宽、窄→宽→窄、自由窗连续拖拽；
- 两个消费者同时订阅，卸载一个后另一个继续更新；
- 相同最终 window 从不同路径到达时结果相同；
- breakpoint 改变不会重挂 NavigationContainer、Store 或业务 controller。
