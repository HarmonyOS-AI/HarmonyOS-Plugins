# 页面清单生成（大工程适配用）

给 AI 的引导文档，不是脚本。页面发现已经合入确定性脚本 `scripts/project-scan.py`，
复杂或非单点任务只运行一次即可，不需要额外页面扫描——`@Entry` 装饰器与 `module.json5`/`main_pages.json` 的注册
关系是 HarmonyOS 平台固定的**文件格式**；`NavDestination(` 内容匹配虽然不是文件格式
（没有"注册表"可比对），但发现方式本身也是确定性的字符串/正则匹配，同样不需要引导。
本文档只覆盖脚本**做不了**的部分——因工程而异，必须结合当前工程实际情况判断：

1. 脚本没查到注册信息的候选页面，到底是死代码还是动态路由目标页
2. 工程如果完全不走 `main_pages.json`/`@Entry`/`NavDestination` 常规套路，怎么补一份扫描
3. 每个候选页面属于哪种页面类型

**拿不准就标 `unknown`，不要猜**——这是本 skill 一贯的纪律（见 `SKILL.md` 「这个
skill 不做什么」）：分类误判和运行态误报是同一类问题，都会让开发者不再信任输出。

## 第一步：跑确定性脚本

```bash
python3 $OM/scripts/project-scan.py <工程根> --json
```

读取输出中的 `pages`；每个候选页面包含 `path` / `component` / `kind` / `module` / `registeredRoute` /
`confidence`。**先看 `kind`，再看 `confidence`**——两种发现信号的可信度不是一回事：

| kind | 发现方式 | confidence 取值 |
|---|---|---|
| `entry` | `@Entry` 装饰器，HarmonyOS 静态注册的页面 | `registered` / `entry-unregistered` / `no-registry-found`（文件格式匹配，确定性高） |
| `nav-destination` | 内容里出现 `NavDestination(`，Navigation 动态路由目标页 | 固定 `heuristic`（内容特征匹配，**永远需要核实**） |

**`nav-destination` 通常是大头，不是补充项。** 实测华为官方 demo 工程
（`NewsTemplate/ComprehensiveNews`）：`@Entry` 页面 6 个，`NavDestination` 页面 62 个——
只看 `entry` 会漏掉九成以上的真实页面。拿到清单先看 `kind` 分布，`nav-destination`
占大头是正常现象，不是脚本出错。

`entry` kind 的三档 confidence：

| confidence | 含义 | 下一步 |
|---|---|---|
| `registered` | 命中了所属模块 `main_pages.json` 里的路由 | 直接收进清单，跳到类型分类 |
| `entry-unregistered` | 有 `@Entry` 但在**已解析出的**注册表里找不到对应路由 | 见下节「核实候选页面」 |
| `no-registry-found` | 该页面所属模块解析不出注册表（缺 `pages` 字段、profile 引用失效，或模块本身是 HAR 库，本来就没有页面路由） | 见下节「核实候选页面」；HAR 库模块里的 `@Entry` 常见于组件预览（文件名带 `Sample`/`Preview` 是强信号），不一定是真实业务页面 |

## 核实候选页面（`heuristic`/`entry-unregistered`/`no-registry-found` 怎么处理）

这三类的共同点是：脚本给出的是"候选"而不是"确认"，需要人/AI 进一步核实。

**`nav-destination`（`heuristic`）**：`NavDestination(` 子串命中 + 就近 struct 名关联，
不做括号配对定界，可能把归属算错（比如一个文件里有多个 struct）但基本不会漏页。
核实方法（在工程里搜，不是猜）：

1. 该组件名是否作为字符串出现在某处 `.pushPath(`、`.pushDestination(` 调用里，
   或出现在 `module.json5` 的 `routerMap` 字段指向的 JSON 里（HarmonyOS 5 起支持
   用 `routerMap` 配置代替硬编码 `.navDestination()` 分支）。命中 → 是一个真实可达
   的动态路由页面，正常纳入清单。
2. 搜不到任何引用 → 可能是被其它组件内部复用的弹窗/子视图（不是独立页面），也可能
   是废弃代码，在清单里标注「未找到路由引用，建议向人确认是否为独立页面」，不要
   擅自归类，也不要擅自剔除。

**`entry-unregistered`**：多数是死代码或半成品页面（`@Entry` 页面本身极少会同时又
是动态路由目标页）。搜不到任何 `.pushPath`/`routerMap` 引用 → 标注「未找到任何路由
引用，建议向人确认是否废弃」。

