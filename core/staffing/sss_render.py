"""
core/staffing/sss_render.py — AF Form 1768 coversheet rendering for INFO
(read-ahead) reports: AM/EOD brief, ELON Tech Vanguard, Incubator, intel,
competitive surveillance. These are informational products, not gated action
packages — see the Commander's directive captured in
/home/john/.claude/plans/ok-using-the-staff-mossy-heron.md and the cross-Hale
review at docs/ag_sss_migration_review_20260719.md.

Deliberately independent of `core/staffing/staff_summary_sheet.py`: this
module never opens a mission-board SSS, never touches mission_board.json,
and has no Silver/cross-Hale dependency. INFO reports don't earn a gated
lifecycle — they render in the five-heading 1768 format (Subject / Purpose /
Background / Discussion / Recommendation) plus a staffing-attribution line,
and go out through whatever send path already exists for that report.
"""
from __future__ import annotations

from typing import Optional

_NAVY = "#1a3557"
_CREAM = "#f7f3ea"


def render_info_html(
    *,
    subject: str,
    opr: str,
    staffed_by: list[str],
    purpose: str,
    background: str = "",
    discussion_html: str = "",
    recommendation: str = "",
    tag: str = "",
) -> str:
    """Render an INFO-type 1768 coversheet as HTML, wrapping an existing
    report's already-built HTML body verbatim under Discussion. Chrome only —
    the caller's own send path is untouched."""
    staffed_line = ", ".join(staffed_by) if staffed_by else "—"
    parts = [
        f'<div style="font-family:Georgia,serif;color:{_NAVY};background:{_CREAM};'
        f'padding:24px;max-width:760px">',
        f'<div style="background:{_NAVY};color:#fff;padding:12px 16px;margin-bottom:16px">',
        f'<div style="font-size:16px;font-weight:bold">STAFF SUMMARY SHEET — INFO'
        + (f' ({tag})' if tag else '') + '</div>',
        f'<div style="font-size:12px">SUBJECT: {subject}</div>',
        '</div>',
        f'<p style="margin:4px 0"><b>OPR:</b> {opr} &nbsp; <b>STAFFED BY:</b> {staffed_line} '
        '&nbsp; <b>ACTION:</b> INFO</p>',
        f'<h3 style="color:{_NAVY};margin-bottom:4px">Purpose</h3>'
        f'<p style="margin-top:0">{purpose}</p>',
    ]
    if background:
        parts.append(f'<h3 style="color:{_NAVY};margin-bottom:4px">Background</h3>'
                     f'<p style="margin-top:0">{background}</p>')
    parts.append(f'<h3 style="color:{_NAVY};margin-bottom:4px">Discussion</h3>')
    parts.append(discussion_html or '<p style="margin-top:0">(no content)</p>')
    if recommendation:
        parts.append(f'<h3 style="color:{_NAVY};margin-bottom:4px">Recommendation</h3>'
                     f'<p style="margin-top:0">{recommendation}</p>')
    parts.append(
        '<p style="font-size:11px;color:#888;border-top:1px solid #ccc;'
        'padding-top:8px;margin-top:20px">This is a read-ahead / informational '
        'product — no action, decision, or gate applies.</p>'
    )
    parts.append('</div>')
    return "\n".join(parts)


def render_info_text(
    *,
    subject: str,
    opr: str,
    staffed_by: list[str],
    purpose: str,
    background: str = "",
    discussion: str = "",
    recommendation: str = "",
    tag: str = "",
) -> str:
    """Render an INFO-type 1768 coversheet as plain text/Markdown-safe, for
    Telegram or other non-HTML transports."""
    staffed_line = ", ".join(staffed_by) if staffed_by else "—"
    L = [
        f"STAFF SUMMARY SHEET — INFO" + (f" ({tag})" if tag else ""),
        f"SUBJECT: {subject}",
        f"OPR: {opr} | STAFFED BY: {staffed_line} | ACTION: INFO",
        "",
        "PURPOSE",
        purpose,
    ]
    if background:
        L += ["", "BACKGROUND", background]
    L += ["", "DISCUSSION", discussion or "(no content)"]
    if recommendation:
        L += ["", "RECOMMENDATION", recommendation]
    L += ["", "— read-ahead / informational product — no action, decision, or gate applies —"]
    return "\n".join(L)


if __name__ == "__main__":
    # This module must never depend on the gated SSS engine or mission board —
    # parse actual import statements (docstring prose mentions those names too).
    import ast
    with open(__file__) as f:
        tree = ast.parse(f.read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(n.name for n in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert not any("staff_summary_sheet" in m or "mission_board" in m for m in imported), \
        f"sss_render.py must stay independent of the gated SSS engine, found imports: {imported}"

    html = render_info_html(subject="Test Brief", opr="CC (Hale)",
                            staffed_by=["JET", "TALON", "Sterling"],
                            purpose="Prove the coversheet renders",
                            background="bg text", discussion_html="<p>disc</p>",
                            recommendation="rec text")
    for heading in ("Purpose", "Background", "Discussion", "Recommendation"):
        assert heading in html, f"missing heading: {heading}"
    assert "Test Brief" in html and "JET" in html
    print("[PASS] render_info_html: all headings present, no gate dependency")

    text = render_info_text(subject="Test Brief", opr="Dembe/A2", staffed_by=["Dembe/A2"],
                            purpose="p", background="b", discussion="d", recommendation="r")
    for heading in ("PURPOSE", "BACKGROUND", "DISCUSSION", "RECOMMENDATION"):
        assert heading in text, f"missing heading: {heading}"
    print("[PASS] render_info_text: all headings present")
    print("\n2/2 sss_render checks passed")
