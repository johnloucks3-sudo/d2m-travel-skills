# Task 43 — Hardcoded Statistic (Fabricated Number) — Complete

## Summary
Replaced hardcoded `"181"` (the TCD active stage override count) in the daily audit report with a live count pulled from `tcd.overrides.load_overrides()`.

## File Changed
- `core/ops/gauge_eod_audit_engine.py` (lines 107, 121)

## What Was Fixed
Two prose lines — one Markdown, one HTML — had `"181"` hardcoded when the variable `tcd` already carried `active_stage_overrides` from a line-56 call. Both now use `{tcd.get('active_stage_overrides', 0)}`.

## Verification
| Check | Result |
|---|---|
| `py_compile` | exits 0 |
| `grep -c '181'` engine file | 0 |
| Live count in report | 13 (matches `load_overrides()`) |

## Constraints Respected
- `config/tcd_stage_overrides.json` and `tcd/overrides.py` untouched
- No new dependencies
- Existing `tcd` dict reused, no extra I/O
