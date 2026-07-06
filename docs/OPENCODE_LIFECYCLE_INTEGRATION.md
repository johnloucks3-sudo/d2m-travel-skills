# OpenCode Lifecycle Integration — Architecture Guide
## Wiring the Phase Determination Engine to the Canonical Touchpoint Model
### Dreams2Memories Travel, LLC · 2026-07-06

---

## Why this exists

Thunderbird had two lifecycle perspectives that were never wired together:

1. **Phase Determination Engine** (`core/lifecycle/client_ingester.py`) — algorithmic. Given four
   anchor dates (booking, FPD, embark, disembark) it computes PHASE_0..PHASE_5 with no human
   judgment involved.
2. **Touchpoint Production Model** (`config/lifecycle_touchpoints.json`, anchor-relative — see
   Data Sources below) — operational. It lists the actual deliverables (research, emails, internal
   checks) and *when* each is due, relative to the B/E/FPD/D anchors.

Neither system knew about the other. A phase transition (e.g. a client crossing from Craft into
Execute) had no automatic effect on which touchpoints got worked. This integration closes that gap
without merging the two models — they stay separate perspectives, joined at read time by date-range
arithmetic.

## Data sources — reconciling three different touchpoint counts

Three touchpoint counts exist in this repo and none of them agree:

| Source | Count | Shape |
|---|---|---|
| Canonical framework (`memory: reference_canonical_lifecycle_touchpoints.md`, Commander-approved 2026-04-17) | 23 | Phase-bucketed (Onboarding/Discovery/Momentum/Pre-Departure/Payment/Post-Voyage) |
| This task's spec + `docs/OPENCODE_LIFECYCLE_ARCHITECTURE.md` | 35 | Referenced but not enumerated in either doc |
| `config/lifecycle_touchpoints.json` (pre-existing file, found already populated during this build) | 39 | Anchor-relative (`anchor_origin` ∈ {B,E,FPD,D} + `anchor_offset_days`), sourced from `docs/CLIENT_LIFECYCLE_ARCHITECTURE.md` v1.0 |
| `D2M/clients/kuklinski_touchpoints.json` (one real client's actual TP log) | 25 | Per-client instance, mixes canonical + ad hoc entries |

**This integration uses `config/lifecycle_touchpoints.json` (39 anchor-relative touchpoints) as the
live data source**, for one reason: it is the only one of the four that is *computable*. Anchor
origin + offset days lets code derive an exact target date from a client's actual anchors. The
23-TP canonical model is phase-bucketed by nominal E-day windows (e.g. "E-240 to E-210"), which
looks similar but isn't computable the same way — those windows assume a canonical FPD-to-embark
gap that varies by cruise line (Regent T-120 vs Viking/Silversea T-90), so a static
phase-code -> touchpoint-ID map would silently misfile touchpoints for any client whose contract
term differs from the assumption baked into the bucket. This was verified empirically while
building the mock fixtures (see Anchor Validation below) — the same 39-TP config, evaluated against
three different anchor-gap shapes, produces a different active-touchpoint set each time, which is
exactly the behavior a static bucket cannot reproduce.

The discrepancy is not resolved here — it is flagged. If a future pass reconciles the 23-canonical
and 39-anchor-relative sets into one list, `select_active_touchpoints()` in
`lifecycle_event_handler.py` does not need to change; it only needs `config/lifecycle_touchpoints.json`
to keep the `anchor_origin` / `anchor_offset_days` shape.

## Architecture

```
                                                 ┌───────────────────────────────┐
  Dossier / TESS / anchor-date update  ────────► │  lifecycle_event_handler.py    │
  (booking_date, fpd, embark_date,               │                                │
   disembark_date, payment_status)               │  1. assign_phase()  ───────────┼──► phase_determination_engine.py
                                                  │     (delegates to                    ├─ determine_phase()      [client_ingester.py]
                                                  │      client_ingester.py,              ├─ anchor_validation()    [anchor_validation.py]
                                                  │      adds as_of + payment label)      └─ phase_window()         (this file)
                                                  │                                │
                                                  │  2. compare vs stored phase   │
                                                  │     lifecycle_phase_state.json│  ← persisted last-known phase per booking_id
                                                  │                                │
                                                  │  3. if changed:               │
                                                  │     select_active_touchpoints()┼──► config/lifecycle_touchpoints.json
                                                  │     (anchor arithmetic:              (anchor_origin + anchor_offset_days
                                                  │      target = anchor + offset,        → filtered to [phase_start, phase_end))
                                                  │      kept if inside phase_window)
                                                  │                                │
                                                  │  4. queue_touchpoint_tasks()  ─┼──► core/hale_bus/brain_bridge.py
                                                  │     one A2-research task per         (oc lane — ops/mechanical work,
                                                  │     active touchpoint                 never ground out inline, per standing doctrine)
                                                  │                                │
                                                  │  5. return phase_changed event │
                                                  └───────────────┬────────────────┘
                                                                  │
                                                                  ▼
                                                  ┌───────────────────────────────┐
                                                  │  scripts/lifecycle_event_bridge.py
                                                  │  - runs run_scan() over a client list
                                                  │  - notify_hale(events):
                                                  │      write_bus_state(instance_type="opencode", alerts=[...])
                                                  │      append_channel_activity(channel="console", ...)
                                                  └───────────────┬────────────────┘
                                                                  │
                                                                  ▼
                                                   core/hale_bus/hale_bus_state.json
                                                   (any Hale instance's session-start
                                                    bus read picks up the transition)
```

## File-by-file

### `core/lifecycle/client_ingester.py` (extended, not forked)
Added an `as_of: Optional[date] = None` parameter to `determine_phase()` and
`validate_anchor_dates()`, defaulting to `date.today()` when omitted. This is the only change to
existing behavior, and it's backward compatible — every existing caller (`testing/phase_validation_suite.py`)
passes no `as_of` and is unaffected. The reason for the change: phase transitions and tests both
need to evaluate "what phase would this client be in on date X" without waiting for real time to
pass or monkeypatching `datetime.date.today()`.

### `core/opencode/anchor_validation.py`
Extends `client_ingester.validate_anchor_dates()` — does not duplicate its checks. Adds two the
base validator lacks:
- `booking_date < fpd` (base validator checks embark/disembark/fpd order, not booking-vs-fpd)
- FPD alignment with the cruise line's contract term (Regent T-120, default T-90 for everyone
  else, ±7 day tolerance) — a **warning**, never an error, since real supplier contracts vary by
  promo/fare class.

