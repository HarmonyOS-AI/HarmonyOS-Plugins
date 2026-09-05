"""Tier-0 静态规则集：源码级检查，不需要设备。

**范围只有多设备适配写法。** ArkTS 语法、类型、命名、性能一概不查——那是 devecocli
的职责（``devecocli build`` 与 ``devecocli serve mcp`` 的 check 工具）。往这里加规则前
先问一句：这条规则换到直板机单设备工程上还成立吗？成立就说明它不属于本文件。

**准入门槛**

这里只保留少量高置信规则。被排除的规则通常有同一个失败模式：

    **正则拿不到语法结构，却对语义下结论。**

- S6 判 ``layoutWeight`` 与显式宽高互斥，但主轴方向取决于父容器是 Row 还是 Column，
  正则看不到父容器；实测 83 次命中全是 Row 内的交叉轴 ``height``，且换行写法才触发，
  规则实际检测的是代码格式而不是语义。
- S10/S11 依赖字符级括号配对来划定代码块，一行含 ``{`` 的注释就让边界跑飞；
  S11 更会在开发者按建议改对之后继续报错，直接烧穿自动修复循环。
- S8 把官方推荐的 ``.lanes({minLength, maxLength})`` 判成多列。
- S1/S2/S3/S4/S9/S12 把合法配置、官方 API 选项、用户自定义类名判成缺陷。

因此准入门槛是硬的，**以下四项全部满足才能加进来**：

1. 判据不依赖父节点类型、作用域或代码块边界——正则或真解析能完整覆盖判据。
2. 在真实工程语料上跑过，命中即真阳（或已用白名单把假阳压到零）。
3. 同时提供阳性样本和“看起来像但其实正常”的阴性自动化用例。
4. 拿不准就不要加。**漏报只是少查一条，误报会让开发者不再信任整个工具。**

规则签名：``fn(path: str, text: str) -> list[Issue]``，单文件处理，引擎负责遍历。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable

from .device_types import declaration_errors, module_object
from .json5 import loads_json5

SEVERITY_FAIL = "FAIL"
SEVERITY_WARN = "WARN"


@dataclass
class Issue:
    rule: str
    severity: str
    title: str
    file: str
    line: int
    snippet: str
    detail: str
    suggestion: str

    def to_dict(self) -> dict:
        return {
            "rule": self.rule, "severity": self.severity, "title": self.title,
            "file": self.file, "line": self.line, "snippet": self.snippet,
            "detail": self.detail, "suggestion": self.suggestion,
        }


@dataclass(frozen=True)
class StaticRuleMeta:
    rule_id: str
    title: str
    severity: str
    suffixes: tuple[str, ...]


_RULES: list[Callable] = []


def static_rule(rule_id: str, title: str, severity: str, suffixes: tuple[str, ...] = (".ets",)):
    def decorator(fn: Callable) -> Callable:
        fn.meta = StaticRuleMeta(rule_id, title, severity, suffixes)
        _RULES.append(fn)
        return fn
    return decorator


def registered_rules() -> list[StaticRuleMeta]:
    return [fn.meta for fn in _RULES]


def _blank(text: str, comments: bool = False, strings: bool = False) -> str:
    """把注释和/或字符串字面量替换成等长空白，换行一律保留。

    等长替换保证后续正则的偏移与行号仍然对应原文，因此规则不需要做任何位置换算。

    - ``comments=True``：注释里出现 API 名是文档化的常态（``foo()  // 别用
      KeyboardAvoidMode.PAN``、文件头注释里写 ``display.on('foldStatusChange')``
      说明用途），**按注释判缺陷一定是误报**。
    - ``strings=True``：日志、错误提示、迁移备忘里提到 API 名同样不是"使用"。
      只有 S5 需要它——S16 恰恰要在字符串字面量里匹配 lpx 单位，全局擦掉就废了。

    扫描时始终跟踪字符串状态，避免把 URL 里的 ``//`` 当成注释开头。模板字符串的
    ``${}`` 内如果含引号会让状态错位，后果是少擦掉一段，方向是漏报而非误报。
    """
    out = list(text)
    i, n = 0, len(text)
    quote = ""  # 当前所处的字符串引号；"" 表示不在字符串内
    while i < n:
        ch = text[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = ""
            elif strings and ch != "\n":
                out[i] = " "
            i += 1
            continue
        if ch in "'\"`":
            quote = ch
            i += 1
            continue
        if comments and ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                out[i] = " "
                i += 1
            continue
        if comments and ch == "/" and i + 1 < n and text[i + 1] == "*":
            while i < n and not (text[i] == "*" and i + 1 < n and text[i + 1] == "/"):
                if text[i] != "\n":
                    out[i] = " "
                i += 1
            for _ in range(2):
                if i < n:
                    out[i] = " "
                    i += 1
            continue
        i += 1
    return "".join(out)


def run_all(path: str, text: str, rel: str) -> list[Issue]:
    scan_text = _blank(text, comments=True) if path.endswith(".ets") else text
    issues: list[Issue] = []
    for fn in _RULES:
        if not path.endswith(fn.meta.suffixes):
            continue
        issues.extend(fn(rel, scan_text))
    return issues


def _line_of(text: str, pos: int) -> int:
    return text[:pos].count("\n") + 1


def _issue(meta: StaticRuleMeta, rel: str, text: str, pos: int, snippet: str,
           detail: str, suggestion: str) -> Issue:
    return Issue(meta.rule_id, meta.severity, meta.title, rel, _line_of(text, pos),
                 snippet.strip().replace("\n", " ")[:90], detail, suggestion)


# --- S5 幻觉 API -------------------------------------------------------------
#
# `GridRow.onBreakpointChange` 是 API 11 起存在的官方 API，不得列入黑名单。
# SDK 声明文件：
#     ets/component/grid_row.d.ts:1000
#     onBreakpointChange(callback: (breakpoints: string) => void): GridRowAttribute;  // @since 11
# 该 API 从 API 11 起就真实存在。
#
# 错误的黑名单比没有黑名单更糟——它会禁掉本来可用的 API，把开发者推向更绕的写法。
#
# 因此：**往 HALLUCINATED_APIS 里加任何条目前，必须先在 SDK 的 .d.ts 里
# grep 确认其不存在，并把 grep 命令与结果写进注释。** 二手说法不算证据。
HALLUCINATED_APIS: dict[str, tuple[str, str]] = {
    # 方法调用形式（匹配 `.symbolName(`）。目前为空。加条目的格式：
    #   "symbolName": ("完整名称", "为什么不能用 + 替代方案"),
    # 附带证据注释：
    #   grep -rn "symbolName" <SDK>/ets/component/*.d.ts   → 无命中
}

HALLUCINATED_MEMBERS: dict[str, tuple[str, str]] = {
    # 枚举成员形式（匹配 `Enum.MEMBER`）。规则同上：**必须先 grep 实证**。
    #
    # 证据（HarmonyOS SDK, DevEco default/openharmony）：
    #   sed -n '5631,5700p' ets/api/@ohos.arkui.UIContext.d.ts | grep -E '^\s*[A-Z_]+ ='
    #   → OFFSET=0 / RESIZE=1 / OFFSET_WITH_CARET=2 / RESIZE_WITH_CARET=3 / NONE=4
    #   PAN 无命中。它出现在华为 avoid-areas skill 的 AVOID-04 决策里，
    #   疑似从 Android 的 adjustPan 串过来。
    "KeyboardAvoidMode.PAN": (
        "KeyboardAvoidMode.PAN",
        "该枚举成员不存在（实际只有 OFFSET / RESIZE / OFFSET_WITH_CARET / "
        "RESIZE_WITH_CARET / NONE），疑似与 Android 的 adjustPan 混淆",
    ),
}


@static_rule("S5", "使用了不存在的 API", SEVERITY_FAIL)
def hallucinated_api(rel: str, text: str) -> list[Issue]:
    # 日志、错误提示、迁移备忘里提到 API 名不是"使用"，擦掉字符串再匹配。
    # 注释已由 run_all 擦过，这里只需再擦字符串；行号仍对应原文。
    text = _blank(text, strings=True)
    out = []
    for symbol, (full, why) in HALLUCINATED_APIS.items():
        for m in re.finditer(rf"\.\s*{re.escape(symbol)}\s*\(", text):
            out.append(_issue(hallucinated_api.meta, rel, text, m.start(), m.group(0),
                              f"{full}：{why}",
                              "以 SDK 声明文件为准；训练数据里记得的 API 不等于真实存在"))
    for symbol, (full, why) in HALLUCINATED_MEMBERS.items():
        for m in re.finditer(rf"\b{re.escape(symbol)}\b", text):
            out.append(_issue(hallucinated_api.meta, rel, text, m.start(), m.group(0),
                              f"{full}：{why}",
                              "以 SDK 声明文件为准；训练数据里记得的 API 不等于真实存在"))
    return out


# --- S13 平行视界配置互斥 ----------------------------------------------------
# 出处: easy_go.json 配置规格
#
# 走 json.loads 真解析。全部判据都是**同一配置对象内部的结构性矛盾**——不依赖
# 语法结构、不依赖跨文件上下文，因此命中即真阳。
#
# 新增判据只挂在 routerSplitOptions / navigationSplitOptions 的**值对象**上，
# 不是全文搜 key：easy_go.json 里别处也可能出现叫 mode 的字段，
# 只有分栏选项对象里的 mode 才是平行视界的分栏模式。
SPLIT_OPTION_KEYS = ("routerSplitOptions", "navigationSplitOptions")

# mode 是 number 枚举（API 26）：0 购物模式 / 1 导航模式。
_EASY_GO_MODES = (0, 1)
# 两个"开小口子"的字段，各自只在对侧模式下有意义，配反了静默不生效。
_MODE_ONLY_KEYS = {"pagePairs": 1, "transPages": 0}
# ratio 形如 "2 | 1"，竖线前后必须各有一个空格。
_SPLIT_RATIO = re.compile(r"^\d+ \| \d+$")
# splitDividerColor 是 #AARRGGBB 八位十六进制，AA 不能省。
_ARGB_COLOR = re.compile(r"^#[0-9a-fA-F]{8}$")


def _check_split_options(rule_meta, rel: str, opts: dict, path: str) -> list[Issue]:
    """校验单个 *SplitOptions 对象的内部自洽性。"""
    out: list[Issue] = []

    def fail(detail: str, suggestion: str, where: str) -> None:
        out.append(Issue(rule_meta.rule_id, SEVERITY_FAIL, rule_meta.title,
                         rel, 1, where, detail, suggestion))

    mode = opts.get("mode")
    if mode is not None:
        # bool 是 int 的子类，True 会被当成 1，必须显式排除。
        if isinstance(mode, bool) or not isinstance(mode, int) or mode not in _EASY_GO_MODES:
            fail(f"mode 取值 {mode!r} 不合法，它是 number 枚举：0 购物模式 / 1 导航模式",
                 "改成 0 或 1；注意是数字不是字符串", f"{path}.mode")
        else:
            for key, required_mode in _MODE_ONLY_KEYS.items():
                if key in opts and mode != required_mode:
                    other = "购物模式" if required_mode == 0 else "导航模式"
                    fail(f"{key} 只在 mode={required_mode}（{other}）下生效，当前 mode={mode}",
                         f"删掉 {key}，或把 mode 改成 {required_mode}",
                         f"{path}.{key}")

    for key in ("wideSplit", "squareSplit"):
        ratio = opts.get(key)
        if isinstance(ratio, dict) and isinstance(ratio.get("ratio"), str):
            if not _SPLIT_RATIO.match(ratio["ratio"]):
                fail(f"{key}.ratio 为 {ratio['ratio']!r}，格式必须是 \"左 | 右\"，竖线前后各一个空格",
                     '写成 "2 | 1" 这种形式；少一个空格整条配置静默不生效',
                     f"{path}.{key}.ratio")

    divider = opts.get("splitDividerColor")
    if isinstance(divider, dict):
        for scheme in ("light", "dark"):
            value = divider.get(scheme)
            if isinstance(value, str) and not _ARGB_COLOR.match(value):
                fail(f"splitDividerColor.{scheme} 为 {value!r}，必须是 #AARRGGBB 八位十六进制",
                     "补上两位透明度前缀，例如 #FFE5E5E5；六位写法不生效",
                     f"{path}.splitDividerColor.{scheme}")

    return out


@static_rule("S13", "平行视界配置冲突", SEVERITY_FAIL, suffixes=("easy_go.json",))
def easy_go_conflict(rel: str, text: str) -> list[Issue]:
    out = []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []

    def walk(obj, path="$"):
        if isinstance(obj, dict):
            if all(k in obj for k in SPLIT_OPTION_KEYS):
                out.append(Issue(
                    easy_go_conflict.meta.rule_id, SEVERITY_FAIL,
                    easy_go_conflict.meta.title, rel, 1, path,
                    "routerSplitOptions 与 navigationSplitOptions 不能同时存在于同一配置块",
                    "按工程实际使用的路由框架二选一；开启平行视界后也不能混用 Router 与 Navigation",
                ))
            for key in SPLIT_OPTION_KEYS:
                opts = obj.get(key)
                if isinstance(opts, dict):
                    out.extend(_check_split_options(
                        easy_go_conflict.meta, rel, opts, f"{path}.{key}"))
            for k, v in obj.items():
                walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, f"{path}[{i}]")

    walk(data)
    return out


# --- S15 字号字面量低于 UI 基线 ------------------------------------------------
# 出处: UI 质量检查 QC-11，见 references/quality-checklist.md
#
# 只覆盖字面量写法——变量、$r() 资源引用漏得掉，因此 QC-11 整体仍需人判。
# 判据是纯数值比较，不依赖任何上下文；在 358 个真实文件上 0 命中。
MIN_FONT_SIZE_VP = 8
"""手机、折叠屏和平板使用的最低字号基线（vp）。"""

_FONT_SIZE_LITERAL = re.compile(r"\.fontSize\s*\(\s*(\d+(?:\.\d+)?)\s*\)")


@static_rule("S15", "字号低于上架下限", SEVERITY_FAIL)
def font_size_too_small(rel: str, text: str) -> list[Issue]:
    out = []
    for m in _FONT_SIZE_LITERAL.finditer(text):
        if float(m.group(1)) >= MIN_FONT_SIZE_VP:
            continue
        out.append(_issue(font_size_too_small.meta, rel, text, m.start(), m.group(0),
                          f"字号 {m.group(1)}vp 低于上架下限 {MIN_FONT_SIZE_VP}vp"
                          "（QC-11 强制项）",
                          f"至少改到 {MIN_FONT_SIZE_VP}vp，正文推荐 12vp 以上；"
                          "SymbolGlyph 的 fontSize 同样受此约束"))
    return out


# --- S16 字号使用 lpx 单位 ---------------------------------------------------
# 出处: lpx 是大屏字体异常放大的头号原因（质量问题案例）
#
# lpx 按"实际宽度 / designWidth"缩放，屏幕越宽字越大。用在尺寸上尚可讨论，
# 用在字号上必然导致平板与展开态文字巨大。
# 正则要求引号紧跟 `(`，不会误伤 $r() 资源引用；在 358 个真实文件上 0 命中。
_FONT_SIZE_LPX = re.compile(r"\.fontSize\s*\(\s*['\"`][^'\"`]*lpx")


@static_rule("S16", "字号使用 lpx 单位", SEVERITY_WARN)
def font_size_lpx(rel: str, text: str) -> list[Issue]:
    return [
        _issue(font_size_lpx.meta, rel, text, m.start(), m.group(0),
               "字号用 lpx 会随屏幕宽度等比放大，平板与折叠展开态上文字会显著过大"
               "（大屏字体异常放大的头号原因）",
               "字号改用 fp/vp；需要随断点变化时用 BreakpointType 按断点取值，"
               "而不是让单位替你做缩放")
        for m in _FONT_SIZE_LPX.finditer(text)
    ]


# --- S17 模块目标设备声明 ----------------------------------------------------
# module.json5 是 HAP/HAR/HSP 的安装能力边界。缺少 deviceTypes，或把折叠屏
# 写成 foldable，会导致包无法安装到目标设备。此规则只检查单文件内可确定的
# 声明合法性；是否覆盖当前目标形态由 check-device-types.py 判断。
@static_rule(
    "S17", "模块设备类型声明缺失或错误", SEVERITY_FAIL,
    suffixes=("module.json5",),
)
def module_device_types(rel: str, text: str) -> list[Issue]:
    module = module_object(loads_json5(text))
    if module is None:
        return []  # 配置语法错误由 devecocli build 负责
    errors = declaration_errors(module)
    if not errors:
        return []
    key = re.search(r"[\"']deviceTypes[\"']\s*:", text)
    position = key.start() if key else 0
    snippet = key.group(0) if key else "module.deviceTypes"
    return [
        _issue(
            module_device_types.meta, rel, text, position, snippet, detail,
            '按目标形态声明：手机/折叠屏使用 "phone" 或 "default"，平板使用 '
            '"tablet"；不要把未要求的设备类型写死',
        )
        for detail in errors
    ]
