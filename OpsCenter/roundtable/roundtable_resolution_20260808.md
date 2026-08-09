# ROUND TABLE RESOLUTION — Email C2 / Tasking Redesign
**OC + AG + CC · 2026-08-08 · Chair: OC (Hale)**

## THE VERDICT
All three seats independently converged. This is a **unanimous resolution**, not a majority opinion.

### Convergence (all 3 seats agree)
1. **One canonical flow.** Poller → classifier → mission board → threaded reply. No parallel front doors.
2. **Decommission the hodgepodges**: `email_task_ingest.py` (orphaned JSON queue + opencode_inbox.md side-channel, its watcher already dead), `email_c2.py` `[WING]`, and trim `run_commander_directive_sweep.py` to fetch-only.
3. **Every email creates a mission-board row** — nothing dropped. Weight scales with mode.
4. **Reply is a WHO/RDD/ACTION/DELIVERABLE receipt** — the human-Exec feedback loop. This is the single most important missing artifact (AG emphasized it hard: "proof the loop is closed before work begins").
5. **Verification scales with the claim, not the mode** — TASKING/CC gate behind cross-engine verify; FYI/ACK auto-close at creation.

## DIVERGENCE + CHAIR'S CALL
| Point | AG seat | CC seat | Chair resolution |
|---|---|---|---|
| ACK handling | Auto-closed record task (4th bucket) | **Thread/ticket-id linkage** — ACK closes the loop Hale opened, not a 4th classifier mode | **CC.** ACK is about direction (Commander closing *my* loop), which a text-only classifier cannot detect. Use `In-Reply-To`/ticket-id on the reply path. |
| Highest-leverage fix | Receipt format | **Hardcoded `assigned_to="unassigned"`** in `_create_email_mission()` silently defeats WHO/RDD for every email task today | **CC.** Wire existing `mission_board_sync` schema (assigned_to, deadline_hours, acceptance_criteria) — it already exists, caller just doesn't fill it. |

## RESOLVED DESIGN (one flow)
```
1. SWEEP   run_commander_directive_sweep.py → FETCH-ONLY (strip its inline classify)
2. CLASS   email_mode_classifier.py → TASKING / CC / FYI / (ACK via thread-linkage, not classify)
3. ROUTE   directive_executor.route_email() →
             TASKING: full mission (assigned_to=RoutedSeat, acceptance_criteria, deadline_hours)
             CC:      full mission, seat inferred from content  (Commander intent → same bar as TASKING)
             FYI:     lightweight mission, auto-CLOSED at creation
             ACK:     close referenced ticket via thread/ticket-id
4. RECEIPT  ALWAYS send — WHO/RDD/ACTION/DELIVERABLE block (threaded reply) BEFORE work
5. ROUTE    task_templates.build_ag_task / build_oc_task / build_cc_task, gated by is_checkable()
6. EXECUTE  seat works it
7. VERIFY   TASKING/CC: cross-engine verify_and_record; FYOck: none needed
8. CLOSE    reply: Done + artifact (verified) / UNVERIFIED truthfully / Acknowledged-closed
```
**CC ROUTE = `/ask` wrapper (real Claude). AG ROUTE = `contact_ag.py` native (real Gemini). Neither seat routes through the other's lane.**

