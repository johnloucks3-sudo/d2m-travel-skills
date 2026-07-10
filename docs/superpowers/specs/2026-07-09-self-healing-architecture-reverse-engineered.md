# Self-Healing Architecture — Reverse-Engineered — Design

**Date:** 2026-07-09 | **Source:** Reverse-engineered from existing code (no prior single doc existed) | **Hale Orchestrator Plan:** PLN-1ea9e8
**Status:** DESIGN — evaluated against running code, gaps identified, integration implemented same session

---

## Problem Statement

Self-healing capability was built incrementally across two unrelated efforts that were never reconciled into one architecture: a mature CI Repair Warehouse (Sterling, 2026-07-02) and a lighter fleet-observability layer (this week: crash reporter, py-spy diagnostics, restart-flap detector). Neither references the other. Hale Orchestrator — built later the same evening this doc is written — existed for neither. This doc names what's actually there, then integrates the orchestrator as a tracking/evaluation layer over both.

## What Actually Exists (reverse-engineered from code, not assumed)

### Lane 1 — CI Repair Warehouse (the "healing" engine)
`config/ci_registry.json` (53 registered skills, policy-of-record) → `core/ci/ci_health.py::sweep()` (probes every skill) → on RED, `_try_repair()` → `core/ci/repairs/schema.py::run_capability()` (the safety-contract runner) → one of 8 `core/ci/repairs/cluster_[a-h].py` files (~5,100 lines, ~53 `RepairSpec`s).

Each `RepairSpec` is a typed `explore() → assess() → repair(apply=) → verify()` loop with:
- `RiskTier` (SAFE auto-applies / CAUTION auto-applies+notifies / DESTRUCTIVE always stages, never auto-fires — enforced in the runner, not the spec, so no capability can bypass it)
- Durable cross-spawn anti-flap (circuit breaker + cooldown + per-window cap, read from a JSON state file because the engine is spawned fresh per heartbeat and in-memory breakers would reset)
- Full audit trail (`CapabilityResult.as_dict()` appended to `ci_repair_warehouse_audit.jsonl`)

This is a genuinely mature, already-self-evaluating system. It answers Sterling's "how will we know it worked?" for the 53 registered CI skills specifically.

### Lane 2 — Fleet Observability (built this session, NOT a healing loop)
`core/monitoring/crash_reporter.py` (stdlib-only faulthandler + excepthook + threading.excepthook + SIGTERM handler, zero-touch via `sitecustomize.py` on PYTHONPATH across 51 units) + `scripts/diagnose_hung_process.py` (py-spy / Docker-privileged fallback, on-demand) + `scripts/restart_flap_detector.py` (rolling-window restart-count timer).

This lane is **passive**: it detects and logs (crash_reporter writes a report; flap detector pages Whetstone), but **executes zero repairs**. It is also **not scoped to the 53 CI-registered skills** — it watches all 51 PYTHONPATH-enrolled units, most of which have no `RepairSpec` at all.

### The gap
Two lanes, zero cross-reference, and neither has a Hale-Orchestrator-style compliance ledger:
- Lane 1 has its own audit trail (`CapabilityResult`) but it's warehouse-private JSON, not something Hale's own compliance record (`hale_decisions.md`) ever sees.
- Lane 2 has no evaluation step at all — a crash is logged, a flap is paged, and that's the end of the record. There's no mechanically-checkable answer to "was this understood" the way Lane 1 has for registered skills.

## Decision — Autonomy Boundary (stated once, not left open)

The Commander's "totally autonomous" framing could be read as "expand auto-apply scope" (e.g., let DESTRUCTIVE-tier repairs fire, or let Lane 2 start executing fixes). **That is explicitly out of scope for this pass.** Per existing standing orders (`SO_CI_RAZOR_SHARP_20260620`: Hale already holds CI refresh/revision/replacement authority; only *spend* reaches the Commander) this integration does not require a Commander gate — but *raising* the tier-gate itself would be a genuine safety-doctrine change and is not being done here. Integration in this pass = **ledger only**: Hale Orchestrator wraps the existing decision points and records them; it does not alter what auto-fires, what stages, or what's DESTRUCTIVE. If a future pass wants to expand auto-apply scope, that's a separate, explicitly-flagged decision.

