# Agents_NEW — Agent Integration Guides
## Thunderbird OS | Guides for OpenCode, Goose, and Specialist Models

This directory contains operational guides written specifically for autonomous AI agents (OpenCode, Goose, DeepSeek, etc.) to understand Thunderbird OS patterns and execute tasks effectively.

---

## Files

### `OAUTH_HEADLESS_FOR_OPENCODE.md` (READ FIRST)
**For:** OpenCode, headless Claude tasks, DeepSeek
**What:** How to use the OAuth token injection pattern for Google API access from headless tasks
**When:** Before running any task that needs Gmail, Drive, Sheets, or Calendar access
**Key content:**
- Quick start (3 options for using the wrapper)
- Real-world examples (email digest, research, Drive integration)
- Testing procedures
- Troubleshooting guide

---

## How to Use This Directory

### For OpenCode/DeepSeek Models
When you're tasked with a headless job that needs Google API access:
1. Read `OAUTH_HEADLESS_FOR_OPENCODE.md`
2. Choose your approach (wrapper, env export, or Python subprocess)
3. Implement the pattern
4. Test using the examples provided
5. Report results back

### For Hale (COS)
When onboarding a new agent or enabling a new capability:
1. Write a guide in this directory explaining the pattern
2. Include: purpose, quick start, examples, troubleshooting
3. Reference it when tasking agents on that capability

---

## Future Guides (Placeholder)

These will be added as new capabilities are formalized:
- `MCP_FOR_OPENCODE.md` — How to call MCP tools from headless tasks
- `DRIVE_SYNC_FOR_AGENTS.md` — Syncing local files to Google Drive
- `TELEGRAM_INTEGRATION_FOR_AGENTS.md` — Broadcasting to Telegram from daemons
- `DOSSIER_UPDATES_FOR_AGENTS.md` — Reading/writing dossiers programmatically
- `EMAIL_DRAFTING_FOR_AGENTS.md` — Creating Gmail drafts without send

---

## Style Guide for New Guides

When writing an agent integration guide:
1. **Start with the problem:** Why does the agent need this pattern?
2. **Quick start:** 3 simple ways to get started (pick one method)
3. **Real examples:** Copy-paste-ready code snippets for common tasks
4. **Troubleshooting:** Common errors and how to fix them
5. **Testing:** Concrete tests the agent can run right now
6. **Report template:** What to say back when the test succeeds

Assume the agent:
- Is competent (can write Python, Bash, understand auth)
- Doesn't want to read long documents (keep sections short)
- Wants concrete examples, not theory
- Will forget details after first run (make troubleshooting clear)

---

*Agents_NEW | Integration Guides | Thunderbird OS | 2026-04-23*
