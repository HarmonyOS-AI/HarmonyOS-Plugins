# 模块目标设备声明

`module.json5` 的字段名是 `module.deviceTypes`（复数）。它决定 HAP、HAR、HSP 能否参与对应设备上的构建、安装和运行；页面已经完成响应式改造，不代表包已经支持该设备。

## 映射

| 一多目标形态 | 可满足的 `deviceTypes` | 说明 |
|---|---|---|
| 直板手机、折叠屏的折叠态/展开态/悬停态 | `"phone"` 或 `"default"` | 按工程所用 SDK 和现有模块约定二选一，不写 `"foldable"` |
| 平板 | `"tablet"` | 只写 `"default"` 不能安装到平板 |

用户只提出“一多适配”而未限定设备时，默认目标是手机、折叠屏、平板三种设备，因此每个相关模块需要同时满足“`phone/default` 二选一”和“包含 `tablet`”。以下两种都可接受：

```json5
{
  "module": {
    "deviceTypes": ["default", "tablet"]
  }
}
```

或沿用使用 `phone` 的工程约定：

```json5
{
  "module": {
    "deviceTypes": ["phone", "tablet"]
  }
}
```

如果用户明确只要求手机或折叠屏，则 `deviceTypes` 具备 `"phone"` 或 `"default"` 任一项即可，不强制增加 `"tablet"`。如果只要求平板，则只校验 `"tablet"`。保留工程中与已确认范围不冲突的其他合法设备类型，不因本次适配删除，也不为了统一格式强制把 `phone` 迁移成 `default`。

## 检查与修改

1. 枚举工程内每个 HAP、HAR、HSP 的 `src/main/module.json5`，不能只检查入口 HAP。
2. 根据用户明确的目标形态对照上表；未限定设备时默认检查手机、折叠屏和平板，用户已缩小范围时不追加设备。
3. 已有 `deviceTypes` 时做集合补充并保留其他合法值；缺失时新增字段。
4. 修改后执行 `devecocli build`，确认声明可编译；构建成功不能替代目标设备安装验证。

完整验证还应检查 `deviceTypes` 缺失、空数组、`foldable` 误写，以及当前任务是否满足 `phone/default` 二选一和 `tablet` 能力；这些检查不属于本知识 Skill 的编译验证范围。
