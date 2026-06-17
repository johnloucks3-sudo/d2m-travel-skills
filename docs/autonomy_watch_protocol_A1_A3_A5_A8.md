# AUTONOMY WATCH PROTOCOL — A1 / A3 / A5 / A8
## MISSION-167 · 14-Day Standing Watch
**Owner:** A7 Sterling | **Reviewer:** COS Hale | **Escalation Authority:** Commander  
**Established:** 2026-06-17 | **First Sterling manual audit:** 2026-06-20 (Day 3) | **Watch closes:** 2026-07-01  
**Check script:** `scripts/autonomy_health_check.py`

---

## SCOPE CLARIFICATION

**Prior execution note (2026-06-10):** A prior auto-execution claimed MISSION-167 complete against a different
script set (Brief Compression, FPD Sentinel, Session Continuity, WF-17 deep-link). That output is preserved at
`output/executor_results/MISSION-167_20260610.md` but does NOT satisfy the mission as chartered. The four
scripts named in that doc (morning_brief_engine.py, fpd_sentinel.py, session_open_brief.py, thunderbird_gmail.py)
remain production-healthy per that run. This document governs the persona autonomy layer:
the scripts that generate and dispatch client-facing content on behalf of A1/A3/A5/A8.

---

## WATCHED SCRIPTS — PERSONA MAP

| Persona | Role | Primary Autonomy Scripts | Run Cadence |
|---------|------|-------------------------|-------------|
| **A1 Navarro** | Client profiles, CRM, dossier intake | `core/booking/thunderbird_dossier_scanner.py`, `core/client/thunderbird_auto_enrich.py` | On-demand / MCP-invoked |
| **A3 Dani** | Client email, lifecycle delivery | `core/lifecycle/lifecycle_scheduler.py`, `scripts/dani_voice_draft.py`, `core/email/thunderbird_dani_engine.py` | Daily 06:00 MT (scheduler), on-demand (voice_draft) |
| **A5 Castillo** | Strategy, business planning | `OpsCenter/wind_staff.py` (castillo persona), invoked via `opencode_headless_claude_dispatch.py` | On-demand only — NO standing daemon |
| **A8 Reyes** | Dossier readiness, FPD, TP tracking | `core/booking/thunderbird_tp_scheduler.py`, `core/booking/thunderbird_dossier_scanner.py`, `scripts/fpd_sentinel.py` | Daily 06:00 MT via morning_brief_engine.py |

**A5 Castillo status:** No standing daemon. Castillo runs only when explicitly invoked via wind_staff.py or
headless dispatch. Monitoring is limited to invocation logs in `logs/opencode_wind_staff_castillo_*.log`.
Runaway loop risk for A5 is LOW (no scheduler, no cron). Monitor confirms: no phantom invocations.

---

## MONITORING CRITERIA — FOUR SIGNALS

### Signal 1: Error Rate (QUANTITATIVE)

Threshold: **Any error > 0 in the most recent run = YELLOW. Persistent errors (3+ consecutive runs) = RED.**

| Script | Log File | Error Signal | Baseline (verified 2026-06-17) |
|--------|----------|--------------|-------------------------------|
| lifecycle_scheduler.py | `logs/lifecycle_scheduler.log` | `ERROR` loglines; `"errors": []` key in scheduler_complete events | 0 errors in 82 logged runs |
| dani_voice_draft.py | `logs/dani_voice_draft.log` | `DANI-VOICE ERROR` loglines; `status=voice_error` in queue | 29 voice_error entries (all `[FILL_CLIENT_EMAIL]` placeholder — known, non-client emails) |
| thunderbird_dossier_scanner.py | `OpsCenter/logs/dossier_freshness.jsonl` | `stale_count > 0` or scanner exception | 0 stale entries (last run 2026-06-14) |
| thunderbird_tp_scheduler.py | `logs/lifecycle_scheduler.log` | OVERDUE_ALERT entries with no dedup skip | 3 stale TPs (kuklinski TP_3, lyons TP_0.5/TP_1 — pre-watch, known) |
| fpd_sentinel.py | `OpsCenter/state/fpd_state.json` | JSON parse failure; unexpected `OVERDUE` states | Valid JSON, 5 clients, no OVERDUE flags |

**Known condition — voice_error (29 entries, all 2026-05-30):** All 29 errors are `gmail_update_failed`
caused by `[FILL_CLIENT_EMAIL]` placeholder in the draft queue. This is a DATA gap (client email not
populated), not a script bug. These are pre-watch entries. Monitor watches for NEW voice_errors (ts >= watch start date).