Returns the base report plus `"pass"` (alias of `"valid"`) and `"reasons"` (errors + warnings
combined) — the vocabulary the task spec asks for.

### `core/opencode/phase_determination_engine.py`
Thin orchestration layer, not a reimplementation:
- `assign_phase()` — calls `client_ingester.determine_phase()` + `anchor_validation.validate_anchors()`,
  adds a `payment_status` label in the **Deposit / In Progress / FPD Due / Paid** vocabulary the
  task spec asks for (derived from raw paid/pending/partial + timing vs FPD — see the
  `_payment_status_label()` docstring for the exact heuristic).
- `phase_window()` — returns `(start_date, end_date_exclusive)` for a phase, computed from a
  specific client's own anchors, using the same boundary conditions as
  `client_ingester.PHASE_DEFINITIONS`. This is what makes anchor-relative touchpoint selection
  possible: a touchpoint is "active" for a phase if its own target date falls inside that window.

### `core/opencode/lifecycle_event_handler.py`
The event dispatcher itself:
- `load_phase_state()` / `save_phase_state()` — persisted last-known phase per `booking_id` in
  `core/opencode/lifecycle_phase_state.json` (path overridable via `LIFECYCLE_PHASE_STATE_PATH`
  env var for test isolation). Without this, "did the phase change" has nothing to compare against.
- `select_active_touchpoints()` — anchor arithmetic against `config/lifecycle_touchpoints.json`
  (path overridable via `LIFECYCLE_TOUCHPOINTS_CONFIG_PATH`), filtered to the new phase's window.
- `check_client()` — the per-client entry point: compute phase, compare to stored, if changed
  queue tasks and persist the new phase, return the event (or `None` if unchanged).
- `run_scan()` — `check_client()` over a list, returns only the events that fired.
- Task queueing accepts an injectable `bridge` object (`.add(title, description, lane, priority)`)
  so tests never have to touch the shared production `brain_bridge_board.json`. Defaults to
  `core.hale_bus.brain_bridge.BrainBridge()` — ops/mechanical work goes to the **oc lane**, per
  `SO_TALON_JET_DIVISION_OF_LABOR_20260703` (Hale posts, never grinds this inline).

