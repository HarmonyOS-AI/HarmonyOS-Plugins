#!/usr/bin/env python3
"""Reuse, start, or prepare one matching representative device."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PREFLIGHT = SCRIPT_DIR / "preflight.py"


class PrepareError(ValueError):
    pass


def run(command: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise PrepareError(f"命令超时: {' '.join(command)}") from error
    except OSError as error:
        raise PrepareError(f"命令无法执行: {' '.join(command)}: {error}") from error


def require_success(result: subprocess.CompletedProcess[str], action: str) -> str:
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise PrepareError(f"{action}失败: {detail[-1000:]}")
    return result.stdout


def load_state(root: Path) -> dict[str, Any]:
    path = root / ".onemulti" / "evidence" / "index.json"
    if not path.is_file():
        raise PrepareError("缺少 evidence/index.json")
    index = json.loads(path.read_text(encoding="utf-8"))
    entry = next((item for item in index.get("entries", []) if item.get("evidenceId") == "E-PREFLIGHT"), None)
    if entry is None or not isinstance(entry.get("data"), dict):
        raise PrepareError("缺少步骤四 preflight evidence")
    return entry["data"]


def current_plans(root: Path, batch_id: str) -> list[dict[str, str]]:
    ledger = json.loads((root / ".onemulti" / "decisions.json").read_text(encoding="utf-8"))
    return [
        {"issueId": issue["issueId"], "form": plan["form"], "checkId": plan["checkId"]}
        for issue in ledger.get("issues", []) if issue.get("batchId") == batch_id
        and issue.get("changeStatus") == "modified"
        for plan in issue.get("verificationPlan", [])
    ]


def device_rows(output: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in output.splitlines():
        columns = re.split(r"\s{2,}", line.strip())
        if len(columns) == 4 and columns[1] != "Serial" and set(columns[0]) != {"-"}:
            kind = columns[2].lower()
            if kind == "device":
                kind = "physical"
            rows.append({
                "name": columns[0], "serial": columns[1],
                "kind": kind, "deviceType": columns[3].lower(),
            })
    return rows


def json_prefix(output: str) -> Any:
    start = min((offset for offset in (output.find("["), output.find("{")) if offset >= 0), default=-1)
    if start < 0:
        raise PrepareError("模拟器枚举未返回 JSON")
    try:
        value, _ = json.JSONDecoder().raw_decode(output[start:])
        return value
    except json.JSONDecodeError as error:
        raise PrepareError("模拟器枚举返回的 JSON 无法解析") from error


def target_types(plans: list[dict[str, str]]) -> list[str]:
    forms = " ".join(str(item.get("form", "")).lower() for item in plans)
    fold = any(token in forms for token in ("fold", "triple", "expanded", "hover", "折叠", "展开", "悬停"))
    tablet = any(token in forms for token in ("tablet", "pad", "平板", "multi-window", "free-window", "多窗", "自由窗口"))
    phone = any(token in forms for token in ("phone", "handset", "手机"))
    if fold and tablet or tablet and phone:
        return ["triplefold"]
    if fold:
        return ["triplefold", "widefold", "foldable"]
    if tablet:
        return ["tablet"]
    if phone:
        return ["phone"]
    raise PrepareError("无法从冻结 verificationPlan 推导代表设备类型")


def matching(row: dict[str, str], candidates: list[str]) -> bool:
    return row.get("deviceType", "").lower() in candidates


def call_preflight(root: Path, command: str, *extra: str) -> str:
    result = run([sys.executable, str(PREFLIGHT), command, str(root), *extra], timeout=90)
    if result.returncode:
        raise PrepareError((result.stderr or result.stdout).strip())
    return result.stdout.strip()


def bind(root: Path, row: dict[str, str]) -> str:
    payload = {
        "kind": row["kind"],
        "identifier": row["serial"],
    }
    with tempfile.TemporaryDirectory(prefix="onemulti-device-") as temporary:
        path = Path(temporary) / "device.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return call_preflight(root, "bind-device", "--input", str(path))


def enumerate_devices(executable: str, timeout: float) -> list[dict[str, str]]:
    output = require_success(run([executable, "device", "list"], timeout=timeout), "设备枚举")
    return device_rows(output)


def enumerate_instances(executable: str, timeout: float) -> list[dict[str, str]]:
    output = require_success(
        run([executable, "emulator", "list", "--format", "json"], timeout=timeout),
        "模拟器实例枚举",
    )
    payload = json_prefix(output)
    if not isinstance(payload, list):
        raise PrepareError("模拟器实例列表必须为 JSON 数组")
    rows: list[dict[str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        device_type = str(item.get("deviceType", "")).strip().lower()
        if not name or not device_type:
            continue
        rows.append({
            "name": name,
            "kind": "emulator",
            "deviceType": device_type,
            "status": str(item.get("status", "stopped")).strip().lower() or "stopped",
            "osVersion": str(item.get("osVersion", "")).strip(),
        })
    return rows


def require_license(root: Path, executable: str) -> None:
    call_preflight(root, "check-license", "--devecocli", executable)
    state = load_state(root)
    if state.get("stage") != "license_accepted":
        raise PrepareError(f"模拟器 License 尚未就绪: {state.get('reason')}")


def install_required_result(candidates: list[str], warning: str | None = None) -> dict[str, Any]:
    response: dict[str, Any] = {
        "ok": True,
        "action": "install-device",
        "targetTypes": candidates,
        "next": "ask-install",
    }
    if warning:
        response["warning"] = warning
    return response


def candidate_rank(device_type: str, candidates: list[str]) -> int:
    try:
        return candidates.index(device_type.lower())
    except ValueError:
        return len(candidates)


def select_connected_device(
    connected: list[dict[str, str]], candidates: list[str], instance_name: str | None = None,
) -> dict[str, str] | None:
    matches = [row for row in connected if matching(row, candidates)]
    if instance_name:
        return next(
            (row for row in matches if row["kind"] == "emulator" and row["name"] == instance_name),
            None,
        )
    return min(
        matches,
        key=lambda row: (
            0 if row["kind"] == "physical" else 1,
            candidate_rank(row["deviceType"], candidates),
            row["name"],
            row["serial"],
        ),
        default=None,
    )


def select_installed_instance(
    instances: list[dict[str, str]], candidates: list[str], instance_name: str | None = None,
) -> dict[str, str] | None:
    matches = [item for item in instances if matching(item, candidates)]
    if instance_name:
        return next((item for item in matches if item["name"] == instance_name), None)
    return min(
        matches,
        key=lambda item: (
            0 if item.get("status") == "running" else 1,
            candidate_rank(item["deviceType"], candidates),
            item["name"],
        ),
        default=None,
    )


def downloaded(value: Any) -> bool:
    return value is True or str(value).strip().lower() == "true"


def select_image(executable: str, candidates: list[str], timeout: float) -> dict[str, Any]:
    images: list[dict[str, Any]] = []
    for device_type in candidates:
        output = require_success(
            run([
                executable, "emulator", "image", "list", "--all",
                "--device-type", device_type, "--format", "json",
            ], timeout=timeout),
            f"{device_type} 模拟器镜像枚举",
        )
        payload = json_prefix(output)
        if not isinstance(payload, list):
            raise PrepareError(f"{device_type} 模拟器镜像列表必须为 JSON 数组")
        images.extend(
            item for item in payload
            if isinstance(item, dict)
            and str(item.get("deviceType", "")).lower() == device_type
            and str(item.get("osVersion", "")).strip()
        )
    if not images:
        raise PrepareError(f"没有可用的模拟器镜像，所需类型: {candidates}")
    return next((item for item in images if downloaded(item.get("downloaded"))), images[0])


def generated_instance_name(device_type: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", device_type).strip("_") or "device"
    return f"OneMulti_{normalized}_{int(time.time())}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--devecocli", default="devecocli")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--use-device", help="使用已连接设备的 identifier")
    action.add_argument("--instance-name", help="使用已安装的模拟器实例")
    action.add_argument("--auto-install", action="store_true", help="自动安装并启动推荐模拟器")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--connect-timeout", type=float, default=300.0)
    parser.add_argument("--command-timeout", type=float, default=120.0)
    parser.add_argument("--download-timeout", type=float, default=1800.0)
    args = parser.parse_args()

    root = Path(args.project).resolve()
    executable = shutil.which(args.devecocli)
    if executable is None:
        print(json.dumps({"ok": False, "error": f"找不到 devecocli: {args.devecocli}"}, ensure_ascii=False), file=sys.stderr)
        return 2
    if args.poll_seconds <= 0 or args.connect_timeout <= 0 or args.command_timeout <= 0 or args.download_timeout <= 0:
        print(json.dumps({"ok": False, "error": "轮询间隔和各项超时必须大于 0"}, ensure_ascii=False), file=sys.stderr)
        return 2

    started_instance: str | None = None
    created_instance: str | None = None
    installed_image: dict[str, str] | None = None
    started_at = time.monotonic()
    try:
        state = load_state(root)
        if state.get("stage") not in {
            "multimodal_approved", "license_attention_required", "license_accepted",
        }:
            raise PrepareError("设备准备只能在用户确认基础测试与多模交互测试后执行")
        plans = current_plans(root, state.get("batchId", ""))
        candidates = target_types(plans)
        connected = enumerate_devices(executable, args.command_timeout)

        if args.use_device:
            selected_device = next(
                (
                    row for row in connected
                    if args.use_device in {row["serial"], row["name"]} and matching(row, candidates)
                ),
                None,
            )
            if selected_device is None:
                raise PrepareError("用户选择的设备未连接或与目标形态不匹配")
            mode = bind(root, selected_device)
            print(json.dumps({
                "ok": True, "mode": mode, "device": selected_device, "started": False,
                "elapsedSeconds": round(time.monotonic() - started_at, 3),
            }, ensure_ascii=False))
            return 0

        connected_device = select_connected_device(connected, candidates, args.instance_name)
        if connected_device is not None:
            mode = bind(root, connected_device)
            print(json.dumps({
                "ok": True, "mode": mode, "device": connected_device, "started": False,
                "elapsedSeconds": round(time.monotonic() - started_at, 3),
            }, ensure_ascii=False))
            return 0

        inspection_warning: str | None = None
        try:
            instances = enumerate_instances(executable, args.command_timeout)
        except PrepareError as error:
            instances = []
            inspection_warning = str(error)

        if inspection_warning and (args.instance_name or args.auto_install):
            raise PrepareError(inspection_warning)

        selected = select_installed_instance(instances, candidates, args.instance_name)
        if args.instance_name and selected is None:
            raise PrepareError("用户选择的模拟器未安装或与目标形态不匹配")

        if selected is None:
            if not args.auto_install:
                print(json.dumps(
                    install_required_result(candidates, inspection_warning),
                    ensure_ascii=False,
                ))
                return 0
            require_license(root, executable)
            image = select_image(executable, candidates, args.command_timeout)
            device_type = str(image["deviceType"])
            os_version = str(image["osVersion"])
            instance_name = generated_instance_name(device_type)
            if not downloaded(image.get("downloaded")):
                require_success(
                    run([
                        executable, "emulator", "image", "download",
                        "--device-type", device_type, "--os-version", os_version,
                    ], timeout=args.download_timeout),
                    "模拟器镜像下载",
                )
            require_success(
                run([
                    executable, "emulator", "create", instance_name,
                    "--device-type", device_type, "--os-version", os_version,
                ], timeout=args.command_timeout),
                "模拟器实例创建",
            )
            created_instance = instance_name
            installed_image = {"deviceType": device_type, "osVersion": os_version}
        else:
            instance_name = selected["name"]

        if selected is None or selected.get("status") != "running":
            if selected is not None:
                require_license(root, executable)
            require_success(
                run([executable, "emulator", "start", instance_name], timeout=args.command_timeout),
                "模拟器启动",
            )
            started_instance = instance_name

        deadline = time.monotonic() + args.connect_timeout
        while True:
            connected = enumerate_devices(executable, args.command_timeout)
            emulator = next(
                (row for row in connected if row["kind"] == "emulator" and row["name"] == instance_name),
                None,
            )
            if emulator is not None:
                break
            if time.monotonic() >= deadline:
                raise PrepareError(f"模拟器 {instance_name} 在 {args.connect_timeout:g} 秒内未连接")
            time.sleep(args.poll_seconds)

        mode = bind(root, emulator)
        print(json.dumps({
            "ok": True, "mode": mode, "device": emulator,
            "started": started_instance is not None,
            "created": created_instance is not None,
            "instanceName": instance_name,
            "installedImage": installed_image,
            "elapsedSeconds": round(time.monotonic() - started_at, 3),
        }, ensure_ascii=False))
        return 0
    except (PrepareError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        if started_instance is not None:
            run([executable, "emulator", "stop", started_instance], timeout=args.command_timeout)
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
