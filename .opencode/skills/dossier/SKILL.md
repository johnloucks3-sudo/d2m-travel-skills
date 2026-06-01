---
name: dossier
description: "Smart client dossier lookup by name. Locate dossier file, surface key fields (ship, FPD, booking ref, travelers, specials, insurance, payment status), run scanner alerts, TESS cross-reference, emit structured summary. Triggers on: dossier, look up client, client file, pull dossier, check client, who is, client profile, show client, client status, client record, find dossier, Kuklinski dossier, McLeod dossier, Furlow dossier, Nichols dossier, Westbrook dossier, Loucks dossier, Spencer dossier, Morton dossier, client lookup, booking summary, show booking"
---

# /dossier — Client Dossier Lookup

You execute this procedure yourself. All steps run natively — no handoff to Claude Code.
Use /ask-opus only for judgment calls on conflicting primary sources.

## Usage

```
/dossier [client name or partial name]
```

Examples: `/dossier Kuklinski` · `/dossier McLeod` · `/dossier furlow` · `/dossier morton`

---

## Step 1 — Locate the Dossier File

```bash
# List all dossiers, grep by client name (case-insensitive)
ls /home/john/Thunderbird/dossiers/ | grep -i "[CLIENT_NAME]"

# If multiple matches, prefer files in this priority order:
#   1. Individual booking dossier (e.g., Kuklinski_Viking_Panama.md)
#   2. Master DOSSIER_ file (e.g., DOSSIER_VikingMars_PanamaCanal_Dec2026.md)
#   3. Prospects subfolder (dossiers/prospects/) — pre-booking clients

# Show the full dossiers directory tree (one level) to orient:
ls /home/john/Thunderbird/dossiers/
ls /home/john/Thunderbird/dossiers/prospects/ 2>/dev/null
```

**File naming conventions (from dossiers/CLAUDE.md):**
| Pattern | Example |
|---|---|
| Individual booking | `{LastName}_{Ship}_{BookingRef}.md` |
| Master trip | `DOSSIER_{Ship}_{Region}_{MonthYear}.md` |
| Supplemental | `{LastName}_{Topic}.md` |

If no match found: check both the root `dossiers/` dir and `dossiers/prospects/`. If still missing, report: "No dossier found for [name] — check spelling or use `/validate` to create."

---

## Step 2 — Read the Dossier + Extract Key Fields

```bash
cat /home/john/Thunderbird/dossiers/[DOSSIER_FILE]
```

Extract and hold these fields in context. Surface ALL of them in your output.

**Required fields (ERROR if missing):**
- Client name(s) — full legal names as on passport
- Ship / cruise line
- Booking confirmation #(s)
- Departure date (embarkation)
- Cabin category + number (if assigned)
- Final Payment Date (FPD) + amount due / paid status
- Client email address(es)

**Important fields (WARN if missing):**
- Air travel — PNR, airline, routes, seat assignments
- Insurance status (see classification table below)
- Hotel — pre/post cruise
- Transfers — all ground transport
- Dietary / medical / accessibility notes
- Emergency contacts
- Specials — celebrations, preferences, loyalty status

**YAML frontmatter fields to check first** (at top of file between `---` delimiters):
```
client, full_name, cruise_line, ship, voyage, departure, return,
fpd, fpd_amount, fpd_status, status, relationship, completed_tps
```

---

## Step 3 — Run Dossier Validation

```bash
cd /home/john/Thunderbird

# Single client (by keyword — case-insensitive):
python3 itinerary/validate_dossier.py --client [name]

# Single client with email JSON output (eliminates manual WF-17 drafting):
python3 itinerary/validate_dossier.py --client [name] --email-json

# Direct file path:
python3 itinerary/validate_dossier.py dossiers/[DOSSIER_FILE]

# All active dossiers:
python3 itinerary/validate_dossier.py --all
```

