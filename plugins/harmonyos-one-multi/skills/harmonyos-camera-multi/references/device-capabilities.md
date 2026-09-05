# 相机模块规格

目标机型的**前后置摄像头配置与关键能力**。选 `cameraPosition`、判断折叠切镜重灾区、决定是否有深感/可变光圈/潜望长焦时用它。

> **数据性质**：来自 `harmonyos-huawei-device-catalog/references/*`（快照 2026-07-15）的「相机规格」段。
> **运行态实测值优先于本表** —— 设备实际可用摄像头以 `getSupportedCameras()` 返回为准，形态切换后用 `foldStatusChange` 回调带的 `supportedCameras` 刷新。

> **三态语义（不可被顺手填值）**：`不支持` = 官网明确否定；`未公开` = 官网该型号页没写（信息缺口，非否定）；`需精确 SKU 核验` = 该行合并了多个未逐一核验的 SKU。多数手机「手写笔」「外接键鼠」类项是 `未公开` 而非 `不支持`。

> **禁止跨代/跨后缀继承**：Pro 不能套 Pro+，风驰版不能继承 Pro Max。表中每行独立核验。

## 适配锚点（先看这里）

- **折叠屏双前摄是 `cameraPosition=FRONT` 折叠切镜重灾区**：Mate X6 / X7 / Pura X Max 内屏 + 外屏各一颗前摄，折展时可用前摄集合会变，必须按 [切镜重建实现机制](camera-fold.md#切镜重建实现机制) 重建。
- **3D 深感影响 cameraPosition 枚举与生物识别 UI**：Mate 70 Pro 及以上、Mate 80 Pro 及以上的前置含 3D 深感摄像头。

## 直板机

| 型号 | 后置 (BACK) | 前置 (FRONT) | 关键特性 | 数据态 |
|---|---|---|---|---|
| Mate 60 | 50MP 可变光圈 OIS + 12MP 超广角 + 12MP 潜望长焦 OIS | 13MP 超广角 | 可变光圈 / 潜望长焦 | 需精确 SKU 核验 |
| Mate 70 | 50MP F1.4-F4.0 OIS + 40MP 超广角 + 12MP 潜望长焦 OIS + 1.5MP 红枫 | 13MP 超广角 | 可变光圈 / 潜望 / 红枫 | 官方值 |
| Mate 70 Pro / Pro 优享版 | 50MP 可变光圈 + 40MP 超广角 + 48MP 微距长焦 OIS + 红枫 | 13MP 超广角 + **3D 深感** | 微距长焦 / 3D 深感 | 官方值 |
| Mate 70 Pro+ / RS | 同 Pro 但全部 RYYB（50/40/48MP）+ 红枫 | 13MP 超广角 + **3D 深感** | RYYB 不得反套 Pro | 官方值 |
| Mate 70 Air | 50MP F1.8 OIS + 12MP RYYB 长焦 + 8MP 超广角微距 + 红枫 | 10.7MP 超广角（**无 3D 深感**） | 前摄独立处理 | 官方值 |
| Mate 80 | 50MP RYYB 可变光圈 + 40MP 超广角 + 12MP RYYB 潜望长焦 + 二代红枫 | 13MP AF + **3D 深感** | AF 前摄 | 官方值 |
| Mate 80 Pro | 50MP RYYB 可变光圈 + 40MP RYYB 超广角 + 48MP 微距长焦 + 二代红枫 | 13MP AF + **3D 深感** | 8x 光学品质 | 官方值 |
| Mate 80 Pro Max / RS | 50MP + 40MP + 50MP 微距长焦 + **50MP 超长焦** + 二代红枫 | 13MP AF + **3D 深感** | 双长焦入口 | 官方值 |
| Mate 80 Pro Max 风驰版 | 50MP + 40MP + 50MP 微距长焦（**官网未列超长焦/红枫**） | 13MP AF + 3D 深感 | 不得继承 Pro Max | 官方值 |
| Pura 70 | 50MP 可变光圈 + 13MP 超广角 + 12MP 潜望长焦 | 13MP 超广角 | Ultra 单独核验 | 需精确 SKU 核验 |
| Pura 80 | 50MP 可变光圈 + 13MP 超广角 + 12MP 潜望长焦 + 红枫 | 13MP AF | — | 官方值 |
| Pura 90 | 50MP F1.8 + 12.5MP 超广角 + 50MP 潜望长焦 + 红枫 | 50MP AF + 红枫 | 13/24/88mm | 官方值 |
| Pura 90 Pro | 50MP F1.4-F4.0 + 12.5MP 超广角 + 50MP 微距长焦 + 二代红枫 | 13MP 超广角 AF | 13/24/90.5mm | 官方值 |
| Pura 90 Pro Max | 50MP 超高动态 + 40MP 超广角 + **200MP 长焦微距** + 二代红枫 | 13MP 超广角 AF | 2 亿长焦 | 官方值 |
| nova 12 / 13 | 50MP 主摄（Pro/Ultra 加长焦/超广角） | 50/60MP，部分双摄 | 前摄挖孔按 SKU | 需精确 SKU 核验 |
| nova 14 | 50MP RYYB + 12MP 长焦人像 OIS + 8MP 超广角微距 | 50MP | 3 摄 | 官方值 |
| nova 14 活力版 | 50MP + 8MP 超广角微距（**无长焦**） | 50MP | 不展示长焦入口 | 官方值 |
| nova 14 Pro | 50MP 可变光圈 + 12MP 长焦人像 + 8MP 超广角微距 + 红枫 | 50MP + 8MP（**前双**） | 前置双摄 | 官方值 |
| nova 14 Ultra | 50MP 可变光圈 + 50MP 潜望长焦 + 13MP 超广角微距 + 红枫 | 50MP + 8MP（前双） | 潜望 | 官方值 |
| nova 15 | 50MP + 12MP 长焦人像 + 红枫 | 50MP | — | 官方值 |
| nova 15 Pro | 50MP F1.8 OIS + 12MP 长焦人像 + 13MP 超广角微距 + 红枫 | 50MP + 红枫 | — | 官方值 |
| nova 15 Ultra | 50MP 可变光圈 + 50MP 潜望长焦 + 50MP 超广角微距 + 红枫 | 50MP + 红枫 | 三枚 50MP | 官方值 |
| nova 16 | 50MP + 50MP 潜望长焦 + 红枫 | 50MP | — | 官方值 |
| nova 16z | 50MP + 12MP 长焦人像 + 红枫 | 50MP | **不得继承 nova16 的 50MP 潜望** | 官方值 |
| nova 16 Pro | **200MP** + 50MP 潜望长焦 + 50MP 超广角微距 + 红枫 | 50MP + 红枫 | 2 亿主摄 | 官方值 |
| nova 16 Ultra | 200MP + 50MP 潜望长焦 F2.2 + 50MP 超广角微距 + 红枫 | 50MP F2.0 + 红枫 | Pro/Ultra 长焦光圈不可混用 | 官方值 |
| 畅享 70X / 尊享版 | 50MP + 2MP 景深 | 8MP | 景深入口 | 官方值 |
| 畅享 90 / Plus / 90m Plus | 50MP（单摄） | 8MP | **不得展示超广角/长焦** | 官方值 |
| 畅享 90 Pro Max | 50MP RYYB | 8MP | RYYB 不得反套其他畅享90 | 官方值 |

## 折叠屏（双前摄 → 切镜重点）

| 型号 | 后置 (BACK) | 前置 (FRONT) | 折叠切镜要点 |
|---|---|---|---|
| Mate X5 | **未列** | **未列** | 需精确 SKU 核验 |
| Mate X6 | 50MP 可变光圈 + 40MP 超广角 + 48MP 长焦微距 + 红枫 | **内屏 8MP + 外屏 8MP** | 双前摄 / 后置自拍 |
| Mate X7 | 50MP 可变光圈（标 F1.4 / 典藏 F1.49）+ 40MP 超广角 + 50MP 长焦微距 + 二代红枫 | **内屏 8MP + 外屏 8MP** | 内外屏生命周期分别处理 |
| Mate XT | 50MP 超光变 + 12MP 超广角 + 12MP 潜望长焦 | 8MP | F/M/G 切换保活 |
| Mate XTs | 50MP 可变光圈 + 40MP 超广角 + 12MP 潜望长焦 + 红枫 | 8MP 超广角 | 双屏同显 |
| Pura X | 50MP + 40MP 超广角微距 + 8MP 长焦 + 红枫 | 10.7MP 超广角 | 双屏同显 / 后置自拍 |
| Pura X Max | 50MP 可变光圈 + 12.5MP 超广角 + **50MP 潜望长焦** + 二代红枫 | **外屏 8MP + 内屏 8MP** | 区分内外前摄 |
| Pocket 2 | 50MP OIS + 12MP 超广角 + 8MP 长焦 + 2MP 超光谱 | 10.7MP 超广角 | 圆形外屏预览 |
| nova Flip | 50MP + 8MP 超广角 | 32MP | 外屏预览 |
| nova Flip S | 50MP F1.9 + 8MP 超广角 F2.2 | 32MP F2.2 | 内外屏预览 |

## 平板（无后置长焦，多为前后双摄）

| 型号 | 后置 (BACK) | 前置 (FRONT) | 备注 |
|---|---|---|---|
| MatePad Pro 11 2024 | 13MP + 8MP 广角级 | 16MP 级 | 需精确 SKU 核验 |
| MatePad Pro 12.2 2025 | 50MP AF + 8MP 广角 | 8MP | 文档扫描 |
| MatePad Pro 13.2 2025 | 50MP AF + 8MP 广角 | 16MP 广角 | 前摄规格页未公开视频规格 |
| MatePad Pro Max | 50MP AF + 二代红枫 | 12MP | — |
| MatePad Air 12 2024 | 13MP 级 | 8MP 级 | 需精确 SKU 核验 |
| MatePad Air 12 2025 | 50MP AF | 8MP | 4K 仅柔光版 |
| MatePad 11.5 S | 13MP AF | 8MP 级 | 需精确 SKU 核验 |
| MatePad 11.5 2026 | 13MP 级 | 8MP 级 | 需精确 SKU 核验 |
| MatePad Mini | 50MP + 8MP 广角 | 32MP | 蜂窝通话 |

## 官方规格页溯源

数据来自华为官方规格页（快照 2026-07-15）。表里标 `需精确 SKU 核验` 或型号不在上表时，按系列到对应规格页核验；核验前只返回 `family-inferred`。

**直板手机**（`consumer.huawei.com/cn/phones/<slug>/specs/`）：

| 系列 | 覆盖型号 | slug |
|---|---|---|
| Mate 70 / 70 Pro / 70 Pro 优享版 / 70 Pro+ / 70 RS / 70 Air / 80 / 80 Pro / 80 Pro Max / 80 Pro Max 风驰版 / 80 RS | Mate 70–80 全系 | `mate70` / `mate70-pro` / `mate70-pro-youxiangban` / `mate70-pro-plus` / `mate70-rs-ultimate-design` / `mate70-air` / `mate80` / `mate80-pro` / `mate80-pro-max` / `mate80-pro-max-fengchiban` / `mate80-rs-ultimate-design` |
| Pura 80 / 90 / 90 Pro / 90 Pro Max | Pura 80–90 | `pura80` / `pura90` / `pura90-pro` / `pura90-pro-max` |
| nova 14 / 14 Pro / 14 Ultra / 14 活力版 / 15 / 15 Pro / 15 Ultra / 16 / 16z / 16 Pro / 16 Ultra | nova 14–16 | `nova14` / `nova14-pro` / `nova14-ultra` / `nova14-vigor` / `nova15` / `nova15-pro` / `nova15-ultra` / `nova16` / `nova16-z` / `nova16-pro` / `nova16-ultra` |
| 畅享 70X / 70X 尊享版 / 90 / 90 Plus / 90m Plus / 90 Pro Max | 畅享 70X/90 | `enjoy-70x` / `enjoy-70x-zunxiang` / `enjoy-90` / `enjoy-90-plus` / `enjoy-90m-plus` / `enjoy-90-pro-max` |
| Mate 60 / Pura 70 / nova 12 / nova 13 | 早期或精确 SKU 未核验 | `需精确 SKU 核验`，查对应规格页 |

**折叠屏**：

| 型号 | 规格 slug |
|---|---|
| Mate X6 | `mate-x6` |
| Mate X7 | `mate-x7` |
| Mate XT / XTs | `mate-xt-ultimate-design` / `mate-xts-ultimate-design` |
| Pura X / Pura X Max | `pura-x` / `pura-x-max` |
| Pocket 2 | `pocket-2-youxiangban`（标准/优享/艺术定制参考） |
| nova Flip / Flip S | `nova-flip` / `nova-flip-s` |

**平板**：

| 型号 | 规格 slug（`consumer.huawei.com/cn/tablets/<slug>/specs/`） |
|---|---|
| MatePad Pro 12.2 2025 / 13.2 2025 / Pro Max | `matepad-pro-12-2-2025` / `matepad-pro-13-2-2025` / `matepad-pro-max` |
| MatePad Air 12 2025 | `matepad-air-2025` |
| MatePad 11.5 2026 | `matepad-11-5-2026` |
| MatePad Mini | `matepad-mini` |

> Mate X5 相机、Mate 60 全系、Pura 70 全系、nova 12/13、MatePad Pro 11 2024、MatePad Air 2024、MatePad 11.5 S 在官方页未完整列出相机参数，标 `需精确 SKU 核验`，禁止从同代基础款推断。
