# 工具边界、静态规则与回归

## 与 devecocli 分工

把 HarmonyOS 通用工程能力交给 `devecocli`：

| 任务 | 命令 |
|---|---|
| 编译、ArkTS 语法与类型检查 | `devecocli build`；修改过的 HSP 另用 `devecocli build --modules <模块名...>`；逐文件检查使用 `devecocli serve mcp` 的 `check` |
| 安装与启动 | `devecocli run [--module <模块>] [--device <设备>]` |
| 设备与模拟器 | `devecocli device list`、`devecocli emulator list\|create\|start\|stop` |
| 日志与崩溃 | `devecocli log --level E`、`--crash --bundle-name <包名>` |
| 官方文档检索 | `devecocli docs search <关键词>` 查候选；`devecocli docs read <documentId>` 读全文 |
| 截图与设备操作 | `devecocli` 或设备控制工具 |

本 Skill 负责工程扫描、状态账本和全部验证动作，并内置少量确定性的 UI 静态检查。不要重复实现领域 Skill 已提供的根因与修法，也不要重复实现 ArkTS 语法、类型、命名、性能或通用质量检查。

文档检索由当前领域 Skill 判断是否需要，Workflow 只控制调用阶段。搜索摘要不是结论，不能代替工程源码、当前 SDK 编译或设备验证。

## 不做运行态自动布局判定

不要声称脚本能自动判断平板布局是否正确。布局、折痕、遮挡与视觉比例最终必须由人看目标形态截图。

以下场景不适合用通用几何规则自动下结论：

- `Navigation` 后台路由分支保留旧几何与 `visible=true`，导致溢出/重叠稳定误报。
- 弹窗与 Sheet 是独立窗口，跨窗口比较会把正常叠放判成重叠。
- `.translate()` 和 `Swiper` 相邻页位移会被误判为文本裁剪。
- dump 缺少 schema 校验时，一个字段缺失可让结果从 0 FAIL 变为 21 FAIL。

因此，本 Skill 不提供运行态自动布局判定；设备验证只采集运行事实和截图，视觉结论由具备图像能力的模型或用户确认。

## 静态检查脚本

施工后记录 L1 构建与适用的静态检查结果：

```bash
python3 $OM/scripts/verification/run-foundation.py . --prepare-first-round \
  --check-script $OM/scripts/verification/checks/ui/static-check.py
```

脚本从本批已修改 Issue 的 `changedFiles` 定位所属模块；若包含 HSP（`module.type=shared`），先按 `build-profile.json5` 中的模块名去重执行 `devecocli build --modules <模块名...>`，再执行默认构建。没有 HSP 修改时保持原行为；第 2–5 轮修复重测同样处理。任一构建失败均记录为 L1 失败，不以默认构建成功代替 HSP 编译成功。

涉及模块目标设备声明或装机失败时，可另行诊断；全工程声明检查不作为每批施工收尾的必过项：

```bash
python3 $OM/scripts/verification/checks/ui/check-device-types.py . \
  --target-form <目标形态> --json
```

`--check-script` 可重复提供；没有适用脚本时只执行构建。检查命令返回失败码时，保留结果并进入第四步分析、修复，不反复执行相同收尾命令。静态检查通过不代表运行或视觉正确。

## 回归

`evals/` 只存在于 Skill 源目录，不安装到工程。修改流程、扫描、验证或静态检查脚本后运行 workflow 自身契约测试；领域知识 Skill 在各自目录单独回归。

```bash
cd <skill源目录>
python3 evals/run_evals.py
```

回归覆盖多模块页面发现、路由、账本、验证、报告、frontmatter 和本地链接。

修改 `scripts/onemulti/` 后，把结果重新安装到目标工程的 `.onemulti/`：

```bash
python3 scripts/install-to-project.py <工程根>
```

`project-scan.py` 输出的 `pages` 仍需用真实多模块工程人工核对完整性。
