# A7 STERLING — THUNDERBIRD WING METRICS DASHBOARD
**Iteration: 1 (Baseline)  |  Generated: 2026-05-16 12:48 MT  |  Owner: A7 Brig Gen (Ret.) Thomas "Gauge" Sterling**

> "What doesn't get measured does not get improved."
> Data source: `~/.local/share/opencode/opencode.db` (live query)  |  Window: last 7 days unless noted.
> Next scheduled update: Sunday 2026-05-18 18:00 MT.  |  Cadence: Weekly.

---

## OVERALL WING HEALTH

| Metric | Status | Value | Threshold | Action Required |
|--------|--------|-------|-----------|-----------------|
| Model Discipline (24h) | RED | 5 violations, $5.32 billed | $0 banned, $0.10 OR cap | Immediate — see Section 1 |
| Model Discipline (7d) | RED | $15.93 total spend | $0.50/wk tolerance | Immediate — see Section 1 |
| Banned Models Active (7d) | RED | 2 models active | 0 permitted | Immediate — see Section 1 |
| High-Variant Surcharge (7d) | RED | $12.16 (Triggers 1+2) | $0 | Immediate — see Section 1 |
| WF-17 Pipeline Gate | PENDING | — | — | Awaiting data source |
| Telegram Response Time | PENDING | — | — | Awaiting data source |
| Pre-Commit Hook Pass Rate | YELLOW | hook deployed; baseline TBD | >= 95% | Establish baseline this week |
| Wing Cost vs Budget (7d) | RED | $15.93 vs $0.50 tolerance | $0.50/wk | 31x over approved band |

**Rationale for RED:** Two banned models were active in the last 7 days, one free-base model ran variant=high
incurring $3.74 reasoning surcharge in a single session, and `google/gemini-3.1-flash-lite-preview`
(banned) accumulated $10.75 across 30 sessions. The approved model stack is $0/week native plus a
flat-fee Gemini 2.5 Flash. There is no approved path to $15.93/week.

---

## SECTION 1 — MODEL SLA (OpenCode Session Audit)

### 1A. 7-Day Model Usage Summary

Data source: `opencode.db` — sessions in rolling 7-day window (2026-05-09 to 2026-05-16).

| Model | Provider | Variant | 7d Cost | Sessions | Avg Tok/In | Status |
|-------|----------|---------|---------|----------|------------|--------|
| google/gemini-3.1-flash-lite-preview | openrouter | high | $8.4165 | 4 | 8,509,364 | **RED — BANNED + High variant** |
| deepseek-v4-flash-free | opencode | high | $3.7424 | 1 | 16,067,231 | **RED — Free-base[high] surcharge** |
| google/gemini-3.1-flash-lite-preview | openrouter | default | $2.2475 | 25 | 226,854 | **RED — BANNED** |
| deepseek/deepseek-chat-v3.1 | openrouter | default | $1.4375 | 10 | 694,452 | **RED — BANNED** |
| google/gemini-3.1-flash-lite-preview | openrouter | unknown | $0.0870 | 1 | 195,612 | **RED — BANNED** |
| gpt-5 | openai | default | $0.0000 | 1 | 0 | YELLOW — unapproved, no cost |
| gemini/gemini-3.1-flash-lite | openrouter | default | $0.0000 | 1 | 0 | YELLOW — unapproved, no cost |
| big-pickle | opencode | default | $0.0000 | 1 | 22,987 | **GREEN — approved** |

**7-Day Total: $15.9309 across 44 sessions**

### 1B. Cost vs Budget

| Budget Line | Target | Actual (7d) | Variance | Status |
|-------------|--------|-------------|----------|--------|
| Native OpenCode (big-pickle) | $0.00 | $0.00 | $0.00 | GREEN |
| OpenCode free-base (deepseek-v4-flash-free, variant=default) | $0.00 | $0.00 | $0.00 | GREEN |
| Google Gemini 2.5 Flash (flat-fee approved) | flat | $0.00 | — | GREEN (not used) |
| OpenRouter free-tier (nemotron:free) | $0.00 | $0.00 | — | GREEN (not used) |
| **Weekly spend tolerance (all models)** | **$0.50** | **$15.93** | **+$15.43** | **RED — 31x over** |
| **Banned model spend** | **$0.00** | **$12.16** | **+$12.16** | **RED** |
| **High-variant surcharge** | **$0.00** | **$3.74** | **+$3.74** | **RED** |

> **Budget baseline definition (A7 established this iteration):** Approved stack = $0/week native +
> flat-fee Gemini 2.5 Flash. Weekly tolerance for incidental probes or fallback usage: $0.50.
> Anything above $0.50/week requires Commander review. This threshold is permanent and will be
> measured against weekly henceforth. Owner: A7 Sterling. Review cadence: weekly.

### 1C. Banned Model Detections (7d)

| Model | Provider | Sessions | 7d Cost | 7d Tokens In | First Detected |
|-------|----------|----------|---------|--------------|----------------|
| google/gemini-3.1-flash-lite-preview | openrouter | 30 | $10.7510 | 34,904,441 | This audit window |
| deepseek/deepseek-chat-v3.1 | openrouter | 10 | $1.4375 | 6,944,520 | This audit window |