**Exit codes:**
| Code | Meaning | Action |
|---|---|---|
| 0 | Clean — all checks passed | Safe to generate / proceed |
| 1 | Warnings only | Review before proceeding |
| 2 | Errors | Do NOT generate — fix gaps first |

**What the validator checks:**
- Booking confirmation # present
- Departure date present
- Payment status present
- Client names present
- Client email address present
- Passport data (WARN)
- Flight PNR (WARN)
- Insurance status (WARN)
- Hotel confirmation (WARN)
- Transfer status (WARN)
- Dollar amounts sourced (WARN — Pipeline Integrity Rule 4)
- Known spelling errors (Herculaneum, Valletta, Blacklane, etc.)
- Port order against known voyage sequences
- Pipeline Rule 2: dollar amounts present but no CONFIRMED/INFERRED tags

**Email JSON output** (when `--email-json` flag used) writes to:
`/home/john/Thunderbird/output/{ClientName}_email_template_{YYYY-MM-DD}.json`

Fields in the JSON: `client_name`, `booking_ref`, `ship`, `departure`, `payment_status`, `email_to`, `outstanding_items`, `insurance_status`, `dining_window_relevant`, `suggested_cta`, `harlan_flag`, `draft_subject`

---

## Step 4 — Insurance Status Classification

The validator classifies insurance into one of these states. Report the exact classification:

| Classifier Output | What It Means | Wing Action |
|---|---|---|
| `DECLINED — soft re-raise appropriate` | Client said no | Re-raise gently at next TP |
| `DEFERRED — follow up now` | Client wanted to wait | Follow up immediately |
| `STANDALONE POLICY — verify coverage scope` | Allianz or standalone purchased | Confirm policy # and scope |
| `CC COVERAGE ONLY — no standalone policy` | Chase Sapphire / card coverage | Flag scope gaps |
| `WANTS INSURANCE — no policy yet, action needed` | Expressed interest, not acted | Action required |
| `MENTIONED — status unclear, verify` | Reference found, status unclear | Verify before next TP |
| `NO MENTION — raise proactively` | No insurance discussion on file | Must raise proactively |

---

## Step 5 — FPD Status Check

```bash
# Check all client FPDs via mission board
python3 /home/john/Thunderbird/OpsCenter/mission_board_sync.py list
```

**FPD alert thresholds:**
| Days to FPD | Status | Action |
|---|---|---|
| > 60 days | Green | Note in output |
| 30–60 days | Yellow | Flag to Commander |
| < 30 days | Red | Immediate escalation |
| Overdue | CRITICAL | Commander + client contact needed |

Calculate days to FPD manually from today (2026-06-01) if the script is unavailable.

---

## Step 6 — TESS Cross-Reference

```bash
cd /home/john/Thunderbird

# List all TESS trips
python3 -c "
import sys, json
sys.path.insert(0, '/home/john/Thunderbird')
from core.booking.thunderbird_tess import TessClient
tc = TessClient()
result = tc.list_trips()
print(json.dumps(result, indent=2, default=str))
"

# Get a specific booking by booking ref
python3 -c "
import sys, json
sys.path.insert(0, '/home/john/Thunderbird')
from core.booking.thunderbird_tess import TessClient
tc = TessClient()
result = tc.list_bookings()
print(json.dumps(result, indent=2, default=str))
"
```

**Primary source hierarchy (SO-PIPELINE-INTEGRITY-20260528):**
1. Cruise line portal — verified same session (most authoritative)
2. TESS booking record
3. Client dossier

**When TESS and dossier disagree:** Portal figure is authoritative. Flag the discrepancy explicitly. Do not resolve silently.

Verify against TESS:
- Booking status (confirmed / pending / waitlisted)
- FPD matches dossier
- Passenger names match exactly (must match passport)
- Cabin assigned / category correct
- Promotions / SBC credits applied

---

## Step 7 — Run Dossier Scanner (Gap Detection)

