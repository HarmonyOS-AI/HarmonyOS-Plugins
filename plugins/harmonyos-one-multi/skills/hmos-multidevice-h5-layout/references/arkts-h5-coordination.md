# ArkTS 与 H5 联动适配

## 何时进入联动场景

出现以下任一条件时命中 `H5-08`：

- 同时提供 ArkTS Web 容器/桥接代码与 H5 消费代码。
- ArkTS 已把窗口、旋转或折叠变化传给 H5。
- 只提供一端，但修复需要另一端生产或消费事件。
- 页面加载、监听注册或 reload 导致首次状态和后续状态不一致。

## 契约先于代码

复用项目已有桥接机制，并先记录：

| 项目 | 必须明确 |
| --- | --- |
| 生产者 | 哪个 ArkTS 生命周期或系统事件产生信号 |
| 传输 | 现有 JSBridge、注册对象、消息通道或脚本调用 |
| 消费者 | 哪个 H5 模块注册，何时注册和卸载 |
| 名称 | 事件/API 名是否两端完全一致 |
| 载荷 | 字段、类型、单位、可选性、版本或序号 |
| 时序 | 首次状态、变化状态、H5 未就绪、页面重载/恢复 |
| 结果 | H5 如何重新测量，而非直接套用原生尺寸 |

不要在不知道现有桥接 API 的情况下写具体 ArkTS 调用。先搜索项目中相邻事件的生产、注册和消费模式，再按同一方式实现。

## 推荐职责链

先独立检查 ArkTS 父布局到 Web 组件的外部尺寸链。若 Web 组件本身没有获得正确可用区域，直接修复 ArkTS 容器约束；只有外部尺寸正确但 H5 未响应，才继续检查事件链：

```text
HarmonyOS 窗口/折叠事件
  → ArkTS 归一化为语义信号
  → 现有桥接传输
  → H5 收到后合并到下一动画帧
  → H5 重新读取 documentElement.clientWidth
  → 更新根字号或布局状态
```

ArkTS 传来的 `screenWidthDp/screenHeightDp` 可以保留作日志或业务元数据，但 CSS/REM 的最终输入优先来自 H5 当前 layout viewport。原生事件可能早于 Web viewport 稳定，H5 收到事件后应调度测量，而不是立即把 dp 数值当 CSS px。

## H5 消费端模式

把原生事件和 Web 标准事件汇聚到同一个幂等调度器；沿用项目原 REM 公式：

```typescript
let frameId = 0;

function refreshResponsiveState(): void {
  frameId = 0;
  const width = document.documentElement.clientWidth || window.innerWidth;
  if (!Number.isFinite(width) || width <= 0) return;
  // 调用项目现有 REM/布局同步函数，不能在这里发明第二套公式。
}

function scheduleResponsiveRefresh(): void {
  if (frameId) cancelAnimationFrame(frameId);
  frameId = requestAnimationFrame(refreshResponsiveState);
}

window.addEventListener('resize', scheduleResponsiveRefresh, { passive: true });
// 现有桥接回调中同样调用 scheduleResponsiveRefresh。
```

如果原生载荷包含序号，只处理比上次更新的序号；如果项目没有序号，不为简单幂等刷新强制扩充协议。

## ArkTS 生产端规则

- 复用已有窗口/折叠监听和桥接，不并行创建第二条同义通道。
- 仅在有效变化时发送；高频窗口变化做必要合并，但不能丢最终状态。
- H5 未就绪时保留最新状态，或在 H5 ready 后响应一次主动拉取。
- 页面销毁时移除窗口监听、桥接对象和待执行任务。
- 不在 ArkTS 中复制 H5 的断点表或 REM 公式。
- 除非页面不可修改且业务接受状态丢失，否则不要以 reload 代替事件消费。

## 单端交接模板

### 只有 H5

```yaml
handoff_required:
  - owner: arkts
    need: "复用现有桥接发送窗口变化语义信号"
    contract: "事件名与字段以项目现有注册为准；H5 已提供幂等调度入口"
    acceptance: "外屏↔内屏和旋转时，H5 消费入口各收到最终状态"
```

### 只有 ArkTS

```yaml
handoff_required:
  - owner: h5
    need: "在现有事件消费者中调用统一响应式调度器"
    contract: "事件仅作重测量信号；用 clientWidth 计算 REM"
    acceptance: "相同最终 viewport 得到相同 computed root font-size"
```

## 联动验证矩阵

| 路径 | ArkTS 检查 | H5 检查 |
| --- | --- | --- |
| H5 首次加载 | Web 组件尺寸正确；ready 前状态不永久丢失 | 注册后获得或主动读取首次状态 |
| 外屏 → 内屏 | 发送最终变化且字段合法 | 下一帧读取新 viewport，REM/布局更新 |
| 内屏 → 外屏 | 不残留旧状态 | 相同最终宽度得到相同结果 |
| 内屏旋转 | 不重复注册监听 | 高频事件合并，最终方向正确 |
| 分屏连续调整 | 不把物理屏幕当窗口 | resize 持续生效且业务状态保留 |
| 页面重载/返回 | 桥接恢复且无重复监听 | 初始化与后续事件结果一致 |
| H5 消费异常 | 记录/容错符合现有机制 | 无监听泄漏或无限重试 |

`HYBRID` 的完成条件是双方的静态检查或构建通过、上述目标路径有证据、契约一致，并且直板机基线无退化。单端模式只能宣告本端完成和对端交接就绪。
