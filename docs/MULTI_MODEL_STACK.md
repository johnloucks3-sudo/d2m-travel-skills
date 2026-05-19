# ARCHIVED: Historical Reference Only. See AGENTS.md for live stack.

# THUNDERBIRD MULTI-MODEL STACK
## Post-Goose Architecture | 2026-04-06

---

## THE NEW STACK

| Tool | Role | Models | Cost |
|------|------|--------|------|
| **Claude Code** (MAX) | Primary agent — reasoning, code, strategy, client work | Opus 4.6, Sonnet 4.6 | $0 (MAX subscription) |
| **OpenCode** | Multi-model agent — ops, scanning, bulk tasks, non-Anthropic work | Default: DeepSeek V3.1 + 75+ providers via OpenRouter | ~$0.27/M (default) + free/paid tiers |
| **Claude Agent SDK** | Programmatic dispatch — headless tasks, Nexus integration | Same as Claude Code | $0 (MAX) |

## WHEN TO USE WHAT

| Task | Use | Why |
|------|-----|-----|
| Client emails, proposals, voice work | Claude Code (MAX) | Best reasoning, D2M voice, $0 |
| Code architecture, complex debugging | Claude Code (MAX) | Strongest multi-step reasoning |
| Bulk file scanning, data processing | OpenCode (free models) | Zero cost, good enough |
| Quick research, summarization | OpenCode (DeepSeek V3.1) | Low cost (~$0.27/M) |
| Intel sweeps, web scraping | OpenCode or dedicated scripts | Doesn't need Opus |
| Arbitration between conflicting outputs | Claude Code (MAX) | Judgment calls stay with Claude |

## QUICK START

```bash
# Claude Code (primary — already configured)
cd ~/Thunderbird && claude

# OpenCode (multi-model — new)
cd ~/Thunderbird && opencode

# OpenCode headless run
opencode run "scan all Python files for deprecated imports"

# OpenCode with specific model
opencode --model openrouter/deepseek/deepseek-chat-v3.1 run "summarize this file"

# OpenCode web UI (access from browser/phone)
opencode web
```

## MODEL SWITCHING IN OPENCODE

Press `/model` inside OpenCode to switch models mid-session.

Free models (no API key needed):
Default (low-cost, ~$0.27/M):
- `openrouter/deepseek/deepseek-chat-v3.1` — DeepSeek V3.1 (primary model)

Free fallbacks (no API key needed):
- `opencode/minimax-m2.5-free` — MiniMax M2.5
- `opencode/nemotron-3-super-free` — Nemotron 3 Super

With ANTHROPIC_API_KEY (from .env):
- `anthropic/claude-sonnet-4-6`
- `anthropic/claude-opus-4-6`

With OPENROUTER_API_KEY (from .env):
- Any of 400+ models via OpenRouter

## MCP INTEGRATION

OpenCode reads `.opencode.json` in the project root. MCP server configured:
```json
{
  "mcpServers": {
    "dreams2memories": {
      "command": "/home/john/Thunderbird/mcp_launcher_core.sh"
    }
  }
}
```

All 285 D2M tools available in OpenCode, same as Claude Code.

## UNINSTALL

```bash
bash ~/Thunderbird/scripts/uninstall_opencode.sh
```

Removes OpenCode binary, config, PATH entries. Claude Code unaffected.

## GOOSE DECOMMISSION STATUS

Goose remains installed but is no longer the primary ops engine. OpenCode replaces its role:
- Multi-model routing → OpenCode native
- Ops brain (DeepSeek V3.1) → OpenCode default model
- MCP tools → OpenCode MCP config
- Headless dispatch → `opencode run` replaces `opencode run`
- Recipes → OpenCode agents/plugins

To fully remove Goose later:
```bash
pip uninstall goose-ai
rm -rf ~/.config/goose
```

---

*Stack updated 2026-04-06 | COS Hale*