## COMMANDER-FACING FEEDBACK (what a letter-in is now worth)
Every letter, CCPU, or forward returns, before any work:
```
WHO:         Hale/OC · Dani · Sterling · Harlan · AG · CC
RDD:         2026-08-09 18:00 MT
ACTION:      <one line, e.g. "verify Furlow flights against Centrav + Amadeus">
DELIVERABLE: <what is produced, e.g. "confirmed fare + booking note">
```
Tasking → Full mission + receipt + verification → Done.
CC → Same bar (Commander's intent, per non-negotiable #3).
FYI → Filed receipt, auto-closed.
Ack → Thread closes the loop Hale opened.

# ROUND TABLE RESOLUTION — Email C2 / Tasking Redesign
**OC + AG + CC · 2026-08-08 · Chair: OC (Hale)**

## THE VERDICT
All three seats independently converged. This is a **unanimous resolution**, not a majority opinion.

### Convergence (all 3 seats agree)
1. **One canonical flow.** Poller → classifier → mission board → threaded reply. No parallel front doors.
2. **Decommission the hodgepodges**: `email_task_ingest.py` (orphaned JSON queue + opencode_inbox.md side-channel, its watcher already dead), `email_c2.py` `[WING]`, and trim `run_commander_directive_sweep.py` to fetch-only.
3. **Every email creates a mission-board row** — nothing dropped. Weight scales with mode.
4. **Reply is a WHO/RDD/ACTION/DELIVERABLE receipt** — the human-Exec feedback loop. This is the single most important missing artifact (AG emphasized it hard: "proof the loop is closed before work begins").
5. **Verification scales with the claim, not the mode** — TASKING/CC gate behind cross-engine verify; FYI/ACK auto-close at creation.

## DIVERGENCE + CHAIR'S CALL
| Point | AG seat | CC seat | Chair resolution |
|---|---|---|---|
| ACK handling | Auto-closed record task (4th bucket) | **Thread/ticket-id linkage** — ACK closes the loop Hale opened, not a 4th classifier mode | **CC.** ACK is about direction (Commander closing *my* loop), which a text-only classifier cannot detect. Use `In-Reply-To`/ticket-id on the reply path. |
| Highest-leverage fix | Receipt format | **Hardcoded `assigned_to="unassigned"`** in `_create_email_mission()` silently defeats WHO/RDD for every email task today | **CC.** Wire existing `mission_board_sync` schema (assigned_to, deadline_hours, acceptance_criteria) — it already exists, caller just doesn't fill it. |

## RESOLVED DESIGN (one flow)
```
1. SWEEP   run_commander_directive_sweep.py → FETCH-ONLY (strip its inline classify)
2. CLASS   email_mode_classifier.py → TASKING / CC / FYI / (ACK via thread-linkage, not classify)
3. ROUTE   directive_executor.route_email() →
             TASKING: full mission (assigned_to=RoutedSeat, acceptance_criteria, deadline_hours)
             CC:      full mission, seat inferred from content  (Commander intent → same bar as TASKING)
             FYI:     lightweight mission, auto-CLOSED at creation
             ACK:     close referenced ticket via thread/ticket-id
4. RECEIPT  ALWAYS send — WHO/RDD/ACTION/DELIVERABLE block (threaded reply) BEFORE work
5. ROUTE    task_templates.build_ag_task / build_oc_task / build_cc_task, gated by is_checkable()
6. EXECUTE  seat works it
7. VERIFY   TASKING/CC: cross-engine verify_and_record; FYOck: none needed
8. CLOSE    reply: Done + artifact (verified) / UNVERIFIED truthfully / Acknowledged-closed
```
**CC ROUTE = `/ask` wrapper (real Claude). AG ROUTE = `contact_ag.py` native (real Gemini). Neither seat routes through the other's lane.**

## COMMANDER-FACING FEEDBACK (what a letter-in is now worth)
Every letter, CCPU, or forward returns, before any work:
```
WHO:         Hale/OC · Dani · Sterling · Harlan · AG · CC
RDD:         2026-08-09 18:00 MT
ACTION:      <one line, e.g. "verify Furlow flights against Centrav + Amadeus">
DELIVERABLE: <what is produced, e.g. "confirmed fare + booking note">
```
Tasking → Full mission + receipt + verification → Done.
CC → Same bar (Commander's intent, per non-negotiable #3).
FYI → Filed receipt, auto-closed.
Ack → Thread closes the loop Hale opened.

## ROUTING — WHO DOES THE WORK (revised 2026-08-08, live headroom doctrine)

Live capacity at dispatch time is the assignment authority, not preference. The numbers
below are the actual meters read 2026-08-08 22:00 MT; the same checks re-fire on every
dispatch via `core.relay.engine_limits.check_headroom()` (+ `core.relay.cc_capacity` for CC).

### Live headroom snapshot (2026-08-08)
| Seat | Model lane | Headroom | 5-hr | 7-day | Status |
|---|---|---|---|---|---|
| OC | DeepSeek v4 ($0) | 100% | — | — | GREEN (unlimited) |
| CC | Claude Sonnet/Opus via `/ask` / `/ask-opus` (MAX) | 62% | 4% | 38% | YELLOW-ok |
| AG | Gemini 3.1 Pro via `contact_ag` native | 7.4% | — | — | RED — reserve-only |

### Assignment matrix (capability + limit + reliability)
| Work type | Primary | Secondary / verify | Gate |
|---|---|---|---|
| Mechanical ops (sweep, dedup, filings, receipts) | OC | — | none ($0) |
| Cheap-but-judgment (template fill, copy polish) | OC | AG/CC quick verify | `is_checkable()` |
| Real coding / architecture / data-risk edits | CC | OC ground-truth verify | CC headroom > 25% |
| Vision / 1M-context / heavy Google Workspace | AG | OC | **FORBIDDEN below 15% headroom** |
| Cross-engine verification (DONE verdicts) | opposite engine, never self | — | SO-2026-07-19 |
| Client-facing wording / dollar-figure emails | CC | AG witness on $ figures | Harlan sign-off on $ figures |
| ACK / structural closes | OC (cheap, no reasoning) | — | none |
| Large autonomous multi-hour builds | OC present, steps dispatched verified | CC oversees | Task Precision Ladder |

### Routing rules (loop-closed, no exceptions)
- **OC-first by default** — OC headroom >= 25% triggers self-execution ($0) per OC-first doctrine.
- **CC ONLY via `/ask` / `/ask-opus`** (real Claude, MAX bucket). **Never via `contact_ag.py`**
  — that burns AG's reserve lane. (Corrected in-session by Commander 2026-08-08.)
- **AG is near-void (7.4% at last read)** — routine tasking must NOT default to AG. AG is the
  reserve lane: vision, huge context, cross-engine verification only.
- **Routing is computed live, not by vibe** — `route_decision` reads `check_headroom`
  (`LIMITED_WARN` < 15%) for both OC→AG and OC→CC at dispatch time.
- **Verification is cross-engine and non-optional** (SO-2026-07-19): the engine that did the
  work never grades its own work. AG still usable for `verify_and_record` even when LIMITED.

### Reliability notes (repo history)
- AG's default-preferences path (GPT-OSS 120B) is hallucination-prone — always force a strong model on AG.
- AG went dark ~2.5h solo self-executing 2026-08-01 (auto-delegation trap) — never leave AG
  unattended on a long autonomous task; verify against ground truth.
- OC is the cheapest lane but not the smartest — ambiguity, not IQ, is the failure mode.
  Ambiguity in Commander intent routes EARLY to CC judgment.
