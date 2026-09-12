#!/usr/bin/env python3
"""直接向正式 evidence 索引和账本原子登记一轮验证事实。"""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT))

from onemulti.ledger import LedgerError, add_verification, atomic_write, load_ledger  # noqa: E402


def read_json(path: str) -> Any:
    return json.load(sys.stdin) if path == "-" else json.loads(Path(path).read_text(encoding="utf-8"))


def write_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}-", suffix=".tmp", dir=path.parent)
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


def restore(path: Path, content: bytes) -> None:
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}-restore-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def plan_keys(ledger: dict[str, Any]) -> set[tuple[str, str, str]]:
    batch_id = ledger.get("task", {}).get("currentBatch")
    return {
        (issue["issueId"], plan["form"], plan["checkId"])
        for issue in ledger["issues"]
        if issue.get("batchId") == batch_id and issue.get("changeStatus") == "modified"
        for plan in issue.get("verificationPlan", [])
    }


def next_id(entries: list[dict[str, Any]]) -> str:
    used = {str(item.get("evidenceId")) for item in entries}
    number = 1
    while f"E-AUTO-{number:04d}" in used:
        number += 1
    return f"E-AUTO-{number:04d}"


def normalize_links(raw: Any, plans: set[tuple[str, str, str]], issue_ids: set[str]) -> list[dict[str, str]]:
    if not isinstance(raw, list) or not raw:
        raise LedgerError("links 必须为非空数组")
    result: list[dict[str, str]] = []
    for link in raw:
        if not isinstance(link, dict):
            raise LedgerError("link 必须为对象")
        if {"issueId", "form", "checkId"} <= set(link) and (
            link["issueId"], link["form"], link["checkId"]
        ) in plans:
            result.append({key: link[key] for key in ("issueId", "form", "checkId")})
        elif "issueId" in link and not ({"form", "checkId"} & set(link)) \
                and link["issueId"] in issue_ids:
            result.append({"issueId": link["issueId"]})
        else:
            raise LedgerError("link 必须命中已确认 issue 或 verificationPlan")
    return result


def entry(index: dict[str, Any], kind: str, round_number: int,
          links: list[dict[str, str]], *, data: dict[str, Any] | None = None,
          path: str | None = None) -> dict[str, Any]:
    value = {
        "evidenceId": next_id(index["entries"]), "type": kind,
        "round": round_number, "links": links,
    }
    value["data" if data is not None else "path"] = data if data is not None else path
    return value


def aggregate_status(statuses: list[str]) -> str:
    if "failed" in statuses:
        return "failed"
    if "not_verified" in statuses:
        return "not_verified"
    if statuses and all(status == "not_applicable" for status in statuses):
        return "not_applicable"
    if statuses and all(status in {"passed", "not_applicable"} for status in statuses):
        return "passed"
    return "not_verified"


def validate_current_batch_results(ledger: dict[str, Any]) -> None:
    """Validate only frozen Step 4 targets; global consistency belongs to Step 5."""
    batch_id = ledger.get("task", {}).get("currentBatch")
    targets = [
        issue for issue in ledger.get("issues", [])
        if issue.get("batchId") == batch_id
        and issue.get("changeStatus") == "modified"
    ]
    if not targets:
        raise LedgerError("当前已确认批次没有可校验的已修改 issue")
    for issue in targets:
        issue_id = issue["issueId"]
        planned = [(item["form"], item["checkId"]) for item in issue.get("verificationPlan", [])]
        results = issue.get("verificationResults", [])
        actual = [(item.get("form"), item.get("checkId")) for item in results]
        if len(planned) != len(set(planned)):
            raise LedgerError(f"{issue_id} 冻结计划包含重复项")
        if len(actual) != len(set(actual)) or not set(actual) <= set(planned):
            raise LedgerError(f"{issue_id} 的结果包含重复项或计划外项目")
        for result in results:
            status = result.get("status")
            reason = result.get("reason")
            if status not in {"passed", "failed", "not_verified", "not_applicable"}:
                raise LedgerError(f"{issue_id} 存在无效结果状态")
            if status != "passed" and (not isinstance(reason, str) or not reason.strip()):
                raise LedgerError(f"{issue_id} 的非 passed 结果必须包含 reason")
            if status == "passed" and reason is not None:
                raise LedgerError(f"{issue_id} 的 passed 结果 reason 必须为 null")


