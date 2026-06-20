# STANDING ORDER — CRITICAL INFRASTRUCTURE (CI) RAZOR-SHARP DOCTRINE
## Dreams2Memories Travel, LLC · Thunderbird Wing · Effective 2026-06-20
*Author: V. Hale, VCS (with Sterling A7). Commander directive 2026-06-20.*

---

## ⚠️ ZERO-WORKAROUND STANDARD (the spine — Commander: "status quo of numerous fails and workarounds is unacceptable")

A standing workaround on a CI skill is **not a solution — it is an unreplaced failing tool**, and it is the failure state this doctrine exists to end. **The standard is zero standing CI workarounds.**

1. Any workaround applied to a CI skill MUST be recorded in that registry entry as `active_workaround: {desc, since, burn_down_by}`. An undocumented workaround is a policy violation.
2. An active workaround **counts as a failure every sweep** until removed — it feeds the replacement triggers, so a chronic workaround auto-forces a REPLACE.
3. **Whetstone owns burn-down** — root-cause fix or tool replacement. Never institutionalize the workaround.
4. Goal metric: `active_workarounds == 0`, shown on the CI dashboard. Spot-it-fix-it: kill the root cause, don't surface-and-live-with-it.

---

## DESIGNATION

**Critical Infrastructure = capabilities whose failure stops the Wing from operating.** v1 CI skills (each with a paired CI tool):

| CI Skill | Paired CI Tool |
|---|---|
| portal-access | Camoufox + **setup-browser-cookies** (Commander's authenticated session / real residential IP) + throttle-from-request-1 (≥3s) — **$0, no proxy** (spend gate CLOSED 2026-06-20: Imperva block was self-inflicted rate-limiting, not IP reputation) |
| web-fetch | Trafilatura (clean-extract) + Anansi (fetch/SPA) |
| headless-dispatch | `core/ai_infra/thunderbird_headless_spawn.py` (claude -p / MAX) |
| credential-keepalive | `scripts/keepalive_supervisor.py` |
| tech-adoption | `core/intel/thunderbird_incubator.py` + `wind_staff.py` |

## THE POLICY IS THE REGISTRY

`config/ci_registry.json` is the source of truth **and** the policy. Each entry carries: `health_probe`, `currency_window_hours`, `reeval_cadence_days`, `latency_sla_ms`, `fallback`, `active_workaround`, `keeper`, and the owner fields. Do not restate per-skill values here — they live in the registry.

**RAZOR_SHARP** iff probe == GREEN **and** `age(last_verified) < currency_window_hours` **and** `age(last_reeval) < reeval_cadence_days`. Otherwise **DULL** (refresh it) or **RED** (down now). Computed by `core/ci/registry.py`.

## REPLACEMENT CRITERIA (Commander: "fail XXX times / undue delay → replace")

A CI tool → **REPLACE** when ANY trigger fires (`core/ci/replacement.py`, thresholds in `replacement_policy`):

| Trigger | Threshold |
|---|---|
| Consecutive failures | ≥ 3 in a row |
| Rolling failure rate | ≥ 5 failures in 7 days |
| Undue delay (sustained) | run > `latency_sla_ms` on ≥ 3 of last 5 runs |
| Undue delay (spike) | any single run > 3× `latency_sla_ms` |
| Hung tool | probe timeout ≥ 2 consecutive |
| Standing workaround | counts as a failure each sweep (feeds the above) |

REPLACE is more severe than DULL/RED: RED = down now (may recover); DULL = currency overdue (refresh); **REPLACE = chronic — swap the tool.**

## CADENCE & PAGING

`scripts/ci_sweep.py` runs daily (systemd `ci-sweep.timer`). DULL/RED/REPLACE pages **Whetstone (A14)**. If a client-affecting CI skill (portal-access, credential-keepalive) is RED or REPLACE → escalate to Commander. Dashboard: `output/CI_DASHBOARD.md`.

## OWNERSHIP

| Function | Owner |
|---|---|
| Discovery / ID (what to adopt, what to kill) | ELON (A12) |
| Access-intel (how to get in, bot-walls, proxy) | Dembe (A2) |
| Gate (complexity, cost, metrics, SLA) | Sterling (A7) |
| Currency / updating / integration / burn-down | **Whetstone (A14)** |

## ⚠️ HALE CI EXECUTION AUTHORITY (Commander directive 2026-06-20)

Hale has standing authority to **immediately direct a CI refresh, revision, replacement, or implementation** — no Commander gate, no notify-and-wait. Intent: keep D2M on the cutting edge without the Commander as a bottleneck. When a CI skill goes DULL/RED/REPLACE, Hale directs the fix on the spot (Whetstone executes, ELON nominates the swap, Sterling gates post-hoc). **The ONLY thing that still reaches the Commander is a financial commitment** — Hale selects and implements; the Commander signs the dollar. Free/self-host CI changes = Hale executes immediately, reports after. Client-send gate unaffected.

## ADDING A CI SKILL

ELON nominates → Sterling gates → Whetstone adds the registry entry (probe + windows + SLA + fallback) → first sweep verifies. Scouting (ELON/Dembe) runs unfiltered; the gate is on the build/adoption, not on the scouting.

---
*Canonical: this SO + `config/ci_registry.json`. Engines: `core/ci/`. CLI: `scripts/ci_sweep.py`.*
