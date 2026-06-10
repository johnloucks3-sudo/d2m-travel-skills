# Work Item Tracker — Autonomous Runner Action Items

## Overview
Hale tracks 8 work items from the autonomous runner 4-hour test. **Monitoring only — no pestering.** Red alerts only when deadlines pass or blockers surface.

## 8 Items Being Tracked

| ID | Owner | Priority | Deadline | Status |
|-------|---------|----------|----------|---------|
| WI-001 | Sterling | P0 | Jun 13 | Grandeur Furlow HEL→ARN seat assignment |
| WI-002 | Dembe | P1 | Jun 15 | McLeod Hilton Molino Stucky CRS # |
| WI-003 | Dembe | P1 | Jun 17 | McLeod pre-voyage (phone, GIF, charges) |
| WI-004 | Dembe | P1 | Jun 15 | Kuklinski Jun 15 validation email |
| WI-005 | Dembe | P1 | Jun 20 | Kuklinski Josh Morton form |
| WI-006 | Dembe | P1 | Jun 20 | Grandeur Furlow address + seat docs |
| WI-007 | Intel | P1 | Jun 20 | Kuklinski post-departure insurance |
| WI-008 | Dembe | P2 | Aug 22 | Grandeur excursion recommendations |

## Quick Commands

```bash
# Show all work items
python3 /home/john/Thunderbird/OpsCenter/work_item_tracker.py status

# Get JSON summary (for morning brief + automation)
python3 /home/john/Thunderbird/OpsCenter/work_item_tracker.py brief

# Mark item as in progress
python3 /home/john/Thunderbird/OpsCenter/work_item_tracker.py in_progress WI-001

# Mark item as complete
python3 /home/john/Thunderbird/OpsCenter/work_item_tracker.py complete WI-001 "Optional notes here"
```

Or source the shortcut commands:
```bash
source /home/john/Thunderbird/OpsCenter/work_item_commands.sh
wi-status          # Show all
wi-start WI-001    # Mark in progress
wi-done WI-001     # Mark complete
```

## Integration Points

### Morning Brief (0530 MT)
The morning brief automatically includes work item status:
- **Summary**: X/8 complete | Y in progress | Z open
- **Progress bar**: 0% → 100%
- **Red alerts**: Any overdue items (deadline passed)

### Autonomous Runner (Every 2 hours, weekdays 0600–2200 MT)
When runner identifies work completion, it will:
1. Detect completion from dossier/email/portal activity
2. Update work item tracker automatically
3. Surface in morning brief + exception alerts

### Weekly Review
Every Monday, work item summary included in weekly retro.

## Monitoring Only

**What Hale does:**
- ✅ Tracks item status (open/in progress/complete)
- ✅ Alerts on overdue items (red status, deadline passed)
- ✅ Reports progress in morning brief + weekly review
- ✅ No nagging, no reminders, no escalations to Commander

**What Hale does NOT do:**
- ❌ Send Telegram pings to mark items
- ❌ Generate follow-up emails to staff
- ❌ Chase staff for progress updates
- ❌ Escalate to Commander (except RED status: deadline passed)

## Red Alert Criteria

Hale sends **Telegram alert to Commander ONLY when:**
1. **Deadline passed** (item is open/in_progress AND deadline date ≤ today)
2. **Critical blocker** (item marked with blocker status in notes)

Example red alert:
```
🚨 WI-001 OVERDUE
   Grandeur Furlow HEL→ARN seat assignment
   Deadline: Jun 13 | Status: Open
   Owner: Sterling
```

## File Locations

- **Tracker data**: `/home/john/Thunderbird/OpsCenter/work_items_active.json`
- **Tracker script**: `/home/john/Thunderbird/OpsCenter/work_item_tracker.py`
- **Commands shortcut**: `/home/john/Thunderbird/OpsCenter/work_item_commands.sh`
- **Morning brief integration**: `/home/john/Thunderbird/OpsCenter/hale_morning_brief.py`

## Manual Updates

Commander or staff can manually update items:

```bash
# If Sterling completes the seat assignment
python3 work_item_tracker.py complete WI-001 "Called Finnair AA 9018 on Jun 10. Seats confirmed: 14A 14B for Furlow. CRS updated."

# If Dembe starts working on McLeod
python3 work_item_tracker.py in_progress WI-002

# If Dembe completes McLeod hotel
python3 work_item_tracker.py complete WI-002 "Hilton Venice confirmed, CRS #HV-2026-06-XXX, sent to clients Jun 12"
```

Notes are optional but encouraged for audit trail.

## Design Philosophy

This tracker runs **inside OpenCode** — no external tools, no Telegram spam, no dashboard overhead. Just:
1. Read the tracker for status
2. Update it when work completes
3. Morning brief shows progress
4. Red alerts only on overdue

No ceremony. No pestering. Just status.