**Banned model spend 7d: $12.1885**

These models were identified in prior cost audits and added to `BANNED_PAID` in
`OpsCenter/harlan_cost_monitor.py`. The gate script `OpsCenter/a7_model_audit_gate.py`
now enforces this list. Both models were running in OpenCode sessions — likely as
fallback or override routing. Root cause investigation: who or what process is
setting `model = google/gemini-3.1-flash-lite-preview` in OpenCode config?

Immediate action item: audit `.opencode.json` fallback order. `google/gemini-2.5-flash`
(approved flat-fee) is the intended fallback when `opencode/big-pickle` is unavailable,
not `gemini-3.1-flash-lite-preview`.

### 1D. High-Variant Surcharge Events (7d)

| Model | Variant | Sessions | Surcharge | Input Tokens | Notes |
|-------|---------|----------|-----------|--------------|-------|
| google/gemini-3.1-flash-lite-preview | high | 4 | $8.4165 | 34,037,456 | Also banned — dual violation |
| deepseek-v4-flash-free | high | 1 | $3.7424 | 16,067,231 | Free-base model + high variant |
| google/gemini-3.1-flash-lite-preview | high (24h) | 1 | $0.2483 | 839,093 | Within 24h window |

**Fix:** `variant=high` must only be set when a task explicitly requires deep reasoning
(e.g., complex multi-hop analysis). Routine ops, email drafts, intel sweeps =
`variant=default`. This should be enforced at the OpenCode task runner level, not
left to per-session override. Owner: A7 Sterling to raise with COS as process change.

### 1E. Compliant Model Activity (7d)

| Model | Provider | Sessions | Cost | Notes |
|-------|----------|----------|------|-------|
| big-pickle | opencode | 1 | $0.00 | Only 1 session — underutilized |

**Finding:** The approved primary model (`opencode/big-pickle`) was used in only 1 of
44 sessions this week (2.3% utilization). The wing is overwhelmingly routing to
unapproved and banned models. This is the root failure: the approved routing is not
being followed. Fix the routing configuration, not individual sessions.

---

## SECTION 2 — WF-17 PIPELINE (Client Email Quality Gate)

| Metric | Status | Notes |
|--------|--------|-------|
| Draft-to-send cycle time (WF-17) | PENDING DATA SOURCE | No timestamp log connected yet |
| Client email gate compliance | PENDING DATA SOURCE | No gate log file identified yet |
| Two-lane pipeline violations (pre-commit) | Measured by a7_pre_commit_gate.py | Baseline: 0 violations in hook install run |
| Stationery apply-at-publish compliance | PENDING DATA SOURCE | Grep audit of recent commits recommended |

**Data source gap:** WF-17 cycle time requires timestamp logging from
`core/email/thunderbird_gmail.py` at draft creation and at publish. The
`logs/publish_audit.log` file is the designated audit log (per SO 07 MAY 2026).
**Action item:** A7 to pull `logs/publish_audit.log` next iteration and establish
draft-to-send latency baseline. Owner: A7 Sterling. Target: populated by Week 2.

---

## SECTION 3 — CHAIN EFFICIENCY (Provider-Level Cost/Session Ratio)

Data source: `opencode.db` — 7-day window.

| Provider | Sessions | Total Cost | Cost/Session | Efficiency Rating |
|----------|----------|------------|--------------|-------------------|
| opencode (native) | 2 | $3.74 | $1.87/sess | RED — variant=high surcharge |
| openrouter | 37 | $12.19 | $0.33/sess | RED — banned models + high variant |
| openai | 1 | $0.00 | $0.00/sess | YELLOW — unapproved, zero cost |
| **Target (approved stack)** | — | **$0.00** | **$0.00/sess** | GREEN |

**Efficiency finding:** The approved model stack achieves $0/session. The wing is
averaging $0.36/session across all providers this week — an infinite-percent deviation
from the $0 target. Every dollar above $0 is waste preventable by correct routing.

**Chain efficiency formula (for future iterations):**
- Efficiency Score = (sessions on approved models) / (total sessions) * 100
- This week: 2 / 44 = **4.5%** — CRITICAL. Target: >= 95%.

---

## SECTION 4 — TELEGRAM RESPONSE TIME

| Metric | Status | Notes |
|--------|--------|-------|
| Commander message to first response | PENDING DATA SOURCE | No log capture implemented |
| Bot uptime (D2MC2C) | LIVE (per hale_state.json) | bot_id: 8754681793 |
| Bot uptime (Dani) | LIVE (per hale_state.json) | bot_id: 8726363494 |
| SLA target | < 2 minutes | Per Hale Agent Tasking Architecture |

**Data source gap:** Telegram response latency requires message-received and
message-sent timestamps from `core/communication/thunderbird_telegram_c2.py`.
**Action item:** Instrument incoming message handler with timestamp logging to
`logs/telegram_response.log`. Owner: A7 Sterling. Target: populated by Week 3.

---

## SECTION 5 — WING FINANCIAL PULSE (from hale_state.json)

