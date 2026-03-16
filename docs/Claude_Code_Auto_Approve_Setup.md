# Claude Code — Reducing Approval Prompts
## Setup Guide for Dreams2Memories / Thunderbird Project

---

## Option 1: Project-Level CLAUDE.md (Recommended for this project)
Create `~/Thunderbird/CLAUDE.md` with project-specific permissions and instructions.

## Option 2: Use `/permissions` Command
Type `/permissions` in Claude Code to interactively manage which tools auto-approve.

## Option 3: Skip All Permissions (Use with Caution)
```bash
claude --dangerously-skip-permissions
```
Skips ALL approval prompts. Fast but no safety net.

## Option 4: Targeted Auto-Approve (Best Balance)
```bash
claude config set --global autoApprove "Read,Write,Edit,Glob,Grep,WebSearch,WebFetch,mcp__dreams2memories__*"
```
Auto-approves file operations, web searches, and all MCP travel tools. Still prompts for destructive operations (git push, rm, etc.).

---

## Recommended: Combine Options 1 + 4

### Step 1: Set global auto-approve
```bash
claude config set --global autoApprove "Read,Write,Edit,Glob,Grep,WebSearch,WebFetch,mcp__dreams2memories__*"
```

### Step 2: Create ~/Thunderbird/CLAUDE.md
```markdown
# Thunderbird Project — Dreams2Memories Travel Automation

## Permissions
- Allow all file reads, writes, and edits in this project without confirmation.
- Allow all MCP tool calls (dreams2memories) without confirmation.
- Allow web searches and fetches without confirmation.
- Allow bash commands for non-destructive operations without confirmation.

## Project Notes
- Working directory: ~/Thunderbird/
- MCP Server: travel_mcp_server.py (dreams2memories_travel_mcp)
- Primary tools: hotel search, cruise research, itinerary generation, Drive sync
- Commission default: 25% (22% for SLH/premium properties)
```

### Step 3: Verify settings
```bash
claude config list
```