```bash
cd /home/john/Thunderbird

python3 -c "
import sys, json
from datetime import datetime
sys.path.insert(0, '/home/john/Thunderbird')
from core.booking.thunderbird_dossier_scanner import _scan_one_dossier
from pathlib import Path

path = Path('/home/john/Thunderbird/dossiers/[DOSSIER_FILE]')
today = datetime.now()
alerts = _scan_one_dossier(path, today)
for a in alerts:
    print(f'[{a.severity}] {a.category}: {a.message}')
"
```

The scanner flags:
- FPD overdue or within 14 days without payment confirmed
- Unassigned flight seats
- Uncertain passport verification ("I think?")
- Insurance not confirmed (when insurance is mentioned)
- Uncertain portal uploads
- Overdue validation touchpoints
- Open action items (unchecked boxes)
- File corruption (size >500KB or repeated-line artifact)

**Corruption detection:** If scanner returns a CRITICAL corruption alert — do NOT use this dossier for any client work. Restore from Drive or git.

---

## Step 8 — Harlan Financial Flag

For any dossier containing dollar amounts, check whether Harlan 6-step sign-off is needed before any client email is drafted:

The validator's `harlan_flag` field will return one of:
- `"none"` — no dollar amounts in dossier
- `"needs Rule 5 — N dollar amounts present"` — Harlan sign-off required before WF-17
- `"cleared"` — Harlan sign-off already on file

**If `needs Rule 5`:** Before any client email with $ figures proceeds to WF-17, Harlan must complete:
1. Portal balance (live check)
2. Portal FPD (live check)
3. Compare vs dossier — flag any delta
4. Root cause the delta or flag as unresolved
5. Credits / promotions verified
6. Sign-off: `"Confirmed: $X as of [date], source: [portal/TESS/dossier]"`

---

## Step 9 — Structured Output

Produce this block after completing all steps:

```
DOSSIER SUMMARY — [Client Full Name]
Generated: [timestamp]

TRIP:
  Ship:        [ship name and cruise line]
  Voyage:      [route description]
  Departure:   [YYYY-MM-DD — port]
  Return:      [YYYY-MM-DD — port]
  Nights:      [N]

BOOKING(S):
  Ref:         [booking confirmation #]
  Cabin:       [category + number if assigned]
  Travelers:   [names]
  Agency Conf: [if available]

FINANCIAL:
  Total cost:  $[X]
  Paid:        $[X]
  Balance due: $[X]
  FPD:         [date] — [GREEN/YELLOW/RED/OVERDUE] — [days to FPD]
  Harlan flag: [none / needs Rule 5 / cleared]

DOSSIER HEALTH:
  Validator exit: [0=clean / 1=warnings / 2=errors]
  Errors:      [list or "none"]
  Warnings:    [list or "none"]

INSURANCE: [classifier output from Step 4]

KEY SPECIALS:
  [dietary, medical, accessibility, celebrations, loyalty — or "none on file"]

AIR:
  [PNR(s), routes, seat status — or "not booked" / "not on file"]

HOTEL:
  Pre-cruise:  [status or "none"]
  Post-cruise: [status or "none"]

SCANNER ALERTS:
  [CRITICAL/WARNING/INFO alerts — or "none"]

TESS CROSS-REF:
  Status:      [confirmed / pending / not found in TESS]
  Delta:       [discrepancy with dossier — or "none"]

OUTSTANDING ITEMS:
  [numbered list of action items — or "none"]

SUGGESTED CTA:
  [single most important next action for client]

NEXT LIFECYCLE TP:
  [next touchpoint name + when it fires]
```

---

## Active Client Roster (Quick Reference)

