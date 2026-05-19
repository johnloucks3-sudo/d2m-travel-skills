# STAFF TASKING TIMERS SYSTEM
## Dreams2Memories Travel, LLC | Thunderbird OS | v1.0 | 2026-04-08

---

## OBJECTIVE

**Commander Vision:** *"When I am dealing with clients, the staff gives me what I need BEFORE I even need it and it is well composed, reflecting great credit upon D2M."*

**System Purpose:** Automatically task the A2→A6→A9→A3 workflow at precise deadlines derived from the 35-touchpoint client lifecycle architecture, ensuring all client deliverables are drafted, reviewed, and ready for Commander approval on time.

---

## ARCHITECTURE OVERVIEW

```
ANCHOR DATES (Client Dossier)
         ↓
         ├─ Booking Date (D+0)
         ├─ Final Payment Date (FPD)
         └─ Embarkation Date (EMB)
                  ↓
    DEADLINE CALCULATOR
    (35-touchpoint map + rules)
                  ↓
         TASK QUEUE GENERATOR
    (next 90 days, priority-sorted)
                  ↓
         ┌────────┼────────┐
         ↓        ↓        ↓
      A2/A6    A9/A3   COS/A3
       INBOX   INBOX   INBOX
   (goose)    (both)  (claude)
         ↓        ↓        ↓
    WF-17 GATE (COS reviews logo, sig block, stationery)
         ↓
    COMMANDER APPROVAL (johnloucks3@gmail.com)
         ↓
       SEND
```

---

## COMPONENTS

### 1. ANCHOR DATE DETECTION
**File:** `core/lifecycle/client_ingester.py` (existing)

Scans dossiers in `~/Thunderbird/dossiers/` for:
- `booking_date` — when client booked (D+0, immovable)
- `embark_date` — sail date (T-0, immovable)
- `fpd_date` — calculated as embark_date - 120 days (Oceania/Cunard: -90 days)

If `fpd_date` not present, system calculates it from embark_date.

### 2. DEADLINE CALCULATION ENGINE
**File:** `OpsCenter/staff_tasking_timers_system.py` (NEW)

Maps all 35 touchpoints to anchor dates:
- **Booking-based:** D+0, D+7, D+14, D+30 → add days to booking_date
- **Embarkation-based:** T-180, T-120, T-90, T-7, T-0, T+7 → add/subtract from embark_date
- **FPD-based:** FPD-30, FPD-1, FPD+1 → add/subtract from fpd_date
- **Month-offset:** "Month 3 + 14 days" → parse month number and add days

### 3. TASK QUEUE GENERATOR
Generates task list for next 90 days:

```python
for each client:
    for each touchpoint:
        send_date = calculate_deadline(anchor_date, offset)
        draft_due = send_date - touchpoint.draft_lead_days
        
        if draft_due <= now and send_date > now:
            queue.append(TASK)
```

**Draft Lead Times (from lifecycle architecture):**
- Standard: 14 days before send
- Insurance (7-day rule): 3 days before send
- Urgent: 0 days (same-day draft)

### 4. STAFF INBOX DISPATCHER
Routes tasks to correct inboxes:

| Owners | Route To |
|--------|----------|
| A2, A6, A9 (research/narrative/finance) | `opencode_inbox.md` |
| A3, COS, EXEC | `claude_inbox.md` |
| Mixed (e.g., A2→A6→A3) | Route to primary owner |

**Task Format:**
```markdown
---
## TASK: TASK-0.5-Furlow
status: UNREAD
from: Staff-Tasking-Timers-System
injected: 2026-04-08T06:15:00Z
priority: P0
task: |
  Deliverable: Welcome / voyage validation email
  Client: Furlow (Regent Grandeur, Aug 29, 2026)
  Phase: 0 / Touchpoint 0.5
  Send Date: 2026-04-14
  Owners: A2→A6→A9→A3

  Draft due by 2026-04-07.
  For WF-17 gate and Commander approval flow.
```

### 5. CRITICAL PATH ENFORCEMENT
6 touchpoints with hard deadlines that **cannot slip**:

