---
name: morning-brief
description: "Generate and send the daily morning brief to johnloucks3. Pulls live state from blackboard_sync, mission board, hale_state.json financial pulse, and wing health — formats as the canonical hale_brief.md template, then sends as a full internal email (not a draft) to johnloucks3@gmail.com via gmail_send_from_wing. Triggers on: morning brief, daily brief, send brief, brief commander, morning update, daily update, hale brief, send the brief, generate brief, run brief"
---

# /morning-brief — Daily Brief Generation + Commander Send

You execute this procedure yourself. This is a full-send internal operation — no draft step, no WF-17 gate.
Target recipient is johnloucks3@gmail.com (Commander's within-wing inbox). This send is pre-authorized per SO 27 MAR 2026.
Use /ask-opus only if a multi-source synthesis judgment call exceeds your reasoning ceiling.

## Usage

```
/morning-brief
```

Runs immediately. No arguments required. Pulls all data live. Sends on completion.

---

## Step 1 — Run Blackboard Sync (Sterling)

Refresh the blackboard before reading it — you want live state, not cached.

```bash
cd /home/john/Thunderbird
python3 OpsCenter/blackboard_sync.py
```

Expected output: `[blackboard_sync] OK (4/4 files)` or partial with list of failed files.

Then read the freshly written summary:

```bash
cat /home/john/Thunderbird/OpsCenter/collaboration/blackboard_summary.txt
```

Extract:
- `Budget:` line — Claude / OpenCode / Groq / Deepseek status
- `Active tasks:` count
- `Last Deepseek ruling:`
- `Open items:` (first 3)
- `Next priority:`

If blackboard_sync fails: read `OpsCenter/collaboration/blackboard.md` directly as fallback.

---

## Step 2 — Pull Mission Board (ELON)

```bash
python3 /home/john/Thunderbird/OpsCenter/mission_board_sync.py list board
```

`cmd_list_board()` returns active missions with priority flags: P0=🔴 P1=🟠 P2=🟡 P3=🟢.
Output format per mission: `{priority_flag} {id}: {title}` + status / assigned_to / suspense_date.

Also pull suspended for awareness:

```bash
python3 /home/john/Thunderbird/OpsCenter/mission_board_sync.py list suspended
```

Extract:
- Active mission count
- Any P0/P1 missions — title + assigned_to + suspense
- Any suspense dates firing today or within 24h

---

## Step 3 — Read Financial Pulse (Harlan)

```python
import json
from pathlib import Path

state = json.loads(Path("/home/john/Thunderbird/hale_state.json").read_text())
fp = state.get("financial_pulse", {})

# Key fields:
pipeline        = fp.get("pipeline_d2m_share_upcoming", 0)      # D2M share, upcoming voyages
tess_received   = fp.get("tess_received", 0)                     # checks received in TESS
sheet_expected  = fp.get("sheet_commission_expected", 0)         # total sheet commissions expected
d2m_share       = fp.get("sheet_d2m_share", 0)                  # D2M share of sheet total
upcoming_count  = fp.get("sheet_upcoming_count", 0)             # voyage count
tess_trips      = fp.get("tess_trips", 0)
tess_bookings   = fp.get("tess_bookings", 0)
tess_clients    = fp.get("tess_clients", 0)
last_checked    = fp.get("last_checked", "unknown")
raw_snippet     = fp.get("raw_snippet", "")

print(f"Pipeline D2M share: ${pipeline:,.2f} across {upcoming_count} voyages")
print(f"TESS received: ${tess_received:,.2f}")
print(f"Sheet total expected: ${sheet_expected:,.2f} | D2M share: ${d2m_share:,.2f}")
print(f"Last checked: {last_checked}")
```

**Harlan financial sign-off note:** The financial pulse is sourced from `hale_state.json` which aggregates TESS + commission sheet. For the morning brief these figures are a summary dashboard — no individual booking dollar amounts are cited. Harlan 6-step sign-off is required only when a specific client dollar figure appears in a client-facing email. The morning brief to Commander uses aggregate pipeline figures only — those do not require individual Harlan sign-off, but flag `last_checked` age if > 12 hours stale.

### 3.5. FARE WATCH — Daily Price Check (Active: Jun 6–20, 2026)

**Target:** Icelandair May 2027 (DEN→VCE + ATH→DEN). Runs every brief for 14 days.

```python
import json, asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "Thunderbird"))

watches = json.loads(Path.home().joinpath("Thunderbird/core/travel/data/fare_watches.json").read_text())
targets = ["loucks-silver-nova-may2027-outbound", "loucks-silver-nova-may2027-return"]

# Report current vs baseline
for wid in targets:
    w = watches.get(wid)
    if w:
        cp = w.get("current_price_pp", 0)
        bp = w.get("baseline_price_pp", 0)
        pct = ((cp - bp) / bp * 100) if bp else 0
        arrow = "⬆" if pct > 0 else "⬇" if pct < 0 else "—"
        alert = "🔴 BREACH" if w.get("alert_below") and cp and cp <= w["alert_below"] else "✅ OK"
        print(f"{w['label']}: ${cp}/pp (baseline ${bp}) {arrow} {abs(pct):.0f}% {alert}")

# Re-run Centrav to get live prices
from core.travel.thunderbird_centrav_search import run_centrav_search
async def refresh():
    r1 = await run_centrav_search("DEN", "VCE", "2027-04-30", adults=2, cabins=["business"])
    r2 = await run_centrav_search("ATH", "DEN", "2027-06-01", adults=2, cabins=["business"])
    fw = json.loads(Path.home().joinpath("Thunderbird/core/travel/data/fare_watches.json").read_text())
    for key, r in [("loucks-silver-nova-may2027-outbound", r1), ("loucks-silver-nova-may2027-return", r2)]:
        b = r.get("results", {}).get("business", {})
        if b.get("lowest_total"):
            fw[key]["current_price_pp"] = b["lowest_total"] / 2
        fw[key]["last_checked"] = __import__("datetime").datetime.now().isoformat()
    Path.home().joinpath("Thunderbird/core/travel/data/fare_watches.json").write_text(json.dumps(fw, indent=2))
    for label, r in [("DEN→VCE Business", r1), ("ATH→DEN Business", r2)]:
        p = r.get("results", {}).get("business", {}).get("lowest_total", 0)
        print(f"{label}: ${p} total / ${p/2 if p else 0} pp {'✅' if p else '⚠️'}")
asyncio.run(refresh())
```

**Duration:** This section runs through Jun 20, 2026. After that date, remove this section and retire to `Step 6 — Open Items` if prices haven't moved.

---

## Step 4 — Read Wing Health (Sterling)

```python
import json
from pathlib import Path

state = json.loads(Path("/home/john/Thunderbird/hale_state.json").read_text())
health = state.get("wing_health", {})
tasks  = state.get("open_tasks", [])
staff  = state.get("staff_load", {})

# Bots
bots = health.get("telegram_bots", {})
d2mc2c = bots.get("D2MC2C", {}).get("status", "UNKNOWN")
dani   = bots.get("Dani", {}).get("status", "UNKNOWN")

# Services
mcp_status      = health.get("mcp_server", "UNKNOWN")
opencode_status = health.get("opencode_status", "UNKNOWN")
chrome_port     = health.get("chrome_debug_port_9222", "UNKNOWN")

# OAuth error flag
oauth_error = any("invalid_grant" in str(t) for t in tasks)

print(f"MCP: {mcp_status} | OpenCode: {opencode_status} | Chrome:9222: {chrome_port}")
print(f"Telegram D2MC2C: {d2mc2c} | Dani bot: {dani}")
print(f"OAuth token expired: {oauth_error}")
```

Status thresholds:

| Status | Meaning |
|---|---|
| ONLINE / LIVE | Green — operational |
| UNKNOWN | Yellow — state not checked this session |
| OFFLINE / EXPIRED / invalid_grant | Red — action required |

---

## Step 5 — Read Session State + Open Items

```bash
cat /home/john/Thunderbird/session_autosave_latest.md
```

Scan for:
- `## OPEN ITEMS` or `### Open` section — extract first 3 items
- `## NEXT` or `### NEXT PRIORITIES` section — extract first 2
- Any WF-17 items awaiting Commander review
- Any client departure within 21 days

Also read hale_state.json `brain_routing_log` for last brain dispatch:

```python
log = state.get("brain_routing_log", [])
if log:
    last = log[-1]
    print(f"Last brain: {last['brain']} | Task: {last['task'][:60]} | {last['ts'][:16]}")
```

---

## Step 6 — Compose the Brief

Format the brief to match `hale_brief.md` exactly. Section order is canonical:

```
🦅

THUNDERBIRD DAILY BRIEF — [DATE] · [HH:MM MT]
— V. Hale, VCS

---

### 1. CLIENT WIRE
[Table: Client | Ship | Departure | FPD | Priority]
FPD status logic:
  - Departure date passed → flag as OVERDUE + days since
  - FPD due within 7 days → "Due [date] — URGENT"
  - FPD on track → "Due [date] — On track"
  - OVERDUE → "OVERDUE [N]d"

### 2. WF-17 GATE — AWAITING COMMANDER REVIEW
[Table: Client | TP | Draft Status]
List any voice_drafted lifecycle touchpoints not yet sent.
Flag oldest overdue first. If none: "No drafts staged — gate clear."

### 3. FINANCIAL PULSE
[Table: Metric | Value]
Rows: D2M pipeline | TESS received | Sheet commissions expected | D2M share | TESS pkg total
Note last_checked time. If > 12h stale: add "⚠️ Stale — refresh recommended."

### 3.5. FARE WATCH — Active Price Monitoring (Jun 6–20)
[Table: Route | Cabin | Current/pp | Baseline/pp | ±% | Alert]
Target: Icelandair May 2027 (DEN→VCE + ATH→DEN Business). Run Centrav refresh, print comparison.

### 3.6. PERX INTERLINE RATES — TA Rate Signal Watch (Standing — no expiry)
[Table: Sailing | Cabin Category | Price/pp | vs Baseline | Signal]

**Watched sailings (Commander standing order 2026-06-08):**
- Seven Seas Grandeur — Dec 29, 2026 → Concierge D, Concierge E, Balcony
- Silver Nova — May 5, 2027 (voyage 1 of 3) → Balcony/Veranda, Suite
- Silver Nova — May 12, 2027 (voyage 2 of 3) → Balcony/Veranda, Suite
- Silver Nova — May 19, 2027 (voyage 3 of 3) → Balcony/Veranda, Suite

**How to pull:**
```bash
python3 /home/john/Thunderbird/scripts/perx_cabin_pricer.py --brief
```

If no live data (first run or Perx session expired): read `data/perx_cabin_prices.json` for last cached prices. Label as [LIVE] or [cached dd-Mon].

**Signal logic:** Interline rate on Perx is a **leading indicator** — heavy discounts precede TA rate release by 7–14 days. Flag any sailing where price is ≥15% below baseline.

Signal thresholds: 👁 WATCH (−15%), ⚠️ SIGNAL (−25%), 🔴 URGENT (−35%) → check TA portals immediately.

### 4. WING HEALTH
[Table: System | Status]
Rows: MCP server | Telegram D2MC2C | Telegram Dani | Chrome:9222 | OpenCode | OAuth token
Use ✅ ONLINE / LIVE, ❌ OFFLINE/EXPIRED, 💤 UNKNOWN

### 5. STAFF ASSIGNMENTS
[Table: Persona | Status | Active Tasks]
Read from hale_state.json staff_load. ACTIVE if last_seen=true, OFFLINE if false.
Show last brain dispatch.

### 6. DECISIONS NEEDED
Numbered list — only items requiring Commander action.
Sources: WF-17 gate items, OAuth token issues, departures within 21 days, P0 missions.
If none: "No Commander decisions required today."

### 7. INTEL FLASH
One-liners: scheduled reviews due today, SO anniversaries, mission board P0s firing.

---
— V. Hale, VCS · Thunderbird Wing · [DATE HH:MM MT]
— Victoria "Victory" Hale, SES-6 | Thunderbird Wing | [DATE HH:MM MT]
Next brief: [DATE+1] 07:00 MT
```

Client Wire table data sources:
- Client names, ships, departure dates → read dossiers in `/home/john/Thunderbird/dossiers/`
- FPD status → hale_state.json or session_autosave_latest.md if aggregated there
- If dossier data unavailable, use data from last known hale_brief.md as fallback, flagging as "from prior brief — verify"

---

## Step 7 — Send to Commander via gmail_send_from_wing

**This is a full send, not a draft. johnloucks3 is within-wing. No WF-17 gate.**

```python
import sys
sys.path.insert(0, '/home/john/Thunderbird')
sys.path.insert(0, '/home/john/Thunderbird/core/email')

from thunderbird_gmail import gmail_send_from_wing

# brief_html = the HTML-formatted brief body (build from Step 6 content)
# For plain-text brief: pass markdown directly — _wrap_staff_html() handles conversion

result = gmail_send_from_wing(
    to="johnloucks3@gmail.com",
    subject=f"Thunderbird Daily Brief — {date_str} · {time_str} MT",
    body=brief_body,       # plain text or HTML string from Step 6
    persona_id="COS",      # Victory Hale — COS template with 4-ring command seal
)
print(result)
# Expected: {"status": "success", "action": "sent", "message_id": "...", ...}
```

`gmail_send_from_wing()` signature:
- `to: str` — recipient address (must be in COMMANDER_ADDRS set)
- `subject: str`
- `body: str` — plain text or HTML; `_wrap_staff_html(body, "COS")` applied automatically
- `persona_id: str` — default "COS"; uses COS command-grade dark template with 4-ring seal
- `cc: Optional[str]` — not needed for brief

Sends FROM `d2mconcierge@gmail.com` with display name "Victory Hale, D2M Travel".
COS template: dark navy background, gold rings, command-channel footer.

**If gmail_send_from_wing fails with auth error:**
```bash
# Check token file exists
ls /home/john/Thunderbird/creds/johnloucks3_token.json
ls /home/john/Thunderbird/gmail_token.json

# Refresh token (requires interactive browser — flag to Commander)
# python3 /home/john/Thunderbird/core/email/thunderbird_gmail.py --authorize
```

---

## Step 8 — Write hale_brief.md + Update hale_state.json

After send confirmation, persist the brief:

```python
from pathlib import Path
from datetime import datetime, timezone, timedelta

MT = timezone(timedelta(hours=-6))
now_str = datetime.now(MT).strftime("%Y-%m-%d %H:%M MT")

# Write brief to canonical file
Path("/home/john/Thunderbird/hale_brief.md").write_text(brief_markdown)

# Update session checkpoint in hale_state.json
import json
state_path = Path("/home/john/Thunderbird/hale_state.json")
state = json.loads(state_path.read_text())
state["session_context"]["last_checkpoint"] = datetime.now(MT).isoformat()
state_path.write_text(json.dumps(state, indent=2, default=str))
```

---

## Quality Checklist (verify before send)

- [ ] Blackboard sync ran successfully (or fallback used and noted)
- [ ] Mission board pulled — active count matches reality
- [ ] Financial pulse: all 5 metrics present, `last_checked` noted
- [ ] Wing health: all 6 systems have a status (never blank)
- [ ] Staff load: active counts match staff_load in hale_state.json
- [ ] Decisions Needed: only items requiring Commander action (not status items)
- [ ] FPD overdue flags: clients with OVERDUE FPDs are flagged with day count
- [ ] WF-17 gate: staged drafts listed with oldest-first ordering
- [ ] Subject line includes date and time MT
- [ ] Sent FROM d2mconcierge · persona_id="COS" · TO johnloucks3@gmail.com
- [ ] hale_brief.md written after send
- [ ] hale_state.json session checkpoint updated

---

## Routing Rules

| Email type | Account | Action |
|---|---|---|
| Morning brief | d2mconcierge → johnloucks3 | Full send — gmail_send_from_wing() |
| Client draft | d2mconcierge | Draft only — gmail_create_draft_sync() |
| Personal | johnloucks3 | Draft only — WING-PERSONAL-DRAFT label |

**PII fence:** Brief contains no raw client PII beyond names and booking references — all figures are aggregated. Do NOT pass brief content to DeepSeek/external LLMs. Brief synthesis stays inside Claude Code / OpenCode.

---

## Common Issues + Fixes

| Issue | Fix |
|---|---|
| `blackboard_sync.py` prints PARTIAL | Check which files failed; proceed with what succeeded |
| `invalid_grant` in open_tasks | OAuth token expired; flag in Wing Health section as ❌; note in Decisions Needed |
| `mission_board.json` locked | Retry after 3s — another process was writing; `LOCK_PATH` auto-clears |
| `hale_state.json` has no `financial_pulse` key | Financial pulse not run this session — note in brief as "STALE — pulse not run" |
| `gmail_send_from_wing` raises RuntimeError | Wing Gmail not authorized — check `~/Thunderbird/creds/` for persona token; flag to Commander |
| `_wrap_staff_html` import error | `sys.path.insert(0, '/home/john/Thunderbird/core/email')` before import |
| Brief lands in spam | Already mitigated — d2mconcierge→johnloucks3 is an established internal send path |
| `staff_load` keys don't match (DEM vs INTEL) | hale_state.json uses 5-seat OC names: HALE, DANI, STERLING, INTEL, HARLAN — map as needed |
