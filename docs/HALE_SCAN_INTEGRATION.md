# Hale Proactive Scan — Integration & Operations Guide
## Status: ✅ LIVE (2026-04-12) · Phase 2 predictive intelligence added 2026-07-06

---

## Overview

The **Hale Proactive Scan** system automatically identifies operational risks and opportunities. It runs daily at **01:00 MDT** and appends findings to `hale_brief.md`, with HIGH priority items sent to Commander via Telegram.

---

## Architecture

### 1. **hale_proactive_scan.py** — Core Scanner
**Location:** `scripts/hale_proactive_scan.py`
**Output:** `hale_scan_results.json`

Runs 5-point scan:
- **Deadline Radar:** Upcoming FPD/EMB milestones (≤14 days)
- **Stale Tasks:** Missions inactive >48h
- **Staff Gaps:** Personnel idle ≥7 days
- **Data Consistency:** Memory/brief/state alignment
- **Conflict Detection:** Priority overload (>5 active missions)

Each finding tagged with priority: **HIGH** (≤7d / >3d idle / critical) or **MEDIUM**.

### 1b. **core/hale/predictive_intelligence.py** — Phase 2 Predictive Layer
**Added:** 2026-07-06 · **Output:** merged into `hale_scan_results.json["scans"]`

Runs 5 additional forward-looking scans, called from `hale_proactive_scan.py::main()`
via `run_all()`:

- **Vendor contract expirations** — reads `config/vendor_contracts.json` (mirrors
  Drive/`Thunderbird_Commercial_Ops` once a sync job populates it; empty today, so
  the scan correctly reports zero rather than fabricating a deadline).
- **Insurance policy renewals** — reads `config/insurance_policies.json` (mirrors
  Drive/`Thunderbird_Shield_Logistics`; same empty-registry-until-synced status).
- **Commission reconciliation cycle** — flags if no `commission_reconciliation_*.md`
  has been filed in `OpsCenter/state/` within `RECONCILIATION_GRACE_DAYS` (5) of the
  1st of the current month.
- **Client re-engagement windows** — parses `dossiers/*.md` for past embarkation
  dates per client, flags clients whose most recent completed voyage is ≥18 months
  (548 days) ago with no active follow-on mission on the board. Attaches a
  `cohort_signal`/`predicted_rebook_window` using the modal historical quarter
  across repeat-booking clients ("similar clients rebook in Q3" pattern).
- **Competitor intel freshness** — flags if the newest file matching `*competitor*`
  under `intel/` is older than `COMPETITOR_INTEL_STALE_DAYS` (7).

Every function takes injectable `now=`/path parameters for testability and returns
`[]` when its source has no data — see `tests/test_hale_predictive_intelligence.py`
(17 tests, including a synthetic 6-month cohort-history validation of the Q3
re-engagement prediction).

**Populating the two Drive-backed registries:** once `Thunderbird_Commercial_Ops`
and `Thunderbird_Shield_Logistics` are locally synced, append entries to the
`contracts`/`policies` arrays in the two config files above — the scan needs no
code change to pick them up.

### 2. **hale_scan_wirer.py** — Output Integrator
**Location:** `scripts/hale_scan_wirer.py`

Orchestrates:
1. Executes the proactive scan
2. Parses `hale_scan_results.json`
3. Formats findings into markdown sections
4. Updates `hale_brief.md` with new SCAN SUMMARY at top
5. Extracts HIGH priority items
6. Sends Telegram alert to Commander (if HIGH items exist)

### 3. **Systemd Timer & Service**
**Service:** `/etc/systemd/system/hale-daily-scan.service`
**Timer:** `/etc/systemd/system/hale-daily-scan.timer`

```
OnCalendar=*-*-* 01:00:00   # Daily at 01:00 MDT (= 07:00 UTC)
AccuracySec=30s
Persistent=true              # Catches up if system was down
```

---

## Output Format

### hale_brief.md Structure
```markdown
## SCAN SUMMARY
*Timestamp: 2026-04-12T22:21:27.777243*

### 📅 Deadline Radar
- **OVERDUE** | Lyons (FPD) | 33d out [**HIGH**]
- **UPCOMING** | Westbrook (Proposal Send) | 7d out [**HIGH**]

### ⏱️ Stale Tasks (>48h)
- MISSION-001: Finalize proposal (72h old) [**HIGH**]

### 👥 Staff Gaps (7+ days idle)
- A2 (Dembe): 14 days idle [**HIGH**]

### ⚖️ Data Consistency Issues
- Furlow payment status not reflected in brief [**MEDIUM**]

### ⚠️ Priority Conflicts
- 7 active missions may indicate priority overload [**MEDIUM**]

**Summary:** 5 total findings | **3 HIGH** | 2 MEDIUM

# Daily Hale Transformation Audit — 2026-04-12
...existing content preserved...
```

