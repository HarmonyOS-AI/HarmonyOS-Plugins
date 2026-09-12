"""跨框架体验标准、完整覆盖校验及纯质量聚合；不推断领域修法。"""

from __future__ import annotations

import hashlib
import json
from typing import Any

STANDARD_VERSION = "one-multi-1"
GRADES = ("ready", "optimized", "differentiated")
GRADE_LABELS = {"ready": "基础可用", "optimized": "自适应优化", "differentiated": "场景增强"}
# (ID, grade, title, applicability). 条件项也进入完整矩阵，排除必须说明理由。
CRITERIA = (
    ("CORE-01", "ready", "核心任务可完成，关键内容和操作无溢出或遮挡", "always"),
    ("STATE-01", "ready", "旋转、折展、窗口变化及组合后业务状态连续", "always"),
    ("INPUT-01", "ready", "输入、键盘避让及基础外设操作可用", "conditional"),
    ("MEDIA-01", "ready", "媒体或相机比例、方向及资源恢复正确", "conditional"),
    ("LAYOUT-01", "optimized", "布局按窗口及父约束合理重排，窄高和宽短窗口可用", "always"),
    ("NAV-01", "optimized", "导航、分栏和返回语义适合内容并保持选中状态", "conditional"),
    ("OVERLAY-01", "optimized", "弹窗、浮层和次要控件在各窗口尺寸合理且可操作", "conditional"),
    ("ACCESS-01", "optimized", "字体放大、焦点和适用的键鼠交互可完成核心任务", "always"),
    ("FOLD-01", "differentiated", "悬停姿态改善业务操作，退出姿态后状态连续", "fold-posture"),
    ("CAMERA-01", "differentiated", "设备支持的双面预览或切镜改善拍摄任务", "camera-experience"),
    ("DRAG-01", "differentiated", "跨栏或跨窗拖拽完成业务任务且取消时数据一致", "drag-drop"),
    ("STYLUS-01", "differentiated", "手写笔书写或绘制及适用的压感、擦除体验通过", "stylus"),
)
CATALOG = {item[0]: dict(zip(("criterionId", "grade", "title", "applicability"), item)) for item in CRITERIA}
ENHANCEMENTS = {item[3] for item in CRITERIA if item[1] == "differentiated"}
SUPPORTED_FORMS = {"phone", "tablet", "foldable", "foldable-expanded", "foldable-folded"}


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def criteria_for(config: dict) -> list[dict]:
    target = GRADES.index(config["targetGrade"])
    return [item for item in CATALOG.values() if GRADES.index(item["grade"]) <= target
            and (item["grade"] != "differentiated" or item["applicability"] in config["enhancements"])]


def expected_checks(task: dict, batch: dict) -> list[dict]:
    config = task.get("quality")
    if not config:
        return []
    return [{"checkId": "Q-" + digest([page, form, item["criterionId"]])[:20],
             "criterionId": item["criterionId"], "page": page, "form": form}
            for page in sorted(set(batch["pages"]))
            for form in sorted(set(task["targetForms"]))
            for item in criteria_for(config)]


