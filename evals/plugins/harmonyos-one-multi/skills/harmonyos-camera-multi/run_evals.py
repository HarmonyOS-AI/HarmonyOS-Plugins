#!/usr/bin/env python3
"""Camera 领域 Skill 离线回归：结构、引用和知识边界契约。"""

from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from skill_contract import run as run_skill_contract  # noqa: E402


def main() -> int:
    passed = failed = 0
    print("— skill-contract")
    for result in run_skill_contract(HERE.parent):
        print(f"  {'PASS' if result.passed else 'FAIL'}  {result.name}: {result.detail}")
        passed += int(result.passed)
        failed += int(not result.passed)

    print(f"合计 {passed} 通过 / {failed} 失败")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
