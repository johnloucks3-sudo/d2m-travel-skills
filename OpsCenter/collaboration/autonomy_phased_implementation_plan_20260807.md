# AUTONOMOUS OPS — PHASED IMPLEMENTATION PLAN | 2026-08-07

**BLUF:** Commander approved all 37 War Room ideas for implementation. CC owns the stack (CC + OC active, AG limited-use, Grok excluded). 3-phase build. Phase 1 started: idea #8 shipped and verified; OC's ideation pass failed (timeout) — noted, will not block build via OC on tightly-scoped tasks.

```
Overall Program: [██░░░░░░░░░░░░░░░░░░]  1/37 shipped (Phase 1 underway)
```

---

## SOURCING (37 ideas, 0 duplicates)
- CC seed: 9 (#1–9)
- Staff Room (Hale/Dani/Sterling/Dembe/Harlan): 16 (#10–25)
- AG (client-facing/strategic): 12 (#26–37, renumbered from AG's 1–12)
- OC (ops/infra ideation pass): **FAILED — timeout after 300s**, ticket bb-332b2f9e. OC's per-task hard cap is 5 min; open-ended ideation doesn't fit that budget. Not retried for ideation — OC gets tightly-scoped literal-step build tasks instead (see Phase 1 below).

## LANE POSTURE (this Commander directive)
| Seat | Posture | Notes |
|------|---------|-------|
| CC | Owns the stack, self-executes small/judgment work | This session |
| OC | Active, mechanical/literal-step tasks only | Just failed an open-ended ask; keep specs tight, <5min |
| AG | Limited — use sparingly | 7.9% daily headroom left at dispatch time (233/253) |
| Grok | Excluded this program | Commander directive |

---

## PHASE 1 — Low-risk, self-contained, ships this session/next (target: 1-2 days)
Selection criteria: no external API dependency, no client-facing surface, reversible, testable now.

| # | Idea | Owner | Status |
|---|------|-------|--------|
| 8 | Verification caching w/ TTL (`integrity_check.verify_and_record`) | CC | 🟢 **SHIPPED** — cache hit/miss tested, `logs/integrity_check_cache.json`, TTL 900s default |
| 16 | Silent-failure self-repair (restart-and-reverify before paging) | CC | 🟢 **SHIPPED** — new `scripts/timer_self_repair.py` (opscenter_watchdog covers live services, flap-detector covers slow-drip flapping; this closes the 3rd gap: dead timers / broken crons). Systemd unit live, runs every 30 min. Found 9 REAL broken automations on first run (see below) — repairs attempted, unresolved ones auto-paged via `incident_queue`, not a new alert path. |
| 6 | Decision matrix auto-refresh (30 min) | CC | ⚪ Queued — needs discovery (no `decision_matrix` module found in repo; likely net-new against `hale_state.json`) |
| 14 | Self-certifying mission close | CC | ⚪ Queued — extends `mission_board_sync.py:cmd_sss_close` |
| 4 | Cross-lane load balancing before dispatch | CC | ⚪ Queued — natural extension of `engine_limits.check_headroom()`, already proven this session |

## PHASE 2 — Medium complexity, internal systems, needs design pass (target: 1-2 weeks)
#1 escalation timer · #2 predictive batching · #3 credential auto-heal · #5 outcome learning loop · #7 anomaly playbooks · #9 adaptive concurrency · #11 client portal self-service · #13 sentiment pre-triage · #15 auto-generated status papers · #17 dossier staleness refresh · #18 booking-triggered port intel · #19 competitive price-delta alerting · #20 commission reconciliation (exceptions-only) · #22 margin/ROI auto-check · #23 chop-chain auto-advance · #24 pre-answered status digest · #25 cross-persona handoff · #33 supplier commission dispute bot · #36 commission tier optimizer · #37 VIP intake extractor

## PHASE 3 — High complexity / external integration / touches Three Gates (target: needs design review + Commander checkpoint before build)
#10 batch-approve draft queue ⚠ **flagged disagreement** (Sterling wants per-item spot-check retained; Dani wants full batching — Commander tiebreak needed) · #12 auto-draft itinerary revisions · #21 FPD/dunning sweep ⚠ **flagged** (Harlan wants dunning tone kept out of Dani's standard queue — separate template lane) · #26 fare-drop arbitrage engine · #27 milestone/pulse broadcast · #28 (dup of #33, dedup on build) · #29 competitive fleet intel crawler · #30 churn-risk radar · #31 self-healing Travefy sync · #32 multi-model consensus quoting gate · #34 disruption sentinel (AIS/weather) · #35 (dup #36) · Client-facing sends and financial commitments in ALL of these still route through WF-17 / Commander approval per the Three Gates — "approve for implementation" builds the machinery, does not waive the per-instance send/commit gate.

---

## TIEBREAKS — RESOLVED (Hale decision, Commander delegated 2026-08-07)
1. **#10 batch-approve client drafts:** Sterling's position wins. Batch-approve capped to documents/status/routine confirmations only. Free-text replies keep mandatory per-item spot-check — tone/fact-accuracy risk on unscripted client replies is exactly where a bad auto-draft does the most damage, and Dani's volume argument doesn't apply to the low-risk subset. Reclassified Phase 2 (bounded scope, lower risk than original ask).
2. **#21 dunning drafts:** Harlan's position wins. Separate collections/dunning template lane, not folded into Dani's standard client-comms queue — collections tone is a materially different voice from relationship-building client comms; mixing risks a wrong-tone send. Stays Phase 2/3 per financial-commitment sensitivity, but unblocked to scope.

## NEXT
- Phase 1 items #16, #6, #14, #4 — building next, self-executed by CC (small/judgment-bearing) or handed to OC with literal steps once scoped.
- Status updates as each phase item ships. No further OC ideation retries — OC's lane is fine for literal execution, not open-ended brainstorming (confirmed today).