### Telegram Alert (HIGH Items Only)
```
🦅 **HALE PROACTIVE SCAN — HIGH PRIORITY ITEMS**

1. 📅 Lyons FPD in 33 days
2. 📅 Westbrook Proposal Send in 7 days
3. ⏱️ Stale task: Finalize proposal (72h old)

*See hale_brief.md for full SCAN SUMMARY*
```

---

## Operations

### Running Manually
```bash
# Full pipeline (scan + wire + brief update)
python3 /home/john/Thunderbird/scripts/hale_scan_wirer.py

# Scan only (produces hale_scan_results.json)
python3 /home/john/Thunderbird/scripts/hale_proactive_scan.py

# View results
cat hale_scan_results.json | jq '.'
```

### Timer Status
```bash
# Check next fire time
systemctl list-timers hale-daily-scan.timer

# Check recent executions
journalctl -u hale-daily-scan.service -n 50 --no-pager

# Manually trigger
systemctl start hale-daily-scan.service
```

### Enable/Disable
```bash
# Enable (will run at next 01:00 MDT)
systemctl enable hale-daily-scan.timer

# Disable
systemctl disable hale-daily-scan.timer

# Check status
systemctl is-enabled hale-daily-scan.timer
systemctl is-active hale-daily-scan.timer
```

---

## Test Results (2026-04-12)

### Test 1: Manual Execution
```
[wirer] Running proactive scan...
✅ Scan complete. Found 0 proactive items.
[wirer] Updated hale_brief.md with SCAN SUMMARY
[wirer] ✅ Scan wiring complete
HIGH priority: 0 | MEDIUM priority: 0
Status: ✅ PASS
```

### Test 2: Content Preservation
```
Before: hale_brief.md with audit content
After: SCAN SUMMARY prepended, original content preserved
Status: ✅ PASS
```

### Test 3: Systemd Integration
```
Last run: 2026-04-12 22:21:30 MDT
Next run: 2026-04-13 01:00:00 MDT (in ~2h 38m)
Journal: ✅ Service runs cleanly, zero errors
Status: ✅ PASS
```

---

## Threshold Tuning

Edit `scripts/hale_proactive_scan.py`:

| Scan | Threshold | HIGH Trigger | MEDIUM Trigger |
|------|-----------|--------------|-----------------|
| **Deadline Radar** | Line 95 | `days_out <= 7` | `days_out <= 14` |
| **Stale Tasks** | Line 122-130 | `age_hours > 72` | `age_hours > 48` |
| **Staff Gaps** | Line 152-159 | `days_idle > 14` | `days_idle >= 7` |
| **Data Consistency** | Line 181-199 | Manual (per-check) | Manual (per-check) |
| **Conflict Detection** | Line 209-222 | Manual (>5 missions) | Manual (>5 missions) |

Example: To make deadline radar trigger at 21 days instead of 14:
```python
# Line 91
if deadline["days_out"] <= 21:  # Changed from 14
    results.append({
        ...
        "priority": "HIGH" if deadline["days_out"] <= 7 else "MEDIUM",
    })
```

---

## Logging & Debugging

### Journal (Full Service Logs)
```bash
journalctl -u hale-daily-scan.service -f  # Follow output
journalctl -u hale-daily-scan.service --since "2 hours ago"
```

### JSON Results
```bash
cat /home/john/Thunderbird/hale_scan_results.json | jq '.scans'
```

### Scan Count by Type
```bash
jq '.scans | map_values(length)' /home/john/Thunderbird/hale_scan_results.json
```

---

## Known Limitations

1. **No Telegram on Manual Run:** Manual invocation updates `hale_brief.md` but does NOT send Telegram unless HIGH items exist. (Telegram gateway requires active session.)
2. **Dossier Parsing:** FPD/EMB detection uses regex; malformed dates will be skipped silently.
3. **5-Minute Initial Delay:** Timer fires at 01:00 MDT but systemd may add ≤30s accuracy window.
4. **No Backfill:** If system was down at 01:00 MDT, Persistent=true will fire on next boot (not backfill to 01:00).

---

## Next Steps

- Monitor first production runs (check journal daily)
- Adjust thresholds based on false positive rate
- Consider adding email backup if Telegram fails
- Document customizations in `hale_decisions.md`

**Hale Integration Status: ✅ LIVE — Ready for production**

---

*Last updated: 2026-04-12 22:35 MDT*
*System: hale-daily-scan.timer (enabled, next: 2026-04-13 01:00)*
