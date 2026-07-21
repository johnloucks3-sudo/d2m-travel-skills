# CI Lifecycle Sweeps Repair — 2026-07-21

**Issue:** `lifecycle-dossiers` and `lifecycle-booking-surveys` CI sweeps reported RED (client-affecting) with auto-repair failing.

**Root Cause Analysis (Systematic Debugging — Phase 1-2):**

Both probes showed stale pipelines (292h/286h ago, threshold 26h):
- `lifecycle-dossiers`: Last ran 2026-07-09 18:53 (13 days stale)
- `lifecycle-booking-surveys`: Last ran 2026-07-09 (13 days stale)

Investigation revealed:
1. **`d2m-dossier-freshness.service` pointed to wrong Python:** Used system `/usr/bin/python3` instead of venv
2. **`d2m-dossier-freshness.service` pointed to wrong script:** Ran `scripts/dossier_freshness.py` (writes to `logs/`, not the probe marker) instead of `core/ops/dossier_freshness.py` (writes `OpsCenter/logs/dossier_freshness.jsonl`, the probe's source-of-truth)
3. **`d2m-booking-survey.service` did not exist:** No systemd service or timer defined
4. **Missing logging:** Both services lacked `StandardOutput` and `StandardError` configuration, causing silent failures

**Sterling A7 Review (Independent Architecture Check):**
Confirmed the dossier script path was the root issue — the service was running a non-producer script. This created a flap loop: RED (probe watches unwritten file) → auto-repair fires → GREEN (temporary, until next 26h boundary) → cycle repeats indefinitely without a real producer running.

**Repairs Applied:**

### 1. Fixed `/home/john/.config/systemd/user/d2m-dossier-freshness.service`
```diff
- ExecStart=/usr/bin/python3 /home/john/Thunderbird/scripts/dossier_freshness.py
+ ExecStart=/home/john/Thunderbird/.venv/bin/python3 /home/john/Thunderbird/core/ops/dossier_freshness.py
+ StandardOutput=append:/home/john/Thunderbird/logs/d2m-dossier-freshness.log
+ StandardError=append:/home/john/Thunderbird/logs/d2m-dossier-freshness.log
+ Environment=PYTHONPATH=/home/john/Thunderbird
```

### 2. Created `/home/john/.config/systemd/user/d2m-booking-survey.service`
```ini
[Unit]
Description=D2M — booking survey generator
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/home/john/Thunderbird
EnvironmentFile=-/home/john/Thunderbird/.env
ExecStart=/home/john/Thunderbird/.venv/bin/python3 /home/john/Thunderbird/scripts/booking_survey_generator.py
StandardOutput=append:/home/john/Thunderbird/logs/d2m-booking-survey.log
StandardError=append:/home/john/Thunderbird/logs/d2m-booking-survey.log
Environment=PYTHONPATH=/home/john/Thunderbird
```

### 3. Created `/home/john/.config/systemd/user/d2m-booking-survey.timer`
```ini
[Unit]
Description=Booking survey generator — daily 06:00 MDT

[Timer]
OnCalendar=*-*-* 06:00:00 America/Denver
Persistent=true

[Install]
WantedBy=timers.target
```

### 4. Reloaded systemd
```bash
systemctl --user daemon-reload
systemctl --user enable d2m-booking-survey.timer
```

**Verification (Fresh Evidence — 2026-07-21 17:10 MT):**

✅ **Dossier probe:** GREEN, exit 0
  - Pipeline ran 6.1h ago (within 26h threshold)
  - Marker file `OpsCenter/logs/dossier_freshness.jsonl` written at 17:07:22 (just verified)
  - Contains audit with stale dossier detection

✅ **Booking-survey probe:** GREEN, exit 0
  - Ran 4+ minutes ago
  - State file `OpsCenter/state/booking_survey_state.json` updated

✅ **Both services:** Exit code 0/SUCCESS
  - Running with correct venv Python
  - Logging configured

✅ **Both timers:** Enabled and scheduled
  - Dossier: 05:30 MT daily
  - Booking-survey: 06:00 MT daily

**Outstanding Items (Sterling A7 Charter):**
1. Retire dead script: `scripts/dossier_freshness.py` (dead code — globs `*.json`, posts revoked Telegram token)
2. Add producer↔marker↔timer consistency check to CI registry lint
3. Monitor: Ensure dossier probe stays GREEN without auto-repair for 7 consecutive days (no flap)
4. Future: Widen survey probe staleness margin from 25h to 26–27h (currently 1h safety margin)

**Owner:** A7 (process/metrics) — daily audit rollup starting 2026-07-22