Source: `hale_state.json` financial_pulse node — last pulled 2026-05-16 06:45 MT.

| Metric | Value | Status |
|--------|-------|--------|
| D2M pipeline (upcoming voyages) | $21,440.75 (23 voyages) | GREEN |
| Commission expected (35 bookings) | $35,214.47 | GREEN |
| D2M share total | $27,146.41 | GREEN |
| TESS received (checks) | $244.80 | GREEN |
| Due now | $0.00 | GREEN |
| TESS auth status | ONLINE | GREEN |

**Note:** Commission audit function transferred to A9 Harlan per 2026-05-13 transformation.
Hale receives result only. A7 reads these numbers from state file — does not independently
audit commission data. If numbers conflict with Harlan's brief, surface discrepancy.

---

## SECTION 6 — SYSTEM HEALTH (from hale_state.json)

Source: `hale_state.json` wing_health node — last checked 2026-05-16 12:42 MT.

| System | Status | Notes |
|--------|--------|-------|
| MCP Server (port 8765) | ONLINE | GREEN |
| Telegram D2MC2C bot | LIVE | GREEN |
| Telegram Dani bot | LIVE | GREEN |
| OpenCode (Big Pickle) | RUNNING | YELLOW — SPSA discrepancy noted in brief |
| Claude Headless | READY (Max OAuth) | GREEN |
| Chrome Debug Port 9222 | OFFLINE | YELLOW — not monitored |
| TESS Auth | ONLINE | GREEN |
| OAuth Cache | LIVE | GREEN |

---

## SECTION 7 — PRE-COMMIT HOOK STATUS

| Check | Hook File | Status | Last Run |
|-------|-----------|--------|----------|
| Staged-file compliance gate | a7_pre_commit_gate.py | Deployed | Session open |
| Model audit gate (new) | a7_model_audit_gate.py | Deployed 2026-05-16 | 2026-05-16 12:48 MT |
| Spawn whitelist enforcement | a7_pre_commit_gate.py | Active | Per commit |
| Two-lane pipeline guard | a7_pre_commit_gate.py | Active | Per commit |
| Duplicate script detector | a7_pre_commit_gate.py | Active | Per commit |

**Pre-commit pass rate:** Baseline being established this iteration. First full-week
measurement target: 2026-05-23 dashboard. Threshold: >= 95% pass rate.
Metric owner: A7 Sterling. Measurement method: grep `exit 1` in hook execution logs.

---

## SECTION 8 — COMPOUNDING RULES ACTIVATED THIS ITERATION

Per A7 charter: every finding becomes a permanent rule in the appropriate hook or daemon.

| Finding | Rule Activated | Where Enforced | Effective |
|---------|---------------|----------------|-----------|
| Banned models active (gemini-3.1-flash-lite-preview, deepseek-chat-v3.1) | Added to BANNED_MODELS in a7_model_audit_gate.py | Pre-commit model gate | 2026-05-16 |
| Free-base[high] reasoning surcharge | Trigger 2: variant=high on free-base = RED | Pre-commit model gate | 2026-05-16 |
| OpenRouter paid drift | Trigger 1: OR cost > $0.10/24h = RED | Pre-commit model gate | 2026-05-16 |
| Weekly budget $0.50 tolerance | Permanent threshold in dashboard | Weekly dashboard | 2026-05-16 |
| big-pickle utilization only 4.5% | Routing investigation flagged to COS | hale_decisions.md action item | 2026-05-16 |

---

## FINDINGS SUMMARY — ITEMS REQUIRING ACTION

Every finding below has a metric, a threshold, and an owner. No finding closes without all three.

| # | Finding | Metric | Threshold | Owner | Deadline |
|---|---------|--------|-----------|-------|----------|
| 1 | Banned models active (gemini-3.1-flash-lite-preview, deepseek-chat-v3.1) | $0 banned model spend/week | $0.00 | COS to fix OpenCode routing | 2026-05-18 |
| 2 | Free-base model variant=high surcharge ($3.74 single session) | variant=high usage on free-base | 0 events/week | COS / task runner config | 2026-05-18 |
| 3 | big-pickle utilization 4.5% (should be primary model) | pct sessions on approved models | >= 95% | COS to audit .opencode.json | 2026-05-18 |
| 4 | WF-17 cycle time data gap | draft-to-send latency (minutes) | < 30 min | A7 Sterling — instrument publish_audit.log | 2026-05-23 |
| 5 | Telegram response time data gap | msg-received to msg-sent latency | < 2 min | A7 Sterling — instrument telegram_c2.py | 2026-05-30 |
| 6 | Pre-commit pass rate baseline | pct commits passing gate | >= 95% | A7 Sterling — collect over first full week | 2026-05-23 |

---

*A7 Brig Gen (Ret.) Thomas "Gauge" Sterling | Thunderbird Wing, D2M*
*Iteration 1 — Baseline | 2026-05-16 | Next: Sunday 2026-05-18 18:00 MT*
*Data sources: opencode.db (live), hale_state.json (snapshot 06:45 MT), harlan_cost_monitor.py (schema reference)*
