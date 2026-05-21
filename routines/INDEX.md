# Claude Routine Templates — Thunderbird OS

Created 2026-05-21. Copy each into `claude.ai/routines` then invoke with `/` in any session.

## Available Routines

| Command | Trigger | What it does | Replaces |
|---------|---------|-------------|----------|
| `/agentic-intel` | Nightly 01:00 | Web research → digest of AI/agentic dev | `thunderbird-agentic-intel.timer` |
| `/tech-monitor` | Daily 10:00 | Top tech stories from HN/Reddit/GitHub | Daily ritual tech phase |
| `/claude-code-digest` | On-demand | Claude Code news + community tips | Daily ritual digest |
| `/competitive-surveillance` | Weekly | Travel AI competitor landscape | Batch task |
| `/silver-spirit-intel` | Daily | Silver Spirit news/pricing/availability | `silver-spirit-daily-intel.timer` |
| `/world-intel` | On-demand | Travel advisories + weather for client trips | Batch task |
| `/incubator-research` | On-demand | Research → classify → roadmap | `d2m-incubator-*.timer` |
| `/payment-alerts` | Daily | FPD deadline scanner | `d2m-fpd-alert.timer` |

## How to Install

1. Go to `claude.ai/routines`
2. Click "Create Routine"
3. Set the **slash command** name (e.g., `agentic-intel`)
4. Paste the prompt from `routines/<name>.md`
5. Optionally set a **schedule** (e.g., daily at 01:00 for `/agentic-intel`)
6. Save — now invoke from any session with `/<name>`

## Notes

- All routines run on Claude MAX (via claude.ai web) — $0 incremental cost
- Output text in session; you can copy/paste or ask Claude to email
- If a routine returns info that needs action, tag me (OpenCode) via Telegram or NEXUS
- ZEN limits: DeepSeek V4 = 100/hr, 500/day. Preflight guard auto-alerts at 60%.
