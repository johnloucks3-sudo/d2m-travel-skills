#!/bin/bash
# Z7 — Flowise Visual LangChain Builder Setup
# Runs Flowise via Docker, imports D2M Document Sculptor flow
# Run once from YOGA terminal: bash deploy/z7_install.sh

set -e
cd /home/john/Thunderbird

echo "=== Z7: Flowise ==="

# 1. Pull Flowise image
echo "[1/3] Pulling Flowise Docker image..."
sg docker -c "docker pull flowiseai/flowise:latest"

# 2. Install systemd service
echo "[2/3] Installing Flowise systemd service..."
cp deploy/z7_flowise.service ~/.config/systemd/user/d2m-flowise.service
systemctl --user daemon-reload
systemctl --user enable d2m-flowise.service
systemctl --user start d2m-flowise.service
sleep 5
systemctl --user status d2m-flowise.service --no-pager | head -10

# 3. Wait for Flowise to be ready
echo "[3/3] Waiting for Flowise to start..."
for i in $(seq 1 12); do
    if curl -sf http://localhost:3011/api/v1/chatflows &>/dev/null; then
        echo "  Flowise ready."
        break
    fi
    echo "  Waiting ($i/12)..."
    sleep 5
done

# Import D2M sculptor flow
if curl -sf http://localhost:3011/api/v1/chatflows &>/dev/null; then
    echo "Importing D2M Document Sculptor flow..."
    curl -s -X POST http://localhost:3011/api/v1/chatflows/importchatflows \
        -H "Content-Type: application/json" \
        -d @deploy/flowise/d2m_sculptor_flow.json \
        && echo "  Flow imported." \
        || echo "  Flow import failed — import manually via UI"
fi

echo ""
echo "=== Z7 LIVE ==="
echo "  Flowise UI: http://localhost:3011  (flowise.d2mluxury.quest after DNS)"
echo "  D2M flows pre-loaded: Document Sculptor (client), Document Sculptor (friends)"
echo ""
echo "Next: Run 'cloudflared tunnel route dns 0e0f57b6-33a1-4ed1-b3db-9b886f5add72 flowise.d2mluxury.quest'"
echo "      Then add flowise entry to ~/.cloudflared/config.yml (already prepped)"
