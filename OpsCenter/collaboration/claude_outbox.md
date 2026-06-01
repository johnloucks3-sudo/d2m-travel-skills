
## OC OUTPUT — POST-INTEGRATION-FIX-WATCHER-SPAWN
**Status:** COMPLETE — 2026-05-31T19:30:00Z
**From:** OpenCode (JET)
**Task:** Retrofit watcher to use lighter MCP spawn (options a+b)

### What was done

**Root cause confirmed:** The watcher's `_invoke_claude` passed `--mcp-config /home/john/.claude/mcp.json` on every spawn — all 9 MCP servers (context7, dreams2memories, skiplagged, kiwi, trivago, ferryhopper, airbnb, multi-model, lastminute, ticketmaster). Each headless spawn incurred 30-60s startup loading the full stack.

**Fix — three changes:**

1. **`/home/john/.claude/mcp_light.json`** — created minimal MCP profile with only 2 essential servers: `context7` and `dreams2memories`. Excludes all travel-specific MCPs (skiplagged, kiwi, trivago, ferryhopper, airbnb, lastminute, ticketmaster) that are irrelevant for inbox-processing tasks.

2. **`core/ai_infra/thunderbird_headless_spawn.py`** — `spawn_headless_claude()` now accepts an optional `mcp_config` parameter. Defaults to full `mcp.json` for backwards compatibility. Parameter is cascaded through `_spawn_background()`, `_spawn_with_retry()`, and `_spawn_synchronous()`.

3. **`OpsCenter/thunderbird_tasking_watcher.py`** — `_invoke_claude()` now passes `mcp_config=MCP_LIGHT` to `spawn_headless_claude()`. This uses the foolproof wrapper (OAuth handling, prereq checks, background mode) with the light MCP profile.

### Options evaluated
| Option | Verdict |
|--------|---------|
| (a) Use dispatch_claude.py as watcher spawn | **Adopted** — watcher already used `spawn_headless_claude()` (the same function dispatch_claude.py wraps); just needed `mcp_config` param |
| (b) Light MCP profile | **Adopted** — `mcp_light.json` with only essential servers |
| (c) Pre-warm MCP servers | **Rejected** — adds complexity, no persistent cache mechanism exists |
| (d) Conditional MCP loading | **Rejected** — watcher tasks are always inbox-processing, not travel; single light profile sufficient |

### Estimated impact
- Spawn overhead: ~60s → ~10s (eliminates 7 travel MCP server startups)
- No functional change: inbox-processing tasks never needed travel MCPs
- OAuth, error handling, and monitoring preserved
