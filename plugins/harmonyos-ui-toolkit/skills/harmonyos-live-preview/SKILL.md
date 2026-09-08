---
name: harmonyos-live-preview
description: Preview, screenshot, and interact with HarmonyOS ArkUI pages in a browser using the local HarmonyOS toolchain, without launching DevEco Studio. Supports hot rebuilds on .ets edits, multiple device sizes, custom resolutions and densities, runtime resizing, component-tree inspection, and tap/swipe/type controls. Use to verify ArkUI changes visually, preview or capture a page, check responsive layouts, or diagnose blank and incorrect rendering. 适用于鸿蒙页面预览、界面截图、多设备与自定义尺寸验证、组件树断言，以及白屏或样式错乱排查。
---

# HarmonyOS ArkUI 实时预览

在浏览器里渲染 HarmonyOS ArkUI 应用，与它交互（点击、滑动、输入、系统返回），每次编辑 `.ets` 自动
重建刷新——全程只依赖 HarmonyOS 的 `command-line-tools`（hvigorw + SDK 自带的独立 `Previewer`
引擎），不需要 DevEco Studio。对 agent 来说它同时是**验证工具**：截下来的帧可以直接用图像阅读
能力查看，组件树可以做机器断言（渲染文本、布局矩形、映射回源码行）。架构、引擎参数、命令管道协议
等机制考证见 [references/how-it-works.md](references/how-it-works.md)，只在排查深层问题时才需要读。

## 前置条件

- **HarmonyOS 工具链**——独立 `command-line-tools` 或完整 DevEco Studio 均可，只需要它的**根目录**。
  用 `--clt <dir>`（别名 `--sdk`）传入，或设 `$HARMONY_SDK`/`$HARMONY_CLT`；不传则自动探测
  `~/command-line-tools`、`~/Library/command-line-tools`、`/Applications/DevEco-Studio.app`、
  `/opt/deveco-studio`、`%ProgramFiles%\Huawei\DevEco Studio`。探测失败就先找到根目录（问用户或搜
  常见安装位置）再传。两种布局（`bin/hvigorw` 或 `tools/hvigor/bin/hvigorw`）都能解析。
- **Node.js ≥ 21**（需要全局 `WebSocket`）。无 npm 依赖，纯标准库。
- **可构建的 HarmonyOS 工程**（根目录有 `build-profile.json5`）。依赖没装（没有 `oh_modules/`）就先
  `ohpm install --all`。**设了 `http_proxy`/`https_proxy` 时 ohpm 会假报 `NOTFOUND package '…'`**
  ——包其实在源上，是代理拦了；用
  `env -u http_proxy -u https_proxy -u all_proxy ohpm install --all` 绕过。
- **平台：macOS / Linux。** 引擎经 Unix-domain socket 通信，运行时不支持 Windows。
- **无头 Linux（ECS/容器/CI）可用，无需 GPU：** 没有 `$DISPLAY` 时编排器自动起 Xvfb + Mesa 软件渲染，
  但依赖要预装——Debian/Ubuntu：`apt-get install -y xvfb libgl1 libglu1-mesa libgl1-mesa-dri
  fonts-noto-cjk`；Fedora：`dnf install -y xorg-x11-server-Xvfb mesa-libGL mesa-dri-drivers
  google-noto-sans-cjk-fonts`。桌面 Linux/macOS 直接复用现有 display。

## 启动预览

单进程编排器：构建、起引擎、起浏览器 viewer、监视 `.ets`，一个进程全包。

```bash
node ${CLAUDE_PLUGIN_ROOT}/skills/harmonyos-live-preview/scripts/preview.mjs \
  --project /absolute/path/to/HarmonyOSProject
```

