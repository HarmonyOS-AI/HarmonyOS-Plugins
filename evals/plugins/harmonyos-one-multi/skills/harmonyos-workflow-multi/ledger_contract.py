"""task-ledger.py 的 schema v3 端到端合同测试。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
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
                "desc": "启动应用，进入 Index 页面",
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
            assert "reset" in help_text and "archive" not in help_text
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
            assert "hifiRequired" not in bootstrapped["task"]
            assert bootstrapped["batches"][0]["hifiRequired"] is False
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
            # 动作说明缺失、空白或类型错误时拒绝写入批次，不影响已有账本。
            for invalid_desc in (None, "", "  ", 123):
                invalid_route = _route_map()
                step = invalid_route["routes"][0]["steps"][0]
                if invalid_desc is None:
                    step.pop("desc")
                else:
                    step["desc"] = invalid_desc
                _write(route_map, invalid_route)
                result = command(
                    "put-batch", str(ledger), "--input", str(batch),
                    "--route-map", str(route_map), expect=1,
                )
                assert ".desc" in result.stdout + result.stderr
                assert _digest(ledger) == before_route_gate
            _write(route_map, _route_map())
            command(
                "put-batch", str(ledger), "--input", str(batch),
                "--route-map", str(route_map),
            )
            assert json.loads(ledger.read_text(encoding="utf-8"))["task"]["status"] == "planning"

            # 高保真要求按批保存；增量改计划或状态不能把已记录要求重置掉。
            hifi_patch = root / "hifi-patch.json"
            _write(hifi_patch, {"batchId": "B01", "hifiRequired": True})
            command("put-batch", str(ledger), "--input", str(hifi_patch),
                    "--route-map", str(route_map))
            command("put-batch", str(ledger), "--input", str(batch),
                    "--route-map", str(route_map))
            assert json.loads(ledger.read_text(encoding="utf-8"))["batches"][0]["hifiRequired"] is True
            for required in (False, True):
                _write(hifi_patch, {"batch": {"hifiRequired": required}})
                command("transition-batch", str(ledger), "B01", "--input", str(hifi_patch))
                hifi_data = json.loads(ledger.read_text(encoding="utf-8"))
                assert hifi_data["batches"][0]["hifiRequired"] is required
                assert hifi_data["batches"][0]["status"] == "pending"
                assert hifi_data["batches"][0]["specConfirmed"] is False
                assert hifi_data["task"]["targetForms"] == ["phone-portrait", "foldable-expanded"]
            before_hifi_error = _digest(ledger)
            for invalid_required in ("true", 1, None):
                _write(hifi_patch, {"batch": {"hifiRequired": invalid_required}})
                result = command("transition-batch", str(ledger), "B01", "--input", str(hifi_patch), expect=1)
                assert "hifiRequired" in result.stdout + result.stderr
                _write(hifi_patch, {"batchId": "B01", "hifiRequired": invalid_required})
                result = command("put-batch", str(ledger), "--input", str(hifi_patch),
                                 "--route-map", str(route_map), expect=1)
                assert "hifiRequired" in result.stdout + result.stderr
                assert _digest(ledger) == before_hifi_error
            # 不在 task 重复维护，也不因尚无 HTML 文件而增加写入门禁。
            _write(hifi_patch, {"hifiRequired": True})
            command("set-task", str(ledger), "--input", str(hifi_patch), expect=1)
            assert _digest(ledger) == before_hifi_error
            command("validate", str(ledger))

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

            # 已完成任务可继续；只刷新批次和任务状态，不清理原 SPEC 或证据。
            completed_data = json.loads(ledger.read_text(encoding="utf-8"))
            evidence_before_resume = _digest(root / "evidence" / "index.json")
            resume_patch = root / "resume.json"
            _write(resume_patch, {"status": "executing", "testConclusion": "not_run"})
            command("transition-batch", str(ledger), "B01", "--input", str(resume_patch))
            resumed_data = json.loads(ledger.read_text(encoding="utf-8"))
            assert resumed_data["task"]["status"] == "executing"
            assert resumed_data["issues"] == completed_data["issues"]
            assert resumed_data["decisions"] == completed_data["decisions"]
            assert resumed_data["batches"][0]["specConfirmed"] is True
            assert _digest(root / "evidence" / "index.json") == evidence_before_resume
            command("transition-batch", str(ledger), "B01", "--input", str(batch_done))

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
            # 新任务清理旧产物，保留运行资源与工程代码；不再创建历史副本。
            reset_project = root / "reset-project"
            reset_om = reset_project / ".onemulti"
            reset_om.mkdir(parents=True)
            reset_ledger = reset_om / "decisions.json"
            shutil.copy2(ledger, reset_ledger)
            shutil.copytree(evidence_dir, reset_om / "evidence")
            shutil.copytree(root / "output", reset_om / "output")
            preserved = [reset_om / "SKILL.md"] + [
                reset_om / directory / "keep.txt" for directory in ("assets", "references", "scripts", ".git")
            ]
            source_file = reset_project / "Index.ets"
            for path in preserved + [source_file]:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("keep", encoding="utf-8")
            for name in ("adaptation-report-B01.html", "adaptation-summary.html",
                         "adaptation-report-batch1.md", "page-scan-extra.py", "task.tmp"):
                (reset_om / name).write_text("old output", encoding="utf-8")
            external = root / "external-data"
            external.mkdir()
            (external / "keep.txt").write_text("outside", encoding="utf-8")
            (reset_om / "external-link").symlink_to(external, target_is_directory=True)
            # 误传工程目录或链接目录必须在删除前拒绝。
            original_digest = _digest(ledger)
            command("reset", str(ledger), expect=1)
            assert _digest(ledger) == original_digest
            linked_root = root / "linked-project"
            linked_root.mkdir()
            (linked_root / ".onemulti").symlink_to(reset_om, target_is_directory=True)
            command("reset", str(linked_root / ".onemulti" / "decisions.json"), expect=1)
            assert reset_ledger.is_file()
            cleared = json.loads(command("reset", str(reset_ledger)).stdout)
            assert cleared["removed"]
            assert {path.name for path in reset_om.iterdir()} == {"SKILL.md", "assets", "references", "scripts", ".git"}
            assert all(path.read_text(encoding="utf-8") == "keep" for path in preserved + [source_file])
            assert (external / "keep.txt").read_text(encoding="utf-8") == "outside"
            assert json.loads(command("reset", str(reset_ledger)).stdout)["removed"] == []

            # 清理后重新生成路由和计划，不能把新任务的产物一起删掉。
            next_task = root / "next-task.json"
            next_input = json.loads(bootstrap_input.read_text(encoding="utf-8"))
            next_input["task"]["taskId"] = "ui-eval-002"
            next_input["task"]["currentBatch"] = "B01"
            _write(next_task, next_input)
            (reset_om / "output").mkdir()
            next_route = reset_om / "output" / "route-map.json"
            _write(next_route, _route_map())
            command(
                "bootstrap", str(reset_ledger), "--input", str(next_task),
                "--route-map", str(next_route),
            )
            assert next_route.is_file()
            new_data = json.loads(reset_ledger.read_text(encoding="utf-8"))
            assert new_data["task"]["taskId"] == "ui-eval-002"
            assert new_data["task"]["status"] == "planning" and new_data["issues"] == []
            assert {path.name for path in (reset_om / "evidence").iterdir()} == {"index.json"}
            assert json.loads((reset_om / "evidence" / "index.json").read_text(encoding="utf-8")) == {
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
                            "desc": f"启动应用，进入 {Path(page).stem} 页面",
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
                    {"batchId": batch, "pages": [page], "dependencies": [], "risk": "low",
                     "hifiRequired": batch == "B01"}
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
            hifi_batches = json.loads(multi_ledger.read_text(encoding="utf-8"))
            assert hifi_batches["task"]["confirmationMode"] == "aggregate"
            assert {batch["batchId"]: batch["hifiRequired"] for batch in hifi_batches["batches"]} == {
                "B01": True, "B02": False,
            }

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

            # 缺少或失败的施工检查不阻断进入验证；失败记录仍保留。
            verify_command(preflight, "begin", str(multi))
            failing_check = om / "scripts" / "failing-check.py"
            failing_check.parent.mkdir(exist_ok=True)
            failing_check.write_text("raise SystemExit(1)\n", encoding="utf-8")
            failed_foundation = subprocess.run(
                [sys.executable, str(foundation), str(multi), "--prepare-first-round",
                 "--devecocli", str(fake_devecocli), "--check-script", str(failing_check)],
                text=True, capture_output=True, check=False,
            )
            assert failed_foundation.returncode == 1, failed_foundation.stderr
            assert not json.loads(failed_foundation.stdout)["ok"]
            verify_command(preflight, "begin", str(multi))
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
                "next": "wait-model-switch",
                "multimodalAvailable": False,
                "reason": "multimodal_probe_failed",
                "message": (
                    "当前模型未通过图片理解探测，请选择后续测试方式：\n\n"
                    "1. 仅基础测试（默认方案）：保留构建和静态检查结果，多模态测试标记为未验证，"
                    "继续生成报告。请回复“仅基础测试”。\n"
                    "2. 继续多模态测试：请先切换到支持图片理解的模型，"
                    "再回复“切换完，继续执行多模态测试”。"
                ),
            }
            # 用户选择或预授权默认方案时走基础测试；失败探测本身仍保持 STOPPED。
            basic_only = json.loads(verify_command(
                preflight, "record-test-scope", str(multi), "--choice", "basic_only",
            ).stdout)
            assert basic_only["mode"] == "STATIC_ONLY"
            assert basic_only["next"] == "record-static-only-results"
            assert not preflight_state()["data"].get("device")
            verify_command(preflight, "begin", str(multi))
            assert json.loads(verify_command(preflight, "record-multimodal", str(multi)).stdout) == failed_probe
            # 模拟用户在下一轮切换模型并明确继续；不是在失败后弹卡要求重试。
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
            assert failed_again == failed_probe
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
            # 只使用假 CLI：验证 L2 失败仍可执行 L3，首轮失败不结束批次，
            # 修复后第 2–5 轮仍能写入新结果；这里不启动真实设备。
            test_tmp = om / "evidence" / "tmp"
            test_tmp.mkdir(exist_ok=True)
            device_file = test_tmp / "device.json"
            _write(device_file, {"kind": "emulator", "identifier": "fixture-device"})
            verify_command(preflight, "bind-device", str(multi), "--input", str(device_file))
            calls = test_tmp / "cli-calls.txt"
            fake_devecocli.write_text(
                f"#!{sys.executable}\nimport sys\nfrom pathlib import Path\n"
                f"with Path({str(calls)!r}).open('a') as stream:\n"
                "    stream.write(sys.argv[1] + '\\n')\n",
                encoding="utf-8",
            )
            for round_number in range(1, 6):
                if round_number == 2:
                    failing_check.write_text("raise SystemExit(0)\n", encoding="utf-8")
                foundation_result = subprocess.run(
                    [sys.executable, str(foundation), str(multi), "--round", str(round_number),
                     "--devecocli", str(fake_devecocli), "--check-script", str(failing_check)],
                    text=True, capture_output=True, check=False,
                )
                assert foundation_result.returncode == (1 if round_number == 1 else 0), \
                    foundation_result.stderr
                levels = json.loads(foundation_result.stdout)["levels"]
                assert levels["L1"] == 0 and levels["L3"] == 0
                assert preflight_state()["data"]["mode"] == "FULL"
                result_status = "passed" if round_number == 5 else "failed"
                round_input = test_tmp / "repair-round.json"
                _write(round_input, {
                    "round": round_number,
                    "commands": [{
                        "argv": ["fixture-ui-check", str(round_number)],
                        "exitCode": 0 if result_status == "passed" else 1,
                        **({"reason": f"第 {round_number} 轮新定位的布局问题"}
                           if result_status == "failed" else {}),
                        "links": [{"issueId": "B01-UI-001", "form": "foldable-expanded",
                                   "checkId": "layout"}],
                    }],
                    "artifacts": [],
                    "results": [{
                        "issueId": "B01-UI-001", "form": "foldable-expanded", "checkId": "layout",
                        "status": result_status,
                        **({"reason": f"第 {round_number} 轮新定位的布局问题"}
                           if result_status == "failed" else {}),
                    }],
                })
                verify_command(evidence, "record-batch", str(multi), "--input", str(round_input))
                round_ledger = json.loads(multi_ledger.read_text(encoding="utf-8"))
                assert round_ledger["batches"][0]["status"] == "executing"
                assert round_ledger["batches"][0]["testConclusion"] == "not_run"
                assert round_ledger["issues"][0]["verificationResults"][0]["status"] == result_status
            assert calls.read_text(encoding="utf-8").splitlines() == ["build", "run"] * 5
            evidence_index = json.loads((om / "evidence" / "index.json").read_text(encoding="utf-8"))
            foundations = [item for item in evidence_index["entries"]
                           if item.get("data", {}).get("phase") == "step3_foundation"]
            assert [item["round"] for item in foundations[-5:]] == [1, 2, 3, 4, 5]
            assert [item["data"]["exitCode"] for item in foundations[-5:]] == [1, 0, 0, 0, 0]

            # 独立多模块夹具：模块名不同于目录名，嵌套 HSP、同名前缀 HAR 和后续批次隔离。
            hsp_project = root / "hsp-build"
            shutil.copytree(multi, hsp_project)
            hsp_om = hsp_project / ".onemulti"
            module_definitions = [
                ("entry", "entry", "entry"),
                ("ui_shared", "libs/ui", "shared"),
                ("nested_shared", "libs/ui/nested", "shared"),
                ("other_har", "libs/ui-extra", "har"),
                ("later_shared", "libs/later", "shared"),
            ]
            profile_path = hsp_project / "build-profile.json5"
            _write(profile_path, {"modules": [
                {"name": name, "srcPath": directory} for name, directory, _ in module_definitions
            ]})
            for name, directory, kind in module_definitions:
                module_file = hsp_project / directory / "src/main/module.json5"
                module_file.parent.mkdir(parents=True, exist_ok=True)
                module_file.write_text(
                    "// JSON5 fixture\n{'module': {'name': '" + name
                    + "', 'type': '" + kind + "',},}\n", encoding="utf-8",
                )
            hsp_ledger = json.loads((hsp_om / "decisions.json").read_text(encoding="utf-8"))
            hsp_ledger["issues"][0]["changedFiles"] += [
                "libs/ui/a.ets", "libs/ui/b.ets", "libs/ui/nested/c.ets", "libs/ui-extra/d.ets",
            ]
            hsp_ledger["issues"][1].update({
                "changeStatus": "modified", "changedFiles": ["libs/later/a.ets"],
                "changeSummary": "后续批次的修改不得混入本批 HSP 构建",
            })
            _write(hsp_om / "decisions.json", hsp_ledger)
            hsp_calls = hsp_om / "evidence/tmp/hsp-calls.jsonl"
            fail_hsp = hsp_om / "evidence/tmp/fail-hsp"
            hsp_cli = hsp_project / "fake-devecocli"
            hsp_cli.write_text(
                f"#!{sys.executable}\nimport json, sys\nfrom pathlib import Path\n"
                f"with Path({str(hsp_calls)!r}).open('a') as stream:\n"
                "    stream.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                f"if '--modules' in sys.argv and Path({str(fail_hsp)!r}).exists():\n"
                "    print('fixture HSP compile error', file=sys.stderr)\n"
                "    raise SystemExit(7)\n", encoding="utf-8",
            )
            hsp_argv = ["build", "--modules", "nested_shared", "ui_shared"]
            default_build = ["build"]
            device_run = ["run", "--device", "fixture-device"]

            def run_hsp(*arguments: str, expected: int = 0) -> tuple[dict, list]:
                hsp_calls.write_text("", encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(foundation), str(hsp_project),
                     "--devecocli", str(hsp_cli), *arguments],
                    text=True, capture_output=True, check=False,
                )
                assert result.returncode == expected, result.stdout + result.stderr
                return json.loads(result.stdout), [
                    json.loads(line) for line in hsp_calls.read_text(encoding="utf-8").splitlines()
                ]

            fail_hsp.write_text("fail", encoding="utf-8")
            result, commands = run_hsp("--prepare-first-round", expected=1)
            assert commands == [hsp_argv, default_build]
            assert result["levels"]["L1"] == 7 and result["levels"]["L3"] is None
            fail_hsp.unlink()
            result, commands = run_hsp("--prepare-first-round")
            assert commands == [hsp_argv, default_build]
            assert result["hspModules"] == ["nested_shared", "ui_shared"]
            # 同源码且 HSP 已编译时，首轮只装机；旧版无 HSP 记录时必须补跑。
            result, commands = run_hsp("--round", "1")
            assert commands == [device_run] and result["levels"]["L1"] is None
            hsp_index_path = hsp_om / "evidence/index.json"
            hsp_index = json.loads(hsp_index_path.read_text(encoding="utf-8"))
            hsp_index["entries"] = [item for item in hsp_index["entries"]
                                    if item.get("data", {}).get("phase") != "hsp_build"]
            _write(hsp_index_path, hsp_index)
            for round_number in range(1, 6):
                result, commands = run_hsp("--round", str(round_number))
                assert commands == [hsp_argv, default_build, device_run]
                assert result["levels"]["L1"] == 0
            # HSP 失败不能被入口成功覆盖，也不能安装旧包；配置识别失败同样登记。
            fail_hsp.write_text("fail", encoding="utf-8")
            result, commands = run_hsp("--round", "5", expected=1)
            assert commands == [hsp_argv, default_build]
            assert result["levels"]["L1"] == 7 and result["levels"]["L3"] is None
            hsp_index = json.loads(hsp_index_path.read_text(encoding="utf-8"))
            assert any(item.get("data", {}).get("phase") == "hsp_build"
                       and item["data"].get("exitCode") == 7
                       and "HSP compile error" in item["data"].get("stderr", "")
                       for item in hsp_index["entries"])
            profile_path.write_text("{invalid", encoding="utf-8")
            result, commands = run_hsp("--round", "5", expected=1)
            assert commands == [default_build] and result["levels"]["L3"] is None
            hsp_index = json.loads(hsp_index_path.read_text(encoding="utf-8"))
            assert "HSP 模块识别失败" in hsp_index["entries"][-1]["data"]["stderr"]
            assert next(item for item in hsp_index["entries"]
                        if item.get("evidenceId") == "E-PREFLIGHT")["data"]["mode"] == "FULL"
            assert json.loads((hsp_om / "decisions.json").read_text(encoding="utf-8"))["batches"][0]["status"] == "executing"

            # 构建失败、命令缺失都登记错误；不启动旧包，也不把 preflight 改成 STOPPED。
            fake_devecocli.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            for cli_path in (fake_devecocli, test_tmp / "missing-cli"):
                failed_build = subprocess.run(
                    [sys.executable, str(foundation), str(multi), "--round", "5",
                     "--devecocli", str(cli_path)],
                    text=True, capture_output=True, check=False,
                )
                assert failed_build.returncode == 1, failed_build.stderr
                assert json.loads(failed_build.stdout)["levels"]["L3"] is None
                assert preflight_state()["data"]["mode"] == "FULL"
            fake_devecocli.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            excessive_round = subprocess.run(
                [sys.executable, str(foundation), str(multi), "--round", "6",
                 "--devecocli", str(fake_devecocli)],
                text=True, capture_output=True, check=False,
            )
            assert excessive_round.returncode == 2
            # 未登记的额外日志不作为证据，也不阻断收尾校验。
            (om / "evidence" / "extra.log").write_text("unused log", encoding="utf-8")
            verify_command(validate_state, str(multi))
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
            # 流程状态不是写入权限：补测、证据和回归记录不被旧状态或确认标记卡住。
            phase_patch = root / "batch-phase.json"
            for status in ("pending", "completed", "stopped"):
                _write(phase_patch, {"status": status, "specConfirmed": False})
                command("transition-batch", str(multi_ledger), "B01", "--input", str(phase_patch))
                prepare_foundation()
                phase_preflight = json.loads(verify_command(preflight, "begin", str(multi)).stdout)
                assert phase_preflight["next"] == "record-multimodal"
                verify_command(evidence, "record-batch", str(multi), "--input", str(result_file))
                command(
                    "add-deferred-regression", str(multi_ledger), "B01-UI-001",
                    "--input", str(deferred_file),
                )
                phase_data = json.loads(multi_ledger.read_text(encoding="utf-8"))
                assert phase_data["batches"][0]["status"] == status
                assert phase_data["batches"][0]["specConfirmed"] is False
            _write(phase_patch, {"specConfirmed": True})
            command("transition-batch", str(multi_ledger), "B01", "--input", str(phase_patch))
            # 补测恢复后，原批次可再次进入第四步，原证据仍可读取。
            command("transition-batch", str(multi_ledger), "B01", "--input", str(resume_patch))
            prepare_foundation()
            resumed_preflight = json.loads(verify_command(preflight, "begin", str(multi)).stdout)
            assert resumed_preflight["next"] == "record-multimodal"
            assert b01_artifact.read_bytes() == b"B01 screenshot"
            assert json.loads(multi_ledger.read_text(encoding="utf-8"))["issues"] == after_test["issues"]
            command("transition-batch", str(multi_ledger), "B01", "--input", str(done_file))
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
            assert initial_probe["next"] == "ask-test-scope"
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
