# STAFF TASKING TIMER SYSTEM ARCHITECTURE
## Automated Client Deliverable Workflow
### "Staff gives me what I need BEFORE I even need it and it is well composed"
### Dreams2Memories Travel, LLC | Thunderbird OS | 2026-04-07

---

## EXECUTIVE SUMMARY

**Objective:** Automate the entire 35-touchpoint client lifecycle with systemd timers that task staff members at precise intervals, ensuring Commander receives polished, ready-to-send drafts 14 days before each client communication deadline.

**Core Principle:** Staff workflow completes **BEFORE** Commander needs to review, with quality assurance built into every step.

---

## ARCHITECTURAL COMPONENTS

### 1. TIMER TIERS

```
TIER 1: Phase Timers (6)          → Monthly cadence per client phase
TIER 2: Touchpoint Timers (35)     → Specific deliverable triggers
TIER 3: Staff Workflow Timers (4)  → A2→A6→A9→A3 chained sequence
TIER 4: Quality Gates (2)          → COS WF-17 → Commander approval
```

### 2. TIMING CALCULATION ENGINE

```python
def calculate_timers(booking_date, embark_date, fpd):
    """Dynamically calculates all timer triggers based on anchor dates"""
    
    # Convert all T-minus to actual calendar dates
    phases = {
        'phase_0': booking_date + timedelta(days=30),
        'phase_1': embark_date - timedelta(days=365),  # T-12mo
        'phase_2': fpd,  # Final Payment Date anchor
        'phase_3': embark_date - timedelta(days=120),  # T-4mo
        'phase_4': embark_date,
        'phase_5': embark_date + timedelta(days=30)
    }
    
    # Staff workflow offsets (days before send)
    workflow_offsets = {
        'a2_research': 21,
        'a6_narrative': 18, 
        'a9_financial': 16,
        'a3_final': 14,
        'cos_review': 7,
        'commander_approval': 0
    }
    
    return phases, workflow_offsets
```

### 3. SYSTEMD TIMER STRUCTURE

```bash
# Example: Pre-voyage brief timer (Task 3.3)
/etc/systemd/system/d2m-task-3.3-pre-voyage-brief.timer
/etc/systemd/system/d2m-task-3.3-pre-voyage-brief.service

# Timer activation:
systemctl enable d2m-task-3.3-pre-voyage-brief.timer
systemctl start d2m-task-3.3-pre-voyage-brief.timer
```

---

## STAFF WORKFLOW AUTOMATION

### A. PRE-SEND WORKFLOW CHAIN (14-Day Pipeline)

```
          [T-21]              [T-18]              [T-16]              [T-14]
CLIENT NEED → A2 RESEARCH → A6 NARRATIVE → A9 FINANCIAL → A3 FINAL DRAFT → COS → COMMANDER
   Send Date    Raw Intel      Story Craft     $$ Validation   Brand Polish   WF-17 Gate   ✅ Ready
```

### B. STAFF TASKING PROTOCOL

| Role | Lead Time | Action | Output Destination |
|------|----------|--------|-------------------|
| **A2 (Dembe)** | T-21 | Research intel delivery | `opencode_inbox.md` (data) |
| **A6 (Moreau)** | T-18 | Narrative drafting | `claude_inbox.md` (copy) |
| **A9 (Gauge)** | T-16 | Financial validation | `claude_inbox.md` (pricing) |
| **A3 (Dani)** | T-14 | Final voice polish | `claude_inbox.md` (ready draft) |
| **COS (Hale)** | T-7 | WF-17 compliance check | `claude_inbox.md` (approved) |
| **Commander** | Send day | Final send approval | `johnloucks3@gmail.com` |

---

## TIMER CATALOG — 35 TOUCHPOINTS

### PHASE 0 — ONBOARDING (D+0 to D+30)

| Task | Description | Draft Due | Send | Timer Trigger | Staff Chain |
|------|-------------|----------|------|---------------|-------------|
| 0.3 | Insurance email | D+3 | D+7 | `booking_date + 3d` | A9→A3 (**7-day rule**) |
| 0.4 | Guest profile forms | D+3 | D+7 | `booking_date + 3d` | A3 (direct) |
| 0.5 | Welcome email | D+7 | D+14 | `booking_date + 7d` | A2→A6→A9→A3 |

### PHASE 1 — DISCOVERY (D+30 to T-12mo)

