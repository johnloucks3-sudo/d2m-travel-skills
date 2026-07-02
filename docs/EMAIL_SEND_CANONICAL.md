# THUNDERBIRD — CANONICAL EMAIL SEND PATTERN
## The definitive guide for Claude Code, OpenCode, and all Wing agents
**Status: GOLD STANDARD — DO NOT DEVIATE**
*Authored: 2026-06-25 · Hale (CC) · Source: live-verified against Gmail API*

---

## WHY THIS EXISTS

OpenCode's MCP-based Gmail sends are unreliable — authentication failures, token scope mismatches, silent draft losses. Claude Code proved a direct Python + google-auth pattern that:
- Sends fully-formatted dark navy HTML to johnloucks3 inbox **in one shot**
- Uses the johnloucks3 OAuth token directly (no MCP intermediary)
- Survives session restarts without re-auth
- Produces Commander-readable rich HTML, not plain text

**This pattern is mandatory for all internal briefs and reports. Client products still follow WF-17 draft flow.**

---

## TOKEN FILE LOCATIONS

| Account | Token path | Used for |
|---|---|---|
| **johnloucks3** (primary) | `/home/john/Thunderbird/creds/johnloucks3_token.json` | Internal sends (briefs, reports, instructions) |
| **d2mconcierge** | `/home/john/Thunderbird/creds/persona_gmail_token.json` (alias: `config/persona_gmail_token.json`) | Client draft creation only |

**Always use johnloucks3 token for direct sends to Commander.** Never use d2mconcierge token to send — it routes through d2mluxury.quest which bounces iCloud/me.com addresses.

---

## THE CANONICAL SEND PATTERN (Python)

```python
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN = "/home/john/Thunderbird/creds/johnloucks3_token.json"
TO = "johnloucks3@gmail.com"
SUBJECT = "Your subject line"

HTML = """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="background:#07076b;...">
  <!-- full HTML body — see COLOR PALETTE below -->
</body>
</html>"""

# Build and send
creds = Credentials.from_authorized_user_file(TOKEN)
service = build('gmail', 'v1', credentials=creds, cache_discovery=False)

msg = MIMEMultipart('alternative')
msg['To'] = TO
msg['From'] = 'johnloucks3@gmail.com'
msg['Subject'] = SUBJECT
msg.attach(MIMEText(HTML, 'html'))

raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
result = service.users().messages().send(userId='me', body={'raw': raw}).execute()
print(f"SENT: {result['id']}")
```

**That's it. No MCP. No draft step. No intermediate files. Direct API call.**

---

## COLOR PALETTE — DARK NAVY SYSTEM

