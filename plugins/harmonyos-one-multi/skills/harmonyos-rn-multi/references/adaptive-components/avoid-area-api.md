# AvoidArea API 审计与 Provider 接入

仅在项目明确需要 HarmonyOS system/cutout/navigation-indicator 等精确区域，且实际安装了兼容的 avoid-area 包时读取。普通安全区优先使用项目已验证的单一 provider。

## 接入前确认

从实际包/HAR/类型确认：

- public export 和 TurboModule 名称；
- area type 枚举；
- Rect 字段和原始单位；
- 同步初始快照是否可能为空；
- add/remove 是否支持多个 listener；
- 非 HarmonyOS 或低版本返回行为。

历史发布物可能提供 `getWindowAvoidArea`、`addAvoidAreaListener` 和 `removeAvoidAreaListener`，但签名不得从旧文档外推。

## 唯一 Provider

应用级 Provider 负责：

1. 建立平台和 capability guard；
2. 注册唯一原生 listener；
3. 获取或补读初始快照；
4. 将 rect 映射到 owning application window；
5. 在 adapter 边界把物理 px 转为 RN layout units；
6. 按 area type 合并并发布 React state；
7. 向多个消费者 fan-out；
8. 幂等注销和释放。

页面不得直接持有原生 listener，也不得再次做 PixelRatio 转换。

## 合并原则

- system、cutout、navigation indicator 不机械相加；
- 先判断 RNSurface 是否已被 Host 限制在安全区；
- 沉浸式背景可以延伸，关键内容由唯一 owner 避让；
- 页面、Modal、Sheet 和导航不能重复消费同一方向 inset；
- `TYPE_KEYBOARD` 不替代页面已选定的键盘策略。

## 稳定业务契约

```ts
type Insets = Readonly<{ top: number; right: number; bottom: number; left: number }>;

type AvoidSnapshot = Readonly<{
  insets: Insets;
  source: 'harmony-avoid' | 'safe-area' | 'fallback';
  sequence: number;
  unit: 'rn-layout-unit';
}>;
```

## 验证

初始启动、沉浸/非沉浸、四方向 cutout、状态栏/导航条显隐、旋转、折展、分屏、Modal、两个并发消费者和重复挂载。一个消费者卸载不得使其他消费者停止更新。
