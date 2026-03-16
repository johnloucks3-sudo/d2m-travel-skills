#!/usr/bin/env bash
# =============================================================================
# D2M MCP Server — VPS Deployment Script
# Target: openSUSE Tumbleweed
# =============================================================================
set -euo pipefail

APP_USER="d2m"
APP_DIR="/opt/thunderbird"
PORT=8765

echo "=== D2M MCP Server VPS Setup (openSUSE Tumbleweed) ==="

# 1. System packages
echo "Installing system dependencies..."
sudo zypper refresh
sudo zypper install -y python313 python313-pip python313-venv \
    gcc python313-devel libffi-devel openssl-devel \
    chromium playwright-chromium \
    git curl

# 2. Create service user
if ! id "$APP_USER" &>/dev/null; then
    echo "Creating service user: $APP_USER"
    sudo useradd -r -m -d /home/$APP_USER -s /bin/bash $APP_USER
fi

# 3. Create app directory
echo "Setting up $APP_DIR..."
sudo mkdir -p $APP_DIR/output $APP_DIR/screenshots
sudo chown -R $APP_USER:$APP_USER $APP_DIR

# 4. Copy project files (run from local machine)
echo ""
echo ">>> MANUAL STEP: Copy Thunderbird files to VPS <<<"
echo "Run from your local machine:"
echo "  rsync -avz --exclude='venv' --exclude='__pycache__' \\"
echo "    ~/Thunderbird/ user@VPS_IP:$APP_DIR/"
echo ""
read -p "Press Enter after files are copied..."

# 5. Python venv + dependencies
echo "Setting up Python venv..."
sudo -u $APP_USER bash -c "
    cd $APP_DIR
    python3.13 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install mcp[cli] pydantic httpx playwright playwright-stealth
    pip install google-api-python-client google-auth google-auth-oauthlib
    pip install weasyprint pytesseract pillow openpyxl jinja2
    pip install amadeus
    playwright install chromium
"

# 6. Install systemd service
echo "Installing systemd service..."
sudo cp $APP_DIR/deploy/d2m-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable d2m-mcp.service

# 7. Firewall
echo "Opening port $PORT..."
sudo firewall-cmd --permanent --add-port=$PORT/tcp 2>/dev/null || \
    echo "Note: firewall-cmd not available — open port $PORT manually if needed"
sudo firewall-cmd --reload 2>/dev/null || true

# 8. Start service
echo "Starting D2M MCP Server..."
sudo systemctl start d2m-mcp.service
sleep 2
sudo systemctl status d2m-mcp.service

echo ""
echo "=== Deployment Complete ==="
echo "MCP SSE endpoint: http://VPS_IP:$PORT/sse"
echo "Health check: curl http://VPS_IP:$PORT/sse"
echo ""
echo "Claude.ai MCP config (add to client):"
echo '  {'
echo '    "mcpServers": {'
echo '      "dreams2memories": {'
echo '        "transport": "sse",'
echo "        \"url\": \"http://VPS_IP:$PORT/sse\""
echo '      }'
echo '    }'
echo '  }'
echo ""
echo "Commands:"
echo "  sudo systemctl status d2m-mcp    # Check status"
echo "  sudo journalctl -u d2m-mcp -f    # Tail logs"
echo "  sudo systemctl restart d2m-mcp   # Restart"
