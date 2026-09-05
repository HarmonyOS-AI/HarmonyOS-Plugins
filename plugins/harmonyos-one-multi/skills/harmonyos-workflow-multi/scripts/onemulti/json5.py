"""HarmonyOS 配置文件使用到的轻量 JSON5 解析器。"""

from __future__ import annotations

import json
import re


_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")


def normalize_json5(text: str) -> str:
    """移除注释、转换单引号字符串并清理尾随逗号。"""
    result: list[str] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            result.append(ch)
            i += 1
            escaped = False
            while i < n:
                current = text[i]
                i += 1
                result.append(current)
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == '"':
                    break
            continue
        if ch == "'":
            i += 1
            content: list[str] = []
            escaped = False
            while i < n:
                current = text[i]
                i += 1
                if escaped:
                    content.append(current if current == "'" else "\\" + current)
                    escaped = False
                    continue
                if current == "\\":
                    escaped = True
                    continue
                if current == "'":
                    break
                content.append(current)
            result.append('"' + "".join(content).replace('"', '\\"') + '"')
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        result.append(ch)
        i += 1
    return _TRAILING_COMMA_RE.sub(r"\1", "".join(result))


def loads_json5(text: str) -> object | None:
    """解析本 Skill 所需的 JSON5 子集；失败时返回 ``None``。"""
    try:
        return json.loads(normalize_json5(text))
    except json.JSONDecodeError:
        return None
