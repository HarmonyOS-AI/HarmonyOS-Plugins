# 可执行路由表格式

`$OM/output/route-map.json` 是第一步生成、第四步消费的唯一可执行路由输入。模型必须按本文生成合法 JSON；不得用 Mermaid、Markdown 表格或自然语言路径替代。图形只可由该 JSON 派生用于人工查看，不参与测试。

## 生成方式

### 局部分析路径

用户明确指定单个页面、组件或文件，且分析其直接依赖后确认不需要继续发现其他页面时，不运行 `project-scan.py`。读取目标页、承载它的容器或注册表、直接入口、直接出口和公共依赖，由模型直接生成局部 `route-map.json`。该文件只覆盖本次目标对应页面的可达路径，不要求补齐工程内其他页面的路由链路。

```text
目标页面 → 入口容器与直接跳转 → 核实用户动作 → route-map.json
```

### 工程扫描路径

涉及多个页面、模块、公共能力或全工程，或者范围仍需发现时，无论最终生成几个批次，都执行扫描。是否运行扫描只由任务复杂度决定，不按最终批次数判断：

```bash
python3 $OM/scripts/project-scan.py . --json
```

`project-scan.py` 一次遍历并向 stdout 输出 `pages / nodes / edges / unresolved / orphanRoutes`，不生成第二个正式扫描文件。模型结合源码核实候选页面、Tabs、动态变量、ViewModel 调用归属、按钮动作和条件分支后，直接生成唯一的 `$OM/output/route-map.json`：

1. 静态可确定且已核实的节点和边写入 `routes[].steps`。
2. 同一目标存在多个入口或条件分支时拆成多个 `routeId`。
3. 无法核实的动态目标写入 `unresolved`，不得猜测或用坐标直达。
4. 最终 `routes` 覆盖全部批次，每条路径都能从应用入口顺序执行到 `targetPage`。

## 顶层结构

```json
{
  "schemaVersion": 1,
  "routes": [],
  "unresolved": []
}
```

- `schemaVersion`：固定为 `1`。
- `routes`：已核实、可顺序执行的路径数组，至少一项。
- `unresolved`：仍无法确定的动态路径；没有时写空数组，不得把猜测写进 `routes`。

## 路径结构

一个 `routeId` 只表示一条从应用入口到目标页面的线性路径。路径可包含任意数量的步骤；存在分支或多个入口时拆成多个 `routeId`。

```json
{
  "routeId": "R-B02-NEWS-DETAIL",
  "batchId": "B02",
  "targetPage": "feature/news/src/main/ets/pages/NewsDetail.ets",
  "steps": [
    {
      "stepId": "S01",
      "action": "launch",
      "target": "entry/EntryAbility",
      "expectPage": "Index"
    },
    {
      "stepId": "S02",
      "action": "tap",
      "locator": { "by": "text", "value": "首页" },
      "expectPage": "HomePage"
    },
    {
      "stepId": "S03",
      "action": "swipe",
      "direction": "up",
      "distance": "medium"
    },
    {
      "stepId": "S04",
      "action": "tap",
      "locator": { "by": "text", "value": "更多" },
      "expectPage": "NewsListPage"
    },
    {
      "stepId": "S05",
      "action": "tap",
      "locator": { "by": "text", "value": "南京交通新进展" },
      "expectPage": "NewsDetail"
    }
  ]
}
```

字段要求：

| 字段 | 要求 |
|---|---|
| `routeId` | 全文件唯一，推荐 `R-<batchId>-<语义名>` |
| `batchId` | 必须命中 `decisions.json.batches[].batchId` |
| `targetPage` | 工程相对源码路径，必须属于对应批次 |
| `steps` | 非空有序数组；数组顺序就是执行顺序 |
| `stepId` | 当前路径内唯一，使用 `S01`、`S02` 递增 |
| `action` | 仅使用 `launch / tap / swipe / input / back / wait` |
| `expectPage` | 页面跳转后填写，用于中途失败定位；不发生跳转时可省略 |

动作参数：

- `launch`：必须有 `target`。
- `tap`：必须有 `locator`；`locator.by` 仅使用 `text / id / type`，`value` 不得为空。
- `swipe`：必须有 `direction`，仅使用 `up / down / left / right`；`distance` 可用 `short / medium / long`。
- `input`：必须有 `locator` 和字符串 `value`。
- `back`：不需要额外参数，可填写 `expectPage`。
- `wait`：必须有正整数 `timeoutMs`，只用于等待确定的页面或状态就绪，不得替代断言。

## 与验证计划关联

路由表不保存 `checks`。第二步生成 SPEC 时，在每个 `verificationPlan` 项中引用已有 `routeId`：

```json
{
  "form": "unfolded",
  "checkId": "detail-two-column",
  "routeId": "R-B02-NEWS-DETAIL",
  "check": "展开态新闻详情位于左栏，相关推荐位于右栏，两栏同时可见且无截断"
}
```

职责固定为：

```text
route-map.json：routeId → 如何到达页面
decisions.json：issueId + form + checkId → 使用哪个 routeId、检查什么
evidence/index.json：实际步骤、证据和结果
```

同一路径可被多个验证项复用，但 `routeId` 的 `targetPage` 必须等于该 issue 的 `page`，或属于其
`affectedPages`；仅处于同一批次不算有效关联。没有页面导航需求的构建或静态检查不写入
`verificationPlan`，也不虚构 `routeId`。

## 未解析项

```json
{
  "source": "feature/news/src/main/ets/viewmodel/NewsVM.ets:86",
  "target": "动态变量 routeName",
  "reason": "无法静态确定目标页面"
}
```

`unresolved` 只记录事实，不参与自动执行。若某个已确认验证项只能依赖未解析路径，该项必须记为 `not_verified`，不得改用坐标直达或临时猜测路径。

## 生成与执行规则

1. `routes` 必须覆盖全部批次；每个 `targetPage`、`batchId` 和步骤都要来自工程事实。
2. 禁止保留 `TODO`、`TBD`、`待规划`或空定位器；无法确认的内容写入 `unresolved`。
3. 第四步按 `verificationPlan.routeId` 查找路径并逐步执行。每个带 `expectPage` 的步骤执行后先确认页面；任一步失败即停止该路径，并记录 `routeId + stepId + expected + actual`。
4. 测试只读取已通过校验且哈希已冻结的 `route-map.json`，不得在第四步重新生成、修改或搜索替代路由文件。
