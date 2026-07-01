# SO — TOTAL CI: Autonomous Lifecycle, TP & ARC Operations
## Standing Order · 2026-07-01 · Author: Sterling (A7) · Accountable: Hale (COS) · Commander-directed

---

## 1. Purpose & Redefinition

**Commander directive 2026-07-01:** CI (Critical Infrastructure) is hereby redefined to mean **anything required for autonomous lifecycle, TP, and ARC operations** — not only the technical probes (portals, fare-watch, dispatch) that the CI registry covered as of commit `0c758396`.

Every **client-facing lifecycle product** and every piece of **supporting infrastructure** the Wing has produced is now in scope for the razor-sharp, self-healing, autonomous standard defined below.

---

## 2. The CI Qualification Standard (definition of "done")

A capability **qualifies as razor-sharp CI** only when it satisfies ALL SIX:

| # | Criterion | Test |
|---|---|---|
| 1 | **REGISTRY** | Entry in `config/ci_registry.json` — id, owner, `currency_window_hours`, `client_affecting`, `fallback`, `dead_man_switch`. The table IS the policy. |
| 2 | **PROBE** | `scripts/ci_probe_<id>.py` measuring *outcome, not presence*. Exit `0`=GREEN, `1`=RED. Final stdout line `GREEN/RED <id>: <detail>`. |
| 3 | **REPAIR** | Real repair fn in `core/ci/ci_auto_repair_engine.py::REPAIR_FUNCTIONS` — restart/refresh/rebuild/re-stage. Returns `bool`. |
| 4 | **ESCALATE** | `client_affecting` flag routes RED→repair-fail to Commander (🔴); else to Sterling (⚙️). Repaired = ⚡ AUTONOMY, no Commander action. |
| 5 | **SCHEDULE** | Runs on a live schedule (`ci-sweep.timer` and/or a `supertimer` bot). Darkness is impossible without an alarm. |
| 6 | **DEADMAN** | Dead-man switch: if the product/service goes silent, someone is paged (pattern: `scripts/fare_watch_deadman.py`). |

**Autonomy meaning (per Commander 2026-07-01): "autonomous UP-TO-SEND."** Each product builds itself → self-heals → stages a ready-to-send draft. The **WF-17 client-send gate holds** for real clients. Loucks-as-client trips run fully end-to-end (WF-17 waived for the Commander). This SO does NOT rescind WF-17.

---

## 3. Hard Constraints (unchanged)

1. WF-17 client-send gate — no autonomous send to any client address.
2. Financial-commitment gate — including paid subscriptions for any adopted tool.
3. Strategic gate (>90d OR >$5K).
4. The 6 protected email-scanner/relay files (SO 2026-06-08) — no autonomous modification.

---

## 4. Registration Procedure (per capability — proven 6-step)

1. Write `scripts/ci_probe_<id>.py` (efficacy).
2. Write `repair_<id>()` in `core/ci/ci_auto_repair_engine.py`; add to `REPAIR_FUNCTIONS`.
3. Add registry entry in `config/ci_registry.json` (template: `fare-watch-centrav`).
4. Wire schedule (supertimer bot or `.timer`).
5. Add dead-man switch if silence = undetected failure.
6. Test: probe exits 0/1, repair returns bool, registry id present, sweep lists it. Commit.

`core/ci/ci_health.py::sweep()` already fires `_try_repair()` on RED and escalates — new probes inherit repair+escalation for free.

---

## 5. Governance — Position-Paper Gates

Program advances by milestone. **Every milestone terminates in a position paper rendered on-screen** (and full-sent to johnloucks3 — internal deliverable, no draft gate). Fixed format: **SITUATION · WHAT WE BUILT · PROBE EVIDENCE (before/after) · TOOLS ADOPTED/REPLACED · RISK & RESIDUAL GAPS · DECISION REQUIRED (approve/redirect/hold).** No track advances past its gate without Commander approval or redirect.

Milestones: **M0** Charter & Standard (this SO + verified inventory + scorecard + orchestrator decision) → **M1** Infrastructure CI → **M2** existing lifecycle products autonomous → **M3** missing lifecycle products coded → **M4** harness/tool replacement → **M5** unified razor-sharp steady state.

---

## 6. Completion Criterion

`output/CI_DASHBOARD.md` shows **every** infrastructure service, all **14** lifecycle product categories, and the **23** technical skills as RAZOR_SHARP — each with a live probe, a working repair, and a dead-man switch — and a forced failure of any one triggers autonomous repair with the correct escalation tier.

---

*Sterling (A7) — Process/Metrics/Code. Accountable owner: Hale (COS). Supersedes nothing; extends SO_CI_RAZOR_SHARP_20260620 coverage from technical CI to total CI.*
