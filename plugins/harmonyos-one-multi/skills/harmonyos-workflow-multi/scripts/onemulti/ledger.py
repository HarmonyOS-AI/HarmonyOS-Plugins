"""一多适配任务账本的校验、结果聚合和原子写入。"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
import re
import shutil
import tempfile
from typing import Any, Callable

DEFAULT_TARGET_FORMS = ("phone", "foldable", "tablet")


SCHEMA_VERSION = 3
TASK_STATUSES = {"planning", "executing", "completed"}
BATCH_STATUSES = {"pending", "executing", "completed", "stopped"}
CHANGE_STATUSES = {"pending", "modified", "not_modified", "blocked"}
VERIFY_STATUSES = {"not_verified", "passed", "failed", "not_applicable"}
TEST_CONCLUSIONS = {"not_run", "passed", "failed"}
CONFIRMATION_MODES = {"batch", "aggregate"}
TASK_FIELDS = {
    "taskId", "scope", "targetForms", "confirmationMode",
    "routeMap", "status", "currentBatch",
}
BATCH_FIELDS = {
    "batchId", "pages", "dependencies", "predecessors", "domains",
    "risk", "status", "specConfirmed", "testConclusion", "hifiRequired",
}
ISSUE_FIELDS = {
    "issueId", "batchId", "page", "component", "domain", "affectedPages",
    "targetForms", "problem", "source", "rootCause", "proposal", "plannedFiles",
    "verificationPlan", "changeStatus", "verificationResults", "changedFiles",
    "changeSummary", "notChangedReason", "introducedByBatch", "deferredRegressions",
}
DEFERRED_REGRESSION_FIELDS = {"page", "batchId", "reason", "suggestedCheck"}
ISSUE_SOURCES = {"baseline", "task_analysis", "execution_found", "batch_regression"}
# 决策来源只区分“用户明确确认”和“无法交互时的最小假设”。
# 不允许使用含糊的 agent/system 值，避免把模型自己的选择伪装成人工确认。
DECISION_AUTHORS = {"user", "assumed"}
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class LedgerError(ValueError):
    """账本输入或结构校验错误。"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def generated_task_id() -> str:
    return datetime.now(timezone.utc).strftime("one-multi-%Y%m%d-%H%M%S")


def _is_string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _objects(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, dict) for item in value)


def normalize_task(task: dict[str, Any] | None = None) -> dict[str, Any]:
    """补齐任务级默认字段；一多任务未限定设备时覆盖默认三设备。"""
    result = deepcopy(task or {})
    result.setdefault("taskId", generated_task_id())
    result.setdefault("scope", [])
    if not result.get("targetForms"):
        result["targetForms"] = list(DEFAULT_TARGET_FORMS)
    result.setdefault("confirmationMode", "batch")
    result.setdefault("routeMap", None)
    # Task 总体状态只由批次状态聚合，初始化输入不能预设或覆盖。
    result["status"] = "planning"
    result.setdefault("currentBatch", None)
    return result


def new_ledger(task: dict[str, Any] | None = None) -> dict[str, Any]:
    """创建空账本。后续所有增量都必须经 CLI 原子写入。"""
    return {
        "schemaVersion": SCHEMA_VERSION,
        "task": normalize_task(task),
        "decisions": [],
        "pages": {},
        "batches": [],
        "issues": [],
    }


def is_bootstrap_ledger(data: object) -> bool:
    """判断是否为安装器创建、尚未绑定任务的空账本。

    安装器会预创建 ``task=null`` 的 schemaVersion=3 文件。只有其余集合
    全为空时才允许视为安全占位，防止把已有任务数据误当成空账本覆盖。
    """
    return (
        isinstance(data, dict)
        and data.get("schemaVersion") == SCHEMA_VERSION
        and data.get("task") is None
        and data.get("decisions") == []
        and data.get("pages") == {}
        and data.get("batches") == []
        and data.get("issues") == []
        and set(data) == {"schemaVersion", "task", "decisions", "pages", "batches", "issues"}
    )


