"""可执行 route-map.json 的共享校验器。"""

from __future__ import annotations

import json
import os
from typing import Any


class RouteMapError(ValueError):
    """路由表结构或引用无效。"""


TOP_FIELDS = {"schemaVersion", "routes", "unresolved"}
ROUTE_FIELDS = {"routeId", "batchId", "targetPage", "steps"}
COMMON_STEP_FIELDS = {"stepId", "action", "desc", "expectPage"}
ACTION_FIELDS = {
    "launch": {"target"},
    "tap": {"locator"},
    "swipe": {"direction", "distance"},
    "input": {"locator", "value"},
    "back": set(),
    "wait": {"timeoutMs"},
}
LOCATOR_FIELDS = {"by", "value"}
LOCATOR_TYPES = {"text", "id", "type"}
DIRECTIONS = {"up", "down", "left", "right"}
DISTANCES = {"short", "medium", "long"}
PLACEHOLDERS = ("TODO", "TBD", "待规划", "<route", "<page", "<页面")


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _check_placeholders(value: object, location: str = "route-map") -> None:
    if isinstance(value, str):
        if any(marker.lower() in value.lower() for marker in PLACEHOLDERS):
            raise RouteMapError(f"{location} 含占位内容: {value}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _check_placeholders(item, f"{location}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            _check_placeholders(item, f"{location}.{key}")


def _validate_locator(value: object, location: str) -> None:
    if not isinstance(value, dict) or set(value) != LOCATOR_FIELDS:
        raise RouteMapError(f"{location} 必须且只能包含 by/value")
    if value.get("by") not in LOCATOR_TYPES or not _text(value.get("value")):
        raise RouteMapError(f"{location} 的 by/value 无效")


def _validate_step(step: object, location: str) -> None:
    if not isinstance(step, dict):
        raise RouteMapError(f"{location} 必须是对象")
    action = step.get("action")
    if action not in ACTION_FIELDS:
        raise RouteMapError(f"{location}.action 非法: {action}")
    allowed = COMMON_STEP_FIELDS | ACTION_FIELDS[action]
    if set(step) - allowed:
        raise RouteMapError(f"{location} 存在未知字段: {sorted(set(step) - allowed)}")
    if not _text(step.get("stepId")):
        raise RouteMapError(f"{location}.stepId 不能为空")
    if not _text(step.get("desc")):
        raise RouteMapError(f"{location}.desc 必须是非空字符串")
    if "expectPage" in step and not _text(step["expectPage"]):
        raise RouteMapError(f"{location}.expectPage 必须是非空字符串")

    if action == "launch" and not _text(step.get("target")):
        raise RouteMapError(f"{location}.target 不能为空")
    if action in {"tap", "input"}:
        _validate_locator(step.get("locator"), f"{location}.locator")
    if action == "input" and not isinstance(step.get("value"), str):
        raise RouteMapError(f"{location}.value 必须是字符串")
    if action == "swipe":
        if step.get("direction") not in DIRECTIONS:
            raise RouteMapError(f"{location}.direction 非法")
        if "distance" in step and step["distance"] not in DISTANCES:
            raise RouteMapError(f"{location}.distance 非法")
    if action == "wait" and (
        not isinstance(step.get("timeoutMs"), int)
        or isinstance(step.get("timeoutMs"), bool)
        or step["timeoutMs"] <= 0
    ):
        raise RouteMapError(f"{location}.timeoutMs 必须是正整数")


def validate_route_map_data(
    data: object,
    *,
    required_batches: set[str] | None = None,
    batch_pages: dict[str, set[str]] | None = None,
) -> dict[str, Any]:
    """校验 JSON 结构，以及可选的批次和页面引用。"""
    if not isinstance(data, dict) or set(data) != TOP_FIELDS:
        raise RouteMapError("route-map.json 顶层必须且只能包含 schemaVersion/routes/unresolved")
    if data.get("schemaVersion") != 1:
        raise RouteMapError("route-map.json schemaVersion 必须为 1")
    routes = data.get("routes")
    unresolved = data.get("unresolved")
    if not isinstance(routes, list) or not routes:
        raise RouteMapError("route-map.json routes 必须是非空数组")
    if not isinstance(unresolved, list):
        raise RouteMapError("route-map.json unresolved 必须是数组")
    _check_placeholders(data)

    route_ids: set[str] = set()
    covered_batches: set[str] = set()
    for route_index, route in enumerate(routes):
        location = f"routes[{route_index}]"
        if not isinstance(route, dict) or set(route) != ROUTE_FIELDS:
            raise RouteMapError(f"{location} 必须且只能包含 routeId/batchId/targetPage/steps")
        route_id = route.get("routeId")
        batch_id = route.get("batchId")
        target_page = route.get("targetPage")
        steps = route.get("steps")
        if not all(_text(value) for value in (route_id, batch_id, target_page)):
            raise RouteMapError(f"{location} 的 routeId/batchId/targetPage 不能为空")
        if route_id in route_ids:
            raise RouteMapError(f"routeId 重复: {route_id}")
        route_ids.add(route_id)
        covered_batches.add(batch_id)
        if os.path.isabs(target_page) or ".." in target_page.split("/"):
            raise RouteMapError(f"{location}.targetPage 必须是工程相对路径")
        if batch_pages is not None:
            if batch_id not in batch_pages:
                raise RouteMapError(f"{location}.batchId 不存在: {batch_id}")
            if target_page not in batch_pages[batch_id]:
                raise RouteMapError(f"{location}.targetPage 不属于批次 {batch_id}: {target_page}")
        if not isinstance(steps, list) or not steps:
            raise RouteMapError(f"{location}.steps 必须是非空数组")
        step_ids: set[str] = set()
        for step_index, step in enumerate(steps):
            step_location = f"{location}.steps[{step_index}]"
            _validate_step(step, step_location)
            step_id = step["stepId"]
            if step_id in step_ids:
                raise RouteMapError(f"{location} 内 stepId 重复: {step_id}")
            step_ids.add(step_id)
        if steps[0].get("action") != "launch":
            raise RouteMapError(f"{location} 必须从 launch 开始")

    if required_batches is not None:
        missing = sorted(required_batches - covered_batches)
        if missing:
            raise RouteMapError(f"route-map.json 未覆盖批次: {missing}")

    for index, item in enumerate(unresolved):
        if not isinstance(item, dict) or set(item) != {"source", "target", "reason"}:
            raise RouteMapError(f"unresolved[{index}] 必须且只能包含 source/target/reason")
        if not all(_text(item.get(key)) for key in ("source", "target", "reason")):
            raise RouteMapError(f"unresolved[{index}] 字段不能为空")
    return data


def load_route_map(
    path: str,
    *,
    required_batches: set[str] | None = None,
    batch_pages: dict[str, set[str]] | None = None,
) -> dict[str, Any]:
    """读取并校验 route-map.json。"""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError as error:
        raise RouteMapError(f"无法读取 route-map.json: {error}") from error
    except json.JSONDecodeError as error:
        raise RouteMapError(f"route-map.json 解析失败: {error}") from error
    return validate_route_map_data(
        data,
        required_batches=required_batches,
        batch_pages=batch_pages,
    )


def validate_verification_routes(data: dict[str, Any], ledger: dict[str, Any]) -> None:
    """校验 verificationPlan.routeId 存在并真正到达问题影响页面。"""
    routes = {item["routeId"]: item for item in data["routes"]}
    invalid: list[str] = []
    for issue in ledger.get("issues", []):
        if not isinstance(issue, dict):
            continue
        for plan in issue.get("verificationPlan", []):
            if not isinstance(plan, dict):
                continue
            route_id = plan.get("routeId")
            route = routes.get(route_id)
            affected_pages = {
                value for value in [issue.get("page"), *issue.get("affectedPages", [])]
                if isinstance(value, str) and value
            }
            if (
                route is None
                or route.get("batchId") != issue.get("batchId")
                or route.get("targetPage") not in affected_pages
            ):
                invalid.append(
                    f"{issue.get('issueId', 'unknown')}/{plan.get('form')}/"
                    f"{plan.get('checkId')}->{route_id}"
                )
    if invalid:
        raise RouteMapError(
            "verificationPlan 存在缺失、跨批次或未到达问题影响页面的 routeId: "
            f"{invalid}"
        )
