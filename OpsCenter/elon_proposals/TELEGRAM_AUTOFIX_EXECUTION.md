# Telegram Gateway — Auto-Heal Disabled for Diagnostic Window
*Executed 2026-07-06 16:03 MT*

## What was disabled

`thunderbird-telegram-gw.service` previously had two competing `Restart=` directives:
- Base unit: `Restart=always` (M-153 self-heal, restarts on any exit)
- Drop-in `resource-limits.conf`: `Restart=on-failure` (ELON Tier-1 hardening, overrides the base unit)

Added a new drop-in that sorts last alphabetically and wins the override:

```
/home/john/.config/systemd/user/thunderbird-telegram-gw.service.d/zz-disable-restart.conf
[Service]
Restart=no
```

Confirmed effective via `systemctl --user show thunderbird-telegram-gw.service -p Restart` → `Restart=no`.

**Effect:** if the process crashes or exits during the diagnostic window, systemd will NOT restart it. The service will show as `inactive`/`failed` and stay down until manually restarted. This is intentional — the goal is to catch the actual crash signature instead of having it silently self-heal.

**To restore auto-heal:**
```bash
rm /home/john/.config/systemd/user/thunderbird-telegram-gw.service.d/zz-disable-restart.conf
systemctl --user daemon-reload
systemctl --user restart thunderbird-telegram-gw.service
```

## Current status (at time of execution)

Service was `active (running)` since 15:47:19 MDT, PID 2008041, no crashes yet. Journal shows recurring
`TG API getUpdates exception: ... Read timed out (read timeout=35)` — these are long-poll timeouts, not crashes; the gateway's own retry loop handles them without process exit.

## How to monitor crash logs

Diagnostic capture script: `/home/john/Thunderbird/scripts/telegram_diagnostic_capture.sh`
Running in background (PID 2038590, `timeout 24h` wrapper), writing to:
`/home/john/Thunderbird/logs/telegram_diagnostic_20260706_160259.log`

Live tail:
```bash
tail -f /home/john/Thunderbird/logs/telegram_diagnostic_20260706_160259.log
```

Check whether the service is still up vs. has died and stayed down:
```bash
systemctl --user status thunderbird-telegram-gw.service --no-pager
```

If it dies during the window, the log will capture the exact exception/exit reason and systemd will NOT
mask it with an auto-restart — the failure state persists until someone looks at it.

## Next steps for Commander review

1. Let the 24h capture run (ends ~2026-07-07 16:03 MT).
2. Review `telegram_diagnostic_20260706_160259.log` for any crash/exit lines (vs. benign read-timeout retries).
3. If a real crash signature is found — root-cause it (auth expiry, unhandled exception, OOM) before re-enabling auto-heal, since `Restart=always`/`on-failure` will otherwise keep masking it.
4. Re-enable auto-heal by removing `zz-disable-restart.conf` once root cause is identified or the window closes with no crashes.
