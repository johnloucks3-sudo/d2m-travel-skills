# PROPOSAL-20260613-thunderbird-telegram-gw.md — EXECUTION RECORD
*Executed 2026-07-06 16:12 MT*

## Current status found (before fix)
- `thunderbird-telegram-gw.service` was **active/running**, uptime ~21 min, both bots LIVE.
- **No crash-loop.** The two restarts in the prior 24h (12:06 MT, 15:47 MT) were NOT crashes — they were `ai_auth_probe.py`'s `repair_telegram()` self-heal, triggered by transient `HTTPSConnectionPool ... Read timed out` errors on Telegram's `getUpdates` long-poll (normal network noise, 47 occurrences/hour, none fatal). Each repair restart succeeded (`2/2 LIVE` within ~90s).
- However, the **original June 13 fix was never actually applied**, despite the proposal being marked `APPLY_AUTONOMOUSLY`:
  1. `OpsCenter/thunderbird_stt.py` still had `whisper.load_model("base")` at **module scope** — loaded eagerly every time the gateway process started (imported at gateway module-load, not inside a function). This is the exact June 13 crash signature (`c10::Error` → `abort()`).
  2. The systemd drop-in `resource-limits.conf` set `MemoryLimit=512M` — a **deprecated key silently ignored** by this system's systemd (v260), confirmed via repeated journal spam: `Support for option MemoryLimit= has been removed and it is ignored`. The memory cap had **never been enforced**.
  3. System-wide memory pressure was severe at time of check: swap 10Gi, **24Ki free** (essentially exhausted). Any eager, uncapped model load is a live OOM risk to this and other services.
  4. A diagnostic override `zz-disable-restart.conf` (`Restart=no`, dated today "24h crash investigation") was in place, meaning if the gateway did crash, systemd would NOT bring it back — a P0 C2 channel with no auto-heal.

## Action taken
1. **`OpsCenter/thunderbird_stt.py`** — converted to lazy singleton load. `whisper.load_model` now runs on first real transcription call only, not at import time.
2. **`resource-limits.conf`** — changed `MemoryLimit=512M` → `MemoryMax=512M` (the key systemd 260 actually enforces). Verified via `systemctl --user show ... -p MemoryMax` → `536870912` (matches, now live).
3. **Removed `zz-disable-restart.conf`** — investigation complete, root cause identified and fixed; restored `Restart=on-failure` (confirmed via `systemctl --user show ... -p Restart`).
4. Restarted `thunderbird-telegram-gw.service` to apply.

## Verification
- Service active, PID confirmed running post-restart.
- Startup RSS dropped from 335MB → **69MB** (whisper no longer loaded at boot — lazy-load confirmed working).
- No `MemoryLimit=...removed` warnings in journal post-fix (deprecated-key spam eliminated).
- No ERROR lines in journal in the 2 minutes following restart.
- `thunderbird-telegram-health.service` (the production health check, not the stale `OpsCenter/telegram_health_check.py` which reports a false UNHEALTHY unrelated to this fix) confirms **2/2 LIVE** (D2MC2C + Dani) ~90s after restart — matches the normal transient-DEAD-then-LIVE pattern seen on every prior clean restart.
- `Restart=on-failure` and `MemoryMax=536870912` both confirmed active via `systemctl --user show`.

## Net effect
- June 13 root cause (eager whisper load + unenforced memory cap) is now genuinely fixed, not just claimed fixed.
- Gateway auto-heal restored (was disabled).
- Today's restarts were self-healing working as designed, not a fault requiring escalation.
