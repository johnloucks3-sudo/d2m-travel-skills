#!/usr/bin/env python3
"""Surgical patch: replace render_briefing_html() body + wire Telegram in run_briefing()."""

SRC      = "/home/john/Thunderbird/thunderbird_morning_briefing.py"
NEW_BODY_FILE = "/home/john/Thunderbird/_new_body.txt"

with open(SRC, "r", encoding="utf-8") as f:
    content = f.read()

with open(NEW_BODY_FILE, "r", encoding="utf-8") as f:
    NEW_BODY = f.read()

# ── EDIT 1: Replace render_briefing_html() body ──────────────────────────────
DOCSTRING = '    """Render the full briefing as branded expandable-card HTML email."""\n'
OLD_END_MARKER = '    return html\n\n\n# ---------------------------------------------------------------------------\n# Revenue Pipeline'

ds_pos = content.find(DOCSTRING)
assert ds_pos != -1, "DOCSTRING not found"
body_start = ds_pos + len(DOCSTRING)

end_pos = content.find(OLD_END_MARKER, body_start)
assert end_pos != -1, "END MARKER not found"

old_body = content[body_start:end_pos]
print(f"[EDIT 1] Old body: {len(old_body)} chars")
print(f"[EDIT 1] New body: {len(NEW_BODY)} chars")

new_content = content[:body_start] + NEW_BODY + content[end_pos:]

# ── EDIT 2: Wire Telegram into run_briefing() ────────────────────────────────
OLD2 = "        send_briefing_email(html, subject)\n        return subject"
NEW2 = (
    "        send_briefing_email(html, subject)\n"
    "        # ── Telegram C2 digest ──\n"
    "        try:\n"
    "            send_telegram_digest(rss_direct or [], anchor_report, summary)\n"
    "        except Exception as e:\n"
    "            logger.warning(f\"Telegram digest failed (non-fatal): {e}\")\n"
    "        return subject"
)

count2 = new_content.count(OLD2)
assert count2 == 1, f"Expected 1 occurrence of EDIT 2 anchor, found {count2}"
new_content = new_content.replace(OLD2, NEW2)
print(f"[EDIT 2] Telegram wired OK")

# Write back
with open(SRC, "w", encoding="utf-8") as f:
    f.write(new_content)
print("[DONE] File written successfully.")
print(f"[INFO] Final file size: {len(new_content)} chars")
