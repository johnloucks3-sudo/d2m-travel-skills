# Deliverable: M2 & M3 Rate Guard Fixes

## 1. Summary of Changes (Points 1–6)
1. `get_weekly_pct()`: Updated return type annotation to `tuple[Optional[float], int]`, changed all failure return statements from `(0.0, 0)` to `(None, 0)` to fail closed on broken telemetry, and updated docstring to document `None` as UNKNOWN.
2. Constants: Added module-level constants `FIVE_HOUR_WARN = 70`, `FIVE_HOUR_CRIT = 85`, `FIVE_HOUR_STOP = 90`, and `HUD_CACHE_PATH = Path.home() / ".claude" / "hud" / ".usage-cache.json"`.
3. `get_five_hour_pct()`: Added function reading live 5-hour usage % from `HUD_CACHE_PATH`, returning `None` if missing, unreadable, malformed, reporting an error, or missing `fiveHour`.
4. `_compute_target_state()`: Added `five_hour_pct` parameter (default `None`), implemented fail-closed handling for `pct is None` (evaluates to CRIT) and `five_hour_pct is None` (evaluates to WARN), and selected the most severe state across weekly, sonnet, and 5-hour axes (`ROLLBACK < NORMAL < WARN < CRIT < STOP`).
5. `tokens_remaining()`: Added guard for `used_pct is None`, returning `0` tokens remaining instead of raising `TypeError`.
6. `evaluate()` & `_alert_message()`: Updated `evaluate()` to fetch and pass `five_hour_pct` to state computation and save `last_five_hour_pct` in state data; updated `_alert_message()` to gracefully render `[UNKNOWN — telemetry unavailable]` for `None` values and include 5-hour window usage.

## 2. Acceptance Criteria Verification

### Command 1: Py_compile guard module
```
$ python3 -m py_compile core/ops/thunderbird_rate_limit_guard.py
(exit code: 0)
```

### Command 2: Py_compile test suite
```
$ python3 -m py_compile tests/test_rate_limit_guard_5h.py
(exit code: 0)
```

### Command 3: Pytest test suite
```
$ python3 -m pytest tests/test_rate_limit_guard_5h.py -q
......                                                                   [100%]
6 passed in 0.08s
(exit code: 0)
```

### Command 4: Grep `get_five_hour_pct`
```
$ grep -c "def get_five_hour_pct" core/ops/thunderbird_rate_limit_guard.py
1
```

### Command 5: Grep `FIVE_HOUR_CRIT`
```
$ grep -c "FIVE_HOUR_CRIT" core/ops/thunderbird_rate_limit_guard.py
2
```