def validate_quality(ledger: dict) -> list[str]:
    task = ledger.get("task")
    if not isinstance(task, dict):
        return []
    config = task.get("quality")
    batches = [b for b in ledger.get("batches", []) if isinstance(b, dict)]
    if config is None:
        return ["qualityChecks 需要 task.quality"] if any("qualityChecks" in b for b in batches) else []
    if not isinstance(config, dict) or set(config) != {"standardVersion", "targetGrade", "enhancements"}:
        return ["task.quality 需要且只允许 standardVersion/targetGrade/enhancements"]
    errors = []
    if config["standardVersion"] != STANDARD_VERSION:
        errors.append("不支持的质量标准版本；旧结果不得自动迁移达标")
    if config["targetGrade"] not in GRADES:
        errors.append("targetGrade 必须是 ready/optimized/differentiated")
    enhancements = config["enhancements"]
    if (not isinstance(enhancements, list) or any(not isinstance(e, str) or e not in ENHANCEMENTS for e in enhancements)
            or len(enhancements) != len(set(e for e in enhancements if isinstance(e, str)))):
        errors.append("enhancements 必须是不重复的受支持专项数组")
    elif bool(enhancements) != (config["targetGrade"] == "differentiated"):
        errors.append("仅 differentiated 需要至少一个增强专项")
    forms = task.get("targetForms")
    if not isinstance(forms, list) or not forms or any(not isinstance(f, str) or f not in SUPPORTED_FORMS for f in forms):
        errors.append("质量评级仅支持明确的手机、折叠屏和平板形态")
    if errors:
        return errors
    for batch in batches:
        checks = batch.get("qualityChecks")
        if checks is None:  # 未编制的批次保持未评估，不能在汇总中被忽略。
            continue
        if not isinstance(batch.get("pages"), list) or not all(isinstance(p, str) for p in batch["pages"]):
            continue
        if not isinstance(checks, list) or not all(isinstance(c, dict) for c in checks):
            errors.append("qualityChecks 必须是对象数组")
            continue
        expected = {c["checkId"]: c for c in expected_checks(task, batch)}
        ids = [c.get("checkId") for c in checks]
        if any(not isinstance(i, str) for i in ids) or len(set(i for i in ids if isinstance(i, str))) != len(ids) or set(i for i in ids if isinstance(i, str)) != set(expected):
            errors.append(f"{batch.get('batchId')}.qualityChecks 必须完整覆盖页面×形态×标准，不能删项或重复")
        for check in checks:
            base = expected.get(check.get("checkId")) if isinstance(check.get("checkId"), str) else None
            if not base:
                continue
            if set(check) != set(base) | {"routeId", "scenario", "applicability", "reason"}:
                errors.append("质量检查字段应为标识、routeId/scenario/applicability/reason，结果只能来自证据")
            if any(check.get(k) != v for k, v in base.items()):
                errors.append("质量检查的页面、形态或标准与确定性标识不一致")
            applicable = check.get("applicability")
            if not isinstance(applicable, str) or applicable not in {"applicable", "not_applicable"}:
                errors.append("applicability 必须是 applicable/not_applicable")
            if applicable == "not_applicable":
                if CATALOG[base["criterionId"]]["applicability"] == "always":
                    errors.append(f"{base['criterionId']} 不允许排除")
                if not isinstance(check.get("reason"), str) or not check["reason"].strip():
                    errors.append("不适用项必须记录业务或能力原因；设备缺失应记未验证")
            else:
                for key in ("routeId", "scenario"):
                    if not isinstance(check.get(key), str) or not check[key].strip():
                        errors.append(f"适用质量检查需要非空 {key}")
                if check.get("reason") is not None:
                    errors.append("适用质量检查的 reason 应为 null")
    return errors


def plan_digest(task: dict, batch: dict) -> str:
    return digest({"config": task["quality"], "pages": batch["pages"],
                   "forms": task["targetForms"], "checks": batch.get("qualityChecks", [])})


def aggregate(rows: list[dict], target: str, enhancements: list[str]) -> dict:
    """所有适用门槛逐级通过；缺证据、空范围、全 N/A 都不能升级。"""
    achieved = None
    for grade in GRADES[:GRADES.index(target) + 1]:
        level = [r for r in rows if r["grade"] == grade]
        if not level or any(r["status"] not in {"passed", "not_applicable"} for r in level):
            break
        if not any(r["status"] == "passed" for r in level):
            break
        if grade == "differentiated" and any(
            not any(r["enhancement"] == e and r["status"] == "passed" for r in level)
            for e in enhancements
        ):
            break
        achieved = grade
    return {"achievedGrade": achieved, "targetMet": achieved == target,
            "failed": sum(r["status"] == "failed" for r in rows),
            "notVerified": sum(r["status"] == "not_verified" for r in rows)}