| 参数 | 作用 | 默认值 |
|---|---|---|
| `--project <dir>` | 工程根目录 | 当前目录 |
| `--module <name>` | 要预览的模块 | entry 类型模块（自动发现） |
| `--page <route>` | 要预览的 `@Entry` 路由，如 `pages/AdaptiveIndex` | pages 配置里第一个页面 |
| `--device <规格>` | 内置档位 `phone`（1080×2340@480dpi 竖屏 = 360×780vp）/ `tablet`（2048×1280@320dpi 横屏 = 1024×640vp），或**任意自定义尺寸** `宽x高[@dpi]`（见下）——断点/响应式调试按 vp 算 | `phone` |
| `--devices <列表>` | 逗号分隔，**同时**预览多个尺寸，例如 `phone,tablet,1440x3200@560`，并排显示在浏览器 viewer 里。给了就覆盖 `--device`。 | 未给时等价于 `--device` 的单一档位 |
| `--clt`/`--sdk <dir>` | 工具链根目录 | 见前置条件 |
| `--port <n>` | viewer HTTP 端口 | `8088` |
| `--ability-mode` | 跑真正的 UIAbility 而不是直接渲染 `--page`（见下） | 关（页面模式） |
| `--no-watch` | 只构建一次，不做编辑后自动刷新 | 默认 watch |
| `--keep-alive` | 浏览器 tab 关闭后不自动释放（无头/常驻用） | 默认自动释放 |

模块、UIAbility、包名、pages 配置都从工程配置文件自动发现，以上参数只是覆盖项。

### 自定义尺寸

`--device`/`--devices` 除了 `phone`/`tablet` 两个内置档位，还接受**任意尺寸规格**：

```
[<设备类型>:]<宽>x<高>[@<dpi>]
```

```bash
--devices 1440x3200@560           # 自定义手机（411×914vp）
--devices tablet:1200x800         # tablet 类型 + 自定义尺寸（dpi 沿用该类型默认值 320）
--devices 2in1:2560x1600@240      # 换设备类型：ArkUI 拿到的 deviceType 也跟着变
--devices phone,tablet,1440x3200@560   # 混着写，并排预览
```

- **设备类型**默认 `phone`，可选 `phone`/`tablet`/`wearable`/`tv`/`car`/`2in1`/`default`（引擎
  `supportedDevices` 全集）。它决定 ArkUI 看到的 `deviceType`，只有 `phone`/`tablet` 有内置默认
  分辨率，其余类型必须显式写尺寸。
- **dpi** 默认按类型取（phone 480 / tablet 320 / 2in1 240 / 其余 320）。**真正决定布局断点的是
  vp = px ÷ (dpi/160)**，只改 px 不改 dpi 等于换了个"更大的屏"，改 dpi 才是换"更密的屏"。
- **范围**：宽高 50–3840 px，dpi 120–640（引擎自己的校验区间）。
- 面板 id 由规格生成（`phone-1440x3200-560dpi`、`tablet-1200x800`），`drive.mjs --device` 用它定位；
  写成和内置档位等价的尺寸（`1080x2340@480`）会回落成 `phone`，不会多开一块面板。
- 每个尺寸的 `-f` 设备配置文件（vp 分辨率 + 安全区）由脚本按该尺寸现算现生成，放在会话私有临时
  目录里，退出时删除。安全区按 **dpi** 换算（状态栏 39vp / 导航条 28vp），不会因为分辨率变大就变粗。

### 同时预览多个尺寸

```bash
node ${CLAUDE_PLUGIN_ROOT}/skills/harmonyos-live-preview/scripts/preview.mjs \
  --project /absolute/path/to/HarmonyOSProject --devices phone,tablet
```

每个尺寸各起一个独立的 `Previewer` 引擎进程，浏览器 viewer 里横向并排各画一块面板；每次重建
（改 `.ets`）会重启**全部**配置的引擎。不传 `--devices` 时单尺寸的行为和开销与以前完全一样。

`drive.mjs` 用 `--device <id>` 选定要操作哪个面板：

```bash
$DRIVE devices                    # 列出已配置的尺寸 + 各自在线状态（含 engineError，见下）
$DRIVE shot --all                 # 一次性截出所有尺寸，写 <out>-<id>.jpg（默认 /tmp/harmony-preview-<id>.jpg）
$DRIVE tap "提交订单" --device tablet   # 只影响 tablet 那块面板
$DRIVE tree --device phone         # 不传 --device 时默认第一个配置的尺寸——单尺寸用法完全不用改
```

### 运行中改尺寸（不重建、不重启引擎）

对应 DevEco 里拖预览窗口边框那件事，走引擎自己的 `ResolutionSwitch` 命令：**引擎不重启、页面状态
不丢**，约 200ms 后新尺寸的帧就到了。

