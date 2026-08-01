"""
core/comms/report_action_buttons.py — USAFA Standard Interactive Action Block Generator

Authority: Commander Directives (2026-07-31)
Style: USAFA Blue (#003366) & USAFA Silver (#8A9EA7) Card Layout
Features:
  - 14px Bold High-Contrast Action Buttons (8px 16px padding)
  - Standard 3-Line Decision Snippets (Line 1: Item & Priority, Line 2: Context, Line 3: Action + Buttons)
"""
from __future__ import annotations
import urllib.parse
import html as _html

C2_EMAIL = "d2mconcierge@gmail.com"

# USAFA Color Palette Tokens
USAFA_BLUE = "#003366"
USAFA_SILVER = "#8A9EA7"
CARD_BG = "#F8FAFC"
CARD_BORDER = "#CBD5E1"

def render_usafa_card_action_block(
    item_id: str,
    title: str,
    priority: str = "P1",
    context_snippet: str = "",
    recommended_action: str = ""
) -> str:
    """Renders USAFA Blue & Silver Card with 3-Line Decision Snippet + 14px Action Buttons."""
    try:
        from core.comms.commander_queue import is_closed
        if is_closed(item_id):
            return ""
    except Exception:
        pass

    if str(item_id).startswith("TCD-"):
        try:
            from tcd.writeback import read_sheet_rows
            rows = read_sheet_rows()
            raw_id = str(item_id).replace("TCD-", "")
            for r in rows:
                if str(r.get("id")) == raw_id:
                    if r.get("snippet"):
                        context_snippet = _html.escape(r.get("snippet"), quote=True)
                    if r.get("link"):
                        link = str(r.get("link"))
                        if link.startswith("http://") or link.startswith("https://"):
                            link_escaped = _html.escape(link, quote=True)
                            context_snippet += f" · <a href='{link_escaped}' style='color:{USAFA_BLUE};'>Source Document</a>"
                    break
        except Exception:
            pass
            
    # Escape other interpolations for XSS safety
    title = _html.escape(title, quote=True)
    if recommended_action:
        recommended_action = _html.escape(recommended_action, quote=True)

    clean_id = urllib.parse.quote(item_id)
    approve_subj = urllib.parse.quote(f"[WING] APPROVE {item_id}")
    modify_subj = urllib.parse.quote(f"[WING] MODIFY {item_id}")
    comment_subj = urllib.parse.quote(f"[WING] COMMENT {item_id}")
    reject_subj = urllib.parse.quote(f"[WING] REJECT {item_id}")
    close_subj = urllib.parse.quote(f"[WING] CLOSE {item_id}")

    approve_url = f"mailto:{C2_EMAIL}?subject={approve_subj}&body=APPROVED%3A%20{clean_id}"
    modify_url = f"mailto:{C2_EMAIL}?subject={modify_subj}&body=MODIFY%20DETAILS%20FOR%20{clean_id}%3A%0A"
    comment_url = f"mailto:{C2_EMAIL}?subject={comment_subj}&body=COMMENTS%20FOR%20{clean_id}%3A%0A"
    reject_url = f"mailto:{C2_EMAIL}?subject={reject_subj}&body=REJECTED%3A%20{clean_id}"
    close_url = f"mailto:{C2_EMAIL}?subject={close_subj}&body=CLOSED%3A%20{clean_id}"

    p_color = "#b91c1c" if priority.upper() == "P0" else ("#c2410c" if priority.upper() == "P1" else "#1d4ed8")
    p_badge = f'<span style="background:{p_color};color:#ffffff;padding:2px 6px;border-radius:3px;font-size:11px;font-weight:bold;margin-right:6px;">{priority.upper()}</span>'
    
    snippet_html = f'<div style="font-size:13px;color:#334155;margin-bottom:8px;line-height:1.4;"><b>Context:</b> {context_snippet}</div>' if context_snippet else ""
    action_text_html = f'<div style="font-size:13px;color:#0f172a;margin-bottom:10px;line-height:1.4;"><b>Action:</b> {recommended_action}</div>' if recommended_action else ""

    return f"""
<div style="margin-top:12px;margin-bottom:16px;padding:14px;background:{CARD_BG};border:1px solid {CARD_BORDER};border-left:4px solid {USAFA_BLUE};border-radius:6px;font-family:Arial,sans-serif;">
  <!-- Line 1: Item & Priority -->
  <div style="font-weight:bold;font-size:14px;color:{USAFA_BLUE};margin-bottom:6px;">
    {p_badge} {title} <span style="color:#64748b;font-size:12px;font-weight:normal;">[{item_id}]</span>
  </div>
  
  <!-- Line 2: Context Snippet -->
  {snippet_html}
  
  <!-- Line 3: Recommended Action -->
  {action_text_html}
  
  <!-- Action Buttons Block -->
  <div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;">
    <a href="{approve_url}" style="display:inline-block;padding:8px 16px;background:#15803d;color:#ffffff;text-decoration:none;border-radius:6px;font-weight:bold;font-size:14px;margin-right:6px;margin-bottom:4px;box-shadow:0 1px 2px rgba(0,0,0,0.15);">🟢 APPROVE</a>
    <a href="{modify_url}" style="display:inline-block;padding:8px 16px;background:#b45309;color:#ffffff;text-decoration:none;border-radius:6px;font-weight:bold;font-size:14px;margin-right:6px;margin-bottom:4px;box-shadow:0 1px 2px rgba(0,0,0,0.15);">🟡 MODIFY</a>
    <a href="{comment_url}" style="display:inline-block;padding:8px 16px;background:{USAFA_BLUE};color:#ffffff;text-decoration:none;border-radius:6px;font-weight:bold;font-size:14px;margin-right:6px;margin-bottom:4px;box-shadow:0 1px 2px rgba(0,0,0,0.15);">💬 COMMENTS</a>
    <a href="{reject_url}" style="display:inline-block;padding:8px 16px;background:#b91c1c;color:#ffffff;text-decoration:none;border-radius:6px;font-weight:bold;font-size:14px;margin-right:6px;margin-bottom:4px;box-shadow:0 1px 2px rgba(0,0,0,0.15);">🔴 REJECT</a>
    <a href="{close_url}" style="display:inline-block;padding:8px 16px;background:#475569;color:#ffffff;text-decoration:none;border-radius:6px;font-weight:bold;font-size:14px;margin-bottom:4px;box-shadow:0 1px 2px rgba(0,0,0,0.15);">⚪ CLOSE</a>
  </div>
</div>
"""

def render_item_action_block_html(item_id: str, item_title: str = "") -> str:
    """Compatibility wrapper for item-level action blocks."""
    return render_usafa_card_action_block(item_id, item_title, priority="P1")

def render_report_action_block_html(report_id: str, title: str = "", report_type: str = "report") -> str:
    """Renders USAFA action block for overall report."""
    return render_usafa_card_action_block(report_id, title, priority="P0", context_snippet="Overall Report Summary", recommended_action="Review and approve overall report.")

def render_report_action_block_md(report_id: str, title: str = "") -> str:
    """Renders compact Telegram Markdown command trippers."""
    title_disp = f" ({title})" if title else ""
    return (
        f"\n⚡ **COMMAND ACTION TRIPPERS [{report_id}]{title_disp}:**\n"
        f"🟢 `[WING] APPROVE {report_id}` | 🟡 `[WING] MODIFY {report_id}` | "
        f"💬 `[WING] COMMENT {report_id}` | 🔴 `[WING] REJECT {report_id}` | ⚪ `[WING] CLOSE {report_id}`\n"
    )
