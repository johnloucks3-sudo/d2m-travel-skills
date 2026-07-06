# UNIFIED C2 FABRIC — Phase 1 Implementation
**Date:** 2026-07-06 · **Ref:** `docs/UNIFIED_C2_FABRIC_PROPOSAL_20260706.md` (Gate 4: Approve Phase 1)
**Scope:** Visibility bus only. No auto-execute / silence=GO semantics — that is Phase 2, out of scope here.

---

## 1. What was already shipped (this session started from here, not from zero)

Commit `475c63bea` ("Phase 1 — file-locked bus + cross-channel activity log", same day) had already added:
- An `fcntl` advisory exclusive lock (`_locked_bus()`) around `hale_bus_state.json` writes in `hale_bus_write.py`.
- `append_channel_activity()` / `read_channel_activity()` — a flat, capped (500-entry) cross-channel log keyed by `channel` (console/wave/telegram/email).
- `scripts/ci_probe_c2_fabric_roundtrip.py` — a CI probe asserting a write/read round-trip on the bus and (rate-limited) on AgentMail.

This document covers what was **added on top** of that baseline: real atomicity, the two named Phase 1 modules (`c2_fabric_read.py` / `c2_fabric_write.py`), a fix to a live unlocked writer found mid-session, and the concurrency test.

---

## 2. Lock strategy

**One lock file, one lock, all writers.** `LOCK_PATH = HALE_BUS_PATH.with_suffix(".lock")`, acquired via blocking `fcntl.flock(LOCK_EX)` in `hale_bus_write._locked_bus()`. Every writer to `hale_bus_state.json` — old and new — imports and uses this exact context manager:

| Writer | Status |
|---|---|
| `hale_bus_write.write_bus_state` / `append_channel_activity` | Pre-existing, now writes atomically (see §3) |
| `c2_fabric_write.record_channel_event` (new) | Uses `_locked_bus()` from `hale_bus_write` — no second lock |
| `hale_bus_handoff.HaleBusHandoff` (fixed this session, see §4) | Now uses `_locked_bus()` — previously had **no lock at all** |

**Decision: no SQLite WAL.** The proposal offered fcntl-or-WAL. WAL would be a second concurrency mechanism layered on a resource fcntl already owns — the two don't coordinate with each other, and a writer using WAL semantics while another uses fcntl gets no mutual exclusion at all. Single mechanism, shared by every writer, or none of this works.

**Why blocking, not non-blocking, for correctness:** the actual exclusion guarantee comes from `LOCK_EX` (blocking) inside every writer's critical section — this always eventually serializes. A non-blocking probe (`_probe_contention()` in `c2_fabric_write.py`) exists only to *count* contention as a metric; it is never used to decide whether to proceed, so a race in the probe itself can only under-count contention, never break exclusion.

---

## 3. Atomicity (the gap the prior commit left open)

The prior writers did `HALE_BUS_PATH.write_text(json.dumps(...))` **inside** the lock. That serializes writers against each other, but a single `write_text()` call is open→truncate→write→close — not atomic at the OS level. A reader with no lock (all reads in this system are lock-free by design, since reads are frequent and locking every read would add contention for no benefit) could observe a truncated or partially-written file mid-write.

**Fix:** `hale_bus_write._atomic_write_json(path, data)` writes to `path.with_suffix(f".tmp.{pid}")` in the same directory, then `os.replace(tmp, path)`. `os.replace` is atomic on POSIX (same filesystem, which this always is — same directory). A reader now always sees either the complete prior state or the complete new state, never a partial write. All writers (`write_bus_state`, `append_channel_activity`, `c2_fabric_write.record_channel_event`, `hale_bus_handoff`) now go through this helper.

---

## 4. Found and fixed mid-session: an unlocked, non-atomic writer already in production

While validating the new read path against the live bus, the `channel_activity` log (8 CI-probe canary entries present at session start) had gone empty. Root cause: `core/hale_bus/hale_bus_handoff.py`'s `HaleBusHandoff` class read-modify-writes the same `hale_bus_state.json` with **no lock and no atomicity** (`self.state_file.write_text(...)` directly). It is called from several always-on daemons: `keyword_auto_router.py`, `session_startup_keyword_router.py`, `claude_code_prompt_handler.py`, `opencode_keyword_dispatcher.py`. One of these raced the CI probe timer's locked/atomic write, read a stale snapshot, and overwrote it back — a textbook lost update, and exactly the failure mode Harlan's red-team review named ("four async processes writing the same JSON file simultaneously is a corruption trap").

