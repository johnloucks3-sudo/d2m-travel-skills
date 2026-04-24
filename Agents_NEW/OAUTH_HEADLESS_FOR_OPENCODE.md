# OAuth Headless Pattern for OpenCode Models
## Thunderbird OS | DeepSeek/OpenCode Integration | 2026-04-23

---

## What This Is

When you (OpenCode) dispatch headless Claude tasks via `claude -p`, you now have automatic access to cached Google OAuth tokens. No re-authentication. No expired token errors. Seamless Google API access.

**This document:** How to use it. When to use it. How to troubleshoot when it doesn't.

---

## Why You Need This

**Problem:** Headless Claude tasks that read Gmail, write to Drive, or access Google Sheets fail because tokens expire between runs.

**Solution:** Formalized OAuth token injection. Your headless Claude calls automatically inherit fresh Google credentials.

**Benefit for you:** Write fire-and-forget tasks without worrying about auth plumbing.

---

## Quick Start

### Option A: Use the Wrapper (Simplest)

```bash
# For simple one-off headless Claude tasks
~/claude_with_oauth.sh "Read the file ~/Thunderbird/CLAUDE.md and summarize the standing orders to stdout"

# With logging
~/claude_with_oauth.sh "Your task here" > /tmp/task.log 2>&1 &
```

**When to use:** Any `claude -p` task. The wrapper auto-injects tokens. No setup needed.

---

### Option B: Direct Environment Export (For Bash Scripts)

```bash
#!/bin/bash
# Your script that calls claude -p

# Export OAuth tokens
export GOOGLE_OAUTH_TOKEN=$(jq -r '.access_token' ~/.claude/oauth/google_token.json)
export DRIVE_TOKEN_PATH=~/.claude/oauth/google_token.json

# Now claude -p calls have token access
claude -p "Read from Gmail and summarize to Drive"
```

**When to use:** Long-running scripts or multi-step workflows where you need tokens available to subprocess Claude calls.

---

### Option C: Python Subprocess with Token Env

```python
import subprocess
import json
import os

# Load token
oauth_cache = os.path.expanduser('~/.claude/oauth/google_token.json')
with open(oauth_cache) as f:
    token_data = json.load(f)

# Set up environment for subprocess
env = os.environ.copy()
env['GOOGLE_OAUTH_TOKEN'] = token_data['access_token']
env['DRIVE_TOKEN_PATH'] = oauth_cache

# Call headless Claude
result = subprocess.run(
    ['claude', '-p', 'Your task here'],
    env=env,
    capture_output=True,
    text=True
)
print(result.stdout)
```

**When to use:** When you're orchestrating multiple tasks in Python and need fine-grained token control.

---

## Real-World Examples

### Example 1: Scan Gmail Inbox → Summarize to Drive

```bash
#!/bin/bash
# OpenCode task: daily email digest

LOG="/tmp/opencode_email_digest.log"
TASK_PROMPT="
Read all unread emails from johnloucks3@gmail.com from the last 24 hours.
For each email:
  - Extract sender, subject, key points
  - Note any action items for Commander
Create a summary and write to Google Drive file: /Thunderbird/intel/daily_email_digest.md
"

~/claude_with_oauth.sh "$TASK_PROMPT" > "$LOG" 2>&1 &
echo "Email digest task spawned (PID: $!). Output: $LOG"
```

---

### Example 2: Research Task with Drive Integration

```bash
#!/bin/bash
# OpenCode task: competitive intelligence sweep

RESEARCH_PROMPT="
1. Search for news about Silversea cruise line (last 48 hours)
2. Extract: pricing changes, new routes, customer reviews, operational news
3. Save results as JSON to Google Drive: /Thunderbird/intel/silversea_sweep_2026-04-23.json
4. Include sources and timestamps
"

~/claude_with_oauth.sh "$RESEARCH_PROMPT" > /tmp/research.log 2>&1
tail -20 /tmp/research.log
```

---

### Example 3: Multi-Step Workflow (Python)

```python
#!/usr/bin/env python3
# OpenCode: Build daily brief with Drive persistence

import subprocess
import json
import os
from datetime import datetime

oauth_cache = os.path.expanduser('~/.claude/oauth/google_token.json')
with open(oauth_cache) as f:
    token = json.load(f)['access_token']

def run_claude_task(prompt):
    """Run headless Claude with OAuth token"""
    env = os.environ.copy()
    env['GOOGLE_OAUTH_TOKEN'] = token
    result = subprocess.run(
        ['claude', '-p', prompt],
        env=env,
        capture_output=True,
        text=True
    )
    return result.stdout + result.stderr

# Step 1: Gather intelligence
print("[*] Scanning world intel...")
intel_output = run_claude_task("""
Search for travel industry news (last 24h):
- Cruise line updates
- Travel tech news
- Competitor pricing
Return as JSON with sources.
""")

# Step 2: Save to Drive
print("[*] Saving intel to Drive...")
brief_prompt = f"""
Take this intelligence report and save to Google Drive file: /Thunderbird/intel/daily_brief_{datetime.now().strftime('%Y-%m-%d')}.md

Intelligence:
{intel_output}

Format as markdown with sections, links, and key findings.
"""

run_claude_task(brief_prompt)
print("[✓] Daily brief complete")
```

---

## Architecture Overview

