# Claude Spawn Monitor IOI (Hale Directive 2026-04-29)
## Purpose
When OpenCode spawns Claude (UNREAD inbox → Opus/Sonnet), timer starts. Check inbox/outbox/file every 5min; Telegram COMPLETE/timeout/ETA.

## Implementation
- Timer: thunderbird_claude_spawn_monitor.timer (5min)
- Script: OpsCenter/claude_spawn_monitor.py (tail logs, grep status, ls manual.md, Telegram Hale/Cmdr)
- State: hale_state_unified.json (active_timers[])