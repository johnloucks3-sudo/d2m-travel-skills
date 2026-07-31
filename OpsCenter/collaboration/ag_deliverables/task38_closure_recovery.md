AG-BUILD DONE: Recovered 37 lost TCD closures using the writeback.set_override API.

Talon, here's the independent read on this: 

I wrote and executed the recovery script (`scripts/recover_lost_tcd_closures.py`). It parses `hale_decisions.md` for `TCD-CLOSE` on `2026-07-29` and safely pushes them to the overrides config using the existing locking API. 

**Math Clarification (The ~122 lost approvals gap):**
The audit trail does indeed have 150 lines containing `TCD-CLOSE` for `2026-07-29`. However, the exact log format means each single closure generates exactly **two** lines:
1. `<!-- PLAN:CLOSE plan_id=TCD-CLOSE-{id}-{timestamp} ... -->`
2. `**Plan Closed:** TCD-CLOSE-{id}-{timestamp}`

So 150 lines exactly represents 75 total closures. Among those 75 closures, only **38 unique items** were being closed (due to duplicate/race-condition logging of the same items). Of those 38, `1` (`gmail-johnloucks3-19faef2b29e32ace`) had already safely survived in `tcd_stage_overrides.json`, so the script newly added exactly **37** missing closures.

### Acceptance Criteria Walkthrough

**1. Compilation & Dry Run:**
```bash
$ python3 -m py_compile scripts/recover_lost_tcd_closures.py
$ python3 scripts/recover_lost_tcd_closures.py --dry-run
Found 38 unique TCD-CLOSE closures on 2026-07-29 in audit trail.
[DRY-RUN] Using temporary file: /tmp/tmpkvtvji30/tcd_stage_overrides.json
Would newly add 37 closures.
Done writing.
Total keys now: 48
```

**2. Real Run:**
```bash
$ python3 scripts/recover_lost_tcd_closures.py
Found 38 unique TCD-CLOSE closures on 2026-07-29 in audit trail.
[REAL-RUN] Using real file: /home/john/Thunderbird/config/tcd_stage_overrides.json
Would newly add 37 closures.
Done writing.
Total keys now: 48
```

**3. Verification of pre-existing keys & total count:**
```bash
$ python3 -c "import json;d=json.load(open('config/tcd_stage_overrides.json'));print('total keys:',len(d))"
total keys: 48
```
All 11 pre-existing keys survived intact:
- `mission-MISSION-747` (stage: P)
- `watch-prediction-ledger-stale` (stage: P)
- `gmail-johnloucks3-19faef2b29e32ace` (status: Closed)
- `mission-MISSION-720` (stage: P)
- `gmail-d2mconcierge-19fa953527c588d7` (stage: P)
- `gmail-d2mconcierge-19fa948a70185600` (stage: P)
- `gmail-d2mconcierge-19fa94441cbf83f7` (stage: P)
- `gmail-d2mconcierge-19fa9426d1dead1f` (stage: P)
- `gmail-d2mconcierge-19fa8ccd0a9fcb80` (stage: P)
- `alert-LOUCKS-3122006-FPD-ALERT` (stage: P)
- `elon-verify-latest` (stage: P)

**4. Idempotency Check:**
```bash
$ python3 scripts/recover_lost_tcd_closures.py
Found 38 unique TCD-CLOSE closures on 2026-07-29 in audit trail.
[REAL-RUN] Using real file: /home/john/Thunderbird/config/tcd_stage_overrides.json
Would newly add 0 closures.
Done writing.
Total keys now: 48
```