| Task | Description | Draft Due | Send | Timer Trigger | Staff Chain |
|------|-------------|----------|------|---------------|-------------|
| 1.4 | Voyage preview | Month 3 | Month 3+14d | `booking_date + 90d` | A2→A6→A3 |
| 1.5 | Air fare delivery | T-12mo−14d | T-12mo | `embark_date - 379d` | A2→A3 |
| 1.6 | Hotel delivery | T-12mo−14d | T-12mo | `embark_date - 379d` | A2→A6→A3 |

### PHASE 2 — MOMENTUM (T-12mo to T-4mo)

| Task | Description | Draft Due | Send | Timer Trigger | Staff Chain |
|------|-------------|----------|------|---------------|-------------|
| 2.1 | Air booking decision | T-11mo−14d | T-11mo | `embark_date - 334d` | A2→A9→A3 |
| 2.3 | Hotel booking rec | T-10mo−14d | T-10mo | `embark_date - 304d` | A2→A6→A9→A3 |
| 2.6 | Excursion rec | T-7mo−14d | T-7mo | `embark_date - 194d` | A2→A6→A3 |
| 2.8 | Excursion confirm | T-180+3d | T-180+7d | `embark_date - 177d` | A3 (direct) |
| 2.9 | FPD reminder | FPD−44d | FPD−30 | `fpd - 44d` | A9→A3 |
| 2.12 | Dining rec | T-104d | T-90 | `embark_date - 104d` | A2→A6→A3 |
| 2.14 | FPD confirmation | FPD+0 | FPD+1 | `fpd` | A9→A3 |

### PHASE 3 — PRE-DEPARTURE (T-4mo to T-0)

| Task | Description | Draft Due | Send | Timer Trigger | Staff Chain |
|------|-------------|----------|------|---------------|-------------|
| 3.1 | Document audit | T-90−14d | T-90 | `embark_date - 104d` | COS→A3 |
| 3.3 | Pre-voyage brief | T-35 | T-21 | `embark_date - 35d` | A2→A6→A9→A3 |
| 3.5 | Final confirmation | T-10 | T-7 | `embark_date - 10d` | A3 (direct) |
| 3.6 | Send-off email | T-3 | T-0 | `embark_date - 3d` | A6→A3 |

### PHASE 5 — POST-VOYAGE (T+1 to T+30)

| Task | Description | Draft Due | Send | Timer Trigger | Staff Chain |
|------|-------------|----------|------|---------------|-------------|
| 5.1 | Welcome home | T+voyage−3 | T+1 to T+3 | `disembark_date - 3d` | A6→A3 |
| 5.2 | Post-voyage survey | T+voyage−3 | T+7 | `disembark_date - 3d` | A3 (direct) |
| 5.3 | Thank you + referral | T+12 | T+14 | `disembark_date + 12d` | A6→A3 |
| 5.4 | Next voyage plant | T+28 | T+30 | `disembark_date + 28d` | A2→A6→A3 |

---

## CRITICAL PATH TIMERS (NON-NEGOTIABLE)

| Priority | Task | Timer Date Calculation | Consequences of Miss |
|----------|------|----------------------|---------------------|
| **P0** | Insurance email | `booking_date + 3d` | Pre-existing waiver expires → coverage void |
| **P0** | Air fare delivery | `embark_date - 379d` | Business class inventory vanishes → client pays 2-3× |
| **P0** | Hotel booking | `embark_date - 304d` | Luxury properties fill → inferior options at higher rates |
| **P0** | Excursion research | `AT BOOKING` (Viking) | Best excursions sell out → client disappointment |
| **P0** | Dining reservations | `embark_date - 104d` | Specialty restaurants fill → missed experiences |
| **P0** | Final Payment | `fpd - 44d` (reminder) | Booking cancellation → loss of deposit |

---

## QUALITY ASSURANCE FRAMEWORK

