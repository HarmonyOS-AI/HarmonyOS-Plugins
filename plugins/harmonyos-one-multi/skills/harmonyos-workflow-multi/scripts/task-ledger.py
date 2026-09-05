#!/usr/bin/env python3
"""一多适配任务账本 CLI：安全维护 decisions.json。

所有复杂输入都通过 ``--input <json文件>`` 或 ``--input -`` 传入，
避免 Agent 在命令行里拼接 JSON。批量命令同时接受单个对象、对象数组和
``{"复数名": [...]}`` 包装对象。
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
import re
import shutil
import sys
import tempfile
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from onemulti.ledger import (  # noqa: E402
    BATCH_STATUSES,
    CHANGE_STATUSES,
    LedgerError,
    TEST_CONCLUSIONS,
    add_deferred_regression,
    add_verification,
    archive_ledger,
    atomic_write,
    batch_by_id,
    issue_by_id,
    is_bootstrap_ledger,
    load_json,
    load_ledger,
    merge_pages,
    mutate,
    new_ledger,
    normalize_batch,
    normalize_decision,
    normalize_issue,
    put_by_id,
    refresh_task_status,
    related_page_paths,
    validate_ledger,
)
from onemulti.route_map import (  # noqa: E402
    RouteMapError,
    load_route_map,
    validate_verification_routes,
)


COPYABLE_EXAMPLES = {
    "bootstrap": """可复制 JSON 示例（bootstrap.json）：
{
  "task": {
    "taskId": "one-multi-20260810-001",
    "scope": ["entry/src/main/ets/pages/Index.ets"],
    "targetForms": ["phone", "foldable", "tablet"],
    "confirmationMode": "batch",
    "currentBatch": "B01"
  },
  "decisions": [{
    "decisionId": "D-001",
    "scope": ["entry/src/main/ets/pages/Index.ets"],
    "summary": "确认页面与目标形态",
    "by": "user",
    "reason": "用户明确指定范围",
    "conflictsWith": []
  }],
  "pages": [{
    "path": "entry/src/main/ets/pages/Index.ets",
    "type": "page",
    "module": "entry",
    "dependencies": []
  }],
  "batches": [{
    "batchId": "B01",
    "pages": ["entry/src/main/ets/pages/Index.ets"],
    "dependencies": [],
    "predecessors": [],
    "domains": ["size-layout"],
    "risk": "low"
  }]
}""",
    "init": """可复制 JSON 示例（task.json）：
{"task":{"taskId":"one-multi-20260810-001","scope":["entry/src/main/ets/pages/Index.ets"],"targetForms":["phone","foldable","tablet"],"confirmationMode":"batch"}}""",
    "set-task": """可复制 JSON 示例（task-patch.json）：
{"task":{"currentBatch":"B01"}}""",
    "put-decision": """可复制 JSON 示例（decision.json）：
{"decisions":[{"decisionId":"D-001","scope":["entry/src/main/ets/pages/Index.ets"],"summary":"确认页面与目标形态","by":"user","reason":"用户明确指定范围","conflictsWith":[]}]}""",
    "merge-pages": """可复制 JSON 示例（pages.json）：
{"pages":[{"path":"entry/src/main/ets/pages/Index.ets","type":"page","module":"entry","dependencies":[]}]}""",
    "put-batch": """可复制 JSON 示例（batches.json）：
{"batches":[{"batchId":"B01","pages":["entry/src/main/ets/pages/Index.ets"],"dependencies":[],"predecessors":[],"domains":["size-layout"],"risk":"low"}]}""",
    "transition-batch": """可复制 JSON 示例（batch-patch.json）：
{"batch":{"specConfirmed":true,"status":"executing"}}
流程主路径：pending -> executing -> completed；终止时进入 stopped""",
    "put-issues": """可复制 JSON 示例（issues.json）：
{"issues":[{"issueId":"B01-UI-001","batchId":"B01","page":"entry/src/main/ets/pages/Index.ets","component":"Index","targetForms":["tablet"],"problem":"平板仍为单列","source":"task_analysis","rootCause":"未消费断点","proposal":"md+ 使用双列","plannedFiles":["entry/src/main/ets/pages/Index.ets"],"verificationPlan":[{"form":"tablet","checkId":"layout-two-column","routeId":"R-B01-INDEX","check":"平板显示双列且无截断"}]}]}""",
    "transition-issue": """可复制 JSON 示例（issue-patch.json）：
{"issue":{"changeStatus":"modified","changedFiles":["entry/src/main/ets/pages/Index.ets"],"changeSummary":"md+ 使用双列"}}""",
    "add-deferred-regression": """可复制 JSON 示例（deferred-regression.json）：
{"page":"entry/src/main/ets/pages/Home.ets","batchId":"B01","reason":"页面复用本批修改的公共组件","suggestedCheck":"检查布局和核心交互"}""",
    "put-verification": """可复制 JSON 示例（result.json）：
{"verification":{"form":"tablet","checkId":"layout-two-column","status":"passed","reason":null}}""",
}


def add_example(parser: argparse.ArgumentParser, command: str) -> None:
    parser.epilog = COPYABLE_EXAMPLES[command]
    parser.formatter_class = argparse.RawDescriptionHelpFormatter


def read_input(path: str) -> Any:
    """读取文件或标准输入中的 JSON，统一转换解析错误。"""
    if path == "-":
        try:
            return json.load(sys.stdin)
        except json.JSONDecodeError as error:
            raise LedgerError(f"标准输入 JSON 解析失败: {error}") from error
    return load_json(path)


def object_input(path: str, wrapper: str | None = None) -> dict[str, Any]:
    """读取单个对象；允许输入被 task/batch/issue 等键包裹。"""
    data = read_input(path)
    if wrapper and isinstance(data, dict) and wrapper in data:
        data = data[wrapper]
    if not isinstance(data, dict):
        raise LedgerError("输入必须是 JSON 对象")
    return data


def list_input(path: str, wrapper: str) -> list[dict[str, Any]]:
    """读取对象数组，也接受单个对象以减少 Agent 构造输入时的失误。"""
    data = read_input(path)
    if isinstance(data, dict) and wrapper in data:
        data = data[wrapper]
    elif wrapper == "pages" and isinstance(data, dict) and "path" not in data:
        data = [{"path": key, **value} for key, value in data.items() if isinstance(value, dict)]
    elif isinstance(data, dict):
        data = [data]
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise LedgerError(
            f"输入必须是单个对象、对象数组，或包含 {wrapper} 数组的对象"
        )
    return data


def cleanup_issue_input(path: str, ledger_path: str) -> None:
    """成功写入后删除 .onemulti 内的 issue 临时输入，避免形成第二份事实源。"""
    if path == "-":
        return
    candidate = os.path.realpath(path)
    om_root = os.path.realpath(os.path.dirname(os.path.abspath(ledger_path)))
    transient_roots = (os.path.join(om_root, "evidence", "tmp"),)
    if any(candidate == root or candidate.startswith(root + os.sep) for root in transient_roots):
        try:
            os.unlink(candidate)
        except FileNotFoundError:
            pass


def duplicate_issue_outputs(ledger_path: str) -> list[str]:
    """返回 output 中错误持久化的 issue 清单或状态补丁。"""
    output = os.path.join(os.path.dirname(os.path.abspath(ledger_path)), "output")
    if not os.path.isdir(output):
        return []
    pattern = re.compile(r"^issues?(?:[-_].*)?\.json$", re.IGNORECASE)
    return sorted(name for name in os.listdir(output) if pattern.fullmatch(name))


def validate_route_map(path: str, batches: list[dict[str, Any]] | None = None) -> str:
    """检查可执行 JSON 路由表，并覆盖计划中的全部批次和页面。"""
    absolute = os.path.abspath(path)
    try:
        required_batches = {
            batch["batchId"] for batch in batches or [] if isinstance(batch.get("batchId"), str)
        }
        batch_pages = {
            batch["batchId"]: set(batch.get("pages", []))
            for batch in batches or [] if isinstance(batch.get("batchId"), str)
        }
        load_route_map(
            absolute,
            required_batches=required_batches or None,
            batch_pages=batch_pages or None,
        )
    except RouteMapError as error:
        raise LedgerError(str(error)) from error
    return absolute


def require_registered_route_map(ledger_path: str, ledger: dict[str, Any]) -> None:
    """校验已登记的路由图，防止文件后来被删除或替换成空模板。"""
    if not ledger.get("batches"):
        return
    reference = ledger.get("task", {}).get("routeMap")
    if not isinstance(reference, str) or not reference:
        raise LedgerError("账本已有批次但缺少 task.routeMap；必须先生成路由图")
    if reference != "output/route-map.json":
        raise LedgerError("task.routeMap 必须是相对 .onemulti 的 output/route-map.json")
    route_path = os.path.join(os.path.dirname(os.path.abspath(ledger_path)), reference)
    validate_route_map(route_path, ledger["batches"])
    try:
        route_data = load_route_map(route_path)
        validate_verification_routes(route_data, ledger)
    except RouteMapError as error:
        raise LedgerError(str(error)) from error


def initialize_evidence_index(ledger_path: str, task_id: str) -> None:
    """为新任务原子创建外置 evidence 索引，不把证据塞回账本。"""
    evidence_dir = os.path.join(os.path.dirname(os.path.abspath(ledger_path)), "evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    destination = os.path.join(evidence_dir, "index.json")
    write_evidence_index(destination, {"schemaVersion": 3, "taskId": task_id, "entries": []})


def write_evidence_index(destination: str, index: dict[str, Any]) -> None:
    """原子写入外置 evidence 索引。"""
    evidence_dir = os.path.dirname(destination)
    os.makedirs(evidence_dir, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".index-", suffix=".tmp", dir=evidence_dir)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(index, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def command_init(args: argparse.Namespace) -> dict[str, Any]:
    task = object_input(args.input, "task")
    if os.path.exists(args.ledger):
        existing = load_json(args.ledger)
        # 首次安装已创建 task=null 的安全占位账本，可直接初始化；只有真实旧任务
        # 才要求显式归档，避免误覆盖历史确认和证据。
        if is_bootstrap_ledger(existing):
            pass
        elif not args.archive_existing:
            raise LedgerError(f"账本已存在: {args.ledger}；如需开始新任务请使用 --archive-existing")
        else:
            archive_ledger(args.ledger, args.history_root)
    ledger = new_ledger(task)
    atomic_write(args.ledger, ledger)
    initialize_evidence_index(args.ledger, ledger["task"]["taskId"])
    return ledger


def _bootstrap_pages(value: object) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [
            {"path": path, **page}
            for path, page in value.items()
            if isinstance(path, str) and isinstance(page, dict)
        ]
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return value
    raise LedgerError("bootstrap.pages 必须是页面数组或 path-keyed 对象")


def command_bootstrap(args: argparse.Namespace) -> dict[str, Any]:
    """一次性创建 task、decisions、pages、batches 和 evidence 空索引。"""
    data = object_input(args.input)
    allowed = {"task", "decisions", "pages", "batches"}
    if set(data) - allowed:
        raise LedgerError(f"bootstrap 顶层存在未知字段: {sorted(set(data) - allowed)}")
    task = data.get("task")
    if not isinstance(task, dict):
        raise LedgerError("bootstrap.task 必须是对象")
    decisions = data.get("decisions", [])
    batches = data.get("batches", [])
    if not isinstance(decisions, list) or not all(isinstance(item, dict) for item in decisions):
        raise LedgerError("bootstrap.decisions 必须是对象数组")
    if not isinstance(batches, list) or not batches or not all(isinstance(item, dict) for item in batches):
        raise LedgerError("bootstrap.batches 必须是非空对象数组")
    pages = _bootstrap_pages(data.get("pages", []))

    # 先在内存中完成全部关联和状态校验；任何输入错误都不能污染现有账本。
    ledger = new_ledger(task)
    put_by_id(ledger["decisions"], decisions, "decisionId", normalize_decision)
    merge_pages(ledger, pages)
    put_by_id(ledger["batches"], batches, "batchId", normalize_batch)
    route_map = validate_route_map(args.route_map, ledger["batches"])
    expected = os.path.realpath(os.path.join(
        os.path.dirname(os.path.abspath(args.ledger)), "output", "route-map.json"
    ))
    if os.path.realpath(route_map) != expected:
        raise LedgerError("route-map.json 必须位于 decisions.json 同级目录下的 output/route-map.json")
    ledger["task"]["routeMap"] = "output/route-map.json"
    for batch in ledger["batches"]:
        for page_path in batch["pages"]:
            if page_path in ledger["pages"]:
                ledger["pages"][page_path]["batchId"] = batch["batchId"]
    refresh_task_status(ledger)
    errors = validate_ledger(ledger)
    if errors:
        raise LedgerError("\n".join(errors))

    if os.path.exists(args.ledger):
        existing = load_json(args.ledger)
        if not is_bootstrap_ledger(existing):
            if not args.archive_existing:
                raise LedgerError(f"账本已存在: {args.ledger}；如需开始新任务请使用 --archive-existing")
            archive_ledger(args.ledger, args.history_root)
    atomic_write(args.ledger, ledger)
    initialize_evidence_index(args.ledger, ledger["task"]["taskId"])
    return ledger


def command_validate(args: argparse.Namespace) -> dict[str, Any]:
    ledger = load_ledger(args.ledger)
    duplicates = duplicate_issue_outputs(args.ledger)
    if duplicates:
        raise LedgerError(
            "output 中存在重复问题清单或状态补丁；问题唯一事实源是 decisions.json.issues[]，"
            f"请删除: {duplicates}"
        )
    require_registered_route_map(args.ledger, ledger)
    return ledger


def command_archive(args: argparse.Namespace) -> dict[str, Any]:
    ledger = load_ledger(args.ledger)
    if ledger.get("task") is None:
        raise LedgerError("空账本没有可归档的任务")
    destination = archive_ledger(args.ledger, args.history_root)
    return {"ledger": ledger, "archive": destination}


def command_set_task(args: argparse.Namespace) -> dict[str, Any]:
    """更新任务游标和配置；总体状态由批次状态自动聚合。"""
    patch = object_input(args.input, "task")
    if "status" in patch:
        raise LedgerError("task.status 由批次状态自动计算，不能通过 set-task 写入")

    def operation(ledger: dict[str, Any]) -> None:
        current = ledger["task"]
        current.update(deepcopy(patch))

    return mutate(args.ledger, operation)


def command_put_decision(args: argparse.Namespace) -> dict[str, Any]:
    """新增或按 decisionId 更新结构决策。

    这里只记录会影响后续批次或可复用的选择。普通 SPEC 是否批准只写
    ``batch.specConfirmed``，不在 decisions 中重复维护。
    """
    decisions = list_input(args.input, "decisions")
    return mutate(
        args.ledger,
        lambda ledger: put_by_id(
            ledger["decisions"], decisions, "decisionId", normalize_decision
        ),
    )


def command_merge_pages(args: argparse.Namespace) -> dict[str, Any]:
    """增量合并页面扫描结果；full-scan 时还会标记本轮消失的页面。"""
    pages = list_input(args.input, "pages")
    return mutate(args.ledger, lambda ledger: merge_pages(ledger, pages, args.full_scan))


def command_put_batch(args: argparse.Namespace) -> dict[str, Any]:
    """写入批次计划；单批和多批都强制校验 route-map.json。"""
    batches = list_input(args.input, "batches")

    def operation(ledger: dict[str, Any]) -> None:
        put_by_id(ledger["batches"], batches, "batchId", normalize_batch)
        if not args.route_map:
            raise LedgerError("写入批次计划必须提供 --route-map $OM/output/route-map.json")
        route_map = validate_route_map(args.route_map, ledger["batches"])
        expected = os.path.realpath(os.path.join(
            os.path.dirname(os.path.abspath(args.ledger)), "output", "route-map.json"
        ))
        if os.path.realpath(route_map) != expected:
            raise LedgerError("route-map.json 必须位于 decisions.json 同级目录下的 output/route-map.json")
        ledger["task"]["routeMap"] = os.path.relpath(
            route_map, os.path.dirname(os.path.abspath(args.ledger))
        )
        for batch in batches:
            batch_id = batch.get("batchId")
            for page in batch.get("pages", []):
                if page in ledger["pages"]:
                    ledger["pages"][page]["batchId"] = batch_id
        refresh_task_status(ledger)

    return mutate(args.ledger, operation)


def command_transition_batch(args: argparse.Namespace) -> dict[str, Any]:
    patch = object_input(args.input, "batch")

    def operation(ledger: dict[str, Any]) -> None:
        batch = batch_by_id(ledger, args.batch_id)
        if "specConfirmed" in patch:
            if not isinstance(patch["specConfirmed"], bool):
                raise LedgerError("batch.specConfirmed 必须是布尔值")
        if "status" in patch:
            if patch["status"] not in BATCH_STATUSES:
                raise LedgerError(f"batch.status 非法: {patch['status']}")
        if "testConclusion" in patch and patch["testConclusion"] not in TEST_CONCLUSIONS:
            raise LedgerError(f"batch.testConclusion 非法: {patch['testConclusion']}")
        batch.update(deepcopy(patch))
        refresh_task_status(ledger)

    return mutate(args.ledger, operation)


def command_put_issues(args: argparse.Namespace) -> dict[str, Any]:
    issues = list_input(args.input, "issues")
    if args.batch_id and any(issue.get("batchId") != args.batch_id for issue in issues):
        raise LedgerError("put-issues 输入包含其他批次的问题")

    def operation(ledger: dict[str, Any]) -> None:
        put_by_id(ledger["issues"], issues, "issueId", normalize_issue)
        for issue in issues:
            stored = issue_by_id(ledger, issue["issueId"])
            for page_path in related_page_paths(ledger, stored):
                page = ledger["pages"][page_path]
                if page.get("batchId") is None:
                    page["batchId"] = stored["batchId"]
        require_registered_route_map(args.ledger, ledger)

    result = mutate(args.ledger, operation)
    cleanup_issue_input(args.input, args.ledger)
    return result


def command_transition_issue(args: argparse.Namespace) -> dict[str, Any]:
    """更新问题施工状态；验证结果必须走专用命令。"""
    patch = object_input(args.input, "issue")
    allowed = {"changeStatus", "changedFiles", "changeSummary", "notChangedReason"}
    if set(patch) - allowed:
        raise LedgerError(f"transition-issue 只允许字段: {sorted(allowed)}")

    def operation(ledger: dict[str, Any]) -> None:
        issue = issue_by_id(ledger, args.issue_id)
        if "changeStatus" in patch:
            if patch["changeStatus"] not in CHANGE_STATUSES:
                raise LedgerError(f"changeStatus 非法: {patch['changeStatus']}")
        issue.update(deepcopy(patch))

    result = mutate(args.ledger, operation)
    cleanup_issue_input(args.input, args.ledger)
    return result


def command_put_verification(args: argparse.Namespace) -> dict[str, Any]:
    """幂等写入单个 form+checkId 结果。"""
    result = object_input(args.input, "verification")
    return mutate(args.ledger, lambda ledger: add_verification(ledger, args.issue_id, result))


def command_add_deferred_regression(args: argparse.Namespace) -> dict[str, Any]:
    """幂等记录当前 issue 对其他批次页面的潜在影响。"""
    item = object_input(args.input)
    return mutate(
        args.ledger,
        lambda ledger: add_deferred_regression(ledger, args.issue_id, item),
    )


def summary(ledger: dict[str, Any]) -> dict[str, Any]:
    """CLI 只输出稳定摘要，避免把完整账本重复塞回模型上下文。"""
    task = ledger.get("task") or {}
    return {
        "schemaVersion": ledger.get("schemaVersion"),
        "taskId": task.get("taskId"),
        "taskStatus": task.get("status"),
        "pages": len(ledger.get("pages", {})),
        "decisions": len(ledger.get("decisions", [])),
        "batches": len(ledger.get("batches", [])),
        "issues": len(ledger.get("issues", [])),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="初始化 schemaVersion=3 精简账本")
    init.add_argument("ledger")
    init.add_argument("--input", required=True, help="task JSON 文件，- 表示 stdin")
    init.add_argument("--archive-existing", action="store_true")
    init.add_argument("--history-root")
    init.set_defaults(handler=command_init)
    add_example(init, "init")

    bootstrap = commands.add_parser(
        "bootstrap",
        help="原子初始化 task、决策、页面和批次计划（推荐）",
        description="原子初始化完整任务计划。先在内存中校验全部引用和 route-map，成功后才写入账本。",
    )
    bootstrap.add_argument("ledger")
    bootstrap.add_argument("--input", required=True, help="包含 task/decisions/pages/batches 的 JSON 文件")
    bootstrap.add_argument("--route-map", required=True, help="已核实的 output/route-map.json")
    bootstrap.add_argument("--archive-existing", action="store_true")
    bootstrap.add_argument("--history-root")
    bootstrap.set_defaults(handler=command_bootstrap)
    add_example(bootstrap, "bootstrap")

    validate = commands.add_parser("validate", help="校验 schema、状态和引用")
    validate.add_argument("ledger")
    validate.set_defaults(handler=command_validate)

    archive = commands.add_parser("archive", help="归档账本、output 和 evidence")
    archive.add_argument("ledger")
    archive.add_argument("--history-root")
    archive.set_defaults(handler=command_archive)

    set_task = commands.add_parser("set-task", help="更新任务游标和配置")
    set_task.add_argument("ledger")
    set_task.add_argument("--input", required=True)
    set_task.set_defaults(handler=command_set_task)
    add_example(set_task, "set-task")

    decision = commands.add_parser("put-decision", help="新增或更新用户决策/模型假设")
    decision.add_argument("ledger")
    decision.add_argument(
        "--input", required=True,
        help='JSON 文件或 -；支持单个决策、决策数组、{"decisions":[...]}',
    )
    decision.set_defaults(handler=command_put_decision)
    add_example(decision, "put-decision")

    merge = commands.add_parser("merge-pages", help="增量合并 page-inventory 输出")
    merge.add_argument("ledger")
    merge.add_argument(
        "--input", required=True,
        help='JSON 文件或 -；支持单页、页面数组、{"pages":[...]} 或 path-keyed 对象',
    )
    merge.add_argument("--full-scan", action="store_true")
    merge.set_defaults(handler=command_merge_pages)
    add_example(merge, "merge-pages")

    put_batch = commands.add_parser(
        "put-batch",
        help="新增或更新批次",
        description="新增或更新批次。--input 支持单个批次、批次数组或包装对象。",
    )
    put_batch.add_argument("ledger")
    put_batch.add_argument(
        "--input", required=True,
        help='JSON 文件或 -；支持单个批次、批次数组、{"batches":[...]}',
    )
    put_batch.add_argument("--route-map", required=True, help="必填：已核实的 route-map.json")
    put_batch.set_defaults(handler=command_put_batch)
    add_example(put_batch, "put-batch")

    transition_batch = commands.add_parser("transition-batch", help="更新批次状态")
    transition_batch.add_argument("ledger")
    transition_batch.add_argument("batch_id")
    transition_batch.add_argument("--input", required=True)
    transition_batch.set_defaults(handler=command_transition_batch)
    add_example(transition_batch, "transition-batch")

    put_issues = commands.add_parser("put-issues", help="新增或更新批次问题")
    put_issues.add_argument("ledger")
    put_issues.add_argument("--batch-id")
    put_issues.add_argument(
        "--input", required=True,
        help='JSON 文件或 -；支持单个问题、问题数组、{"issues":[...]}',
    )
    put_issues.set_defaults(handler=command_put_issues)
    add_example(put_issues, "put-issues")

    transition_issue = commands.add_parser("transition-issue", help="更新问题施工状态")
    transition_issue.add_argument("ledger")
    transition_issue.add_argument("issue_id")
    transition_issue.add_argument("--input", required=True)
    transition_issue.set_defaults(handler=command_transition_issue)
    add_example(transition_issue, "transition-issue")

    deferred = commands.add_parser(
        "add-deferred-regression",
        help="记录当前问题对其他批次页面的潜在影响",
    )
    deferred.add_argument("ledger")
    deferred.add_argument("issue_id")
    deferred.add_argument("--input", required=True)
    deferred.set_defaults(handler=command_add_deferred_regression)
    add_example(deferred, "add-deferred-regression")

    verification = commands.add_parser("put-verification", help="幂等写入一个验证结果")
    verification.add_argument("ledger")
    verification.add_argument("issue_id")
    verification.add_argument("--input", required=True)
    verification.set_defaults(handler=command_put_verification)
    add_example(verification, "put-verification")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = args.handler(args)
        if args.command == "archive":
            output = {**summary(result["ledger"]), "archive": result["archive"]}
        else:
            output = summary(result)
        print(json.dumps({"ok": True, **output}, ensure_ascii=False, indent=2))
        return 0
    except LedgerError as error:
        print(json.dumps({"ok": False, "errors": str(error).splitlines()}, ensure_ascii=False, indent=2),
              file=sys.stderr)
        return 1
    except (OSError, TypeError) as error:
        print(json.dumps({"ok": False, "errors": [str(error)]}, ensure_ascii=False, indent=2),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
