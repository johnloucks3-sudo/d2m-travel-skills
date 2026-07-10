# Hale Orchestrator — Unified Plan/Compliance/Evaluation Ledger — Design

**Date:** 2026-07-09 | **Source:** Commander-directed brainstorming session, Claude Code (Thunderbird)
**Status:** DESIGN — approved by Commander section-by-section, pending final spec review
**Companion doctrine:** `Personas/hale_cos.md` (OODA loop, Autonomy Posture), `core/ci/repairs/schema.py` (RiskTier/AssessResult pattern reused), `core/ops/three_voice_arbitration.py` (structured-submission/ruling pattern reused)

---

## Problem Statement

Hale's planning, compliance, initiative, and evaluation behavior today is governed entirely by prose doctrine (`CLAUDE.md`, `Personas/hale_cos.md`) and scattered untyped JSON/markdown state (`mission_board.json`, `hale_decisions.md`, `commander_prediction_ledger.json`). Nothing in code tracks a plan's compliance checks against standing orders, logs initiative taken beyond the literal ask, or produces a mechanically-checkable pass/fail assessment at close-out. Standards are asserted in prose ("Hale did X") rather than verified against named criteria. Sterling's own recurring question — "how will we know it worked?" — currently has no code-backed answer for Hale's own operating loop, only for the narrower CI self-healing and Three-Voice-Arbitration subsystems.

## Goal

One unified orchestrator — a `Plan` object carrying compliance checks, initiative notes, planning criteria, and a final evaluation as facets of a single lifecycle — applied **universally** (every task, however small) without imposing meaningful authoring overhead on trivial work, and without ever blocking or gating Hale's actual execution authority.

## Non-Goals

- Not a runtime supervisor or approval gate. The orchestrator never blocks execution; it is a compliance/evaluation ledger only.
- Not a replacement for `mission_board.json`, `commander_prediction_ledger.json`, or the Three-Voice-Arbitration engine. It reads context from these where useful but does not migrate or absorb them.
- Not a rewrite of the Wing Exercise Protocol's T0–T3 tiering — it reuses that classification where a tier is given, it doesn't reimplement it.

---

## Architecture

```
core/ops/hale_orchestrator.py          # the library
  Plan               dataclass: id, task_summary, tier, opened_at,
                      compliance_checks[], initiative_notes[],
                      criteria[] (auto or explicit), status
  AssessResult        dataclass: plan_id, verdict, quality_tier,
                      criteria_met[], criteria_missed[], criteria_unverified[],
                      notes, closed_at
  PlanStore          reads/writes structured fenced blocks in hale_decisions.md
  open_plan(...)     -> Plan            (auto-derives criteria unless given)
  assess_plan(plan)  -> AssessResult    (PASS/FAIL + optional G/Y/R tier)
  close_plan(plan, result)              # writes the closing block

.claude/hooks/hale_orchestrator_backstop.py   # Stop hook
  - scans this turn's tool-call log for an OPENED block with no matching
    CLOSED block in hale_decisions.md
  - if no Plan was opened at all this turn -> auto-files a trivial
    default Plan+PASS (the 3-item floor, mechanically checked)
  - if a real Plan was opened but never closed (task died mid-way) ->
    auto-closes it FAIL, notes="never reached assessment" — orphaned
    plans are visible, not silently swallowed
```

Two entry points, one log. Hale calls the library directly for anything she consciously wants to plan/gate (cheap by default, richer when explicit criteria are supplied for T1+ work). The Stop hook is the safety net guaranteeing universal coverage — nothing this turn goes unlogged, including abandoned plans, which is itself useful audit signal.

This generalizes two patterns already proven in this codebase rather than inventing a new one: `core/ci/repairs/schema.py`'s dataclass+enum assess/verify contract, and `core/ops/three_voice_arbitration.py`'s structured-input → durable-log shape.

## Components

**`Plan` dataclass**
```python
@dataclass
class Plan:
    plan_id: str                    # short random id, e.g. "PLN-8f2a1c"
    task_summary: str               # one line, what's being done
    tier: str                       # "trivial" | "T1" | "T2" | "T3"
    opened_at: str                  # ISO timestamp
    compliance_checks: list[str]    # e.g. ["no client-send gate crossed", "no financial commit"]
    initiative_notes: list[str]     # free-text: proactive work beyond the literal ask
    criteria: list[str]             # auto-derived or explicit — what "done" means
    status: str                     # "open" | "closed"
```

**`AssessResult` dataclass**
```python
@dataclass
class AssessResult:
    plan_id: str
    verdict: str                       # "PASS" | "FAIL"
    quality_tier: Optional[str]        # "GREEN" | "YELLOW" | "RED" | None (trivial plans skip this)
    criteria_met: list[str]
    criteria_missed: list[str]
    criteria_unverified: list[str]     # distinct from missed — see Error Handling
    notes: str
    closed_at: str
```

**Auto-derivation rule** — for a plan with no explicit criteria, `open_plan()` generates a fixed 3-item floor: *(1)* no Commander gate crossed without authorization, *(2)* every file/action claimed as done is independently verifiable (stat/read-back), *(3)* no unhandled exception. Zero authoring cost for trivial work.

**Tier reuse** — `open_plan(tier="T2"/"T3", ...)` pulls the matching Wing Exercise Prompt Charter fields in as additional `compliance_checks` rather than duplicating that classification logic.

