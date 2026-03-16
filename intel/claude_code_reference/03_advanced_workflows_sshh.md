# How I Use Every Claude Code Feature — Advanced Workflows
## Source: blog.sshh.io/p/how-i-use-every-claude-code-feature
## Author: Shrivu Shankar (enterprise Claude Code user)
## Saved: 2026-03-09 by Thunderbird OS

---

## D2M EXECUTIVE SUMMARY

This is the most operationally valuable article of the three. Written by someone running Claude Code in an enterprise monorepo. Key takeaways for Thunderbird OS:

**Context Management (Critical for our 97-tool MCP):**
- Avoid `/compact` — it's opaque and error-prone. Use `/clear` + restart instead.
- Run `/context` mid-session to check token allocation. Monorepo baseline ~20K tokens (10%).
- For complex multi-step tasks: have Claude dump progress to .md file, `/clear`, then continue from the doc. This prevents context degradation.

**MCP Architecture Insight (Validates + Challenges our approach):**
- MCP should be reserved for **complex stateful environments** (like Playwright browser sessions).
- Stateless integrations (Jira, AWS, GitHub) work better as simple CLIs.
- Our MCP is justified for Google Workspace (stateful auth), Playwright, Hotelbeds — but simpler tools could potentially be CLI wrappers.
- Effective MCP tools should be high-level: `download_raw_data()`, `take_gated_action()`, `execute_code_with_state()`.

**Hooks Strategy (Implement This):**
- Block at COMMIT stage, not write stage. Blocking mid-plan confuses agents.
- Use `PreToolUse` hook on `Bash(git commit)` — check for `/tmp/agent-pre-commit-pass` file.
- Hint hooks (non-blocking) for suboptimal patterns.

**Subagent Warning (Affects our persona system):**
- Custom subagents "gatekeep context" from the main agent — prevents holistic reasoning.
- Better: put key context in CLAUDE.md, let main agent spawn `Task()` clones dynamically.
- Our personas work differently (Groq-powered, not Claude subagents), so this doesn't directly apply, but worth noting if we ever make personas into Claude subagents.

**Skills > MCP for most workflows:**
- Skills formalize the "scripting" model — agents write code to interact with CLIs/scripts.
- More flexible than rigid MCP tool definitions.
- Could convert some of our simpler MCP tools into skills.

**GitHub Action pattern:**
- Run `query-claude-gha-logs --since 5d | claude -p "identify common stuck points"` for continuous improvement. Could apply to our MCP error logs.

---

## FULL ARTICLE

### CLAUDE.md

Foundational file as agent's operational guide. For monorepos: strictly curated 13KB, documenting only tools used by 30%+ of engineers.

**Key Principles:**

1. **Start with Guardrails, Not Manuals** — Document issues as they arise, not upfront.

2. **Avoid @-Filing Docs** — Bloats context. Instead pitch "why" and "when" to read files: "For complex usage or if you encounter a FooBarError, see path/to/docs.md."

3. **Provide Alternatives to Restrictions** — Not "Never use --foo-bar flag" but "Prefer alternative-flag instead."

4. **Use as Forcing Function** — Simplify CLI commands through wrappers. If CLAUDE.md needs extensive docs for a tool, the tool's UX is broken.

Sync CLAUDE.md with AGENTS.md for compatibility with other AI IDEs.

### Context Management

Run `/context` mid-session to understand token allocation. Monorepo baseline: ~20,000 tokens (10% of 200k), leaving 180,000 for actual work.

**Three Workflows:**

1. **/compact (Avoid)** — Automatic compaction is opaque and error-prone.

2. **/clear + /catchup (Simple Restart)** — Clear state, then custom command reads changed files in git branch.

3. **Document & Clear (Complex Restart)** — Claude dumps progress to markdown, clear state, continue from documentation.

### Custom Slash Commands

Minimal setup:
- `/catchup` — Read all changed files in current branch
- `/pr` — Clean code, stage changes, prepare PR

Philosophy: If you need extensive custom command documentation, redesign the underlying tools. Agents should handle natural language without learned command syntax.

### Custom Subagents

Two problems:
1. **Context Gatekeeping** — Hiding testing context from main agent prevents holistic reasoning
2. **Rigid Workflows** — Forcing Claude into human-defined delegation contradicts autonomous decision-making

**Preferred: "Master-Clone" architecture.** Put key context in CLAUDE.md, let main agent decide when/how to spawn `Task()` clones. Agent manages orchestration dynamically.

**Parallel scripting pattern:**
```bash
claude -p "in /pathA change all refs from foo to bar"
# Run multiple instances in parallel for large-scale refactors
```

### Resume, Continue & History

`claude --resume` and `claude --continue` for session management. Analyze historical session data in `~/.claude/projects/` to identify common exceptions and error patterns for CLAUDE.md improvement.

### Hooks

**Two Types:**

1. **Block-at-Submit Hooks** — `PreToolUse` wraps `Bash(git commit)`. Test script creates `/tmp/agent-pre-commit-pass` only if all tests pass. Missing file = blocked commit = forced test-and-fix loop.

2. **Hint Hooks** — Non-blocking feedback for suboptimal patterns.

**Critical:** Avoid write-time blocks (on Edit/Write operations). Blocking mid-plan confuses agents. Validate at commit stage instead.

### Planning Mode

Essential for large features. Built-in planning mode defines:
- How to build
- Inspection checkpoints
- Minimal context needed

Enterprise: custom planning tool aligned with internal tech design format, enforcing security/privacy/code structure best practices.

### Skills

Potentially more significant than MCP. Formalizes "Scripting" agent model.

Agent autonomy progression:
1. Single massive prompt (brittle, unscalable)
2. Tool calling with hand-crafted abstractions (bottlenecks)
3. **Scripting with raw environment access** (most robust and flexible)

Skills productionize the scripting layer.

### MCP (Model Context Protocol)

Refined focus. Effective MCPs = secure gateways with high-level tools:
- `download_raw_data(filters...)`
- `take_sensitive_gated_action(args...)`
- `execute_code_in_environment_with_state(code...)`

MCP's role: auth/networking/security management, NOT reality abstraction.

Stateless tools (Jira, AWS) → simple CLIs.
Complex stateful environments (Playwright) → MCP justified.

### Claude Code SDK

Three applications:
1. **Massive Parallel Scripting** — Simple bash calling `claude -p "..."` in parallel
2. **Internal Chat Tools** — Wrapping complex processes in simple interfaces for non-technical users
3. **Rapid Prototyping** — Testing agentic ideas before full deployment

### GitHub Action (GHA)

Transforms Claude Code from personal tool to auditable company infrastructure.

"PR-from-anywhere" — trigger from Slack, Jira, CloudWatch with tested results.

Data-driven improvement:
```bash
query-claude-gha-logs --since 5d | claude -p "identify common stuck points and fix them, then put up a PR"
```

### settings.json Configuration

- **HTTPS_PROXY/HTTP_PROXY** — Debug raw traffic; network sandboxing for background agents
- **MCP_TOOL_TIMEOUT/BASH_MAX_TIMEOUT_MS** — Increase for complex commands
- **ANTHROPIC_API_KEY** — Enterprise: usage-based pricing (accounts for 1:100x developer variance)
- **"permissions"** — Regular self-audits of allowed auto-run commands
