# Claude Code: Everything You Need to Know
## Source: github.com/wesammustafa/Claude-Code-Everything-You-Need-to-Know
## Saved: 2026-03-09 by Thunderbird OS

---

## D2M EXECUTIVE SUMMARY

This is the most comprehensive single-source Claude Code reference available as of March 2026. Key takeaways for Thunderbird OS:

**Directly Actionable:**
- **Skills system** (`.claude/commands/`) — Our 9 personas could be exposed as skills for faster invocation. E.g., `/cos` to route through Hale, `/a2` for Dembe's research voice.
- **Agent Teams** (experimental) — Enable with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. Could let TITAN coordinate sub-agents for parallel ship intel + hotel search + flight search.
- **Fast Mode** — 2.5x speed at 6x cost. Use for time-sensitive client quotes, avoid for background sweeps.
- **Hooks** — `PreToolUse` can validate before MCP tool execution. Could enforce commission math validation before any client-facing output.
- **`/teleport`** — Sends CLI session to claude.ai web. Useful when switching from YOGA to browser mid-task.

**Pricing Intel (for cost management):**
- Pro $20/mo now includes ALL models (Opus 4.6, Sonnet 4.5, Haiku 4.5)
- API: Opus $5/$25 per MTok, Sonnet $3/$15, Haiku $1/$5
- Fast Mode: $30/$150 per MTok (6x standard)
- Average Pro user spends ~$6/day

**Architecture Validation:**
- Our 97-tool MCP server is well beyond what most users run (typical is 5-15 tools)
- Our persona system is unique — no comparable implementations found in the guide
- The guide validates our CLAUDE.md approach but warns about size (keep under 200 lines)

---

## FULL GUIDE CONTENTS

### Core Concepts

LLMs vs Claude Code: Claude Code is a terminal-based tool that leverages Claude's LLM technology. The distinction matters: an LLM represents the underlying AI engine, while Claude Code packages that engine into a developer-focused interface.

### 2026 Model Landscape

| Model | Context | Best For |
|-------|---------|----------|
| Claude Opus 4.6 | 200K (1M beta via API) | Complex reasoning, architecture |
| Claude Sonnet 4.5 | 200K | Balanced performance |
| Claude Haiku 4.5 | 200K | Fast, lightweight tasks |

All three included in Pro subscription ($20/month).

### Usage & Tokens

Pro subscribers: ~45 messages per 5-hour rolling window. ~0.75 words per token for English.

### Subscription Tiers (February 2026)

| Plan | Cost | Model Access |
|------|------|--------------|
| Pro | $20/mo | All three models |
| Max 5x | $100/mo | All three (5x usage) |
| Max 20x | $200/mo | All three (20x usage) |

### Fast Mode

2.5x faster Opus 4.6 responses at 6x pricing ($30/$150 per MTok vs $5/$25). Toggle with `/fast`.

### Key Commands (2026)

**Authentication:**
- `/auth login` / `/auth logout` / `/auth status`

**Model & Performance:**
- `/model` — Switch between Opus 4.6, Sonnet 4.5, Haiku 4.5
- `/fast` — Toggle 2.5x faster responses (Opus only)
- `/cost` — Display token usage statistics

**Session Management:**
- `/debug` — Troubleshoot current session
- `/teleport` — Send session to claude.ai/code for web access
- `/rename` — Auto-generate descriptive session names

**Project Tools:**
- `/init` — Initialize project with CLAUDE.md guide
- `/hooks` — Interactive menu for hook configuration
- `/mcp` — Manage MCP server connections
- `/memory` — Edit CLAUDE.md memory files

### Skills (Custom Slash Commands)

Skills = reusable markdown files in `.claude/commands/`.

**Workflow Skills:**
- `/pr` — Automated PR creation with commit splitting
- `/tdd` — Test-driven development workflow
- `/review` — Multi-perspective code review (Product, Dev, QA, Security, DevOps, UX)

**Analysis:**
- `/five` — Five Whys root cause analysis
- `/ux` — UX designer persona
- `/test` — Unit testing best practices
- `/todo` — Task management in todos.md

**Security:** Skills execute with full project access. Only use trusted skills.

**Creating Skills:**
```bash
mkdir -p .claude/commands
# File format: skill-name.md (lowercase, hyphens)
# Structure: # Title, ## Behavior, ## Guidelines, ## Examples
```

### MCP (Model Context Protocol)

Registry: https://registry.modelcontextprotocol.io/ (launched Sept 2025)
Donated to Agentic AI Foundation (Linux Foundation) for vendor-neutral dev.

**Three Pillars:** Tools (AI-controlled), Resources (app-controlled), Prompts (user-controlled)

**Playwright MCP:**
```bash
claude mcp add playwright npx '@playwright/mcp@latest'
```

### Agent Teams (Experimental 2026)

Enable: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
- Team leads coordinate specialist agents
- Shared task lists for synchronization
- Parallel execution

### Hooks

Events: PreToolUse, PostToolUse, Notification, UserPromptSubmit, Stop, SubagentStop, SessionEnd, PreCompact, SessionStart, TeammateIdle, TaskCompleted

Exit code 0 = success; exit code 2 = block execution.
Hooks can return JSON for PreToolUse (permissionDecision), PostToolUse (decision, additionalContext), UserPromptSubmit.

### Workflows

**Explore > Plan > Code > Commit:**
Read files > create plan (use "think", "think hard", "ultrathink") > implement > commit

**Test-Driven:** Write tests > confirm fail > implement > confirm pass > commit

**Visual Iteration:** Code > screenshot > iterate > commit

### Git Worktrees

Multiple Claude sessions on different branches simultaneously. No interference.

### Best Practices

**Do:** Descriptive kebab-case names, one workflow per skill, test edge cases, document, commit to `.claude/commands/`
**Don't:** Run untrusted skills, overload single skills, use ambiguous instructions, create circular references

### Important 2026 Changes

- Pro includes ALL Claude models
- Model IDs: `claude-opus-4-6`, `claude-sonnet-4-5-20250929`, `claude-haiku-4-5-20251001`
- MCP governed by foundation
- Agent Teams experimental
- 1M context in API beta only

### Resources

- Docs: https://code.claude.com/docs/en/overview
- MCP Registry: https://registry.modelcontextprotocol.io/
- Models: https://platform.claude.com/docs/en/about-claude/models/overview
