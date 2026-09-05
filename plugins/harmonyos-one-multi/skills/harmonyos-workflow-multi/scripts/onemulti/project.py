"""HarmonyOS 页面与路由扫描的公共实现。"""

from __future__ import annotations

import os
import re
from typing import Iterator, Sequence, TypedDict

from .json5 import loads_json5

# 扫描时跳过的目录。
# .onemulti 是 skill 被安装进工程后的落脚点，不属于被检查的业务代码。
# .preview 是 DevEco 预览器的生成产物，对生成代码报缺陷只会让 agent 去改一个
# 下次预览就会被覆盖的文件。
SKIP_DIRS = {
    "node_modules",
    "oh_modules",
    "build",
    ".git",
    ".hvigor",
    ".idea",
    ".preview",
    "dist",
    ".onemulti",
}

def looks_like_harmonyos_project(root: str) -> bool:
    return os.path.isfile(os.path.join(root, "build-profile.json5")) or os.path.isfile(
        os.path.join(root, "oh-package.json5")
    )


def iter_files(root: str, suffixes: Sequence[str]) -> Iterator[str]:
    """遍历工程内以 suffixes 任一项结尾的文件，自动跳过 SKIP_DIRS。"""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(tuple(suffixes)):
                yield os.path.join(dirpath, name)


class PageRegistry(TypedDict):
    modulePath: str
    moduleName: str
    srcMainDir: str
    routes: list[str] | None  # None = 该模块没能解析出页面注册表


