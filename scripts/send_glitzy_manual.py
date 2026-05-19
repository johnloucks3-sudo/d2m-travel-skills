#!/usr/bin/env python3
import base64, json
from pathlib import Path
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

THUNDERBIRD = Path("/home/john/Thunderbird")
TOKEN_FILE = THUNDERBIRD / "gmail_token.json"
MANUAL_FILE = THUNDERBIRD / "docs" / "PERSONA_COMMUNICATION_MANUAL.md"
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    TOKEN_FILE.write_text(creds.to_json())

service = build("gmail", "v1", credentials=creds)
manual = MANUAL_FILE.read_text()

# ── markdown → glitzy HTML ──────────────────────────────────────────────
lines = manual.split("\n")
out = []
i = 0
in_code = False
code_buf = []

def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

while i < len(lines):
    line = lines[i]
    stripped = line.strip()

    # ── code fences ──────────────────────────────────────────────────────
    if stripped.startswith("```"):
        if not in_code:
            in_code = True
            code_buf = []
        else:
            out.append('<pre style="background:#eee8db;padding:12px;border-radius:4px;font-family:monospace;color:#333;overflow-x:auto;font-size:13px;line-height:1.5;">')
            out.append(esc("\n".join(code_buf)))
            out.append("</pre>")
            in_code = False
        i += 1
        continue
    if in_code:
        code_buf.append(stripped)
        i += 1
        continue

    # ── tables ───────────────────────────────────────────────────────────
    if stripped.startswith("|") and stripped.endswith("|"):
        rows = []
        while i < len(lines) and lines[i].strip().startswith("|"):
            rows.append(lines[i].strip())
            i += 1
        out.append('<table style="border-collapse:collapse;width:100%;margin:12px 0;font-family:Georgia,serif;color:#0000ff;font-size:14px;">')
        for ri, row in enumerate(rows):
            cells = [c.strip() for c in row.split("|")[1:-1]]
            if ri == 1 and all(c.startswith("-") for c in cells if c):
                continue
            tag = "th" if ri == 0 else "td"
            cell_style = 'border:1px solid #0000ff;padding:8px;text-align:left;'
            if ri == 0:
                cell_style += 'background-color:#0000ff;color:#ffffff;font-weight:bold;'
            out.append(f"<tr>{''.join(f'<{tag} style=\"{cell_style}\">{esc(c)}</{tag}>' for c in cells)}</tr>")
        out.append("</table>")
        continue

    # ── headings ─────────────────────────────────────────────────────────
    if stripped.startswith("## "):
        out.append(f'<h2 style="color:#0000ff;font-family:Georgia,serif;margin-top:28px;margin-bottom:8px;">{esc(stripped[3:])}</h2>')
        i += 1
        continue
    if stripped.startswith("### "):
        out.append(f'<h3 style="color:#0000ff;font-family:Georgia,serif;margin-top:20px;margin-bottom:6px;">{esc(stripped[4:])}</h3>')
        i += 1
        continue

    # ── separators ───────────────────────────────────────────────────────
    if stripped == "---":
        out.append('<hr style="border:none;border-top:2px solid #0000ff;margin:24px 0;">')
        i += 1
        continue

    # ── blank lines ──────────────────────────────────────────────────────
    if not stripped:
        out.append('<br>')
        i += 1
        continue

    # ── list items ───────────────────────────────────────────────────────
    if stripped.startswith("- ") or stripped.startswith("* "):
        text = esc(stripped[2:])
        # inline bold
        text = text.replace("**", "<b>", 1).replace("**", "</b>", 1)
        out.append(f'<li style="color:#0000ff;font-family:Georgia,serif;margin:3px 0;line-height:1.6;">{text}</li>')
        i += 1
        continue

    # ── paragraphs ───────────────────────────────────────────────────────
    text = esc(stripped)
    text = text.replace("**", "<b>", 1).replace("**", "</b>", 1)
    out.append(f'<p style="color:#0000ff;font-family:Georgia,serif;margin:8px 0;line-height:1.6;font-size:15px;">{text}</p>')
    i += 1

content = "".join(out)

# ── wrap with luxurious D2M stationery ────────────────────────────────────
html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background-color:#eee8db;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#eee8db;">
<tr><td align="center" style="padding:40px 20px;">
<table width="660" cellpadding="36" cellspacing="0" style="background-color:#f7f3ea;border-radius:3px;">
<tr><td style="font-family:Georgia,serif;color:#0000ff;">

<div style="text-align:center;padding:24px 0 14px 0;border-bottom:3px solid #0000ff;margin-bottom:28px;">
<div style="font-size:30px;font-weight:bold;color:#0000ff;letter-spacing:3px;margin-bottom:4px;">DREAMS2MEMORIES TRAVEL</div>
<div style="font-size:15px;color:#0000ff;letter-spacing:2px;">THUNDERBIRD WING &bull; INTERNAL</div>
</div>

{content}

<div style="margin-top:40px;padding-top:18px;border-top:2px solid #0000ff;text-align:center;font-size:12px;color:#0000ff;line-height:1.8;">
Dreams2Memories Travel, LLC<br>
Persona &amp; Human Communication Manual &bull; v1.0 &bull; 2026-05-16<br>
Living document &mdash; update as protocols evolve.
</div>

</td></tr>
</table>
</td></tr>
</table>
</body></html>"""

msg = MIMEText(html, "html", _charset="utf-8")
msg["To"] = "johnloucks3@gmail.com"
msg["From"] = "d2mconcierge@gmail.com"
msg["Subject"] = "✨ Thunderbird Wing — Persona & Human Communication Manual"

raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
service.users().messages().send(userId="me", body={"raw": raw}).execute()
print("Glitzy HTML sent to johnloucks3@gmail.com")