def normalize_page(item: dict[str, Any], existing: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
    """把页面扫描结果标准化，同时保留已有的人工分类。"""
    path = item.get("path")
    if not isinstance(path, str) or not path:
        raise LedgerError("页面缺少非空 path")
    page = deepcopy(existing or {})
    for key, value in item.items():
        if key != "path" and not (key == "type" and value is None and page.get("type") is not None):
            page[key] = deepcopy(value)
    page.setdefault("type", None)
    page.setdefault("module", None)
    page.setdefault("dependencies", [])
    page.setdefault("batchId", None)
    page["missingFromScan"] = False
    page.pop("missingReason", None)
    return path, page


def normalize_batch(item: dict[str, Any]) -> dict[str, Any]:
    """为批次补齐交付要求、执行和测试状态。"""
    batch = deepcopy(item)
    batch.setdefault("pages", [])
    batch.setdefault("dependencies", [])
    batch.setdefault("predecessors", [])
    batch.setdefault("domains", [])
    batch.setdefault("risk", "unknown")
    batch.setdefault("status", "pending")
    batch.setdefault("specConfirmed", False)
    # 这是用户的高保真交付要求，不表示 HTML 已生成或已确认。
    batch.setdefault("hifiRequired", False)
    batch.setdefault("testConclusion", "not_run")
    return batch


def normalize_issue(item: dict[str, Any]) -> dict[str, Any]:
    """为问题 SPEC 补齐施工状态及验证容器。"""
    issue = deepcopy(item)
    issue.setdefault("component", None)
    issue.setdefault("affectedPages", [])
    issue.setdefault("targetForms", [])
    issue.setdefault("source", "task_analysis")
    issue.setdefault("plannedFiles", [])
    issue.setdefault("verificationPlan", [])
    issue.setdefault("changeStatus", "pending")
    issue.setdefault("verificationResults", [])
    issue.setdefault("changedFiles", [])
    issue.setdefault("changeSummary", None)
    issue.setdefault("notChangedReason", None)
    issue.setdefault("introducedByBatch", None)
    issue.setdefault("deferredRegressions", [])
    return issue


def normalize_decision(item: dict[str, Any]) -> dict[str, Any]:
    """补齐一条结构决策的非业务默认字段。

    ``summary/reason/by`` 不设默认值：缺失时必须让校验失败，不能由工具
    悄悄推断。``scope`` 为空表示任务级决策；页面级决策应写完整页面路径。
    """
    decision = deepcopy(item)
    decision.setdefault("scope", [])
    decision.setdefault("conflictsWith", [])
    decision.setdefault("createdAt", utc_now())
    return decision


def verification_status(issue: dict[str, Any]) -> str:
    # 未施工的问题没有可验证的改动；即使 SPEC 中保留了原验证计划，
    # 也不要求为其补造验证结果。
    if issue.get("changeStatus") == "not_modified" and not issue.get("verificationResults"):
        return "not_applicable"
    plan = issue.get("verificationPlan")
    results = issue.get("verificationResults")
    if not isinstance(plan, list) or not plan:
        return "not_verified"
    if not isinstance(results, list):
        return "not_verified"
    result_map = {
        (result.get("form"), result.get("checkId")): result
        for result in results if isinstance(result, dict)
    }
    statuses: list[str] = []
    for item in plan:
        if not isinstance(item, dict):
            return "not_verified"
        result = result_map.get((item.get("form"), item.get("checkId")))
        if result is None:
            return "not_verified"
        status = result.get("status")
        if status not in VERIFY_STATUSES:
            return "not_verified"
        statuses.append(status)
    if "failed" in statuses:
        return "failed"
    if "not_verified" in statuses:
        return "not_verified"
    if statuses and all(status == "not_applicable" for status in statuses):
        return "not_applicable"
    return "passed"


def related_page_paths(ledger: dict[str, Any], issue: dict[str, Any]) -> set[str]:
    """返回问题直接页面及恰好命中页面账本的受影响/计划/实改文件。"""
    pages = ledger.get("pages") if isinstance(ledger.get("pages"), dict) else {}
    candidates: list[object] = [issue.get("page")]
    for key in ("affectedPages", "plannedFiles", "changedFiles"):
        value = issue.get(key)
        if isinstance(value, list):
            candidates.extend(value)
    return {path for path in candidates if isinstance(path, str) and path in pages}


def aggregate_test_conclusion(ledger: dict[str, Any]) -> str:
    """从全部批次实时计算任务测试结论，不写入 task。"""
    conclusions = [
        batch.get("testConclusion", "not_run")
        for batch in ledger.get("batches", []) if isinstance(batch, dict)
    ]
    if "failed" in conclusions:
        return "failed"
    if conclusions and all(value == "passed" for value in conclusions):
        return "passed"
    return "not_run"


def derive_task_status(ledger: dict[str, Any]) -> str:
    """根据全部批次状态计算任务总体进度，不修改账本。"""
    statuses = [
        batch.get("status")
        for batch in ledger.get("batches", [])
        if isinstance(batch, dict)
    ]
    if not statuses or all(status == "pending" for status in statuses):
        return "planning"
    if all(status in {"completed", "stopped"} for status in statuses):
        return "completed"
    return "executing"


def refresh_task_status(ledger: dict[str, Any]) -> str:
    """根据全部批次状态刷新任务总体进度，并返回刷新后的值。"""
    task = ledger.get("task")
    if not isinstance(task, dict):
        raise LedgerError("task 必须是对象")
    status = derive_task_status(ledger)
    task["status"] = status
    return status


def _validate_task(task: object, errors: list[str]) -> None:
    if not isinstance(task, dict):
        errors.append("task 必须是对象")
        return
    if set(task) != TASK_FIELDS:
        errors.append(f"task 字段必须且只能是: {sorted(TASK_FIELDS)}")
    if not isinstance(task.get("taskId"), str) or not SAFE_ID.fullmatch(task.get("taskId", "")):
        errors.append("task.taskId 只能包含字母、数字、点、下划线和连字符")
    if not _is_string_list(task.get("scope")):
        errors.append("task.scope 必须是字符串数组")
    if not _is_string_list(task.get("targetForms")):
        errors.append("task.targetForms 必须是字符串数组")
    if task.get("confirmationMode") not in CONFIRMATION_MODES:
        errors.append("task.confirmationMode 只能是 batch/aggregate")
    if task.get("routeMap") is not None and (
        not isinstance(task.get("routeMap"), str) or not task.get("routeMap")
    ):
        errors.append("task.routeMap 必须是非空字符串或 null")
    if task.get("status") not in TASK_STATUSES:
        errors.append(f"task.status 非法: {task.get('status')}")
    if task.get("currentBatch") is not None and not isinstance(task.get("currentBatch"), str):
        errors.append("task.currentBatch 必须是字符串或 null")


def validate_ledger(ledger: object) -> list[str]:
    """校验完整账本的结构、字段取值和跨对象引用。"""
    errors: list[str] = []
    if not isinstance(ledger, dict):
        return ["账本顶层必须是 JSON 对象"]
    if ledger.get("schemaVersion") != SCHEMA_VERSION:
        errors.append(f"schemaVersion 必须为 {SCHEMA_VERSION}")
    task = ledger.get("task")
    if task is None:
        if not is_bootstrap_ledger(ledger):
            errors.append("task=null 只允许用于安装器创建的全空账本")
    else:
        _validate_task(task, errors)
    expected_top = {"schemaVersion", "task", "decisions", "pages", "batches", "issues"}
    if set(ledger) != expected_top:
        errors.append(f"账本顶层字段必须且只能是: {sorted(expected_top)}")
    for key in ("decisions", "batches", "issues"):
        if not _objects(ledger.get(key)):
            errors.append(f"{key} 必须是对象数组")
    # decisions 是可复用的结构选择，不承担 issue 的施工状态。
    decisions = ledger.get("decisions") if isinstance(ledger.get("decisions"), list) else []
    decision_ids: set[str] = set()
    for index, decision in enumerate(decisions):
        if not isinstance(decision, dict):
            continue
        decision_id = decision.get("decisionId")
        if not isinstance(decision_id, str) or not SAFE_ID.fullmatch(decision_id):
            errors.append(f"decisions[{index}].decisionId 格式非法")
            continue
        if decision_id in decision_ids:
            errors.append(f"重复 decisionId: {decision_id}")
        decision_ids.add(decision_id)
        if decision.get("by") not in DECISION_AUTHORS:
            errors.append(f"decisions[{decision_id}].by 只能是 user/assumed")
        if not isinstance(decision.get("summary"), str) or not decision.get("summary"):
            errors.append(f"decisions[{decision_id}].summary 必须是非空字符串")
        if not isinstance(decision.get("createdAt"), str) or not decision.get("createdAt"):
            errors.append(f"decisions[{decision_id}].createdAt 必须是非空字符串")
        for key in ("scope", "conflictsWith"):
            if not _is_string_list(decision.get(key, [])):
                errors.append(f"decisions[{decision_id}].{key} 必须是字符串数组")
    for decision in decisions:
        if not isinstance(decision, dict):
            continue
        for conflict in decision.get("conflictsWith", []):
            if conflict not in decision_ids:
                errors.append(
                    f"decisions[{decision.get('decisionId')}] 引用不存在的冲突决策: {conflict}"
                )

    pages = ledger.get("pages")
    if not isinstance(pages, dict) or not all(isinstance(k, str) and isinstance(v, dict) for k, v in pages.items()):
        errors.append("pages 必须是以页面路径为 key 的对象")
        pages = {}

    for path, page in pages.items():
        if not _is_string_list(page.get("dependencies", [])):
            errors.append(f"pages[{path}].dependencies 必须是字符串数组")

    batches = ledger.get("batches") if isinstance(ledger.get("batches"), list) else []
    batch_ids: set[str] = set()
    for index, batch in enumerate(batches):
        if not isinstance(batch, dict):
            continue
        batch_id = batch.get("batchId")
        if not isinstance(batch_id, str) or not SAFE_ID.fullmatch(batch_id):
            errors.append(f"batches[{index}].batchId 格式非法")
            continue
        if batch_id in batch_ids:
            errors.append(f"重复 batchId: {batch_id}")
        batch_ids.add(batch_id)
        unknown_batch_fields = set(batch) - BATCH_FIELDS
        if unknown_batch_fields:
            errors.append(f"batches[{batch_id}] 存在未知字段: {sorted(unknown_batch_fields)}")
        for key in ("pages", "dependencies", "predecessors", "domains"):
            if not _is_string_list(batch.get(key, [])):
                errors.append(f"batches[{batch_id}].{key} 必须是字符串数组")
        for page in batch.get("pages", []):
            if page not in pages:
                errors.append(f"batches[{batch_id}] 引用不存在的页面: {page}")
        if batch.get("status") not in BATCH_STATUSES:
            errors.append(f"batches[{batch_id}].status 非法: {batch.get('status')}")
        if not isinstance(batch.get("specConfirmed"), bool):
            errors.append(f"batches[{batch_id}].specConfirmed 必须是布尔值")
        if not isinstance(batch.get("hifiRequired", False), bool):
            errors.append(f"batches[{batch_id}].hifiRequired 必须是布尔值")
        if batch.get("testConclusion") not in TEST_CONCLUSIONS:
            errors.append(f"batches[{batch_id}].testConclusion 非法: {batch.get('testConclusion')}")

    for batch in batches:
        if not isinstance(batch, dict):
            continue
        for predecessor in batch.get("predecessors", []):
            if predecessor not in batch_ids:
                errors.append(f"batches[{batch.get('batchId')}] 前置批次不存在: {predecessor}")
    for path, page in pages.items():
        page_batch = page.get("batchId")
        if page_batch is not None and page_batch not in batch_ids:
            errors.append(f"pages[{path}].batchId 引用不存在的批次: {page_batch}")
    for batch in batches:
        if not isinstance(batch, dict):
            continue
        for path in batch.get("pages", []):
            if path in pages and pages[path].get("batchId") != batch.get("batchId"):
                errors.append(
                    f"pages[{path}].batchId={pages[path].get('batchId')}，"
                    f"与 batches[{batch.get('batchId')}].pages 不一致"
                )

    task = ledger.get("task") if isinstance(ledger.get("task"), dict) else {}
    current = task.get("currentBatch")
    if current is not None and current not in batch_ids:
        errors.append(f"task.currentBatch 不存在: {current}")
    if task and task.get("status") in TASK_STATUSES:
        expected_status = derive_task_status(ledger)
        if task.get("status") != expected_status:
            errors.append(
                f"task.status 应由批次状态聚合为 {expected_status}，"
                f"当前为 {task.get('status')}"
            )

    issue_ids: set[str] = set()
    issues = ledger.get("issues") if isinstance(ledger.get("issues"), list) else []
    for index, issue in enumerate(issues):
        if not isinstance(issue, dict):
            continue
        issue_id = issue.get("issueId")
        if not isinstance(issue_id, str) or not SAFE_ID.fullmatch(issue_id):
            errors.append(f"issues[{index}].issueId 格式非法")
            continue
        if issue_id in issue_ids:
            errors.append(f"重复 issueId: {issue_id}")
        issue_ids.add(issue_id)
        unknown_issue_fields = set(issue) - ISSUE_FIELDS
        if unknown_issue_fields:
            errors.append(f"issues[{issue_id}] 存在未知字段: {sorted(unknown_issue_fields)}")
        batch_id = issue.get("batchId")
        page = issue.get("page")
        if batch_id not in batch_ids:
            errors.append(f"issues[{issue_id}] 引用不存在的批次: {batch_id}")
        if page not in pages:
            errors.append(f"issues[{issue_id}] 引用不存在的页面: {page}")
        elif pages[page].get("batchId") != batch_id:
            errors.append(
                f"issues[{issue_id}].page 的 batchId={pages[page].get('batchId')}，"
                f"应为 {batch_id}"
            )
        for key in ("problem", "rootCause", "proposal"):
            if not isinstance(issue.get(key), str) or not issue.get(key):
                errors.append(f"issues[{issue_id}].{key} 必须是非空字符串")
        for key in ("targetForms", "plannedFiles", "affectedPages", "changedFiles"):
            if not _is_string_list(issue.get(key, [])):
                errors.append(f"issues[{issue_id}].{key} 必须是字符串数组")
        if issue.get("source") not in ISSUE_SOURCES:
            errors.append(f"issues[{issue_id}].source 非法: {issue.get('source')}")
        if issue.get("changeStatus") not in CHANGE_STATUSES:
            errors.append(f"issues[{issue_id}].changeStatus 非法: {issue.get('changeStatus')}")
        if issue.get("changeStatus") == "modified":
            if not issue.get("changedFiles") or not issue.get("changeSummary"):
                errors.append(f"issues[{issue_id}] modified 必须有 changedFiles/changeSummary")
        if issue.get("changeStatus") in {"not_modified", "blocked"} and not issue.get("notChangedReason"):
            errors.append(
                f"issues[{issue_id}] {issue.get('changeStatus')} 必须有 notChangedReason"
            )

        deferred = issue.get("deferredRegressions", [])
        if not _objects(deferred):
            errors.append(f"issues[{issue_id}].deferredRegressions 必须是对象数组")
            deferred = []
        deferred_keys: set[tuple[object, object]] = set()
        for item in deferred:
            if set(item) != DEFERRED_REGRESSION_FIELDS:
                errors.append(
                    f"issues[{issue_id}] deferredRegressions 条目必须只含 "
                    "page/batchId/reason/suggestedCheck"
                )
                continue
            if not all(isinstance(item.get(key), str) and item.get(key) for key in DEFERRED_REGRESSION_FIELDS):
                errors.append(f"issues[{issue_id}] deferredRegressions 条目字段必须为非空字符串")
                continue
            deferred_key = (item["page"], item["batchId"])
            if deferred_key in deferred_keys:
                errors.append(
                    f"issues[{issue_id}] 重复延后回归页面: {item['batchId']}+{item['page']}"
                )
            deferred_keys.add(deferred_key)
            if item["batchId"] == batch_id:
                errors.append(f"issues[{issue_id}] deferredRegressions 只能记录其他批次页面")
            if item["batchId"] not in batch_ids:
                errors.append(
                    f"issues[{issue_id}] deferredRegressions 引用不存在的批次: {item['batchId']}"
                )
            if item["page"] not in pages:
                errors.append(
                    f"issues[{issue_id}] deferredRegressions 引用不存在的页面: {item['page']}"
                )
            elif pages[item["page"]].get("batchId") != item["batchId"]:
                errors.append(
                    f"issues[{issue_id}] deferredRegressions 页面 {item['page']} 的 batchId="
                    f"{pages[item['page']].get('batchId')}，应为 {item['batchId']}"
                )

        plan = issue.get("verificationPlan")
        results = issue.get("verificationResults")
        if not _objects(plan):
            errors.append(f"issues[{issue_id}].verificationPlan 必须是对象数组")
            plan = []
        if not _objects(results):
            errors.append(f"issues[{issue_id}].verificationResults 必须是对象数组")
            results = []
        if issue.get("changeStatus") == "not_modified" and results:
            errors.append(f"issues[{issue_id}] not_modified 不得包含验证结果")
        plan_keys: set[tuple[object, object]] = set()
        for item in plan:
            key = (item.get("form"), item.get("checkId"))
            if not all(
                isinstance(value, str) and value
                for value in (*key, item.get("routeId"), item.get("check"))
            ):
                errors.append(f"issues[{issue_id}] verificationPlan 缺少 form/checkId/routeId/check")
            elif key in plan_keys:
                errors.append(f"issues[{issue_id}] 重复验证计划: {key[0]}+{key[1]}")
            plan_keys.add(key)
        result_keys: set[tuple[object, object]] = set()
        for result in results:
            key = (result.get("form"), result.get("checkId"))
            if set(result) != {"form", "checkId", "status", "reason"}:
                errors.append(f"issues[{issue_id}] 验证结果必须只含 form/checkId/status/reason")
            if key not in plan_keys:
                errors.append(f"issues[{issue_id}] 存在计划外验证结果: {key[0]}+{key[1]}")
            if key in result_keys:
                errors.append(f"issues[{issue_id}] 重复验证结果: {key[0]}+{key[1]}")
            result_keys.add(key)
            status = result.get("status")
            if status not in VERIFY_STATUSES:
                errors.append(f"issues[{issue_id}] 验证结果状态非法: {status}")
            if (status == "passed") != (result.get("reason") is None):
                errors.append(f"issues[{issue_id}] {status} 的 reason 与状态不一致")
        for related_path in related_page_paths(ledger, issue):
            related_batch = pages[related_path].get("batchId")
            if related_batch != batch_id:
                errors.append(
                    f"issues[{issue_id}] 关联页面 {related_path} 的 batchId={related_batch}，"
                    f"应为 {batch_id}"
                )

    return errors


def load_json(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except OSError as error:
        raise LedgerError(f"无法读取 {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise LedgerError(f"JSON 解析失败 {path}: {error}") from error


def load_ledger(path: str) -> dict[str, Any]:
    data = load_json(path)
    errors = validate_ledger(data)
    if errors:
        raise LedgerError("\n".join(errors))
    return data


def atomic_write(path: str, ledger: dict[str, Any]) -> None:
    """同目录写临时文件并原子替换，保证失败时原账本保持不变。"""
    errors = validate_ledger(ledger)
    if errors:
        raise LedgerError("\n".join(errors))
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".decisions-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(ledger, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        parsed = load_json(temporary)
        errors = validate_ledger(parsed)
        if errors:
            raise LedgerError("\n".join(errors))
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def mutate(path: str, operation: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    """所有写命令的统一入口：先加载有效账本，再修改、聚合并原子落盘。"""
    ledger = load_ledger(path)
    updated = deepcopy(ledger)
    operation(updated)
    atomic_write(path, updated)
    return updated


def merge_pages(ledger: dict[str, Any], items: list[dict[str, Any]], full_scan: bool = False) -> None:
    pages = ledger["pages"]
    seen: set[str] = set()
    for item in items:
        path, page = normalize_page(item, pages.get(item.get("path")))
        pages[path] = page
        seen.add(path)
    if full_scan:
        for path, page in pages.items():
            # 只处理曾由页面扫描发现的条目；手动加入的公共组件
            # 本来就不会出现在 page-inventory 输出中，不能误标为消失。
            if path not in seen and (page.get("kind") is not None or page.get("confidence") is not None):
                page["missingFromScan"] = True
                page["missingReason"] = "待确认：页面已从全量扫描消失"


def put_by_id(items: list[dict[str, Any]], incoming: list[dict[str, Any]], key: str,
              normalizer: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
    positions = {item.get(key): index for index, item in enumerate(items)}
    for raw in incoming:
        value = raw.get(key)
        if not isinstance(value, str) or not value:
            raise LedgerError(f"输入缺少非空 {key}")
        if value in positions:
            merged = {**items[positions[value]], **deepcopy(raw)}
            normalized = normalizer(merged)
            items[positions[value]] = normalized
        else:
            normalized = normalizer(raw)
            positions[value] = len(items)
            items.append(normalized)


def issue_by_id(ledger: dict[str, Any], issue_id: str) -> dict[str, Any]:
    for issue in ledger["issues"]:
        if issue.get("issueId") == issue_id:
            return issue
    raise LedgerError(f"找不到 issueId: {issue_id}")


def batch_by_id(ledger: dict[str, Any], batch_id: str) -> dict[str, Any]:
    for batch in ledger["batches"]:
        if batch.get("batchId") == batch_id:
            return batch
    raise LedgerError(f"找不到 batchId: {batch_id}")


def add_verification(ledger: dict[str, Any], issue_id: str, raw: dict[str, Any]) -> None:
    issue = issue_by_id(ledger, issue_id)
    if issue.get("changeStatus") == "not_modified":
        raise LedgerError("not_modified 不进入验证；结论由账本派生为 not_applicable")
    form, check_id = raw.get("form"), raw.get("checkId")
    plan = next(
        (item for item in issue["verificationPlan"]
         if item.get("form") == form and item.get("checkId") == check_id),
        None,
    )
    if plan is None:
        raise LedgerError(f"计划中不存在验证项: {form}+{check_id}")
    if set(raw) != {"form", "checkId", "status", "reason"}:
        raise LedgerError("验证结果必须且只能包含 form/checkId/status/reason")
    if raw.get("status") not in VERIFY_STATUSES:
        raise LedgerError(f"验证结果状态非法: {raw.get('status')}")
    if (raw.get("status") == "passed") != (raw.get("reason") is None):
        raise LedgerError("passed 的 reason 必须为 null，其他状态必须填写 reason")
    result = deepcopy(raw)
    key = (form, check_id)
    positions = {
        (item.get("form"), item.get("checkId")): index
        for index, item in enumerate(issue["verificationResults"])
    }
    if key in positions:
        issue["verificationResults"][positions[key]] = result
    else:
        issue["verificationResults"].append(result)


def add_deferred_regression(ledger: dict[str, Any], issue_id: str, raw: dict[str, Any]) -> None:
    """幂等记录第四步发现的跨批次潜在影响。"""
    if set(raw) != DEFERRED_REGRESSION_FIELDS:
        raise LedgerError(
            "延后回归条目必须且只能包含 page/batchId/reason/suggestedCheck"
        )
    if not all(isinstance(raw.get(key), str) and raw.get(key) for key in DEFERRED_REGRESSION_FIELDS):
        raise LedgerError("延后回归条目字段必须为非空字符串")
    issue = issue_by_id(ledger, issue_id)
    current_batch = ledger.get("task", {}).get("currentBatch")
    if issue.get("batchId") != current_batch:
        raise LedgerError("只能为当前批次 issue 记录延后回归")
    item = deepcopy(raw)
    key = (item["page"], item["batchId"])
    issue.setdefault("deferredRegressions", [])
    positions = {
        (value.get("page"), value.get("batchId")): index
        for index, value in enumerate(issue["deferredRegressions"])
    }
    if key in positions:
        issue["deferredRegressions"][positions[key]] = item
    else:
        issue["deferredRegressions"].append(item)


def reset_task_outputs(path: str) -> list[str]:
    """开始新任务前清理工程内的旧产物；是否为新任务由 Agent 判断。

    只接受专用 .onemulti 目录，避免误删工程或 Skill 源码。保留安装的运行资源，
    其余账本、证据、报告、扫描结果和临时输入全部清理；符号链接只删除链接本身。
    """
    ledger_path = os.path.abspath(path)
    om_root = os.path.dirname(ledger_path)
    if (os.path.basename(ledger_path) != "decisions.json"
            or os.path.basename(om_root) != ".onemulti"
            or os.path.islink(om_root) or os.path.islink(ledger_path)):
        raise LedgerError("reset 只允许清理工程内非符号链接的 .onemulti/decisions.json")
    preserved = {"SKILL.md", "assets", "references", "scripts", ".git"}
    removed: list[str] = []
    for name in sorted(os.listdir(om_root)):
        if name in preserved:
            continue
        target = os.path.join(om_root, name)
        if os.path.islink(target) or not os.path.isdir(target):
            os.unlink(target)
        else:
            shutil.rmtree(target)
        removed.append(target)
    return removed