### A. WF-17 COMPLIANCE CHECKS (COS GATE)
- ✅ D2M logo present and properly sized
- ✅ Stationery template (cream #f7f3ea, blue ink #0000ff)
- ✅ Signature block: "Dani, Dreams2Memories Travel, LLC"
- ✅ No AI disclaimer unless Commander PS added
- ✅ Phone: 719-291-0742 included
- ✅ Legal: FL ST1578, CA 2090937-50, WA UBID 603189022, IA 1202

### B. A3 FINAL DRAFT STANDARDS (T-14)
- ✅ Voice: Dani (A3) — Aggregate → Artist → Advocate
- ✅ Tone: Warm, personal, luxury travel expertise
- ✅ Accuracy: All prices, dates, details validated
- ✅ Completeness: No missing information
- ✅ Brand alignment: Reflects great credit upon D2M

### C. COMMANDER READINESS CHECKLIST (Send Day)
- ✅ Draft received 14 days prior (7 days for insurance)
- ✅ COS WF-17 compliance verified
- ✅ All client-specific details accurate
- ✅ No last-minute changes required
- ✅ Send confidence: 100%

---

## SYSTEM INTEGRATION

### 1. TIMER GENERATION ENGINE
```python
# Activated on each new booking
def generate_timers(client_data):
    """Creates systemd timers for all 35 touchpoints"""
    
    dates = calculate_timers(client_data['booking_date'], 
                             client_data['embark_date'],
                             client_data['fpd'])
    
    for task_id, task_info in TASK_CATALOG.items():
        trigger_date = dates[task_info['phase']] + task_info['offset']
        
        # Create systemd timer
        create_systemd_timer(f"d2m-{client_data['id']}-{task_id}", 
                           trigger_date,
                           task_info['staff_chain'])
```

### 2. STAFF TASKING PROTOCOL
```python
def task_staff_member(staff_role, task_description, due_date):
    """Tasks appropriate staff member via their inbox"""
    
    inbox_map = {
        'A2': '/home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md',
        'A3': '/home/john/Thunderbird/claude_inbox.md',
        'A6': '/home/john/Thunderbird/claude_inbox.md', 
        'A9': '/home/john/Thunderbird/claude_inbox.md',
        'COS': '/home/john/Thunderbird/claude_inbox.md'
    }
    
    task_template = f"""
---
## TASK: {staff_role}-{task_id}-{timestamp}
status: UNREAD
from: Timer System
injected: {current_time}
priority: P1
due: {due_date}
task: {task_description}
"""
    
    append_to_file(inbox_map[staff_role], task_template)
```

### 3. COMMANDER NOTIFICATION
```python
def notify_commander(draft_ready, task_info):
    """Sends email to johnloucks3@gmail.com when draft is ready"""
    
    subject = f"✅ DRAFT READY: {task_info['description']} for {task_info['client']}"
    body = f"""
Draft complete and ready for your review:

- Client: {task_info['client']}
- Deliverable: {task_info['description']}  
- Send Date: {task_info['send_date']}
- Draft Due: {task_info['draft_due']} (✅ {days_early} days early)
- Staff Chain: {task_info['staff_chain']}
- COS WF-17: ✅ Verified

Review draft at: {task_info['draft_location']}
"""
    
    send_gmail("d2mconcierge@gmail.com", "johnloucks3@gmail.com", subject, body)
```

---

## DEPLOYMENT ARCHITECTURE

### 1. TIMER DIRECTORY STRUCTURE
```
/etc/systemd/system/d2m-timers/
├── client_{client_id}/
│   ├── phase_0/
│   │   ├── task_0.3-insurance.timer
│   │   ├── task_0.4-guest-forms.timer
│   │   └── task_0.5-welcome-email.timer
│   ├── phase_1/
│   ├── phase_2/
│   ├── phase_3/
│   ├── phase_4/
│   └── phase_5/
└── templates/
    ├── task_template.timer
    └── task_template.service
```

### 2. MONITORING & LOGGING
```bash
# Timer status monitoring
systemctl list-timers | grep d2m

# Service logs
journalctl -u d2m-*.service --since "1 day ago"

# Task completion tracking
tail -f /home/john/Thunderbird/OpsCenter/logs/task_timers.log
```

### 3. HEALTH CHECKS
```python
def timer_health_check():
    """Validates all timers are active and properly scheduled"""
    
    for client in active_clients:
        for phase in range(6):
            for task in phase_tasks[phase]:
                timer_name = f"d2m-{client['id']}-{task['id']}"
                
                if not timer_active(timer_name):
                    alert_commander(f"Timer failed: {timer_name}")
                    
                if not correct_schedule(timer_name, task['calculated_time']):
                    alert_commander(f"Timer mis-scheduled: {timer_name}")
```

---

## NEXT STEPS FOR IMPLEMENTATION

1. **Phase 1:** Core timer engine + systemd template creation
2. **Phase 2:** Staff tasking automation integration  
3. **Phase 3:** Quality assurance gate implementation
4. **Phase 4:** Commander notification system
5. **Phase 5:** Health monitoring and alerting

**Primary Implementation File:** `core/scheduling/thunderbird_timer_engine.py`

---

*Architecture designed by OpenCode | Schema v1.0 | Ready for Claude implementation | 2026-04-07*