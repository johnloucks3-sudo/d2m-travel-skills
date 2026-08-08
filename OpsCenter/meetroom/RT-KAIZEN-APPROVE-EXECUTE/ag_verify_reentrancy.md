# KAIZEN Runner Re-entrancy & Concurrency Audit (Cross-Engine Check: HALE-AG)
**Target:** `core/relay/task_templates.py` (`acquire_runner_lock`, `claim_ticket`, `reclaim_orphans`), `scripts/kaizen_runner.py`, `scripts/kaizen_runner_oc.py`.
**Auditor:** HALE-AG (Gemini 3.6 Flash)
**Date:** 2026-08-08

---

## 1. Concurrency Analysis
1. **Runner-Level Process Mutex (`acquire_runner_lock`)**:
   - Uses `fcntl.flock(fh, LOCK_EX | LOCK_NB)` on `/tmp/kaizen-runner-{seat}.lock`.
   - Two concurrent instances of the *same* runner (e.g. cron overlap or dual invocation) cannot execute simultaneously; the second immediately aborts.
2. **Cross-Seat Ticket Separation**:
   - `kaizen_runner.py` filters strictly for `seat == "CC"`.
   - `kaizen_runner_oc.py` filters strictly for `seat == "OC"`.
   - CC and OC runners scan disjoint subsets of tickets.
3. **Pre-Dispatch Claiming (`claim_ticket`)**:
   - Sets `status = "in_progress"` with UTC `claimed_at` before dispatching the subprocess.
   - Any sequential scan in subsequent runs sees `status != "open"` and skips.
4. **Orphan Recovery (`reclaim_orphans`)**:
   - Recovers stuck `in_progress` tickets only after `2 * timeout_s` elapsed.
   - Transitions directly to `status = "blocked"` (never back to `open`).
   - Orphaned tickets are never re-dispatched.

## 2. Potential Edge Cases & Failure Modes (Audited)
- **Subprocess Timeout vs Parent Exit:** `subprocess.run(timeout=timeout_s)` raises `TimeoutExpired` inside the lock-holding process; the exception handler synchronously marks the ticket `blocked`. The lock is held throughout.
- **Flock Lock File Truncation (`open(lock_path, "w")`):** Truncation does not drop an active flock held by another process on Linux (inode-bound). Non-blocking flock safely fails on the open fd.
- **Ticket Overwrites / Manual Edits:** `claim_ticket` overwrites disk before dispatch. No dual dispatch possible under non-corrupted disk states.

---

## 3. Verdict
**PASS.** No viable scenario identified where a ticket is dispatched or executed twice under the audited lock + claim + reclaim architecture.