| Touchpoint | Rule | Deadline | Why |
|------------|------|----------|-----|
| **0.3** | 7-DAY RULE | D+7 | Insurance waiver expires D+14-21 |
| **1.5** | T-12mo | T-12 months | Business class vanishes, fares jump |
| **2.3** | T-10mo | T-10 months | Luxury pre/post hotels fill fast |
| **2.6** | T-7mo | T-7 months | Before excursion window opens |
| **2.9** | T-30 | FPD-30 | Payment deadline enforcement |
| **3.3** | T-21 | T-21 days | Client needs 2 weeks to resolve gaps |

When critical path item is queued, system appends **⚠️ CRITICAL** flag to Commander notification.

### 6. COMMANDER NOTIFICATION PROTOCOL
**Destination:** `/home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md`

Appends summary at daily task run:
```markdown
## STAFF-TASKING-TIMERS | 2026-04-08 06:15 MT
**12 tasks queued** for next 90 days

⚠️ **CRITICAL PATH** (2 items):
- 0.3: Insurance recommendation (7-DAY RULE)
- 2.9: FPD 30-day reminder (T-30)

**By Client:**
- Furlow: 4 tasks (Aug 29 embark)
- Lyons: 3 tasks (Aug 11 embark)
- McLeod: 2 tasks (Jun 23 embark)
- ...
```

### 7. QUALITY VALIDATION FRAMEWORK
**WF-17 Gate (before Commander sees draft):**

