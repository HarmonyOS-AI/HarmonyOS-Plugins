# H5 响应式布局与动态窗口

## 基线

```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
```

不要禁用用户缩放。全局使用 `box-sizing: border-box`，为图片、视频和长文本设置可收缩约束。

```css
*, *::before, *::after { box-sizing: border-box; }
img, video { max-inline-size: 100%; block-size: auto; }
.text { min-inline-size: 0; overflow-wrap: anywhere; }
```

这只能解决媒体溢出。出现图片模糊、资源过大、不同窗口需要不同构图、视频裁切或 `srcset/sizes` 问题时，转读 `responsive-media.md`，不要把资源选择塞进普通布局断点。

## 断点策略

从内容断裂位置选择断点，不把设备名称写入 CSS。项目已有断点时先复用；没有时先使用少量语义状态，再用实测调整。

```css
.page { display: grid; grid-template-columns: minmax(0, 1fr); }

@media (min-width: 600px) {
  .cards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (min-width: 840px) {
  .page { grid-template-columns: 16rem minmax(0, 1fr); }
}
```

为组件使用 container query，避免组件被放入侧栏或分屏后仍按整个 viewport 排版：

```css
.panel { container-type: inline-size; }
.card { display: grid; gap: 1rem; }

@container (min-width: 32rem) {
  .card { grid-template-columns: 10rem minmax(0, 1fr); }
}
```

若最低内核不支持 container query，先保留单栏基线，再用 `@supports (container-type: inline-size)` 包裹增强规则。

## 动态窗口

纯视觉变化交给 CSS。业务逻辑确实依赖布局状态时才监听。项目已有 JS 动态 REM 时，根字号重算属于渲染基础设施而非业务状态，命中该场景应改读 `rem-responsive.md`。

```typescript
const expanded = window.matchMedia('(min-width: 840px)');

function syncMode(event: MediaQueryList | MediaQueryListEvent): void {
  document.documentElement.dataset.layout = event.matches ? 'expanded' : 'compact';
}

syncMode(expanded);
expanded.addEventListener('change', syncMode);

// SPA 卸载时执行：expanded.removeEventListener('change', syncMode)
```

组件响应使用 `ResizeObserver`，回调中只读取必要尺寸，合并写操作，避免读写交错造成 layout thrashing。

## 视口高度

移动端地址栏、输入法和沉浸式区域可能改变可视高度。优先使用动态视口单位，并为旧内核保留回退：

```css
.app-shell { min-block-size: 100vh; }
@supports (min-height: 100dvh) {
  .app-shell { min-block-size: 100dvh; }
}
```

不要默认使用固定 `height: 100vh` 包住全部内容；内容增长时应允许滚动。

## 验证

- 在 320、599/600、839/840、宽屏视口及断点两侧测试。
- 连续拖动窗口，而不是只刷新几个固定尺寸。
- 检查横向滚动、焦点、滚动位置、长文本和 200% 字体缩放。
- 在分屏中使用实际 Web 组件宽度，不以物理屏幕截图推断。
