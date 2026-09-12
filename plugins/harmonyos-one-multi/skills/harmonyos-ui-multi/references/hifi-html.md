# 高保真 HTML 生成规范

本规范定义 HarmonyOS 一多 UI 高保真 HTML 的设备展示、视觉基线和可实现性约束。

## 输入依据

生成前必须读取：

1. 当前需求中的问题范围、目标形态和已确认设计决策；
2. [device-matrix.md](device-matrix.md) 中对应设备的尺寸、断点与折叠状态；
3. 工程现有页面源码和资源。

截图、布局树和运行证据均为可选输入。当前环境能够读取并确认内容时才可作为设计依据；无法读取时直接忽略，不得推测。没有可用运行态证据时，依据源码生成，并在 `overview` 中标记“源码推断，待运行态核实”。

## 与实现的关系

- HTML 只表达已给定范围内的视觉目标，不自行新增页面、业务或修改范围。
- 每处目标效果应能映射到具体页面/组件、目标形态和计划修改文件；调用方提供问题或需求 ID 时再展示该 ID。
- 代码实现按 HTML 中的布局、比例、位置、间距和组件状态落地；与最新需求不一致时先同步更新视觉稿。

## 组织方式

先读取需求或调用方提供的目标设备类型，按下表生成默认预览。同一 HTML 按页面分节，文件位置与命名由调用方决定。

| 设备类型 | 默认展示设备 | 默认形态 |
|---|---|---|
| `phone` | 直板机 | 竖屏 |
| `foldable` | 普通双折叠（如 Mate X6/X7） | 内屏展开、竖屏 |
| `foldable` | 阔折叠 Pura X Max | 内屏展开、横屏 |
| `tablet` | 平板 | 横屏 |

包含 `phone / foldable / tablet` 时，**每个页面固定展示以上四张预览**，按表中顺序排列；不能只在首个页面凑齐四种。部分设备范围只保留对应类型的预览及手机基线，`foldable` 始终包含普通双折叠和阔折叠。

默认直接展示正常态，不询问形态选择，不提供横竖屏、折展或悬停等状态选择器，也不额外生成外屏、三折叠或其他方向的画布。只有用户明确要求其他预览形态时才调整；SPEC 或验证计划中的其他状态不自动扩展预览。此规则只决定高保真展示，不改变适配和测试范围；设备矩阵仅用于查取对应参数，不穷举其中所有设备与状态。

## 固定文档骨架

HTML 必须保留以下结构和标识：

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>项目名 - 一多高保真设计稿</title>
  <style>
    /* 其余样式按项目生成；设备比较区保留以下基础约束。 */
    .compare { display:flex; align-items:flex-start; gap:28px; overflow-x:auto; }
    .device-frame {
      --preview-width:320px;
      --preview-height:359px;
      --stage-height:419px;
      --frame-extra:6px;
      flex:0 0 calc(var(--preview-width) + var(--frame-extra));
      width:calc(var(--preview-width) + var(--frame-extra));
    }
    .screen-wrap {
      width:max-content;
      box-sizing:content-box;
      margin:max(0px, calc(var(--stage-height) - var(--preview-height) - var(--frame-extra))) auto 0;
      border:1px solid #444;
      border-radius:14px;
      background:#111;
      padding:2px;
    }
    .screen { width:var(--preview-width); height:var(--preview-height); overflow:hidden; }
    .device-ui {
      width:var(--canvas-width);
      height:var(--canvas-height);
      transform:scale(var(--preview-scale));
      transform-origin:top left;
    }
    .anno { width:100%; white-space:normal; overflow-wrap:anywhere; }
  </style>
