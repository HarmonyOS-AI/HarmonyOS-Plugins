"""质量证据的文件校验、源码指纹与报告模型；不执行构建或设备操作。"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re

from .quality import CATALOG, aggregate, expected_checks, plan_digest

EXCLUDED = {".git", ".onemulti", ".hvigor", "build", "node_modules", "oh_modules", "__pycache__", ".dart_tool"}


def validate_quality_entry(entry: dict) -> None:
    if not isinstance(entry.get("type"), str) or entry["type"] not in {"quality_session", "quality_result"}:
        return
    data = entry.get("data")
    context = {"batchId", "sourceSha256", "planSha256", "routeSha256"}
    result_fields = {"sessionId", "status", "observation", "device", "configuration", "artifacts"}
    required = context | result_fields if entry["type"] == "quality_result" else context
    if not isinstance(data, dict) or set(data) != required:
        raise ValueError("质量证据字段不完整或包含未知字段")
    if not isinstance(data["batchId"], str) or not data["batchId"]:
        raise ValueError("质量证据缺少批次")
    for key in ("sourceSha256", "planSha256", "routeSha256"):
        if not isinstance(data[key], str) or not re.fullmatch(r"[a-f0-9]{64}", data[key]):
            raise ValueError("质量证据指纹无效")
    if entry["type"] == "quality_session":
        if entry.get("links") != []:
            raise ValueError("质量会话通过 data.batchId 关联批次")
        return
    links = entry.get("links")
    if (not isinstance(links, list) or len(links) != 1 or not isinstance(links[0], dict)
            or links[0].get("batchId") != data["batchId"] or "qualityCheckId" not in links[0]):
        raise ValueError("质量结果必须关联单个同批次检查项")
    if not isinstance(data["sessionId"], str) or not data["sessionId"]:
        raise ValueError("质量结果必须关联验证会话")
    if not isinstance(data["status"], str) or data["status"] not in {"passed", "failed", "not_verified"}:
        raise ValueError("质量结果状态非法")
    if not isinstance(data["observation"], str) or not data["observation"].strip():
        raise ValueError("质量结果缺少实际观察或未验证原因")
    if not isinstance(data["artifacts"], list):
        raise ValueError("质量证据 artifacts 必须是数组")


def source_snapshot(root: Path, om_root: Path) -> str:
    """只读哈希；保守地使任意输入变化失效，不对源码进行语义分析。"""
    digest = hashlib.sha256()
    def fail_walk(error: OSError) -> None:
        raise error

    for directory, dirs, files in os.walk(root, followlinks=False, onerror=fail_walk):
        if any((Path(directory) / d).is_symlink() for d in dirs if d not in EXCLUDED):
            raise ValueError("质量源码指纹不支持未排除的符号链接目录")
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED
                         and (Path(directory) / d).resolve() != om_root.resolve())
        for name in sorted(files):
            path = Path(directory) / name
            if name == ".DS_Store" or path.suffix in {".pyc", ".pyo"}:
                continue
            relative = path.relative_to(root).as_posix()
            digest.update(relative.encode() + b"\0")
            if path.is_symlink():
                raise ValueError(f"质量源码指纹不支持符号链接文件: {relative}")
            digest.update(file_hash(path).encode() + b"\0")
    return digest.hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_path(om_root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError("证据需要非空相对路径")
    path = (om_root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to((om_root / "evidence").resolve()) or not path.is_file():
        raise ValueError("质量证据必须是 .onemulti/evidence 内已存在的文件")
    if path.stat().st_size == 0:
        raise ValueError("质量证据不能为空文件")
    return path


def result_state(data: dict, source_sha: str, plan_sha: str, om_root: Path,
                 criterion_id: str = "") -> tuple[str, str]:
    if data.get("sourceSha256") != source_sha:
        return "not_verified", "源码已变化，需重新验证"
    if data.get("planSha256") != plan_sha:
        return "not_verified", "范围或质量计划已变化，需重新验证"
    status = data.get("status")
    if status == "not_verified":
        return status, data.get("observation", "未验证")
    if status not in {"passed", "failed"}:
        return "not_verified", "运行结果状态无效"
    if not all(isinstance(data.get(k), str) and data[k].strip() for k in ("observation", "device", "configuration")):
        return "not_verified", "缺少运行观察、设备或实际配置"
    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return "not_verified", "缺少运行证据；构建、静态分析和设计稿不能证明体验达标"
    for item in artifacts:
        try:
            if not isinstance(item, dict) or not isinstance(item.get("kind"), str) or item["kind"] not in {"runtime_screenshot", "runtime_log", "interaction_trace"}:
                raise ValueError("无效证据类型")
            if file_hash(artifact_path(om_root, item["path"])) != item.get("sha256"):
                raise ValueError("证据内容已变化")
        except (OSError, ValueError, KeyError, TypeError):
            return "not_verified", "运行证据缺失、越界或内容已变化"
    if criterion_id not in {"LAYOUT-01", "OVERLAY-01"} and not any(
        item["kind"] in {"runtime_log", "interaction_trace"} for item in artifacts
    ):
        return "not_verified", "交互、状态和专项检查需要运行日志或交互轨迹，不能仅凭静态截图"
    return status, data["observation"]


def quality_model(ledger: dict, index: dict, om_root: Path, batch_id: str | None = None) -> dict:
    config = ledger["task"].get("quality")
    if not config:
        return {"configured": False, "achievedGrade": None, "rows": []}
    task = ledger["task"]
    selected = [b for b in ledger["batches"] if batch_id is None or b["batchId"] == batch_id]
    try:
        source_sha = source_snapshot(om_root.parent, om_root)
    except (OSError, ValueError):
        source_sha = "unavailable"
    rows = []
    sessions = {e["evidenceId"]: e.get("data", {}) for e in index["entries"] if e.get("type") == "quality_session"}
    try:
        route_sha = file_hash(om_root / "output/route-map.json")
    except OSError:
        route_sha = "unavailable"
    for batch in selected:
        plans = {c["checkId"]: c for c in batch.get("qualityChecks", [])}
        # 后登记的结果覆盖同项旧结果，即使后者原本通过。
        results = {}
        for entry in index["entries"]:
            if entry.get("type") == "quality_result":
                for link in entry.get("links", []):
                    if link.get("batchId") == batch["batchId"]:
                        results[link.get("qualityCheckId")] = entry
        for base in expected_checks(task, batch):
            check = plans.get(base["checkId"])
            criterion = CATALOG[base["criterionId"]]
            status, reason, evidence_id = "not_verified", "尚未编制或执行质量检查", None
            if check and check["applicability"] == "not_applicable":
                status, reason = "not_applicable", check["reason"]
            elif check and base["checkId"] in results:
                entry = results[base["checkId"]]
                data = entry.get("data", {})
                session = sessions.get(data.get("sessionId"))
                context = {"batchId": batch["batchId"], "sourceSha256": source_sha,
                           "planSha256": plan_digest(task, batch), "routeSha256": route_sha}
                if not session or any(data.get(k) != v or session.get(k) != v for k, v in context.items()):
                    status, reason = "not_verified", "验证会话、源码、计划或路由已失效，需重新验证"
                else:
                    status, reason = result_state(data, source_sha, context["planSha256"], om_root, base["criterionId"])
                evidence_id = entry["evidenceId"]
            if batch.get("status") == "stopped":
                status, reason = "not_verified", "批次已停止"
            elif not batch.get("specConfirmed"):
                status, reason = "not_verified", "质量计划尚未随 SPEC 确认"
            rows.append({**base, "batchId": batch["batchId"], "grade": criterion["grade"],
                         "title": criterion["title"], "enhancement": criterion["applicability"],
                         "status": status, "reason": reason, "evidenceId": evidence_id})
    result = {"configured": True, **config, "rows": rows,
              "scope": sorted({p for b in selected for p in b["pages"]}),
              "forms": sorted(set(task["targetForms"])),
              **aggregate(rows, config["targetGrade"], config["enhancements"])}
    # 空批次和未分配的页面不能从全任务评级中消失。
    if not selected or any(not b["pages"] for b in selected) or (batch_id is None and set(ledger["pages"]) != set(result["scope"])):
        result.update(achievedGrade=None, targetMet=False, coverageWarning="页面范围为空或存在未分配页面")
    result["byForm"] = [{"form": form, **aggregate([r for r in rows if r["form"] == form],
                                                   config["targetGrade"], config["enhancements"])}
                        for form in result["forms"]]
    return result