## Architecture (after integration)

```
Lane 1: config/ci_registry.json → ci_health.sweep() → _try_repair()
                                                            │
                                          run_capability() ─┤─→ open_plan()/assess_plan()/close_plan()
                                     (UNCHANGED gates)       │   (NEW — Hale Orchestrator wraps the call,
                                                              │    doesn't touch its logic)
                                                              ▼
                                                    hale_decisions.md (PLN-xxxxx blocks)
                                                              ▲
Lane 2: crash_reporter (on crash) ──────────────────────────┤
        restart_flap_detector (on flap) ─────────────────────┘
                                     (NEW — both open a Plan on their existing
                                      detection event, close it based on
                                      whether root cause was identified)

hale-orchestrator-sweep.timer (already live) catches orphans from BOTH lanes —
no new backstop needed, this is the universal-coverage layer already built.
```

## Components (integration-specific — Lanes 1/2 internals unchanged)

**`ci_health.py::_try_repair()`** — after `run_capability()` returns, open a trivial-tier Plan whose single criterion is `"{skill_id} repair verdict is mechanically recorded"`, immediately assess it MET (the `CapabilityResult` itself is the mechanical check) and close. This does not gate or delay the repair — it's a pure post-hoc ledger entry, called after the existing decision, never around it.

**`crash_reporter.py`** — in the exception/signal handler, after writing the existing crash report, open a trivial Plan (`"crash captured in {module}"`), with criterion `"crash report written to {path}"`, assess MET (file existence check), close. No behavior change to crash capture itself — this is strictly additive logging.

**`restart_flap_detector.py`** — when a unit crosses the flap threshold and Whetstone is paged, open a Plan (`"{unit} flap-paged to Whetstone"`) with criterion `"page delivered"`, assess based on the existing page-send return value, close.

All three integration points follow the same shape: **call the orchestrator AFTER the existing decision is made, never before or around it** — this preserves the Non-Goal from the original Hale Orchestrator design ("never a runtime supervisor or approval gate") and satisfies the autonomy-boundary decision above.

## Error Handling

Same contract as the orchestrator's own design: `open_plan`/`assess_plan`/`close_plan` calls are already internally wrapped (per `hale_orchestrator.py`) so a ledger failure never raises past the call site. All three new call sites additionally wrap the orchestrator calls in their own try/except as defense-in-depth, since these are hot paths (crash handler, repair loop) where an unhandled exception would be actively harmful.

## Testing

- `core/ci/test_ci_health_orchestrator_integration.py` — `_try_repair()` still returns the same `(repaired, detail)` tuple regardless of orchestrator success/failure; a Plan is opened+closed in `hale_decisions.md` when it succeeds; orchestrator exception does not propagate.
- `core/monitoring/test_crash_reporter_orchestrator_integration.py` — crash handler still writes its report and still calls `sys.__excepthook__`/re-raises as before; a Plan is opened+closed; orchestrator exception does not propagate.
- `scripts/test_restart_flap_detector_orchestrator_integration.py` — flap detection still pages as before; a Plan is opened+closed; orchestrator exception does not propagate.

## Decisions Log

| Question | Decision |
|---|---|
| Is this one architecture or two? | **Two lanes, reverse-engineered as such** — CI Repair Warehouse (mature, tiered auto-apply) and Fleet Observability (passive, detect-only). Not merged into one system; that would be a rewrite, not an integration. |
| Does "totally autonomous" mean expanding auto-apply? | **No, explicitly deferred.** Ledger-only integration this pass; tier gates untouched. |
| Where does Hale Orchestrator attach? | **After** each lane's existing decision point, never around/before it — preserves the orchestrator's own "never a runtime supervisor" non-goal. |
