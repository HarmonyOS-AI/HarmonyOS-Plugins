#!/usr/bin/env python3
"""编制完整质量计划、冻结证据上下文、登记实际验证并计算质量等级。"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid

from onemulti.ledger import atomic_write, batch_by_id, load_ledger, LedgerError
from onemulti.quality import STANDARD_VERSION, GRADES, ENHANCEMENTS, expected_checks, plan_digest
from onemulti.quality_evidence import artifact_path, file_hash, quality_model, result_state, source_snapshot
from onemulti.reporting import load_inputs, validate_evidence, ReportError
from onemulti.route_map import load_route_map, RouteMapError


def read_input(path: str) -> dict:
    value = json.load(sys.stdin) if path == "-" else json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("输入必须是 JSON 对象")
    return value


def append_entry(om: Path, ledger: dict, index: dict, kind: str, links: list, data: dict) -> str:
    evidence_id = "quality-" + uuid.uuid4().hex
    index["entries"].append({"evidenceId": evidence_id, "type": kind, "round": None,
                             "links": links, "data": data})
    validate_evidence(index, ledger, om)
    fd, temporary = tempfile.mkstemp(dir=om / "evidence", prefix=".quality-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(index, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, om / "evidence/index.json")
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return evidence_id


def routes_for(om: Path, ledger: dict, batch: dict) -> dict:
    if ledger["task"].get("routeMap") != "output/route-map.json":
        raise ValueError("先登记 output/route-map.json")
    data = load_route_map(str(om / "output/route-map.json"), required_batches={batch["batchId"]},
                          batch_pages={b["batchId"]: set(b["pages"]) for b in ledger["batches"]})
    return {r["routeId"]: r for r in data["routes"] if r["batchId"] == batch["batchId"]}


def execute(args: argparse.Namespace) -> dict:
    om = Path(args.om_root).resolve()
    ledger = load_ledger(str(om / "decisions.json"))
    if not ledger["task"]:
        raise ValueError("先初始化任务与批次")
    if args.command == "configure":
        config = {"standardVersion": STANDARD_VERSION,
                  "targetGrade": args.target, "enhancements": sorted(args.enhancement)}
        if ledger["task"].get("quality") == config:
            return {"quality": config, "status": "unchanged"}
        ledger["task"]["quality"] = config
        # 明确变更目标后重新编制，保留历史证据但不沿用旧评级。
        for batch in ledger["batches"]:
            batch.pop("qualityChecks", None)
            batch["specConfirmed"] = False
        atomic_write(str(om / "decisions.json"), ledger)
        return {"quality": ledger["task"]["quality"], "status": "configured"}
    if not ledger["task"].get("quality"):
        if args.command == "assess":
            return {"configured": False, "achievedGrade": None, "rows": []}
        raise ValueError("先 configure 质量目标")
    if args.command == "assess":
        ledger, index = load_inputs(om)
        if args.batch_id:
            batch_by_id(ledger, args.batch_id)
        return quality_model(ledger, index, om, args.batch_id)
    batch = batch_by_id(ledger, args.batch_id)
    if args.command == "template":
        return {"qualityChecks": [{**c, "routeId": "", "scenario": "", "applicability": "applicable", "reason": None}
                                  for c in expected_checks(ledger["task"], batch)]}
    if args.command == "plan":
        previous = batch.get("qualityChecks")
        batch["qualityChecks"] = read_input(args.input).get("qualityChecks")
        # 验证完整矩阵后，再验证每项实际可执行路径；失败不落盘。
        from onemulti.ledger import validate_ledger
        errors = validate_ledger(ledger)
        if errors:
            raise ValueError("; ".join(errors))
        routes = routes_for(om, ledger, batch)
        for check in batch["qualityChecks"]:
            if check["applicability"] == "applicable" and routes.get(check["routeId"], {}).get("targetPage") != check["page"]:
                raise ValueError(f"{check['checkId']} 未关联目标页面的有效路径")
        if previous != batch["qualityChecks"]:
            batch["specConfirmed"] = False
        atomic_write(str(om / "decisions.json"), ledger)
        return {"status": "planned", "checks": len(batch["qualityChecks"])}
    if not batch.get("qualityChecks"):
        raise ValueError("先编制非空质量检查计划")
    if (ledger["task"]["currentBatch"] != args.batch_id
            or not batch.get("specConfirmed") or batch.get("status") != "executing"):
        raise ValueError("质量验证仅在已确认的当前 executing 批次执行；计划变更后按原流程重新确认")
    ledger, index = load_inputs(om)
    batch = batch_by_id(ledger, args.batch_id)
    source_sha = source_snapshot(om.parent, om)
    plan_sha = plan_digest(ledger["task"], batch)
    route_sha = file_hash(om / "output/route-map.json")
    if args.command == "begin":
        routes_for(om, ledger, batch)
        data = {"batchId": args.batch_id, "sourceSha256": source_sha, "planSha256": plan_sha,
                "routeSha256": route_sha}
        return {"sessionId": append_entry(om, ledger, index, "quality_session", [], data)}
    payload = read_input(args.input)
    session = next((e for e in index["entries"] if e["evidenceId"] == payload.get("sessionId")
                    and e["type"] == "quality_session"), None)
    context = {"batchId": args.batch_id, "sourceSha256": source_sha, "planSha256": plan_sha, "routeSha256": route_sha}
    if not session or session["data"] != context:
        raise ValueError("质量验证会话缺失或源码/计划/路由已变化；重新 begin 并重测")
    check = next((c for c in batch["qualityChecks"] if c["checkId"] == payload.get("checkId")), None)
    if not check or check["applicability"] != "applicable":
        raise ValueError("结果必须对应当前计划的适用检查项")
    if payload.get("status") not in {"passed", "failed", "not_verified"}:
        raise ValueError("status 必须是 passed/failed/not_verified")
    if not isinstance(payload.get("observation"), str) or not payload["observation"].strip():
        raise ValueError("必须说明实际观察或未验证原因")
    artifacts = []
    for item in payload.get("artifacts", []):
        if not isinstance(item, dict) or item.get("kind") not in {"runtime_screenshot", "runtime_log", "interaction_trace"}:
            raise ValueError("只接受运行截图、运行日志或交互轨迹")
        artifacts.append({"kind": item["kind"], "path": item["path"],
                          "sha256": file_hash(artifact_path(om, item["path"]))})
    data = {**context, "sessionId": payload["sessionId"], "status": payload["status"],
            "observation": payload["observation"], "device": payload.get("device"),
            "configuration": payload.get("configuration"), "artifacts": artifacts}
    state, reason = result_state(data, source_sha, plan_sha, om, check["criterionId"])
    if state != payload["status"]:
        raise ValueError(reason)
    links = [{"batchId": args.batch_id, "qualityCheckId": check["checkId"]}]
    return {"evidenceId": append_entry(om, ledger, index, "quality_result", links, data), "status": state}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("configure", "template", "plan", "begin", "record", "assess"):
        command = sub.add_parser(name)
        command.add_argument("om_root")
        if name not in {"configure"}:
            command.add_argument("--batch-id", required=name != "assess")
        if name == "configure":
            command.add_argument("--target", choices=GRADES, required=True)
            command.add_argument("--enhancement", choices=sorted(ENHANCEMENTS), action="append", default=[])
        if name in {"plan", "record"}:
            command.add_argument("--input", required=True)
    try:
        result = execute(parser.parse_args())
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, LedgerError, ReportError, RouteMapError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