### Signal 2: Runaway Loop Detection (QUANTITATIVE)

Runaway pattern: same TP fires multiple times on same day without `"Already fired"` dedup suppression,
or scheduler runs > 5 times/day, or drafts_created spikes unexpectedly.

| Signal | Threshold | How to Detect |
|--------|-----------|---------------|
| Scheduler runs/day | YELLOW: > 4 runs/day. RED: > 8 runs/day | Count `D2M Lifecycle Scheduler` lines per day in lifecycle_scheduler.log |
| Same TP fires without dedup | RED immediately | `"Already fired"` must appear on repeat TP entries; if same TP fires without the prefix, dedup is broken |
| drafts_created per run | YELLOW: > 5 drafts in one run (unusual). RED: any draft created for a client whose dossier has `contact_hold=true` | Grep scheduler_complete events in lifecycle_audit.jsonl |
| wind_staff.py invocations (A5) | RED: any invocation not logged in a claude_outbox or opencode dispatch record | Cross-check logs/opencode_wind_staff_castillo_*.log against router_log or wind_comms.md |

**Baseline (verified 2026-06-17):** 82 runs over the scheduler's life = ~3 runs/day average on active days.
Peak observed: 3 runs on 2026-06-16. drafts_created = 0 in last 48 hrs. Dedup working correctly.

### Signal 3: Off-Lane / WF-17 Gate Breach (RED ALARM — Commander immediate notification)

This is the highest-priority signal. lifecycle_scheduler.py's docstring states: "NEVER auto-sends — all
drafts require Commander approval (WF-17 gate)." The monitor empirically verifies this claim.

| Check | Alarm Level | Detection Method |
|-------|-------------|-----------------|
| Client-address email sent without Commander approval | RED — Commander immediate | Look for `gmail_send` calls in logs; `voice_drafted` status in queue should NEVER have a matching Gmail SENT item unless Commander explicitly sent it. Script generates drafts only; any send is a violation. |
| Draft created with non-placeholder client email but no `THUNDERBIRD-Commander-Review` label | RED — COS within 1 hour | Grep queue for `voice_drafted` + `client_email` without placeholder; verify label presence (manual check, not scriptable without OAuth) |
| A1 Navarro (auto_enrich.py) writes to dossier without a prior scan confirming data quality | YELLOW — Sterling weekly | Confirm enrich cache TTL (4 hours, hardcoded) has not been reduced below 4 hours; check `cache/client_context/` for stale entries |
| A5 Castillo invocation with PII in prompt | RED — COS within 1 hour | `wind_staff.py` prompts go through `opencode_headless_claude_dispatch.py` which has PII fence; confirm dispatch log shows no client last names or booking refs in outbound task records |

**WF-17 empirical verification:** `lifecycle_scheduler.py` calls `gmail_create_draft_sync()`, NOT any send
function. The queue file shows `voice_drafted` entries, not `sent` entries. Email send functions
(`gmail_send_email`, `send_client_email`) are absent from the lifecycle scheduler codebase. Verified clean.

### Signal 4: Output Quality (QUALITATIVE — Sterling human pass; no reliable script proxy)

Output quality cannot be fully mechanized without reading the email content. The script provides a proxy signal only.

**Proxy signals (scriptable):**
- Draft length < 200 characters = placeholder or truncated output (flag as YELLOW)
- `[FILL_` tokens present in a voice_drafted entry = incomplete template (flag as YELLOW)
- TP label mismatch (tp_id in queue does not match expected phase label for that client) = logic error (flag as YELLOW)

**Human review (Sterling — weekly Sunday 18:00 MT Baldrige sweep):**
- Pull 2 random `voice_drafted` entries from the queue, open the Gmail draft, read for:
  - Confirmed facts only (no INFERRED claims per Pipeline Integrity Rule 1)
  - Client name correct, no cross-client contamination
  - Tone consistent with Dani voice card (`d2m_brand_voice.json`)
  - No dollar amounts without a source trace (Pipeline Integrity Rule 4)

---

## 14-DAY CADENCE

**Watch window:** 2026-06-17 through 2026-07-01.

