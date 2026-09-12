# Web 特性兼容与回退矩阵

不要把浏览器能力写成永久事实。先读取项目的 browserslist 或最低浏览器目标，再查 MDN、W3C/WHATWG 规范和目标浏览器官方资料；在结论中记录验证日期。

## 项目级矩阵模板

| 能力 | 可用基线 | 渐进增强 | 特性检测 | 不支持时回退 | 已验证环境 |
| --- | --- | --- | --- | --- | --- |
| 页面断点 | media query | range syntax | `matchMedia()` | 传统 `min-width/max-width` | 待填 |
| 组件响应 | Flex/Grid | container query | `CSS.supports('container-type: inline-size')` | viewport 断点或单栏 | 待填 |
| 动态高度 | `100vh` + 正常滚动 | `100dvh` | `CSS.supports('height: 100dvh')` | `min-height: 100vh` | 待填 |
| 安全区 | 常规 padding | `env(safe-area-inset-*)` | fallback 参数 | `0px` | 待填 |
| 组件尺寸监听 | CSS 自适应 | `ResizeObserver` | `'ResizeObserver' in window` | window resize 或静态基线 | 待填 |
| 键盘可视区 | 正常文档流 | `visualViewport` | `'visualViewport' in window` | `innerHeight` | 待填 |
| 响应式内容图 | `<img src>` | `srcset`、`sizes`、`<picture>` | DOM 属性存在 + 目标环境实测 | `src` 和可用构图 | 待填 |
| 响应式背景图 | 普通 `background-image` | `image-set()` + `type()` | `CSS.supports('background-image', 'image-set("a.png" 1x)')` | 单一背景资源 | 待填 |

## 规则

1. 优先使用 CSS fallback + `@supports`，不要先解析 UA。
2. 一个 `@supports` 只检测同一回退单元；不要让无关可选能力共同失败。
3. 新语法必须保留旧语法可解析的基线，声明顺序从基线到增强。
4. polyfill 只用于业务必须且无法优雅降级的能力；布局增强通常应直接回退。
5. 最低支持环境和当前环境都要验证；只在最新浏览器通过不等于适配完成。

## 证据优先级

1. 项目实际 browserslist/运行环境约束。
2. W3C、WHATWG 或 CSSWG 规范。
3. MDN compatibility data。
4. 目标浏览器官方 release note。
5. 真机或模拟环境最小复现。

博客、论坛和 UA 推断只能提供线索，不能单独支持兼容结论。
