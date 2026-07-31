# Task 25 — Keepalive Shrink Report

**Status:** Done  
**Date:** 2026-07-30  
**Engineer:** Hale (OC)

---

## Summary

Two wasteful Claude spawns (~24% of overnight token budget) were burning Opus tokens to echo "ok". Both the model downgrade and the two new probe config assets are in place.

---

## Changes

### 1. `hooks/claude_oauth_keepalive.sh` (line 7)

```diff
-RESULT=$(env -u ANTHROPIC_API_KEY /home/john/.local/bin/claude --dangerously-skip-permissions --model claude-opus-4-8 -p "Reply with: ok" 2>&1 | head -2)
+RESULT=$(env -u ANTHROPIC_API_KEY /home/john/.local/bin/claude --dangerously-skip-permissions --strict-mcp-config --mcp-config /home/john/Thunderbird/config/probe_mcp_empty.json --settings /home/john/Thunderbird/config/probe_settings_empty --model claude-haiku-4-5-20251001 -p "ok" 2>&1 | head -2)
```

Three changes on the line:
- **Model:** `claude-opus-4-8` → `claude-haiku-4-5-20251001` (expensive reasoning → cheapest model)
- **Prompt:** `"Reply with: ok"` → `"ok"` (no instruction needed for a single-word echo)
- **Flags added:** `--strict-mcp-config --mcp-config .../probe_mcp_empty.json --settings .../probe_settings_empty` (strips MCP servers, tool context, and settings envelope that aren't needed for a keepalive ping)

### 2. `config/probe_mcp_empty.json` (NEW)

```json
{"mcpServers":{}}
```

Empty MCP server config — prevents Claude from loading any MCP tools/servers for the probe call.

### 3. `config/probe_settings_empty/settings.json` (NEW)

```json
{}
```

Empty settings — prevents Claude from loading project settings/permissions config for the probe call.

---

## Acceptance Results

| Check | Expected | Actual |
|---|---|---|
| `bash -n hooks/claude_oauth_keepalive.sh` | exit 0 | exit 0 |
| `grep -c 'claude-opus-4-8'` | 0 | 0 |
| `grep -c 'claude-haiku-4-5-20251001'` | 1 | 1 |
| `probe_mcp_empty.json` loads | `{'mcpServers': {}}` | `{'mcpServers': {}}` |
| `probe_settings_empty/settings.json` loads | `{}` | `{}` |

---

## Impact

**Tokens saved per probe call:** ~99% (Opus system prompt + MCP context ~15K tokens → Haiku with empty config ~0.5K tokens).  
**Budget recovered:** reclaims ~24% of the overnight Max bucket that was burning on "ok".
