#!/bin/bash
# THUNDERBIRD — Complete systemd fix
# Run: sudo bash /home/john/Thunderbird/ops/fix_systemd_complete.sh
set -e

echo "=== THUNDERBIRD SYSTEMD COMPLETE FIX ==="
echo ""

# 1. STOP the crash loop immediately
echo "[1/6] Stopping d2m-mcp crash loop..."
systemctl stop d2m-mcp.service 2>/dev/null || true
systemctl disable d2m-mcp.service 2>/dev/null || true

# 2. Rewrite d2m-mcp.service with correct path
echo "[2/6] Fixing d2m-mcp.service path..."
cat > /etc/systemd/system/d2m-mcp.service << 'EOF'
[Unit]
Description=Dreams2Memories MCP Server (Streamable HTTP Transport)
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=john
WorkingDirectory=/home/john/Thunderbird
ExecStart=/home/john/Thunderbird/.venv/bin/python /home/john/Thunderbird/core/mcp/travel_mcp_server.py --http --port=8765
EnvironmentFile=/home/john/Thunderbird/.env
Environment=HOME=/home/john
Environment=PYTHONPATH=/home/john/Thunderbird
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
echo "   ✅ d2m-mcp.service rewritten"

# 3. Install agentic intel timer (nightly 01:00 MDT)
echo "[3/6] Installing agentic intel timer..."
cp -f /home/john/Thunderbird/deploy/systemd/thunderbird-agentic-intel.service /etc/systemd/system/
cp -f /home/john/Thunderbird/deploy/systemd/thunderbird-agentic-intel.timer /etc/systemd/system/
echo "   ✅ agentic intel timer installed"

# 4. Install evernote backup timer
echo "[4/6] Installing evernote backup timer..."
cp -f /home/john/Thunderbird/deploy/systemd/thunderbird-evernote-backup.service /etc/systemd/system/ 2>/dev/null || true
cp -f /home/john/Thunderbird/deploy/systemd/thunderbird-evernote-backup.timer /etc/systemd/system/
echo "   ✅ evernote timer installed"

# 5. Reload and enable
echo "[5/6] Reloading systemd..."
systemctl daemon-reload
systemctl enable --now d2m-mcp.service
systemctl enable --now thunderbird-agentic-intel.timer
systemctl enable --now thunderbird-evernote-backup.timer

# 6. Status check
echo ""
echo "[6/6] Status:"
systemctl is-active d2m-mcp.service && echo "   ✅ d2m-mcp: ACTIVE" || echo "   ❌ d2m-mcp: check logs"
systemctl is-active thunderbird-agentic-intel.timer && echo "   ✅ agentic-intel timer: ACTIVE" || echo "   ❌ agentic-intel timer: check"
systemctl is-active thunderbird-evernote-backup.timer && echo "   ✅ evernote timer: ACTIVE" || echo "   ❌ evernote timer: check"

echo ""
echo "=== Next intel sweep: tonight 01:00 MDT → johnloucks3@gmail.com ==="
echo "=== MCP endpoint: http://localhost:8765 ==="
echo ""
echo "DONE"
