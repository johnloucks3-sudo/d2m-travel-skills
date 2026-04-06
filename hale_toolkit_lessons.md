# HALE TOOLKIT — LESSONS LEARNED
---
## Direct-Fire Groq Access (2026-04-03)
**Context:** Loucks 32-Day Validation build
**Problem:** Tried "use Groq" assuming CLI or direct model access. No `groq` binary installed. Groq API key exists in Thunderbird config but not exposed to shell sessions.

**What Actually Works:**
1. Groq models are accessible via **OpenRouter** — `curl https://openrouter.ai/api/v1/chat/completions` with models like `deepseek/deepseek-r1-distill-llama-70b:free` (routed through OpenRouter)
2. **Groq MCP tools** exist: `groqGmailQuery`, `groqCalendarQuery`, `groqDriveQuery`, `groqWorkspaceQuery`, `groqConnectorStatus` — thin query wrappers, not build engines
3. **HUD endpoint** at `script.google.com` runs on Groq backend — accessible there
4. **Claude headless** (`claude` CLI) is the proven contractor — default to `claude -p "..." ` for headless fire-and-forget

**Lesson Captured:**
- Do NOT say "use Groq" without specifying the access path (OpenRouter curl / MCP tool / HUD)
- For direct-fire LLM tasks: use `claude -p` (headless) or OpenRouter API calls
- Groq is the HUD brain, not a CLI tool. Don't confuse the two.
- When suggesting a model: always state the execution path, not just the name.

---
