#!/bin/bash
# Z4 — Open WebUI + Ollama Setup
# Installs Ollama, pulls llama3.2:3b, starts Open WebUI via Docker
# Run once from YOGA terminal: bash deploy/z4_install.sh

set -e
cd /home/john/Thunderbird

echo "=== Z4: Open WebUI + Ollama ==="

# 1. Install Ollama
if ! command -v ollama &>/dev/null; then
    echo "[1/5] Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "[1/5] Ollama already installed: $(ollama --version)"
fi

# 2. Start Ollama service (or run in background for first pull)
echo "[2/5] Starting Ollama service..."
if systemctl --user is-active ollama.service &>/dev/null; then
    echo "  Ollama already running"
else
    # Enable and start the systemd service installed by the Ollama installer
    systemctl --user enable ollama.service 2>/dev/null || true
    systemctl --user start ollama.service 2>/dev/null || {
        echo "  systemd not available — starting Ollama in background..."
        nohup ollama serve >> /tmp/ollama.log 2>&1 &
        sleep 3
    }
fi

# 3. Pull model
echo "[3/5] Pulling llama3.2:3b (≈2GB, may take a few minutes)..."
ollama pull llama3.2:3b

echo "[4/5] Verifying model..."
ollama list | grep llama3.2

# 4. Install Open WebUI systemd service
echo "[5/5] Installing Open WebUI systemd service..."
cp deploy/z4_openwebui.service ~/.config/systemd/user/d2m-openwebui.service
systemctl --user daemon-reload
systemctl --user enable d2m-openwebui.service
systemctl --user start d2m-openwebui.service
sleep 3
systemctl --user status d2m-openwebui.service --no-pager | head -10

echo ""
echo "=== Z4 LIVE ==="
echo "  Open WebUI: http://localhost:3010  (openwebui.d2mluxury.quest after DNS)"
echo "  Ollama API:  http://localhost:11434"
echo "  Model:       llama3.2:3b"
echo ""
echo "Next: Run 'cloudflared tunnel route dns 0e0f57b6-33a1-4ed1-b3db-9b886f5add72 openwebui.d2mluxury.quest'"
echo "      Then add openwebui entry to ~/.cloudflared/config.yml (already prepped)"
