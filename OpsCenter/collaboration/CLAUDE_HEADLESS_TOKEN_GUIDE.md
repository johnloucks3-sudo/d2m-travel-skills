# Claude Code Headless — OAuth Token Guide
## Thunderbird OS | Updated 2026-04-08

---

## THREE-TIER DISPATCH (Updated 2026-04-08)

The watcher now has three fallback tiers for headless Claude:

| Tier | Auth | Model | Cost | When |
|------|------|-------|------|------|
| **1** | OAuth (Max plan) | Default (Sonnet/Opus) | **$0** | Commander active in Claude Code (token < 2h old) |
| **2** | API key | Haiku 3.5 | **~$0.06-0.20/task** | Commander away, token stale, API key available |
| **3** | None (OpenRouter) | DeepSeek V3.1 | **~$0.27/M** | Both OAuth and API key unavailable |

This means **headless Claude now works 24/7**. When you're active, it's free.
When you're away, it uses Haiku (cheap). DeepSeek V3.1 is last resort.

---

## THE TOKEN CHAIN

```
Step 1: Commander opens Claude Code (interactive session)
        └── Claude Code generates CLAUDE_CODE_OAUTH_TOKEN in process env

Step 2: Commander sends any message (UserPromptSubmit hook fires)
        └── hooks/refresh_claude_oauth_cache.sh runs
            └── Reads $CLAUDE_CODE_OAUTH_TOKEN from env
            └── Writes to: OpsCenter/.claude_oauth_cache
            └── Format: CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...
            └── Permissions: 0600

Step 3: Watcher detects UNREAD task in claude_inbox.md
        └── thunderbird_tasking_watcher.py → spawn_claude_headless()
            └── Checks cache file age (must be < 2 hours)
            └── If fresh: loads token → injects into subprocess env → runs claude -p
            └── If stale: skips claude -p → falls back to OpenCode/DeepSeek V3.1

Step 4: claude -p headless runs with injected token
        └── Strips ANTHROPIC_API_KEY and ANTHROPIC_BASE_URL (forces OAuth path)
        └── Uses CLAUDE_CODE_OAUTH_TOKEN for authentication
        └── Writes results to claude_outbox.md + opencode_inbox.md
```

---

## KEY FILES

| File | Purpose |
|------|---------|
| `hooks/refresh_claude_oauth_cache.sh` | Caches token from active Claude Code session |
| `OpsCenter/.claude_oauth_cache` | Cached token (plain text, 0600) |
| `OpsCenter/thunderbird_tasking_watcher.py` | Reads cache, spawns headless processes |
| `logs/oauth_cache.log` | Refresh history (successes + warnings) |
| `logs/claude_headless.log` | Headless Claude output/errors |
| `~/.claude/settings.json` | Hook config (UserPromptSubmit) |

---

## FRESHNESS RULES

- **Cache max age:** 2 hours (7200 seconds)
- **If fresh (<2h):** Watcher loads token and attempts `claude -p`
- **If stale (>2h):** Watcher skips `claude -p` entirely, falls back to OpenCode
- **Refresh trigger:** Only happens when Commander is actively using Claude Code
- **No active session = no valid token = OpenCode-only mode**

---

## WHEN THINGS GO WRONG

### Symptom: `401 authentication_error`
**Cause:** Stale token in cache.
**Fix:** Commander opens Claude Code and sends any message. The UserPromptSubmit
hook refreshes the cache automatically. Then restart the watcher:
```bash
systemctl --user restart d2m-tasking-watcher.service
```

### Symptom: `WARNING: CLAUDE_CODE_OAUTH_TOKEN not set — cache not updated`
**Cause:** Hook ran from a context without the env var (watcher, cron, other agent).
**This is expected.** The hook only succeeds inside Claude Code's process tree.

### Symptom: Watcher skips claude -p and always falls back to OpenCode
**Cause:** Commander hasn't been active in Claude Code for >2 hours.
**Fix:** Start a Claude Code session. Token refreshes automatically on first message.

### Symptom: `Invalid API key` (not "expired")
**Cause:** `ANTHROPIC_API_KEY` env var is leaking into the headless process.
**Fix:** Verify `spawn_claude_headless()` strips both `ANTHROPIC_API_KEY` and
`ANTHROPIC_BASE_URL` before spawning.

---

## FOR DEEPSEEK / OPENCODE

You **cannot** refresh the Claude OAuth token yourself. The token comes from
Claude Code's OAuth session with Anthropic. Only Claude Code interactive sessions
generate valid tokens.

If you need Claude-level reasoning and the token is stale:
1. Route the task to `openrouter/deepseek/deepseek-chat-v3.1` (~$0.27/M, no special auth needed)
2. For tasks that truly require Claude: write to `claude_inbox.md` with
   `status: UNREAD` and wait — the watcher will dispatch to Claude when
   the Commander's next session refreshes the token
3. **DO NOT** try to generate, guess, or fabricate OAuth tokens

---

## HOW TO TASK CLAUDE HEADLESS (FOR AGENTS)

Write a task to `/home/john/Thunderbird/claude_inbox.md`:
```markdown
---
task_id: "YOUR-TASK-ID"
priority: "P0"
from: "Your-Agent-Name"
to: "Claude"
status: UNREAD
---

# Task Title

Your full instructions here. Be explicit about:
- What files to read
- What to produce
- Where to write output
```

The watcher polls `claude_inbox.md` via inotify. When it detects `status: UNREAD`:
1. Checks OAuth token freshness
2. If fresh → spawns `claude -p` headless
3. If stale → spawns OpenCode fallback
4. Results land in `OpsCenter/collaboration/claude_outbox.md`

---

## TOKEN LIFECYCLE DIAGRAM

```
                    ┌────────────────────────┐
                    │  Commander Active in    │
                    │  Claude Code Session    │
                    │                        │
                    │  CLAUDE_CODE_OAUTH_TOKEN│
                    │  = sk-ant-oat01-...    │
                    └──────────┬─────────────┘
                               │
                    UserPromptSubmit hook
                               │
                    ┌──────────▼─────────────┐
                    │  .claude_oauth_cache    │
                    │  (refreshed each msg)   │
                    │  TTL: ~2-4 hours        │
                    └──────────┬─────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼──────┐ ┌──────▼────────┐ ┌─────▼──────────┐
    │ Watcher reads  │ │  OpenCode     │ │  Other agents  │
    │ cache, spawns  │ │  inherits     │ │  can read but  │
    │ claude -p      │ │  token in env │ │  can't refresh │
    └────────────────┘ └───────────────┘ └────────────────┘
```

---

*Written by: Col Hale (COS) + Claude Opus | 2026-04-08*
*Committed to memory: OpenCode, DeepSeek, all agents*
