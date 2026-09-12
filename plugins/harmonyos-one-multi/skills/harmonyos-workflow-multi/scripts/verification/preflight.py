#!/usr/bin/env python3
"""Run the ordered Step 4 preflight with a compact schema-v3 evidence state."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT))
from onemulti.route_map import RouteMapError, load_route_map  # noqa: E402

STATE_EVIDENCE_ID = "E-PREFLIGHT"
PUBLIC_MODES = {"FULL", "STATIC_ONLY", "STOPPED"}
LICENSE_ACCEPTED_MESSAGE = "Emulator license agreements are already accepted."
LICENSE_NON_INTERACTIVE_MESSAGE = "requires an interactive terminal"
SNAPSHOT_EXCLUDED = {".git", ".onemulti", ".hvigor", "build", "node_modules", "oh_modules"}
ROUTE_MAP_LEDGER_PATH = "output/route-map.json"
ROUTE_MAP_PROJECT_PATH = Path(".onemulti/output/route-map.json")
VERIFICATION_PATH = Path(".onemulti/references/verification.md")


def write_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".preflight-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def location(project: str) -> tuple[Path, Path, Path]:
    root = Path(project).resolve()
    om = root / ".onemulti"
    return root, om / "evidence" / "index.json", om / "decisions.json"


def digest_json(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def source_snapshot(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in SNAPSHOT_EXCLUDED for part in relative.parts) or not path.is_file():
            continue
        digest.update(relative.as_posix().encode())
        digest.update(b"\0")
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def selected_issues(ledger: dict[str, Any], batch_id: str | None = None) -> list[dict[str, Any]]:
    current = batch_id or ledger.get("task", {}).get("currentBatch")
    return [
        issue for issue in ledger.get("issues", [])
        if isinstance(issue, dict) and issue.get("batchId") == current
        and issue.get("changeStatus") == "modified"
    ]


def plan_snapshot(issues: list[dict[str, Any]]) -> list[dict[str, str]]:
    plans = [
        {"issueId": issue["issueId"], **{key: plan[key] for key in ("form", "checkId", "routeId", "check")}}
        for issue in issues for plan in issue.get("verificationPlan", [])
    ]
    return sorted(plans, key=lambda item: (item["issueId"], item["form"], item["checkId"]))


def validate_boundary(ledger: dict[str, Any]) -> tuple[str, list[dict[str, Any]], list[dict[str, str]]]:
    if not isinstance(ledger, dict) or ledger.get("schemaVersion") != 3:
        raise ValueError("decisions.json 顶层结构或 schemaVersion 无效")
    task, batches = ledger.get("task"), ledger.get("batches")
    if not isinstance(task, dict) or not isinstance(batches, list) or not isinstance(ledger.get("issues"), list):
        raise ValueError("decisions.json 缺少 task/batches/issues")
    batch_id = task.get("currentBatch")
    current_batch = next(
        (item for item in batches if isinstance(item, dict) and item.get("batchId") == batch_id),
        None,
    )
    if not isinstance(batch_id, str) or current_batch is None:
        raise ValueError("无法从账本确定有效 task.currentBatch")
    # 批次确认与流程状态由 Agent 维护，不据此阻断补测或恢复任务。
    issues = selected_issues(ledger, batch_id)
    if not issues:
        raise ValueError("当前已确认批次缺少已修改的问题边界")
    for issue in issues:
        if not isinstance(issue.get("issueId"), str) or not issue["issueId"]:
            raise ValueError("当前批次存在无效 issueId")
        for name in ("plannedFiles", "changedFiles"):
            value = issue.get(name)
            if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
                raise ValueError(f"{issue['issueId']} 缺少有效 {name}")
        plans = issue.get("verificationPlan")
        if not isinstance(plans, list) or not plans:
            raise ValueError(f"{issue['issueId']} 缺少冻结 verificationPlan")
        for plan in plans:
            if not isinstance(plan, dict) or not {"form", "checkId", "routeId", "check"} <= set(plan) or not all(
                isinstance(plan[field], str) and plan[field].strip() for field in plan
            ):
                raise ValueError(f"{issue['issueId']} verificationPlan 结构无效")
    plans = plan_snapshot(issues)
    keys = [(item["issueId"], item["form"], item["checkId"]) for item in plans]
    if len(keys) != len(set(keys)):
        raise ValueError("当前批次 verificationPlan 包含重复计划项")
    return batch_id, issues, plans


def validate_route(root: Path, ledger: dict[str, Any], batch_id: str,
                   plans: list[dict[str, str]]) -> str:
    if ledger["task"].get("routeMap") != ROUTE_MAP_LEDGER_PATH:
        raise ValueError(f"task.routeMap 必须为 {ROUTE_MAP_LEDGER_PATH}")
    path = (root / ROUTE_MAP_PROJECT_PATH).resolve()
    batch_pages = {
        item["batchId"]: set(item.get("pages", [])) for item in ledger["batches"]
        if isinstance(item, dict) and isinstance(item.get("batchId"), str)
    }
    try:
        route = load_route_map(str(path), required_batches={batch_id}, batch_pages=batch_pages)
    except RouteMapError as error:
        raise ValueError(str(error)) from error
    routes = {item["routeId"]: item for item in route["routes"]}
    invalid = [
        f"{item['issueId']}/{item['form']}/{item['checkId']}" for item in plans
        if item["routeId"] not in routes or routes[item["routeId"]]["batchId"] != batch_id
    ]
    if invalid:
        raise ValueError(f"当前批次 verificationPlan 存在缺失或跨批次 routeId: {invalid}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state_entry(index: dict[str, Any]) -> dict[str, Any] | None:
    return next((item for item in index.get("entries", []) if item.get("evidenceId") == STATE_EVIDENCE_ID), None)


def save_state(path: Path, index: dict[str, Any], links: list[dict[str, str]], data: dict[str, Any]) -> None:
    value = {"evidenceId": STATE_EVIDENCE_ID, "type": "preflight_state", "round": None,
             "links": links, "data": data}
    entries = index["entries"]
    for offset, item in enumerate(entries):
        if item.get("evidenceId") == STATE_EVIDENCE_ID:
            entries[offset] = value
            break
    else:
        entries.append(value)
    write_atomic(path, index)


def read_context(project: str) -> tuple[
    Path, Path, dict[str, Any], dict[str, Any], list[dict[str, str]], dict[str, Any]
]:
    root, index_path, ledger_path = location(project)
    index = json.loads(index_path.read_text(encoding="utf-8"))
    entry = state_entry(index)
    if entry is None or not isinstance(entry.get("data"), dict):
        raise ValueError("尚未通过 route gate；先执行 preflight.py begin")
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    data = entry["data"]
    issues = selected_issues(ledger, data.get("batchId"))
    plans = plan_snapshot(issues)
    links = [{"issueId": issue["issueId"]} for issue in issues]
    if (ledger.get("task", {}).get("currentBatch") != data.get("batchId")
            or digest_json(plans) != data.get("planSha256") or entry.get("links") != links):
        raise ValueError("冻结 verificationPlan 或当前批次已在 preflight 期间改变")
    return root, index_path, index, ledger, plans, data


def update_state(index_path: Path, index: dict[str, Any], data: dict[str, Any],
                 *, mode: str, stage: str, reason: str | None = None,
                 device: dict[str, str] | None = None) -> str:
    data.update({"mode": mode, "stage": stage})
    if reason:
        data["reason"] = reason
    else:
        data.pop("reason", None)
    if device is not None:
        data["device"] = device
    entry = state_entry(index)
    save_state(index_path, index, entry["links"] if entry else [], data)
    return mode


def test_scope_estimate_minutes(plans: list[dict[str, str]]) -> int:
    """Return the transient AskQuestion estimate without persisting it as evidence."""
    return 5 + (len(plans) + 1) // 2


def read_protocol(args: argparse.Namespace) -> dict[str, Any]:
    root, _, ledger_path = location(args.project)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    batch_id = ledger.get("task", {}).get("currentBatch")
    if not isinstance(batch_id, str) or not batch_id:
        raise ValueError("无法从账本确定有效 task.currentBatch")
    document = (root / VERIFICATION_PATH).read_text(encoding="utf-8")
    verification_sha = hashlib.sha256(document.encode()).hexdigest()
    return {
        "mode": "STOPPED", "stage": "verification_read", "next": "begin",
        "batchId": batch_id, "verificationSha256": verification_sha,
        "document": document,
    }


def begin(args: argparse.Namespace) -> dict[str, Any]:
    root, index_path, ledger_path = location(args.project)
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if not {"schemaVersion", "taskId", "entries"} <= set(index) or index.get("schemaVersion") != 3:
        raise ValueError("evidence/index.json 必须是 schema v3")
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    batch_id = ledger.get("task", {}).get("currentBatch")
    issues = selected_issues(ledger, batch_id)
    plans = plan_snapshot(issues)
    try:
        batch_id, issues, plans = validate_boundary(ledger)
        if index.get("taskId") != ledger.get("task", {}).get("taskId"):
            raise ValueError("evidence/index.json taskId 与账本不一致")
        source_sha = source_snapshot(root)
        # 构建和静态检查是验证结果，不是进入验证阶段的资格门禁。
        # 缺失或失败时由 run-foundation 补跑，并在本批修复循环中处理。
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        links = [{"issueId": issue["issueId"]} for issue in issues if issue.get("issueId")]
        failed = {
            "batchId": batch_id if isinstance(batch_id, str) else "unknown",
            "mode": "STOPPED", "stage": "boundary_failed",
            "planSha256": digest_json(plans) if plans else None,
            "sourceSha256": None, "routeSha256": None,
            "reason": str(error),
        }
        save_state(index_path, index, links, failed)
        raise
    links = [{"issueId": issue["issueId"]} for issue in issues]
    try:
        route_sha = validate_route(root, ledger, batch_id, plans)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        failed = {
            "batchId": batch_id, "mode": "STATIC_ONLY", "stage": "route_failed",
            "planSha256": digest_json(plans), "sourceSha256": source_sha,
            "routeSha256": None, "reason": str(error),
        }
        save_state(index_path, index, links, failed)
        return {"mode": "STATIC_ONLY", "stage": "route_failed", "next": None,
                "batchId": batch_id, "issues": len(issues), "plans": len(plans),
                "reason": str(error)}
    data = {"batchId": batch_id, "mode": "STATIC_ONLY", "stage": "route_validated",
            "planSha256": digest_json(plans), "sourceSha256": source_sha,
            "routeSha256": route_sha}
    save_state(index_path, index, links, data)
    return {"mode": data["mode"], "stage": data["stage"], "next": "record-multimodal",
            "batchId": batch_id, "issues": len(issues), "plans": len(plans)}


def record_multimodal(args: argparse.Namespace) -> dict[str, Any]:
    root, path, index, _, plans, data = read_context(args.project)
    previous_stage = data["stage"]
    if previous_stage not in {"route_validated", "multimodal_reprobe_required"}:
        raise ValueError("多模态探测只能在 begin 门禁通过后或用户确认重试后执行")
    image = root / ".onemulti" / "assets" / "verification" / "startIcon.png"
    if not image.is_file():
        raise ValueError("多模态探测图片不存在")
    if args.available and args.description.strip():
        if previous_stage == "multimodal_reprobe_required":
            update_state(path, index, data, mode="STATIC_ONLY", stage="multimodal_approved")
            return {
                "mode": "STATIC_ONLY",
                "stage": "multimodal_approved",
                "next": "prepare-device",
            }
        update_state(path, index, data, mode="STOPPED", stage="test_scope_confirmation_required")
        return {
            "mode": "STOPPED",
            "stage": "test_scope_confirmation_required",
            "next": "ask-test-scope",
            "testScopeEstimateMinutes": test_scope_estimate_minutes(plans),
        }
    update_state(path, index, data, mode="STOPPED", stage="multimodal_retry_confirmation_required",
                 reason="multimodal_probe_failed")
    # 选项卡会保持当前轮运行；切换模型需要 Agent 用文字提示并结束当前轮。
    return {
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


def record_test_scope(args: argparse.Namespace) -> dict[str, Any]:
    _, path, index, _, _, data = read_context(args.project)
    previous_stage = data["stage"]
    if previous_stage not in {
        "test_scope_confirmation_required", "multimodal_retry_confirmation_required",
    }:
        raise ValueError("测试范围只能在多模态探测后由用户确认")
    if args.choice == "basic_and_multimodal":
        if previous_stage == "multimodal_retry_confirmation_required":
            update_state(path, index, data, mode="STOPPED", stage="multimodal_reprobe_required")
            return {
                "mode": "STOPPED",
                "stage": "multimodal_reprobe_required",
                "next": "record-multimodal",
            }
        update_state(path, index, data, mode="STATIC_ONLY", stage="multimodal_approved")
        return {
            "mode": "STATIC_ONLY",
            "stage": "multimodal_approved",
            "next": "prepare-device",
        }
    update_state(path, index, data, mode="STATIC_ONLY", stage="multimodal_declined",
                 reason="multimodal_declined_by_user")
    return {
        "mode": "STATIC_ONLY",
        "stage": "multimodal_declined",
        "next": "record-static-only-results",
        "reason": "multimodal_declined_by_user",
    }


def check_license(args: argparse.Namespace) -> str:
    _, path, index, _, _, data = read_context(args.project)
    if data["stage"] == "license_accepted" and not data.get("device"):
        return "STATIC_ONLY"
    if data["stage"] not in {"multimodal_approved", "license_attention_required"} or data.get("device"):
        raise ValueError("License gate 只能在用户确认多模交互测试后、设备绑定前执行")
    executable, status = shutil.which(args.devecocli), "probe_error"
    if executable:
        try:
            result = subprocess.run([executable, "emulator", "license"], stdin=subprocess.DEVNULL,
                                    text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    timeout=60, check=False)
            output = "\n".join(part for part in (result.stdout, result.stderr) if part)
            if result.returncode == 0 and LICENSE_ACCEPTED_MESSAGE in output:
                status = "accepted"
            elif LICENSE_NON_INTERACTIVE_MESSAGE in output:
                status = "not_accepted"
        except (OSError, subprocess.TimeoutExpired):
            pass
    if status == "accepted":
        return update_state(path, index, data, mode="STATIC_ONLY", stage="license_accepted")
    return update_state(path, index, data, mode="STOPPED", stage="license_attention_required",
                        reason=f"emulator_license_{status}")


def skip_emulator(args: argparse.Namespace) -> str:
    _, path, index, _, _, data = read_context(args.project)
    if data["stage"] != "license_attention_required" or data.get("device"):
        raise ValueError("只能在 License 未通过且用户选择跳过时结束模拟器分支")
    return update_state(path, index, data, mode="STATIC_ONLY", stage="emulator_skipped",
                        reason="emulator_license_not_accepted")


def normalize_device(payload: Any, _plans: list[dict[str, str]]) -> dict[str, str]:
    required = {"kind", "identifier"}
    if not isinstance(payload, dict) or not required <= set(payload) \
            or payload.get("kind") not in {"physical", "emulator"}:
        raise ValueError("设备绑定必须包含 kind/identifier")
    if not isinstance(payload.get("identifier"), str) or not payload["identifier"].strip():
        raise ValueError("设备 identifier 无效")
    return {"kind": payload["kind"], "identifier": payload["identifier"].strip()}


def bind_device(args: argparse.Namespace) -> str:
    _, path, index, _, plans, data = read_context(args.project)
    if data.get("device") is not None:
        raise ValueError("唯一设备已经绑定")
    device = normalize_device(json.loads(Path(args.input).read_text(encoding="utf-8")), plans)
    if data["stage"] not in {
        "multimodal_approved", "license_attention_required", "license_accepted",
    }:
        raise ValueError("设备只能在用户确认测试范围后绑定")
    return update_state(path, index, data, mode="FULL", stage="device_ready", device=device)


def confirm_capabilities(args: argparse.Namespace) -> str:
    _, path, index, _, _, data = read_context(args.project)
    if data["stage"] != "device_ready" or not data.get("device"):
        raise ValueError("设备能力尚未在绑定时确认")
    return "FULL"


def status(args: argparse.Namespace) -> str:
    _, _, _, _, _, data = read_context(args.project)
    mode = data.get("mode")
    if mode not in PUBLIC_MODES:
        raise ValueError("preflight 状态包含无效 mode")
    return mode


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    read_cmd = commands.add_parser("read-protocol")
    read_cmd.add_argument("project", nargs="?", default=".")
    read_cmd.set_defaults(handler=read_protocol)
    begin_cmd = commands.add_parser("begin")
    begin_cmd.add_argument("project", nargs="?", default=".")
    begin_cmd.set_defaults(handler=begin)
    modal = commands.add_parser("record-multimodal")
    modal.add_argument("project", nargs="?", default=".")
    modal.add_argument("--available", action="store_true")
    modal.add_argument("--description", default="")
    modal.set_defaults(handler=record_multimodal)
    scope = commands.add_parser("record-test-scope")
    scope.add_argument("project", nargs="?", default=".")
    scope.add_argument("--choice", required=True, choices=("basic_and_multimodal", "basic_only"))
    scope.set_defaults(handler=record_test_scope)
    license_cmd = commands.add_parser("check-license")
    license_cmd.add_argument("project", nargs="?", default=".")
    license_cmd.add_argument("--devecocli", default="devecocli")
    license_cmd.set_defaults(handler=check_license)
    skip = commands.add_parser("skip-emulator")
    skip.add_argument("project", nargs="?", default=".")
    skip.set_defaults(handler=skip_emulator)
    device = commands.add_parser("bind-device")
    device.add_argument("project", nargs="?", default=".")
    device.add_argument("--input", required=True)
    device.set_defaults(handler=bind_device)
    capability = commands.add_parser("confirm-capabilities")
    capability.add_argument("project", nargs="?", default=".")
    capability.set_defaults(handler=confirm_capabilities)
    status_cmd = commands.add_parser("status")
    status_cmd.add_argument("project", nargs="?", default=".")
    status_cmd.set_defaults(handler=status)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        response = args.handler(args)
        mode = response.get("mode") if isinstance(response, dict) else response
        if mode not in PUBLIC_MODES:
            raise ValueError("内部 preflight mode 无效")
        if args.command == "read-protocol" and isinstance(response, dict):
            metadata = dict(response)
            print(metadata.pop("document").rstrip())
            print(json.dumps(metadata, ensure_ascii=False))
        else:
            print(json.dumps(response, ensure_ascii=False) if isinstance(response, dict) else response)
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"preflight: {error}", file=sys.stderr)
        print("STOPPED")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
