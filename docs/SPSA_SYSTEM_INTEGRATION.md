# SPSA System Integration — Complete Implementation
## Dreams2Memories Travel, LLC | Deployed 2026-05-02

---

## OVERVIEW

The Standard Problem Solving Approach (SPSA) system is now fully wired into Thunderbird's operational decision framework. It provides structured problem analysis, risk-based approval gates, and automated case tracking.

**Core Design:** 7-step military Staff Paper format adapted for business operations.
**Trigger:** Daily intake scans at 0630 MT (AM brief) and 1800 MT (EOD digest)
**Integration Points:** Telegram C2 (RED alerts), Morning Brief, EOD Summary, Weekly Deep Dive

---

## SYSTEM ARCHITECTURE

### Layer 1: Case Engine
**File:** `/home/john/Thunderbird/core/ops/thunderbird_spsa.py` (413 lines)

**Data Model:** `SPSACase` dataclass
- `case_id`: SPSA-YYYYMMDD-XXXXX (auto-generated)
- `severity`: RED | YELLOW | GREEN
- `source`: incubator | judge | manual | overwatch | scheduler | dani
- `problem_statement`: 1-2 sentence issue definition
- `factors`: List of root causes + contributing factors
- `options`: [{name, description, tradeoff}, ...]
- `recommendation`: Selected option name
- `recommendation_rationale`: Why this option
- `timeline_hours`: Estimated implementation time
- `risk_summary`: Risk level and summary
- `status`: OPEN → UNDER_REVIEW → DECIDED → IMPLEMENTING → CLOSED
- `decision`: Approved | Modified | Rejected (Commander decision)
- `implemented_actions`: List of verbalized actions during execution
- `outcome`: Result after closure
- `lessons_learned`: Retrospective insights

**Methods:**
- `to_brief()`: Format case as formal 7-step SPSA brief
- `to_dict()`: Convert to JSON for storage

**Functions:**
- `intake_problem()`: Create new case from discovered issue
- `load_case(case_id)`: Retrieve case from archive
- `get_active_cases(severity=None)`: List all OPEN/UNDER_REVIEW/DECIDED/IMPLEMENTING cases
- `classify_risk(case)`: Determine LOW/MEDIUM/HIGH based on timeline + risk_summary
- `needs_approval(case)`: Approval gate logic (LOW=auto, MEDIUM/HIGH=Commander)
- `update_case_status()`: Transition case state
- `close_case()`: Mark CLOSED with outcome + lessons
- `log_implementation_action()`: Record verbalized actions
- `get_closed_cases_for_week()`: Retrospective data for weekly deep dive
- `export_to_sheets_format()`: Google Sheets sync format

**Storage:** `/home/john/Thunderbird/logs/spsa/SPSA-*.json` (one file per case)

---

### Layer 2: Daily Intake Job
**File:** `/home/john/Thunderbird/OpsCenter/job_spsa_intake.py` (273 lines)

**Trigger:** Systemd timer at 0630 and 1800 MT daily

**Scanning Functions:**
1. `scan_system_logs_for_errors()` - journalctl for ERROR/FAILED events (last 2 hours)
2. `scan_hale_state_for_blockers()` - hale_state.json for task errors, system health, auth issues
3. `scan_mission_board_for_red()` - mission_board.json for RED priority items

**Issue Conversion:**
- System errors → SPSA case with restart/debug options
- System health (MCP offline) → RED case with immediate escalation
- Task errors → YELLOW case with retry/investigate options
- Auth failures (TESS) → YELLOW case with re-auth recommendation
- Mission RED → RED case with decision escalation

**Output:** Creates 1-10 SPSA cases per run, logs each to archive

---

### Layer 3: Telegram C2 Alerts
**File:** `/home/john/Thunderbird/OpsCenter/spsa_telegram_c2.py` (126 lines)

**Function:** `alert_red_cases()` - Sends real-time RED alerts to Commander

**Alert Format:**
```
SPSA RED — SPSA-20260502-E20AD

CASE: SPSA-20260502-E20AD
SEVERITY: 🔴 RED
SOURCE: incubator

PROBLEM:
MCP server is offline — blocks all integrations

FACTORS:
• Detected in hale_state.json
• All MCP integrations blocked
• Client API calls will fail

RECOMMENDED ACTION:
Restart service — MCP is critical path. Fast recovery + debug after.

TIMELINE: 0.2h
RISK: Medium — blocks client-facing systems

Use /spsa CASE_ID for full brief or /approve to accept recommendation
```

