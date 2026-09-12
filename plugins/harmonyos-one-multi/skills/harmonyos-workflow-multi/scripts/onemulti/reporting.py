"""从一多任务账本和证据索引生成确定性的 HTML 报告数据与页面片段。"""

from __future__ import annotations

import base64
from collections import defaultdict
from copy import deepcopy
from html import escape
import json
import mimetypes
from pathlib import Path
import re
from typing import Any

from .ledger import validate_ledger


class ReportError(ValueError):
    """报告输入、聚合或模板无效。"""


STATUS_LABELS = {
    "passed": "通过",
    "failed": "未通过",
    "incomplete": "验证未完成",
    "not_verified": "未验证",
    "not_applicable": "不适用",
    "modified": "已修改",
    "not_modified": "未修改",
    "blocked": "阻塞",
    "pending": "待处理",
    "executing": "执行中",
    "completed": "已完成",
    "stopped": "已停止",
    "not_run": "未执行",
}
SAFE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
IMAGE_MIMES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
REASON_LABELS = {
    "command_failed": "命令执行失败",
    "multimodal_declined_by_user": "未进行多模态验证（用户跳过）",
    "representative_device_unavailable": "没有可用的代表性目标设备",
}
def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReportError(f"无法读取 {path}: {error}") from error
    if not isinstance(value, dict):
        raise ReportError(f"{path} 顶层必须是 JSON 对象")
    return value


