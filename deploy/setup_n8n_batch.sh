#!/bin/bash
# setup_n8n_batch.sh — Run once with sudo to activate n8n + batch runner
# Usage: sudo bash /home/john/Thunderbird/deploy/setup_n8n_batch.sh

set -e
DEPLOY=/home/john/Thunderbird/deploy

echo "=== Installing n8n ==="
npm install -g n8n

echo "=== Installing systemd services ==="
cp $DEPLOY/n8n.service /etc/systemd/system/n8n.service
cp $DEPLOY/thunderbird-batch.service /etc/systemd/system/thunderbird-batch.service
cp $DEPLOY/thunderbird-batch.timer /etc/systemd/system/thunderbird-batch.timer

echo "=== Reloading systemd ==="
systemctl daemon-reload

echo "=== Adding DNS route for n8n.d2mluxury.quest ==="
# Run as john — cloudflared credentials live in /home/john/.cloudflared/
sudo -u john /usr/local/bin/cloudflared tunnel route dns 0e0f57b6-33a1-4ed1-b3db-9b886f5add72 n8n.d2mluxury.quest

echo "=== Starting n8n ==="
systemctl enable --now n8n.service

echo "=== Restarting cloudflared tunnel (picks up new n8n route) ==="
systemctl restart d2m-tunnel.service 2>/dev/null || echo "  (tunnel service not found — restart cloudflared manually)"

echo "=== Enabling batch timer ==="
systemctl enable --now thunderbird-batch.timer

echo ""
echo "=== DONE ==="
echo "  n8n URL:      https://n8n.d2mluxury.quest"
echo "  Batch timer:  Mon-Fri 12:05 PM MDT (18:05 UTC)"
echo ""
echo "  Paste into claude.ai → Settings → Integrations → n8n:"
echo "  https://n8n.d2mluxury.quest"
echo ""
systemctl status n8n.service --no-pager