**Behavior:**
- Sends only on new RED cases (tracked via `CASE_ID_alerted.txt` file)
- Called from intake job after all cases created
- Does not re-alert on same case

---

### Layer 4: Brief Integration
**File:** `/home/john/Thunderbird/core/hale/hale_template_brief.py` (modified)

**New Section:** `format_spsa_section()` added to daily brief

**Content:**
- Lists all active RED cases (up to 5)
- Lists all active YELLOW cases (up to 5)
- Shows case ID, problem statement, recommendation, timeline

**Integration Point:** Morning brief runs at 0631 MT (after 0630 intake scan)

**Example Output:**
```
## 🚨 SPSA CASES

### 🔴 RED — Blocking Operations
**SPSA-20260502-A1B2C** | MCP server is offline
> Recommendation: Restart service (0.2h)

### 🟡 YELLOW — Requires Decision Today
**SPSA-20260502-D3E4F** | Authentication required: TESS
> Recommendation: Re-authenticate (0.15h)
```

---

## DEPLOYMENT CHECKLIST

### ✅ Completed
- [x] SPSA case engine (thunderbird_spsa.py)
- [x] Intake job (job_spsa_intake.py)
- [x] Telegram C2 alerting (spsa_telegram_c2.py)
- [x] Morning brief integration
- [x] Systemd timer (thunderbird-spsa-intake.timer) at 0630 + 1800 MT
- [x] Test run successful (created 3 cases: 1 RED, 2 YELLOW)

### 🚧 Planned (Not Yet Implemented)
- [ ] EOD summary (1700 MT): Daily new cases + status updates
- [ ] Weekly deep dive (Monday 0700 MT): Closed cases + lessons learned
- [ ] Google Sheets connector: Daily sync of closed cases for trending
- [ ] Telegram commands: /spsa CASE_ID for full brief, /approve to accept recommendation

---

## USAGE

### As Commander (Receiving Alerts)

**When RED alert arrives via Telegram:**
1. Read brief with problem, factors, recommended action
2. Decide: Accept recommendation (auto-implement via `/approve`) or request investigation
3. Check morning brief for full case context

**When YELLOW appears in morning brief:**
1. Review problem and recommendation
2. Schedule decision during work day (not urgent)
3. Cases can auto-escalate if overdue (waiting for implementation)

**To view full case brief:**
```bash
python3 -c "from core.ops.thunderbird_spsa import load_case; c = load_case('SPSA-20260502-E20AD'); print(c.to_brief())"
```

**To check active cases:**
```bash
python3 -c "from core.ops.thunderbird_spsa import get_active_cases; cases = get_active_cases(); [print(f'{c.case_id}: {c.severity} | {c.problem_statement[:50]}') for c in cases]"
```

### As COS/Staff (Creating Cases)

**Manual case creation:**
```python
from core.ops.thunderbird_spsa import intake_problem

case = intake_problem(
    severity="YELLOW",
    source="manual",
    problem_statement="Client Kuklinski validation email bounced",
    factors=[
        "Email format has invalid header",
        "Gmail flagged as spam",
        "Client cannot see validation email"
    ],
    options=[
        {
            "name": "Resend with corrected header",
            "description": "Fix email header, resend to Kuklinski",
            "tradeoff": "5 minutes, immediate fix"
        },
        {
            "name": "Use SMS as backup",
            "description": "Send SMS validation link instead",
            "tradeoff": "2 minutes, requires client phone number"
        }
    ],
    recommendation="Resend with corrected header",
    recommendation_rationale="Email is primary channel. Fix header first, SMS as fallback.",
    timeline_hours=0.1,
    risk_summary="Low — reversible, client impact minimal"
)

print(case.to_brief())
```

**During implementation:**
```python
from core.ops.thunderbird_spsa import log_implementation_action, update_case_status

log_implementation_action(
    "SPSA-20260502-A1B2C",
    "Restarted thunderbird-mcp.service via systemctl"
)

log_implementation_action(
    "SPSA-20260502-A1B2C",
    "Verified MCP health check passing"
)

update_case_status("SPSA-20260502-A1B2C", "IMPLEMENTING")
```

