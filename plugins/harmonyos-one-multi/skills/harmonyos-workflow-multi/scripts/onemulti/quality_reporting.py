"""质量报告片段；与流程状态、报告档位和构建层级独立。"""

from html import escape

from .quality import GRADE_LABELS


def grade_label(value: str | None) -> str:
    return GRADE_LABELS.get(value, "尚未证明达到基础可用")


def render_quality(model: dict) -> str:
    quality = model.get("quality", {})
    if not quality.get("configured"):
        return '<section class="section" id="quality"><h2>适配质量</h2><p>未评估。现有修复与测试结果不等同于质量等级。</p></section>'
    esc = lambda value: escape(str(value), quote=True)
    form_rows = "".join(f'<tr><td>{esc(r["form"])}</td><td>{esc(grade_label(r["achievedGrade"]))}</td>'
                        f'<td>{r["failed"]}</td><td>{r["notVerified"]}</td></tr>' for r in quality["byForm"])
    labels = {"passed": "通过", "failed": "失败", "not_verified": "未验证", "not_applicable": "不适用"}
    rows = "".join(
        f'<tr><td>{esc(r["page"])}<br>{esc(r["form"])}</td>'
        f'<td>{esc(GRADE_LABELS[r["grade"]])}<br>{esc(r["criterionId"])} {esc(r["title"])}</td>'
        f'<td>{labels[r["status"]]}</td><td>{esc(r["reason"])}'
        f'<br>{esc(r["evidenceId"] or "")}</td></tr>' for r in quality["rows"])
    warning = f'<p>{esc(quality["coverageWarning"])}</p>' if quality.get("coverageWarning") else ""
    return (
        '<section class="section" id="quality"><h2>适配质量</h2>'
        f'<p><strong>目标：</strong>{esc(GRADE_LABELS[quality["targetGrade"]])}　'
        f'<strong>已验证达到：</strong>{esc(grade_label(quality["achievedGrade"]))}</p>'
        f'<p>标准 {esc(quality["standardVersion"])} · 仅适用于下列页面和形态；不代表整个应用认证。</p>'
        f'<p>{esc("；".join(quality["scope"]))}</p>'
        f'<p>增强专项：{esc(" / ".join(quality["enhancements"]) or "无")}</p>'
        f'<p>失败 {quality["failed"]} 项，待验证 {quality["notVerified"]} 项。'
        '已验证等级逐级计算，高级功能不能抵消基础缺陷。</p>' + warning +
        '<div class="table-wrap"><table><thead><tr><th>形态</th><th>已验证等级</th><th>失败</th><th>未验证</th>'
        f'</tr></thead><tbody>{form_rows}</tbody></table></div>'
        '<details><summary>查看标准覆盖、升级差距与证据</summary><div class="table-wrap"><table>'
        '<thead><tr><th>范围</th><th>质量要求</th><th>状态</th><th>依据</th></tr></thead>'
        f'<tbody>{rows}</tbody></table></div></details></section>'
    )
