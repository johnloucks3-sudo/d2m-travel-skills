# CLINE CLI USER MANUAL — THUNDERBIRD WING
## Dreams2Memories Travel, LLC · v1.0 · 31 MAR 2026

---

## 1. WHAT IS CLINE CLI?

Cline CLI 2.11 is an open-source AI agent that runs in your terminal. It replaces Goose as the Thunderbird Wing's background task runner. It runs on **Gemini 2.5 Flash** (free tier) and supports headless/daemon operation via systemd or cron.

**Key advantages over Goose:**
- Native MCP support (can share Thunderbird's 97-tool MCP server)
- Model-agnostic (Gemini, Anthropic, OpenAI, Ollama, Bedrock)
- YOLO mode (`-y`) for fully autonomous execution
- JSON output (`--json`) for machine-readable results
- Auto-condense for long context management

**Location:** `/home/john/.local/bin/cline`
**Config:** `~/.cline/data/`
**Version:** 2.11.0

---

## 2. QUICK START

### Run a one-shot task
```bash
cline "Summarize the files in ~/Thunderbird/intel/"
```

### Run fully autonomous (no confirmations)
```bash
cline -y "Rotate logs in ~/Thunderbird/logs/ older than 7 days"
```

### Run with timeout
```bash
cline -y -t 120 "Run the daily innovation scan and write results to intel/"
```

### Run with JSON output (for scripting)
```bash
cline -y --json -t 60 "Check service health" 2>&1 | jq '.text'
```

---

## 3. KEY FLAGS

| Flag | What it does |
|------|-------------|
| `-y` / `--yolo` | Auto-approve all actions. **Required for headless/daemon use.** |
| `--json` | Output structured JSON instead of styled text |
| `-t <seconds>` | Timeout — kill the task after N seconds |
| `-m <model>` | Override model (e.g., `-m gemini-2.5-pro`) |
| `-c <path>` | Set working directory |
| `-p` / `--plan` | Plan mode — think before acting |
| `-a` / `--act` | Act mode (default) — execute immediately |
| `--auto-condense` | AI-powered context compaction for long tasks |
| `--max-consecutive-mistakes <n>` | Halt after N errors in YOLO mode |
| `--thinking [tokens]` | Enable extended thinking (default 1024 tokens) |
| `-T <id>` | Resume an existing task by ID |
| `--continue` | Resume most recent task in current directory |

---

## 4. AUTHENTICATION

Cline is configured with **Gemini 2.5 Flash** (free tier).

### Check current config
```bash
cline config
```

### Re-authenticate (if key changes)
```bash
cline auth -p gemini -k YOUR_API_KEY -m gemini-2.5-flash
```

### Supported providers
```
gemini, anthropic, openai, openai-native, openrouter, ollama,
bedrock, vertex, deepseek, groq, together, fireworks, mistral,
litellm, xai, sambanova, and 15+ more
```

### Switch to a different provider temporarily
```bash
cline -m claude-sonnet-4-6 "Complex reasoning task here"
```

---

## 5. MCP INTEGRATION

Cline supports MCP servers natively. To connect to Thunderbird's MCP server:

### Add MCP server
```bash
cline mcp
```
This opens an interactive MCP configuration screen.

### Manual MCP config
MCP servers are configured in `~/.cline/data/settings/`. The Thunderbird MCP server runs on `localhost:8765`.

---

## 6. HEADLESS / DAEMON OPERATION

### systemd service template
Create `/home/john/.config/systemd/user/cline-worker.service`:
```ini
[Unit]
Description=Cline CLI Background Worker
After=network.target thunderbird-mcp.service

[Service]
Type=oneshot
Environment="PATH=/home/john/.local/bin:/usr/local/bin:/usr/bin:/bin"
Environment="HOME=/home/john"
WorkingDirectory=/home/john/Thunderbird
ExecStart=/home/john/.local/bin/cline -y --json -t 300 "Read OpsCenter/04_GOOSE_TASK_MANIFEST.md and execute the next open task. Write completion to the manifest."
StandardOutput=append:/home/john/Thunderbird/logs/cline_worker.log
StandardError=append:/home/john/Thunderbird/logs/cline_worker.err

[Install]
WantedBy=default.target
```

### systemd timer (run every 30 minutes)
Create `/home/john/.config/systemd/user/cline-worker.timer`:
```ini
[Unit]
Description=Cline Worker Timer

[Timer]
OnCalendar=*:00/30
Persistent=true

[Install]
WantedBy=timers.target
```

### Enable
```bash
systemctl --user daemon-reload
systemctl --user enable --now cline-worker.timer
```

### Cron alternative
```bash
# Run Cline task every 30 minutes
*/30 * * * * /home/john/.local/bin/cline -y --json -t 300 -c /home/john/Thunderbird "Execute next task from OpsCenter/04_GOOSE_TASK_MANIFEST.md" >> ~/Thunderbird/logs/cline_cron.log 2>&1
```

---

## 7. THUNDERBIRD INTEGRATION PATTERNS

### Pattern A: Drop-in Goose replacement
Replace Goose task manifest references with Cline invocations:
```bash
# Instead of launching Goose with GOOSE_INIT.md:
cline -y -t 600 -c ~/Thunderbird "$(cat OpsCenter/04_GOOSE_TASK_MANIFEST.md)"
```

### Pattern B: Scripted task from task_processor.py
```python
import subprocess
result = subprocess.run(
    ["cline", "-y", "--json", "-t", "180", "-c", "/home/john/Thunderbird",
     "Run daily innovation scan and write to intel/"],
    capture_output=True, text=True, timeout=200
)
```

### Pattern C: Intel scan batch
```bash
#!/bin/bash
# Run all G4-G8 tasks sequentially with rate limiting
for task in "innovation scan" "world intelligence sweep" "tech monitor" "ship intel sweep"; do
    cline -y -t 300 -c ~/Thunderbird "Run ${task}. Write results to intel/. Include hyperlinks on every source."
    sleep 10  # Rate limit between tasks
done
```

### Pattern D: Collaboration with Claude Code
Cline writes to `OpsCenter/collaboration/claude_inbox.md`, Claude picks up via inbox watcher:
```bash
cline -y -t 120 "Research X. Write findings to OpsCenter/collaboration/claude_inbox.md as a GOOSE TASK for Claude."
```

---

## 8. TASK MANAGEMENT

### View task history
```bash
cline history
```

### Resume a task
```bash
cline --continue          # Resume most recent
cline -T <task-id>        # Resume specific task
```

### Kanban board (interactive)
```bash
cline kanban
```

---

## 9. CONFIGURATION FILES

| File | Purpose |
|------|---------|
| `~/.cline/data/globalState.json` | Provider, model, global settings |
| `~/.cline/data/settings/providerSettings.json` | API keys per provider |
| `~/.cline/data/settings/` | All settings files |
| `~/.cline/data/workspaces/` | Per-workspace state |
| `~/.cline/data/logs/` | Task execution logs |

---

## 10. TROUBLESHOOTING

### "Not authenticated"
```bash
cline auth -p gemini -k $(grep GEMINI_API_KEY ~/Thunderbird/.env | cut -d= -f2) -m gemini-2.5-flash
```

### Task hangs
Use `-t <seconds>` to enforce a timeout. YOLO mode with `--max-consecutive-mistakes 3` will halt after 3 errors.

### Rate limiting (Gemini free tier = 10 RPM)
Space batch tasks 6+ seconds apart. Use the `sleep 10` pattern between sequential tasks.

### Check what model is active
```bash
cline config
```

---

## 11. SECURITY NOTES

- **YOLO mode (`-y`)** auto-approves ALL file writes and bash commands. Use only in trusted environments (YOGA server).
- Cline can see all files in the working directory including `.env` files. Set working directory carefully.
- API keys are stored in `~/.cline/data/settings/providerSettings.json` — same security posture as `.env` files.
- No PII should be routed through Gemini free tier. Use Anthropic provider for client data.

---

## 12. QUICK REFERENCE CARD

```
# One-shot task
cline "do something"

# Autonomous + timeout
cline -y -t 120 "do something"

# JSON output for scripts
cline -y --json -t 60 "do something"

# Different model
cline -y -m gemini-2.5-pro "complex task"

# Resume last task
cline --continue

# Auth setup
cline auth -p gemini -k KEY -m gemini-2.5-flash

# MCP config
cline mcp

# Task history
cline history
```

---

*Cline CLI v2.11.0 · Installed 31 Mar 2026 · Thunderbird Wing*
*Replaces: Goose (Block Inc.) · Provider: Gemini 2.5 Flash (free tier)*
*Manual by: COS Hale via Claude Code · Dreams2Memories Travel, LLC*