def _load_json5(path: str) -> object | None:
    """宽松解析一个 JSON5 文件（去注释、单引号转双引号、去尾随逗号），失败返回 None。

    不追求完整 JSON5 语法（无引号 key 不处理），只处理 HarmonyOS 工具链实际
    会生成/允许、且偏离标准 JSON 的几种写法。解析失败一律返回 None 而不是
    抛异常——调用方据此把这个文件当作"解析不出来"处理，不中断整个扫描。
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, UnicodeDecodeError):
        return None
    return loads_json5(text)


def _resolve_routes(pages_ref: object, src_main: str) -> list[str] | None:
    if not isinstance(pages_ref, str) or not pages_ref.startswith("$profile:"):
        return None
    profile_name = pages_ref.split(":", 1)[1]
    profile_path = os.path.join(src_main, "resources", "base", "profile", f"{profile_name}.json")
    profile_data = _load_json5(profile_path)
    if not isinstance(profile_data, dict):
        return None
    routes = profile_data.get("src")
    if not isinstance(routes, list):
        return None
    return [r for r in routes if isinstance(r, str)]


def find_page_registries(root: str) -> list[PageRegistry]:
    """枚举**每一个**模块（HAP/HSP），尽量解析出它的页面注册表。

    HarmonyOS 约定：``"pages": "$profile:main_pages"`` 指向同一 ``src/main`` 目录下的
    ``resources/base/profile/<name>.json``，其 ``src`` 数组是相对 ``ets/`` 的路由字符串
    （不带 ``.ets`` 后缀）。这是 SDK 固定的文件格式，不因工程而异，所以在这里做成
    确定性解析。

    **无论 routes 是否解析成功都要返回该模块**——匹配阶段要先知道"这个页面属于哪个
    模块"，再判断"这个模块有没有可用的注册表"。两步分开是因为多模块工程里，
    一个模块解析失败（缺 `pages` 字段、profile 引用失效）不该被当成"整个工程都没有
    注册表"，也不该被错误地拿别的模块的注册表去比对——那样会把"这页确实没注册"和
    "这页所在模块我们查不到注册表"混为一谈，两者需要人核实的东西完全不同。
    """
    registries: list[PageRegistry] = []
    for module_path in iter_files(root, ("module.json5",)):
        data = _load_json5(module_path)
        if not isinstance(data, dict):
            continue
        module = data.get("module")
        if not isinstance(module, dict):
            continue
        src_main = os.path.dirname(module_path)
        module_name = module.get("name")
        registries.append({
            "modulePath": os.path.relpath(module_path, root),
            "moduleName": module_name if isinstance(module_name, str) else "",
            "srcMainDir": os.path.relpath(src_main, root),
            "routes": _resolve_routes(module.get("pages"), src_main),
        })
    return registries


_DECORATOR_ARGS = r"(?:\([^)]*\))?"
_ENTRY_STRUCT_RE = re.compile(
    rf"@Entry{_DECORATOR_ARGS}\s*(?:@\w+{_DECORATOR_ARGS}\s*)*struct\s+(\w+)"
)


def list_entry_components(root: str) -> list[tuple[str, str]]:
    """找出所有 ``@Entry`` 装饰的 struct，返回 ``[(相对路径, 组件名), ...]``。

    只做词法匹配，不解析 ArkTS 语法树——和 ``static_rules.py`` 的一贯做法一致：
    结构性判据在真实工程上容易因格式差异跑飞，正则能覆盖的判据才收进来。
    """
    results: list[tuple[str, str]] = []
    for path in iter_files(root, (".ets",)):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
        except (OSError, UnicodeDecodeError):
            continue
        relpath = os.path.relpath(path, root)
        for match in _ENTRY_STRUCT_RE.finditer(text):
            results.append((relpath, match.group(1)))
    return results


_STRUCT_RE = re.compile(r"\bstruct\s+(\w+)")


def list_nav_destination_components(root: str) -> list[tuple[str, str]]:
    """找出所有出现 ``NavDestination(`` 的 struct，返回 ``[(相对路径, 组件名), ...]``。

    `NavDestination` 包装的页面是 `Navigation`/`NavPathStack` 动态路由的目标页，
    按设计就不进 `main_pages.json`——`list_entry_components` 天生找不到它们。
    实测华为官方 demo 工程（NewsTemplate/ComprehensiveNews）里，这类页面
    （62 个文件）比 `@Entry` 页面（6 个）多一个数量级，漏掉这条信号会让
    页面清单在真实工程上只覆盖一成不到。

    只做子串匹配 + 就近 struct 名关联（取 `NavDestination(` 前最后一个 struct
    声明），不做括号配对定界——和 `static_rules.py` 反复踩过的坑一样，
    括号配对一遇注释里的 `{` 就跑飞，字符级别的结构判据在真实工程上不可靠。
    一个文件里若真有多个 struct 且关联算错，代价是拿错组件名，
    候选页面本身不会漏——分类阶段本来就要人/AI 核实这一类。
    """
    results: list[tuple[str, str]] = []
    for path in iter_files(root, (".ets",)):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
        except (OSError, UnicodeDecodeError):
            continue
        nav_pos = text.find("NavDestination(")
        if nav_pos == -1:
            continue
        owner = None
        for match in _STRUCT_RE.finditer(text):
            if match.start() > nav_pos:
                break
            owner = match.group(1)
        if owner is None:
            continue
        results.append((os.path.relpath(path, root), owner))
    return results


CONFIDENCE_REGISTERED = "registered"
CONFIDENCE_UNREGISTERED = "entry-unregistered"
CONFIDENCE_NO_REGISTRY = "no-registry-found"
CONFIDENCE_HEURISTIC = "heuristic"

KIND_ENTRY = "entry"
KIND_NAV_DESTINATION = "nav-destination"


class PageCandidate(TypedDict):
    path: str
    component: str
    kind: str
    module: str | None
    registeredRoute: str | None
    confidence: str
    type: None


def _match_module(relpath: str, registries: list[PageRegistry]) -> PageRegistry | None:
    """按 srcMainDir 最长前缀匹配，把页面归到它所属的 HAP/HSP 模块。"""
    best: PageRegistry | None = None
    for registry in registries:
        prefix = registry["srcMainDir"] + os.sep
        if relpath.startswith(prefix) and (best is None or len(registry["srcMainDir"]) > len(best["srcMainDir"])):
            best = registry
    return best


def _expected_route(relpath: str, src_main_dir: str) -> str | None:
    ets_prefix = os.path.join(src_main_dir, "ets") + os.sep
    if not relpath.startswith(ets_prefix):
        return None
    route = relpath[len(ets_prefix):]
    if route.endswith(".ets"):
        route = route[: -len(".ets")]
    return route.replace(os.sep, "/")


def build_page_inventory(root: str) -> list[PageCandidate]:
    """把两种发现信号拼成候选页面清单：`@Entry`（静态注册）与 `NavDestination`
    （动态路由目标页，`kind` 字段区分）。

    共享给 `project-scan.py`（CLI）与回归测试，遍历/匹配逻辑只保留一份。
    **不做页面类型分类**，那部分
    因工程而异，交给 `references/page-inventory.md` 引导 AI 完成。
    """
    registries = find_page_registries(root)
    candidates: list[PageCandidate] = []
    for relpath, component in list_entry_components(root):
        module = _match_module(relpath, registries)
        if module is None or module["routes"] is None:
            candidates.append({
                "path": relpath,
                "component": component,
                "kind": KIND_ENTRY,
                "module": module["moduleName"] if module else None,
                "registeredRoute": None,
                "confidence": CONFIDENCE_NO_REGISTRY,
                "type": None,
            })
            continue

        route = _expected_route(relpath, module["srcMainDir"])
        registered = route is not None and route in module["routes"]
        candidates.append({
            "path": relpath,
            "component": component,
            "kind": KIND_ENTRY,
            "module": module["moduleName"],
            "registeredRoute": route if registered else None,
            "confidence": CONFIDENCE_REGISTERED if registered else CONFIDENCE_UNREGISTERED,
            "type": None,
        })

    for relpath, component in list_nav_destination_components(root):
        module = _match_module(relpath, registries)
        candidates.append({
            "path": relpath,
            "component": component,
            "kind": KIND_NAV_DESTINATION,
            "module": module["moduleName"] if module else None,
            "registeredRoute": None,
            "confidence": CONFIDENCE_HEURISTIC,
            "type": None,
        })

    candidates.sort(key=lambda c: (c["path"], c["kind"]))
    return candidates
