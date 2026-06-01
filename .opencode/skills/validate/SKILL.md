---
name: validate
description: "Run full trip validation for a client booking. Checks dossier completeness, TESS booking status, FPD, financial accuracy. Triggers on: validate, trip validation, booking check, dossier check, validate trip, validate booking, pre-departure check, FPD check, validate client"
---

# /validate — Trip Validation Procedure

You execute this procedure yourself. Full Wing validation — not a handoff.

## Usage

```
/validate [client-name or dossier-file]
```

Example: `/validate Kuklinski` or `/validate DOSSIER_VikingMars_Kuklinski_Dec2026.md`

## Step 1 — Find the Dossier

```bash
# Find by client name (case-insensitive)
ls /home/john/Thunderbird/dossiers/ | grep -i "[client]"

# Read the full dossier
cat /home/john/Thunderbird/dossiers/[DOSSIER_FILE]
```

Key fields to extract and hold in context:
- Client names (all travelers)
- Ship + cruise line
- Departure date + return date
- Booking reference(s)
- Cabin category
- Final Payment Date (FPD)
- Total cost + amount paid + balance due
- Special requests (dining, accessibility, celebrations)
- Air arrangements (if any)

## Step 2 — Run Validation Scripts

```bash
cd /home/john/Thunderbird

# Primary validation (checks dossier completeness, flags missing fields)
python3 itinerary/validate_dossier.py

# Trip architecture check (checks booking structure, touchpoint readiness)
python3 itinerary/thunderbird_trip_architect.py
```

If errors: read the output carefully. Missing fields = gaps to fill before proceeding.

## Step 3 — TESS Cross-Reference

```bash
# Check TESS booking status
python3 -c "
import sys; sys.path.insert(0, '/home/john/Thunderbird')
from core.booking.thunderbird_dossier import get_booking_summary
# Check TESS for booking ref in dossier
"
```

Verify against TESS:
- Booking status (confirmed / pending / waitlisted)
- FPD matches dossier
- Passenger names match exactly
- Cabin assigned
- Promotions / upgrades applied

**Primary source hierarchy:** TESS portal → booking record → client dossier
When portal and dossier disagree → portal is authoritative → flag discrepancy.

## Step 4 — FPD Alert Check

| Days to FPD | Status | Action |
|---|---|---|
| > 60 days | Green | Note in output |
| 30-60 days | Yellow | Flag to Commander |
| < 30 days | Red | Immediate escalation |
| Overdue | CRITICAL | Commander + client contact needed |

```bash
# Check all client FPDs
python3 /home/john/Thunderbird/OpsCenter/mission_board_sync.py list
```

## Step 5 — Financial Verification

For any validation email with $ figures — Harlan 6-step required:
1. Portal balance (live portal check)
2. Portal FPD (live portal check)
3. Compare vs dossier — flag any delta
4. Root cause the delta or leave as unresolved flag
5. Credits/promotions verified
6. Sign-off: `"Confirmed: $X balance due, FPD [date], source: [portal/TESS]"`

## Step 6 — Validation Output

Produce a structured validation checklist:

```
VALIDATION REPORT — [Client] — [Ship] — Departs [Date]
Generated: [timestamp]

BOOKING STATUS: [CONFIRMED/PENDING/ISSUE]
  Booking Ref: [ref]
  Travelers: [names]
  Cabin: [category + number if assigned]

FINANCIAL STATUS:
  Total cost: $[X]
  Paid to date: $[X]
  Balance due: $[X]
  FPD: [date] — [GREEN/YELLOW/RED/OVERDUE]

DOSSIER COMPLETENESS:
  ✅ / ❌ Contact info complete
  ✅ / ❌ Special requests documented
  ✅ / ❌ Air arrangements confirmed
  ✅ / ❌ Pre/post hotel documented
  ✅ / ❌ Excursion interests noted

FLAGS: [any discrepancies, missing data, or action items]

READY FOR: [next lifecycle touchpoint]
```

## Common Issues + Fixes

| Issue | Fix |
|---|---|
| Dossier not found | Check `dossiers/prospects/` for pre-booking clients |
| TESS auth error | `systemctl --user status thunderbird-mcp.service` — MCP may be down |
| FPD discrepancy | Portal is authoritative — update dossier, flag to Commander |
| validate_dossier.py crashes | Check Python path: `cd /home/john/Thunderbird` first |
