# EMAIL MAINTENANCE ENGINE — Design Spec v1.0
## COL Victoria "Iron Vic" Hale, COS — 2026-04-04

> **Author: Hale | Implementer: Claude (headless)**

---

## PROBLEM
`OpsCenter/email_task_ingest.py` is dead — calls nonexistent `mcp_bridge.sh`. Commander has no automated email pipeline despite 5 complete conditioning JSONs sitting in `email_conditioning/`.

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│  THUNDERBIRD EMAIL MAINTENANCE ENGINE                           │
│  File: thunderbird_email_maintenance.py                         │
│  Scheduling: systemd timer + direct MCP tool usage             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │ SWEEP PHASE  │───▶│ CLASSIFY     │───▶│ ROUTE & DRAFT    │   │
│  │ Gmail MCP    │    │ + Tag Match  │    │ Inbox Write      │   │
│  │ gmailSearch  │    │ + Infer      │    │ gmailCreateDraft │   │
│  │ gmailReadMsg │    │ + Dedup      │    │ gmailModifyMsg   │   │
│  └──────────────┘    └──────────────┘    └──────────────────┘   │
│        │                      │                      │           │
│  EMAIL_SWEEP           EMAIL_TASKING          EMAIL_DRAFT       │
│  CONDITIONS.json       CONDITIONS.json        CONDITIONS.json   │
│                              │                      │           │
│                      ┌───────▼───────┐    ┌─────────▼────────┐ │
│                      │ Route to      │    │ Send to          │ │
│                      │ goose_inbox / │    │ Commander/       │ │
│                      │ claude_inbox  │    │ johnloucks3      │ │
│                      │ or delegate   │    │ drafts           │ │
│                      └───────────────┘    └──────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 5 CONDITIONING FILES (ALL EXIST)

| File | Purpose |
|------|---------|
| EMAIL_TASKING_CONDITIONS.json | Routing by tag [COS],[A3],etc. Auto-infer rules |
| EMAIL_SWEEP_CONDITIONS.json | Sweep criteria, skip patterns, interval |
| EMAIL_DRAFT_CONDITIONS.json | Draft rules, Luna→Dembe→COS→Commander flow |
| EMAIL_SEND_TO_COMMANDER_CONDITIONS.json | When to alert Commander |
| EMAIL_SEND_TO_JOHNLOUCKS3_CONDITIONS.json | Daily brief, task completion reports |

## IMPLEMENTATION RULES

1. **NO subprocess chains** — call Gmail via MCP tools directly (Thunderbirdmcp.gmailSearchMessages, gmailReadMessage, gmailCreateDraft, gmailModifyMessage)
2. **Use existing patterns** — model the code on `thunderbird_commander_inbox.py` and `thunderbird_dani_email.py`
3. **Dedup** — maintain state file with processed message IDs, prune at 500
4. **State tracking** — write task lifecycle to activity_board.md
5. **WF-17 compliance** — ALL client-facing emails go to draft, never direct send
6. **Error handling** — catch and log, never crash the sweep
7. **Test-first** — include dry-run mode that logs what it WOULD do

## SCHEDULING

Systemd timer, every 5 minutes per EMAIL_SWEEP_CONDITIONS.json.
Service file should use `/usr/bin/python3` (not .venv — home dir blocks systemd).

## OUTPUT FILES
- `OpsCenter/email_maintenance_state.json` — dedup + last_run
- `OpsCenter/email_maintenance.log` — detailed log
- Drafts in Gmail (not sent — Commander reviews via WF-17)
- Telegram notifications for completions and escalations
- Tasks written to goose_inbox.md / claude_inbox.md

---
*Design by Hale — hand off to Claude for implementation*
