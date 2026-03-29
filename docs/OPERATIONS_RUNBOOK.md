# THUNDERBIRD OS — OPERATIONS RUNBOOK
## Dreams2Memories Travel, LLC
## Infrastructure Repair Completed 2026-03-28
---

## Quick Reference — Provider Chain

| Launcher | Provider | Model | Cost | Use Case |
|----------|----------|-------|------|----------|
| `goose-d2m` | Google Gemini | gemini-2.5-flash | ~$20/mo | Default automated, all timers |
| `goose-d2m-claude` | Claude MAX | claude-sonnet-4-6 | $0 | Interactive sessions |
| `goose-d2m-groq` | Groq | llama-3.3-70b-versatile | Free | Fallback when others down |
| `goose-poe` | Poe (Anthropic trick) | claude-sonnet-4-6 | Poe points | Reserve tank |

**Model override (any launcher):** `GOOSE_MODEL=gemini-2.5-pro goose-d2m session`

## Failover Chain
```
Gemini (goose-d2m) → Claude MAX (goose-d2m-claude) → Groq (goose-d2m-groq) → Poe (goose-poe)
```

## Claude Code / Desktop / Telegram C2
- **Default model:** Sonnet 4.6
- **Upgrade to Opus:** Commander explicit code change required (SO 2026-03-27)
- **Telegram C2:** Runs on MAX plan ($0), bot token in .env

---

## Daily Automated Schedule (MDT)

| Time | System | What |
|------|--------|------|
| 00:50 | `d2m-preflight` | Preflight check — all services, tokens, disk, API |
| 01:00-02:30 | Intel timers | Morning intel block (briefing, world intel, ship intel) |
| 08:00 | `d2m-zfold-test` | Z Fold6 connectivity test (4-tier escalation) |
| 12:00 | Scheduler | Midday pulse |
| 17:00 | Scheduler | EOD summary |
| 18:30-19:30 | Incubator | Prompt → Execute → Review cycle |
| 21:00 | Scheduler | Evening sync + drive sync |
| 03:00 | Logrotate | Log rotation (7-day, compressed) |

## Three-Tier Alerting

| Severity | Channels | Example |
|----------|----------|---------|
| GREEN | Telegram only | Preflight passed |
| YELLOW | Telegram + Email | Token expiring, disk low |
| RED | Telegram + Email + SMS | Service down, no connectivity |

**SMS gateway:** 7192910742@tmomail.net (T-Mobile email-to-SMS)

---

## Key Files Modified (2026-03-28)

### Phase 0: Emergency Triage
- `thunderbird_scheduler.py` ��� Added `fcntl` flock guard (prevents duplicate instances)

### Phase 1: RED Fixes
- `.env` — Consolidated from .env + .env.keys. Now has 21 active keys including Gemini, Poe, Anthropic, OpenAI, DeepSeek, Serper, Pexels, Unsplash
- All 27 systemd services — Added `EnvironmentFile=/home/john/Thunderbird/.env`
- `d2m-scheduler.service` — Added `MemoryMax=800M`
- `d2m-morning-briefing.service` — `TimeoutStartSec=1800`
- `d2m-factbook-refresh.service`, `d2m-airline-monitor.service`, `d2m-x-osint.service` — Added PATH with ~/.local/bin

### Phase 2: YELLOW Fixes
- 7 credential files — `chmod 600` (were 644)
- `config/logrotate.conf` — Created with daily rotation, 7-day retention
- `mcp_launcher.sh` — Defensive .env.keys source added
- `forms_token.json` — Confirmed deleted (covered by gmail_token.json)

### Phase 3: Goose → Gemini
- `/home/john/bin/goose-d2m` — Rewritten: Claude → Gemini 2.5 Flash
- `/home/john/bin/goose-d2m-claude` — NEW: Claude MAX ($0)
- `/home/john/bin/goose-d2m-groq` — NEW: Groq fallback
- `/home/john/bin/goose-poe` — Updated: model selection support
- `~/.config/goose/config.yaml` — Provider=google, all API keys, MCP via launcher

### Phase 4: Hardening
- `thunderbird_preflight.py` — NEW: 7-check preflight with 3-tier alerting
- `thunderbird_zfold_test.py` — NEW: 4-tier phone connectivity test
- `d2m-preflight.timer` — NEW: 00:50 MDT daily
- `d2m-zfold-test.timer` — NEW: 08:00 MDT daily

---

## Troubleshooting

### Service won't start
```bash
systemctl --user status d2m-<service>
journalctl --user -u d2m-<service> --since "1h ago"
```

### Duplicate processes
```bash
# Check
ps aux | grep thunderbird_scheduler | grep -v grep
# Flock guard should prevent — but if needed:
kill <older-PID>
```

### OAuth token expired
```bash
cd ~/Thunderbird
export OAUTHLIB_INSECURE_TRANSPORT=1
python3 thunderbird_google_auth.py --authorize-headless   # Main token
python3 thunderbird_google_auth.py --authorize-persona    # Persona token
```

### Goose won't connect to Gemini
```bash
# Verify key works
curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=***REMOVED-SECRET***" | head -5
# Switch to Claude fallback
goose-d2m-claude session
```

### All notification channels down
Check `~/Thunderbird/zfold_test_state.json` — if "conservation_mode", system reduced load automatically. Manual intervention needed.

---

## Pre-Departure Checklist (Before April 10)

- [ ] Run full preflight: `python3 thunderbird_preflight.py`
- [ ] Verify all timers: `systemctl --user list-timers 'd2m-*'`
- [ ] Test Goose Gemini: `goose-d2m run --no-session -t "Say OK"`
- [ ] Test Goose Claude: `goose-d2m-claude run --no-session -t "Say OK"`
- [ ] Test Z Fold6 connectivity: `python3 thunderbird_zfold_test.py --force`
- [ ] Verify Telegram C2 responds
- [ ] Check OAuth token expiry: `python3 thunderbird_google_auth.py --status`
- [ ] Confirm GCP consent screen is "In Production" (not Testing)
- [ ] 48-hour hands-off dress rehearsal (days 12-13)
- [ ] Review preflight_last.json after 3+ days of automated runs

## 48-Hour Dress Rehearsal Protocol
1. Start: Do NOT touch any Thunderbird system for 48 hours
2. Monitor: Check Telegram for daily preflight GREEN + Z Fold6 check
3. Verify: Morning intel arrives, evening sync runs, no RED alerts
4. Pass criteria: Zero manual intervention needed for 48 hours
5. If any RED: Fix root cause, restart 48-hour clock
