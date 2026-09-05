#!/usr/bin/env python3
"""校验所有 HAP/HAR/HSP 的 module.deviceTypes 是否覆盖一多目标形态。"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui_checks.device_types import (  # noqa: E402
    declaration_errors,
    declared_device_types,
    effective_target_forms,
    missing_requirements,
    module_object,
    required_device_type_groups,
)
from ui_checks.json5 import loads_json5  # noqa: E402
from ui_checks.project import iter_files  # noqa: E402


def inspect(project: Path, target_forms: list[str]) -> dict[str, Any]:
    effective_forms = effective_target_forms(target_forms)
    requirements = required_device_type_groups(effective_forms)
    modules: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for raw_path in iter_files(str(project), ("module.json5",)):
        path = Path(raw_path)
        relative = path.relative_to(project).as_posix()
        try:
            data = loads_json5(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        module = module_object(data)
        if module is None:
            continue
        declared = declared_device_types(module)
        record = {
            "file": relative,
            "module": module.get("name", ""),
            "type": module.get("type", ""),
            "deviceTypes": sorted(declared),
        }
        modules.append(record)
        errors = declaration_errors(module)
        missing = missing_requirements(declared, requirements)
        if errors or missing:
            issues.append({
                **record,
                "missing": missing,
                "errors": errors,
            })
    if not modules:
        issues.append({
            "file": "",
            "module": "",
            "type": "",
            "deviceTypes": [],
            "missing": requirements,
            "errors": ["工程内未发现 module.json5，无法确认 HAP/HAR/HSP 的目标设备声明"],
        })
    return {
        "ok": not issues,
        "targetForms": effective_forms,
        "usedDefaultTargets": not bool(target_forms),
        "requirements": requirements,
        "modules": modules,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument(
        "--target-form", action="append", default=[],
        help="目标形态，可重复；省略时使用手机、折叠屏、平板默认范围",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    project = Path(args.project).resolve()
    if not project.is_dir():
        print(f"找不到工程目录: {project}", file=sys.stderr)
        return 2
    result = inspect(project, args.target_form)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        source = "默认范围" if result["usedDefaultTargets"] else "明确范围"
        print(f"目标形态（{source}）: {result['targetForms']}")
        print(f"deviceTypes 能力要求: {result['requirements']}")
        for issue in result["issues"]:
            print(f"[FAIL] {issue['file']}")
            if issue["errors"]:
                print(f"       {'；'.join(issue['errors'])}")
            if issue["missing"]:
                print(f"       缺少目标设备能力: {issue['missing']}")
        if result["ok"]:
            print(f"通过: {len(result['modules'])} 个 module.json5")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
