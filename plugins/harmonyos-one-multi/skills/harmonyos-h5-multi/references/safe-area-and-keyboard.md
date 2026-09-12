# 安全区与软键盘

## 安全区

在 viewport 声明中启用 `viewport-fit=cover` 后，使用环境变量为内容留出空间；背景可以延伸，关键内容不能被系统区域遮挡。

```css
:root {
  --safe-top: env(safe-area-inset-top, 0px);
  --safe-right: env(safe-area-inset-right, 0px);
  --safe-bottom: env(safe-area-inset-bottom, 0px);
  --safe-left: env(safe-area-inset-left, 0px);
}

.app-shell {
  padding: var(--safe-top) var(--safe-right) var(--safe-bottom) var(--safe-left);
}
```

不要给所有嵌套容器重复叠加 safe area。确定一个页面级消费点；固定底栏可单独使用 `padding-bottom`。

## 软键盘

优先让页面保持正常滚动，使浏览器能够将焦点元素滚入可视区。需要自定义浮层或固定操作栏时，读取 `visualViewport` 并提供无该 API 的回退。

```typescript
function updateViewport(): void {
  const viewport = window.visualViewport;
  const visibleHeight = viewport?.height ?? window.innerHeight;
  document.documentElement.style.setProperty('--visible-height', `${visibleHeight}px`);
}

window.visualViewport?.addEventListener('resize', updateViewport);
window.addEventListener('resize', updateViewport);
updateViewport();
```

卸载页面时移除两个监听器。不要用一次性的“窗口高度减少即键盘弹出”判断驱动业务状态；分屏和旋转也会改变高度。

## 常见根因

- 根容器固定 `height: 100vh` 且 `overflow: hidden`。
- 固定底栏未计入安全区或键盘可视高度。
- 聚焦后立即执行自定义滚动，与浏览器自动滚动竞争。
- 页面级容器和嵌套组件重复消费同一组 safe area，导致 padding 叠加。
- 使用物理屏幕高度计算 Web 页面可用高度。

## 验证

- 顶部、底部和四方向特殊区域均不遮挡关键内容。
- 首屏、页面底部和弹窗中的输入框分别测试键盘弹出。
- 连续切换焦点、收起键盘、旋转和进入分屏，页面不累计偏移。
- 直板机无安全区时 padding 回退为 0。