**COS Checklist (touchpoints before send):**
1. ✓ Logo renders in email sig block
2. ✓ Sig block uses concierge@d2mluxury.quest
3. ✓ Stationery: cream (#f7f3ea), blue (#0000ff), Georgia font
4. ✓ Sign-off: "Thanks" or "Thank you" (NEVER "Best")
5. ✓ No AI disclaimer unless Commander adds as PS
6. ✓ No "happy to help," no concierge announce, no ⚠ unpaid
7. ✓ One-sentence CTA (next action)
8. ✓ CC johnloucks3 on any outbound changes

If QA fails, task is returned to A3 with defect note.

---

## EXECUTION FLOW — DAILY CYCLE

### 06:00 AM MT — Timer Fires
```bash
systemctl start staff-tasking-timers-system.service
```

### 06:05 AM MT — Python Script Runs
1. **Load:** Client dossiers from `~/Thunderbird/dossiers/*.json`
2. **Calculate:** All 35 deadlines for each client
3. **Filter:** Next 90 days, sorted by draft due date
4. **Route:** Append tasks to `claude_inbox.md` and `opencode_inbox.md`
5. **Notify:** Append summary to `claude_outbox.md`
6. **Persist:** Save schedule to `staff_tasking_schedule.json` for dashboard

### ~06:10 AM MT — Staff Picks Up Tasks
- `d2m-tasking-watcher.service` detects UNREAD tasks
- Routes to Claude (claude_inbox) or Goose (opencode_inbox)
- Staff agents task their respective team members
- A2 begins research input (T-21 before send)

### T-14 Days Before Send — A3 Submits Draft
A3 aggregates A2/A6/A9 inputs, applies voice, submits to COS for WF-17 review.

### T-7 Days Before Send — COS QA Gate
COS reviews draft against 8-point checklist. If pass → surface to Commander. If fail → return to A3.

### Send Day — Commander Approval
Commander approves draft from `claude_inbox.md` or `claude_outbox.md`. COS sends via `thunderbird_gmail.py`.

---

## SYSTEMD INTEGRATION

### Installation

```bash
# Copy files to systemd directory
sudo cp /home/john/Thunderbird/OpsCenter/staff_tasking_timers_system.timer \
        /etc/systemd/system/
sudo cp /home/john/Thunderbird/OpsCenter/staff_tasking_timers_system.service \
        /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable staff-tasking-timers-system.timer
sudo systemctl start staff-tasking-timers-system.timer

# Verify
systemctl status staff-tasking-timers-system.timer
systemctl list-timers staff-tasking-timers-system.timer
```

### Monitoring

```bash
# Check next scheduled run
systemctl list-timers staff-tasking-timers-system.timer

# View logs
journalctl -u staff-tasking-timers-system.service -n 50 -f

# Manual trigger (for testing)
systemctl start staff-tasking-timers-system.service

# Check schedule JSON
cat /home/john/Thunderbird/OpsCenter/staff_tasking_schedule.json
```

### Troubleshooting

| Issue | Check |
|-------|-------|
| Timer not firing | `systemctl list-timers` — verify next run time |
| Tasks not appearing | Check `systemctl status staff-tasking-timers-system.service` for errors |
| No dossiers loaded | Verify dossier JSON files exist and are valid |
| Wrong client dates | Check dossier fields: `booking_date`, `embark_date`, `fpd_date` |
| Tasks not reaching inboxes | Check file permissions on `claude_inbox.md`, `opencode_inbox.md` |

---

## CONFIGURATION & TUNING

### Dossier Format (Required Fields)

```json
{
  "client_name": "Furlow",
  "booking_date": "2026-04-01",
  "embark_date": "2026-08-29",
  "fpd_date": "2026-05-31",
  "cruise_line": "Regent Seven Seas",
  "ship": "Grandeur",
  "cabin": "Penthouse Suite",
  "guests": 2,
  "paid_status": "PAID"
}
```

### Customizing Run Time

Edit `staff_tasking_timers_system.timer`:
```ini
[Timer]
OnCalendar=daily
OnCalendar=*-*-* 06:00:00  # Change this to your preferred time
```

### Extending Deadline Lead Times

Edit `LIFECYCLE_SCHEDULE` in `staff_tasking_timers_system.py`:
```python
# Example: increase A2 research lead to 21 days
(0, "0.5", "Welcome email", 21, "D+14", "A2→A6→A9→A3"),
```

### Adding New Lifecycle Touchpoints

Append to `LIFECYCLE_SCHEDULE`:
```python
(phase, "X.Y", "Deliverable name", draft_lead_days, "send_date_calc", "Owners"),
```

---

## EXPECTED OUTCOMES

### For Commander
- ✅ Drafts appear in inbox 14-21 days before send
- ✅ All critical-path items flagged with ⚠️
- ✅ Clean, WF-17-compliant drafts ready for approval
- ✅ No surprises — deadlines visible 90 days in advance

### For A3 (Dani)
- ✅ Clear owner routing (A2→A6→A9→A3)
- ✅ 14-day draft window (never rushing)
- ✅ COS QA feedback before Commander sees it
- ✅ Drafts reflect "great credit upon D2M"

### For COS (Hale)
- ✅ Automated task dispatcher (zero manual tasking)
- ✅ WF-17 quality gate enforcement
- ✅ Critical path visibility
- ✅ Staff workflow coordination (no deadlines slip)

### For Staff (A2, A6, A9)
- ✅ Clear, time-stamped tasks in inbox
- ✅ No ambiguity on deadline or scope
- ✅ Feedback loop visible in dossier archive

---

## INTEGRATION POINTS

| Module | Integration |
|--------|-----------|
| `core/lifecycle/client_ingester.py` | Anchor date detection |
| `thunderbird_dossier.py` | Dossier CRUD, auto-update on send |
| `d2m-tasking-watcher.service` | Detects UNREAD tasks, routes to agents |
| `thunderbird_gmail.py` | Final send execution |
| WF-17 gate | COS logo/stationery validation |
| Commander inbox | johnloucks3@gmail.com notification |

---

## SUPPORT & ESCALATION

**System Stuck?**
```bash
# Check service status
systemctl status staff-tasking-timers-system.service

# View full log
journalctl -u staff-tasking-timers-system.service -n 100

# Run manually to debug
python3 /home/john/Thunderbird/OpsCenter/staff_tasking_timers_system.py
```

**Tasks Not Queuing?**
1. Verify dossiers exist and have `booking_date`, `embark_date`
2. Verify 90-day window (check current date vs. client embark dates)
3. Check file permissions on inboxes
4. Review logs for parse errors

**Critical Path Miss?**
1. Check dossier for missing anchor date
2. Verify FPD calculation (embark - 120 days)
3. Flag to Commander immediately with root cause

---

*Col Victoria "Iron Vic" Hale | Thunderbird Wing | Staff Tasking Timers System v1.0 | 2026-04-08*
