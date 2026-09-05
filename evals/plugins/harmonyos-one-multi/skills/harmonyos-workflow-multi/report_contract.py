"""HTML 报告渲染契约：统计、截图、转义、汇总和失败原子性。"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


_ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _issue(batch_id: str, status: str) -> dict:
    issue_id = f"{batch_id}-UI-001"
    page = f"entry/src/main/ets/pages/{batch_id}.ets"
    result_reason = None if status == "passed" else "multimodal_declined_by_user"
    return {
        "issueId": issue_id,
        "batchId": batch_id,
        "page": page,
        "component": f"{batch_id} 页面",
        "domain": "size-layout",
        "affectedPages": [],
        "targetForms": ["LG"],
        "problem": "固定单列 <script>alert(1)</script>& 会在宽窗留白",
        "source": "task_analysis",
        "rootCause": "布局没有响应窗口宽度",
        "proposal": "LG 使用双列布局",
        "plannedFiles": [page],
        "verificationPlan": [{
            "form": "LG",
            "checkId": "layout",
            "routeId": f"R-{batch_id}",
            "check": "宽窗显示双列且内容不留异常空白",
        }],
        "changeStatus": "modified",
        "verificationResults": [{
            "form": "LG",
            "checkId": "layout",
            "status": status,
            "reason": result_reason,
        }],
        "changedFiles": [page],
        "changeSummary": "已按窗口宽度切换为双列",
        "notChangedReason": None,
        "introducedByBatch": None,
        "deferredRegressions": [],
    }


def _ledger() -> dict:
    batches = []
    pages = {}
    issues = []
    for batch_id, result in (("B01", "passed"), ("B02", "not_verified")):
        page = f"entry/src/main/ets/pages/{batch_id}.ets"
        pages[page] = {
            "type": "page",
            "module": "entry",
            "dependencies": [],
            "batchId": batch_id,
            "missingFromScan": False,
        }
        batches.append({
            "batchId": batch_id,
            "pages": [page],
            "dependencies": [],
            "predecessors": [] if batch_id == "B01" else ["B01"],
            "domains": ["size-layout"],
            "risk": "low",
            "status": "executing",
            "specConfirmed": True,
            "testConclusion": "not_run",
        })
        issues.append(_issue(batch_id, result))
    return {
        "schemaVersion": 3,
        "task": {
            "taskId": "ui-report-contract",
            "scope": list(pages),
            "targetForms": ["LG"],
            "confirmationMode": "batch",
            "routeMap": "output/route-map.json",
            "status": "executing",
            "currentBatch": "B01",
        },
        "decisions": [],
        "pages": pages,
        "batches": batches,
        "issues": issues,
    }


def _evidence() -> dict:
    entries = []
    for number, batch_id in enumerate(("B01", "B02"), start=1):
        entries.append({
            "evidenceId": f"E-CMD-{number:02d}",
            "type": "command",
            "round": 1,
            "links": [{"issueId": f"{batch_id}-UI-001"}],
            "data": {
                "argv": ["devecocli", "build"],
                "exitCode": 0,
                "phase": "step3_foundation",
            },
        })
    entries.append({
        "evidenceId": "E-SHOT-01",
        "type": "screenshot",
        "round": 1,
        "links": [{
            "issueId": "B01-UI-001",
            "form": "LG",
            "checkId": "layout",
        }],
        "path": "evidence/B01/round-1/layout.png",
    })
    return {"schemaVersion": 3, "taskId": "ui-report-contract", "entries": entries}


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_cli(script: Path, root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), str(root), *arguments],
        text=True,
        capture_output=True,
        check=False,
    )


def _assert_navigation_targets(html: str) -> None:
    navigation = html.split('<aside class="side-nav"', 1)[1].split("</aside>", 1)[0]
    targets = re.findall(r'href="(#[^"]+)"', navigation)
    assert targets, "侧栏没有页内导航"
    for target in targets:
        assert f'id="{target[1:]}"' in html, f"侧栏目标不存在: {target}"


def run(skill_root: Path) -> tuple[bool, str]:
    """覆盖报告主流程；返回统一用例结果供 run_evals.py 展示。"""
    script = skill_root / "scripts" / "render-report.py"
    template = skill_root / "assets" / "report" / "report-template.html"
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / ".onemulti"
            target_template = root / "assets" / "report" / "report-template.html"
            target_template.parent.mkdir(parents=True)
            shutil.copy2(template, target_template)
            _write_json(root / "decisions.json", _ledger())
            _write_json(root / "evidence" / "index.json", _evidence())
            _write_json(root / "output" / "route-map.json", {"routes": []})
            screenshot = root / "evidence" / "B01" / "round-1" / "layout.png"
            screenshot.parent.mkdir(parents=True)
            screenshot.write_bytes(_ONE_PIXEL_PNG)

            inputs_before = (_digest(root / "decisions.json"), _digest(root / "evidence" / "index.json"))
            first = _run_cli(script, root, "--batch-id", "B01")
            assert first.returncode == 0, first.stderr
            payload = json.loads(first.stdout)
            assert payload["testConclusion"] == "passed"
            assert payload["flowStatus"] == "completed"
            assert payload["verificationState"] == "passed"
            assert payload["counts"] == {
                "blocked": 0,
                "changedFiles": 1,
                "failed": 0,
                "issues": 1,
                "modified": 1,
                "notApplicable": 0,
                "notModified": 0,
                "notVerified": 0,
                "passed": 1,
                "plans": 1,
            }
            report_b01 = root / "adaptation-report-B01.html"
            html = report_b01.read_text(encoding="utf-8")
            assert "验证截图" in html and "data:image/png;base64," in html
            assert "B01 · 批次报告" in html
            assert "B01 · 批次报告 ·" not in html
            assert "LG · layout" in html
            assert "<th>原因</th><th>证据</th>" in html
            assert "<th>检查</th><th>最终结果</th><th>说明</th>" in html
            assert "L1 构建" in html and "L2 静态检查" in html and "运行态验证" in html
            assert 'class="metric" href="#changes"' in html
            assert 'class="metric" href="#validation"' in html
            assert 'id="changes"' in html and 'id="validation"' in html
            assert 'aria-label="报告导航"' in html and "B01 · 报告导航" in html
            assert "grid-template-columns: 204px minmax(0, 1fr)" in html
            _assert_navigation_targets(html)
            assert "查看详细执行记录" not in html
            assert "未发现适配前历史问题" in html
            assert "<script>alert(1)</script>" not in html
            assert "&lt;script&gt;alert(1)&lt;/script&gt;&amp;" in html
            assert 'src="http' not in html and 'href="http' not in html
            assert "路由表" not in html
            assert inputs_before == (
                _digest(root / "decisions.json"),
                _digest(root / "evidence" / "index.json"),
            ), "报告脚本修改了账本或 evidence"

            first_digest = _digest(report_b01)
            repeated = _run_cli(script, root, "--batch-id", "B01")
            assert repeated.returncode == 0, repeated.stderr
            assert _digest(report_b01) == first_digest, "相同输入重复生成不确定"

            no_proof = json.loads((root / "evidence" / "index.json").read_text(encoding="utf-8"))
            no_proof["entries"] = [
                entry for entry in no_proof["entries"] if entry["evidenceId"] != "E-SHOT-01"
            ]
            _write_json(root / "evidence" / "index.json", no_proof)
            no_proof_result = _run_cli(script, root, "--batch-id", "B01")
            assert no_proof_result.returncode != 0
            assert _digest(report_b01) == first_digest, "缺少验证证据时覆盖了有效报告"
            _write_json(root / "evidence" / "index.json", _evidence())

            second = _run_cli(script, root, "--batch-id", "B02")
            assert second.returncode == 0, second.stderr
            second_payload = json.loads(second.stdout)
            assert second_payload["testConclusion"] == "failed"
            assert second_payload["flowStatus"] == "completed"
            assert second_payload["verificationState"] == "incomplete"
            assert second_payload["counts"]["notVerified"] == 1
            html_b02 = (root / "adaptation-report-B02.html").read_text(encoding="utf-8")
            assert "验证截图" not in html_b02 and "data:image/" not in html_b02
            assert "任务流程：已完成" in html_b02 and "基础验证通过" in html_b02
            assert '<span>任务流程</span><strong>已完成</strong>' in html_b02
            assert "未进行多模态验证（用户跳过）" in html_b02
            assert "待补充验证" in html_b02
            assert "1 项运行态检查尚未完成" in html_b02
            assert 'class="metric" href="#pending-validation"' in html_b02
            assert 'id="pending-validation"' in html_b02
            assert "<h2>未解决问题</h2>" not in html_b02
            validation_table = html_b02.split("<h2>验证结果矩阵</h2>", 1)[1].split("</table>", 1)[0]
            assert "<th>证据</th>" not in validation_table
            assert "multimodal_declined_by_user" not in html_b02
            assert "<span>最终结论</span>" not in html_b02

            foundation_failed = _evidence()
            foundation_failed["entries"][1]["data"]["exitCode"] = 1
            _write_json(root / "evidence" / "index.json", foundation_failed)
            failed_foundation = _run_cli(script, root, "--batch-id", "B02")
            assert failed_foundation.returncode == 0, failed_foundation.stderr
            failed_foundation_html = (root / "adaptation-report-B02.html").read_text(
                encoding="utf-8"
            )
            assert "验证未通过" in failed_foundation_html
            assert "L1/L2 基础检查" in failed_foundation_html
            assert "构建或静态检查至少一项未通过" in failed_foundation_html

            ledger = json.loads((root / "decisions.json").read_text(encoding="utf-8"))
            ledger["task"]["status"] = "completed"
            ledger["task"]["currentBatch"] = "B02"
            for batch in ledger["batches"]:
                batch["status"] = "completed"
                batch["testConclusion"] = "passed" if batch["batchId"] == "B01" else "failed"
            _write_json(root / "decisions.json", ledger)
            summary = _run_cli(script, root, "--summary")
            assert summary.returncode == 0, summary.stderr
            summary_payload = json.loads(summary.stdout)
            assert summary_payload["testConclusion"] == "failed"
            assert summary_payload["flowStatus"] == "completed"
            assert summary_payload["verificationState"] == "failed"
            assert summary_payload["counts"]["issues"] == 2
            summary_html = (root / "adaptation-summary.html").read_text(encoding="utf-8")
            assert "adaptation-report-B01.html" in summary_html
            assert "adaptation-report-B02.html" in summary_html
            assert "汇总报告导航" in summary_html and "批次报告" in summary_html
            assert summary_html.count('class="nav-batch"') == 2
            _assert_navigation_targets(summary_html)
            assert "基础检查未通过，仍有 1 项运行或视觉检查未验证" in summary_html
            assert "0 项验证失败" not in summary_html

            valid_report_digest = _digest(report_b01)
            broken = json.loads((root / "evidence" / "index.json").read_text(encoding="utf-8"))
            broken["entries"][-1]["path"] = "evidence/B01/round-1/missing.png"
            _write_json(root / "evidence" / "index.json", broken)
            rejected = _run_cli(script, root, "--batch-id", "B01")
            assert rejected.returncode != 0
            assert report_b01.exists() and _digest(report_b01) == valid_report_digest, (
                "异常输入覆盖了上一份有效报告"
            )
    except Exception as error:  # noqa: BLE001 - 契约需返回完整失败原因
        return False, str(error)
    return True, "批次/汇总统计、截图归档、转义、确定性和异常拒绝均通过"
