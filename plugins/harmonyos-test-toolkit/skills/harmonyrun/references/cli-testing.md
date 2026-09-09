# 运行测试

## 单个目标

在目标项目目录运行，替换目标应用与设备序列号：

```bash
harmonyrun run "打开目标应用，进入设置页，验证关于入口可见" \
  -d SERIAL --steps 20 --save-trajectory step
```

复杂流程可加 `--reasoning`；参数详情用 `harmonyrun run --help` 查看。

## 测试套件

复制 [套件示例](../assets/smoke-suite.json)，按真实应用改写包名、前置条件、步骤和预期结果。
用例描述用户可观察的目标，不写死屏幕坐标或临时元素索引。

- 用例 ID 保持唯一，`level` 从 L0（最高优先级）到 L5。
- `test_steps` 可写字符串、字符串数组，或 `action/checkpoint` 对象数组；同一数组不混用形式。
- 折叠屏专用例使用 `requires.foldable=true`；设备不支持时跳过。
- 固定显示姿态用 `config_overrides` 中的 `orientation` / `fold_display`，执行后仍需核验实际姿态。
- 新增字段前，用安装包 `harmonyrun.batch/schemas/test_suite.schema.json` 校验支持的格式。

```bash
harmonyrun test ./suite.json -d SERIAL --case home-smoke
harmonyrun test ./suite.json -d SERIAL --level L1
harmonyrun test ./suite.json -d SERIAL --save-trajectory step
```

`--level L1` 包括 L0 和 L1。重复 `-d` 会把用例分配到设备池；若要求每台设备完整覆盖，
应逐台指定设备执行整套测试。

## 查看结果

```bash
harmonyrun view /absolute/path/to/本次运行目录
```

使用命令打印的本次运行目录，结合套件 `report.json`、失败原因和截图核对结果。
检查实际执行数量与跳过项，避免把未匹配用例的运行视为全部通过。

## 生成 Hypium 回归

从含 `report.json` 的成功套件运行目录生成；回放需要在同一 Python 环境安装 Hypium：

```bash
python -m pip install hypium
harmonyrun hypium generate /absolute/path/to/suite-run -o ./hypium-project
harmonyrun hypium run ./hypium-project -d SERIAL
```

检查生成的选择器和断言，以回放报告确认结果。

## 使用已有远程设备

用户提供远程设备服务后，通过环境变量 `HARMONYRUN_FARM_URL`、`HARMONYRUN_FARM_TOKEN`
配置连接，再运行：

```bash
harmonyrun farm devices
harmonyrun farm run "打开目标应用，验证首页显示正常" --device SERIAL
```
