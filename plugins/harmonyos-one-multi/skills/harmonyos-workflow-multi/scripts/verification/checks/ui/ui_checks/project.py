"""UI 领域检查使用的源文件遍历。"""

from __future__ import annotations

import os
from typing import Iterator, Sequence

from .static_rules import Issue, run_all

# 扫描时跳过的目录。
# .preview 是 DevEco 预览器的生成产物，对生成代码报缺陷只会让 agent 去改一个
# 下次预览就会被覆盖的文件。
# .onemulti 是 skill 安装进工程的产物，不属于用户代码，与 onemulti/project.py 保持一致。
SKIP_DIRS = {
    "node_modules",
    "oh_modules",
    "build",
    ".git",
    ".hvigor",
    ".idea",
    ".preview",
    ".onemulti",
    "dist",
}

# 静态规则适用的源文件类型
SOURCE_SUFFIXES = (".ets", "module.json5", "easy_go.json")


def iter_files(root: str, suffixes: Sequence[str]) -> Iterator[str]:
    """遍历工程内以 suffixes 任一项结尾的文件，自动跳过 SKIP_DIRS。"""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(tuple(suffixes)):
                yield os.path.join(dirpath, name)


def scan_static(root: str) -> list[Issue]:
    """对整个工程跑 Tier-0 静态规则。

    规则本身只处理单文件（``run_all(path, text, relpath)``），遍历归这里——
    静态检查与改造速查都要扫同一批文件，两处各写一遍必然分叉。
    """
    issues: list[Issue] = []
    for path in iter_files(root, SOURCE_SUFFIXES):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
        except (OSError, UnicodeDecodeError):
            continue
        issues.extend(run_all(path, text, os.path.relpath(path, root)))
    return issues
