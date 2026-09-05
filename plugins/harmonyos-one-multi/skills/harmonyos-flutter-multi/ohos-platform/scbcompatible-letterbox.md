# UX-11 / 系统兼容信箱（SCBCompatible）排查手册

> 适用：Flutter × HarmonyOS 阔折叠（Pura X / Pura X Max 等）  
> 症状：内屏展开横屏两侧蓝/紫渐变留白、内容成竖条、顶栏三点把手  
> 对应：本 skill **UX-11 / PX-06**；实现入口以本文件为准。

---

## 0. 先做分流（30 秒）

| 信号 | 更可能是 | 下一步 |
| --- | --- | --- |
| 左右是**系统色渐变/模糊墙纸**，有 **三点把手** | **UX-11 系统兼容窗** | 本手册 WMS 取证 |
| 窗口已全宽，仅**内容**居中窄列 | UX-02 Flutter `maxWidth` | `P-WIDE-FILL` |
| 仅竖屏锁 + 展开黑边 | UX-11 方向子类 | 查 `setPreferredOrientations` OH 映射 |

**原则：先 WMS，后猜 Flutter 布局。**

---

## 1. 客观取证（必做）

### 1.1 WMS 窗口矩形

```bash
hdc -t <deviceId> shell "hidumper -s WindowManagerService -a '-a'"
```

关注含**本应用包名关键字**与 `SCBCompatible` 的行，方括号一般为 `[x y 宽 高]`：

```text
# 失败例（信箱）
YourApp0        [ 453  0  1678 1828 ]   # 应用窗远窄于屏
SCBCompatible…  [ 0    0  2584 1828 ]   # 系统兼容层铺满 → 蓝底来源
屏宽约 2584

# 通过例
YourApp0        [ 0  0  2584 1828 ]     # 宽≈屏宽
# 理想：无伴随窄窗的 SCBCompatible
```

同屏对照其它已全屏应用若已是全屏矩形，说明设备可铺满，问题在本应用声明/窗口模式。

### 1.2 已装包配置

```bash
hdc shell "bm dump -n <bundleName>"
```

核对：`versionCode`、`deviceTypes`、`orientation`、`supportWindowMode` 是否等于刚编的 HAP。

### 1.3 HAP 自检

读取 `entry-*-signed.hap` 内 `module.json`，确认不是「本地源码已改、包里仍是旧配置」。

---

## 2. 根因分层

```
L0  SCBCompatible 系统兼容信箱（蓝底）     ← 必须先退出
L1  应用窗口几何（宽≈屏宽）
L2  方向 / deviceTypes / follow_desktop
L3  Flutter 断点与全宽布局
```

常见根因组合：

1. **系统兼容显示**：阔折叠内屏宽屏比例下，未适配应用被放进固定比例窗，`SCBCompatible` 填两侧。  
2. **方向映射踩坑**：Flutter `portraitUp+landscapeLeft+Right` → OH bitmask `0x0B` → `Orientation.LOCKED`。  
3. **安装未更新**：`hdc install -r` 遇更高 `versionCode` 或脏配置，`bm dump` 仍仅 `phone`。  
4. **仅 maximize 不够**：已调用 `maximize(ENTER_IMMERSIVE)` / `resize` 仍可能停在信箱；需收紧窗口模式声明。

---

## 3. 修复顺序（Agent 执行清单）

复制跟踪：

```
- [ ] 1. WMS 分流：本应用窗宽 vs 屏宽；有无 SCBCompatible
- [ ] 2. bm dump / HAP module.json 对比（防假安装）
- [ ] 3. module.json5：deviceTypes 含 tablet；supportWindowMode 仅 fullscreen（若不需要分屏）
- [ ] 4. EntryAbility：setSupportedWindowModes([FULL_SCREEN])
- [ ] 5. 全屏布局 + resetAspectRatio + maximize(ENTER_IMMERSIVE)；仍窄则 resize(屏宽,屏高)
- [ ] 6. windowSizeChange / foldStatusChange 延迟重试（兼容窗常晚定型）
- [ ] 7. OHOS 避免启动 LOCKED 向 setPreferredOrientations；恢复方向勿乱写 UNSPECIFIED
- [ ] 8. 卸载重装或提高 versionCode 后验收 WMS
- [ ] 9. 窗口铺满后，再查 Flutter UX-02 限宽
```

### 3.1 module.json5（示例）

```json5
{
  "module": {
    "deviceTypes": ["phone", "tablet"],
    "abilities": [{
      "name": "EntryAbility",
      "orientation": "auto_rotation",   // 或按一多策略 follow_desktop / auto_rotation_unspecified
      "supportWindowMode": ["fullscreen"]  // 去掉 split/floating 降低信箱概率
    }]
  }
}
```

### 3.2 EntryAbility（要点）

```ts
import { bundleManager } from '@kit.AbilityKit';
import { window, display } from '@kit.ArkUI';

// onWindowStageCreate:
windowStage.setSupportedWindowModes([bundleManager.SupportWindowMode.FULL_SCREEN]);
const win = windowStage.getMainWindowSync();
win.setWindowLayoutFullScreen(true);
win.resetAspectRatio();
win.maximize(window.MaximizePresentation.ENTER_IMMERSIVE);
// 若 getWindowProperties().windowRect 仍明显小于 display.getDefaultDisplaySync()
// → win.resize(screenW, screenH)
// 并监听 windowSizeChange / foldStatusChange，延迟 120/400/900ms 重试
```

### 3.3 Flutter 方向（OHOS）

```dart
// ❌ portraitUp + landscapeLeft + landscapeRight → OH LOCKED
// ✅ OHOS：启动勿 setPreferredOrientations；或四向含 portraitDown
// ✅ 恢复：OHOS 可 no-op，交给原生窗口策略
```

### 3.4 安装

```bash
hdc uninstall <bundleName>
hdc install <path/to/entry-default-signed.hap>
# 或 versionCode 增大后：hdc install -r <hap>
```

`module.json5` 变更：**热重载无效**；全量 `flutter build hap` 慢（多插件 assembleHar），仅 entry 变更可尝试只编 entry HAP。

---

## 4. 验收矩阵

| 形态 | 用例 | 通过标准 |
| --- | --- | --- |
| 内屏横屏冷启动 | 打开 App | WMS 应用宽≈屏宽；无系统蓝底信箱 |
| 外屏→内屏展开 | 开合连续 | 同上，不长时间停在窄窗 |
| 对照 | 同屏已适配 App | 确认设备本身可全屏 |

---

## 5. 误判与反模式

| 反模式 | 说明 |
| --- | --- |
| 只改登录页 `maxWidth` | 未解决 L0 `SCBCompatible` |
| 认为 `-r` 一定更新 Ability 配置 | 用 `bm dump` 证伪 |
| 认为 maximize 一定退兼容 | 本机已证伪，须配合仅 fullscreen |
| 用机型名 `if (PuraXMax)` 改布局 | 一律窗口断点 |

---

## 6. 与 UX-02 的边界

- **UX-11**：窗口窄 + 系统底 → 本手册  
- **UX-02**：窗口已满，内容限宽居中 → `P-WIDE-FILL`  

两者可叠加：先过 UX-11，再修 UX-02。

---

## 7. 延伸阅读

本文件同时承担 UX-11 与 PX-06 的完整分层命令、修复顺序和验收矩阵，不再维护重复短版。
