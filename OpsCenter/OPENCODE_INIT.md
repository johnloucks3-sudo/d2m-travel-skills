

# OPENCODE HALE INIT — Key Protocols

## ⚠️ MANDATORY SESSION STARTUP — HALE BUS (Standing Order 2026-06-24, enforced 2026-07-04)
**Run before anything else:**
```python
from core.hale_bus.hale_bus_read import load_bus_at_startup
load_bus_at_startup("opencode")
```
This loads inter-Hale state (open missions, active projects, alerts) written by other instances — Claude Code's checkpoint runs at session end. **At session end, write your own:**
```python
from core.hale_bus.hale_bus_write import checkpoint_session
checkpoint_session("opencode")
```
Bus content is not a security perimeter (all instances read/write the same file) — no PII/secrets in it. Found 2026-07-04: OpenCode showed OFFLINE on the bus and this file had never referenced calling either function — fixed here.

## ⚠️ DECISION MATRIX ON LOGIN (Commander directive 2026-07-04)
Every session open, check `OpsCenter/state/heartbeat_scan_latest.json` (or run `python3 scripts/hale_heartbeat_scan.py`) for overdue suspenses, aging P0/P1 missions, and stale CI tools. Present decision-worthy findings via structured multiple-choice, one item per question — not a prose list. If genuinely zero findings, say so plainly.

## ⚠️ HALE HEARTBEAT SCAN (built 2026-07-04)
`scripts/hale_heartbeat_scan.py` — runs 4x/day via `hale-heartbeat.timer` (0300/0900/1500/2100 MT), zero-LLM, reads `overnight_ops_log.json` + `config/ci_registry.json` + `mission_board.json`. Every finding carries a `file` field (`file://` path to the most specific real source — a wrapped CI script, a client dossier match, or the mission board itself) for direct linking in any surfaced output. Quiet-exit if nothing crosses threshold.

## ⚠️ ANCHOR-DATE SCANNER — KNOWN STALENESS ISSUE (found + partially fixed 2026-07-04)
`core/scheduling/thunderbird_anchor_dates.py::KNOWN_BOOKINGS` is a hand-maintained, hardcoded dict — NOT synced with TESS/portal/dossier. Two bugs found: (1) no "trip already sailed" exclusion — FIXED, `compute_anchors()`/`scan_all_bookings_due()` now skip a booking's anchors once `disembark_date` has passed. (2) hardcoded `fpd_status` can be stale (says PENDING when actually PAID) — code now respects `fpd_status=="PAID"` when set, but the DATA itself needs Harlan's verification against portal/TESS (MISSION-1540, open). Do not trust `KNOWN_BOOKINGS.fpd_status` as ground truth without checking that mission's resolution first.

## D2M EMAIL TEMPLATE — HARD RULE (UPDATED 2026-06-25 — ALL EMAILS, NOT JUST CLIENTS)
**Dark navy is the ONLY template for ALL emails to johnloucks3 — internal, personal, client, everything.**
USAFA cream (#f7f3ea) / blue (#0000ff) are PERMANENTLY RETIRED across all contexts.
Source: Commander directive 2026-06-25. Full reference: `docs/EMAIL_SEND_CANONICAL.md`

Colors (bgcolor ATTRIBUTE survives Gmail; CSS gradient = enhancement only):
- Outer: `#07076b` | Panel: `#09095a` | Deep/code: `#0d0d4a` | Text: `#e8f1ff`
- Headings: `#a8c4ff` | Labels: `#7090cc` | Links: `#c8dcff`
- Ok: `#4ade80` | Warn: `#f59e0b` | Error: `#f87171` | Border: `#2a2a8f`
- ❌ NEVER `#f7f3ea` (cream) — RETIRED for ALL email types, not just clients

Builder: `python3 scripts/d2m_email_builder.py --body [body.html] --to [addr] --subject "[s]" [--name "First"]`
Template: `storage/templates/d2m_canonical_darknavy.html` ({{BODY_CONTENT}} placeholder)

## CANONICAL EMAIL SEND PATTERN — READ THIS BEFORE SENDING ANY EMAIL
**Full doc:** `docs/EMAIL_SEND_CANONICAL.md` — DO NOT SKIP THIS.
**Helper:** `scripts/wing_email_sender.py` (import or CLI)

```python
# MINIMUM CORRECT PATTERN — copy this exactly
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN = "/home/john/Thunderbird/creds/johnloucks3_token.json"
creds = Credentials.from_authorized_user_file(TOKEN)
service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
msg = MIMEMultipart('alternative')
msg['To'] = "johnloucks3@gmail.com"
msg['From'] = "johnloucks3@gmail.com"   # ← REQUIRED or wrong account inserts
msg['Subject'] = "Subject"
msg.attach(MIMEText(HTML, 'html'))      # ← HTML must be full dark-navy template
raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
result = service.users().messages().send(userId='me', body={'raw': raw}).execute()
print(f"SENT: {result['id']}")
```

**HARD RULES:**
- `cache_discovery=False` — always. Stale cache causes 403s.
- `msg['From'] = 'johnloucks3@gmail.com'` — always explicit. Never omit.
- Dark navy palette ONLY — `#07076b` outer, `#09095a` panels. Never cream for wing emails.
- Internal briefs/reports = FULL SEND (this pattern). Client products = `drafts().create()` (WF-17).
- DO NOT use MCP Gmail tools for sends — scope failures, silent drops. Python only.
- DO NOT use concierge@d2mluxury.quest as From — bounces iCloud (Amy Darrow incident Jun 2026).

**Color quick-ref:** outer `#07076b` · panel `#09095a` · heading `#a8c4ff` · body `#e8f1ff` · label `#7090cc` · ok `#4ade80` · warn `#f59e0b` · error `#f87171` · link `#c8dcff`

## EOD + INCUBATOR (SO-EOD-INCUBATOR-20260610)
- 1730 MT: Nomination ping → Telegram. 5-min window. No reply = execute.
- 1800 MT: EOD brief → johnloucks3. 4 sections (prose Done List, tight Search section).
- Overnight: build gate candidate. AM brief surfaces results.
- Config: `OpsCenter/eod_incubator_config.json` | Full SO: `standing_orders/SO_EOD_INCUBATOR_PROTOCOL_20260610.md`

# BLACKBOARD_START — auto-updated by blackboard_sync.py — do not edit manually
<!-- Last sync: 2026-07-28 15:55 MT -->
```
=== THUNDERBIRD BLACKBOARD [2026-07-28 15:55 MT] ===
Budget: Claude MAX Wkly-64% | Sonnet-64% | Runs-3/15 | OpenCode GREEN | Groq UNKNOWN | Deepseek UNKNOWN
Seat budgets: CC:23%⚠STALE | OC:0%⚠STALE | AG:0%⚠STALE
Active tasks: 0
Last Deepseek ruling: NONE
Open items: none logged
Next priority: check session_autosave_latest.md
Standing: Claude=judgment | OpenCode=ops | Deepseek=arbitrator | PII fence: Deepseek
Session checkpoint: /home/john/Thunderbird/session_autosave_latest.md
Full blackboard: /home/john/Thunderbird/OpsCenter/collaboration/blackboard.md
================================================
```
# BLACKBOARD_END
