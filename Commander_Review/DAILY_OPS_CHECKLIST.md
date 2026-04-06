# THUNDERBIRD WING — DAILY OPS CHECKLIST
**Updated:** 2026-03-29 | Owner: COS (Hale)
**Show this file on every Claude Code or Goose login.**

---

## ON LOGIN — ALWAYS CHECK FIRST

```
systemctl --user status thunderbird-overwatch thunderbird-telegram-c2
cat OpsCenter/03_CLAUDE_MAX_QUEUE.json
cat OpsCenter/01_TASK_QUEUE.json
```

| Check | Tool | Healthy When |
|-------|------|--------------|
| Overwatch daemon alive | `systemctl --user status thunderbird-overwatch` | `active (running)` |
| Telegram C2 alive | `systemctl --user status thunderbird-telegram-c2` | `active (running)` |
| Task queue | `cat OpsCenter/01_TASK_QUEUE.json` | `[]` or new tasks to process |
| Claude MAX queue | `cat OpsCenter/03_CLAUDE_MAX_QUEUE.json` | `[]` or hand off to Claude |
| OpsCenter test | `python3 OpsCenter/opscenter_test_harness.py` | 33/33 green (currently 31/33) |
| Goose manifest | `cat OpsCenter/04_GOOSE_TASK_MANIFEST.md` | Check completion log |

---

## ACTIVE PROJECT TASKS (Clear before end of session)

