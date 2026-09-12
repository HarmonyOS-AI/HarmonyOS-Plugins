#!/usr/bin/env python3
"""记录流程构建基线，并按需运行流程内置的静态检查脚本。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))
from onemulti.json5 import loads_json5  # noqa: E402

EVIDENCE_SESSION = SCRIPT_DIR / "evidence-session.py"
SNAPSHOT_EXCLUDED = {".git", ".onemulti", ".hvigor", "build", "node_modules", "oh_modules"}


class FoundationError(ValueError):
    pass


def changed_hsp_modules(root: Path, issues: list[dict[str, Any]]) -> list[str]:
    """按本批实际修改文件定位 HSP；CLI 使用 profile 中的模块名，不使用目录名。"""
    changed = {(root / name).resolve() for issue in issues for name in issue.get("changedFiles", [])}
    profile_path = root / "build-profile.json5"
    if not changed or not profile_path.is_file():
        return []

    def read_config(path: Path) -> dict[str, Any]:
        data = loads_json5(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise FoundationError(f"无法解析模块配置: {path}")
        return data

    modules = [((root / item["srcPath"]).resolve(), item["name"])
               for item in read_config(profile_path)["modules"]]
    # 先匹配最深模块，避免嵌套模块或同名前缀目录被归入父模块。
    modules.sort(key=lambda item: len(item[0].parts), reverse=True)
    touched: dict[Path, str] = {}
    for path in changed:
        for directory, name in modules:
            if path.is_relative_to(directory):
                touched[directory] = name
                break
    return sorted({name for directory, name in touched.items()
                   if read_config(directory / "src/main/module.json5")["module"]["type"] == "shared"})


def run(command: list[str], cwd: Path, timeout: float) -> tuple[subprocess.CompletedProcess[str], float]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            command, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as error:
        output = error.stdout or ""
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        result = subprocess.CompletedProcess(
            command, 124, stdout=output, stderr=f"命令超时: {' '.join(command)}",
        )
    except OSError as error:
        result = subprocess.CompletedProcess(
            command, 127, stdout="", stderr=f"命令无法执行: {' '.join(command)}: {error}",
        )
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
        help="步骤三检查：执行 L1/L2 并登记结果；未通过不阻断进入第四步",
    )
    args = parser.parse_args()

    root = Path(args.project).resolve()
    om = root / ".onemulti"
    try:
        if not 1 <= args.round <= 5:
            raise FoundationError("round 必须为 1..5")
        executable = shutil.which(args.devecocli) or args.devecocli
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
        ledger = json.loads((om / "decisions.json").read_text(encoding="utf-8"))
        current = ledger["task"]["currentBatch"]
        modified_issues = [
            issue for issue in ledger["issues"]
            if issue.get("batchId") == current and issue.get("changeStatus") == "modified"
        ]
        links = [{"issueId": issue["issueId"]} for issue in modified_issues]
        hsp_modules: list[str] = []
        hsp_error = ""
        try:
            hsp_modules = changed_hsp_modules(root, modified_issues)
        except (FoundationError, OSError, KeyError, TypeError, UnicodeError) as error:
            # 无法确定构建范围也应记录为 L1 失败，不冒充已覆盖 HSP，不中断收尾。
            hsp_error = f"HSP 模块识别失败: {error}"
        hsp_argv = [executable, "build", "--modules", *hsp_modules]
        records: list[dict[str, Any]] = []
        timings: dict[str, float] = {}
        build: subprocess.CompletedProcess[str] | None = None
        hsp_build: subprocess.CompletedProcess[str] | None = None
        build_code: int | None = None
        static_checks: list[tuple[str, subprocess.CompletedProcess[str]]] = []
        source_sha = source_snapshot(root)
        issue_ids = {link["issueId"] for link in links}
        previous = [] if args.prepare_first_round else [
            item["data"] for item in index.get("entries", [])
            if item.get("type") == "command" and isinstance(item.get("data"), dict)
            and item["data"].get("phase") == "step3_foundation"
            and issue_ids <= {link.get("issueId") for link in item.get("links", [])}
        ]
        # 只复用本批、同源码且通过的基础检查；其余情况直接补跑，不退回施工。
        reusable = not hsp_error and bool(previous) and previous[-1].get("exitCode") == 0 \
            and previous[-1].get("sourceSha256") == source_sha
        if reusable and hsp_modules:
            # 旧版仅默认构建的成功记录，不能证明本批 HSP 已被显式编译。
            reusable = any(
                item.get("data", {}).get("phase") == "hsp_build"
                and item["data"].get("argv") == hsp_argv
                and item["data"].get("exitCode") == 0
                and item["data"].get("sourceSha256") == source_sha
                and issue_ids <= {link.get("issueId") for link in item.get("links", [])}
                for item in index.get("entries", [])
            )
        run_l1_l2 = args.prepare_first_round or args.round > 1 or not reusable
        if run_l1_l2:
            if hsp_modules:
                hsp_build, timings["L1HSP"] = run(hsp_argv, root, args.timeout)
                records.append(command_record(
                    links, hsp_argv, hsp_build, phase="hsp_build", source_sha256=source_sha,
                ))
            build_argv = [executable, "build"]
            build, timings["L1"] = run(build_argv, root, args.timeout)
            timings["L1"] += timings.get("L1HSP", 0)
            builds = ([hsp_build] if hsp_build is not None else []) + [build]
            build_code = 1 if hsp_error else next((item.returncode for item in builds if item.returncode), 0)

            for index, value in enumerate(args.check_script, start=1):
                script_path = Path(value)
                if not script_path.is_absolute():
                    script_path = root / script_path
                check_argv = [sys.executable, str(script_path.resolve()), str(root), "--json"]
                check, timings[f"staticCheck{index}"] = run(check_argv, root, args.timeout)
                static_checks.append((str(script_path), check))
            if not args.prepare_first_round:
                records.append(command_record(links, build_argv, build))
                for script_path, check in static_checks:
                    records.append(command_record(
                        links, [sys.executable, script_path, str(root), "--json"], check,
                    ))
            check_stdout = "\n".join(item.stdout for _, item in static_checks)
            check_stderr = "\n".join(item.stderr for _, item in static_checks)
            combined_result = subprocess.CompletedProcess(
                args=[sys.executable, str(Path(__file__).resolve()), str(root),
                      "--round", str(args.round), *(
                          ["--prepare-first-round"] if args.prepare_first_round else []
                      )],
                returncode=0 if build_code == 0 and all(
                    item.returncode == 0 for _, item in static_checks
                ) else 1,
                stdout="\n".join(item.stdout for item in builds) + "\n" + check_stdout,
                stderr="\n".join(item.stderr for item in builds) + "\n" + hsp_error + "\n" + check_stderr,
            )
            # 每轮都刷新基础检查结果，报告不能一直沿用施工期的旧失败。
            records.append(command_record(
                links, list(combined_result.args), combined_result,
                phase="step3_foundation", source_sha256=source_sha,
            ))

        launch: subprocess.CompletedProcess[str] | None = None
        l1_l2_passed = not run_l1_l2 or (
            build_code == 0
            and all(item.returncode == 0 for _, item in static_checks)
        )
        build_passed = not run_l1_l2 or build_code == 0
        # 无可用构建产物时不装机；静态检查失败本身不禁止收集 L3 证据。
        if not args.prepare_first_round and build_passed and preflight.get("mode") == "FULL":
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
            "hspModules": hsp_modules,
            "levels": {
                "L1": build_code,
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
