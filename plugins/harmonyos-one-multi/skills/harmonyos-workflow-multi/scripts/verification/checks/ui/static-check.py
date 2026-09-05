#!/usr/bin/env python3
"""Tier-0 静态断言 CLI：源码级检查，**不需要设备**，秒级完成。

规则集在 `ui_checks/static_rules.py`，工程遍历在 `ui_checks/project.py`。
本文件只负责参数解析与输出格式。

用法::

    python3 static-check.py <工程根>            # 文本输出
    python3 static-check.py <工程根> --json     # JSON 输出
    python3 static-check.py --rules             # 列出规则

退出码: 0 = 无 FAIL, 1 = 存在 FAIL, 2 = 输入错误。
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui_checks import static_rules  # noqa: E402
from ui_checks.project import scan_static  # noqa: E402
from ui_checks.static_rules import SEVERITY_FAIL  # noqa: E402


def cmd_rules() -> int:
    for meta in static_rules.registered_rules():
        print(f"  {meta.rule_id:4} {meta.severity:5} {meta.title:24} 适用: {','.join(meta.suffixes)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="一多适配静态断言（无需设备）")
    parser.add_argument("project", nargs="?", help="HarmonyOS 工程根目录")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--rules", action="store_true", help="列出已注册规则")
    args = parser.parse_args()

    if args.rules:
        return cmd_rules()
    if not args.project or not os.path.isdir(args.project):
        print("请提供有效的工程根目录", file=sys.stderr)
        return 2

    issues = scan_static(args.project)
    fails = sum(1 for i in issues if i.severity == SEVERITY_FAIL)
    warns = len(issues) - fails

    if args.json:
        print(json.dumps({
            "summary": {"fail": fails, "warn": warns},
            "issues": [i.to_dict() for i in issues],
        }, ensure_ascii=False, indent=2))
    else:
        for issue in sorted(issues, key=lambda i: (i.severity != SEVERITY_FAIL, i.rule)):
            mark = "✗" if issue.severity == SEVERITY_FAIL else "!"
            print(f"[{mark}] {issue.rule} {issue.title}")
            print(f"    {issue.file}:{issue.line}")
            print(f"    {issue.snippet}")
            print(f"    {issue.detail}")
            print(f"    建议: {issue.suggestion}\n")
        print(f"合计: {fails} FAIL / {warns} WARN")

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
