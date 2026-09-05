# Skill 评测

`evals/` 保存针对生产插件和 Skill 的版本化评测资产，但不属于任何插件安装包。目录镜像被测目标：

```text
evals/plugins/<plugin-name>/skills/<skill-name>/
├── eval.config.json
├── run.mjs
├── tests/
├── cases/       # 有声明式行为用例时创建
├── fixtures/    # 有最小输入工程或数据时创建
├── graders/     # 有独立评分逻辑时创建
└── expected/    # 只保存稳定、可审查的黄金结果
```

只创建实际需要的目录，不保留空目录。依赖方向固定为 `evals -> plugins`，生产 Skill 不得读取或调用
`evals/`。确定性断言优先于模型评分；涉及宿主安装行为的套件应从临时插件缓存运行，而不是依赖源码目录外的文件。

运行全部已注册评测：

```bash
npm run evals
```

生成的模型输出、截图、日志、HTML 报告和临时工程写入 `.eval-runs/`、`.eval-cache/` 或系统临时目录，
不进入版本控制。
