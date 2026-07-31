# Task: fix repair/probe mismatch in the "email-handling" CI auto-repair skill

## Context — root cause already confirmed, this is a fix task, not investigation

The Commander was paged hourly for 7+ hours by `🔴 COMMANDER ACTION REQUIRED — ci-rapid-repair/
AUTO_APPLIED:email-handling failed. Auto-repair unsuccessful ... verify still RED — escalating`.

**Root cause, already found and the immediate symptom already resolved (do not redo this
investigation):**
- The probe `scripts/ci_probe_email_handling.py` checks freshness + delivery-gap of
  `/home/john/Thunderbird/OpsCenter/state/d2m_digest_state.json`, written by
  `scripts/d2m_commander_digest.py` (systemd unit `d2m-commander-digest.timer`/`.service`, meant
  to run once daily at 14:05 MT).
- That timer was found DISABLED (confirmed via `systemctl --user is-enabled
  d2m-commander-digest.timer` → `disabled`). It had not fired since 2026-07-28 — 3 days of no
  digest runs, so the probe's staleness check (26h window) tripped RED and stayed RED.
- The SAFE auto-repair action for this skill, `repair_email_handling()` in
  `core/ci/ci_auto_repair_engine.py` (~line 222), does NOT touch this timer at all — it only
  checks that Gmail OAuth token FILES exist on disk (a completely different failure mode). So
  every `AUTO_APPLIED` cycle "succeeded" at its own narrow check, then re-ran the probe, which
  checks something the repair never touched — hence "applied but verify=RED" on every single
  cycle, forever, by construction. This is a structural mismatch between what the repair fixes
  and what the probe verifies, not a flaky/intermittent bug.
- I (CC) already ran `systemctl --user enable --now d2m-commander-digest.timer` directly as an
  emergency unblock — confirmed live: the courier ran immediately, delivered 3 real digest items,
  wrote a fresh state entry, and `python3 scripts/ci_probe_email_handling.py` now exits 0
  (`RAZOR_SHARP`). The immediate client-affecting alert storm is stopped. **Do not re-verify this
  part or re-run the courier — it already ran for real and delivered real email; running it again
  is not idempotent-safe to repeat casually.**

**What is NOT yet fixed, and is your actual task:** the auto-repair system will make the exact
same mistake again the next time this timer gets disabled (by a future bug, a bad edit, a manual
mistake) — because `repair_email_handling()` still doesn't touch the timer that the probe actually
depends on. Fix that structural gap.

## What to actually do

1. Read `core/ci/ci_auto_repair_engine.py`'s `repair_email_handling()` (~line 222) and
   `core/ci/repairs/cluster_g.py`'s email-handling wrapper (~line 214 onward — this wraps
   `repair_email_handling` per the file's own "PRESERVE-INTERNALS RULE: all apply-paths wrap
   existing, tested repair_<skill> bodies by import — no drift, no duplication" comment, and its
   "PROTECTED-FILE GUARANTEE (SO 2026-06-08)" which lists exactly which files
   `email-handling` repair may NEVER modify — read this list, it still applies).
2. Extend `repair_email_handling()` to ALSO check and fix the actual condition the probe verifies:
   is `d2m-commander-digest.timer` enabled and active? If not, enable and start it
   (`systemctl --user enable --now d2m-commander-digest.timer` via `subprocess.run`, matching the
   existing style in this file — check how other repair functions in this same file invoke
   `systemctl` for a consistent pattern, e.g. search for `systemctl` calls elsewhere in
   `core/ci/ci_auto_repair_engine.py`). Keep the existing token-file check too — do not remove it,
   both failure modes are real, just currently only one of them is actually checked by the probe.
3. This must stay a SAFE-tier repair per the existing doc comment ("email-handling SAFE (timer
   restart) / DESTRUCTIVE (creds file missing)") — enabling/starting a timer is exactly the
   "timer restart" the SAFE tier already promises in its own docstring, so this is filling in
   documented-but-never-implemented behavior, not expanding scope.
4. Do NOT modify any of the 6 protected files listed in cluster_g.py's PROTECTED-FILE GUARANTEE.
   Do NOT touch `d2m_commander_digest.py`, `ci_probe_email_handling.py`, or the timer/service unit
   files themselves — only the repair function's Python logic.
5. Write a unit test (new file `tests/test_repair_email_handling.py`) that: (a) monkeypatches or
   mocks the `subprocess.run` call so no REAL systemctl command executes during the test, (b)
   asserts that when the mocked "is the timer enabled" check reports `disabled`, the repair
   function attempts to enable it (assert the mock was called with the right systemctl args), (c)
   asserts the existing token-file check behavior is unchanged (still checks the same paths).

## Explicit exclusions
- Do NOT re-run `d2m-commander-digest.timer`, `d2m_commander_digest.py`, or
  `ci_probe_email_handling.py` for real during testing — they send a real email digest / touch
  real state. Test only with mocked `subprocess.run` calls.
- Do NOT modify any of the 6 protected files named in cluster_g.py.
- Do NOT touch the anti-flap/circuit-breaker logic (`BLOCKED_COOLDOWN`/`BLOCKED_CIRCUIT` in
  `logs/ci_rapid_repair.log` — that's a different module, working as designed, out of scope).

## Acceptance criteria (mechanically checkable — run these yourself)
```
python3 -m py_compile core/ci/ci_auto_repair_engine.py core/ci/repairs/cluster_g.py tests/test_repair_email_handling.py
python3 -m pytest tests/test_repair_email_handling.py -q
git status --short core/ci/repairs/ scripts/d2m_commander_digest.py scripts/ci_probe_email_handling.py   # confirm only cluster_g.py (if touched) shows, and the two named scripts show NO changes
```
Report the literal output of all three.

## Reply path
- Write your fix in place, plus the new test file.
- Write a deliverable to the ABSOLUTE path given to you separately: what changed and why, the
  literal acceptance-criteria output, and any uncertainty (tagged, not filtered).
- Print a one-line verdict starting "AG DONE:".
