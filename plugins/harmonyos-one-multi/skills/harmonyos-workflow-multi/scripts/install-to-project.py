#!/usr/bin/env python3
"""把一多流程 Skill 安装到目标 HarmonyOS 工程内。

**为什么需要这个脚本**：多数 agent 运行环境（opencode、CI 沙箱、容器）
会把文件访问限制在项目目录内。实测 opencode 1.15.3 直接拒绝读取项目外路径::

    permission requested: external_directory (/path/to/skill/*); auto-rejecting

因此 skill 必须能被安装进工程，而不是靠绝对路径引用。

安装内容（不含 evals 测试数据）::

    <工程>/.onemulti/{SKILL.md,assets/,references/,scripts/}

安装后会把 ``/.onemulti/`` 幂等追加到工程根 ``.gitignore``，避免账本、证据、报告和
Skill 副本出现在开发者的 Git 修改列表中；已有忽略规则保持不变。

同目录下的 decisions.json 是工程数据：首次安装时创建空账本，重装时保留不动。若为非常规路由工程生成过
`.onemulti/page-scan-extra.py`（见 references/page-inventory.md），同样保留不动——
本脚本只替换 SKILL.md/assets/references/scripts 四项，`.onemulti/` 下的
其它文件不受影响。

用法::

    python3 install-to-project.py <工程根>

退出码: 0 = 安装完成, 2 = 输入错误。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from onemulti.project import looks_like_harmonyos_project  # noqa: E402

# 只有这些是 skill 代码；decisions.json 属于工程数据
INSTALLED_ITEMS = ("SKILL.md", "assets", "references", "scripts")
REQUIRED_RUNTIME_FILES = (
    "scripts/project-scan.py",
    "scripts/task-ledger.py",
    "scripts/render-report.py",
    "scripts/verification/preflight.py",
    "scripts/verification/evidence-session.py",
    "scripts/verification/prepare-device.py",
    "scripts/verification/run-foundation.py",
    "scripts/verification/checks/ui/static-check.py",
    "scripts/verification/checks/ui/check-device-types.py",
    "scripts/validate-state.py",
)

GITIGNORE_ENTRY = "/.onemulti/"
EQUIVALENT_GITIGNORE_ENTRIES = {".onemulti", ".onemulti/", "/.onemulti", GITIGNORE_ENTRY}

INITIAL_LEDGER = {
    "schemaVersion": 3,
    "task": None,
    "decisions": [],
    "pages": {},
    "batches": [],
    "issues": [],
}

def copy_skill(skill_dir: str, dest: str) -> None:
    """只替换代码部分。

    decisions.json（决策账本）、evidence/（采集证据）、page-scan-extra.py
    （非常规路由工程的补充扫描脚本，若生成过）是**工程数据**，
    重装 skill 绝不能把它们删掉——决策账本丢失意味着此前所有人工确认作废。
    """
    os.makedirs(dest, exist_ok=True)
    for item in INSTALLED_ITEMS:
        source = os.path.join(skill_dir, item)
        if not os.path.exists(source):
            continue
        target = os.path.join(dest, item)
        if os.path.isdir(source):
            shutil.rmtree(target, ignore_errors=True)
            shutil.copytree(
                source,
                target,
                ignore=shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc", "*.pyo"),
            )
        else:
            shutil.copy2(source, target)


def prune(dest: str) -> None:
    """清掉系统元数据、Python 缓存与自身安装脚本（装完就不需要了）。"""
    for dirpath, dirnames, filenames in os.walk(dest, topdown=True):
        for name in list(dirnames):
            if name == "__pycache__":
                shutil.rmtree(os.path.join(dirpath, name), ignore_errors=True)
                dirnames.remove(name)
        for name in filenames:
            if name == ".DS_Store" or name.endswith((".pyc", ".pyo")):
                os.remove(os.path.join(dirpath, name))

    installer = os.path.join(dest, "scripts", os.path.basename(__file__))
    if os.path.isfile(installer):
        os.remove(installer)


def initialize_ledger(dest: str) -> None:
    """首次安装时原子创建空账本；重装时完整保留已有账本。"""
    ledger = os.path.join(dest, "decisions.json")
    if os.path.exists(ledger):
        return
    pending = ledger + ".tmp"
    with open(pending, "w", encoding="utf-8") as handle:
        json.dump(INITIAL_LEDGER, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.replace(pending, ledger)


def ensure_project_gitignore(target: str) -> None:
    """忽略工程根的 .onemulti，保留原文件并避免重复追加等价规则。"""
    gitignore = os.path.join(target, ".gitignore")
    existing = ""
    if os.path.isfile(gitignore):
        with open(gitignore, "r", encoding="utf-8", errors="replace") as handle:
            existing = handle.read()
        rules = {
            line.strip()
            for line in existing.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        if rules & EQUIVALENT_GITIGNORE_ENTRIES:
            print(f".gitignore 已忽略 .onemulti，跳过: {gitignore}")
            return

    with open(gitignore, "a", encoding="utf-8") as handle:
        if existing and not existing.endswith(("\n", "\r")):
            handle.write("\n")
        handle.write(f"{GITIGNORE_ENTRY}\n")
    print(f"已追加忽略规则 {GITIGNORE_ENTRY}: {gitignore}")


def mark_executable(dest: str) -> None:
    """给脚本加执行位。Windows 无此概念，直接跳过。"""
    if os.name == "nt":
        return
    scripts = os.path.join(dest, "scripts")
    for dirpath, _, filenames in os.walk(scripts) if os.path.isdir(scripts) else []:
        for name in filenames:
            path = os.path.join(dirpath, name)
            if name.endswith(".py"):
                mode = os.stat(path).st_mode
                os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def missing_runtime_files(dest: str) -> list[str]:
    """Return required runtime entries absent from the installed project copy."""
    return [path for path in REQUIRED_RUNTIME_FILES if not os.path.isfile(os.path.join(dest, *path.split("/")))]


def measure(dest: str) -> tuple[int, int]:
    """返回 (文件数, 总字节数)。"""
    count = total = 0
    for dirpath, _, filenames in os.walk(dest):
        for name in filenames:
            path = os.path.join(dirpath, name)
            try:
                total += os.path.getsize(path)
            except OSError:
                continue
            count += 1
    return count, total


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "K", "M"):
        if value < 1024:
            return f"{value:.0f}B" if unit == "B" else f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}G"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("target", help="HarmonyOS 工程根目录")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.target):
        print(f"找不到目标目录: {args.target}", file=sys.stderr)
        return 2

    # 粗检是否为 HarmonyOS 工程——装错地方比装不上更麻烦
    if not looks_like_harmonyos_project(args.target):
        print(
            f"警告: {args.target} 下没有 build-profile.json5 / oh-package.json5，",
            file=sys.stderr,
        )
        print("      看起来不是 HarmonyOS 工程根目录。若确认无误可忽略。", file=sys.stderr)

    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dest = os.path.join(args.target, ".onemulti")

    copy_skill(skill_dir, dest)
    prune(dest)
    initialize_ledger(dest)
    ensure_project_gitignore(args.target)
    mark_executable(dest)
    if missing := missing_runtime_files(dest):
        print(f"安装缺少必要验证入口: {missing}", file=sys.stderr)
        return 2

    count, total = measure(dest)
    print(f"已安装: {dest}（{count} 个文件 / {human_size(total)}）")

    print(f"""
下一步:
  1. 读取流程说明  {os.path.join(dest, 'SKILL.md')}
  2. 建立构建基线  devecocli build
  3. 按问题加载独立领域 Skill""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