| Client | Ship | Booking Ref(s) | Departure | FPD Status |
|---|---|---|---|---|
| Kuklinski Group (3 couples) | Viking Mars | 9593880, 9593873, 9595029 | 2026-12-17 | PAID IN FULL |
| Morton / Dodge | Viking Mars | 9595029 | 2026-12-17 | PAID IN FULL |
| McLeod / McGlasson | Silver Muse | 298475 | 2026-06-23 | PAID IN FULL |
| Furlow | Regent Grandeur | 3071222 | 2026-08-29 | OVERDUE |
| Ely / Darrow | Regent Grandeur | 3096289 | 2026-08-29 | OVERDUE |
| Nichols | Regent Grandeur | 3078056 | 2026-08-29 | OVERDUE |
| Loucks (J&S) | Silver Nova | 566910 | 2026-04-10 | OVERDUE |
| Westbrook | Silver Nova | 566904 | 2026-04-10 | OVERDUE |
| Loucks (J&S) | Regent Grandeur | 3122006 | 2026-12-29 | Pending |

Prospects live in `/home/john/Thunderbird/dossiers/prospects/`.

---

## Trip Keys (thunderbird_dossier.py TRIPS dict)

Use these keys when calling `create_trip_dossier(trip_key)` or `--create` CLI flag:

| Trip Key | Clients |
|---|---|
| `Grandeur_Scandinavia_Aug2026` | Furlow, Ely/Darrow, Nichols |
| `SilverMuse_Mediterranean_Jun2026` | McLeod/McGlasson |
| `VikingMars_PanamaCanal_Dec2026` | Kuklinski x2, Morton/Dodge |
| `SilverNova_Pacific_Apr2026` | Loucks, Westbrook |
| `Regent_LesserAntilles_Dec2026` | McLeod/McGlasson |
| `Regent_Loucks_Dec2026` | Loucks |
| `Prestige_SeasonToCheer_Dec2027` | McLeod/McGlasson |
| `Princess_MexicoRiviera_Mar2027` | McLeod/McGlasson |

```bash
# List all available trips with client names:
cd /home/john/Thunderbird
python3 core/booking/thunderbird_dossier.py --list

# Preview a dossier without writing to Drive:
python3 core/booking/thunderbird_dossier.py --preview VikingMars_PanamaCanal_Dec2026

# Create/refresh a single trip dossier on Drive:
python3 core/booking/thunderbird_dossier.py --create VikingMars_PanamaCanal_Dec2026
```

---

## PII Fence (Hard Rule)

Client dossiers contain PII (names, DOBs, emails, phone numbers, booking refs, payment data).

**Never pass dossier content to DeepSeek, external LLMs, or any brain that is not Claude.**
Strip all PII before any OpenCode ZEN counter-voice call. The Wing stays clean.

---

## Common Issues + Fixes

| Issue | Fix |
|---|---|
| No dossier found for client name | Try partial name: `grep -ri "[partial]" /home/john/Thunderbird/dossiers/` · Check `prospects/` subfolder |
| validate_dossier.py crashes with ImportError | `cd /home/john/Thunderbird` first — script uses relative imports |
| TESS auth error (invalid_grant) | OAuth token expired — run token refresh; check `hale_state.json` open_tasks for current error |
| TESS returns empty bookings | TESS may not have this booking — cross-ref booking ref against dossier, not TESS |
| Dossier file >500KB | Corruption detected — do NOT use. Run: `git show HEAD:dossiers/[FILE]` to restore |
| FPD discrepancy portal vs dossier | Portal is authoritative — update dossier, flag delta to Commander |
| Validator exits 2 (errors) | Fix errors before proceeding to any client email — missing booking ref or client email blocks WF-17 |
| Multiple dossier files for same client | Read both — newer file (by modified date) is primary; older may have additional context |
| Client not in TESS | New booking may not be in CRM yet — use dossier as primary source, flag to Hale for TESS entry |
| Dollar amounts without CONFIRMED tag | Pipeline Rule 2 — tag each amount as CONFIRMED, INFERRED, or UNKNOWN before any email draft |

---

## Feed Into

After dossier lookup:
- Client email needed → `/email-draft` (uses dossier as primary source)
- Validation check needed → `/validate` (full trip validation procedure)
- Flight pricing needed → `/flight-price`
- Tour pricing needed → `/tour-price`
