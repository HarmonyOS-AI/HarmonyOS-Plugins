"""UI 领域 Skill 的结构与知识边界契约。"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


def _result(name: str, passed: bool, detail: str) -> CheckResult:
    return CheckResult(name, passed, detail)


def run(root: Path) -> list[CheckResult]:
    skill = root / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    keys = set()
    if match:
        keys = {
            line.split(":", 1)[0].strip()
            for line in match.group(1).splitlines()
            if ":" in line and not line.startswith((" ", "\t"))
        }

    broken: list[str] = []
    link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    markdown = [skill, *sorted((root / "domains").rglob("*.md")),
                *sorted((root / "references").rglob("*.md"))]
    for source in markdown:
        for raw in link_re.findall(source.read_text(encoding="utf-8")):
            target = raw.split("#", 1)[0]
            if target and "://" not in target and not target.startswith("$"):
                if not (source.parent / target).resolve().exists():
                    broken.append(f"{source.relative_to(root)} -> {raw}")

    required = [
        "domains/size-layout.md", "domains/window-form.md", "domains/avoid-area.md",
        "domains/fold-form.md", "domains/orientation.md", "domains/global-adaptation.md",
        "references/hifi-html.md", "references/device-matrix.md",
    ]
    missing = [path for path in required if not (root / path).exists()]
    behavior = json.loads((root / "evals" / "behavior" / "cases.json").read_text(encoding="utf-8"))
    missing_behavior_resources = [
        f"{case.get('id')} -> {resource}"
        for case in behavior
        for resource in case.get("required_resources", [])
        if not (root / resource).exists()
    ]
    forbidden_paths = [
        "scripts", "scripts/install-to-project.py", "scripts/project-scan.py",
        "scripts/task-ledger.py", "scripts/validate-state.py", "scripts/render-report.py",
        "assets/report", "references/task-ledger.md", "references/verification.md",
        "references/reporting.md", "references/route-map.md", "references/page-inventory.md",
    ]
    present_forbidden_paths = [path for path in forbidden_paths if (root / path).exists()]
    forbidden_refs = [
        "$OM/decisions.json", "scripts/project-scan.py", "references/task-ledger.md",
        "references/verification.md", "references/reporting.md", "references/route-map.md",
        "harmonyos-workflow-multi/",
    ]
    all_text = "\n".join(path.read_text(encoding="utf-8") for path in markdown)
    leaked_refs = [token for token in forbidden_refs if token in all_text]
    return [
        _result("frontmatter", keys == {"name", "description"}, f"字段={sorted(keys)}"),
        _result("markdown-links", not broken, "无坏链" if not broken else "; ".join(broken)),
        _result("domain-assets", not missing, "完整" if not missing else f"缺失={missing}"),
        _result(
            "behavior-resources",
            not missing_behavior_resources,
            "完整" if not missing_behavior_resources else "; ".join(missing_behavior_resources),
        ),
        _result(
            "knowledge-boundary",
            not present_forbidden_paths and not leaked_refs,
            "只包含知识、引用和代码资产"
            if not present_forbidden_paths and not leaked_refs
            else f"路径={present_forbidden_paths}, 引用={leaked_refs}",
        ),
        _result(
            "direct-task-semantics",
            "诊断、修复明确的局部布局问题" in text
            and "只读取当前问题的目标页面" in text,
            "局部任务可直接处理",
        ),
    ]
