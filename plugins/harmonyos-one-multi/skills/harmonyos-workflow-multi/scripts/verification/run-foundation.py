#!/usr/bin/env python3
"""记录流程构建基线，并按需运行流程内置的静态检查脚本。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
EVIDENCE_SESSION = SCRIPT_DIR / "evidence-session.py"
SNAPSHOT_EXCLUDED = {".git", ".onemulti", ".hvigor", "build", "node_modules", "oh_modules"}


class FoundationError(ValueError):
    pass


def run(command: list[str], cwd: Path, timeout: float) -> tuple[subprocess.CompletedProcess[str], float]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            command, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise FoundationError(f"命令超时: {' '.join(command)}") from error
    except OSError as error:
        raise FoundationError(f"命令无法执行: {' '.join(command)}: {error}") from error
    return result, time.monotonic() - started


def call_session(root: Path, command: str, *extra: str, input_data: str | None = None) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(EVIDENCE_SESSION), command, str(root), *extra],
        input=input_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
    )
    if result.returncode:
        raise FoundationError((result.stderr or result.stdout).strip())
    return json.loads(result.stdout)


def command_record(
    links: list[dict[str, str]], argv: list[str], result: subprocess.CompletedProcess[str],
    *, phase: str | None = None, source_sha256: str | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {"links": links, "argv": argv, "exitCode": result.returncode}
    if phase:
        record["phase"] = phase
    if source_sha256:
        record["sourceSha256"] = source_sha256
    if result.returncode != 0:
        record["reason"] = "command_failed"
        if result.stdout:
            record["stdout"] = result.stdout[-8000:]
        if result.stderr:
            record["stderr"] = result.stderr[-8000:]
    return record


def source_snapshot(root: Path) -> str:
    """Hash project inputs while excluding Skill state, dependencies, and generated outputs."""
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in SNAPSHOT_EXCLUDED for part in relative.parts) or not path.is_file():
            continue
        digest.update(relative.as_posix().encode())
        digest.update(b"\0")
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--round", type=int, default=1)
    parser.add_argument("--devecocli", default="devecocli")
    parser.add_argument("--device", help="覆盖 preflight 绑定的设备 identifier")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument(
        "--check-script", action="append", default=[], metavar="PATH",
        help="可重复指定流程 Skill 内置的静态检查脚本",
    )
    parser.add_argument(
        "--prepare-first-round", action="store_true",
        help="步骤三收尾：执行 L1/L2 并合并登记为一条 evidence",
    )
    args = parser.parse_args()

    root = Path(args.project).resolve()
    om = root / ".onemulti"
    try:
        if not 1 <= args.round <= 5:
            raise FoundationError("round 必须为 1..5")
        executable = shutil.which(args.devecocli)
        if executable is None:
            raise FoundationError(f"找不到 devecocli: {args.devecocli}")
        preflight_path = om / "evidence" / "index.json"
        preflight: dict[str, Any] = {}
        if not args.prepare_first_round:
            if not preflight_path.is_file():
                raise FoundationError("缺少 evidence/index.json")
            index = json.loads(preflight_path.read_text(encoding="utf-8"))
            state_entry = next((item for item in index.get("entries", []) if item.get("evidenceId") == "E-PREFLIGHT"), None)
            if state_entry is None or not isinstance(state_entry.get("data"), dict):
                raise FoundationError("缺少步骤四 preflight evidence；先执行 preflight.py begin")
            preflight = state_entry["data"]
            if preflight.get("mode") == "STOPPED":
                raise FoundationError("preflight 仍为 STOPPED，不能执行测试层")
        if args.prepare_first_round and args.round != 1:
            raise FoundationError("步骤三 L1/L2 evidence 只能登记为第 1 轮")
        if not args.prepare_first_round and args.round == 1:
            if preflight.get("mode") == "FULL":
                expected_snapshot = preflight.get("sourceSha256")
                if not expected_snapshot:
                    raise FoundationError("begin 缺少工程输入快照")
                if source_snapshot(root) != expected_snapshot:
                    preflight.update({
                        "mode": "STOPPED", "stage": "source_stale",
                        "reason": "source_changed_after_begin",
                    })
                    state_entry["data"] = preflight
                    write_json_atomic(preflight_path, index)
                    raise FoundationError("begin 后工程输入已变化；返回步骤三重新完成施工检查")
        ledger = json.loads((om / "decisions.json").read_text(encoding="utf-8"))
        current = ledger["task"]["currentBatch"]
        links = [
            {"issueId": issue["issueId"]}
            for issue in ledger["issues"]
            if issue.get("batchId") == current and issue.get("changeStatus") == "modified"
        ]
        records: list[dict[str, Any]] = []
        timings: dict[str, float] = {}
        build: subprocess.CompletedProcess[str] | None = None
        static_checks: list[tuple[str, subprocess.CompletedProcess[str]]] = []
        run_l1_l2 = args.prepare_first_round or args.round > 1
        if run_l1_l2:
            build_argv = [executable, "build"]
            build, timings["L1"] = run(build_argv, root, args.timeout)

            for index, value in enumerate(args.check_script, start=1):
                script_path = Path(value)
                if not script_path.is_absolute():
                    script_path = root / script_path
                check_argv = [sys.executable, str(script_path.resolve()), str(root), "--json"]
                check, timings[f"staticCheck{index}"] = run(check_argv, root, args.timeout)
                static_checks.append((str(script_path), check))
            if args.prepare_first_round:
                check_stdout = "\n".join(item.stdout for _, item in static_checks)
                check_stderr = "\n".join(item.stderr for _, item in static_checks)
                combined_result = subprocess.CompletedProcess(
                    args=[sys.executable, str(Path(__file__).resolve()), str(root), "--prepare-first-round"],
                    returncode=0 if build.returncode == 0 and all(
                        item.returncode == 0 for _, item in static_checks
                    ) else 1,
                    stdout=(build.stdout + "\n" + check_stdout),
                    stderr=(build.stderr + "\n" + check_stderr),
                )
                records.append(command_record(
                    links, list(combined_result.args), combined_result,
                    phase="step3_foundation", source_sha256=source_snapshot(root),
                ))
            else:
                records.append(command_record(links, build_argv, build))
                for script_path, check in static_checks:
                    records.append(command_record(
                        links, [sys.executable, script_path, str(root), "--json"], check,
                    ))

        launch: subprocess.CompletedProcess[str] | None = None
        l1_l2_passed = not run_l1_l2 or (
            build is not None and build.returncode == 0
            and all(item.returncode == 0 for _, item in static_checks)
        )
        if not args.prepare_first_round and l1_l2_passed and preflight.get("mode") == "FULL":
            identifier = args.device or str((preflight.get("device") or {}).get("identifier", "")).strip()
            if not identifier:
                raise FoundationError("FULL 模式缺少已绑定设备 identifier")
            launch_argv = [executable, "run", "--device", identifier]
            launch, timings["L3"] = run(launch_argv, root, args.timeout)
            records.append(command_record(links, launch_argv, launch))

        batch = {"round": args.round, "commands": records, "artifacts": [], "results": []}
        call_session(root, "record-batch", "--input", "-", input_data=json.dumps(batch, ensure_ascii=False))

        passed = l1_l2_passed and (
            args.prepare_first_round
            or preflight.get("mode") != "FULL"
            or launch is not None and launch.returncode == 0
        )
        print(json.dumps({
            "ok": passed,
            "mode": preflight.get("mode"),
            "levels": {
                "L1": None if build is None else build.returncode,
                "staticChecks": {
                    script_path: result.returncode for script_path, result in static_checks
                },
                "L3": None if launch is None else launch.returncode,
            },
            "elapsedSeconds": {key: round(value, 3) for key, value in timings.items()},
        }, ensure_ascii=False))
        return 0 if passed else 1
    except (FoundationError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