```bash
$DRIVE resize 1440x3000@560              # 改默认面板；省略 @dpi 表示沿用当前密度
$DRIVE resize 720x1560 --device tablet   # 只改 tablet 那块
$DRIVE shot /tmp/after.jpg               # resize 会阻塞到新尺寸的帧真的出现，截图不会截到旧尺寸
```

浏览器 viewer 里则是**拖每块面板右下角的 `⇲`**，松手即生效；面板标题实时显示 `px @dpi · vp`。

- 运行时 resize 的上限比启动参数低：宽高 50–**3000** px（引擎两侧的校验区间本来就不同）。
- 尺寸**扛得住重建**：改 `.ets` 触发的重建会重启引擎，桥接层会在新引擎出首帧后把当前尺寸重新下发，
  不会跳回启动尺寸。
- 设备类型（`deviceType`）不能在运行时改——那是启动参数，换类型要带新 `--device` 重启编排器。
- 安全区厚度是引擎在 resize 时按 px 沿用的，不会按新 dpi 重算（宽度会跟着新分辨率走）。要精确的安全
  区，用启动参数指定该尺寸。

**换页面 = 重启编排器**：`--page` 是启动参数，没有运行时切页接口。预览另一个 `@Entry` 就带新
`--page` 重启（Claude Preview 场景：改 `launch.json` 的 `runtimeArgs` 再 preview-start 一次）。
`--page` 只接受模块 pages 配置（`$profile:main_pages`）里列出的路由。**只有 `@Preview` 没有
`@Entry` 的裸组件（DevEco 的"组件预览"）不支持**（纯 CLI 复刻不了 DevEco 的 IDE 侧实现，考证见
[how-it-works.md § 组件预览调查](references/how-it-works.md#component-preview-investigation)）。
替代方案：预览承载它的页面，或用 [harness 模式](#mock-the-dependency)手写包装页——含 `@Preview`
的文件在页面模式下照常预览，装饰器本身无副作用。

### 优先用宿主应用的内嵌浏览器

如果当前 agent 运行在自带内嵌浏览器/预览工具的宿主里——如 **Claude 的 `Claude Preview` 工具**
（`preview_start`/`preview_screenshot`/`preview_eval`/…）或 **Codex** 的等价机制——优先用它们，
而不是裸 shell 起 `preview.mjs` 再让用户自己开浏览器：宿主工具管得住进程生命周期，还自带截图。

Claude 的接法：在工程根目录 `.claude/launch.json` 里加一项（文件不存在就建；已有其他配置就
追加，别覆盖）：

```json
{
  "version": "0.0.1",
  "configurations": [
    {
      "name": "harmonyos-live-preview",
      "runtimeExecutable": "node",
      "runtimeArgs": [
        "${CLAUDE_PLUGIN_ROOT}/skills/harmonyos-live-preview/scripts/preview.mjs",
        "--project", "/absolute/path/to/HarmonyOSProject"
      ],
      "port": 8088
    }
  ]
}
```

然后按 `name` 调 preview-start 工具（它会复用同配置已在跑的服务，重复调用不会起重复的编排器）。
Codex 或其他宿主：查该宿主自己的启动约定注册预览，不要照搬 `.claude/launch.json` 格式。
完全没有内嵌工具时（纯终端），直接跑 `preview.mjs`，让用户打开打印出的 `http://127.0.0.1:8088`。

无论哪种方式启动，下面的 `drive.mjs` 验证/交互命令都照常可用——编排器会把自己登记到注册表，
`drive.mjs` 自动发现它（多实例时传 `--port`）。

## 核心循环：编辑 → 重建 → 验证

最常见的用法：你刚改了 `.ets`，要拿到"真的生效了"的证据再向用户汇报。

```bash
DRIVE="node ${CLAUDE_PLUGIN_ROOT}/skills/harmonyos-live-preview/scripts/drive.mjs"

# 1) 保存文件后，阻塞到 watcher 触发的这一轮重建结束
$DRIVE wait --for-rebuild        # 构建失败 → 打印 ArkTS 报错行并 exit 1
# 2) 截一帧，用你的图像阅读能力亲眼看
$DRIVE shot /tmp/preview.jpg     # 然后 Read /tmp/preview.jpg
# 3) 机器断言：确认新文案/新组件真的渲染出来了
$DRIVE find "提交订单"            # 打印匹配节点的 rect/归一化中心/源码行；找不到 exit 1
$DRIVE tree --depth 6            # 紧凑组件树大纲：type "文本" rect @源码行
```

避免误报成功的四条规则：

- **别用 sleep，别保存后立刻查 `/status`**——watcher 有 200ms 防抖，立刻查看到的还是**上一轮**
  构建的 `ok`。`wait --for-rebuild` 保证"最新一次被监听的文件变更已经构建完成"，无论保存后隔了
  多久才调用，结论都正确。
- **`wait` exit 3 = 这次编辑根本没触发构建**——watcher 只监听 `<module>/src/main/ets` 下的
  **`.ets`** 文件，改 `resources/`（string.json、图片）、`module.json5` 或其他模块的文件都不会
  触发重建。touch 一个被 watch 的 `.ets`（或重启编排器）让改动进下一轮构建；开着 `--no-watch`
  时同理。
- **构建失败时画面保留上一帧正常内容**——旧帧截图看起来一切正常。先看 `wait` 的退出码，再信截图。
- 每次重建后引擎整个重启（一次完整 `PreviewBuild`，约 3–7 秒），期间 `engineConnected` 短暂为
  false——`wait` 会把构建、引擎重连、出帧三个条件都等齐才返回。

`tree`/`find` 输出里的 `@ entry/src/main/ets/pages/Index.ets(20:9)` 是源码位置：看到哪个节点
渲染得不对，直接映射回源码行去改，不用肉眼在工程里找。

## 与预览交互

浏览器 viewer 页面本身就能点击/滑动/物理键盘输入/系统返回/拖右下角改尺寸（给用户演示用）。脚本化
驱动用 drive.mjs：

```bash
$DRIVE tap "登录"                 # 按渲染文本找元素点其中心；多个匹配会列出，加 --index 消歧
$DRIVE tap 0.5,0.3               # 坐标：0..1 归一化；>1 按设备像素算，find 输出可直接粘贴
$DRIVE swipe 0.5,0.75 0.5,0.25   # 向上滑=列表向下滚；move 事件按真实时间分布，fling 才有速度
$DRIVE tap "请输入内容" && $DRIVE type "hello 123"   # 先 tap 输入框聚焦，再打字
$DRIVE key Enter                 # Enter / Backspace / Tab / Space
$DRIVE back                      # 系统返回：弹路由栈 / 关对话框
$DRIVE resize 720x1560           # 运行中改这块面板的尺寸（见上）
$DRIVE raw FoldStatus '{"FoldStatus":"fold"}' --type set   # 逃生舱：向命令管道发任意引擎命令
```

`raw` 能发引擎支持的任意命令（`FoldStatus`、`Resolution`、`OrientationChanged`、`LoadDocument`
等，完整词汇表见 how-it-works.md）；配合 `PREVIEW_ENGINE_LOG=1` 能看到引擎对每条命令的应答。
`--type` 默认 `action`，**只实现了 `RunSet` 的命令（`ResolutionSwitch`、`FoldStatus`…）必须写
`--type set`**，否则引擎会静默丢弃。

交互后的验证与编辑后一样：`shot` + `find`/`tree` 断言状态变化（点了"关注"之后 `find "已关注"`）。
交互能力在热重载之后依然保持——输入通道随引擎重启自动重接。

**键盘通道没有 IME：只有 `[a-zA-Z0-9 ]` + Enter/Backspace/Tab 能到达引擎，中文和符号打不进去。**
要验证中文文本的显示，把值写进页面/harness 的 `@State` 或 mock 数据，而不是运行时打字。

自己手搓 `/input` 协议时（不经 drive.mjs）：body 为 `{t:"p",phase:"down|move|up",x,y}`（0..1 归一
化）、`{t:"key",key,code}`、`{t:"back"}`。注意键盘 keyAction 用 Previewer 自己的枚举
（DOWN=0/UP=1/PRESS=2），不是 `@ohos.multimodalInput` 的——用错了引擎照样 ack `result:true` 但字
不上屏；drive.mjs 和 viewer 已内置正确值，协议细节见
[how-it-works.md](references/how-it-works.md#driving-input-interaction)。

## 页面起不来？按顺序排查

1. **`$DRIVE wait` exit 1（`build:"error"`）**——读打印出的 ArkTS 报错行，按行号回源码修。
2. **构建 ok 但白屏/空帧**——页面运行时访问了 Previewer 模拟不了的东西。引擎是 UI 沙箱不是完整
   运行时：白名单外的组件（`Web`、`Video`、`XComponent`、`RichEditor`、瀑布流 `Grid`——布局辅助的
   `GridRow`/`GridCol` 反而在白名单里）和接口（除 `http.createHttp` 外的网络、传感器、大多数
   Ability/Context 调用）**构建照样成功**，运行时才白屏或抛异常。对照
   [references/preview-coverage.md](references/preview-coverage.md) 的完整白名单；依赖注入类失败
   （`@Link`/`@Consume` 根组件、未 mock 的 HSP、真实后端）→ 用下面的 harness 模式。先查
   `$DRIVE devices`（或 `/status` 的 `engineError` 字段）——引擎会把运行时报错主动推回来，常常
   已经有可读的报错文本。更完整的原始输出（ArkTS console、`LoadPage` 失败、JS 异常）用
   `PREVIEW_ENGINE_LOG=1` 启动 `preview.mjs`——引擎 stdout 默认被丢弃，这个开关把它放出来。
3. **`engineConnected:false` 且不恢复**——引擎进程没起来，业务代码一行都没跑到。无头 Linux 查
   Xvfb/Mesa 依赖是否装齐（见前置条件）；查工具链根目录是否解析正确（`--clt`）；`lws` 端口被上一轮
   的孤儿引擎占着时日志会有 `lws_socket_bind: ERROR on binding`，换 `--lws` 重启即可。
   `PREVIEW_ENGINE_LOG=1` 里如果是 `load hsp failed, hsp name:<module>`，说明某个 `"type": "shared"`
   依赖缺 `.preview/config/buildConfig.json`——正常情况下编排器每次构建后会自动补齐（日志里的
   `preview-config: wired …`），没补上就看那个模块有没有产出 `.preview/<product>/intermediates/
   loader_out/<target>/ets/modules.abc`。
4. **组件树只有 root 没 children**——引擎跑的不是 `PreviewBuild` 产物。正常流程不会发生；见
   [how-it-works.md](references/how-it-works.md#getting-the-arkui-inspector-tree)。

<a id="mock-the-dependency"></a>

## 当页面起不来时：mock 掉依赖

耦合重的真实工程里，入口页往往一开就白屏。**先按报错原文分类，再选招**——不同类别解法完全不同，
用错了白费功夫。完整决策表、每种配方的可运行代码和验证命令都在
**[references/mock-playbook.md](references/mock-playbook.md)**，动手写 mock/harness 前先读它。
分类速查：

- **F 类（最高频）：组件树只有一个空 `Navigation`。** 现代模板的 entry 页面基本都是"空壳 +
  `NavPathStack.pushPathByName` 具名路由跳真首页"，具名路由在 Previewer 沙箱里解析不到 builder
  （`PREVIEW_ENGINE_LOG=1` 可见 `Builder function is empty`），**`--ability-mode` 救不了**。解法：
  写一个 `@Entry` harness 直接调目标页的 Builder（函数名就在 `router_map.json` 的 `buildFunction`
  里），注册进 `main_pages.json` 后 `--page` 预览，不动业务代码。同一招直接用于预览二级/三级页面
  （详情页、设置页）——`XxxBuilder()` 基本都是零参的，真正的参数在 `NavPathStack` 单例 /
  `AppStorageV2` 这类全局 store 里，**harness 要在渲染前把 store 灌好**；时间主要花在读源码搞清
  参数从哪来，不是编译。配方见
  [mock-playbook.md § 绕开具名路由](references/mock-playbook.md#绕开具名路由)。
- **A 类（页面直接摸 UIAbility/窗口）——改 3 行就好。** 报错形如
  `Cannot read property getMainWindowSync of undefined`：页面模式不跑 UIAbility，context 上没有
  `windowStage`，成员初始化就抛异常，整页 build 不出来（`@MockSetup` 也救不了，它跑得更晚）。解法：
  把这条链路声明成 `| undefined` + `?.`，真机行为不变。变体：初始化逻辑写在 `EntryAbility.onCreate`
  里、页面模式压根不执行——这类加 `--ability-mode` 就好，0 改动；加完**必须再看一次 `tree`**，别只
  看异常日志。配方见 [mock-playbook.md § 防御式改写](references/mock-playbook.md#防御式改写)。
- **B 类（数据层拿不到数据，骨架在但内容空）——用官方 Hamock 模块 mock。** 被预览模块加
  `@ohos/hamock` devDependency + `src/mock/mock-config.json5`。`preview.mjs` 每次构建后会自动补上
  DevEco 才写的 `.preview/config/buildConfig.json`，所以这套机制在纯 CLI 下**开箱可用**——启动日志
  出现 `mock: wired …` 就说明接上了。**mock 只能写在被预览的那个模块里**，替换依赖模块的实现也得在
  entry 下写、用包名做 key。配方见 [mock-playbook.md § 模块 mock](references/mock-playbook.md#模块-mock)。
- **D 类（`@Link`/`@Consume`/`@ObjectLink` 缺父级提供者）或只想单独看某个组件——harness 包装页。**
  加一个 `@Entry` 自己当父组件喂字面量 mock，注册进 pages 配置后 `--page` 预览。注意 ArkTS 的
  `{...}` 字面量只能初始化没有自定义构造函数/`readonly` 字段/方法的类型，否则构建直接死在
  `arkts-no-obj-literals-as-types`；验证完删掉 harness 或排除出正式构建——它是普通 `@Entry`，留在
  pages 配置里会被打进正式包。配方见
  [mock-playbook.md § harness 包装页](references/mock-playbook.md#harness-包装页)。

无论用哪招，都用 `$DRIVE find "<mock 特征文案>"` 断言 mock 真的生效，别靠截图肉眼判断。

## 预览模式（page vs ability）

- **页面模式（默认）**——直接渲染 `--page` 指定的 `@Entry` 路由，等价于 DevEco 的单页预览。不运行
  任何 UIAbility，所以即使 ability 的 `loadContent` 加载的是别的页面，任意已注册 `@Entry` 都能显示。
  `@ohos.router` 的页面间跳转在此模式下照样可用。
- **Ability 模式（`--ability-mode`）**——启动真正的 UIAbility（走 `onCreate`/`onWindowStageCreate`
  生命周期），显示它 `loadContent` 的内容；此时 `--page` 不生效。需要走 ability 启动逻辑时才用。

## 生命周期／释放

不会留孤儿 `Previewer` 进程，不需要用户手动收拾：

- **关浏览器 tab → 自动释放**（viewer 的 SSE 存活通道断开后 ~10 秒宽限）。只在浏览器连接过之后才
  生效，所以纯 `drive.mjs`/curl 的无头流程不会被误杀；`--keep-alive` 彻底关闭。
- **会话结束 → 兜底清理**：`scripts/cleanup.mjs` 按 `$TMPDIR/harmonyos-live-preview/sessions/`
  注册表精确终止（不是 `pkill`）。Claude Code 用 `SessionEnd` 钩子自动调它
  （[hooks/hooks.json](../../hooks/hooks.json)）；没有会话结束钩子的宿主（Codex、OpenCode、纯终端）
  直接跑这个脚本即可——它本来就只是兜底，关标签页和 Ctrl-C 两条路径不依赖它。
- **手动**：Ctrl-C。三条路径走同一个幂等 shutdown。

注册表是机器上**全局共享**的一个目录，所以每条记录都带一个 owner，cleanup 默认只清自己的——否则多个
agent 会话并行时，任何一个会话结束都会把别人正在跑的预览一起杀掉。owner 的取值与宿主无关：

```bash
export HARMONY_PREVIEW_OWNER=<任意标识>   # 任何宿主/脚本都能用这个声明归属
node cleanup.mjs                          # 只清本 owner 的
node cleanup.mjs --session <id>           # 清指定 owner 的
node cleanup.mjs --all                    # 无视归属全清（逃生舱）
```

不设 `HARMONY_PREVIEW_OWNER` 时会退回读 `CLAUDE_CODE_SESSION_ID`（Claude Code 会注入它，钩子还会把
`{session_id}` 从 stdin 传进来）；**两者都没有就退化成"全清"**，也就是加这个机制之前的行为，所以在
Codex/OpenCode 下不会漏清。没有 owner 的旧记录同样照清，兜底不打折。

引擎进程如果因为原生崩溃卡在不可中断等待（`ps` 里 `UE` 状态），`kill -9` 也杀不掉，会一直占着它的
`--lws` 端口——换一个 `--lws` 重启即可，不用在清理上耗时间。

**同一个工程可以同时开多个预览**（不同 `--port`/`--lws`，比如对照两个页面）：hvigor 的
`.preview/<product>/` 构建树是按工程共享的，并发跑 `PreviewBuild` 会互相写坏中间产物（症状是
build FAILED，报 `JSON5: invalid end of input` 或资源重复声明），所以编排器之间用一把跨进程
锁把构建排队，日志里会看到 `build lock: another preview is building this project — waiting`。等的只是
构建那几秒，引擎和交互全程并行。**预览不同工程不受影响**，锁按工程+product 分。

## HTTP 接口（桥接层）

drive.mjs 覆盖了下列接口的常见用法；直接访问适合自定义驱动或宿主工具（`preview_eval` 等）：

| 路由 | 说明 |
|---|---|
| `/` | 可交互 viewer 页面，每个配置的设备一块面板（含各自的 `#a11y` 组件树 DOM 叠加层，浏览器自动化可见真实元素；右下角 `⇲` 可拖拽改尺寸） |
| `/status` | 顶层字段镜像"默认设备"（`--devices` 里第一个）：`{engineConnected, hasFrame, resolution, density, launchResolution, launchDensity, frameResolution, interactive, frameAgeMs, engineError, build, buildError, buildAgeMs, buildStartedAgoMs, lastChangeAgeMs}`；`build` 状态机：`idle→building→ok\|error`；另加 `devices` 数组，逐个设备给出同样的字段。几何三件套：`resolution/density` 是**当前**尺寸（跟随运行时 resize），`launchResolution/launchDensity` 是引擎启动时的尺寸，`frameResolution` 是手上这一帧的真实像素（resize 后要 ~200ms 才跟上） |
| `/devices` | 和 `/status.devices` 内容一样，单独暴露一份，方便只要设备列表不要构建状态的场景 |
| `/frame.jpg` | 默认设备当前帧 JPEG（无帧时 503） |
| `/devices/:id/frame.jpg` | 指定设备的当前帧 JPEG |
| `/mjpeg` / `/devices/:id/mjpeg` | `multipart/x-mixed-replace` 流，默认设备 / 指定设备 |
| `/inspector` / `/devices/:id/inspector` | ArkUI 组件树 JSON：`{$type, $rect, $debugLine, $attrs（含渲染文本 content/placeholder 与无障碍字段）, $children}`；引擎未就绪 503 |
| `/input` / `/devices/:id/input` | `POST` 输入事件 → 引擎命令（见上），打给默认设备 / 指定设备 |
| `/resize` / `/devices/:id/resize` | `POST {width, height, density?}` 运行时改尺寸（引擎 `ResolutionSwitch`，不重建不重启）。越界 400，命令管道没连上 503，成功返回该设备的最新状态 |
| `/alive` | viewer 的 SSE 存活通道（驱动自动释放，全局一份，不分设备） |

单设备时，`/status` 顶层字段、`/frame.jpg`、`/inspector`、`/input` 的行为与多尺寸支持之前完全
一样——`/devices/:id/...` 和 `devices` 数组是纯增量，不影响任何现有对接。

## 已知限制（相比 DevEco）

- **重载更慢**：一次重载 = 完整 `PreviewBuild`（约 3–7 秒）+ 引擎重启，没有 DevEco 的亚秒级原地
  热替换。交互能力则持平（同一条命令通道）。
- **单次预览级的 `colorMode`/`locale` 不可切换**——固化为档位里的默认值。
- **设备类型不能运行时切**——尺寸能拖着改，`deviceType` 只能靠重启编排器换。
- **裸 `@Preview` 组件预览不支持**——用 harness 模式替代（见上）。

取舍的完整分析见 [how-it-works.md](references/how-it-works.md#trade-offs)。
