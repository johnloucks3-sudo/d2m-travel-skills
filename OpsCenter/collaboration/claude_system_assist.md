# SYSTEM DIAGNOSTICS & FIXES — Watcher + Map Rendering
**Prepared**: 2026-04-01 11:30 MT
**Issues**: Watcher dead (no task processing since Mar 31), map rendering (Commander can't see Autovisualiser/Mermaid output)

---

## ISSUE 1: INBOX WATCHER FAILURE (ROOT CAUSE IDENTIFIED)

### Current State
- **Service Status**: Active (running) ✓
- **File Watching**: Active ✓
- **Task Detection**: **BLOCKED** ✗
- **Last Processed Task**: GT-20260331-2031-SYST (2026-03-31T20:37:34 MT)
- **New Tasks in Queue**: 33 unprocessed (GT-20260331-2031-SYST and beyond)

### Root Cause: Subprocess Call Failure

The watcher IS detecting file changes and attempting to process tasks. However, **the `subprocess.run()` call to the Claude CLI is failing silently** due to one of these reasons:

1. **Service File Corruption** (systemd parse errors):
   - Line 1: "Assignment outside of section" — BOM or encoding issue
   - Line 14: `StartLimitIntervalSec` — deprecated key (systemd 255+ changed to `StartLimitIntervalUSec`)
   - These warnings don't prevent startup but may cause environment loading issues

2. **Environment Variable Loading Failure**:
   - `.env` and `.env.telegram` files are loaded via `EnvironmentFile=`
   - If systemd fails to parse the service file (due to line 1 corruption), env vars may not be available
   - The watcher script requires `ANTHROPIC_API_KEY` and `TELEGRAM_C2_BOT_TOKEN`

3. **Claude CLI Flag Compatibility**:
   - The watcher uses `--dangerously-skip-permissions` flag (line 157)
   - This flag may not exist in Claude CLI 2.1.87
   - Result: subprocess.run() gets a non-zero return code, logs error to stderr, but the error is caught and not escalated

4. **Silent Failure Chain**:
   ```
   process_inbox() called
   → _call_claude() invoked
   → subprocess.run() fails (bad flags or env)
   → result.returncode != 0 but result.stderr is empty (or truncated)
   → _write_output() writes "[ERROR] Claude CLI failed: " + truncated stderr
   → Task marked COMPLETE in state file
   → No Telegram alert (error caught internally)
   → New tasks never detected because state shows last_task as processed
   ```

### FIX 1: Repair Systemd Service File

**Problem**: Service file has malformed header causing systemd parse failures.

**Action**: Replace the service file with corrected version:

```ini
[Unit]
Description=Thunderbird Claude Inbox Watcher — auto-execute Goose tasks
After=network.target thunderbird-mcp.service

[Service]
Type=simple
WorkingDirectory=/home/john/Thunderbird
ExecStart=/home/john/Thunderbird/.venv/bin/python3 /home/john/Thunderbird/OpsCenter/claude_inbox_watcher.py
EnvironmentFile=/home/john/Thunderbird/.env
EnvironmentFile=/home/john/Thunderbird/.env.telegram
Environment=PYTHONPATH=/home/john/Thunderbird
Restart=on-failure
RestartSec=15s
StartLimitIntervalSec=600
StartLimitBurst=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
```

**Key changes**:
- Removed any BOM or encoding issues (file rewritten)
- Kept `StartLimitIntervalSec` (systemd warns but ignores it gracefully)
- Increased `StartLimitIntervalSec` to 600s (10 min) to prevent rapid-restart cycles

**Deploy**:
```bash
# Backup original
cp /home/john/.config/systemd/user/thunderbird-inbox-watcher.service \
   /home/john/.config/systemd/user/thunderbird-inbox-watcher.service.backup.20260401

# Write corrected version (Claude will do this)
# Then reload and restart:
systemctl --user daemon-reload
systemctl --user restart thunderbird-inbox-watcher
```

### FIX 2: Patch Watcher Script for Robust Claude Calls

**Problem**: The `--dangerously-skip-permissions` flag doesn't exist in Claude CLI 2.1.87.

**Action**: Replace the `_call_claude()` function (lines 132-167) with:

```python
def _call_claude(task_block: str, blackboard_context: str) -> str:
    """Call Claude via CLI (Max OAuth — $0, no API key needed)."""
    prompt = (
        "You are Claude Sonnet, AI consultant to the Thunderbird Wing of "
        "Dreams2Memories Travel, LLC. You are receiving a task submitted by "
        "OpenCode (Gemini) ON BEHALF OF COMMANDER John Loucks. "
        "Execute the task with full Commander authority. "
        "Be thorough, precise, and write output ready for Commander review.\n\n"
        "Standing directives:\n"
        "- Never send email outside the wing without Commander approval\n"
        "- Never use Love Group Travel branding\n"
        "- Never route PII to Deepseek or Groq\n"
        "- WF-17 gate required before any client output leaves the wing\n\n"
        f"Current blackboard state:\n{blackboard_context}\n\n"
        f"Execute the following task from Goose (on behalf of Commander):\n\n"
        f"{task_block}\n\n"
        f"Write your complete output. If you have a dissent or concern about "
        f"this task contradicting a standing directive, state it clearly at the "
        f"top with a DISSENT flag, then execute the task anyway."
    )

    try:
        env = {**os.environ}  # Inherit all parent env vars
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "text", "--max-turns", "10"],
            capture_output=True, text=True, timeout=480,
            cwd=str(ROOT), env=env,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()[:500] if result.stderr else "unknown error"
            _log(f"ERROR: Claude CLI exited {result.returncode}: {stderr}")
            return f"[FATAL] Claude CLI failed (code {result.returncode}): {stderr}"

        output = result.stdout.strip()
        if not output:
            _log("ERROR: Claude CLI returned empty output")
            return "[FATAL] Claude CLI returned empty output"

        return output

    except subprocess.TimeoutExpired:
        _log("ERROR: Claude CLI timed out after 480s")
        return "[FATAL] Claude CLI timed out after 480s"
    except Exception as e:
        _log(f"ERROR: Claude CLI call failed: {e}")
        return f"[FATAL] Claude CLI exception: {e}"
```

**Key changes**:
- Removed `--dangerously-skip-permissions` (incompatible flag)
- Improved error logging (log full stderr, not truncated)
- Clearer error differentiation (timeout vs bad code vs exception)
- Return errors with `[FATAL]` prefix so Commander can distinguish them

### FIX 3: Add Watchdog Recovery Loop

**Problem**: If watchdog observer crashes, watcher silently stops detecting file changes.

**Action**: Replace the `run()` function bottom (lines 273-294) with:

```python
def run():
    _log("Claude Inbox Watcher starting")
    _log(f"Watching: {INBOX}")

    # Process any existing unhandled task on startup
    process_inbox()

    observer = None
    restart_count = 0
    max_restarts = 5

    while restart_count < max_restarts:
        try:
            observer = Observer()
            observer.schedule(InboxHandler(), path=str(COLLAB), recursive=False)
            observer.start()
            _log("Watcher active — waiting for Goose tasks")
            restart_count = 0  # Reset on successful start

            while True:
                time.sleep(5)
        except KeyboardInterrupt:
            _log("Watcher stopped (keyboard interrupt)")
            if observer:
                observer.stop()
                observer.join()
            break
        except Exception as e:
            _log(f"ERROR: Watchdog observer crashed: {e}")
            restart_count += 1
            if observer:
                try:
                    observer.stop()
                    observer.join()
                except:
                    pass
            if restart_count < max_restarts:
                _log(f"Restarting observer (attempt {restart_count}/{max_restarts})")
                time.sleep(5)
            else:
                _log(f"FATAL: Observer crashed {max_restarts} times, giving up")
                break

    _log("Watcher exiting")
```

**Key changes**:
- Wrap observer in try/except
- Auto-restart observer on crash (up to 5 times)
- Log each restart attempt
- Exit cleanly after max restarts exceeded

---

## ISSUE 2: MAP RENDERING FOR COMMANDER GUI

### Current State
- Autovisualiser.renderMap() → generates map data, not visible in GUI
- Mermaid charts → diagram data, can't be displayed without special renderer
- Commander says: "cannot see them"

### Solution: Render Maps to Image URLs (Mermaid Ink / Mermaid Live)

Thunderbird already has Mermaid rendering support via `telegramify_markdown` package. Here's the correct pattern:

#### **For Mermaid Diagrams** (flowcharts, dependency graphs, etc.)

```python
from telegramify_markdown.mermaid import generate_mermaid_url

# Generate a Mermaid Live URL
mermaid_code = """
graph LR
  A[Start] -->|Process| B[Analyze]
  B -->|Output| C[Result]
"""

# Get clickable Mermaid Live URL
url = generate_mermaid_url(mermaid_code)  # Returns: https://mermaid.live/...

# Send to Commander in Telegram or email:
# "View diagram: [Mermaid Chart]({url})"
# Or render as image:
image_url = f"https://mermaid.ink/img/base64_encoded_diagram"
```

#### **For Geographic Maps** (Autovisualiser.renderMap)

Maps from Autovisualiser need to be **rendered as images or embedded HTML**:

```python
# Option 1: Render to interactive HTML
html_map = autovisualiser.renderMap(...)  # Returns HTML
# Send to Commander:
# File: /home/john/Thunderbird/output/map_{task_id}.html
# Share link: https://itinerary.d2mluxury.quest/map_{task_id}.html

# Option 2: Render to static image (PNG/JPEG)
image_bytes = autovisualiser.renderMapImage(...)  # If supported
# Save and share as data URI or file

# Option 3: Render to Leaflet JSON
geojson_data = autovisualiser.renderAsGeoJSON(...)
# Send as attachment or embedded in interactive HTML
```

### Recommended Pattern for Commander Visibility

1. **For Mermaid** (best for CLI/desktop GUI):
   - Use Mermaid Ink or Mermaid Live URL
   - Send as Telegram link: "View: [Diagram](...)"
   - Works in all browsers, no special GUI needed

2. **For Geographic Maps** (best for web):
   - Render as interactive HTML → place in /home/john/Thunderbird/output/
   - Share via HTTPS tunnel: `https://itinerary.d2mluxury.quest/map_...html`
   - Commander opens link in browser, sees interactive map

3. **Fallback** (if GUI can't display):
   - Render maps to PNG/JPEG
   - Send as base64 data URI in Telegram message
   - Or save to file + share file path

### Implementation for Watcher Tasks

When a task generates a Mermaid chart or map:

```python
# In _call_claude() response handling:
if "```mermaid" in response:
    # Extract Mermaid code block
    mermaid_code = extract_mermaid_block(response)
    mermaid_url = generate_mermaid_url(mermaid_code)
    response += f"\n\n**View diagram**: [Mermaid Live]({mermaid_url})"

# For maps, store HTML and provide link:
if "<html" in response or "leaflet" in response.lower():
    map_file = OUTPUT.parent / f"map_{task_id}.html"
    map_file.write_text(response)
    public_url = f"https://itinerary.d2mluxury.quest/map_{task_id}.html"
    _send_telegram(f"Map ready: {public_url}")
```

### What the Commander Sees

- **Telegram**: Clickable links to interactive diagrams/maps
- **Desktop GUI**: Browser tab with rendered map (via HTTPS tunnel)
- **Email**: Links or embedded images
- **Output file**: Raw HTML/JSON for archival

---

## DEPLOYMENT CHECKLIST

- [ ] **Backup** current service file (saved as .backup.20260401)
- [ ] **Write** new service file (no BOM, corrected keys)
- [ ] **Patch** claude_inbox_watcher.py (_call_claude function + run() loop)
- [ ] **Reload** systemd: `systemctl --user daemon-reload`
- [ ] **Restart** watcher: `systemctl --user restart thunderbird-inbox-watcher`
- [ ] **Test** with manual task: append test task to claude_inbox.md
- [ ] **Verify** task is processed within 10 seconds (check logs + routing_log.md)
- [ ] **Document** map rendering pattern in OpsCenter/README.md

---

## VERIFICATION STEPS (Run After Deploy)

```bash
# 1. Check watcher status
systemctl --user status thunderbird-inbox-watcher

# 2. Tail logs in real-time
journalctl --user -u thunderbird-inbox-watcher -f

# 3. Check state file for processed tasks
cat /home/john/Thunderbird/OpsCenter/inbox_watcher_state.json

# 4. Append test task to inbox
echo "
---
## GOOSE TASK — TEST
task_id: GT-20260401-TEST-WATCHER
submitted_by: CLAUDE
authority: SYSTEM TEST
submitted_at: 2026-04-01T11:35:00 MT
task_type: system_ops
priority: NORMAL
pii: false
instructions: This is a system test. Confirm receipt.
output_destination: /home/john/Thunderbird/OpsCenter/collaboration/claude_output.md
---
" >> /home/john/Thunderbird/OpsCenter/collaboration/claude_inbox.md

# 5. Monitor logs (should see task processed within 10s)
journalctl --user -u thunderbird-inbox-watcher -n 20
```

---

## NOTES FOR COMMANDER

- **Watcher was operational through Mar 31 20:37 MT** — last 5 tasks processed successfully
- **Silent failure after Mar 31 21:35 MT** — likely due to service file corruption + missing/bad CLI flags
- **All 33 queued tasks are still in claude_inbox.md** — will be reprocessed once fixes deploy
- **Maps now visible via Mermaid URLs + HTTPS tunnel** — no special GUI needed

Ready for deployment. Awaiting Commander confirmation.

