# PROPOSAL-20260607 (thunderbird-telegram-gw-root-cause) — Execution Report
*Executed 2026-07-06 16:11 MT*

## Finding: Phase 1 was already in progress when this task started

A concurrent/prior session had already executed Phase 1 of this proposal 4 minutes before this
task began — see `TELEGRAM_AUTOFIX_EXECUTION.md` (timestamped 16:03 MT). That work:

- Added `/home/john/.config/systemd/user/thunderbird-telegram-gw.service.d/zz-disable-restart.conf`
  (`Restart=no`), overriding both the base unit's `Restart=always` and the `resource-limits.conf`
  drop-in's `Restart=on-failure` — confirmed via `systemctl --user show ... -p Restart` → `Restart=no`.
- Started a 24h journal capture to `logs/telegram_diagnostic_20260706_160259.log`.

## Gap found and fixed

The diagnostic capture had been launched as a plain background bash job tied to the prior session's
shell. That session ended and killed the capture ~7 minutes into the 24h window (log stopped
growing at 16:10:08 despite `timeout 24h`). This would have silently produced an empty diagnostic
window — exactly the kind of masked failure this proposal exists to prevent.

**Fix applied:** relaunched the same capture command as a detached `systemd-run --user` transient
unit (`telegram-diag-capture.service`, PID 2108327), which survives independent of any single CLI
session. Verified `active (running)` via `systemctl --user status`.

```bash
systemd-run --user --unit=telegram-diag-capture --description="24h Telegram gw crash diagnostic capture (PROPOSAL-20260607)" \
  /bin/bash -c 'timeout 24h journalctl --user -u thunderbird-telegram-gw.service -f --no-pager >> /home/john/Thunderbird/logs/telegram_diagnostic_20260706_160259.log 2>&1'
```

## Verification — service health

- `thunderbird-telegram-gw.service`: `active (running)` since 2026-07-06 15:47:19 MDT (24+ min uptime,
  no crashes since that restart).
- Both bot poll threads confirmed live in journal: `[D2MC2C] Poll thread started`, `[Dani] Poll thread
  started`, `2 bot threads running. Gateway v2.0 LIVE.`
- `Restart=no` confirmed active — any future crash in the diagnostic window will surface as
  `failed`/`inactive`, not be silently auto-healed.
- Repeated `TG API getUpdates exception: ... Read timed out (read timeout=35)` entries in the journal
  are long-poll timeouts the gateway's own retry loop absorbs without process exit — not the crash
  signature. No actual crash/traceback observed in this session's window.

## Context: crash frequency has already dropped substantially since the proposal was authored

Proposal (2026-06-07) reported 16 restarts/7 days (~2.3/day). Current 7-day count: **9 restarts**,
most preceded by long (1–21 hour) clean uptimes rather than tight crash-looping. Intervening fixes
already in place (Tier-1 hardening `resource-limits.conf` 2026-06-13, MISSION-153 self-heal restart
policy, MISSION-168 "root-cause overwatch crash loop" completed) have already addressed part of the
original defect. This diagnostic window will determine whether a residual root cause remains or
whether the remaining restarts are explainable by known causes (OOM, manual restarts, deploys).

## Next steps (Phase 1b / Phase 2 — Sterling, once window closes)

1. Diagnostic window ends ~2026-07-07 16:03 MT (per original capture start time).
2. Review `logs/telegram_diagnostic_20260706_160259.log` for any real crash/exit signature vs. benign
   timeout retries.
3. If a crash signature is found: escalate to Sterling for diagnosis + patch before re-enabling
   auto-heal (`rm zz-disable-restart.conf && systemctl --user daemon-reload && systemctl --user restart
   thunderbird-telegram-gw.service`).
4. If window closes clean: re-enable auto-heal as a backstop (not primary control) and monitor 7 days
   for the 0-restart target.
5. Architectural question (webhooks vs. polling) remains a Commander-level call per ELON's original
   framing — deferred until diagnostic data is in hand.

*— Hale, executing PROPOSAL-20260607-thunderbird-telegram-gw-root-cause.md*
