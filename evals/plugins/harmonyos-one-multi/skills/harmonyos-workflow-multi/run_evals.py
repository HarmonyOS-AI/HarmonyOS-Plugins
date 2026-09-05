#!/usr/bin/env python3
"""工程级 workflow Skill 离线契约测试。"""

from __future__ import annotations

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
UI_CHECK_ROOT = HERE.parent / "scripts" / "verification" / "checks" / "ui"
sys.path.insert(0, str(UI_CHECK_ROOT))

from onemulti.project import build_page_inventory  # noqa: E402
from ui_checks import static_rules  # noqa: E402
from ui_checks.project import scan_static  # noqa: E402
from ledger_contract import run as run_ledger  # noqa: E402
from report_contract import run as run_report  # noqa: E402
from skill_contract import run as run_skill  # noqa: E402
from ui_device_types_contract import run as run_device_types  # noqa: E402


def main() -> int:
    passed = failed = 0
    print("— ui-static-rules")
    fixtures = HERE / "ui_static" / "fixtures"
    for case in sorted(path for path in fixtures.iterdir() if path.is_dir()):
        expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
        issues = scan_static(str(case / "project"))
        got_fail = {item.rule for item in issues if item.severity == static_rules.SEVERITY_FAIL}
        got_warn = {item.rule for item in issues if item.severity == static_rules.SEVERITY_WARN}
        ok = got_fail == set(expected.get("expect_fail", [])) \
            and got_warn == set(expected.get("expect_warn", []))
        print(f"  {'PASS' if ok else 'FAIL'}  {case.name}")
        passed += int(ok)
        failed += int(not ok)

    print("— inventory")
    fixtures = HERE / "inventory" / "fixtures"
    for case in sorted(path for path in fixtures.iterdir() if path.is_dir()):
        expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))["expect"]
        actual = [
            {key: value for key, value in item.items() if key != "type"}
            for item in build_page_inventory(str(case / "project"))
        ]
        ok = actual == expected
        print(f"  {'PASS' if ok else 'FAIL'}  {case.name}")
        passed += int(ok)
        failed += int(not ok)

    print("— workflow-contract")
    for result in run_skill(HERE.parent):
        print(f"  {'PASS' if result.passed else 'FAIL'}  {result.name}: {result.detail}")
        passed += int(result.passed)
        failed += int(not result.passed)

    for name, runner in (("task-ledger", run_ledger), ("html-report", run_report)):
        ok, detail = runner(HERE.parent)
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: {detail}")
        passed += int(ok)
        failed += int(not ok)

    ok, detail = run_device_types(HERE.parent)
    print(f"  {'PASS' if ok else 'FAIL'}  ui-device-types: {detail}")
    passed += int(ok)
    failed += int(not ok)

    print(f"合计 {passed} 通过 / {failed} 失败")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
