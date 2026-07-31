# Deliverable: Fix for Email-Handling Probe / Auto-Repair Mismatch

**Author:** Hale-AG (Gemini 3.6 Flash Engine)  
**Date:** 2026-07-31  
**Target:** `core/ci/ci_auto_repair_engine.py`, `core/ci/repairs/cluster_g.py`, `tests/test_repair_email_handling.py`

---

## 1. Executive Summary & Root Cause Fix

- **Root Cause:** The `ci_probe_email_handling.py` probe verifies freshness and delivery gap of `OpsCenter/state/d2m_digest_state.json`, which depends on `d2m-commander-digest.timer` running periodically. However, `repair_email_handling()` in `core/ci/ci_auto_repair_engine.py` previously only verified that Gmail OAuth token files existed on disk. When `d2m-commander-digest.timer` was disabled, `repair_email_handling()` declared success without enabling/starting the timer, causing an endless loop of AUTO_APPLIED repair attempts that failed post-repair probe verification.
- **Durable Fix Implemented:**
  1. Extended `repair_email_handling()` in `core/ci/ci_auto_repair_engine.py` to explicitly check if `d2m-commander-digest.timer` is enabled and active using `systemctl --user is-enabled` and `is-active`. If not, it executes `systemctl --user enable --now d2m-commander-digest.timer` via `subprocess.run`.
  2. Preserved existing credential token file presence checks.
  3. Added `d2m-commander-digest.timer` to `_EMAIL_TIMERS` in `core/ci/repairs/cluster_g.py` so cluster G's explore/assess/repair methods monitor and manage the digest timer.
  4. Added a dedicated pytest suite `tests/test_repair_email_handling.py` mocking `subprocess.run` to verify enable/start behavior, active timer bypass, and missing credential file failure handling.

---

## 2. What Changed & Why

### A. `core/ci/ci_auto_repair_engine.py`
- **Change:** Updated `repair_email_handling()` to check `d2m-commander-digest.timer` `is-enabled` and `is-active` states, and invoke `systemctl --user enable --now d2m-commander-digest.timer` if inactive or disabled.
- **Why:** Satisfies the operational dependency checked by `ci_probe_email_handling.py` while preserving existing token checks.

### B. `core/ci/repairs/cluster_g.py`
- **Change:** Added `"d2m-commander-digest.timer"` to `_EMAIL_TIMERS`.
- **Why:** Enables cluster G's assessment and repair plan generation to monitor and restart `d2m-commander-digest.timer`.

### C. `tests/test_repair_email_handling.py`
- **Change:** Created new test file with 3 test cases:
  - `test_repair_email_handling_disabled_timer_enables`: asserts that disabled timer triggers `systemctl --user enable --now d2m-commander-digest.timer`.
  - `test_repair_email_handling_active_timer_no_enable_needed`: asserts active timer avoids redundant enable calls.
  - `test_repair_email_handling_missing_tokens_fails`: asserts token presence validation is preserved.

---

## 3. Acceptance Criteria — Literal Outputs

### Command 1: `python3 -m py_compile core/ci/ci_auto_repair_engine.py core/ci/repairs/cluster_g.py tests/test_repair_email_handling.py`
```
Exit code: 0
Stdout: (empty)
Stderr: (empty)
```

### Command 2: `python3 -m pytest tests/test_repair_email_handling.py -q`
```
...                                                                      [100%]
3 passed in 0.05s
```

### Command 3: `git status --short core/ci/repairs/ scripts/d2m_commander_digest.py scripts/ci_probe_email_handling.py`
```
 M core/ci/repairs/cluster_g.py
```
*(Confirms `scripts/d2m_commander_digest.py` and `scripts/ci_probe_email_handling.py` were NOT touched, maintaining protected file guarantees.)*

---

## 4. Protected Files Audit

The 6 protected scanner/relay files and probe scripts were untouched:
- `OpsCenter/run_commander_directive_sweep.py` — UNTOUCHED
- `OpsCenter/dispatch_and_email.py` — UNTOUCHED
- `OpsCenter/email_task_ingest.py` — UNTOUCHED
- `core/email/thunderbird_commander_inbox.py` — UNTOUCHED
- `OpsCenter/relay_send.py` — UNTOUCHED
- `core/relay/wing_relay.py` — UNTOUCHED
- `scripts/d2m_commander_digest.py` — UNTOUCHED
- `scripts/ci_probe_email_handling.py` — UNTOUCHED

---

## 5. Tagged Findings & Uncertainty Assessment

- `[FINDING-1] [Confidence: High] [Severity: Low]`: `_EMAIL_TIMERS` in `cluster_g.py` was updated to include `d2m-commander-digest.timer`. This ensures Cluster G's `explore()` and `assess()` reflect digest timer status alongside OAuth keepalive timers.
- `[UNCERTAINTY-1] [Confidence: High] [Severity: Info]`: No live `systemctl` or digest runs were triggered during testing per explicit instructions. The repair logic was validated via mocked unit tests and static syntax compilation.
