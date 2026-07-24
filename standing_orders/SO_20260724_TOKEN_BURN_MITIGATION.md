# SO-20260724 — TOKEN BURN MITIGATION

**Effective:** 2026-07-24 07:30 MT  
**Authority:** John Loucks (Commander)  
**Applies to:** CC (Claude Code), OpsCenter automation, nexus daemon, systemd timers

## RATIONALE

On 2026-07-24 morning, token usage jumped from 0% (weekly reset at 21:00 MT 2026-07-23) to 12% in 10.5 hours due to **4 email-responder timers firing simultaneously**, each spawning a full Claude MAX session (190KB each). At unchecked rate: **27.4% per day → 191% per week → exhaustion by Tuesday.**

## ROOT CAUSE

- `dani-email-responder.timer` (15-min cadence)
- `hale-email-responder.timer` (15-min cadence)
- `persona-email-responder.timer` (15-min cadence)
- `wind-email-responder.timer` (15-min cadence)

All 4 fired at 07:33 MT same morning, spawning 4 redundant MAX sessions in parallel.

## ACTIONS EXECUTED (2026-07-24 07:30 MT)

1. ✅ **Disabled 4 email-responder timers** (permanently)
2. ✅ **Created batched-email-queue-processor** (30-min cadence, single Opus session)
3. ✅ **Added budget guard to nexus.py** (circuit-breaker at 80%/50%)

## STANDING RULES (PERMANENT)

### Rule 1: No Parallel Timer Spawns
**Prohibition:** No two systemd timers may spawn Claude sessions within 5 minutes of each other.

**Rationale:** Parallel spawns cause cost amplification. Email/intelligence tasks must queue + batch.

**Check:** Before creating new `.timer` file, audit existing timers. Offset new timer by 5+ minutes from nearest existing.

**Enforcement:** Weekly timer audit report (Fridays 17:00 MT).

### Rule 2: Model Routing by Task Type
**MAX (claude-opus-4-8):** Strategic analysis, final client products, decision synthesis only.

**Opus (claude-opus-4-8):** Email sweeps, intelligence ingestion, routine monitoring, background tasks.

**Rule:** If background timer prompt > 5 lines, route to Opus.

### Rule 3: Budget Hard Stops
- **≥80% used:** CRITICAL — no new spawns (emergency mode)
- **≥50% used:** HIGH — Opus only, no MAX spawns
- **<50% used:** GREEN — normal operation

**Enforcement:** Implemented in nexus.py `should_spawn_claude()` function.

**Logging:** All guard triggers logged to `OpsCenter/nexus_audit.log` with reason + intended task.

### Rule 4: Weekly Budget Report
**When:** Every Friday 17:00 MT (EOD)

**Content:** 
- Full audit log of all timer spawns
- Model routing decisions
- Guard trigger log (timestamp + budget % + blocked task)
- Projected burn rate for coming week
- Any timers recommended for disable/batch

**Threshold:** If projected burn > 90% by week-end, escalate to Commander with timer recommendations.

## MITIGATIONS — IMPACT

| Metric | Before | After | Impact |
|--------|--------|-------|--------|
| Email responder sessions/day | 96 (4×24h) | 48 (1×30-min batch) | 50% reduction |
| Cost per email sweep | 190KB (MAX) | 29KB (Opus) | 85% savings |
| Daily burn (estimated) | 27.4% | ~6% | 78% cut |
| Weekly budget duration | 1.3 days | 11+ days | 8× longer |
| Guard triggers | None | Automated at 80%/50%/15% | Circuit-breaker active |

**Budget status at action (07:30 MT):** 12% used → 13% by 07:50 (timers off working)

## EXEMPTIONS

None. All background automation subject to these rules.

## RELATED PROCEDURES

- **docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md** — Approved spawn patterns (all timers must use `thunderbird_headless_spawn` wrapper)
- **OpsCenter/nexus.py** — Budget guard implementation
- **core/relay/email_batch_processor.py** — Batched queue processor (replaces 4 parallel timers)

---

**Last Updated:** 2026-07-24 07:52 MT  
**Next Review:** 2026-07-31 (after one week of operation)  
**Review Criteria:** Burn rate sustained at <10% daily, no guard triggers > 2/week

**Signoff:** John Loucks, Commander · Hale, Chief of Staff · A7 Sterling, Process Authority
