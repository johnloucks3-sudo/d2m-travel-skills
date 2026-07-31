# Task: fail-closed telemetry + 5-hour window awareness in core/ops/thunderbird_rate_limit_guard.py

## Context
File: `/home/john/Thunderbird/core/ops/thunderbird_rate_limit_guard.py`

Two confirmed defects:

**M2 — fails open.** `get_weekly_pct()` (currently ~line 112) shells out to
`ccusage weekly --json`. That command reliably crashes with a Node V8 out-of-memory error and
never returns valid JSON. On ANY failure (non-zero exit, empty weeks, or exception),
`get_weekly_pct()` currently returns `(0.0, 0)` — indistinguishable from "you've used nothing."
This must fail CLOSED instead: unknown usage must never be reported as zero usage.

**M3 — wrong constraint modelled.** The guard only tracks a weekly percentage. The Anthropic
account's 5-hour rolling window (a real, separate constraint) is not modelled anywhere in this
file, even though a WORKING live feed for it already exists on this machine at
`~/.claude/hud/.usage-cache.json`, refreshed every 60 seconds by an existing, unrelated tool.
That file's shape (real example):
```json
{"timestamp":1785475429827,"data":{"fiveHour":93,"fiveHourResets":"2026-07-31T06:59:59.769Z","sevenDay":6,"sevenDayResets":"2026-08-07T02:59:59.769Z"},"error":false}
```
`fiveHour` and `sevenDay` are already percentages (0–100), not raw token counts.

## Changes required (exact)

1. `get_weekly_pct() -> tuple[float | None, int]`: change every failure return from `(0.0, 0)` to
   `(None, 0)`. Update the docstring to say "Returns (None, 0) on failure — None means UNKNOWN,
   never treat it as zero."

2. Add three new module-level constants near the existing `THRESH_*` constants:
   ```python
   FIVE_HOUR_WARN = 70    # % — 5h window heads-up
   FIVE_HOUR_CRIT = 85    # % — 5h window graceful degradation engages
   FIVE_HOUR_STOP = 90    # % — 5h window hard guard
   ```

3. Add a new function, placed near `get_weekly_pct`:
   ```python
   def get_five_hour_pct() -> Optional[float]:
       """Read the live 5-hour OAuth usage % from the existing HUD cache
       (~/.claude/hud/.usage-cache.json), refreshed every 60s by an unrelated tool.
       Returns None if the file is missing, unreadable, malformed, reports an error,
       or is missing the fiveHour figure — never guess.
       """
   ```
   Implement it to read `Path.home() / ".claude" / "hud" / ".usage-cache.json"`, return `None`
   on any exception or if `data.get("error")` is truthy or `data["data"]["fiveHour"]` is absent,
   else return `float(data["data"]["fiveHour"])`.
   Define the cache path as a MODULE-LEVEL constant (e.g. `HUD_CACHE_PATH = Path.home() / ...`)
   rather than inline in the function, so it can be monkeypatched in tests.

4. `_compute_target_state(pct, sonnet_pct=0.0, five_hour_pct=None) -> GuardState`: change the
   signature to accept the new `five_hour_pct` parameter (default `None` for backward
   compatibility with any other caller). New logic, in this precedence:
   - If `pct is None` (weekly figure unknown): treat as at least CRIT severity for the weekly
     axis (fail closed — never let an unknown weekly reading resolve to NORMAL or WARN).
   - Compute the severity implied by `sonnet_pct` as today (SONNET_STOP/SONNET_CRIT).
   - Compute the severity implied by `five_hour_pct`: if `five_hour_pct is None`, treat as at
     least WARN severity (unknown 5h reading must never resolve all the way down to NORMAL);
     if not None, apply `FIVE_HOUR_STOP`/`FIVE_HOUR_CRIT`/`FIVE_HOUR_WARN` the same way the
     existing `THRESH_STOP`/`THRESH_CRIT`/`THRESH_WARN` apply to `pct`.
   - The function's return value is the MOST SEVERE state implied by any of: the weekly-pct
     axis, the sonnet-pct axis, the five-hour-pct axis. (Severity order, least to most severe:
     ROLLBACK < NORMAL < WARN < CRIT < STOP. ROLLBACK only applies when `pct` is known and
     `pct < THRESH_ROLLBACK` — an unknown `pct` can never produce ROLLBACK.)
   - Preserve existing behavior for the case where `pct` is a known float and `five_hour_pct` is
     a known float both comfortably below WARN: result must still be NORMAL (do not make this
     stricter than today for the fully-healthy case).

