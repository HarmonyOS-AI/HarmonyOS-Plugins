"""Camera 领域 Skill 的结构、引用与独立发布边界契约。"""

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

    markdown = [skill, *sorted((root / "references").rglob("*.md"))]
    broken: list[str] = []
    link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for source in markdown:
        for raw in link_re.findall(source.read_text(encoding="utf-8")):
            target = raw.split("#", 1)[0]
            if target and "://" not in target and not target.startswith("$"):
                if not (source.parent / target).resolve().exists():
                    broken.append(f"{source.relative_to(root)} -> {raw}")

    required = [
        "assets/CameraFoldable.ets",
        "references/camera-root-causes.md",
        "references/camera-capabilities.md",
        "references/camera-fold.md",
        "references/camera-output.md",
        "references/camera-frames.md",
        "references/camera-preview-ui.md",
        "references/cases/camera-fold-cases.md",
        "references/cases/camera-output-cases.md",
        "references/device-capabilities.md",
    ]
    missing = [path for path in required if not (root / path).exists()]

    behavior_path = root / "evals" / "behavior" / "cases.json"
    behavior = json.loads(behavior_path.read_text(encoding="utf-8"))
    duplicate_ids = sorted({case["id"] for case in behavior if sum(
        item.get("id") == case.get("id") for item in behavior
    ) > 1})

    forbidden_paths = [
        "scripts", "assets/report", "references/task-ledger.md",
        "references/reporting.md", "references/verification.md",
        "references/cases/camera-verification-matrix.md",
        "references/route-map.md", "references/page-inventory.md",
    ]
    present_forbidden_paths = [path for path in forbidden_paths if (root / path).exists()]
    all_text = "\n".join(path.read_text(encoding="utf-8") for path in markdown)
    forbidden_refs = [
        ".onemulti", "decisions.json", "task-ledger.py", "render-report.py",
        "project-scan.py", "harmonyos-workflow-multi/", "../harmonyos-",
    ]
    leaked_refs = [token for token in forbidden_refs if token in all_text]

    return [
        _result("frontmatter", keys == {"name", "description"}, f"字段={sorted(keys)}"),
        _result("markdown-links", not broken, "无坏链" if not broken else "; ".join(broken)),
        _result("topic-assets", not missing, "完整" if not missing else f"缺失={missing}"),
        _result("behavior-cases", not duplicate_ids, "ID 唯一" if not duplicate_ids else f"重复={duplicate_ids}"),
        _result(
            "knowledge-boundary",
            not present_forbidden_paths and not leaked_refs,
            "可独立发布，不依赖流程目录"
            if not present_forbidden_paths and not leaked_refs
            else f"路径={present_forbidden_paths}, 引用={leaked_refs}",
        ),
        _result(
            "direct-task-semantics",
            "诊断、修复明确的局部相机问题" in text
            and "在明确范围内直接修改" in text,
            "局部相机任务可直接处理",
        ),
    ]
