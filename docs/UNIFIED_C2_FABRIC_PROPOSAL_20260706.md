# UNIFIED C2 FABRIC — T3 Wing Exercise Proposal
**Date:** 2026-07-06 · **Classification:** T3 (Strategy/doctrine, new pattern, hard to reverse) · **Gate:** Commander Decision (Gate 4)
**Charter owner:** Commander (delegated draft to Hale, per session directive) · **Status:** ✅ APPROVED 2026-07-06 (Gate 4, Phase 1+2+3 in full, overriding staff's 30-day burn-in recommendation — see `hale_decisions.md:6098-6146`) — BUILT and verified live same session (`core/hale_bus/hale_bus_write.py`, `core/ops/confirmed_auto_execute.py`, `scripts/ci_probe_c2_fabric_roundtrip.py`). **DOC CORRECTION 2026-07-16:** this header incorrectly read "AWAITING APPROVAL" for 10 days after approval and was cited as still-pending by three later documents (`docs/CROSS_HALE_TASK_DELEGATION_DESIGN_20260716.md`, `OpsCenter/STAFF_PACKAGE_HOT_WINDOW_20260716.md`, `logs/hale_hot_window_20260716.md`) — those references are stale; the underlying bus is live, only the cross-Hale delegation ticket schema (a separate, later ask) still needs wiring onto it.

---

## 1. PROMPT CHARTER

| Field | Content |
|---|---|
| **Success criteria** | Commander never has to re-explain context because it happened "in the wrong channel." Every non-gated action increases in autonomy without a single new gate violation. Measurable via 3 metrics below. |
| **Scope IN** | Console (Claude Code), Wave Terminal, Telegram (@D2MC2C_bot), Email (AgentMail Primary C2) — unifying visibility + phased auto-execute across all four. |
| **Scope OUT** | The three hard gates (client send/WF-17, financial commitment, strategic >90d/$5K) — unchanged, absolute, regardless of channel. No new paid tools/subscriptions. No change to WhatsApp (stays decommissioned). |
| **Named staff** | Sterling (process/metrics), Harlan (cost/concurrency), Dembe (risk/weakest-link), Dani (client-voice impact — flagged, low relevance), Hale (synthesis/routing). |
| **Token/time budget** | This session to design + package. Implementation (if approved) is a separate follow-on pass, phased per below — not same-session. |
| **Exit condition** | Commander approves, requests revision, or rejects at Gate 4 below. One revision pass included. |

---

## 2. CURRENT STATE (AS-IS) — Four Disconnected Channels

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌──────────────────┐
│   CONSOLE   │   │    WAVE     │   │  TELEGRAM   │   │   EMAIL/AgentMail │
│ Claude Code │   │  Terminal   │   │ @D2MC2C_bot │   │   (Primary C2,    │
│    (CC)     │   │    (OC)     │   │             │   │  built today)     │
└──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └─────────┬─────────┘
       │                 │                 │                    │
       │   SILO          │   SILO          │   SILO             │  SILO
       │  (own context)  │ (own context)   │ (own context)      │ (own context)
       ▼                 ▼                 ▼                    ▼
  Commander must remember which channel holds which decision/context.
  hale_bus_state.json exists but is CC<->OC session-checkpoint only —
  not real-time, not read by Telegram or Email at all.
```

**Named gap:** a decision made in Console isn't visible from Wave without a manual checkpoint; Telegram and Email are entirely outside the bus today.

---

## 3. RED-TEAM FINDINGS (staff pass, verbatim — this changed the design)

The first draft proposed a single shared-state bus where **any channel's silence = auto-execute GO, uniformly.** Staff killed that as written:

- **Sterling:** *"a shared queue where 'silence=GO' fires uniformly across four channels multiplies the blast radius of a missed notification... that's not a silo problem, it's a false-consensus problem, and it's worse than repeating yourself."* Required before "done": (1) cross-channel gate-integrity test, 100% pass, no exceptions; (2) `auto_execute_confirmed_delivery_pct` ≥99% — silence only counts as GO on a **confirmed-delivered** notice; (3) bus write-conflict rate = 0.
- **Harlan:** *"Four async processes writing the same JSON file simultaneously is a corruption trap... that's the waste: not money, but silent state rot."* Also: Telegram/Email/Console have different latency — a uniform 5-minute window fires GO signals out of order across channels. Cost verdict: cheaper than today (one read per cycle vs four), but needs file-locking, ~30 lines, no material cost.
- **Dembe (55% confidence as originally written):** *"AgentMail went from 'does not exist' to 'Primary C2' and 'shared decision bus writer' in the same day, with zero operational history."* Weakest link, named plainly: **an unread email sitting six hours reads as 'silence=GO' identically to a Telegram message seen and ignored for five minutes — those are not the same kind of silence, and the design treated them as interchangeable.** Recommends a burn-in period before AgentMail gets bus-write privileges.
- **Dani:** ⚠ not addressed by design (no client-facing behavior changes) — correctly out of scope, flagged per doctrine rather than silently skipped.

**Synthesis (Hale):** all three substantive objections converge on one point — the design was safe on consolidation, unsafe on uniform auto-execute. Fixed by phasing, not abandoning.

---

## 4. REVISED SCHEMATIC (TO-BE, phased)

```
                    ┌───────────────────────────────────┐
                    │   hale_bus_state.json (LOCKED)     │
                    │   + SQLite WAL or fcntl lock       │
                    │   Single visibility ledger          │
                    └───────────────┬─────────────────────┘
              WRITE (append-only, locked) │ READ (full state)
        ┌───────────────┬─────────────────┼─────────────────┬───────────────┐
        ▼               ▼                 ▼                 ▼
┌──────────────┐ ┌──────────────┐ ┌───────────────┐ ┌────────────────────┐
│   CONSOLE    │ │     WAVE     │ │   TELEGRAM    │ │  EMAIL / AgentMail  │
│ sync, instant│ │ sync, instant│ │ near-real-time│ │  async, can sit     │
│ control plane│ │control plane │ │ push+ack       │ │  UNREAD for hours   │
└──────────────┘ └──────────────┘ └───────┬───────┘ └──────────┬──────────┘
                                           │                    │
                            Phase 2:               Phase 3 (GATED):
                     confirmed-delivery       only after 30-day burn-in
                     auto-execute timer        proves AgentMail reliable
                     (Telegram only)           under real concurrent load
```

### Phase 1 — Visibility Bus (low risk, approvable now)
- Add file-locking (SQLite WAL, or `fcntl` advisory lock — Harlan's fix) to `hale_bus_state.json`.
- Every channel appends its own activity to the bus (what happened, when, which channel). Every channel can read the full cross-channel log.
- **No change to auto-execute semantics at all.** Pure consolidation. This alone kills "repeat yourself across channels."
- Acceptance: bus write-conflict rate = 0 under a concurrent-write stress test (Harlan's ask).

### Phase 2 — Confirmed-Delivery Auto-Execute (Telegram + Console/Wave only)
- Extend Auto-Execute Protocol (notify → 5-min window → silence=GO) onto the shared bus, but **only** for channels where "silence" has one unambiguous meaning: Console/Wave (synchronous, Commander is present) and Telegram (push, delivery-confirmable via existing bot API).
- Silence only counts as GO on a **confirmed-delivered** notification (Sterling's ask) — not "sent," delivered.
- **Email/AgentMail is explicitly excluded from silence=GO in Phase 2** — stays "notify + wait for explicit reply," exactly as today. Dembe's finding stands: an unread inbox is not equivalent to an ignored push.
- Acceptance: cross-channel gate-integrity test at 100% (Sterling's ask) — a scripted suite that attempts a client-send/financial/strategic action from each enabled channel and asserts every gate holds, no exceptions.

### Phase 3 — Email folded into timed auto-execute (GATED, not approved today)
- Only considered after 30 days of AgentMail operating as Primary C2 with zero silent-delivery failures (Dembe's burn-in ask).
- Even then: Commander decides at that point whether "unread N hours" should ever equal "silence=GO" for email, or whether email permanently stays an explicit-reply channel by design, not by immaturity. That's a separate future decision, not assumed here.

---

## 5. METRICS (Sterling owns, tracked weekly)

| Metric | Target | Source |
|---|---|---|
| Cross-channel gate-integrity test pass rate | 100%, zero exceptions | Scripted suite, run before enabling Phase 2 on any new channel |
| `auto_execute_confirmed_delivery_pct` | ≥99% | Per-channel delivery receipt vs notifications sent |
| Bus write-conflict rate | 0 | File-lock instrumentation |
| `lessons_implementation_rate_pct` | ≥80% (existing standard) | hale_decisions.md tracking |

---

## 6. WHAT DOES NOT CHANGE
- The three Commander gates — absolute, regardless of channel, checked in Phase 2's gate-integrity test explicitly.
- WhatsApp stays decommissioned.
- Email/AgentMail's WF-17 and Lyons-exception rules — unaffected by this proposal.
- SO-2026-05-04 Real Autonomy Charter — this is an extension mechanism, not a replacement.

---

## 7. GATE 4 — COMMANDER DECISION
**Approve Phase 1 only** · **Approve Phase 1 + 2** · **Revise** · **Reject**

Phase 3 is not on the table today regardless of Commander's answer — it requires the 30-day AgentMail burn-in first, full stop.
