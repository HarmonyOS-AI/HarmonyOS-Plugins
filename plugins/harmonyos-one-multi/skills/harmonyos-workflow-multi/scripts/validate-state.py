#!/usr/bin/env python3
"""校验工程内一多适配账本、证据索引及二者关联关系。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from onemulti.ledger import validate_ledger as validate_core_ledger  # noqa: E402
from onemulti.route_map import (  # noqa: E402
    RouteMapError,
    load_route_map,
    validate_verification_routes,
)


RESULT_STATUSES = {"not_verified", "passed", "failed", "not_applicable"}
COMMON_EVIDENCE_FIELDS = {"evidenceId", "type", "round", "links"}
ROUTE_MAP_PROJECT_PATH = Path(".onemulti/output/route-map.json")
ROUTE_MAP_LEDGER_PATH = "output/route-map.json"


def fail(message: str) -> None:
    raise ValueError(message)


def load_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path} 顶层必须是对象")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def validate_route_map(path_value: str, project: Path, ledger: dict) -> tuple[str, str]:
    """校验唯一 JSON 路由文件，并核对冻结验证计划引用。"""
    candidate = Path(path_value)
    expected = (project / ROUTE_MAP_PROJECT_PATH).resolve()
    if candidate.is_absolute():
        route_path = candidate
    elif candidate.as_posix() == ROUTE_MAP_LEDGER_PATH:
        route_path = project / ROUTE_MAP_PROJECT_PATH
    else:
        route_path = project / candidate
    route_path = route_path.resolve()
    try:
        relative = route_path.relative_to(project.resolve())
    except ValueError as error:
        raise ValueError(f"路由表路径越出工程根目录: {route_path}") from error
    if route_path != expected:
        fail(f"路由表必须位于工程根目录下的 {ROUTE_MAP_PROJECT_PATH.as_posix()}: {relative}")
    registered = ledger.get("task", {}).get("routeMap")
    if registered is not None and registered != ROUTE_MAP_LEDGER_PATH:
        fail(
            f"task.routeMap 必须保存相对 .onemulti 的路径 {ROUTE_MAP_LEDGER_PATH}: "
            f"{registered}"
        )
    if not route_path.is_file():
        fail(f"路由表文件不存在: {relative}")
    batches = [item for item in ledger.get("batches", []) if isinstance(item, dict)]
    batch_pages = {
        item["batchId"]: set(item.get("pages", []))
        for item in batches if isinstance(item.get("batchId"), str)
    }
    try:
        route_data = load_route_map(
            str(route_path),
            required_batches=set(batch_pages),
            batch_pages=batch_pages,
        )
    except RouteMapError as error:
        fail(str(error))
    try:
        validate_verification_routes(route_data, ledger)
    except RouteMapError as error:
        fail(str(error))
    return relative.as_posix(), sha256(route_path)


def validate_ledger(ledger: dict) -> tuple[
    str,
    dict[tuple[str, str, str], dict],
    set[str],
    dict[str, str],
    set[str],
    dict[tuple[str, str, str], str],
]:
    core_errors = validate_core_ledger(ledger)
    if core_errors:
        fail("账本结构、聚合或终态不一致: " + "; ".join(core_errors))
    expected = {"schemaVersion", "task", "decisions", "pages", "batches", "issues"}
    if set(ledger) != expected or ledger.get("schemaVersion") != 3:
        fail("decisions.json 顶层结构或 schemaVersion 无效")
    task = ledger.get("task")
    if not isinstance(task, dict) or not task.get("taskId"):
        fail("decisions.json 缺少 task.taskId")
    issues = ledger.get("issues")
    if not isinstance(issues, list):
        fail("decisions.json issues 必须是数组")

    plans: dict[tuple[str, str, str], dict] = {}
    result_statuses: dict[tuple[str, str, str], str] = {}
    issue_ids: set[str] = set()
    issue_batches: dict[str, str] = {}
    decision_ids = {
        item.get("decisionId") for item in ledger.get("decisions", [])
        if isinstance(item, dict) and item.get("decisionId")
    }
    for issue in issues:
        if not isinstance(issue, dict) or not issue.get("issueId"):
            fail("issues 中存在无效对象")
        issue_id = issue["issueId"]
        if issue_id in issue_ids:
            fail(f"重复 issueId: {issue_id}")
        issue_ids.add(issue_id)
        issue_batches[issue_id] = issue["batchId"]
        plan = issue.get("verificationPlan")
        results = issue.get("verificationResults")
        if not isinstance(plan, list) or not isinstance(results, list):
            fail(f"{issue_id} 的 verificationPlan/verificationResults 必须是数组")
        issue_plan_keys: set[tuple[str, str]] = set()
        for item in plan:
            if not isinstance(item, dict) or set(item) != {"form", "checkId", "routeId", "check"}:
                fail(f"{issue_id} 的 verificationPlan 条目结构无效")
            local_key = (item["form"], item["checkId"])
            key = (issue_id, *local_key)
            if local_key in issue_plan_keys or key in plans:
                fail(f"重复计划项: {'/'.join(key)}")
            issue_plan_keys.add(local_key)
            plans[key] = item

        seen_results: set[tuple[str, str]] = set()
        for result in results:
            if not isinstance(result, dict) or set(result) != {"form", "checkId", "status", "reason"}:
                fail(f"{issue_id} 的 verificationResults 必须只含四个字段")
            local_key = (result["form"], result["checkId"])
            if local_key not in issue_plan_keys or local_key in seen_results:
                fail(f"{issue_id} 存在计划外或重复验证结果: {'/'.join(local_key)}")
            seen_results.add(local_key)
            status = result["status"]
            if status not in RESULT_STATUSES:
                fail(f"{issue_id} 存在无效结果状态: {status}")
            if (status == "passed") != (result["reason"] is None):
                fail(f"{issue_id}/{local_key[0]}/{local_key[1]} 的 reason 与状态不一致")
            result_statuses[(issue_id, result["form"], result["checkId"])] = status

    return task["taskId"], plans, issue_ids, issue_batches, decision_ids, result_statuses


def validate_index(
    index: dict,
    om_root: Path,
    task_id: str,
    plans: dict[tuple[str, str, str], dict],
    issue_ids: set[str],
    issue_batches: dict[str, str],
    decision_ids: set[str],
    result_statuses: dict[tuple[str, str, str], str],
) -> tuple[set[tuple[str, str, str, str]], set[str]]:
    allowed_top = {"schemaVersion", "taskId", "entries"}
    if not allowed_top <= set(index) or index.get("schemaVersion") != 3:
        fail("evidence 索引顶层结构或 schemaVersion 无效")
    if index.get("taskId") != task_id or not isinstance(index.get("entries"), list):
        fail("evidence 索引 taskId 不一致或 entries 无效")

    evidence_ids: set[str] = set()
    indexed_paths: set[str] = set()
    coverage: set[tuple[str, str, str, str]] = set()
    for entry in index["entries"]:
        if not isinstance(entry, dict):
            fail("evidence entries 中存在非对象")
        evidence_id = entry.get("evidenceId")
        if not evidence_id or evidence_id in evidence_ids:
            fail(f"evidenceId 缺失或重复: {evidence_id}")
        evidence_ids.add(evidence_id)
        if not COMMON_EVIDENCE_FIELDS <= set(entry) or (("data" in entry) == ("path" in entry)):
            fail(f"{evidence_id} 必须包含公共字段且只能选择 data 或 path")
        if not isinstance(entry["links"], list):
            fail(f"{evidence_id}.links 必须是数组")
        if not isinstance(entry.get("type"), str) or not entry["type"]:
            fail(f"{evidence_id}.type 必须是非空字符串")
        if entry["round"] is not None and (
            not isinstance(entry["round"], int) or isinstance(entry["round"], bool)
            or not 1 <= entry["round"] <= 5
        ):
            fail(f"{evidence_id}.round 必须为 null 或 1..5")
        if "data" in entry and not isinstance(entry["data"], dict):
            fail(f"{evidence_id}.data 必须是对象")
        if entry["type"] == "command" and "data" in entry:
            data = entry["data"]
            if not isinstance(data.get("argv"), list) or not isinstance(data.get("exitCode"), int):
                fail(f"{evidence_id}.data 缺少 argv/exitCode")
            if data["exitCode"] == 0 and any(name in data for name in ("reason", "stdout", "stderr")):
                fail(f"{evidence_id} 成功命令不得保存 reason/stdout/stderr")

        if entry["type"] == "preflight_state":
            required = {
                "batchId", "mode", "stage", "planSha256", "sourceSha256", "routeSha256"
            }
            data = entry.get("data")
            if not isinstance(data, dict) or not required <= set(data):
                fail(f"{evidence_id} preflight_state 结构无效")
            if entry["round"] is not None:
                fail(f"{evidence_id}.round 必须为 null")

        path_value = entry.get("path")
        if path_value is not None:
            if not isinstance(path_value, str) or not path_value:
                fail(f"{evidence_id}.path 必须是非空字符串")
            relative = Path(path_value)
            target = (om_root / relative).resolve()
            try:
                target.relative_to(om_root.resolve())
            except ValueError as error:
                raise ValueError(f"{evidence_id} path 路径越界") from error
            linked_batches = {
                issue_batches[link["issueId"]]
                for link in entry["links"]
                if isinstance(link, dict) and link.get("issueId") in issue_batches
            }
            if len(linked_batches) > 1:
                fail(f"{evidence_id} path 不能同时链接多个批次: {sorted(linked_batches)}")
            expected_parents: set[Path] = set()
            if linked_batches:
                batch_id = next(iter(linked_batches))
                expected_parents.add(Path("evidence") / batch_id / f"round-{entry['round']}")
            if entry["round"] is None or relative.parent not in expected_parents or not target.is_file():
                expected = ", ".join(sorted(path.as_posix() for path in expected_parents))
                fail(f"{evidence_id} path 必须是对应轮次目录下已有文件 ({expected}): {relative}")
            indexed_paths.add(relative.as_posix())

        for link in entry["links"]:
            if not isinstance(link, dict) or not link:
                fail(f"{evidence_id} 存在无效 link")
            if "decisionId" in link and link["decisionId"] not in decision_ids:
                fail(f"{evidence_id} 引用了不存在的 decisionId")
            l3_link = any(field in link for field in ("form", "checkId"))
            if l3_link:
                if not {"issueId", "form", "checkId"} <= set(link):
                    fail(f"{evidence_id} 的计划项 link 必须包含 issueId/form/checkId")
                key = (link["issueId"], link["form"], link["checkId"])
                if link["issueId"] not in issue_ids or key not in plans:
                    fail(f"{evidence_id} 引用了不存在的计划项: {'/'.join(key)}")
                coverage.add((*key, entry["type"]))
            elif "issueId" in link:
                if link["issueId"] not in issue_ids:
                    fail(f"{evidence_id} 引用了不存在的 issueId")

    # 只校验已登记证据；额外日志、截图不参与结论，也不阻断批次收尾。
    return coverage, indexed_paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", default=".", help="HarmonyOS 工程根目录")
    parser.add_argument(
        "--route-map",
        help=(
            "前置校验使用的路由表；接受工程相对路径 .onemulti/output/route-map.json，"
            "或账本相对路径 output/route-map.json"
        ),
    )
    args = parser.parse_args()
    project = Path(args.project).resolve()
    om_root = project / ".onemulti"
    ledger_path = om_root / "decisions.json"
    index_path = om_root / "evidence" / "index.json"
    try:
        ledger = load_object(ledger_path)
        task_id, plans, issue_ids, issue_batches, decision_ids, result_statuses = validate_ledger(ledger)
        validate_index(
            load_object(index_path), om_root, task_id, plans, issue_ids, issue_batches, decision_ids,
            result_statuses,
        )
        route_result = validate_route_map(args.route_map, project, ledger) if args.route_map else None
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"INVALID: {error}", file=sys.stderr)
        return 2
    result = {"status": "valid", "mode": "formal", "taskId": task_id, "plans": len(plans)}
    if route_result:
        result.update({"routeMap": route_result[0], "routeSha256": route_result[1]})
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