### `scripts/lifecycle_event_bridge.py`
CLI entry point: loads a JSON client list, runs the scan, and for any events that fired, notifies
Hale via the shared bus:
- `write_bus_state(instance_type="opencode", alerts=[...])` — so any Hale instance's mandatory
  session-start bus read (`hale_bus_read.load_bus_at_startup`) picks up the transition without the
  Commander repeating context.
- `append_channel_activity(channel="console", event_type="phase_changed", ...)` — the
  cross-channel visibility feed (Unified C2 Fabric Phase 1).

This is an **internal notify only**. No client-facing or external send happens here, and none
should — a phase transition is an internal signal that research/production tasks are now due, not
a client-facing event.

## Integration points with the CC lifecycle orchestrator

No `lifecycle_orchestrator.py` exists yet on the Claude Code side (checked at build time — only
`core/lifecycle/client_ingester.py` exists). The integration point, when it's built, is:
`core.opencode.lifecycle_event_handler.check_client()` / `run_scan()` are the functions a CC-side
orchestrator (or a scheduled OpenCode job) should call whenever a dossier's anchor dates or payment
status change. They are pure functions over a client dict plus an optional `as_of` — no hidden
state beyond the phase-state file, so either side of the CC/OC boundary can call them.

## Known limitation — Qdrant coupling in `brain_bridge.py`

`core/hale_bus/brain_bridge.py`'s `BrainBridge.add()` unconditionally embeds every task into the
production Qdrant `thunderbird_memories` collection (`_qdrant_embed_task()`), even when
`BRAIN_BRIDGE_BOARD_PATH` is overridden to a scratch file for testing. This surfaced during this
build: two manual smoke-test runs of `lifecycle_event_bridge.py` against the real `BrainBridge()`
left 126 orphaned test-task embeddings in production Qdrant (cleaned up same session — filtered by
the mock booking IDs and deleted). **Do not run `lifecycle_event_bridge.py` against the default
(real) `BrainBridge()` for testing purposes** — use the pytest suite
(`core/opencode/test_lifecycle_integration.py`), which injects a `FakeBridge` and never touches
Qdrant, the board file, or the hale_bus. A follow-up fix (out of scope for this build) would gate
`_qdrant_embed_task()` behind the same `BRAIN_BRIDGE_BOARD_PATH` override so board-path isolation
also isolates the Qdrant side effect.

## Test scenarios (`core/opencode/fixtures/mock_clients.json` + `test_lifecycle_integration.py`)

| Scenario | Booking ID | What it exercises |
|---|---|---|
| **Normal** | `MOCK-NORMAL-001` | Standard Regent T-120 gap. Adjacent transition PHASE_1 → PHASE_2. Anchor validation passes clean (no contract-term warning). |
| **Early embark** | `MOCK-EARLY-EMBARK-002` | Last-minute Viking booking, full payment posted almost immediately. Phase *skips* PHASE_2 entirely: PHASE_1 → PHASE_3 → PHASE_4. Anchor validation warns (FPD far outside nominal T-90). |
| **Late FPD** | `MOCK-LATE-FPD-003` | Regent contract with FPD only 9 days before embark (T-120 badly violated). Anchor validation flags the drift as a warning while still passing (dates are logically ordered, just operationally unusual). Phase jumps PHASE_1 → PHASE_3, skipping PHASE_2. |

All 5 tests pass (`python3 -m pytest core/opencode/test_lifecycle_integration.py -v`):
verified transitions fire the correct event type and phase codes, verified task queueing produces
exactly one task per active touchpoint (all tagged `lane="oc"`), and verified phase state persists
across calls keyed by `booking_id`.

## Files delivered

- `core/opencode/phase_determination_engine.py`
- `core/opencode/anchor_validation.py`
- `core/opencode/lifecycle_event_handler.py`
- `scripts/lifecycle_event_bridge.py`
- `core/opencode/fixtures/mock_clients.json` (test fixtures)
- `core/opencode/test_lifecycle_integration.py` (test suite)
- `docs/OPENCODE_LIFECYCLE_INTEGRATION.md` (this file)
- Minimal extension to `core/lifecycle/client_ingester.py` (added `as_of` param, backward compatible)
- Minimal extension to `core/hale_bus/brain_bridge.py` (added `BRAIN_BRIDGE_BOARD_PATH` env override, mirrors existing `HALE_BUS_STATE_PATH` pattern)