</head>
<body>
  <header class="topbar">...</header>
  <aside class="rule-strip">...</aside>

  <section class="doc-section" id="overview">...</section>

  <section class="doc-section hifi-page"
    data-page="首页"
    data-source="entry/src/main/ets/pages/HomePage.ets"
    data-runtime-state="源码推断，待运行态核实"
    data-changes="可选的需求或问题 ID">
    <div class="compare">
      <div class="device-frame" data-device="phone-sm"
        style="--canvas-width:374px;--canvas-height:827px;--preview-scale:.5;--preview-width:187px;--preview-height:413.5px;--stage-height:419.5px">
        <div class="screen-wrap"><div class="screen"><div class="device-ui">直板机竖屏基线 UI</div></div></div>
        <div class="anno">直板机 · 竖屏</div>
      </div>
      <div class="device-frame" data-device="foldable-portrait"
        style="--canvas-width:711px;--canvas-height:798px;--preview-scale:.45;--preview-width:319.95px;--preview-height:359.1px;--stage-height:419.5px">
        <div class="screen-wrap"><div class="screen"><div class="device-ui">普通双折叠展开态 UI</div></div></div>
        <div class="anno">Mate X6/X7 · 内屏展开 · 竖屏</div>
      </div>
      <div class="device-frame" data-device="foldable-wide-landscape"
        style="--canvas-width:939px;--canvas-height:664px;--preview-scale:.34;--preview-width:319.26px;--preview-height:225.76px;--stage-height:419.5px">
        <div class="screen-wrap"><div class="screen"><div class="device-ui">阔折叠展开态 UI</div></div></div>
        <div class="anno">Pura X Max · 内屏展开 · 横屏</div>
      </div>
      <div class="device-frame" data-device="tablet-landscape"
        style="--canvas-width:1137px;--canvas-height:711px;--preview-scale:.28;--preview-width:318.36px;--preview-height:199.08px;--stage-height:419.5px">
        <div class="screen-wrap"><div class="screen"><div class="device-ui">平板横屏 UI</div></div></div>
        <div class="anno">平板 · 横屏</div>
      </div>
    </div>
  </section>

  <section class="doc-section" id="implementation-map">...</section>
  <section class="doc-section" id="acceptance">...</section>
