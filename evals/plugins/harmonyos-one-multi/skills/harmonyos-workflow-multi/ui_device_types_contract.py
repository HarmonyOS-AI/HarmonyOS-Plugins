"""目标形态到 module.deviceTypes 的端到端契约。"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile


def _write_module(project: Path, name: str, module_type: str, device_types: list[str] | None) -> None:
    path = project / name / "src" / "main" / "module.json5"
    path.parent.mkdir(parents=True, exist_ok=True)
    module: dict[str, object] = {"name": name, "type": module_type}
    if device_types is not None:
        module["deviceTypes"] = device_types
    path.write_text(json.dumps({"module": module}), encoding="utf-8")


def _run(
    script: Path, project: Path, target_forms: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    arguments = [sys.executable, str(script), str(project), "--json"]
    for form in target_forms or []:
        arguments.extend(["--target-form", form])
    return subprocess.run(
        arguments,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
    )


def run(skill_root: Path) -> tuple[bool, str]:
    script = skill_root / "scripts" / "verification" / "checks" / "ui" / "check-device-types.py"
    with tempfile.TemporaryDirectory() as temp_dir:
        project = Path(temp_dir)
        _write_module(project, "entry", "entry", ["phone", "tablet"])
        _write_module(project, "feature", "har", ["default"])
        _write_module(project, "shared", "shared", None)
        failed = _run(script, project)
        if failed.returncode != 1:
            return False, f"缺失声明未阻断，exit={failed.returncode}: {failed.stderr}"
        data = json.loads(failed.stdout)
        if not data["usedDefaultTargets"] or data["targetForms"] != ["phone", "foldable", "tablet"]:
            return False, "未限定设备时没有采用手机、折叠屏、平板默认范围"
        by_file = {issue["file"]: issue for issue in data["issues"]}
        tablet_requirement = [{"target": "tablet", "anyOf": ["tablet"]}]
        if by_file["feature/src/main/module.json5"]["missing"] != tablet_requirement:
            return False, "HAR 未识别缺少 tablet"
        shared = by_file["shared/src/main/module.json5"]
        if shared["missing"] != data["requirements"] or not shared["errors"]:
            return False, "HSP 未同时识别声明缺失与目标覆盖缺失"

        _write_module(project, "feature", "har", ["default", "tablet"])
        _write_module(project, "shared", "shared", ["phone", "tablet"])
        passed = _run(script, project)
        if passed.returncode != 0:
            return False, f"完整声明被误报: {passed.stdout} {passed.stderr}"

        _write_module(project, "entry", "entry", ["phone"])
        _write_module(project, "feature", "har", ["default"])
        _write_module(project, "shared", "shared", ["phone"])
        narrowed = _run(script, project, ["foldable-expanded"])
        if narrowed.returncode != 0:
            return False, f"只适配折叠屏时错误强制 tablet: {narrowed.stdout} {narrowed.stderr}"
        narrowed_data = json.loads(narrowed.stdout)
        if narrowed_data["usedDefaultTargets"] or narrowed_data["requirements"] != [{
            "target": "phone/foldable", "anyOf": ["default", "phone"],
        }]:
            return False, "明确缩小范围后仍使用默认三设备"

        _write_module(project, "entry", "entry", ["tablet"])
        _write_module(project, "feature", "har", ["tablet"])
        _write_module(project, "shared", "shared", ["tablet"])
        tablet_only = _run(script, project, ["tablet-landscape"])
        if tablet_only.returncode != 0:
            return False, f"只适配平板时错误强制手机能力: {tablet_only.stdout} {tablet_only.stderr}"
        tablet_data = json.loads(tablet_only.stdout)
        if tablet_data["requirements"] != [{"target": "tablet", "anyOf": ["tablet"]}]:
            return False, "只适配平板时仍保留了手机/折叠屏能力要求"
    return True, "默认三设备；缩小范围后按 phone/default 二选一动态校验"
