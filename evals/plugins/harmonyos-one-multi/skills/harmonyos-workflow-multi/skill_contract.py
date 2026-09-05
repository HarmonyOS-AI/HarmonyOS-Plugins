"""工程级 workflow Skill 的结构与职责契约。"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import re
import tempfile


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
    for source in [skill, *sorted((root / "references").rglob("*.md"))]:
        for raw in link_re.findall(source.read_text(encoding="utf-8")):
            target = raw.split("#", 1)[0]
            if target and "://" not in target and not target.startswith("$"):
                if not (source.parent / target).resolve().exists():
                    broken.append(f"{source.relative_to(root)} -> {raw}")

    required = [
        "scripts/project-scan.py", "scripts/task-ledger.py", "scripts/validate-state.py",
        "scripts/render-report.py", "scripts/verification/preflight.py",
        "scripts/verification/checks/ui/static-check.py",
        "scripts/verification/checks/ui/check-device-types.py",
        "references/task-ledger.md", "references/verification.md", "references/reporting.md",
        "references/hifi-delivery.md", "references/domain-verification/camera.md",
        "evals/behavior/cases.json",
        "assets/report/report-template.html",
    ]
    missing = [path for path in required if not (root / path).exists()]

    install_ok = False
    install_detail = "未执行"
    try:
        installer = root / "scripts" / "install-to-project.py"
        spec = importlib.util.spec_from_file_location("workflow_installer_contract", installer)
        if spec is None or spec.loader is None:
            raise RuntimeError("无法加载安装器")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            module.copy_skill(str(root), str(project / ".onemulti"))
            copied = project / ".onemulti"
            if (copied / "domains").exists():
                raise ValueError("workflow 安装包不应包含领域知识")
            if (copied / "evals").exists():
                raise ValueError("workflow 安装包不应包含 evals")
            if not (copied / "scripts" / "task-ledger.py").is_file():
                raise ValueError("缺少流程运行脚本")
            if missing := module.missing_runtime_files(str(copied)):
                raise ValueError(f"缺少运行入口: {missing}")
        install_ok = True
        install_detail = "只复制流程与验证运行资源，不含 evals"
    except Exception as error:  # noqa: BLE001
        install_detail = str(error)

    batch_report = "python3 $OM/scripts/render-report.py $OM --batch-id <batchId>"
    summary_report = "python3 $OM/scripts/render-report.py $OM --summary"
    report_stage_ok = (
        batch_report in text
        and summary_report in text
        and text.index(batch_report) < text.index("全部批次进入终态后") < text.index(summary_report)
    )

    return [
        _result("frontmatter", keys == {"name", "description"}, f"字段={sorted(keys)}"),
        _result("markdown-links", not broken, "无坏链" if not broken else "; ".join(broken)),
        _result("workflow-assets", not missing, "完整" if not missing else f"缺失={missing}"),
        _result("installer-boundary", install_ok, install_detail),
        _result(
            "routing-semantics",
            "直接修复、全量分析还是按预定流程交付" in text
            and "局部问题交给对应领域 Skill" in text,
            "区分直接修复、全量分析和预定流程",
        ),
        _result(
            "domain-boundary",
            "不在 workflow 中复制领域根因" in text and "领域 Skill 不安装到 `.onemulti`" in text,
            "领域知识保持独立",
        ),
        _result(
            "report-stage-boundary",
            report_stage_ok,
            "批次报告与最终汇总分阶段执行",
        ),
    ]