**`no-registry-found`**：先确认这不是误报——检查该模块 `module.json5` 是否真的没有
`pages` 字段（用 `--json` 输出核对 `module` 字段是否为空，为空说明连模块本身都没
匹配上，先看目录结构是不是不符合 `xxx/src/main/` 惯例）。确认后按下节处理。

## 非常规路由工程（整个模块/工程都查不到常规信号时）

工程完全不用官方 `main_pages.json`/`NavDestination`（比如自研路由表、纯配置驱动的
页面注册）时，这两种发现信号都会落空。这时候：

1. 先确认这不是误报——检查该模块 `module.json5` 是否真的没有 `pages` 字段
   （用 `$OM/scripts/project-scan.py` 的 `--json` 输出核对 `pages[].module` 是否为空，
   为空说明连模块本身都没匹配上，先看目录结构是不是不符合 `xxx/src/main/` 惯例）。
2. 确认是自研路由后，找出该工程实际的路由注册方式（搜 `router.pushUrl`、自定义路由
   表文件名、路由注册的 TS/ArkTS 常量/装饰器等），**现写一次性补充脚本**，别泛化成
   通用规则——这正是本 skill 静态规则准入门槛反复强调的教训：写死的判据一旦离开
   它诞生时看的那个工程就大概率误判。

   补充脚本要求：
   - 复用 `onemulti/project.py` 现成的 `iter_files`/`SKIP_DIRS` 做目录遍历，
     不要重新发明"哪些目录不该扫"这份清单。
   - 落盘到 `.onemulti/page-scan-extra.py`（工程数据区，不在 `scripts/` 下，
     重装 skill 不会被清掉，可重复运行）。
   - 产出格式尽量对齐 `project-scan.py` 的 `pages` 字段（`path`/`component`/`kind`/`module`/
     `confidence`），方便后续合并逻辑不用为这一种工程再写一套。

3. 如果该工程的路由约定过于特殊、无法用脚本可靠识别（比如完全动态生成、运行时
   反射注册），如实在报告里写清楚"页面清单不完整，以下模块无法自动枚举"，
   把范围收窄到能确认的部分，不要为了凑出一份"完整清单"而编造页面。

## 页面类型分类

词汇对齐 `$OM/references/layout-strategies.md` 现有分类，不新造体系：
`list-page` / `detail-page` / `form-page` / `home-nav` / `media-page` / `other` / `unknown`。

启发式信号（按优先级）：

1. **目录名/文件名**：`*List`/`*Home`（列表页）、`*Detail`/`*Info`（详情页）、
   `*Form`/`*Edit`/`*Create`（表单页）、`*Player`/`*Preview`（媒体页）。
   命名规范的工程这一条基本够用。
2. **主导组件**（读 `build()` 里出现频率最高、承担主体内容的组件）：
   `List`/`Grid`/`WaterFlow` 为主 → 列表页；`TextInput`/`TextArea`/`Select` 密集
   → 表单页；`Video` 为主 → 媒体页；根节点是
   `Tabs`/`SideBarContainer`/`Navigation` 且承载多个子路由 → 首页导航容器。
3. 两条都判不清楚 → `unknown`，进人工核实清单，**不要为了不留空白硬塞一个类型**。

## 合并进决策账本

分类结果连同 `project-scan.py` 输出中的 `pages` 一起写入 `$OM/decisions.json` 的 `pages`。
`pages` 是以页面路径为 key 的对象，每项记录 `type`、`module`、公共依赖、所属批次、源码摘要和扫描缺失标记。页面执行进度由关联 Issue 计算，不在这里重复保存。**与已有条目做 diff，不要整体覆盖**：

- 新出现的页面（新增文件）→ 追加，并设置 `missingFromScan=false`
- 清单里消失的页面（文件被删/重命名，无法反向匹配）→ 不要直接从账本删掉，
  设置 `missingFromScan=true` 和 `missingReason="待确认：页面已从全量扫描消失"`，交给人核实
- 已有条目 → 更新扫描字段；之前已有具体类型而本次无法判断时，不用 `unknown` 覆盖。
  源码摘要未变化则保留既有验证结论；摘要变化时，将该页相关问题的旧验证证据标记过期。

汇总结果按类型分组播报给用户（"工程有 N 个列表页 / M 个详情页 / K 个待核实"），
这是生成批次和选择代表页的依据；结构决策按页面类型复用，不按页面数量重复询问。
