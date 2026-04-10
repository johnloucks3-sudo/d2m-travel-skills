#!/bin/bash
# Gmail Service Diagnostic Script

echo "=== GMAIL SERVICE DIAGNOSTICS ==="
echo "Run time: $(date)"
echo ""

# 1. Check MCP server status
echo "1. MCP SERVER STATUS:"
systemctl --user status thunderbird-telegram-gw.service | head -5
echo ""

# 2. Check Gmail token existence
echo "2. GMAIL TOKEN CHECK:"
if [ -f "creds/gmail_token.json" ]; then
    echo "✅ Gmail token exists: creds/gmail_token.json"
    echo "   Size: $(wc -c < creds/gmail_token.json) bytes"
    echo "   Modified: $(stat -c %y creds/gmail_token.json)"
else
    echo "❌ Gmail token NOT found"
fi
echo ""

# 3. Check Google credentials
echo "3. GOOGLE CREDENTIALS CHECK:"
if [ -f "creds/credentials.json" ]; then
    echo "✅ Google credentials exist: creds/credentials.json"
else
    echo "❌ Google credentials NOT found"
fi
echo ""

# 4. Check Python environment
echo "4. PYTHON ENVIRONMENT:"
echo "   Python path: $(which python3)"
echo "   Python version: $(python3 --version)"
echo "   venv active: $(source .venv/bin/activate && echo "YES" || echo "NO")"
echo ""

# 5. Check module availability
echo "5. MODULE AVAILABILITY:"
echo "   thunderbird_gmail: $(python3 -c 'import sys; sys.path.extend(["./core", "./core/communication"]); try: from thunderbird_gmail import GmailService; print("✅ Available") except Exception as e: print("❌ Error:", e)' 2>&1)"
echo ""

# 6. Check MCP tool registration
echo "6. MCP TOOL REGISTRATION:"
echo "   Gmail tools should appear in MCP server startup output"
echo ""

echo "=== DIAGNOSTICS COMPLETE ==="
