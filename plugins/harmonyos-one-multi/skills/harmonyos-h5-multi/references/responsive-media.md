# 响应式图片、背景图与视频

## 何时使用

命中 `H5-09` 时完整读取本文件：媒体溢出或拉伸、宽屏模糊、窄屏下载超大资源、不同窗口需要不同裁切、`srcset/sizes/picture/image-set` 配置异常、视频随窗口变化被裁坏或重新加载。

如果媒体尺寸正常且问题只来自父级 Grid/Flex 约束，主场景仍是 `H5-01`；只读取 `responsive-layout.md`。如果候选语法在最低目标内核不工作，再把 `H5-06` 作为次场景并读取兼容矩阵。

## 先判语义和变化类型

| 问题 | 首选机制 | 关键证据 |
| --- | --- | --- |
| 图片/视频越界或变形 | 流式 CSS、固有尺寸、`aspect-ratio`、合适的 `object-fit` | 媒体 rect、父容器、固有宽高 |
| 相同构图、CSS slot 固定，仅 DPR 不同 | `srcset` 的 `1x/2x` 描述符 | CSS 显示尺寸固定，只有像素密度变化 |
| 相同构图、slot 随窗口或列数变化 | `srcset` 的 `w` 描述符 + `sizes` | 每个断点/容器下的实际 slot 宽度 |
| 宽窄窗口需要不同裁切或视觉重点 | `<picture><source media>` + `<img>` 回退 | art direction 需求，不只是清晰度 |
| 装饰性 CSS 背景需要密度/格式候选 | `image-set()`，保留普通 `background-image` 回退 | 背景不承载必要信息 |
| 视频只需适应容器 | 流式盒、稳定比例、`object-fit` | 不因 resize 更换流或重建播放器 |

不要同时用 `x` 和 `w` 描述同一个 `srcset`。`sizes` 描述的是图片在 CSS 布局中的预计 slot，不是物理屏幕宽度，也不是候选文件宽度。

## 所有权补充

沿用 `capability-boundary.md` 的输入模式。媒体布局和候选选择通常由 H5 独立完成；只有资源 URL、签名、权限或业务清单来自原生时才扩展共享契约。ArkTS 提供可用资源数据，H5 根据 slot、DPR 和媒体条件表达选择规则，不在原生按机型换图。标准 HTML/CSS 能自行响应 viewport 时，不额外创建屏幕变化事件。

## 源码审计

1. 沿组件定位媒体 DOM、包装容器、对应 CSS、图片加载器/CDN 参数和框架封装，确认修改的是源文件而非构建产物。
2. 记录 `currentSrc`、`naturalWidth/Height`、`clientWidth/Height`、DPR、computed `object-fit/aspect-ratio` 和父容器尺寸。
3. 枚举 `src/srcset/sizes/source media/type` 与候选文件固有尺寸；确认候选真的是不同资源，不是多个 URL 指向同一文件。
4. 连续改变 viewport 和组件容器，记录每个布局状态的真实 slot。`sizes` 必须近似这些值并与 CSS 断点同时维护。
5. 检查内容语义、`alt`、宽高属性、懒加载和首屏关键媒体；不要为追求自适应破坏可访问性或 LCP。

## 基础尺寸约束

```css
.media-frame {
  overflow: clip;
  aspect-ratio: 16 / 9;
}

.media-frame > :is(img, video) {
  display: block;
  inline-size: 100%;
  block-size: 100%;
  object-fit: cover;
}
```

只有允许裁切时才使用 `cover`。证件、图表、二维码、商品全貌等不能丢失边缘信息的内容优先 `contain` 或自然高度。为 `<img>` 提供与默认资源比例一致的 `width`/`height` 属性，浏览器可在资源加载前预留空间；CSS 仍可覆盖最终显示尺寸。

## 同构图分辨率切换

slot 随布局变化时使用 `w + sizes`：

```html
<img
  src="news-640.jpg"
  srcset="news-480.jpg 480w, news-960.jpg 960w, news-1440.jpg 1440w"
  sizes="(min-width: 840px) 28rem, (min-width: 600px) 50vw, 100vw"
  width="1440"
  height="810"
  alt="救援人员在河岸转移受困群众"
>
```

示例数值不是通用断点。先读取项目 CSS 中实际列宽、gap、侧栏和 max-width，再写 `sizes`。如果 CSS 改变列数或最大宽度，同一改动必须检查 `sizes`；否则视觉布局正确但浏览器仍可能下载错误候选。

slot 固定且只需要高密度资源时使用 `x`：

```html
<img
  src="avatar-48.png"
  srcset="avatar-48.png 1x, avatar-96.png 2x"
  width="48"
  height="48"
  alt="张明头像"
>
```

