#!/usr/bin/env python3
"""一次扫描 HarmonyOS 工程的候选页面、路由节点和静态跳转边。

脚本统一输出页面清单和路由关系，避免分别运行页面、路由脚本造成重复遍历。
动态变量、按钮语义、条件分支与 ViewModel 归属留给 AI 核实。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from onemulti.project import (  # noqa: E402
    _load_json5,
    build_page_inventory,
    find_page_registries,
    iter_files,
)


# 这里只匹配能够静态确定目标的字面量调用。变量、函数返回值和复杂表达式
# 必须留给 AI 结合调用上下文核实，脚本不能为了“多识别”而猜边。
NAMED_CALL = re.compile(
    r"\b(?P<method>pushPathByName|replacePathByName|pushDestination|pushPath)"
    r"\s*\(\s*['\"](?P<name>[^'\"]+)['\"]"
)
OBJECT_CALL = re.compile(
    r"\b(?P<method>pushUrl|replaceUrl|push|replace)\s*\(\s*\{"
    r"(?P<body>.{0,800}?)\}\s*\)",
    re.DOTALL,
)
URL_FIELD = re.compile(r"\b(?:url|name)\s*:\s*['\"](?P<name>[^'\"]+)['\"]")


def line_of(text: str, pos: int) -> int:
    """把正则匹配偏移换成面向用户的 1-based 行号。"""
    return text[:pos].count("\n") + 1


def module_root_for(route_map_path: str) -> str:
    """从 resources/base/profile/route_map.json 反推出模块根目录。"""
    marker = os.path.join("src", "main", "resources")
    index = route_map_path.find(marker)
    return route_map_path[:index].rstrip(os.sep) if index >= 0 else os.path.dirname(route_map_path)


def add_node(nodes: dict[str, dict], node: dict) -> None:
    """按稳定 id 去重；先发现的注册信息优先于后续弱候选。"""
    nodes.setdefault(node["id"], node)


def scan(project: str) -> dict:
    """扫描工程并返回页面清单、静态节点、边和待核实项。"""
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    unresolved: list[dict] = []
    route_index: dict[str, list[str]] = {}
    page_to_node: dict[str, str] = {}
    builder_index: dict[str, str] = {}
    route_map_count = 0
    counted_maps: set[str] = set()
    pages = build_page_inventory(project)

    def register_route_table(path: str, module_root: str) -> bool:
        """登记一张路由表文件；同一 route id 只索引一次，返回表内容是否有效。"""
        nonlocal route_map_count
        data = _load_json5(path)
        if not isinstance(data, dict) or not isinstance(data.get("routerMap"), list):
            return False
        real = os.path.realpath(path)
        if real not in counted_maps:
            counted_maps.add(real)
            route_map_count += 1
        module = os.path.basename(module_root) or "."
        for item in data["routerMap"]:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                continue
            name = item["name"]
            node_id = f"route:{module}:{name}"
            if node_id in nodes:
                continue
            source = item.get("pageSourceFile")
            page = None
            if isinstance(source, str):
                page = os.path.relpath(os.path.join(module_root, source), project)
            add_node(nodes, {
                "id": node_id,
                "kind": "route",
                "name": name,
                "page": page,
                "module": module,
                "builder": item.get("buildFunction"),
                "entry": False,
            })
            route_index.setdefault(name, []).append(node_id)
            if page:
                page_to_node[page] = node_id
            builder = item.get("buildFunction")
            if isinstance(builder, str):
                builder_index[builder] = node_id
        return True

    def router_map_issue(module_file: str, reference: object, reason: str) -> None:
        unresolved.append({
            "source": module_file,
            "target": reference if isinstance(reference, str) else str(reference),
            "type": "router-map",
            "reason": reason,
            "evidence": {"file": module_file, "snippet": f"routerMap: {reference}"},
        })

    # 第一层：route_map.json 是命名路由的权威注册来源。
    for path in iter_files(project, ("route_map.json",)):
        register_route_table(path, module_root_for(path))

    # 第一层补充：module.json5 的 routerMap 引用解析。route_map.json 文件名
    # 只覆盖 DevEco 默认名；工程使用任意 profile 名时，以 module.json5 的
    # ``routerMap: "$profile:xxx"`` 引用为准（page-inventory.md 的既定契约）。
    for module_file in iter_files(project, ("module.json5",)):
        module_doc = _load_json5(module_file)
        if not isinstance(module_doc, dict) or not isinstance(module_doc.get("module"), dict):
            continue
        reference = module_doc["module"].get("routerMap")
        if reference is None:
            continue
        rel_module = os.path.relpath(module_file, project)
        profile = None
        if isinstance(reference, str) and reference.startswith("$profile:"):
            profile = reference.split(":", 1)[1]
        if not profile or profile in {".", ".."} or any(sep in profile for sep in ("/", "\\")):
            router_map_issue(rel_module, reference, "router-map-reference-invalid")
            continue
        src_main = os.path.dirname(module_file)
        # pageSourceFile 相对模块根记录；module.json5 位于 <模块>/src/main/ 下，
        # 向上两级才是模块根，与文件名层 module_root_for 的口径一致。
        module_root = os.path.dirname(os.path.dirname(src_main))
        table = os.path.join(src_main, "resources", "base", "profile", f"{profile}.json")
        if not os.path.isfile(table):
            router_map_issue(rel_module, reference, "router-map-file-missing")
        elif not register_route_table(table, module_root):
            router_map_issue(rel_module, reference, "router-map-content-invalid")

    # 第二层：main_pages.json 提供 Stage 模型入口页。
    for registry in find_page_registries(project):
        for route in registry["routes"] or []:
            page = os.path.join(registry["srcMainDir"], "ets", route + ".ets")
            node_id = f"entry:{registry['moduleName']}:{route}"
            add_node(nodes, {
                "id": node_id,
                "kind": "entry",
                "name": route,
                "page": page,
                "module": registry["moduleName"],
                "builder": None,
                "entry": True,
            })
            route_index.setdefault(route, []).append(node_id)
            page_to_node[page] = node_id

    # 第三层：页面清单补充未注册但具有页面特征的候选，避免图中漏节点。
    for candidate in pages:
        page = candidate["path"]
        if page in page_to_node:
            continue
        node_id = f"page:{page}"
        add_node(nodes, {
            "id": node_id,
            "kind": candidate["kind"],
            "name": candidate["component"],
            "page": page,
            "module": candidate["module"],
            "builder": None,
            "entry": False,
        })
        page_to_node[page] = node_id

    seen_edges: set[tuple[str, str, str, str, int]] = set()

    def emit(source_file: str, target_name: str, edge_type: str, line: int, snippet: str) -> None:
        """把一条字面量跳转转换成边；目标不唯一时保留为待核实。"""
        targets = route_index.get(target_name, [])
        source_id = page_to_node.get(source_file)
        if source_id is None:
            source_id = f"source:{source_file}"
            add_node(nodes, {
                "id": source_id, "kind": "source", "name": os.path.basename(source_file),
                "page": source_file, "module": None, "builder": None, "entry": False,
            })
        if len(targets) != 1:
            unresolved.append({
                "source": source_file,
                "target": target_name,
                "type": edge_type,
                "reason": "route-not-found" if not targets else "duplicate-route-name",
                "evidence": {"file": source_file, "line": line, "snippet": snippet},
            })
            return
        key = (source_id, targets[0], edge_type, source_file, line)
        if key in seen_edges:
            return
        seen_edges.add(key)
        edges.append({
            "from": source_id,
            "to": targets[0],
            "type": edge_type,
            "confidence": "exact",
            "evidence": {"file": source_file, "line": line, "snippet": snippet},
        })

    # 最后扫描 ArkTS 调用点。只有唯一命名目标才进入 exact 边。
    for path in iter_files(project, (".ets",)):
        rel = os.path.relpath(path, project)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
        except (OSError, UnicodeDecodeError):
            continue

        for match in NAMED_CALL.finditer(text):
            method = match.group("method")
            emit(rel, match.group("name"), "replace" if method.startswith("replace") else "push",
                 line_of(text, match.start()), match.group(0)[:160])

        for match in OBJECT_CALL.finditer(text):
            field = URL_FIELD.search(match.group("body"))
            if field:
                method = match.group("method")
                emit(rel, field.group("name"), "replace" if method.startswith("replace") else "push",
                     line_of(text, match.start()), match.group(0).replace("\n", " ")[:160])

        caller = page_to_node.get(rel)
        if caller:
            for builder, target in builder_index.items():
                if nodes[target].get("page") == rel:
                    continue
                match = re.search(rf"\b{re.escape(builder)}\s*\(", text)
                if not match:
                    continue
                key = (caller, target, "embed", rel, line_of(text, match.start()))
                if key in seen_edges:
                    continue
                seen_edges.add(key)
                edges.append({
                    "from": caller, "to": target, "type": "embed", "confidence": "exact",
                    "evidence": {"file": rel, "line": line_of(text, match.start()), "snippet": match.group(0)},
                })

    incoming = {edge["to"] for edge in edges}
    orphans = [node_id for node_id, node in nodes.items()
               if node["kind"] == "route" and node_id not in incoming]
    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "project": os.path.abspath(project),
        "summary": {
            "pages": len(pages),
            "routeMapFiles": route_map_count,
            "nodes": len(nodes),
            "edges": len(edges),
            "unresolved": len(unresolved),
            "orphanRoutes": len(orphans),
        },
        "pages": pages,
        "nodes": sorted(nodes.values(), key=lambda item: item["id"]),
        "edges": sorted(edges, key=lambda item: (item["from"], item["to"], item["type"])),
        "unresolved": unresolved,
        "orphanRoutes": orphans,
    }


def markdown(graph: dict) -> str:
    """生成供 AI 二次核实的路由图骨架。

    分片表故意保留“待规划”占位；Agent 必须补齐当前任务范围内的动态边和批次后，
    task-ledger.py 才允许登记批次计划。
    """
    node_ids = {node["id"]: f"N{i}" for i, node in enumerate(graph["nodes"], 1)}
    summary = graph["summary"]
    lines = [
        "# 页面路由图", "", "## 结论摘要", "",
        f"- 候选页面：{summary['pages']}",
        f"- 入口/页面节点：{summary['nodes']}",
        f"- 静态路由边：{summary['edges']}",
        f"- 未解析项：{summary['unresolved']}",
        f"- 孤立路由：{summary['orphanRoutes']}",
        "", "## 阅读约定", "",
        "- L0：入口页；L1：入口直接到达；L2：经一个中间页面到达。",
        "- `push/replace/embed/tab` 表示跳转或嵌入类型；AI 需补充动态边和用户动作。",
        "", "## 路由主图", "", "```mermaid", "flowchart TD",
    ]
    for node in graph["nodes"]:
        label = f"{node['name']}\\n{node.get('page') or ''}".replace('"', "'")
        lines.append(f"  {node_ids[node['id']]}[\"{label}\"]")
    for edge in graph["edges"]:
        lines.append(f"  {node_ids[edge['from']]} -- \"{edge['type']}\" --> {node_ids[edge['to']]}")
    lines.extend(["```", "", "## 路由明细", "", "| 来源 | 目标 | 类型 | 证据 |", "|---|---|---|---|"])
    node_names = {node["id"]: node["name"] for node in graph["nodes"]}
    for edge in graph["edges"]:
        evidence = edge["evidence"]
        lines.append(
            f"| {node_names[edge['from']]} | {node_names[edge['to']]} | {edge['type']} | "
            f"`{evidence['file']}:{evidence['line']}` |"
        )
    lines.extend([
        "", "## 分片路由表", "",
        "| 批次 | 页面 | 层级 | 上游入口 | 下游页面 | 公共依赖 |",
        "|---|---|---|---|---|---|",
        "| 待规划 | 待 AI 核实 | - | - | - | - |",
        "", "## 孤立与待核实项", "", "### 孤立路由", "",
    ])
    if graph["orphanRoutes"]:
        node_names = {node["id"]: node["name"] for node in graph["nodes"]}
        lines.extend(f"- `{node_names.get(node_id, node_id)}`" for node_id in graph["orphanRoutes"])
    else:
        lines.append("无。")
    lines.extend(["", "### 动态边与未解析项", ""])
    if graph["unresolved"]:
        for item in graph["unresolved"]:
            evidence = item["evidence"]
            lines.append(f"- `{evidence['file']}:{evidence['line']}` → `{item['target']}`：{item['reason']}")
    else:
        lines.append("无。")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="HarmonyOS 页面与路由统一扫描")
    parser.add_argument("project", help="工程根目录")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true")
    output.add_argument("--markdown", action="store_true")
    args = parser.parse_args()
    if not os.path.isdir(args.project):
        print("请提供有效的工程根目录", file=sys.stderr)
        return 2
    graph = scan(args.project)
    if args.json:
        print(json.dumps(graph, ensure_ascii=False, indent=2))
    elif args.markdown:
        print(markdown(graph), end="")
    else:
        summary = graph["summary"]
        print(
            f"候选页面 {summary['pages']} / 路由节点 {summary['nodes']} / "
            f"跳转边 {summary['edges']} / 待核实 {summary['unresolved']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
