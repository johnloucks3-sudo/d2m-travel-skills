#!/usr/bin/env python3
"""Upload Chromebook Field Kit guide to Google Drive."""

import sys
sys.path.insert(0, "/home/john/Thunderbird")
from thunderbird_drive import _get_drive_service
from googleapiclient.discovery import build

DEPLOY_FOLDER_ID = "1YNeH6Uq_hK8RgUoqfSoC2yliY7VmpM1P"

svc = _get_drive_service()

# Create Google Doc
file_metadata = {
    "name": "Chromebook Field Kit — Setup & Failover Guide",
    "mimeType": "application/vnd.google-apps.document",
    "parents": [DEPLOY_FOLDER_ID]
}
doc = svc.files().create(body=file_metadata, fields="id").execute()
doc_id = doc["id"]
print(f"Doc created: {doc_id}")

# Get Docs API service - reuse credentials from Drive service
creds = svc._http.credentials
docs_svc = build("docs", "v1", credentials=creds)

CONTENT = """CHROMEBOOK FIELD KIT — SETUP & FAILOVER GUIDE
Dreams2Memories Travel, LLC
Last Updated: 2026-03-09

PURPOSE
Make the HP 14 Chromebook a self-sufficient field machine that works even when the dv7 home server tunnel is down.

ARCHITECTURE OVERVIEW
Normal mode: Chromebook → Claude CLI → SSE to mcp.d2mluxury.quest → dv7 serves 97 MCP tools
Failover mode: Chromebook → Claude CLI → local stdio MCP server → tools run directly on Chromebook
The smart launcher script auto-detects which mode to use.

═══════════════════════════════════════════════════════
ONE-TIME SETUP (Do this before leaving home)
═══════════════════════════════════════════════════════

STEP 1: SYNC THE CODEBASE
Open the Linux terminal (penguin) on the Chromebook:

    mkdir -p ~/Thunderbird
    rsync -avz --exclude='.venv' --exclude='venv' \\
        --exclude='__pycache__' --exclude='*.pyc' \\
        john@10.0.0.64:~/Thunderbird/ ~/Thunderbird/

Copies the full Thunderbird codebase from dv7. ~5 min on LAN.

STEP 2: CREATE PYTHON VIRTUAL ENVIRONMENT

    cd ~/Thunderbird
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip wheel setuptools
    pip install -r requirements.txt

Installs all dependencies (~500MB). Only needed once.

STEP 3: INSTALL PLAYWRIGHT (for browser tools)

    cd ~/Thunderbird
    source venv/bin/activate
    python3 -m playwright install chromium

STEP 4: VERIFY CREDENTIAL FILES
These should already be synced by rsync. Verify they exist:

    ls ~/Thunderbird/credentials.json
    ls ~/Thunderbird/gmail_token.json
    ls ~/Thunderbird/drive_token.json
    ls ~/Thunderbird/gmail_oauth_credentials.json
    ls ~/Thunderbird/amadeus_credentials.json
    ls ~/Thunderbird/hotelbeds_credentials.json

If any are missing:
    scp john@10.0.0.64:~/Thunderbird/<filename> ~/Thunderbird/

STEP 5: CREATE MCP CONFIG FILES

Remote config (normal mode — uses dv7):

    mkdir -p ~/.claude
    cat > ~/Thunderbird/.claude/mcp-remote.json << 'EOF'
    {
      "mcpServers": {
        "dreams2memories_travel_mcp": {
          "type": "sse",
          "url": "https://mcp.d2mluxury.quest/sse"
        }
      }
    }
    EOF

Local config (failover mode — runs on Chromebook):

    cat > ~/Thunderbird/.claude/mcp-local.json << 'EOF'
    {
      "mcpServers": {
        "dreams2memories_travel_mcp": {
          "command": "/home/john/Thunderbird/venv/bin/python3",
          "args": ["/home/john/Thunderbird/travel_mcp_server.py"],
          "cwd": "/home/john/Thunderbird"
        }
      }
    }
    EOF

STEP 6: INSTALL THE SMART LAUNCHER

    mkdir -p ~/bin
    cat > ~/bin/thunderbird << 'LAUNCHER'
    #!/bin/bash
    REMOTE_URL="https://mcp.d2mluxury.quest/sse"
    LOCAL_MCP="$HOME/Thunderbird/.claude/mcp-local.json"
    REMOTE_MCP="$HOME/Thunderbird/.claude/mcp-remote.json"
    TARGET="$HOME/.claude/mcp.json"

    echo "Checking tunnel..."
    if curl -sf --max-time 5 "$REMOTE_URL" -o /dev/null 2>&1; then
        echo "✓ Tunnel alive — using dv7 (remote SSE)"
        cp "$REMOTE_MCP" "$TARGET"
    else
        echo "✗ Tunnel down — starting local MCP server"
        cp "$LOCAL_MCP" "$TARGET"
        echo "  Local stdio mode active."
        echo "  Some tools need internet (Google APIs, Amadeus)."
    fi
    cd ~/Thunderbird && claude
    LAUNCHER
    chmod +x ~/bin/thunderbird

Now just type 'thunderbird' to launch.

STEP 7: TEST LOCAL MODE

    cd ~/Thunderbird && source venv/bin/activate
    timeout 10 python3 travel_mcp_server.py 2>&1 | tail -5

You should see "Starting MCP server..." — confirms local capability.

═══════════════════════════════════════════════════════
BEFORE EACH TRIP (Keeping It Current)
═══════════════════════════════════════════════════════

Re-sync codebase:
    rsync -avz --exclude='.venv' --exclude='venv' \\
        --exclude='__pycache__' --exclude='*.pyc' \\
        john@10.0.0.64:~/Thunderbird/ ~/Thunderbird/

Update packages (if requirements.txt changed):
    cd ~/Thunderbird && source venv/bin/activate
    pip install -r requirements.txt

═══════════════════════════════════════════════════════
WHAT WORKS WHERE
═══════════════════════════════════════════════════════

WORKS OFFLINE (No Internet):
  • PDF rendering (Jinja2 + WeasyPrint)
  • Template editing and file operations
  • Persona character sheets (text only)
  • Local data analysis

NEEDS INTERNET (Even in Local Mode):
  • Google APIs (Drive, Sheets, Gmail, Calendar)
  • Amadeus flight search
  • Hotelbeds hotel search
  • Groq LLM (persona voice)
  • Web scraping / browser automation

═══════════════════════════════════════════════════════
TROUBLESHOOTING
═══════════════════════════════════════════════════════

TUNNEL WON'T CONNECT:
    ssh ssh.d2mluxury.quest "systemctl --user status thunderbird-tunnel"
    ssh ssh.d2mluxury.quest "systemctl --user restart thunderbird-tunnel"

MCP SERVER WON'T START LOCALLY:
    cd ~/Thunderbird && source venv/bin/activate
    python3 travel_mcp_server.py 2>&1 | head -20
    # Look for import errors — usually a missing pip package

GOOGLE API AUTH ERRORS:
    # Tokens may have expired. Re-copy from dv7:
    scp john@10.0.0.64:~/Thunderbird/gmail_token.json ~/Thunderbird/
    scp john@10.0.0.64:~/Thunderbird/drive_token.json ~/Thunderbird/

═══════════════════════════════════════════════════════
DV7 REMOTE MANAGEMENT (From Anywhere)
═══════════════════════════════════════════════════════

Check all services:
    ssh ssh.d2mluxury.quest "systemctl --user status d2m-mcp d2m-api thunderbird-tunnel"

Restart everything:
    ssh ssh.d2mluxury.quest "systemctl --user restart d2m-mcp d2m-api thunderbird-tunnel"

View health check log:
    ssh ssh.d2mluxury.quest "tail -20 ~/Thunderbird/logs/health_check.log"

View MCP server logs:
    ssh ssh.d2mluxury.quest "journalctl --user -u d2m-mcp --since '30 min ago' --no-pager"
"""

# Insert content
docs_svc.documents().batchUpdate(
    documentId=doc_id,
    body={"requests": [{"insertText": {"location": {"index": 1}, "text": CONTENT}}]}
).execute()

print(f"Content written!")
print(f"https://docs.google.com/document/d/{doc_id}/edit")
