# INBOX CONSOLIDATION REPORT
**Date:** 2026-04-07
**Author:** Claude Code (Hale)
**Task:** Consolidate all inbox/outbox files, fix stale references, verify pipeline

---

## 1. All Files Found

| File | Status | Notes |
|------|--------|-------|
| `/home/john/Thunderbird/claude_inbox.md` | **CANONICAL** | Root-level Claude inbox |
| `/home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md` | **CANONICAL** | Claude result outbox |
| `/home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md` | **CANONICAL** | OpenCode task inbox |
| `/home/john/Thunderbird/OpsCenter/collaboration/opencode_outbox.md` | **CANONICAL** (new) | Created this session |
| `/home/john/Thunderbird/OpsCenter/collaboration/claude_inbox.md` | STALE | Had pending tasks — merged into canonical |
| `/home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md` | STALE | Decommissioned — merged into opencode_inbox.md |
| `/home/john/Thunderbird/claude_outbox.md` | STALE | Had historical inter-agent content — merged into canonical outbox |

---

## 2. Content Merged

| Source | Destination | Action |
|--------|-------------|--------|
| `/home/john/Thunderbird/claude_outbox.md` (root) | `OpsCenter/collaboration/claude_outbox.md` | Appended full content (historical inter-agent discussion) |
| `OpsCenter/collaboration/claude_inbox.md` | `claude_inbox.md` (root canonical) | Appended with source header (had MISSION-002-003 and lifecycle tasks) |
| `OpsCenter/collaboration/opencode_inbox.md` | `OpsCenter/collaboration/opencode_inbox.md` | Appended with source header (had OpenCode intro + NEXUS V2.1 review JSON) |

Files NOT deleted — content preserved in canonical files.

---

## 3. Fixes Applied

### thunderbird_tasking_watcher.py
- `CLAUDE_INBOX` path fixed: `OpsCenter/collaboration/claude_inbox.md` → `/home/john/Thunderbird/claude_inbox.md` (canonical root)
- `GOOSE_INBOX` renamed to `OPENCODE_INBOX`, path updated to `opencode_inbox.md`; legacy alias `GOOSE_INBOX = OPENCODE_INBOX` retained
- `spawn_goose_headless()` replaced with `spawn_opencode_headless()` — now calls `opencode run -m openrouter/deepseek/deepseek-chat-v3.1`; legacy alias `spawn_goose_headless = spawn_opencode_headless` retained
- `handle_goose_spawn()` replaced with `handle_opencode_inbox()`; legacy alias retained
- HANDLERS dispatch map updated to use `OPENCODE_INBOX` and `handle_opencode_inbox`
- Startup Telegram ping updated to say "OpenCode" not "Goose"
- Service restarted — running clean (PID 1225232)

### hooks/auto_inject_inbox.sh
- Removed watch on stale `OpsCenter/collaboration/claude_inbox.md`
- Now watches only canonical `claude_inbox.md` at root
- Injection message updated to reference single canonical path

### AGENTS.md
- Added "Canonical Inbox / Outbox" section with full file layout table
- Documents canonical paths, decommissioned files, cross-bot routing pattern
- Updated `claude_outbox.md` path reference (was incorrectly showing root path)
- Clarifies default OpenCode model: `openrouter/deepseek/deepseek-chat-v3.1`

### OpsCenter/config.py
- Already correct: `GOOSE_INBOX = OPENCODE_INBOX` alias present, canonical paths set
- No changes needed

### OpsCenter/nexus.py
- No stale goose references found — uses config.py imports
- No changes needed

### OpsCenter/thunderbird_telegram_gw.py
- Has `call_goose_engine = call_opencode_engine` alias already in place
- No path references to old inboxes
- No changes needed

### OpsCenter/keyword_router.py
- No inbox path references found
- No changes needed

---

## 4. Canonical Layout (Final)

```
CLAUDE INBOX:   /home/john/Thunderbird/claude_inbox.md
CLAUDE OUTBOX:  /home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md

OPENCODE INBOX:  /home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md
OPENCODE OUTBOX: /home/john/Thunderbird/OpsCenter/collaboration/opencode_outbox.md

CROSS-BOT ROUTING:
  OpenCode → Claude: append to claude_inbox.md
  Claude → OpenCode: append to opencode_inbox.md
  Both write results to their own outbox
  Watcher pings Commander on any inbox change (inotify, sub-second)
```

---

## 5. Nexus / Watcher Status

| Service | Status |
|---------|--------|
| `thunderbird-overwatch.service` | RUNNING — PID 97822 (`task_processor.py`) — last activity 01:46 MDT (nightly intel sweep, 146 findings) |
| `d2m-tasking-watcher.service` | RUNNING — PID 1225232 — restarted 08:05 MDT with updated paths |

**Known non-critical warning:** `StartLimitIntervalSec` in `[Service]` section is ignored by user systemd (it's a `[Unit]` directive). Harmless.

**nexus_inbox_state.json:** Not found in `OpsCenter/state/` — watcher uses `OpsCenter/inbox_watcher_state.json` instead (correct path per watcher code). State file initialized on startup.

---

## 6. Headless Claude Task Results

Tasks INBOX-VERIFY-001 and INBOX-VERIFY-002 written to `claude_inbox.md` and triggered via:
```bash
env -u ANTHROPIC_BASE_URL -u ANTHROPIC_API_KEY claude --dangerously-skip-permissions -p "..."
```

**Result (from logs/inbox_verify.log):**
- INBOX-VERIFY-001: COMPLETE — confirmed reading from canonical `/home/john/Thunderbird/claude_inbox.md`
- INBOX-VERIFY-002: COMPLETE — confirmed `opencode_inbox.md` exists and is correctly formatted
- Confirmations written to `claude_outbox.md`

**Pipeline verdict: VERIFIED OPERATIONAL**

---

*Report generated by Claude Code (Hale) — 2026-04-07*