</body>
</html>
```

`--canvas-width/--canvas-height` 使用目标窗口的逻辑尺寸；`--preview-scale` 在两个方向使用同一缩放比例，`--preview-width/--preview-height` 为缩放后的展示尺寸；同一 `.compare` 的 `--stage-height` 统一取最大设备外框高度，使各设备屏幕底边对齐。

上述骨架示例覆盖三类设备、四张预览，实际尺寸按 `device-matrix.md` 对应行取值。每个页面按默认映射或用户明确指定的预览形态，在同一个可横向滚动的 `.compare` 中展示，不得拆成上下互不对应的多个页面段落。

## 生成规则

1. 手机 `sm` 页面是基线，只允许为修复现有问题做最小调整，不重新设计信息架构。
2. 只重排工程已有内容；不得新增业务模块、营销文案、虚构控件、项目外图片或无依据的交互。
3. 设备名称、状态、宽高、断点和折痕方向必须来自 `device-matrix.md` 或实际运行窗口，不得猜测。
4. 每处目标形态变化都必须关联页面/组件和计划修改文件，并在 `implementation-map` 中列出目标形态/断点、视觉效果、关键比例/位置/状态和可实施的 ArkUI 策略。ArkUI 策略可使用 `GridRow/GridCol`、`List.lanes`、`Navigation`、`SideBarContainer`、Tabs 挪移或内容缩进。
5. 设备框内只展示应用 UI；设计说明、证据、风险和实现建议放在设备框外。
6. 应用根容器必须填满设备框。设备外框须按屏幕内容收缩，边框和内边距不得压缩屏幕或产生单侧黑块；同组设备按屏幕底边对齐，框外说明自动换行且不得撑宽设备列。黑色背景只允许用于真实相机或视频区域，不能用来填补布局空白。
7. 设备内部 UI 必须先按目标窗口逻辑尺寸排版，再用单一比例整体缩放到预览框；不得只根据预览宽度推导字号、纵向间距或组件高度。填充剩余空间的 Flex/Grid 子项应允许收缩，必要时使用 `min-width/min-height: 0` 与 `minmax(0, 1fr)`；不得用 `overflow:hidden` 掩盖内容溢出。
8. 标注 `span/offset`、分栏比例或折痕避让时，视觉宽度和位置必须真实体现该比例，不能只写文字说明。
9. HTML 必须自包含：CSS 写在文件内，不使用 CDN、网络字体、远程脚本或其他运行依赖。

## HarmonyOS 设计基线

先继承工程现有页面、资源和设计令牌，再应用已确认设计决策、`device-matrix.md` 与运行窗口约束；仅当工程没有明确规范时，才使用以下基线。不得借适配替换品牌色、字体体系、圆角、阴影或信息层级。

- **单位与网格**：实现标注使用 `vp`，文字使用 `fp`；新增或调整的间距优先对齐 8vp 网格，小元素允许按 4vp 对齐。HTML 可按比例缩放设备框，但展示比例必须与标注值一致。
- **边距与留白**：手机页面边距通常为 16–24vp，平板或折叠屏展开态通常为 24–32vp。宽屏允许通过栅格、内容最大宽度和左右缩进形成有依据的留白，不得为了填满屏幕新增装饰内容。
- **文字与可读性**：新增或调整的正文不小于 14fp，行高保持 1.4–1.6 倍并支持系统字体缩放；文字与背景对比度不低于 4.5:1，大文字和交互元素不低于 3:1。放大字体后不得发生关键内容截断、重叠或操作入口丢失。
- **触摸与状态**：可点击区域不小于 48vp × 48vp，相邻交互区域至少间隔 8vp。仅在需求涉及相关交互时展示默认、按下、禁用、加载、空状态或焦点状态，并保持同类组件一致。
- **安全区域**：状态栏、导航条、手势区域、软键盘和折痕均视为不可遮挡区域；关键文字、主操作和连续内容不得跨越折痕或落入系统遮挡区。悬停态按真实折叠方向划分内容区与控制区。
- **视觉层级**：优先复用工程已有颜色、图标和组件样式；同类元素保持一致，父容器圆角不小于子元素。仅在已有设计或层级表达确有需要时使用阴影，禁止用额外卡片、渐变或装饰掩盖布局问题。

## 必备内容

- `overview`：页面、目标设备、设计依据及运行证据状态；
- `hifi-page`：每个页面的手机基线、目标设备效果和关联变化；
- `implementation-map`：`页面/组件 → 计划文件 → 形态/断点 → 视觉效果 → 关键比例/位置/状态 → ArkUI 策略`；
- `acceptance`：目标设备覆盖、问题覆盖、手机基线、无虚构内容、实现映射和证据限制。

## HTML 生成后自检

HTML 交付前至少确认：

- 文件不存在未替换的 `{{...}}`；
- `topbar`、`rule-strip`、`overview`、`hifi-page`、`compare`、`implementation-map` 和 `acceptance` 均存在；
- 需求范围内每个页面和变化都能在 HTML 中找到；
- `implementation-map` 中的页面、计划文件、目标形态和视觉效果相互一致；
- 逐个 `hifi-page` 核对设备覆盖：全量三类设备默认恰好四张预览，分别为直板机竖屏、普通双折叠展开竖屏、Pura X Max 展开横屏、平板横屏；无默认状态选择器或擅自增加的形态，用户明确指定的例外按需求核对；
- 设计沿用工程现有体系，新增布局符合 vp/fp、8vp 网格、文字对比度和 48vp 触摸目标要求；
- 目标形态已体现系统栏、软键盘、折痕和字体缩放等与本批问题相关的安全区域；
- 每个设备的首尾内容、最后一行列表或网格、底部操作和安全间距均完整可见；预期滚动的区域应明确表现为可滚动，不得被设备框静默裁切；
- 文件中不存在 `http://`、`https://` 或远程资源依赖；
- 本地浏览器可直接打开，页面没有明显裁切、溢出、设备框底部空白或错误留白。

校验失败时不得宣称生成成功；应先修复文件或说明失败原因。

## 交付给用户

HTML 自检通过后，调用当前 Agent 或插件提供的 HTML 预览能力，将 HTML 绝对路径交给该工具。预览成功后再提示用户查看，并同时说明文件路径；不得只回复路径或 Markdown 链接。

如果当前环境没有 HTML 预览工具，或预览调用失败，应明确说明预览未成功打开，并将文件路径作为人工打开的兜底方式，不得宣称已完成预览交付。
