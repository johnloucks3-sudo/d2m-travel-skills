AG-BUILD DONE: engine_limits.py and test suite written and passing.

**Acceptance Criteria output:**

1. Compilation and tests:
```bash
$ python3 -m py_compile core/relay/engine_limits.py && python3 -m pytest tests/test_engine_limits.py -x 2>&1 | tail -20
============================= test session starts ==============================
platform linux -- Python 3.13.13, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/john/Thunderbird
plugins: anyio-4.12.1
collected 6 items

tests/test_engine_limits.py ......                                       [100%]

============================== 6 passed in 0.05s ===============================
```

2. Independence test (from `test_independence`):
After recording `cap_hourly` (30) calls for 'OC', `check_headroom('OC')` correctly returns `ok=False`. `check_headroom('AG')` returns `ok=True` and `hour_used` = 0.

3. Missing/corrupt ledger test (from `test_corrupt_ledger` and `test_missing_ledger` and `test_never_crash`):
`usage` returns `{'hour': 0, 'day': 0}` safely without crashing. Exceptions from unwritable directory or bad JSON are cleanly bypassed.

4. Git status:
```bash
$ git status --porcelain core/relay/engine_limits.py tests/test_engine_limits.py
?? core/relay/engine_limits.py
?? tests/test_engine_limits.py
```

Code is isolated as requested, uses stdlib only, and is ready for you to wire up in dispatch. Let me know if you need anything else!
