# STANDING ORDER — READINESS LADDER & "FRESH AND LETHAL" PROTOCOL
## Dreams2Memories Travel, LLC · Thunderbird Wing · Issued 2026-06-21 (Commander directive)

**Classification:** Strategic — doctrine. Issued directly by the Commander. Execution authority delegated to Hale + staff **without Commander approval** (see §3).

---

## WHY (Commander, 2026-06-21)
> "Remove initialization context bloat — ~90K forces me to use Opus because Sonnet has to compact too much. Continually search for tools we haven't used in a defined period and phase them out. You and your staff do that without my approval. Set a daily/weekly/monthly/quarterly protocol to keep the Thunderbird stack fresh and lethal."

Two problems, one cure: the stack accumulates (context AND tools) and never sheds. Bloat forces a more expensive model; dead tools rot silently ([[feedback_silent_sensor_efficacy_monitoring]], MISSION-324). The fix is a graduated demotion ladder run on a fixed clock.

---

## §1. THE READINESS LADDER (applies to BOTH auto-load context AND tools/code/services)
A force-structure model. Everything starts at the lowest readiness that still does its job; demote on disuse, recall on need.

| Tier | Context meaning | Tool/service meaning | Recall cost |
|---|---|---|---|
| **ACTIVE DUTY** | auto-loaded every session (hot context) | running, in the hot path | instant |
| **a) NATIONAL GUARD** | **load-on-demand** — in-repo, indexed, Read/recalled on trigger | installed but invoked only when needed | seconds (Read / invoke) |
| **b) RESERVE** | archived out of the working path (`archive/`, cold docs) | disabled, dependencies intact, recallable | minutes (un-archive / re-enable) |
| **c) RETIRED — ACTIVE RESERVE** | cold storage (`.DISABLED` / soak dir) | stopped + unwired but on disk | hours (restore + rewire) |
| **d) RETIRED COMPLETELY** | eliminated — purged from repo | eliminated — verified-gone, zero callers | rebuild from scratch |

**Demotion is the default direction.** Promotion happens only on demonstrated need. **ACTIVE DUTY is earned, not assumed** — the burden is on a thing to justify staying hot, not on us to justify demoting it.

**"d) Retired completely" = verified-gone, not decided-gone.** Tier-d requires the MISSION-324 verified-decommission check: stopped → refs removed → zero callers → orphan-free → reclaimed. Same discipline as razor-sharp/efficacy: prove the end-state.

## §2. CONTEXT-BLOAT RULE (init footprint)
- **Active-Duty auto-load target: ≤ 15K tokens of files.** Anything above earns a demotion review.
- Heavy personas/manuals/indexes ride a **lean Active-Duty core** (identity + authority + gates + pointers); the full file is **National Guard** (load-on-demand).
- Indexes (MEMORY.md) stay one-line-per-entry — detail lives in topic files (National Guard).
- Adding any `@`-auto-ref multiplies by every turn × every session — it requires a demotion of something else of equal weight. No net Active-Duty growth without a swap.

## §3. AUTHORITY — STAFF EXECUTE WITHOUT COMMANDER APPROVAL
Hale + ELON + Whetstone + Sterling run the ladder and the cadence **autonomously**. Demoting context, phasing out unused tools a→b→c→d, trimming auto-load — all non-gated, execute-and-report. The three Commander gates still hold (client send, financial commitment, strategic), as do the 6 protected files. A tier-d *elimination* of anything client-affecting still surfaces; everything else is the staff's call.

## §4. "FRESH AND LETHAL" — D/W/M/Q CADENCE
| Cadence | What runs | Owner | Engine |
|---|---|---|---|
| **DAILY** | CI razor-sharp health check (100%×7d → weekly); init-footprint check (alert if Active-Duty > 15K) | Whetstone | `ci_daily_routine.py` · `stack_freshness_scan.py --daily` |
| **WEEKLY** | Tool-usage staleness scan → demote unused-≥14d to National Guard; ELON kill-audit (recurring); adoption-shortlist refresh | ELON | `stack_freshness_scan.py --weekly` |
| **MONTHLY** | Reserve sweep — National-Guard items unused another 30d → Reserve; full Whetstone razor-sharp audit; SO/doc purge | Whetstone + Sterling | `stack_freshness_scan.py --monthly` |
| **QUARTERLY** | Retire sweep — Reserve/cold items unused all quarter → tier-c/d (verified-decommission); full stack review; context-bloat hard reset | ELON + Sterling | `stack_freshness_scan.py --quarterly` |

**Staleness thresholds (default, tunable):** unused ≥14d → National Guard · ≥30d further → Reserve · ≥90d further → Retired-active-reserve · ≥1 quarter cold → Retired completely.

Reports roll into the brief; client-affecting tier-d → Commander; everything else logged, not asked.

*Backbone for: init-bloat cut, staleness phase-out, MISSION-324 verified-decommission. Amends SO_CI_RAZOR_SHARP_20260620 (cadence) + SO_TECH_VANGUARD_ELEVATION_20260621 (ELON/Whetstone own the ladder). CLAUDE.md § Readiness Ladder.*