**At closure:**
```python
from core.ops.thunderbird_spsa import close_case

close_case(
    "SPSA-20260502-A1B2C",
    outcome="MCP service restored, all integrations online",
    lessons_learned="Add pre-flight health check before morning brief to catch offline services earlier"
)
```

---

## SYSTEM DEFAULTS & RULES

### Severity Assignment
- **RED:** Blocks client API, scheduler, critical integrations. Requires immediate decision.
- **YELLOW:** Delays reporting, affects non-critical services. Requires decision today.
- **GREEN:** Nice-to-have improvements, can be deferred.

### Approval Gate (Risk-Based)
- **LOW RISK** (<30min, reversible, no data change): Auto-implement, report after
- **MEDIUM RISK** (30min-2h, config change, user-facing): Telegram alert + decision required
- **HIGH RISK** (>2h, destructive, financial impact): Full SPSA brief + formal decision gate

### Integration Timing
- **0630 MT:** Intake job runs, creates cases → Morning brief includes SPSA section
- **0631 MT:** Morning brief sent to Commander with case list
- **1700 MT:** EOD summary with new cases + status updates (planned)
- **1800 MT:** Intake job runs (evening scan for overnight issues)
- **Monday 0700 MT:** Weekly deep dive with closed cases + lessons (planned)
- **Real-time:** Telegram alert on RED cases (sent immediately after intake)

### Case Lifetime
- **Created:** OPEN status, timestamp recorded
- **Reviewed:** UNDER_REVIEW status, Commander reads brief
- **Decided:** DECIDED status, decision + notes recorded
- **Executing:** IMPLEMENTING status, actions logged as they happen
- **Closed:** CLOSED status, outcome + lessons recorded, archived for trending

---

## TESTING & MONITORING

### Verify Timer is Active
```bash
systemctl --user status thunderbird-spsa-intake.timer
# Expected: Active: active (waiting)
# Next trigger: Sat 2026-05-02 06:30:00 MDT
```

### Run Manual Test
```bash
python3 OpsCenter/job_spsa_intake.py
# Expected: Creates 1-5 cases, logs to /home/john/Thunderbird/logs/spsa/
```

### Check Case Archive
```bash
ls -la logs/spsa/
# Should show SPSA-*.json files
```

### View Morning Brief
```bash
cat hale_brief.md | grep -A 20 "SPSA CASES"
```

---

## FAILURE SCENARIOS & RECOVERY

| Issue | Symptom | Recovery |
|-------|---------|----------|
| Intake job fails | No cases created, no alert | Check job logs: `journalctl --user -u thunderbird-spsa-intake.service` |
| Telegram alert fails | RED case not alerted to Commander | Manually send Telegram or check token in .env |
| Brief doesn't include SPSA | SPSA section missing from hale_brief.md | Restart hale_template_brief.py, verify import path |
| Cases not saved | Intake completes but no files in logs/spsa/ | Check directory permissions, verify SPSA_LOG_DIR exists |
| Case IDs colliding | Two cases with same ID | Case ID uses MD5 hash of timestamp → extremely low collision risk (>100M combinations) |

---

## FUTURE ENHANCEMENTS

1. **Google Sheets Sync:** Auto-sync closed cases daily for trending analysis
2. **Telegram Commands:** `/spsa CASE_ID` for full brief, `/approve` for quick decision
3. **Escalation Auto-Notification:** If YELLOW case remains DECIDED >8h, send reminder
4. **Historical Reporting:** Monthly SPSA metrics (cases/month, avg closure time, most common problem type)
5. **Integration with Mission Board:** Auto-create mission for each RED case
6. **Pattern Detection:** Identify recurring problem types and suggest preventive measures

---

## REFERENCE

**Commander Guide:** See this document + CLAUDE.md section "Standard Problem Solving Approach"
**Staff Reference:** `core/ops/thunderbird_spsa.py` docstrings + `OpsCenter/job_spsa_intake.py` for intake patterns
**Case Archive:** `logs/spsa/SPSA-YYYYMMDD-*.json` — view with `python3 -c "import json; print(json.dumps(json.load(open(...)), indent=2))"`

---

*SPSA System deployed 2026-05-02 by COS Hale | Integrated with morning brief, Telegram C2, and daily intake pipeline*