| Cadence | Action | Owner | Output |
|---------|--------|-------|--------|
| **Daily** (automated) | Run `scripts/autonomy_health_check.py` — reads logs/queues, emits PASS/FAIL per persona | Sterling or Hale cron | Output to stdout; RED items route to `OpsCenter/a7_metrics_dashboard.json` |
| **Daily** (human) | Review check script output; act on any RED | Hale (COO disposition) | Note in `OpsCenter/00_COMMAND_LOG.md` if action taken |
| **Day 3 (2026-06-20)** | First Sterling manual quality pass | Sterling | Sample 2 voice_drafted entries; annotate pass/fail in `OpsCenter/00_COMMAND_LOG.md` |
| **Day 7 (2026-06-24)** | Mid-watch review — compare error rate to baseline | Sterling | Update `OpsCenter/a7_metrics_dashboard.json` precommit_pass_rate field |
| **Day 14 (2026-07-01)** | Watch closes. Sterling writes one-paragraph finding to COS | Sterling | Entry in `hale_decisions.md`; protocol promoted to Sunday Baldrige sweep or SOs updated |

---

## PASS/FAIL THRESHOLDS

| Metric | GREEN | YELLOW | RED |
|--------|-------|--------|-----|
| lifecycle_scheduler.py error rate | 0 errors/run | 1 error in isolation | 3+ errors or same error 2 runs in a row |
| dani_voice_draft error rate | 0 new errors (post 2026-06-17) | 1-2 new voice_errors | 3+ new voice_errors in a batch |
| Scheduler runs per day | 1-4 | 5 | >5 or >8 |
| drafts_created for contact_hold client | 0 | — | ANY |
| WF-17 gate breach (client email sent) | 0 | — | ANY — immediate Commander notify |
| Output quality (Sterling pass) | All claims confirmed, correct client | Minor tone drift | Facts from wrong client, PII exposure, unconfirmed dollar claims |
| A5 phantom invocation (no dispatch record) | 0 | — | ANY |
| dossier_freshness stale_count | 0 | 1-2 stale | 3+ stale or scanner exception |

---

## ESCALATION MATRIX

| Condition | Escalation Target | Response Window |
|-----------|------------------|-----------------|
| RED — WF-17 gate breach (any client send) | Commander directly, then COS | Immediate (no queue) |
| RED — Contact-hold draft created | COS Hale, then Commander if draft reaches Gmail | 1 hour |
| RED — PII in A5 dispatch prompt | COS Hale | 1 hour |
| RED — Persistent error (3+ runs) | COS Hale | 4 hours (within same day) |
| YELLOW — Any single isolated error | Sterling corrects + logs in OpsCenter/00_COMMAND_LOG.md | Same day |
| YELLOW — Output quality drift | Sterling flags in weekly Baldrige; Hale routes to Dani for retraining | 48 hours |
| GREEN — All clear | No action; note in daily audit run | — |

---

## COMPOUNDING RULE (A7 charter)

Any finding that fires during the 14-day watch becomes a permanent check in `scripts/autonomy_health_check.py`
and is logged in `OpsCenter/a7_metrics_dashboard.json` under `persona_performance_metrics`. Sterling owns the
delta — findings do not expire with the watch window.

After the 14-day window closes:
- If 0 RED events: protocol folds into the weekly Sunday Baldrige sweep (no new SO required).
- If any RED event: Sterling authors an SO within 7 days per anti-theater rule (SO 16 MAY 2026).
- Metric `lessons_implementation_rate_pct` must remain >= 80%.

---

## FILES UNDER WATCH — READ-ONLY

These scripts are watched but NOT modified by this protocol or the check script:

| File | Persona | Path |
|------|---------|------|
| lifecycle_scheduler.py | A3 Dani | `core/lifecycle/lifecycle_scheduler.py` |
| dani_voice_draft.py | A3 Dani | `scripts/dani_voice_draft.py` |
| thunderbird_dani_engine.py | A3 Dani | `core/email/thunderbird_dani_engine.py` |
| thunderbird_dossier_scanner.py | A1/A8 | `core/booking/thunderbird_dossier_scanner.py` |
| thunderbird_auto_enrich.py | A1 | `core/client/thunderbird_auto_enrich.py` |
| thunderbird_tp_scheduler.py | A8 | `core/booking/thunderbird_tp_scheduler.py` |
| fpd_sentinel.py | A8 | `scripts/fpd_sentinel.py` |
| wind_staff.py (castillo persona) | A5 | `OpsCenter/wind_staff.py` |
| opencode_headless_claude_dispatch.py | A5 (dispatch) | `OpsCenter/opencode_headless_claude_dispatch.py` |

The check script reads log files and JSON state files only. It does not import, exec, or modify any of
the above. Nor does it modify `mission_board.json` or any of the 6 protected email/relay files.