### CLAUDE CODE
| # | Task | Status |
|---|------|--------|
| C2 (#16) | Drain Claude MAX queue — MCP gmail + voice matching | PENDING |
| C3 (#18) | Commit all OpsCenter uncommitted changes | PENDING (do last) |

### GOOSE
| # | Task | Status |
|---|------|--------|
| G1 (#9) | Fix Gemini MAX_TOKENS + retry logic in task_processor.py | PENDING |
| G3 (#17) | Log rotation — RotatingFileHandler for process.log + hale_chat_log | PENDING |
| G4 (#19) | Run daily innovation scan | PENDING |
| G5 (#20) | Run world intelligence sweep | PENDING |
| G6 (#21) | Run tech monitor / news scan | PENDING |
| G7 (#22) | Run ship intelligence sweep | PENDING |

### DEFERRED
| # | Task | When |
|---|------|------|
| #8 | TESS auth — browser SSH + Goose ride-along | Monday 30 MAR afternoon |

---

## AUTOMATED DAILY TIMERS (verify ran — check `journalctl --user -u <service> --since today`)

### Night Run (~01:00–03:00 MDT)
| Time | Service | What | Verify |
|------|---------|------|--------|
| 00:30 | `d2m-booking-monitor` | Payment deadline check | Email to johnloucks3 |
| 00:50 | `d2m-preflight` (runs ~06:50) | System preflight | No errors |
| 01:00 | `d2m-intel-telegram` | Intel digest → Telegram | Check phone |
| 01:30 | `d2m-morning-briefing` | Morning brief → johnloucks3 | Email delivered |
| 01:30 | `d2m-factbook-refresh` | Factbook update | No errors |
| 01:35 | `d2m-fpd-alert` | Final payment deadline alerts | Email if deadlines near |
| 01:40 | `d2m-airline-monitor` | Airline route changes | Email if changes found |
| 01:45 | `thunderbird-innovation-scan` | Daily innovation scan → intel/ | File updated |
| 01:50 | `d2m-power-harvest` | ***REMOVED-SECRET*** intel | File updated |
| 01:55 | `d2m-incubator-am-scrape` | Incubator deep-dive | See intel/incubator_* |
| 02:00 | `d2m-x-osint` | X/OSINT feed | File updated |
| 02:00 | `thunderbird-evernote-backup` | Evernote backup | Mon only |
| 02:04 | `d2m-drive-sync` | rclone → Google Drive | No errors |
| 02:05 | `d2m-sculptor-learn` | Voice learning | No errors |
| 02:10 | `d2m-incubator-a2-intake` | A2 classification intake | See incubator files |
| 02:15 | `d2m-incubator-elon-queue` | ELON build queue | See elon_build_queue.md |
| 02:30 | `d2m-inbox-cleanup` | Gmail label cleanup | No errors |
| 02:31 | `thunderbird-backup-verify` | Backup integrity check | Mon only |
| 02:32 | `d2m-voice-sync` | Voice profile sync | No errors |
| 03:00 | `thunderbird-logrotate` | Log rotation | No errors |
| 23:00 | `thunderbird-drive-sync` | Drive sync (alt) | No errors |

### Day Run
| Time | Service | What | Verify |
|------|---------|------|--------|
| 07:00 | `d2m-email-intel` | Email intel sweep | Email or Telegram |
| 07:03 | `thunderbird-fpd-alert` | FPD alert (system-level) | No errors |
| 12:05 | `thunderbird-batch` | Batch processing | No errors |
| 14:00 | `d2m-zfold-test` | Z Fold display test | No errors |

### Evening Run (Incubator Cycle)
| Time | Service | What | Verify |
|------|---------|------|--------|
| 18:30 | `d2m-incubator-prompt` | COS generates tonight's sector/gap question → Telegram | Check phone |
| 19:00 | `d2m-incubator-execute` | Full tool research | intel/incubator_* updated |
| 19:30 | `d2m-incubator-review` | COS synthesizes → sets AM categories | intel/incubator_last_review.md |
| 20:13 | `d2m-sculptor-harvest` | Voice harvest | No errors |

### Health Monitors (continuous)
| Freq | Service | What |
|------|---------|------|
| 2 min | `thunderbird-watchdog` | OpsCenter service health |
| 5 min | `thunderbird-telegram-health` | Telegram bot alive check |
| 20 min | `d2m-usage-monitor` | Token usage + alert at 82% |
| 1 hr | `hale-chatlog-backup` | Chat log → Drive |
| 24 hr | `thunderbird-opscenter-test` | Full pipeline test → Telegram |

---

## WEEKLY TASKS

| Day | Task | Notes |
|-----|------|-------|
| **Sunday 01:30** | `thunderbird-innovation-scan-weekly` | Deep innovation scan |
| **Monday** | `thunderbird-evernote-backup` | Evernote backup |
| **Monday** | `thunderbird-backup-verify` | Backup integrity |
| **Monday PM** | TESS auth (browser SSH + Goose ride-along) | Deferred from 29 MAR |

---

## MONTHLY TASKS

| Date | Task | Notes |
|------|------|-------|
| **1st @ 07:15** | `thunderbird-monthly-archive` | Product archive |
| **1st** | Commission reconcile | Harlan (A9) |
| **1st** | Git commit alert | `thunderbird-git-commit-alert` |

---

## INTEL DELEGATION — ALL TO GOOSE

Per Commander standing order 2026-03-29. Goose owns:
- Daily innovation scan (G4)
- World intelligence sweep (G5)
- Tech monitor / news scan (G6)
- Ship intelligence sweep (G7)
- All other scanning, searching, tech news

**Intel send rules (SO 27 MAR 2026):** All intel → johnloucks3@gmail.com as **full sends** (not drafts). Send FROM d2mconcierge. Every source gets a clickable hyperlink.

---

## FILE MAINTENANCE (manual or Goose)

| Task | Frequency | Command / Location |
|------|-----------|--------------------|
| Session autosave | Every 10 min (session) | `session_autosave_latest.md` |
| Session checkpoint | Session close | `mcp__dreams2memories__session_checkpoint` |
| WF16 Telegram log | Session close | Write to `session_telegram_YYYY-MM-DD.md` |
| Dossier → Drive mirror | On booking change | `mcp__dreams2memories__sync_all_dossier_files` |
| Master booking sheet | On booking change | Google Sheet via MCP |
| THUNDERBIRD_MASTER_PLAN | On booking change | Manual update Part 5 |
| Goose manifest check | On login | `cat OpsCenter/04_GOOSE_TASK_MANIFEST.md` |

---

## GIT COMMIT CADENCE

Commit every session close. COS prompts if Commander doesn't ask.
- **Never amend** — always new commits
- **Never skip hooks** (`--no-verify`)
- **Never force-push main**
- Alert: `thunderbird-git-commit-alert.timer` fires daily at 21:47
