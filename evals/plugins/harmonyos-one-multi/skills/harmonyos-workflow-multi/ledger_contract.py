"""task-ledger.py 的 schema v3 端到端合同测试。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _route_map() -> dict:
    return {
        "schemaVersion": 1,
        "routes": [{
            "routeId": "R-B01-INDEX",
            "batchId": "B01",
            "targetPage": "entry/src/main/ets/pages/Index.ets",
            "steps": [{
                "stepId": "S01", "action": "launch",
                "target": "entry/EntryAbility", "expectPage": "Index",
            }],
        }],
        "unresolved": [],
    }


def run(skill_root: Path) -> tuple[bool, str]:
    script = skill_root / "scripts" / "task-ledger.py"
    with tempfile.TemporaryDirectory(prefix="onemulti-ledger-eval-") as temporary:
        root = Path(temporary)
        ledger = root / "decisions.json"

        def command(*arguments: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
            result = subprocess.run(
                [sys.executable, str(script), *arguments],
                text=True,
                capture_output=True,
                check=False,
            )
            if result.returncode != expect:
                raise AssertionError(
                    f"{' '.join(arguments)} 退出 {result.returncode}，期望 {expect}: "
                    f"{result.stdout}{result.stderr}"
                )
            return result

        try:
            help_text = command("--help").stdout
            assert "add-evidence" not in help_text, "账本 CLI 不应提供内嵌 evidence 命令"
            assert "bootstrap" in help_text
            for name in (
                "bootstrap", "init", "set-task", "put-decision", "merge-pages",
                "put-batch", "transition-batch", "put-issues", "transition-issue",
                "add-deferred-regression", "put-verification",
            ):
                assert "可复制 JSON 示例" in command(name, "--help").stdout, f"{name} 缺少 JSON 示例"

            # 未限定设备的一多任务必须落成手机、折叠屏、平板三种默认目标。
            default_ledger = root / "default-targets.json"
            default_task = root / "default-targets-input.json"
            _write(default_task, {"taskId": "ui-default-targets", "scope": []})
            command("init", str(default_ledger), "--input", str(default_task))
            default_data = json.loads(default_ledger.read_text(encoding="utf-8"))
            assert default_data["task"]["targetForms"] == ["phone", "foldable", "tablet"]

            # 推荐 bootstrap 必须在单次写入中建立全部计划关联。
            bootstrap_root = root / "bootstrap"
            bootstrap_root.mkdir()
            bootstrap_ledger = bootstrap_root / "decisions.json"
            _write(bootstrap_ledger, {
                "schemaVersion": 3, "task": None, "decisions": [], "pages": {},
                "batches": [], "issues": [],
            })
            bootstrap_output = bootstrap_root / "output"
            bootstrap_output.mkdir()
            bootstrap_route = bootstrap_output / "route-map.json"
            _write(bootstrap_route, _route_map())
            bootstrap_input = bootstrap_root / "bootstrap.json"
            _write(bootstrap_input, {
                "task": {
                    "taskId": "ui-bootstrap-001",
                    "scope": ["entry/src/main/ets/pages/Index.ets"],
                    "targetForms": ["phone-portrait"],
                    "confirmationMode": "batch",
                    "currentBatch": "B01",
                },
                "decisions": [{
                    "decisionId": "D-BOOT", "scope": [], "summary": "确认初始化范围",
                    "by": "user", "reason": "用户明确指定", "conflictsWith": [],
                }],
                "pages": [{
                    "path": "entry/src/main/ets/pages/Index.ets", "type": "page",
                    "module": "entry", "dependencies": [],
                }],
                "batches": [{
                    "batchId": "B01", "pages": ["entry/src/main/ets/pages/Index.ets"],
                    "dependencies": [], "predecessors": [], "domains": ["size-layout"],
                    "risk": "low",
                }],
            })
            command(
                "bootstrap", str(bootstrap_ledger), "--input", str(bootstrap_input),
                "--route-map", str(bootstrap_route),
            )
            bootstrapped = json.loads(bootstrap_ledger.read_text(encoding="utf-8"))
            assert bootstrapped["task"]["currentBatch"] == "B01"
            assert "testConclusion" not in bootstrapped["task"]
            assert bootstrapped["pages"]["entry/src/main/ets/pages/Index.ets"]["batchId"] == "B01"
            assert json.loads(
                (bootstrap_root / "evidence" / "index.json").read_text(encoding="utf-8")
            )["taskId"] == "ui-bootstrap-001"
            before_bootstrap_ledger = _digest(bootstrap_ledger)
            before_bootstrap_evidence = _digest(bootstrap_root / "evidence" / "index.json")
            invalid_bootstrap = json.loads(bootstrap_input.read_text(encoding="utf-8"))
            invalid_bootstrap["task"]["currentBatch"] = "B99"
            _write(bootstrap_input, invalid_bootstrap)
            command(
                "bootstrap", str(bootstrap_ledger), "--input", str(bootstrap_input),
                "--route-map", str(bootstrap_route), expect=1,
            )
            assert _digest(bootstrap_ledger) == before_bootstrap_ledger
            assert _digest(bootstrap_root / "evidence" / "index.json") == before_bootstrap_evidence

            # 安装器创建的 schema v3 空账本必须可校验并可由 init 接管。
            _write(ledger, {
                "schemaVersion": 3,
                "task": None,
                "decisions": [],
                "pages": {},
                "batches": [],
                "issues": [],
            })
            command("validate", str(ledger))

            task = root / "task.json"
            _write(task, {
                "taskId": "ui-eval-001",
                "scope": ["entry/src/main/ets/pages/Index.ets"],
                "targetForms": ["phone-portrait", "foldable-expanded"],
                "confirmationMode": "batch",
            })
            command("init", str(ledger), "--input", str(task))
            evidence_index = root / "evidence" / "index.json"
            index_data = json.loads(evidence_index.read_text(encoding="utf-8"))
            assert index_data == {"schemaVersion": 3, "taskId": "ui-eval-001", "entries": []}

            decision = root / "decision.json"
            _write(decision, {
                "decisionId": "D-001",
                "scope": ["entry/src/main/ets/pages/Index.ets"],
                "summary": "展开态采用双列",
                "by": "user",
                "reason": "用户确认 B01 结构方案",
            })
            command("put-decision", str(ledger), "--input", str(decision))

            before_invalid = _digest(ledger)
            invalid_decision = root / "invalid-decision.json"
            _write(invalid_decision, {
                "decisionId": "D-002",
                "summary": "模型自行扩大范围",
                "by": "agent",
                "reason": "错误示例",
            })
            command("put-decision", str(ledger), "--input", str(invalid_decision), expect=1)
            assert _digest(ledger) == before_invalid, "非法决策改变了原账本"

            pages = root / "pages.json"
            _write(pages, {"pages": [{
                "path": "entry/src/main/ets/pages/Index.ets",
                "component": "Index",
                "kind": "entry",
                "module": "entry",
                "confidence": "registered",
            }, {
                "path": "entry/src/main/ets/components/ResponsivePanel.ets",
                "type": "component",
                "module": "entry",
                "dependencies": [],
            }]})
            command("merge-pages", str(ledger), "--input", str(pages), "--full-scan")

            batch = root / "batch.json"
            _write(batch, {
                "batchId": "B01",
                "pages": ["entry/src/main/ets/pages/Index.ets"],
                "dependencies": [],
                "risk": "low",
            })
            before_route_gate = _digest(ledger)
            command("put-batch", str(ledger), "--input", str(batch), expect=2)
            assert _digest(ledger) == before_route_gate, "缺少 route-map 时仍写入了批次"

            output = root / "output"
            output.mkdir()
            route_map = output / "route-map.json"
            route_map.write_text("# 无效的 Markdown 路由图\n", encoding="utf-8")
            command(
                "put-batch", str(ledger), "--input", str(batch),
                "--route-map", str(route_map), expect=1,
            )
            assert _digest(ledger) == before_route_gate, "旧 Markdown 路由表仍通过校验"
            _write(route_map, _route_map())
            command(
                "put-batch", str(ledger), "--input", str(batch),
                "--route-map", str(route_map),
            )
            assert json.loads(ledger.read_text(encoding="utf-8"))["task"]["status"] == "planning"

            task_running = root / "task-running.json"
            _write(task_running, {"currentBatch": "B01"})
            command("set-task", str(ledger), "--input", str(task_running))

            issues = root / "issues.json"
            _write(issues, {"issues": [{
                "issueId": "B01-UI-001",
                "batchId": "B01",
                "page": "entry/src/main/ets/pages/Index.ets",
                "targetForms": ["phone-portrait", "foldable-expanded"],
                "problem": "展开态仍为手机单列",
                "source": "task_analysis",
                "rootCause": "未使用断点分栏",
                "proposal": "md+ 使用双列",
                "plannedFiles": [
                    "entry/src/main/ets/pages/Index.ets",
                    "entry/src/main/ets/components/ResponsivePanel.ets",
                ],
                "verificationPlan": [
                    {
                        "form": "phone-portrait",
                        "checkId": "phone-baseline",
                        "routeId": "R-B01-INDEX",
                        "check": "折叠态下原手机布局和业务路径可用",
                    },
                    {
                        "form": "foldable-expanded",
                        "checkId": "layout-two-column",
                        "routeId": "R-B01-INDEX",
                        "check": "展开态显示双列",
                    },
                ],
            }]})
            invalid_issues = json.loads(issues.read_text(encoding="utf-8"))
            invalid_issues["issues"][0]["verificationPlan"][0]["routeId"] = "R-MISSING"
            invalid_issue_path = root / "invalid-issues.json"
            _write(invalid_issue_path, invalid_issues)
            before_invalid_route_ref = _digest(ledger)
            command(
                "put-issues", str(ledger), "--batch-id", "B01",
                "--input", str(invalid_issue_path), expect=1,
            )
            assert _digest(ledger) == before_invalid_route_ref, "无效 routeId 污染了账本"
            command("put-issues", str(ledger), "--batch-id", "B01", "--input", str(issues))
            # 账本写入成功后，位于 evidence/tmp 或旧 output 位置的输入文件必须清理。
            transient_dir = root / "evidence" / "tmp"
            transient_dir.mkdir(parents=True, exist_ok=True)
            transient_issue = transient_dir / "issues.json"
            _write(transient_issue, json.loads(issues.read_text(encoding="utf-8")))
            command(
                "put-issues", str(ledger), "--batch-id", "B01",
                "--input", str(transient_issue),
            )
            assert not transient_issue.exists(), "issues 临时输入未在成功写入后清理"
            duplicate_output = output / "issues-b01.json"
            _write(duplicate_output, json.loads(issues.read_text(encoding="utf-8")))
            duplicate_check = command("validate", str(ledger), expect=1)
            assert "唯一事实源" in duplicate_check.stderr
            duplicate_output.unlink()

            # 单批被停止也表示任务流程已经收口；失败结论仍保留在批次中。
            stopped_ledger = root / "stopped-decisions.json"
            stopped_ledger.write_bytes(ledger.read_bytes())
            stopped_patch = root / "stopped-batch.json"
            _write(stopped_patch, {"status": "stopped", "testConclusion": "failed"})
            command(
                "transition-batch", str(stopped_ledger), "B01",
                "--input", str(stopped_patch),
            )
            stopped_data = json.loads(stopped_ledger.read_text(encoding="utf-8"))
            assert stopped_data["task"]["status"] == "completed"
            assert stopped_data["batches"][0]["testConclusion"] == "failed"

            # 明确不施工的问题直接派生为 not_applicable，不要求制造验证结果。
            not_modified_ledger = root / "not-modified-decisions.json"
            not_modified_data = json.loads(ledger.read_text(encoding="utf-8"))
            not_modified_data["batches"][0].update({"status": "executing", "specConfirmed": True})
            not_modified_data["task"]["status"] = "executing"
            not_modified_data["issues"][0].update({
                "changeStatus": "not_modified", "notChangedReason": "现有实现已满足目标",
            })
            _write(not_modified_ledger, not_modified_data)
            command("validate", str(not_modified_ledger))
            not_modified_done = root / "not-modified-done.json"
            _write(not_modified_done, {"status": "completed", "testConclusion": "passed"})
            command(
                "transition-batch", str(not_modified_ledger), "B01",
                "--input", str(not_modified_done),
            )

            changed = root / "changed.json"
            _write(changed, {
                "changeStatus": "modified",
                "changedFiles": [
                    "entry/src/main/ets/pages/Index.ets",
                    "entry/src/main/ets/components/ResponsivePanel.ets",
                ],
                "changeSummary": "展开态增加双列",
            })
            executing = root / "batch-executing.json"
            _write(executing, {"specConfirmed": True, "status": "executing"})
            command("transition-batch", str(ledger), "B01", "--input", str(executing))
            assert json.loads(ledger.read_text(encoding="utf-8"))["task"]["status"] == "executing"
            command("transition-issue", str(ledger), "B01-UI-001", "--input", str(changed))

            # 账本写入不再根据批次状态拦截，施工中允许追加新发现的问题。
            runtime_issue = root / "runtime-issue.json"
            _write(runtime_issue, {
                "issueId": "B01-UI-002",
                "batchId": "B01",
                "page": "entry/src/main/ets/pages/Index.ets",
                "targetForms": ["foldable-expanded"],
                "problem": "施工时发现标题间距异常",
                "source": "execution_found",
                "rootCause": "公共布局调整影响标题间距",
                "proposal": "沿用现有间距，不追加修改",
                "plannedFiles": ["entry/src/main/ets/pages/Index.ets"],
                "verificationPlan": [{
                    "form": "foldable-expanded",
                    "checkId": "runtime-title-spacing",
                    "routeId": "R-B01-INDEX",
                    "check": "展开态标题间距保持现有基线",
                }],
            })
            command(
                "put-issues", str(ledger), "--batch-id", "B01",
                "--input", str(runtime_issue),
            )
            runtime_not_modified = root / "runtime-not-modified.json"
            _write(runtime_not_modified, {
                "changeStatus": "not_modified",
                "notChangedReason": "现有间距符合目标，不需要修改",
            })
            command(
                "transition-issue", str(ledger), "B01-UI-002",
                "--input", str(runtime_not_modified),
            )
            skipped_result = root / "skipped-result.json"
            _write(skipped_result, {
                "form": "foldable-expanded",
                "checkId": "runtime-title-spacing",
                "status": "not_applicable",
                "reason": "not_modified",
            })
            command(
                "put-verification", str(ledger), "B01-UI-002",
                "--input", str(skipped_result), expect=1,
            )

            phone_result = root / "phone-result.json"
            _write(phone_result, {
                "form": "phone-portrait",
                "checkId": "phone-baseline",
                "status": "passed",
                "reason": None,
            })
            command("put-verification", str(ledger), "B01-UI-001", "--input", str(phone_result))

            expanded_result = root / "expanded-result.json"
            _write(expanded_result, {
                "form": "foldable-expanded",
                "checkId": "layout-two-column",
                "status": "passed",
                "reason": None,
            })
            command("put-verification", str(ledger), "B01-UI-001", "--input", str(expanded_result))
            command("validate", str(ledger))

            data = json.loads(ledger.read_text(encoding="utf-8"))
            assert data["schemaVersion"] == 3
            assert "evidence" not in data
            assert "testConclusion" not in data["task"]
            assert data["task"]["routeMap"] == "output/route-map.json"
            assert "specStatus" not in data["issues"][0]
            assert "verifyStatus" not in data["issues"][0]
            related_component = data["pages"]["entry/src/main/ets/components/ResponsivePanel.ets"]
            assert related_component["batchId"] == "B01"
            assert set(data["issues"][0]["verificationResults"][0]) == {
                "form", "checkId", "status", "reason"
            }

            batch_done = root / "batch-done.json"
            _write(batch_done, {"status": "completed", "testConclusion": "passed"})
            command("transition-batch", str(ledger), "B01", "--input", str(batch_done))
            assert json.loads(ledger.read_text(encoding="utf-8"))["task"]["status"] == "completed"
            command("validate", str(ledger))

            before_manual_task_status = _digest(ledger)
            manual_task_status = root / "manual-task-status.json"
            _write(manual_task_status, {"status": "planning"})
            command("set-task", str(ledger), "--input", str(manual_task_status), expect=1)
            assert _digest(ledger) == before_manual_task_status

            before_removed_task_field = _digest(ledger)
            removed_task_field = root / "removed-task-field.json"
            _write(removed_task_field, {"testConclusion": "passed"})
            command("set-task", str(ledger), "--input", str(removed_task_field), expect=1)
            assert _digest(ledger) == before_removed_task_field

            # 证据字段不能混入精简结果，失败写入不能污染有效账本。
            before_illegal_result = _digest(ledger)
            illegal_result = root / "illegal-result.json"
            _write(illegal_result, {
                "form": "foldable-expanded",
                "checkId": "layout-two-column",
                "status": "passed",
                "reason": None,
                "evidence": ["E-001"],
            })
            command("put-verification", str(ledger), "B01-UI-001", "--input", str(illegal_result), expect=1)
            assert _digest(ledger) == before_illegal_result

            evidence_dir = root / "evidence"
            old_artifact = evidence_dir / "B01" / "round-1" / "old.png"
            old_artifact.parent.mkdir(parents=True)
            old_artifact.write_bytes(b"old evidence")
            history = root / "history"
            next_task = root / "next-task.json"
            _write(next_task, {
                "taskId": "ui-eval-002", "scope": [], "targetForms": ["tablet"],
                "confirmationMode": "batch",
            })
            command(
                "init", str(ledger), "--input", str(next_task), "--archive-existing",
                "--history-root", str(history),
            )
            assert (history / "ui-eval-001" / "decisions.json").is_file()
            assert (history / "ui-eval-001" / "evidence" / "index.json").is_file()
            assert (history / "ui-eval-001" / "evidence" / "B01" / "round-1" / "old.png").is_file()
            assert {path.name for path in evidence_dir.iterdir()} == {"index.json"}
            assert json.loads((evidence_dir / "index.json").read_text(encoding="utf-8")) == {
                "schemaVersion": 3, "taskId": "ui-eval-002", "entries": [],
            }

            # 验证状态必须按 currentBatch 隔离，并允许上一批终态后启动下一批。
            multi = root / "multi-batch"
            multi.mkdir()
            om = multi / ".onemulti"
            (om / "output").mkdir(parents=True)
            (om / "references").mkdir()
            (om / "references" / "verification.md").write_text(
                (skill_root / "references" / "verification.md").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            multi_ledger = om / "decisions.json"
            _write(multi_ledger, {
                "schemaVersion": 3, "task": None, "decisions": [], "pages": {},
                "batches": [], "issues": [],
            })
            pages_by_batch = {
                "B01": "entry/src/main/ets/pages/Home.ets",
                "B02": "entry/src/main/ets/pages/Detail.ets",
            }
            multi_route = {
                "schemaVersion": 1,
                "routes": [
                    {
                        "routeId": f"R-{batch}", "batchId": batch, "targetPage": page,
                        "steps": [{
                            "stepId": "S01", "action": "launch",
                            "target": "entry/EntryAbility", "expectPage": page,
                        }],
                    }
                    for batch, page in pages_by_batch.items()
                ],
                "unresolved": [],
            }
            multi_route_path = om / "output" / "route-map.json"
            _write(multi_route_path, multi_route)
            multi_bootstrap = multi / "bootstrap.json"
            _write(multi_bootstrap, {
                "task": {
                    "taskId": "ui-multi-batch", "scope": list(pages_by_batch.values()),
                    "targetForms": ["foldable-expanded"], "confirmationMode": "aggregate",
                    "currentBatch": "B01",
                },
                "pages": [
                    {"path": page, "type": "page", "module": "entry", "dependencies": []}
                    for page in pages_by_batch.values()
                ],
                "batches": [
                    {"batchId": batch, "pages": [page], "dependencies": [], "risk": "low"}
                    for batch, page in pages_by_batch.items()
                ],
            })
            command(
                "bootstrap", str(multi_ledger), "--input", str(multi_bootstrap),
                "--route-map", str(multi_route_path),
            )
            multi_task = multi / "task.json"
            _write(multi_task, {"currentBatch": "B01"})
            command("set-task", str(multi_ledger), "--input", str(multi_task))

            for batch, page in pages_by_batch.items():
                issue_id = f"{batch}-UI-001"
                issue_file = multi / f"{batch}-issue.json"
                _write(issue_file, {
                    "issueId": issue_id, "batchId": batch, "page": page,
                    "targetForms": ["foldable-expanded"], "problem": "布局未适配",
                    "source": "task_analysis", "rootCause": "缺少响应式布局",
                    "proposal": "按断点调整布局", "plannedFiles": [page],
                    "verificationPlan": [{
                        "form": "foldable-expanded", "checkId": "layout",
                        "routeId": f"R-{batch}", "check": "展开态布局正确",
                    }],
                })
                command(
                    "put-issues", str(multi_ledger), "--batch-id", batch,
                    "--input", str(issue_file),
                )
                confirm_file = multi / f"{batch}-confirm.json"
                _write(confirm_file, {"specConfirmed": True})
                command("transition-batch", str(multi_ledger), batch, "--input", str(confirm_file))

            def begin_multi_batch(batch: str) -> None:
                page = pages_by_batch[batch]
                execute_file = multi / f"{batch}-execute.json"
                _write(execute_file, {"status": "executing"})
                command("transition-batch", str(multi_ledger), batch, "--input", str(execute_file))
                modified_file = multi / f"{batch}-modified.json"
                _write(modified_file, {
                    "changeStatus": "modified", "changedFiles": [page],
                    "changeSummary": "补充响应式布局",
                })
                command(
                    "transition-issue", str(multi_ledger), f"{batch}-UI-001",
                    "--input", str(modified_file),
                )

            begin_multi_batch("B01")

            deferred_file = multi / "deferred-regression.json"
            _write(deferred_file, {
                "page": pages_by_batch["B02"],
                "batchId": "B02",
                "reason": "B02 页面复用本批修改的公共组件",
                "suggestedCheck": "检查展开态布局和核心交互",
            })
            command(
                "add-deferred-regression", str(multi_ledger), "B01-UI-001",
                "--input", str(deferred_file),
            )
            # 同一页面幂等更新，账本只保留一条记录。
            updated_deferred = json.loads(deferred_file.read_text(encoding="utf-8"))
            updated_deferred["suggestedCheck"] = "检查展开态布局、点击和返回路径"
            _write(deferred_file, updated_deferred)
            command(
                "add-deferred-regression", str(multi_ledger), "B01-UI-001",
                "--input", str(deferred_file),
            )
            deferred_data = json.loads(multi_ledger.read_text(encoding="utf-8"))
            stored_deferred = deferred_data["issues"][0]["deferredRegressions"]
            assert len(stored_deferred) == 1
            assert stored_deferred[0]["suggestedCheck"] == updated_deferred["suggestedCheck"]

            invalid_deferred = multi / "invalid-deferred-regression.json"
            _write(invalid_deferred, {
                "page": pages_by_batch["B01"],
                "batchId": "B01",
                "reason": "错误地记录当前批次页面",
                "suggestedCheck": "检查布局",
            })
            before_invalid_deferred = _digest(multi_ledger)
            command(
                "add-deferred-regression", str(multi_ledger), "B01-UI-001",
                "--input", str(invalid_deferred), expect=1,
            )
            assert _digest(multi_ledger) == before_invalid_deferred

            preflight = skill_root / "scripts" / "verification" / "preflight.py"
            evidence = skill_root / "scripts" / "verification" / "evidence-session.py"
            foundation = skill_root / "scripts" / "verification" / "run-foundation.py"
            validate_state = skill_root / "scripts" / "validate-state.py"

            def verify_command(script_path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
                result = subprocess.run(
                    [sys.executable, str(script_path), *arguments],
                    text=True, capture_output=True, check=False,
                )
                if result.returncode:
                    raise AssertionError(
                        f"{script_path.name} {' '.join(arguments)} 失败: {result.stdout}{result.stderr}"
                    )
                return result

            probe_image = om / "assets" / "verification" / "startIcon.png"
            probe_image.parent.mkdir(parents=True)
            probe_image.write_bytes(b"multimodal probe fixture")
            fake_devecocli = multi / "fake-devecocli"
            fake_devecocli.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake_devecocli.chmod(0o755)

            def prepare_foundation() -> None:
                verify_command(
                    foundation, str(multi), "--round", "1", "--prepare-first-round",
                    "--devecocli", str(fake_devecocli),
                )

            def preflight_state() -> dict:
                index = json.loads((om / "evidence" / "index.json").read_text(encoding="utf-8"))
                return next(
                    item for item in index["entries"]
                    if item.get("evidenceId") == "E-PREFLIGHT"
                )

            prepare_foundation()
            # begin 不再依赖 read-protocol 凭据，并允许对同一批次幂等重跑。
            verify_command(preflight, "begin", str(multi))
            verify_command(preflight, "read-protocol", str(multi))
            verify_command(preflight, "begin", str(multi))
            state = preflight_state()
            assert state["data"]["batchId"] == "B01"
            assert {item["issueId"] for item in state["links"]} == {"B01-UI-001"}

            failed_probe = json.loads(
                verify_command(preflight, "record-multimodal", str(multi)).stdout
            )
            assert failed_probe == {
                "mode": "STOPPED",
                "stage": "multimodal_retry_confirmation_required",
                "next": "ask-test-scope",
                "multimodalAvailable": False,
                "testScopeEstimateMinutes": 6,
                "reason": "multimodal_probe_failed",
            }
            retry = json.loads(verify_command(
                preflight, "record-test-scope", str(multi),
                "--choice", "basic_and_multimodal",
            ).stdout)
            assert retry == {
                "mode": "STOPPED",
                "stage": "multimodal_reprobe_required",
                "next": "record-multimodal",
            }
            failed_again = json.loads(
                verify_command(preflight, "record-multimodal", str(multi)).stdout
            )
            assert failed_again["stage"] == "multimodal_retry_confirmation_required"
            verify_command(
                preflight, "record-test-scope", str(multi),
                "--choice", "basic_and_multimodal",
            )
            recovered_probe = json.loads(verify_command(
                preflight, "record-multimodal", str(multi), "--available",
                "--description", "蓝色圆形图标",
            ).stdout)
            assert recovered_probe == {
                "mode": "STATIC_ONLY",
                "stage": "multimodal_approved",
                "next": "prepare-device",
            }
            b01_artifact = om / "evidence" / "B01" / "round-1" / "round-1-B01-UI-001-foldable-expanded-layout.png"
            b01_artifact.parent.mkdir(parents=True)
            b01_artifact.write_bytes(b"B01 screenshot")
            result_file = multi / "B01-result.json"
            _write(result_file, {
                "round": 1, "commands": [], "artifacts": [{
                    "type": "screenshot",
                    "path": "evidence/B01/round-1/round-1-B01-UI-001-foldable-expanded-layout.png",
                    "links": [{
                        "issueId": "B01-UI-001", "form": "foldable-expanded",
                        "checkId": "layout",
                    }],
                }],
                "results": [{
                    "issueId": "B01-UI-001", "form": "foldable-expanded",
                    "checkId": "layout", "status": "failed", "reason": "布局仍异常",
                }],
            })
            verify_command(evidence, "record-batch", str(multi), "--input", str(result_file))
            after_test = json.loads(multi_ledger.read_text(encoding="utf-8"))
            current_batch = next(item for item in after_test["batches"] if item["batchId"] == "B01")
            current_issue = next(item for item in after_test["issues"] if item["issueId"] == "B01-UI-001")
            assert current_batch["status"] == "executing"
            assert current_batch["testConclusion"] == "not_run"
            assert "verifyStatus" not in current_issue
            assert current_issue["verificationResults"] == [{
                "form": "foldable-expanded", "checkId": "layout",
                "status": "failed", "reason": "布局仍异常",
            }]
            verify_command(
                validate_state, str(multi), "--route-map", ".onemulti/output/route-map.json",
            )

            done_file = multi / "B01-done.json"
            _write(done_file, {"status": "completed", "testConclusion": "failed"})
            command("transition-batch", str(multi_ledger), "B01", "--input", str(done_file))
            assert json.loads(multi_ledger.read_text(encoding="utf-8"))["task"]["status"] == "executing"
            _write(multi_task, {"currentBatch": "B02"})
            command("set-task", str(multi_ledger), "--input", str(multi_task))
            begin_multi_batch("B02")
            prepare_foundation()
            verify_command(preflight, "read-protocol", str(multi))
            verify_command(preflight, "begin", str(multi))
            state = preflight_state()
            assert state["data"]["batchId"] == "B02"
            assert {item["issueId"] for item in state["links"]} == {"B02-UI-001"}

            initial_probe = json.loads(verify_command(
                preflight, "record-multimodal", str(multi), "--available",
                "--description", "蓝色圆形图标",
            ).stdout)
            assert initial_probe["stage"] == "test_scope_confirmation_required"
            basic_only = json.loads(verify_command(
                preflight, "record-test-scope", str(multi), "--choice", "basic_only",
            ).stdout)
            assert basic_only == {
                "mode": "STATIC_ONLY",
                "stage": "multimodal_declined",
                "next": "record-static-only-results",
                "reason": "multimodal_declined_by_user",
            }

            b02_artifact = om / "evidence" / "B02" / "round-1" / "round-1-B02-UI-001-foldable-expanded-layout.png"
            b02_artifact.parent.mkdir(parents=True)
            b02_artifact.write_bytes(b"B02 screenshot")
            _write(result_file, {
                "round": 1, "commands": [], "artifacts": [{
                    "type": "screenshot",
                    "path": "evidence/B02/round-1/round-1-B02-UI-001-foldable-expanded-layout.png",
                    "links": [{
                        "issueId": "B02-UI-001", "form": "foldable-expanded",
                        "checkId": "layout",
                    }],
                }],
                "results": [{
                    "issueId": "B02-UI-001", "form": "foldable-expanded",
                    "checkId": "layout", "status": "failed", "reason": "布局仍异常",
                }],
            })
            verify_command(evidence, "record-batch", str(multi), "--input", str(result_file))
            index_path = om / "evidence" / "index.json"
            index_data = json.loads(index_path.read_text(encoding="utf-8"))
            artifact_paths = {
                item["path"] for item in index_data["entries"] if "path" in item
            }
            assert artifact_paths == {
                "evidence/B01/round-1/round-1-B01-UI-001-foldable-expanded-layout.png",
                "evidence/B02/round-1/round-1-B02-UI-001-foldable-expanded-layout.png",
            }
            verify_command(
                validate_state, str(multi), "--route-map", ".onemulti/output/route-map.json",
            )

            return True, "默认三设备、schema v3、施工期问题追加、批次证据隔离和原子写入链路通过"
        except (AssertionError, OSError, json.JSONDecodeError) as error:
            return False, str(error)