def normalize_result(raw: Any, plans: set[tuple[str, str, str]]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise LedgerError("result 必须为对象")
    required = {"issueId", "form", "checkId", "status"}
    if not required <= set(raw):
        raise LedgerError("result 只需 issueId/form/checkId/status，未通过时增加 reason")
    key = (raw["issueId"], raw["form"], raw["checkId"])
    if key not in plans:
        raise LedgerError("result 不属于已确认 verificationPlan")
    status = raw["status"]
    if status not in {"passed", "failed", "not_verified", "not_applicable"}:
        raise LedgerError("result status 无效")
    reason = raw.get("reason")
    if status == "passed":
        reason = None
    elif not isinstance(reason, str) or not reason.strip():
        raise LedgerError("未通过结果必须填写 reason")
    return {"issueId": key[0], "form": key[1], "checkId": key[2], "status": status, "reason": reason}


def command_record_batch(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.project).resolve()
    om = root / ".onemulti"
    index_path = om / "evidence" / "index.json"
    ledger_path = om / "decisions.json"
    ledger = load_ledger(str(ledger_path))
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if not {"schemaVersion", "taskId", "entries"} <= set(index) or index.get("schemaVersion") != 3:
        raise LedgerError("evidence/index.json 必须是 schema v3")
    if index.get("taskId") != ledger.get("task", {}).get("taskId") or not isinstance(index.get("entries"), list):
        raise LedgerError("evidence/index.json taskId 或 entries 无效")
    raw = read_json(args.input)
    if not isinstance(raw, dict) or not {"round", "commands", "artifacts", "results"} <= set(raw):
        raise LedgerError("batch 必须包含 round/commands/artifacts/results")
    round_number = raw["round"]
    if not isinstance(round_number, int) or isinstance(round_number, bool) or not 1 <= round_number <= 5:
        raise LedgerError("round 必须为 1..5")
    if not all(isinstance(raw[name], list) for name in ("commands", "artifacts", "results")):
        raise LedgerError("commands/artifacts/results 必须为数组")

    batch_id = ledger.get("task", {}).get("currentBatch")
    current_batch = next(
        (item for item in ledger.get("batches", []) if item.get("batchId") == batch_id),
        None,
    )
    if current_batch is None:
        raise LedgerError("无法从账本确定有效 task.currentBatch")
    plans = plan_keys(ledger)
    issue_ids = {
        issue["issueId"] for issue in ledger["issues"]
        if issue.get("batchId") == batch_id and issue.get("changeStatus") == "modified"
    }
    if not plans or not issue_ids:
        raise LedgerError("当前已确认批次缺少可验证的已修改 issue")
    next_index = deepcopy(index)
    added: list[str] = []
    for item in raw["commands"]:
        if not isinstance(item, dict) or not {"argv", "exitCode", "links"} <= set(item):
            raise LedgerError("command 需要 argv/exitCode/links，可选失败诊断字段")
        argv = item["argv"]
        if not isinstance(argv, list) or not argv or not all(isinstance(value, str) and value for value in argv):
            raise LedgerError("command argv 必须为非空字符串数组")
        exit_code = item["exitCode"]
        if not isinstance(exit_code, int) or isinstance(exit_code, bool):
            raise LedgerError("command exitCode 必须为整数")
        data = {"argv": argv, "exitCode": exit_code}
        for name in ("phase", "sourceSha256"):
            if item.get(name):
                data[name] = str(item[name])
        if exit_code != 0:
            reason = item.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                raise LedgerError("失败命令必须包含非空 reason")
            data["reason"] = reason.strip()
            for name in ("stdout", "stderr"):
                if item.get(name):
                    data[name] = str(item[name])
        value = entry(next_index, "command", round_number,
                      normalize_links(item["links"], plans, issue_ids), data=data)
        next_index["entries"].append(value)
        added.append(value["evidenceId"])

    for item in raw["artifacts"]:
        if not isinstance(item, dict) or not {"type", "path", "links"} <= set(item):
            raise LedgerError("artifact 只需 type/path/links")
        relative = Path(str(item["path"]))
        target = (om / relative).resolve()
        try:
            target.relative_to(om.resolve())
        except ValueError as error:
            raise LedgerError("artifact 路径越出 .onemulti") from error
        expected_dir = Path("evidence") / batch_id / f"round-{round_number}"
        if not target.is_file() or relative.parent != expected_dir:
            raise LedgerError(f"轮次产物必须已存在于 {expected_dir.as_posix()}/")
        value = entry(next_index, str(item["type"]), round_number,
                      normalize_links(item["links"], plans, issue_ids), path=relative.as_posix())
        next_index["entries"].append(value)
        added.append(value["evidenceId"])

    next_ledger = deepcopy(ledger)
    seen: set[tuple[str, str, str]] = set()
    recorded: list[str] = []
    normalized_results = [normalize_result(item, plans) for item in raw["results"]]
    for result in normalized_results:
        key = (result["issueId"], result["form"], result["checkId"])
        if key in seen:
            raise LedgerError(f"本批次包含重复 result: {'/'.join(key)}")
        seen.add(key)
        add_verification(next_ledger, result["issueId"], {
            name: result[name] for name in ("form", "checkId", "status", "reason")
        })
        recorded.append("/".join(key))

    if normalized_results:
        validate_current_batch_results(next_ledger)

    old_index, old_ledger = index_path.read_bytes(), ledger_path.read_bytes()
    try:
        write_atomic(index_path, next_index)
        atomic_write(str(ledger_path), next_ledger)
    except Exception:
        restore(index_path, old_index)
        restore(ledger_path, old_ledger)
        raise
    return {"entries": added, "results": recorded}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    command = commands.add_parser("record-batch")
    command.add_argument("project", nargs="?", default=".")
    command.add_argument("--input", default="-", help="JSON 文件；默认从 stdin 读取")
    command.set_defaults(handler=command_record_batch)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        print(json.dumps({"ok": True, **args.handler(args)}, ensure_ascii=False))
        return 0
    except (LedgerError, OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
