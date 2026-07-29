# C2 RECALIBRATION — CROSS-HALE CERTIFICATION

| ITEM | PASS/FAIL | ACTUAL OUTPUT (TRUNCATED) |
|---|---|---|
| A1 (11 legacy timers absent) | PASS | (None matched in `systemctl --user list-timers --all`) |
| A2 (3 core timers active) | PASS | (Found `thunderbird-morning-consolidated`, `thunderbird-evening-consolidated`, `d2m-fpd-alert`) |
| A3 ('Wilco' ban check) | PASS | Both occurrences in `run_commander_directive_sweep.py` are within "BANNED — never emit these" instructions |
| B1 (No direct sends test) | PASS | `5 passed in 6.57s` |
| B2 (Scaffolding rejection) | PASS | `scaffolding leak: skill-loader scaffolding ('Base directory for this skill:') [...]` |
| B3 (Dedup function) | PASS | `queued suppressed` |
| B4 (Claims check) | PASS | `True False` |
| C1 (Close attribution) | PASS | `OK: close() missing 1 required keyword-only argument: 'by'` |
| C2 (Closure survives regen) | PASS | `closed: True` / `in regenerated queue: False` |
| D1 (Directive executor) | PASS | `trivial-groundtruth -> UNVERIFIED` / `empty-claims -> UNVERIFIED \| replies: True` |
| E1 (Slack unconfigured) | PASS | `SLACK_BOT_TOKEN missing. Add both tokens to /home/john/Thunderbird/.env` / `exit=2` |
| E2 (Slack service enabled) | PASS | `enabled` |

AG-CERT: CERTIFIED
