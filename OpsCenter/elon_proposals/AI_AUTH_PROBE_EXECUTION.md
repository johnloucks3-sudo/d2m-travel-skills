# AI Auth Probe — Execution Record (2026-07-06)

**Root cause (confirmed via git history + proposal chain 2026-06-29 → 2026-07-02):**
`ai_auth_probe.py` classified transient network faults (ECONNRESET, timeouts) the
same as genuine auth failures and escalated/restarted the gateway on a single
blip. Commit `9df1d6d36` added retry/backoff but `escalate()` still fired on the
first unrecovered failure — no cross-cycle memory, no distinction between
"the network hiccuped" and "the token is actually dead."

## 1. Three-state classifier
`classify_probe_result(exc=None, http_status=None, message="")` → one of:

| State | Trigger |
|---|---|
| `HEALTHY` | HTTP 2xx |
| `AUTH_FAILED` | HTTP 400/401/403, or message contains `unauthorized`/`invalid oauth`/`invalid token`/`forbidden` |
| `TRANSIENT` | `socket.timeout`, `TimeoutError`, `subprocess.TimeoutExpired`, `ConnectionResetError`, `ConnectionRefusedError`, or `OSError` with errno in `{ECONNRESET, ETIMEDOUT, ECONNREFUSED, EHOSTUNREACH, ENETUNREACH, EPIPE}`, or message containing `econnreset`/`etimedout`/`connection reset`/`connection refused`/`timed out`/`timeout` |

Unknown failure shapes default to `AUTH_FAILED` (fail loud, don't silently
swallow a novel failure mode). All four probes (`probe_claude_oauth`,
`probe_opencode`, `probe_telegram`, `probe_mcp`) now return `(state, detail)`
using this classifier instead of ad hoc string-prefix checks scattered
through `run_probe_cycle()`.

## 2. Service-liveness precheck
`check_network_liveness()` — one TCP handshake to `1.1.1.1:443` (3s timeout),
run **once per cycle**, before any auth probe executes. If it fails, the
entire cycle is skipped (`network_down_skip` for every component) — no
probes run, no repairs attempt, no escalations fire. Rationale: if the
network path is down, every component would fail identically; testing and
possibly escalating on each one individually is the same false alarm N times.

## 3. Two-strike gate (persistent across the 15-min timer's process boundary)
State file: `OpsCenter/.ai_auth_probe_state.json` (atomic write, fcntl-locked,
`{component: {"consecutive_auth_fail": N}}`).

- `HEALTHY` → counter reset to 0.
- `TRANSIENT` → counter untouched, no repair attempted, no escalation.
- `AUTH_FAILED` → repair attempted; if repair+re-probe still `AUTH_FAILED`,
  counter increments.
  - Strike 1 → logged only (`STRIKE 1/2`).
  - Strike 2+ → `escalate()` fires, `attempts` = live strike count.

`STRIKE_THRESHOLD = 2` in `ai_auth_probe.py`.

## Test results (2026-07-06, live)

**Classifier unit test** (`python3 -c` inline, all assertions passed):
```
HEALTHY http200: HEALTHY
AUTH 401/403/400: AUTH_FAILED
TRANSIENT socket.timeout / ConnectionResetError / subprocess.TimeoutExpired: TRANSIENT
TRANSIENT msg econnreset / etimedout: TRANSIENT
AUTH msg unauthorized: AUTH_FAILED
network liveness: (True, 'network reachable')
```

**Two-strike gate simulation** (fake component forced to `AUTH_FAILED` twice):
```
cycle1: strike_logged   (state file: consecutive_auth_fail = 1)
cycle2: escalated       (state file: consecutive_auth_fail = 2)
```
Confirms: fail once → log only, no page. Fail twice consecutively → escalates
with the correct attempt count. Test incident purged from
`hale_incident_queue.jsonl` before the live run (fake `unit_test_component`
entry, not a real event).

**Live run** — `systemctl --user start ai-auth-probe.service` (exit 0, journal
clean):
```
TRANSIENT: claude_oauth — transient: there's an issue with the selected model... (no repair, no strike, retry next cycle)
OK: telegram
OK: mcp_server
cycle complete: {'claude_oauth': 'transient_skip', 'telegram': 'ok', 'mcp_server': 'ok'}
```
`claude_oauth` hit a model-availability hiccup, correctly classified
`TRANSIENT` (not escalated, not counted as a strike) — this is exactly the
failure mode that used to false-page under the old logic. `telegram` and
`mcp_server` probed genuinely healthy. Final state file: all counters at 0.

## Files changed
- `/home/john/Thunderbird/OpsCenter/ai_auth_probe.py` (full rewrite of
  classification + escalation logic; probe/repair function bodies otherwise
  unchanged)
- New: `/home/john/Thunderbird/OpsCenter/.ai_auth_probe_state.json` (gitignored
  runtime state, created on first run)

**Not in scope, noted for later:** the probe log has duplicate lines per
cycle — `log()` writes to `logs/ai_auth_probe.log` directly, and the systemd
unit's `StandardOutput=append:` points at the same file, so each `print()`
line lands twice. Pre-existing, unrelated to this fix.