def load_inputs(om_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    ledger = load_object(om_root / "decisions.json")
    errors = validate_ledger(ledger)
    if errors:
        raise ReportError("decisions.json 无效: " + "; ".join(errors))
    index = load_object(om_root / "evidence" / "index.json")
    validate_evidence(index, ledger, om_root)
    return ledger, index


def validate_evidence(index: dict[str, Any], ledger: dict[str, Any], om_root: Path) -> None:
    if set(index) != {"schemaVersion", "taskId", "entries"} or index.get("schemaVersion") != 3:
        raise ReportError("evidence/index.json 顶层结构或 schemaVersion 无效")
    if index.get("taskId") != ledger["task"]["taskId"]:
        raise ReportError("evidence/index.json 与 decisions.json 的 taskId 不一致")
    entries = index.get("entries")
    if not isinstance(entries, list):
        raise ReportError("evidence/index.json.entries 必须是数组")

    issues = {item["issueId"]: item for item in ledger["issues"]}
    decision_ids = {
        item["decisionId"] for item in ledger["decisions"]
        if isinstance(item, dict) and isinstance(item.get("decisionId"), str)
    }
    plan_keys = {
        (issue["issueId"], plan["form"], plan["checkId"])
        for issue in ledger["issues"]
        for plan in issue.get("verificationPlan", [])
    }
    evidence_ids: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ReportError("evidence entries 中存在非对象")
        evidence_id = entry.get("evidenceId")
        if not isinstance(evidence_id, str) or not evidence_id or evidence_id in evidence_ids:
            raise ReportError(f"evidenceId 缺失或重复: {evidence_id}")
        evidence_ids.add(evidence_id)
        if not {"type", "round", "links"} <= set(entry):
            raise ReportError(f"{evidence_id} 缺少 type/round/links")
        if not isinstance(entry.get("type"), str) or not entry["type"]:
            raise ReportError(f"{evidence_id}.type 必须是非空字符串")
        round_number = entry.get("round")
        if round_number is not None and (
            not isinstance(round_number, int) or isinstance(round_number, bool)
            or not 1 <= round_number <= 5
        ):
            raise ReportError(f"{evidence_id}.round 必须为 null 或 1..5")
        if ("data" in entry) == ("path" in entry):
            raise ReportError(f"{evidence_id} 必须且只能包含 data 或 path")
        if "data" in entry and not isinstance(entry["data"], dict):
            raise ReportError(f"{evidence_id}.data 必须是对象")
        if not isinstance(entry.get("links"), list):
            raise ReportError(f"{evidence_id}.links 必须是数组")
        for link in entry["links"]:
            if not isinstance(link, dict) or not link:
                raise ReportError(f"{evidence_id} 包含无效 link")
            if "decisionId" in link and link["decisionId"] not in decision_ids:
                raise ReportError(f"{evidence_id} 引用了不存在的 decision")
            if "issueId" not in link:
                if set(link) != {"decisionId"}:
                    raise ReportError(f"{evidence_id} 的 link 缺少有效 issueId/decisionId")
                continue
            if link.get("issueId") not in issues:
                raise ReportError(f"{evidence_id} 引用了不存在的 issue")
            has_plan_key = "form" in link or "checkId" in link
            if has_plan_key and (
                not {"issueId", "form", "checkId"} <= set(link)
                or (link["issueId"], link["form"], link["checkId"]) not in plan_keys
            ):
                raise ReportError(f"{evidence_id} 引用了不存在的验证计划项")
        if "path" in entry:
            if not isinstance(entry["path"], str) or not entry["path"]:
                raise ReportError(f"{evidence_id}.path 必须是非空字符串")
            relative = Path(entry["path"])
            target = (om_root / relative).resolve()
            try:
                target.relative_to(om_root.resolve())
            except ValueError as error:
                raise ReportError(f"{evidence_id} 的文件路径越出 .onemulti") from error
            if not target.is_file():
                raise ReportError(f"{evidence_id} 引用的文件不存在: {relative.as_posix()}")
        if entry["type"] == "screenshot" and not any(
            isinstance(link, dict) and {"issueId", "form", "checkId"} <= set(link)
            for link in entry["links"]
        ):
            raise ReportError(f"{evidence_id} 截图必须关联 issueId/form/checkId")


def esc(value: object) -> str:
    return escape("" if value is None else str(value), quote=True)


def label(value: str) -> str:
    return STATUS_LABELS.get(value, value)


def human_reason(value: object) -> str:
    if value is None or value == "":
        return "—"
    text = str(value)
    return REASON_LABELS.get(text, text)


def status_class(value: str) -> str:
    if value == "completed":
        return "passed"
    if value == "stopped":
        return "failed"
    if value == "incomplete":
        return "not_verified"
    if value == "blocked":
        return "failed"
    return value if value in {"passed", "failed", "not_verified", "not_applicable"} else "neutral"


def safe_batch_id(batch_id: str) -> str:
    if not SAFE_TOKEN.fullmatch(batch_id):
        raise ReportError(f"batchId 不能用于报告文件名: {batch_id}")
    return batch_id


def batch_for(ledger: dict[str, Any], batch_id: str) -> dict[str, Any]:
    for batch in ledger["batches"]:
        if batch.get("batchId") == batch_id:
            return batch
    raise ReportError(f"批次不存在: {batch_id}")


def issues_for(ledger: dict[str, Any], batch_id: str) -> list[dict[str, Any]]:
    return sorted(
        [item for item in ledger["issues"] if item.get("batchId") == batch_id],
        key=lambda item: item["issueId"],
    )


def entry_batch_ids(entry: dict[str, Any], issue_batches: dict[str, str]) -> set[str]:
    values = {
        issue_batches[link["issueId"]]
        for link in entry.get("links", [])
        if isinstance(link, dict) and link.get("issueId") in issue_batches
    }
    data = entry.get("data")
    if isinstance(data, dict) and isinstance(data.get("batchId"), str):
        values.add(data["batchId"])
    return values


def entries_for(index: dict[str, Any], ledger: dict[str, Any], batch_id: str) -> list[dict[str, Any]]:
    issue_batches = {item["issueId"]: item["batchId"] for item in ledger["issues"]}
    return [
        entry for entry in index["entries"]
        if batch_id in entry_batch_ids(entry, issue_batches)
    ]


def plan_rows(issue: dict[str, Any], evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result_map = {
        (item["form"], item["checkId"]): item
        for item in issue.get("verificationResults", [])
    }
    rows: list[dict[str, Any]] = []
    for plan in issue.get("verificationPlan", []):
        key = (plan["form"], plan["checkId"])
        result = result_map.get(key)
        if result is None:
            if issue.get("changeStatus") == "not_modified":
                result = {
                    "status": "not_applicable",
                    "reason": issue.get("notChangedReason") or "未施工",
                }
            elif issue.get("changeStatus") == "blocked":
                result = {
                    "status": "not_verified",
                    "reason": issue.get("notChangedReason") or "问题阻塞",
                }
            else:
                raise ReportError(
                    f"{issue['issueId']}/{plan['form']}/{plan['checkId']} 缺少验证结果"
                )
        evidence_ids = sorted({
            entry["evidenceId"]
            for entry in evidence
            for link in entry.get("links", [])
            if isinstance(link, dict)
            and link.get("issueId") == issue["issueId"]
            and link.get("form") == plan["form"]
            and link.get("checkId") == plan["checkId"]
        })
        if result["status"] == "passed" and not evidence_ids:
            raise ReportError(
                f"{issue['issueId']}/{plan['form']}/{plan['checkId']} 标记为 passed，"
                "但没有按验证项登记 evidence"
            )
        rows.append({
            **plan,
            "status": result["status"],
            "reason": result.get("reason"),
            "evidenceIds": evidence_ids,
        })
    return rows


def foundation_state(evidence: list[dict[str, Any]]) -> dict[str, Any]:
    commands = [
        entry for entry in evidence
        if entry.get("type") == "command"
        and isinstance(entry.get("data"), dict)
        and entry["data"].get("phase") == "step3_foundation"
    ]
    if not commands:
        return {"status": "not_verified", "evidenceId": None, "exitCode": None}
    latest = commands[-1]
    exit_code = latest["data"].get("exitCode")
    return {
        "status": "passed" if exit_code == 0 else "failed",
        "evidenceId": latest["evidenceId"],
        "exitCode": exit_code,
    }


def batch_model(
    ledger: dict[str, Any], index: dict[str, Any], om_root: Path, batch_id: str
) -> dict[str, Any]:
    batch = batch_for(ledger, batch_id)
    issues = issues_for(ledger, batch_id)
    evidence = entries_for(index, ledger, batch_id)
    stopped = batch.get("status") == "stopped"
    if not issues and not stopped:
        raise ReportError(f"{batch_id} 没有问题清单，不能生成报告")
    if not stopped and any(item.get("changeStatus") == "pending" for item in issues):
        raise ReportError(f"{batch_id} 仍有 pending 问题，不能生成报告")

    all_rows: list[dict[str, Any]] = []
    issue_models: list[dict[str, Any]] = []
    for issue in issues:
        normalized_issue = issue
        if stopped and issue.get("changeStatus") == "pending":
            normalized_issue = deepcopy(issue)
            normalized_issue["changeStatus"] = "blocked"
            normalized_issue["notChangedReason"] = "批次已停止"
        if normalized_issue.get("changeStatus") == "modified" and not normalized_issue.get(
            "verificationPlan"
        ):
            raise ReportError(f"{issue['issueId']} 已修改但没有 verificationPlan")
        rows = plan_rows(normalized_issue, evidence)
        all_rows.extend({"issueId": issue["issueId"], **row} for row in rows)
        issue_models.append({**deepcopy(normalized_issue), "planRows": rows})

    foundation = foundation_state(evidence)
    statuses = [item["status"] for item in all_rows]
    failed = statuses.count("failed")
    not_verified = statuses.count("not_verified")
    blocked = sum(item.get("changeStatus") == "blocked" for item in issue_models)
    conclusion = "failed" if (
        stopped
        or
        foundation["status"] != "passed" or failed or not_verified or blocked
    ) else "passed"
    changed_files = sorted({
        path for issue in issue_models for path in issue.get("changedFiles", [])
    })
    baseline = [item for item in issue_models if item.get("source") == "baseline"]
    counts = {
        "issues": len(issue_models),
        "modified": sum(item.get("changeStatus") == "modified" for item in issue_models),
        "notModified": sum(item.get("changeStatus") == "not_modified" for item in issue_models),
        "blocked": blocked,
        "plans": len(all_rows),
        "passed": statuses.count("passed"),
        "failed": failed,
        "notVerified": not_verified,
        "notApplicable": statuses.count("not_applicable"),
        "changedFiles": len(changed_files),
    }
    if stopped or blocked:
        verification_state = "blocked"
    elif foundation["status"] == "failed" or failed:
        verification_state = "failed"
    elif foundation["status"] != "passed" or not_verified:
        verification_state = "incomplete"
    else:
        verification_state = "passed"
    only_multimodal_skipped_state = (
        verification_state == "incomplete"
        and foundation["status"] == "passed"
        and bool(not_verified)
        and all(
            row.get("reason") == "multimodal_declined_by_user"
            for row in all_rows if row.get("status") == "not_verified"
        )
    )
    total_batches = len(ledger["batches"])
    compact = (
        total_batches == 1
        and len(batch.get("pages", [])) <= 3
        and not failed and not not_verified and not blocked and not baseline
    )
    tier = "compact" if compact else "standard"
    return {
        "kind": "batch",
        "tier": tier,
        "task": ledger["task"],
        "decisions": ledger["decisions"],
        "batch": batch,
        "issues": issue_models,
        "rows": all_rows,
        "evidence": evidence,
        "foundation": foundation,
        "conclusion": conclusion,
        "flowStatus": "stopped" if stopped else "completed",
        "verificationState": verification_state,
        "onlyMultimodalSkipped": only_multimodal_skipped_state,
        "counts": counts,
        "changedFiles": changed_files,
        "baselineIssues": baseline,
        "screenshots": screenshots(evidence, om_root),
        "artifacts": artifact_paths(ledger, om_root, batch_id),
    }


def summary_model(ledger: dict[str, Any], index: dict[str, Any], om_root: Path) -> dict[str, Any]:
    if any(batch.get("status") not in {"completed", "stopped"} for batch in ledger["batches"]):
        raise ReportError("仍有未结束批次，不能生成最终汇总报告")
    batches: list[dict[str, Any]] = []
    for batch in sorted(ledger["batches"], key=lambda item: item["batchId"]):
        batch_id = batch["batchId"]
        model = batch_model(ledger, index, om_root, batch_id)
        report_name = f"adaptation-report-{safe_batch_id(batch_id)}.html"
        report_path = om_root / report_name
        if not report_path.is_file():
            raise ReportError(f"最终汇总缺少批次报告: {report_name}")
        batches.append({
            "batch": batch,
            "conclusion": model["conclusion"],
            "flowStatus": model["flowStatus"],
            "verificationState": model["verificationState"],
            "onlyMultimodalSkipped": model["onlyMultimodalSkipped"],
            "counts": model["counts"],
            "report": report_name,
            "unresolved": unresolved_items(model),
        })
    conclusion = "passed" if batches and all(
        item["conclusion"] == "passed" and item["batch"].get("status") == "completed"
        for item in batches
    ) else "failed"
    counts = {
        key: sum(item["counts"][key] for item in batches)
        for key in (
            "issues", "modified", "notModified", "blocked", "plans",
            "passed", "failed", "notVerified", "notApplicable",
        )
    }
    counts["changedFiles"] = len({
        path for issue in ledger["issues"] for path in issue.get("changedFiles", [])
    })
    states = {item["verificationState"] for item in batches}
    if "blocked" in states:
        verification_state = "blocked"
    elif "failed" in states:
        verification_state = "failed"
    elif "incomplete" in states:
        verification_state = "incomplete"
    else:
        verification_state = "passed"
    only_multimodal_skipped_state = (
        verification_state == "incomplete"
        and any(item["onlyMultimodalSkipped"] for item in batches)
        and all(
            item["verificationState"] == "passed" or item["onlyMultimodalSkipped"]
            for item in batches
        )
    )
    return {
        "kind": "summary",
        "tier": "full",
        "task": ledger["task"],
        "decisions": ledger["decisions"],
        "batches": batches,
        "conclusion": conclusion,
        "flowStatus": "completed",
        "verificationState": verification_state,
        "onlyMultimodalSkipped": only_multimodal_skipped_state,
        "counts": counts,
        "artifacts": artifact_paths(ledger, om_root, None),
    }


def screenshots(evidence: list[dict[str, Any]], om_root: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for entry in evidence:
        if entry.get("type") != "screenshot" or not isinstance(entry.get("path"), str):
            continue
        target = (om_root / entry["path"]).resolve()
        mime = mimetypes.guess_type(target.name)[0] or ""
        if mime not in IMAGE_MIMES:
            raise ReportError(f"不支持的截图格式: {entry['path']}")
        encoded = base64.b64encode(target.read_bytes()).decode("ascii")
        result.append({
            "evidenceId": entry["evidenceId"],
            "round": entry.get("round"),
            "links": entry.get("links", []),
            "src": f"data:{mime};base64,{encoded}",
        })
    return result


def artifact_paths(
    ledger: dict[str, Any], om_root: Path, batch_id: str | None
) -> list[dict[str, str]]:
    candidates: list[tuple[str, Path]] = [
        ("任务账本", om_root / "decisions.json"),
        ("证据索引", om_root / "evidence" / "index.json"),
    ]
    if batch_id:
        candidates.append(("高保真设计", om_root / "output" / "html" / f"hifi-{batch_id}.html"))
    result: list[dict[str, str]] = []
    for name, path in candidates:
        if path.is_file():
            try:
                relative = path.resolve().relative_to(om_root.resolve())
            except ValueError as error:
                raise ReportError(f"相关产物路径越出 .onemulti: {path}") from error
            result.append({"name": name, "href": relative.as_posix()})
    return result


def unresolved_items(model: dict[str, Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for issue in model["issues"]:
        statuses = {row["status"] for row in issue["planRows"]}
        if issue.get("changeStatus") == "blocked" or "failed" in statuses:
            reasons = sorted({
                human_reason(row.get("reason")) for row in issue["planRows"]
                if row["status"] == "failed" and row.get("reason")
            })
            items.append({
                "issueId": issue["issueId"],
                "component": str(issue.get("component") or issue.get("page")),
                "reason": "；".join(reasons) or str(issue.get("notChangedReason") or "仍有未闭环项"),
            })
    return items


def pending_validation_items(model: dict[str, Any]) -> list[dict[str, Any]]:
    grouped: dict[str, int] = defaultdict(int)
    for row in model["rows"]:
        if row["status"] == "not_verified":
            grouped[human_reason(row.get("reason"))] += 1
    return [
        {"reason": reason, "count": count}
        for reason, count in sorted(grouped.items())
    ]


def render(template: str, model: dict[str, Any]) -> str:
    validate_template(template)
    if model["kind"] == "batch":
        sections = render_batch(model)
        title = f"一多适配报告 · {batch_heading(model)}"
        eyebrow = f"{model['batch']['batchId']} · 批次报告"
    else:
        sections = render_summary(model)
        title = "一多适配汇总报告"
        eyebrow = "任务汇总"
    values = {
        "TITLE": esc(title),
        "EYEBROW": esc(eyebrow),
        "STATUS_CLASS": status_class(model["flowStatus"]),
        "STATUS_LABEL": esc(f"任务流程：{flow_label(model['flowStatus'])}"),
        "SUBTITLE": esc(subtitle(model)),
        "NAVIGATION": render_navigation(model),
        "METRICS": render_metrics(model),
        "CONTENT": sections,
    }
    html = template
    for key, value in values.items():
        html = html.replace("{{" + key + "}}", value)
    leftovers = re.findall(r"\{\{[A-Z_]+\}\}", html)
    if leftovers:
        raise ReportError(f"HTML 模板仍有未替换占位符: {sorted(set(leftovers))}")
    return html


def validate_template(template: str) -> None:
    required = {
        "TITLE", "EYEBROW", "STATUS_CLASS", "STATUS_LABEL", "SUBTITLE",
        "NAVIGATION", "METRICS", "CONTENT",
    }
    placeholders = set(re.findall(r"\{\{([A-Z_]+)\}\}", template))
    if placeholders != required:
        raise ReportError(
            f"HTML 模板占位符必须且只能为: {sorted(required)}；当前为 {sorted(placeholders)}"
        )
    if re.search(r"(?:https?:)?//", template, re.IGNORECASE):
        raise ReportError("HTML 模板不得引用外部网络资源")


def render_navigation(model: dict[str, Any]) -> str:
    if model["kind"] == "batch":
        sections = [
            ("结论", "#conclusion"),
            ("适配概述", "#overview"),
            ("本批修改", "#changes"),
            ("验证结果", "#validation"),
        ]
        if model["tier"] != "compact":
            sections.append(("构建与执行", "#execution"))
            if unresolved_items(model):
                sections.append(("未解决问题", "#unresolved"))
            if pending_validation_items(model):
                sections.append(("待补充验证", "#pending-validation"))
            if any(issue.get("deferredRegressions") for issue in model["issues"]):
                sections.append(("跨批次影响", "#deferred"))
            sections.append(("历史问题", "#history"))
        sections.append(("相关产物", "#artifacts"))
        links = "".join(
            f'<a href="{href}">{esc(name)}</a>' for name, href in sections
        )
        return (
            f'<h2 class="side-nav-title">{esc(model["batch"]["batchId"])} · 报告导航</h2>'
            '<div class="side-nav-content"><div class="nav-group">'
            f'<div class="nav-list">{links}</div></div></div>'
        )

    section_links = "".join(
        f'<a href="{href}">{esc(name)}</a>'
        for name, href in (
            ("任务结论", "#conclusion"),
            ("任务总览", "#task-overview"),
            ("批次总览", "#batch-overview"),
            ("未完成批次", "#incomplete-batches"),
            ("范围与决策", "#decisions"),
            ("相关产物", "#artifacts"),
        )
    )
    batch_links = "".join(
        '<a class="nav-batch" '
        f'href="{esc(item["report"])}"><span>{esc(item["batch"]["batchId"])}</span>'
        f'<small>{esc(verification_label(item["verificationState"], item))}</small></a>'
        for item in model["batches"]
    )
    return (
        '<h2 class="side-nav-title">汇总报告导航</h2><div class="side-nav-content">'
        '<div class="nav-group"><div class="nav-group-label">本页</div>'
        f'<div class="nav-list">{section_links}</div></div>'
        '<div class="nav-group"><div class="nav-group-label">批次报告</div>'
        f'<div class="nav-list">{batch_links}</div></div></div>'
    )


def batch_heading(model: dict[str, Any]) -> str:
    names: list[str] = []
    for page in model["batch"].get("pages", []):
        name = Path(str(page)).stem
        if name not in names:
            names.append(name)
    heading = "、".join(names[:3])
    if len(names) > 3:
        heading += f" 等 {len(names)} 页"
    return heading or model["batch"]["batchId"]


def subtitle(model: dict[str, Any]) -> str:
    forms = " / ".join(model["task"].get("targetForms", [])) or "未指定形态"
    if model["kind"] == "batch":
        return f"{model['task']['taskId']} · {model['batch']['batchId']} · {forms}"
    return f"{model['task']['taskId']} · {len(model['batches'])} 个批次 · {forms}"


def flow_label(status: str) -> str:
    return "已停止" if status == "stopped" else "已完成"


def only_multimodal_skipped(model: dict[str, Any]) -> bool:
    """基础检查通过，且未验证项全部来自用户跳过多模态验证。"""
    if "onlyMultimodalSkipped" in model:
        return bool(model["onlyMultimodalSkipped"])
    rows = model.get("rows", [])
    pending = [row for row in rows if row.get("status") == "not_verified"]
    return (
        model.get("verificationState") == "incomplete"
        and model.get("foundation", {}).get("status") == "passed"
        and bool(pending)
        and all(row.get("reason") == "multimodal_declined_by_user" for row in pending)
    )


def verification_label(state: str, model: dict[str, Any] | None = None) -> str:
    if model is not None and only_multimodal_skipped(model):
        return "基础验证通过"
    return {
        "passed": "验证通过",
        "incomplete": "验证未完成",
        "failed": "验证未通过",
        "blocked": "存在阻塞",
    }.get(state, state)


def verification_class(model: dict[str, Any]) -> str:
    if only_multimodal_skipped(model):
        return "passed"
    return status_class(model["verificationState"])


def render_metrics(model: dict[str, Any]) -> str:
    counts = model["counts"]
    if model["kind"] == "batch":
        pending_target = "#pending-validation" if counts["notVerified"] else "#validation"
        targets = ("#changes", "#changes", "#validation", pending_target, "#changes")
    else:
        targets = ("#batch-overview",) * 5
    items = (
        ("问题", counts["issues"]),
        ("已修改", counts["modified"]),
        ("验证项", counts["plans"]),
        ("未验证", counts["notVerified"]),
        ("修改文件", counts["changedFiles"]),
    )
    return "".join(
        f'<a class="metric" href="{target}"><strong>{value}</strong><span>{esc(name)}</span></a>'
        for (name, value), target in zip(items, targets)
    )


def conclusion_text(model: dict[str, Any]) -> str:
    counts = model["counts"]
    if model["verificationState"] == "passed":
        return "本批流程已完成，基础构建和全部适用验证项均已通过。"
    if model["verificationState"] == "blocked":
        if model["flowStatus"] == "stopped":
            return "本批流程已停止，报告保留已完成内容和未闭环项。"
        return f"本批流程已结束，但仍有 {counts['blocked']} 个问题被阻塞。"
    if model.get("foundation", {}).get("status") == "failed":
        return "本批流程已完成，但基础构建或静态检查存在失败。"
    if counts["failed"]:
        return f"本批流程已完成，基础构建通过，但仍有 {counts['failed']} 项验证失败。"
    if counts["notVerified"]:
        if only_multimodal_skipped(model):
            return "L1 构建、L2 静态检查通过；未进行多模态验证（用户跳过）。"
        foundation = "基础构建通过，" if model.get("foundation", {}).get("status") == "passed" else ""
        return f"本批流程已完成，{foundation}仍有 {counts['notVerified']} 项运行或视觉检查未验证。"
    return "本批流程已完成，但验证信息仍不完整。"


def render_batch(model: dict[str, Any]) -> str:
    batch = model["batch"]
    overview = (
        '<section class="section" id="overview"><h2>适配概述</h2>'
        f'<p><strong>范围：</strong>{esc("；".join(batch.get("pages", [])))}</p>'
        f'<p><strong>公共依赖：</strong>{esc("；".join(batch.get("dependencies", [])) or "无")}</p>'
        f'<p><strong>风险：</strong>{esc(batch.get("risk", "unknown"))}</p>'
        '</section>'
    )
    conclusion = (
        f'<section class="conclusion {status_class(model["flowStatus"])}" id="conclusion">'
        '<div class="flow-result"><span>任务流程</span>'
        f'<strong>{esc(flow_label(model["flowStatus"]))}</strong></div>'
        '<div class="verification-result"><span>验证状态</span>'
        f'<span class="badge {verification_class(model)}">'
        f'{esc(verification_label(model["verificationState"], model))}</span>'
        f'<p>{esc(conclusion_text(model))}</p></div></section>'
    )
    issues = '<section class="section" id="changes"><h2>本批修改内容</h2>' + "".join(
        render_issue(issue, model["screenshots"]) for issue in model["issues"]
    ) + '</section>'
    validation = render_validation(model)
    execution = render_execution(model)
    unresolved = render_unresolved(model)
    pending_validation = render_pending_validation(model)
    deferred = render_deferred(model["issues"])
    history = render_history(model["baselineIssues"])
    artifacts = render_artifacts(model["artifacts"])
    if model["tier"] == "compact":
        return conclusion + overview + issues + validation + artifacts
    return conclusion + overview + issues + validation + execution + unresolved + pending_validation + deferred + history + artifacts


def render_issue(issue: dict[str, Any], all_screenshots: list[dict[str, Any]]) -> str:
    rows = issue["planRows"]
    counts = defaultdict(int)
    for row in rows:
        counts[row["status"]] += 1
    files = "".join(f"<code>{esc(path)}</code>" for path in issue.get("changedFiles", []))
    screenshots_for_issue = [
        item for item in all_screenshots
        if any(link.get("issueId") == issue["issueId"] for link in item["links"])
    ]
    gallery = render_gallery(screenshots_for_issue, issue["issueId"]) if screenshots_for_issue else ""
    return (
        '<article class="issue-card">'
        '<header>'
        f'<div><span class="issue-id">{esc(issue["issueId"])}</span>'
        f'<h3>{esc(issue.get("component") or issue.get("page"))}</h3></div>'
        f'<span class="badge neutral">{esc(label(issue.get("changeStatus", "pending")))}</span>'
        '</header>'
        '<div class="compare-text">'
        '<div class="before"><h4>修改前</h4>'
        f'<p>{esc(issue.get("problem"))}</p><p class="muted">根因：{esc(issue.get("rootCause"))}</p></div>'
        '<div class="after"><h4>修改后</h4>'
        f'<p>{esc(issue.get("changeSummary") or issue.get("notChangedReason"))}</p>'
        f'<div class="file-list">{files or "<span class=\"muted\">无实际修改文件</span>"}</div></div>'
        '</div>'
        '<div class="issue-result">'
        f'验证结果：{counts["passed"]} 通过 / {counts["failed"]} 失败 / '
        f'{counts["not_verified"]} 未验证 / {counts["not_applicable"]} 不适用'
        '</div>'
        '<details><summary>查看已确认方案</summary>'
        f'<p>{esc(issue.get("proposal"))}</p></details>'
        f'{gallery}</article>'
    )


def render_gallery(items: list[dict[str, Any]], issue_id: str) -> str:
    cards = "".join(
        '<figure><img loading="lazy" '
        f'src="{item["src"]}" alt="{esc(item["evidenceId"])}">'
        f'<figcaption>{esc(item["evidenceId"])} · {esc(screenshot_check(item, issue_id))}'
        f' · round {esc(item.get("round"))}</figcaption></figure>'
        for item in items
    )
    return f'<div class="gallery"><h4>验证截图</h4><div>{cards}</div></div>'


def screenshot_check(item: dict[str, Any], issue_id: str) -> str:
    keys = sorted({
        f'{link["form"]} · {link["checkId"]}'
        for link in item.get("links", [])
        if isinstance(link, dict)
        and link.get("issueId") == issue_id
        and isinstance(link.get("form"), str)
        and isinstance(link.get("checkId"), str)
    })
    return " / ".join(keys) or issue_id


def render_validation(model: dict[str, Any]) -> str:
    show_evidence = any(row["evidenceIds"] for row in model["rows"])
    body = "".join(
        '<tr>'
        f'<td><code>{esc(row["issueId"])}</code></td><td>{esc(row["form"])}</td>'
        f'<td>{esc(row["check"])}</td>'
        f'<td><span class="badge {status_class(row["status"])}">{esc(label(row["status"]))}</span></td>'
        f'<td>{esc(human_reason(row.get("reason")))}</td>'
        + (f'<td>{esc(", ".join(row["evidenceIds"]))}</td>' if show_evidence else "")
        + '</tr>'
        for row in model["rows"]
    )
    evidence_heading = "<th>证据</th>" if show_evidence else ""
    return (
        '<section class="section" id="validation"><h2>验证结果矩阵</h2><div class="table-wrap"><table>'
        '<thead><tr><th>Issue</th><th>形态</th><th>检查内容</th><th>结果</th><th>原因</th>'
        f'{evidence_heading}</tr></thead>'
        f'<tbody>{body}</tbody></table></div></section>'
    )


def execution_result(status: str) -> str:
    return {
        "passed": "通过",
        "failed": "未通过",
        "not_verified": "未执行",
        "partial": "部分完成",
        "not_applicable": "不适用",
    }.get(status, status)


def runtime_execution_summary(model: dict[str, Any]) -> tuple[str, str]:
    counts = model["counts"]
    if counts["failed"]:
        return "failed", f'{counts["failed"]} 项运行或视觉检查失败'
    if counts["notVerified"]:
        reasons = sorted({
            human_reason(row.get("reason"))
            for row in model["rows"] if row.get("status") == "not_verified"
        } - {"—"})
        note = "；".join(reasons) or f'{counts["notVerified"]} 项检查缺少运行证据'
        if counts["passed"]:
            return "partial", f'{counts["passed"]} 项通过，{counts["notVerified"]} 项未验证；{note}'
        return "not_verified", note
    if counts["plans"] == counts["notApplicable"]:
        return "not_applicable", "本批没有适用的运行态检查"
    return "passed", f'{counts["passed"]} 项适用检查均已通过'


def render_execution(model: dict[str, Any]) -> str:
    foundation = model["foundation"]["status"]
    if foundation == "passed":
        foundation_rows = (
            ("L1 构建", ("passed", "最终构建成功")),
            ("L2 静态检查", ("passed", "静态检查无阻断问题")),
        )
    elif foundation == "failed":
        foundation_rows = ((
            "L1/L2 基础检查",
            ("failed", "构建或静态检查至少一项未通过"),
        ),)
    else:
        foundation_rows = ((
            "L1/L2 基础检查",
            ("not_verified", "没有基础检查记录"),
        ),)
    runtime = runtime_execution_summary(model)
    summary_rows = "".join(
        '<tr>'
        f'<td>{esc(name)}</td>'
        f'<td><span class="badge {status_class(status)}">{esc(execution_result(status))}</span></td>'
        f'<td>{esc(note)}</td></tr>'
        for name, (status, note) in (*foundation_rows, ("运行态验证", runtime))
    )
    return (
        '<section class="section" id="execution"><h2>构建与执行记录</h2><div class="table-wrap"><table>'
        '<thead><tr><th>检查</th><th>最终结果</th><th>说明</th></tr></thead>'
        f'<tbody>{summary_rows}</tbody></table></div></section>'
    )


def render_unresolved(model: dict[str, Any]) -> str:
    items = unresolved_items(model)
    if not items:
        return ""
    body = "".join(
        f'<li><strong>{esc(item["component"])}</strong><span>{esc(item["reason"])}</span></li>'
        for item in items
    )
    return f'<section class="section" id="unresolved"><h2>未解决问题</h2><ul class="status-list two-column">{body}</ul></section>'


def render_pending_validation(model: dict[str, Any]) -> str:
    items = pending_validation_items(model)
    if not items:
        return ""
    body = "".join(
        '<li>'
        f'<strong>{item["count"]} 项运行态检查尚未完成</strong>'
        f'<span>{esc(item["reason"])}</span></li>'
        for item in items
    )
    return f'<section class="section" id="pending-validation"><h2>待补充验证</h2><ul class="status-list two-column">{body}</ul></section>'


def render_deferred(issues: list[dict[str, Any]]) -> str:
    items = [
        {"issueId": issue["issueId"], **item}
        for issue in issues for item in issue.get("deferredRegressions", [])
    ]
    if not items:
        return ""
    body = "".join(
        '<tr>'
        f'<td>{esc(item["issueId"])}</td><td>{esc(item.get("page"))}</td>'
        f'<td>{esc(item.get("batchId"))}</td><td>{esc(item.get("reason"))}</td>'
        f'<td>{esc(item.get("suggestedCheck"))}</td></tr>'
        for item in items
    )
    return (
        '<section class="section" id="deferred"><h2>跨批次潜在影响</h2><div class="table-wrap"><table>'
        '<thead><tr><th>Issue</th><th>页面</th><th>批次</th><th>原因</th><th>建议检查</th></tr></thead>'
        f'<tbody>{body}</tbody></table></div></section>'
    )


def render_history(items: list[dict[str, Any]]) -> str:
    if not items:
        return '<section class="section" id="history"><h2>历史问题</h2><p>未发现适配前历史问题。</p></section>'
    body = "".join(
        f'<li><code>{esc(item["issueId"])}</code><span>{esc(item.get("problem"))}</span></li>'
        for item in items
    )
    return f'<section class="section" id="history"><h2>历史问题</h2><ul class="status-list">{body}</ul></section>'


def render_artifacts(items: list[dict[str, str]]) -> str:
    links = "".join(
        f'<a href="{esc(item["href"])}">{esc(item["name"])}</a>' for item in items
    )
    return f'<section class="section" id="artifacts"><h2>相关产物</h2><div class="artifact-list">{links}</div></section>'


def render_summary(model: dict[str, Any]) -> str:
    conclusion = (
        f'<section class="conclusion {status_class(model["flowStatus"])}" id="conclusion">'
        '<div class="flow-result"><span>任务流程</span>'
        f'<strong>{esc(flow_label(model["flowStatus"]))}</strong></div>'
        '<div class="verification-result"><span>总体验证状态</span>'
        f'<span class="badge {verification_class(model)}">'
        f'{esc(verification_label(model["verificationState"], model))}</span>'
        f'<p>{esc(summary_verification_text(model))}</p></div></section>'
    )
    cards = "".join(render_batch_card(item) for item in model["batches"])
    decisions = "".join(
        f'<li><code>{esc(item.get("decisionId"))}</code><span>{esc(item.get("summary"))}</span></li>'
        for item in model["decisions"]
    )
    task = model["task"]
    task_overview = (
        '<section class="section" id="task-overview"><h2>任务总览</h2>'
        f'<p><strong>适配范围：</strong>{esc("；".join(task.get("scope", [])) or "未记录")}</p>'
        f'<p><strong>目标形态：</strong>{esc(" / ".join(task.get("targetForms", [])) or "未指定")}</p>'
        f'<p><strong>任务状态：</strong>{esc(label(task.get("status", "planning")))}</p>'
        f'<p><strong>批次数量：</strong>{len(model["batches"])}</p></section>'
    )
    return (
        conclusion
        + task_overview
        + f'<section class="section" id="batch-overview"><h2>批次总览</h2><div class="batch-grid">{cards}</div></section>'
        + render_incomplete_batches(model["batches"])
        + f'<section class="section" id="decisions"><h2>已确认范围与决策</h2><ul class="status-list">{decisions or "<li>无结构决策</li>"}</ul></section>'
        + render_artifacts(model["artifacts"])
    )


def render_batch_card(item: dict[str, Any]) -> str:
    batch = item["batch"]
    counts = item["counts"]
    unresolved = len(item["unresolved"])
    return (
        f'<article class="batch-card" id="batch-{esc(safe_batch_id(batch["batchId"]))}">'
        f'<header><h3>{esc(batch["batchId"])}</h3><span class="badge {verification_class(item)}">{esc(verification_label(item["verificationState"], item))}</span></header>'
        f'<p>任务流程：{esc(flow_label(item["flowStatus"]))}</p>'
        f'<p>{counts["issues"]} 个问题 · {counts["modified"]} 个已修改 · {counts["plans"]} 项验证</p>'
        f'<p>{counts["passed"]} 通过 · {counts["failed"]} 失败 · {counts["notVerified"]} 未验证 · {unresolved} 个未闭环</p>'
        f'<a class="primary-link" href="{esc(item["report"])}">打开批次报告</a>'
        '</article>'
    )


def summary_verification_text(model: dict[str, Any]) -> str:
    counts = model["counts"]
    state = model["verificationState"]
    if state == "passed":
        return "全部批次流程均已完成，所有适用验证项均已通过。"
    if state == "failed":
        if counts["failed"] == 0:
            pending = (
                f"，仍有 {counts['notVerified']} 项运行或视觉检查未验证"
                if counts["notVerified"] else ""
            )
            return f"任务流程已完成，但基础检查未通过{pending}。"
        return f"任务流程已完成，但仍有 {counts['failed']} 项验证失败。"
    if state == "incomplete":
        if only_multimodal_skipped(model):
            return "全部批次 L1 构建、L2 静态检查通过；未进行多模态验证（用户跳过）。"
        return f"任务流程已完成，但仍有 {counts['notVerified']} 项运行或视觉检查未验证。"
    return f"任务流程已结束，但仍有 {counts['blocked']} 个问题或批次处于阻塞状态。"


def render_incomplete_batches(items: list[dict[str, Any]]) -> str:
    stopped = [item for item in items if item["batch"].get("status") == "stopped"]
    if not stopped:
        return '<section class="section" id="incomplete-batches"><h2>未完成批次</h2><p>无。</p></section>'
    body = "".join(
        '<li>'
        f'<code>{esc(item["batch"]["batchId"])}</code>'
        f'<strong>{esc(label(item["batch"].get("status", "stopped")))}</strong>'
        f'<span>{esc(item["batch"].get("risk") or "未记录停止原因")}</span>'
        '</li>'
        for item in stopped
    )
    return f'<section class="section" id="incomplete-batches"><h2>未完成批次</h2><ul class="status-list">{body}</ul></section>'