```
OAuth Token Cache (~/.claude/oauth/google_token.json)
    ↓ (auto-refreshed every 30 min)
    ↓
Systemd environment file (~/.config/systemd/user/oauth.env)
    ↓
Wrapper script (~/claude_with_oauth.sh) OR direct env export
    ↓
Your headless claude -p task
    ↓
Claude inherits $GOOGLE_OAUTH_TOKEN, calls Google APIs without re-auth
```

---

## Token Lifecycle (What Happens Behind the Scenes)

1. **Initial:** You (OpenCode) are told to run a task → call `~/claude_with_oauth.sh` or set env
2. **Wrapper startup:** Reads `~/.claude/oauth/google_token.json` → extracts access token → exports as `$GOOGLE_OAUTH_TOKEN`
3. **Claude startup:** Claude receives env var with valid token
4. **Google API calls:** Claude uses token to call Gmail, Drive, Sheets APIs without prompting for credentials
5. **Token expiry:** If token expires, systemd auto-refresh hook (runs every 30 min) refreshes it

**Key point:** You don't think about tokens. They're automatically fresh.

---

## When to Use What

| Scenario | Use |
|----------|-----|
| Quick one-off Claude task | `~/claude_with_oauth.sh "prompt"` |
| Bash script spawning Claude | `export GOOGLE_OAUTH_TOKEN=$(jq -r '.access_token' ~/.claude/oauth/google_token.json)` |
| Python orchestrating tasks | Load token in Python, pass via subprocess `env=` |
| Systemd daemon/timer | Service file has `EnvironmentFile=%h/.config/systemd/user/oauth.env` |
| Long-running loop with multiple Claude calls | Set env once at top, reuse in loop |

---

## Troubleshooting

### "OAuth cache not found"

```bash
# This means the token hasn't been created yet
# Solution: Run Claude Code interactively first to set up OAuth
claude code
# (This creates ~/.claude/oauth/google_token.json)

# Then try your task again
~/claude_with_oauth.sh "Your task"
```

---

### "Token extraction failed"

```bash
# Check if token file is valid JSON
jq . ~/.claude/oauth/google_token.json

# If corrupted, delete and re-create
rm ~/.claude/oauth/google_token.json
claude code  # Triggers OAuth flow
```

---

### "Claude can't access Google APIs even with token"

**Check 1:** Token is exported to subprocess
```bash
# Add debug line to your script
echo "Token available: ${GOOGLE_OAUTH_TOKEN:-NOT SET}" >> /tmp/debug.log
```

**Check 2:** Token is valid (not expired)
```bash
# Check token age
jq '.issued_at' ~/.claude/oauth/google_token.json

# If very old, force refresh
systemctl --user start hale-oauth-refresh.service
```

**Check 3:** Wrapper is being used
```bash
# Test wrapper directly
~/claude_with_oauth.sh "echo test"

# Should see token exported (or error about missing token)
```

---

## Advanced: Adding New Services

If you write a new daemon or long-running service that needs Google API access:

**Option 1: Use the wrapper in your script**
```bash
RESULT=$(~/claude_with_oauth.sh "Your task")
echo "$RESULT"
```

**Option 2: Source the oauth.env in your systemd service**
```ini
[Service]
EnvironmentFile=%h/.config/systemd/user/oauth.env
ExecStart=/path/to/your/script.sh
```

---

## Security Notes

- **Token in environment:** The token will be visible in `ps aux` output while Claude runs. Accept this risk for automation convenience.
- **Token in files:** Keep `~/.claude/oauth/` as mode 700 (user-only access).
- **Rotation:** Tokens expire every ~1 hour. The auto-refresh hook updates them every 30 min. You don't need to do anything.
- **Revocation:** If you revoke Google OAuth access, you'll need to re-authenticate via `claude code` to regenerate tokens.

---

## Testing This Right Now

### Test 1: Basic Wrapper Test
```bash
~/claude_with_oauth.sh "Just echo the phrase: 'OpenCode OAuth test successful'"
```
Expected: Claude runs, echo prints result (or auth error if token missing).

### Test 2: Gmail Integration
```bash
~/claude_with_oauth.sh "
Check Gmail (johnloucks3@gmail.com) for any messages from the past hour.
List sender, subject, and first line of each.
"
```
Expected: Claude lists recent emails (or no emails if inbox empty).

### Test 3: Drive Integration
```bash
~/claude_with_oauth.sh "
Create a test file at Google Drive: /Thunderbird/test_oauth_2026-04-23.txt
Content: 'OpenCode OAuth integration test - timestamp: $(date)'
Confirm file created.
"
```
Expected: File created in Drive (or Drive API error if perms missing).

---

## What to Report Back to Commander

After testing, report:
- [ ] Wrapper executable: `ls -l ~/claude_with_oauth.sh`
- [ ] OAuth cache exists: `ls ~/.claude/oauth/google_token.json`
- [ ] Token is valid: `jq '.access_token' ~/.claude/oauth/google_token.json | head -c 20`...
- [ ] Wrapper test passed (Test 1 above)
- [ ] Gmail test passed (Test 2 above) — optional, depends on email permissions
- [ ] Drive test passed (Test 3 above) — optional, depends on Drive permissions

---

## Questions?

Refer to:
- **How it works:** `/home/john/OAUTH_HEADLESS_PATTERN.md` (detailed)
- **Wrapper code:** `~/claude_with_oauth.sh` (read it)
- **Service config:** `~/.config/systemd/user/oauth.env` (environment variables)
- **Systemd services:** `~/.config/systemd/user/hale-*.service` (examples)

---

*OpenCode/DeepSeek Integration Guide | Thunderbird OS | 2026-04-23*