**`PlanStore`** — appends a fenced block to `hale_decisions.md` on open and on close (pure append, matching the file's existing convention — never a rewrite). Close blocks embed the matching `plan_id` so the backstop hook can grep for opens without closes.

## Data Flow

```
1. Hale (explicit path) or Stop-hook (backstop path)
        │
        ▼
2. open_plan(task_summary, tier="trivial"|"T1"|"T2"|"T3", criteria=None)
        │  - generates plan_id
        │  - if criteria is None: auto-derive the 3-item floor
        │  - if tier != "trivial": pull in matching Prompt Charter fields
        │    as compliance_checks
        │  - PlanStore appends an OPENED block to hale_decisions.md
        ▼
3. [Hale executes the actual task — normal tool calls, no orchestrator
    involvement mid-flight; this is a log, not a runtime supervisor]
        ▼
4. assess_plan(plan) — called explicitly at task end, OR by the Stop
   hook if never called
        │  - each criterion checked mechanically where possible
        │    (e.g. "file X written" -> os.path.exists)
        │  - criteria that can't be mechanically checked ->
        │    UNVERIFIED (never a silent PASS)
        │  - verdict = FAIL only if any criterion is MISSED;
        │    UNVERIFIED alone caps quality_tier at YELLOW, not a hard FAIL
        │  - quality_tier only computed for tier != "trivial"
        ▼
5. PlanStore appends a CLOSED block (same plan_id) to hale_decisions.md
        ▼
6. Stop-hook backstop: greps hale_decisions.md for OPENED plan_ids from
   this session with no matching CLOSED block -> auto-closes each FAIL,
   notes="never reached assessment"
```

Key invariant: the orchestrator never blocks or gates execution. It is a compliance/evaluation ledger, not a runtime enforcer — Hale still executes freely inside her existing authority; this makes the record of what she did and whether it held up mechanically checkable afterward, rather than resting on prose self-report.

## Error Handling

- **Orchestrator failures never block real work.** Every call (`open_plan`, `assess_plan`, `close_plan`) is wrapped so an internal exception is caught, logged to `logs/hale_orchestrator_errors.log` (same stdlib pattern as `core/monitoring/crash_reporter.py`), and swallowed. A broken ledger must never stop the actual task.
- **Unverifiable ≠ FAIL.** Criteria resolve to `MET` / `MISSED` / `UNVERIFIED`. `verdict = FAIL` only on a real `MISSED`. An `UNVERIFIED` criterion (e.g., a qualitative check with no mechanical test) downgrades `quality_tier` to at most YELLOW but never forces a hard FAIL — avoiding manufactured false failures on inherently qualitative criteria while still refusing to silently rubber-stamp them as PASS.
- **Concurrent writes across Hale's 8 instantiations.** `hale_decisions.md` is shared per the Hale Bus doctrine. `PlanStore` appends use `fcntl.flock` around open+write+close with short retry/backoff on contention — append-only, no rewriting, worst case a few-hundred-ms wait, never data loss.
- **Backstop hook tolerates the pre-existing prose format.** The orphan-scan only matches the new fenced `<!-- PLAN:... -->` blocks; it ignores every pre-existing prose entry rather than trying to parse it. A hook exception is caught and logged, never blocks session end.

## Testing

**Unit tests (`core/ops/test_hale_orchestrator.py`)** — pure logic, tmp-path I/O only:
- `open_plan()` auto-derives the 3-item floor when no criteria given; passes explicit criteria through untouched.
- `open_plan(tier="T2")` pulls in Prompt Charter fields as compliance checks (mocked Wing Exercise data).
- `assess_plan()` verdict logic: all MET → PASS; any MISSED → FAIL; only UNVERIFIED (no MISSED) → PASS + YELLOW cap, never a hard FAIL.
- `PlanStore` append is safe under concurrent writes — N threads appending against a shared tmp file, assert no interleaved/corrupted blocks (exercises the `fcntl` lock path).
- Backstop orphan-scan ignores pre-existing prose entries, only matches fenced `PLAN:` blocks, correctly identifies an OPENED with no CLOSED as orphaned.

**Integration test** — end-to-end against a scratch copy of `hale_decisions.md`: open trivial plan → close PASS → read back → verify both blocks present and parseable. Separately: open a plan, never close it, run the backstop scan, verify it appends the auto-FAIL block.

**Live verification** (per this session's standing obstacle-routing/verification discipline): after building, run one real trivial task through the full path and read `hale_decisions.md` directly to confirm the OPENED/CLOSED blocks actually landed — not just trust the function's return value.

---

## Decisions Log (from brainstorming session)

| Question | Decision |
|---|---|
| Unified object vs. 6 loosely-coupled modules | **Unified** — one `Plan` lifecycle |
| When is a Plan created | **Universal** — every task, however small |
| Who authors criteria for trivial tasks | **Auto-derived defaults**, explicit criteria layered on top for larger tasks |
| Where does state live | **Extends `hale_decisions.md`** as the canonical structured log |
| Assessment output | **Both** — binary PASS/FAIL gate + optional GREEN/YELLOW/RED quality tier |
| Enforcement mechanism | **Library + Stop-hook backstop** (Approach 3) — explicit calls for real work, hook guarantees universal coverage |