**Fix (this commit):** every public method on `HaleBusHandoff` now runs its load→mutate→save as one critical section inside the shared `_locked_bus()`, and saves via `_atomic_write_json`. `self.state_file` now resolves to the same `HALE_BUS_PATH` constant `hale_bus_write.py` uses (env-override aware), so this class and the Phase 1 modules can never point at two different files under one lock. Verified: `python3 core/hale_bus/test_hale_bus.py` still passes; a manual smoke test against a scratch bus confirms `claim_work`/`add_fpd_alert`/`checkpoint_session` all round-trip correctly under the lock.

This was a real, live corruption path, not a hypothetical — closing it was necessary for Phase 1's "bus write-conflict rate = 0" claim to be true in production, not just true for the two modules named in the task.

---

## 5. New modules

### `core/hale_bus/c2_fabric_write.py`
`record_channel_event(channel, event_type, detail, ref=None, confirmed_delivered=False)` — atomic append to `channel_activity` (schema-compatible with the pre-existing `append_channel_activity`, so either writer's entries are readable by either reader) plus a `c2_channel_state[channel]` rollup (last event, timestamp, confirmed-delivery tag, running count) so a reader doesn't have to rescan the whole log for "what's Telegram's state right now."

Also maintains `c2_metrics`: `total_writes`, `lock_contention_events`, `write_conflict_rate`.

**Honesty note on `write_conflict_rate` (Sterling/Harlan's metric):** under this design it is **0 by construction**, not by detection — the exclusive lock means every writer's read-modify-write is one atomic critical section, so there is no window in which two writers can stomp on each other's update. The field is kept explicit (not omitted) so it's visible in the weekly sweep, and it would surface a regression if a future writer ever imports its own lock instead of `_locked_bus()` (as `hale_bus_handoff.py` had been doing until §4's fix) — but it is not itself an algorithm that detects and resolves conflicts. `lock_contention_events` (via `_probe_contention()`, a non-blocking probe taken immediately before every blocking acquire) is the real, meaningful concurrency signal: how often multiple writers are actually contending for the file. Under the 4-process concurrency test (§6) it read 49/50 — confirming contention is real and the lock is doing its job.

**Phase boundary:** `confirmed_delivered` is a structural tag only. Nothing reads it as an execute signal. That wiring is Phase 2 (confirmed-delivery auto-execute), explicitly out of scope here.

### `core/hale_bus/c2_fabric_read.py`
Read-only, no lock taken (safe because every writer now commits atomically — see §3). `get_channel_rollup(channel)` / `get_unified_channel_state()` give the per-channel latest-status view the flat activity log doesn't provide for free; falls back to scanning `channel_activity` for channels only ever written by the legacy `append_channel_activity` path. `get_c2_metrics()` and `unified_visibility_brief()` (a formatted, four-channel-in-one-call brief) round out the "single visibility ledger" the proposal's success criteria calls for.

---

## 6. Concurrency test: `core/hale_bus/test_c2_fabric_concurrency.py`

Spawns 4 real OS processes (`multiprocessing`, `fork` context — thread-based tests don't exercise `fcntl`'s process-level exclusion) against a **scratch** bus file (`HALE_BUS_STATE_PATH` env override; the production file is never touched by this test). Deliberately mixes the new writer (`c2_fabric_write.record_channel_event`, 2 workers) with the legacy writer (`hale_bus_write.append_channel_activity`, 2 workers) — a test of only the new path would say nothing about the real deployment, where both hit the same file. Each of the 4 workers writes 25 uniquely-tagged markers (100 total).

**Pass criteria:** every marker is present in the final file (no lost updates — the actual meaning of "0 conflicts"; valid JSON alone would pass even with silent data loss, which is exactly what happened in §4).

**Result:**
```
Expected markers: 100 | Found: 100 | Missing: 0
PASS — write_conflict_rate observed: 0.0000
c2_metrics after test: {"total_writes": 50, "write_conflict_rate": 0.0, "lock_contention_events": 49}
```
49/50 new-path writes registered contention from the probe — expected and correct under 4 concurrently-writing processes, and confirms the metric is measuring something real rather than always reading zero by omission.

---

## 7. What Phase 1 explicitly does not do

- No silence=GO / auto-execute wiring on any channel (Phase 2).
- No AgentMail bus-write privileges beyond the existing CI probe's rate-limited canary (Dembe's 30-day burn-in ask, unaddressed by design — that's Phase 3, gated).
- No change to the three Commander gates.
- Does not touch `core/email/channel_router.py` or `core/ops/confirmed_auto_execute.py` — these appear to be a separate, already-committed workstream (Phase 2-shaped: routing + confirmed-auto-execute) in progress elsewhere; out of scope for this Phase 1 pass and not modified here.

## 8. Verification run before commit
```
python3 core/hale_bus/test_hale_bus.py            # 4/4 passed (pre-existing suite, unaffected)
python3 core/hale_bus/test_c2_fabric_concurrency.py  # 100/100 markers, 0 lost updates
```
