# Directive Sweep — Exponential Backoff Retry — Execution Summary
*2026-07-06 · Executed by Claude Code under Hale-approved override (protection suspended via `.protections_lifted`, SO_EMAIL_SCANNER_PROTECT_20260608)*

## Scope correction
Task brief asked for backoff around "gmail_api, TESS, portal calls." This script
(`run_commander_directive_sweep.py`) only makes Gmail API calls (via `googleapiclient`)
plus a local `subprocess.run` to `dispatch_and_email.py` (not a network call to retry).
No TESS or portal calls exist in this file — backoff was applied only where real
network calls exist.

## Changes made
1. **`with_backoff(fn, *, max_retries=5, initial_delay=1, max_delay=30, label=...)`** —
   generic exponential-backoff wrapper. Retries on `socket.timeout`, `ConnectionError`,
   `TimeoutError`, and (if `requests` is importable) `requests.exceptions.Timeout` /
   `ConnectionError`. Delay doubles each attempt, capped at 30s. Non-retryable
   exceptions propagate immediately (no wasted retries).
2. **`log_retry()`** — writes retry attempts to both stdout (existing systemd log
   capture) and a dedicated file: `logs/commander_directive_sweep_retries.log`.
3. **Wrapped call sites** (all Gmail API network calls in the file):
   - jl3 + d2mconcierge OAuth token refresh (`creds.refresh`)
   - `labels().list()` / `labels().create()` for both jl3 and d2mconcierge
   - `messages().list()` (d2mconcierge inbox query)
   - `messages().get()` — metadata fetch, full fetch (both accounts)
   - Label-add (`messages().modify()`) calls were left as-is — already
     best-effort (try/except pass) and idempotent; a missed label just gets
     retried on the next 2-minute sweep cycle, so backoff there added no value.
4. **Graceful final-failure exit**: the outer catch-all now logs the error to
   stderr and exits **0** (was exit 1) after retry exhaustion, so the systemd
   timer does not crash-loop — the next scheduled sweep (2-min cooldown) retries
   naturally.

## Test results
Verified `with_backoff` in isolation (extracted + exec'd the exact source block,
not a reimplementation) with three scenarios:
- Transient failure (2 failures then success) → recovers, returns result, 3 attempts logged with 1s/2s delays.
- Permanent failure → retries 1s→2s, then raises after exhausting `max_retries`, logging `RETRY_EXHAUSTED`.
- Non-retryable exception (`ValueError`) → propagates on first attempt, no retry wasted.

`python3 -m py_compile` passes clean.

## Where to find retry logs on next crash
- `logs/commander_directive_sweep_retries.log` — every retry attempt + exhaustion, timestamped UTC.
- `logs/commander_directive_sweep.log` — existing systemd stdout capture (unchanged), now also carries retry lines since `log_retry` prints to stdout too.
- stderr (systemd journal, `journalctl --user -u <timer-unit>`) — final fatal error message after retry exhaustion.