All internal briefs and wing reports use this palette. **Never cream (#f7f3ea) for wing emails.**

```
BACKGROUNDS
  Page outer:          #07076b   ← body background, must be bgcolor ATTRIBUTE too
  Card/panel:          #09095a   ← content panels
  Inset/deep:          #0d0d4a   ← code blocks, quoted text
  Dark accent:         #0a0a3a   ← table alternating rows

BORDERS & LINES
  Subtle border:       #2a2a8f   ← card borders, hr
  Row divider:         #1a1a4a   ← table row separators
  Inner divider:       #1a1a6e   ← code inline, fine separator

TEXT
  Primary body:        #e8f1ff   ← main content text
  Header/title:        #a8c4ff   ← h1, h2 headings
  Secondary/label:     #7090cc   ← labels, metadata, timestamps
  Link text:           #c8dcff   ← body copy on dark bg

STATUS COLORS (traffic light — use inline on dark navy)
  Confirmed/ok:        #4ade80   ← verified, active, passed
  Warning/pending:     #f59e0b   ← holds, timers, caveats
  Error/dead:          #f87171   ← failures, disabled, retired
  Info/note:           #60a5fa   ← neutral info callouts

TYPOGRAPHY
  Font:                Georgia, serif   ← all wing emails
  Code font:           monospace
  Base size:           13px body, 14-15px headers
  Max container:       720px centered
```

---

## FULL TEMPLATE SKELETON

```html
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="background:#07076b;color:#e8f1ff;font-family:Georgia,serif;padding:32px;max-width:720px;margin:0 auto;">

<!-- HEADER PANEL -->
<div style="background:#09095a;border:1px solid #2a2a8f;border-radius:8px;padding:28px;margin-bottom:20px;">
  <h1 style="color:#a8c4ff;font-size:22px;margin:0 0 8px;">⚡ Title Here</h1>
  <p style="color:#7090cc;font-size:13px;margin:0;">Thunderbird Wing · DATE · Subtitle</p>
</div>

<!-- CONTENT PANEL -->
<div style="background:#09095a;border:1px solid #2a2a8f;border-radius:8px;padding:24px;margin-bottom:20px;">
  <h2 style="color:#a8c4ff;font-size:15px;margin:0 0 14px;">Section Title</h2>

  <!-- STATUS TABLE -->
  <table style="width:100%;border-collapse:collapse;font-size:13px;">
    <tr>
      <td style="padding:6px 8px;color:#7090cc;width:180px;">Label</td>
      <td style="color:#4ade80;">✅ Confirmed value</td>
    </tr>
    <tr>
      <td style="padding:6px 8px;color:#7090cc;">Pending</td>
      <td style="color:#f59e0b;">⏱ Timer value</td>
    </tr>
    <tr>
      <td style="padding:6px 8px;color:#7090cc;">Failed</td>
      <td style="color:#f87171;">❌ Error detail</td>
    </tr>
  </table>

  <!-- CODE BLOCK -->
  <div style="background:#0d0d4a;border-left:3px solid #4ade80;padding:14px;border-radius:4px;margin:10px 0;">
    <p style="color:#7090cc;font-size:11px;text-transform:uppercase;margin:0 0 6px;">Shell command</p>
    <p style="color:#4ade80;font-family:monospace;font-size:15px;margin:0;">your-command here</p>
  </div>

  <!-- INLINE CODE -->
  <code style="background:#1a1a6e;padding:2px 6px;border-radius:3px;">inline code</code>
</div>

<!-- WARNING PANEL -->
<div style="background:#09095a;border:1px solid #f59e0b55;border-radius:8px;padding:20px;margin-bottom:20px;">
  <h2 style="color:#f59e0b;font-size:14px;margin:0 0 8px;">⚠️ Warning Title</h2>
  <p style="color:#c8dcff;font-size:13px;margin:0;">Warning body text.</p>
</div>

<!-- ERROR/DISABLED PANEL -->
<div style="background:#09095a;border:1px solid #f8717155;border-radius:8px;padding:20px;margin-bottom:20px;">
  <p style="color:#f87171;font-size:12px;margin:0;">❌ Disabled feature — reason here.</p>
</div>

<!-- FOOTER RULE + SIGNATURE -->
<hr style="border:none;border-top:1px solid #2a2a8f;margin:24px 0;">
<div style="text-align:center;padding:12px 0;">
  <p style="color:#a8c4ff;font-size:14px;margin:0 0 4px;">⚡ V. Hale, VCS · Thunderbird Wing</p>
  <p style="color:#5060a0;font-size:12px;margin:0;">DATE TIME MT</p>
</div>

</body>
</html>
```

---

## TABLE PATTERN — MULTI-COLUMN DATA

```html
<table style="width:100%;border-collapse:collapse;font-size:13px;font-family:monospace;">
  <!-- CATEGORY HEADER ROW -->
  <tr style="border-bottom:1px solid #1a1a4a;background:#0a0a3a;">
    <td colspan="3" style="padding:5px 8px;color:#5060a0;font-size:11px;letter-spacing:1px;">CATEGORY LABEL</td>
  </tr>
  <!-- DATA ROW (alternating) -->
  <tr style="border-bottom:1px solid #1a1a4a;">
    <td style="padding:6px 8px;color:#4ade80;">command</td>
    <td style="padding:6px 8px;color:#c8dcff;">description</td>
    <td style="padding:6px 8px;color:#7090cc;">notes</td>
  </tr>
  <!-- HEADER ROW -->
  <tr style="border-bottom:1px solid #2a2a8f;">
    <th style="color:#7090cc;text-align:left;padding:7px 8px;">Column 1</th>
    <th style="color:#7090cc;text-align:left;padding:7px 8px;">Column 2</th>
  </tr>
</table>
```

---

## REQUIRED PACKAGES

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

These are already installed on yoga/this system. If running headless, verify:
```bash
python3 -c "from google.oauth2.credentials import Credentials; print('OK')"
```

---

## TEMPLATE RULE — ALL EMAILS TO JOHNLOUCKS3

**Dark navy is the ONLY template. No exceptions. No legacy modes.**

| Email type | Template | From |
|---|---|---|
| Internal brief / report / intel | Dark navy · FULL SEND | johnloucks3 |
| Wing instructions / system docs | Dark navy · FULL SEND | johnloucks3 |
| EOD brief / morning brief | Dark navy · FULL SEND | johnloucks3 |
| Client TP / proposal / validation | Dark navy · DRAFT (WF-17) | johnloucks3 |
| Personal / non-D2M | Dark navy · johnloucks3 inbox | johnloucks3 |

**USAFA cream (#f7f3ea) / blue (#0000ff) colors are PERMANENTLY RETIRED.**
They no longer apply to ANY email — not internal, not personal, not client-facing.
Dark navy (#07076b) is the single Wing email identity across all contexts.

## ROUTING RULES (WHO GETS WHAT TOKEN)

```
ALL emails to Commander → johnloucks3 token → FULL SEND directly
  ✅ Wing daily brief
  ✅ Provider switching instructions
  ✅ EOD brief
  ✅ Intel reports
  ✅ Infra status reports
  ✅ Personal / non-D2M emails
  ✅ Any communication to johnloucks3@gmail.com

Client products (TP emails, proposals, validation) → SAME token → DRAFT in johnloucks3
  ✅ WF-17 flow: create_draft() not send()
  ✅ Label THUNDERBIRD-Commander-Review
  ✅ Commander reviews and sends manually
  ❌ NEVER call send() for client products
```

---

## CAVEATS & KNOWN FAILURE MODES

### 1. MCP Gmail vs Direct Python
- **MCP `mcp__claude_ai_Gmail__*` tools**: scope limited, unreliable auth, silent failures
- **Direct Python via google-auth**: always works, full HTML preserved, no scope issues
- **Rule**: Use direct Python for all sends. MCP only for read/search operations.

### 2. Cache Discovery Warning
Always pass `cache_discovery=False` to `build()`:
```python
service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
```
Without it, stale discovery cache can cause mysterious 403s.

### 3. Token Expiry
johnloucks3 token auto-refreshes via `johnloucks3_oauth_keepalive.timer` (every 90 min).
If token is expired, the `Credentials` object will auto-refresh if a `client_id`/`client_secret` is present in the JSON.
If it fails: `python3 scripts/refresh_johnloucks3_token.py` (or re-auth manually).

### 4. HTML Rendering in Gmail
- **bgcolor ATTRIBUTE required** — CSS background-color strips on some clients
- **Inline all CSS** — `<style>` blocks may strip; use `style=""` on every element
- **No `<link>` tags** — remote CSS never loads in Gmail
- **Table layout** — div-based layouts can collapse; use `<table>` for multi-column
- **max-width: 720px** — wider than this clips on mobile

### 5. d2mluxury.quest Deliverability
**DO NOT use concierge@d2mluxury.quest as From address for client sends.**
Domain has SPF/DKIM gap — bounces at iCloud/me.com (confirmed Amy Darrow bounce Jun 2026).
Use johnloucks3@gmail.com as From for now. Revert after MISSION-289 (DNS fix).

### 6. From Field
Always set explicitly:
```python
msg['From'] = 'johnloucks3@gmail.com'
```
If omitted, Gmail inserts the authenticated account address — which may be d2mconcierge if token is wrong.

---

## QUICK COPY-PASTE SEND SCRIPT

```python
#!/usr/bin/env python3
"""Minimal wing email sender — copy and adapt."""
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN = "/home/john/Thunderbird/creds/johnloucks3_token.json"

def send_wing_email(to, subject, html_body):
    creds = Credentials.from_authorized_user_file(TOKEN)
    service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
    msg = MIMEMultipart('alternative')
    msg['To'] = to
    msg['From'] = 'johnloucks3@gmail.com'
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId='me', body={'raw': raw}).execute()
    return result['id']

if __name__ == '__main__':
    msg_id = send_wing_email(
        to="johnloucks3@gmail.com",
        subject="Test — Wing Email",
        html_body="<body style='background:#07076b;color:#e8f1ff;font-family:Georgia;padding:32px;'>Test</body>"
    )
    print(f"SENT: {msg_id}")
```

---

## REUSABLE HELPER — `scripts/wing_email_sender.py`

This script already exists as `/home/john/Thunderbird/scripts/wing_email_sender.py`.
Import it in any agent task:
```python
from scripts.wing_email_sender import send_wing_email
```

---

*V. Hale, VCS · Thunderbird Wing · 2026-06-25*
*Read by: OpenCode, Claude Code, all headless dispatches*