## 不同构图与格式

不同窗口需要改变裁切或视觉重点时使用 `<picture>`，始终保留最终 `<img>`：

```html
<picture>
  <source media="(min-width: 840px) and (orientation: landscape)" srcset="hero-wide-1600.jpg" width="1600" height="900">
  <source media="(min-width: 600px)" srcset="hero-square-960.jpg" width="960" height="960">
  <img src="hero-portrait-640.jpg" width="640" height="800" alt="发布会主讲人站在新品屏幕前">
</picture>
```

`media` 条件应与构图开始失效的位置一致，不按设备名书写。构图比例不同时给各 `<source>` 提供对应固有尺寸，并在最低目标内核验证布局预留；必要时用同条件 CSS `aspect-ratio` 保底。格式协商可用带 `type` 的 `<source>`，但不要让格式分支与构图分支失去可维护的回退顺序。

装饰背景可渐进增强：

```css
.hero-decoration {
  background-image: url("texture.jpg");
  background-image: image-set(
    url("texture.avif") type("image/avif") 1x,
    url("texture@2x.avif") type("image/avif") 2x,
    url("texture.jpg") type("image/jpeg") 1x
  );
}
```

背景图不会向辅助技术提供内容语义。图片若对理解新闻、商品、图表或操作不可缺少，改用 `<img>`/`picture` 与有效 `alt`，不要用 `image-set()` 掩盖语义问题。

## 视频与动态窗口

视频优先保持播放器节点、播放位置和媒体流稳定，只改变其布局盒：

```css
.video-player {
  display: block;
  inline-size: 100%;
  max-inline-size: 72rem;
  aspect-ratio: 16 / 9;
  block-size: auto;
  background: #000;
}
```

不要在 `resize`、折叠或旋转回调里调用 `load()`、替换 `src` 或重建播放器，除非业务明确要求切流且能恢复播放位置、字幕、音轨和错误状态。直播/DRM/自适应码流属于播放器与媒体传输能力，不在本布局 skill 内重新设计。

## 动态切换语义

- viewport 或 `<source media>` 条件变化后，浏览器会重新评估可用候选，但可能复用已经下载的较高分辨率资源。
- 宽屏缩回窄屏后 `currentSrc` 没降级，不应直接判失败或强制 reload；浏览器避免重复网络请求可能更合理。
- 验证重点是首次进入各窗口时选择合理、放大后清晰、缩小时不溢出、相同最终布局视觉一致，以及没有因自定义 JS 造成重复下载。
- 框架图片组件可能改写 URL、生成 `srcset` 或延迟挂载；以最终 DOM、`currentSrc` 和 Network 为证据，不只看模板源码。

## 禁止模式

- 禁止用 UA、设备型号、折叠状态或 `screen.width` 手动拼接图片 URL；它们不能表达组件真实 slot。
- 禁止给变化 slot 的内容图只写 `2x/3x`；DPR 描述符不能替代布局宽度提示。
- 禁止使用 `w` 描述符却省略 `sizes`；默认估算可能接近 `100vw`，在多栏卡片中浪费带宽。
- 禁止让 `<picture>` 缺少 `<img src>` 回退、固有尺寸和可访问文本。
- 禁止对所有图片默认 `loading="lazy"`；首屏关键图可能因此延迟。是否 lazy 根据首屏位置和项目性能证据决定。
- 禁止用 `object-fit: cover` 隐藏错误比例；先判断裁切是否符合内容语义。
- 禁止把“每次 resize 都重新下载更精确尺寸”作为验收标准；会制造网络抖动并丢失缓存收益。

## 验证矩阵

每个状态记录 viewport、容器宽度、DPR、`currentSrc`、固有尺寸、渲染尺寸、裁切、网络请求和布局位移：

- 直板机首次加载，检查默认 `src`、alt、比例和首屏性能。
- 外屏启动 → 展开内屏，检查 slot 增大后的清晰度与构图。
- 内屏启动 → 折叠外屏，检查不溢出；允许复用已加载大图。
- 内屏竖屏 ↔ 横屏，检查 `<picture>` media 临界值两侧的构图。
- 平板分屏连续调整，检查多栏 slot 与 `sizes` 一致。
- DPR 1/2/3 或目标环境可用档位，检查候选覆盖而非无意义放大。
- 慢网/缓存路径，检查首屏关键图、懒加载和重复请求。
- 200% 字体缩放与长文本，检查媒体不会挤压标题、操作或说明。

完成条件：直板机无退化；目标窗口无拉伸、错误裁切或模糊；候选资源覆盖真实 slot 与 DPR；语义内容可访问；动态窗口不依赖 reload；最低支持环境有可用 `src`/背景/视频基线。