5. `tokens_remaining(used_pct)`: guard against `used_pct is None` — return `0` in that case
   (conservative: unknown remaining is treated as none remaining) instead of raising `TypeError`.

6. `evaluate(send_alerts: bool = True) -> dict`:
   - Call `get_five_hour_pct()` and pass it into `_compute_target_state`.
   - Store the result under a new key `"last_five_hour_pct"` in `state_data` (alongside the
     existing `last_pct`/`last_total`), and include `"five_hour_pct"` in the dict this function
     returns.
   - `_alert_message(...)` currently does `min(int(used_pct / 5), 20)` to build a progress bar —
     this will raise `TypeError` if `used_pct` is `None`. Guard it: if `used_pct is None`, render
     that line as `"All models weekly: [UNKNOWN — telemetry unavailable]"` instead of computing a
     bar. Add a similar line reporting the 5-hour figure (or "UNKNOWN" if `None`) beneath the
     existing weekly line.

## Explicit exclusions
- Do NOT change `WEEKLY_LIMIT_ALL`, `SONNET_*` constants, or `get_sonnet_weekly_pct()`.
- Do NOT change the CLI block at the bottom (`if __name__ == "__main__":`).
- Do NOT call `evaluate()` for real during testing — it writes to the REAL state file at
  `/home/john/Thunderbird/config/rate_guard_state.json`, which is live production state the
  Commander's wing reads. Never overwrite it as a side effect of testing your change.
- Do NOT send a real Telegram message while testing (`_send_telegram` must not be invoked for
  real; if you test `_alert_message`, only test the string it returns).

## Tests required — write ONE new file, do not modify any existing test file
Create `/home/john/Thunderbird/tests/test_rate_limit_guard_5h.py`. It must:
- Monkeypatch `thunderbird_rate_limit_guard.HUD_CACHE_PATH` (the module-level constant from
  step 3) to point at a file inside a `tempfile.mkdtemp()` directory — NEVER the real
  `~/.claude/hud/.usage-cache.json` — and assert `get_five_hour_pct()` correctly parses a
  `{"data": {"fiveHour": 93}, "error": false}` fixture written to that temp path, returning
  `93.0`.
- Assert that a missing file at that monkeypatched temp path makes `get_five_hour_pct()` return
  `None`.
- Assert that a fixture with `{"error": true}` makes `get_five_hour_pct()` return `None`.
- Assert `_compute_target_state(None, 0.0, None)` returns a state whose severity is CRIT or
  worse (i.e. `GuardState.CRIT` or `GuardState.STOP`) — proving the fail-closed behavior from
  step 4.
- Assert `_compute_target_state(5.0, 0.0, 93.0)` returns `GuardState.STOP` (5h STOP threshold
  wins even though weekly is healthy) — proving the "most severe axis wins" behavior.
- Assert `tokens_remaining(None) == 0`.
- MUST NOT import or call `evaluate()`, `load_state()`, or `save_state()` anywhere in this test
  file (those touch the real state file per the exclusion above).

## Acceptance criteria (mechanically checkable — run these yourself before reporting done)
Run from `/home/john/Thunderbird`:
```
python3 -m py_compile core/ops/thunderbird_rate_limit_guard.py     # must exit 0
python3 -m py_compile tests/test_rate_limit_guard_5h.py            # must exit 0
python3 -m pytest tests/test_rate_limit_guard_5h.py -q             # must exit 0, all tests pass
grep -c "def get_five_hour_pct" core/ops/thunderbird_rate_limit_guard.py   # must print 1
grep -c "FIVE_HOUR_CRIT" core/ops/thunderbird_rate_limit_guard.py          # must print 2 or more
```
Report the literal output of all five commands, including the full pytest pass/fail summary
line. If any command fails or does not match, say so plainly — do not report success.

## Reply path
- Write your modified file in place at
  `/home/john/Thunderbird/core/ops/thunderbird_rate_limit_guard.py` (absolute path — inside the
  repo you were given via `--add-dir`, not your sandbox).
- Write the new test file in place at `/home/john/Thunderbird/tests/test_rate_limit_guard_5h.py`.
- Also write a short deliverable to the ABSOLUTE path given to you separately, containing: the
  literal output of the five acceptance-criteria commands above (including the pytest summary
  line), and a one-line summary of what changed at each numbered point 1–6.
- Print a one-line verdict starting "AG DONE:".
