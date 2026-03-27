#!/bin/bash
# Install new Goose-powered systemd timers for Thunderbird intel modules
# Run once after goose-d2m is verified working.
#
# Usage: bash deploy/systemd/install_goose_timers.sh

set -euo pipefail

SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing Goose intel timers..."

# Ensure goose-d2m is executable
chmod +x "$HOME/bin/goose-d2m"
echo "  ✓ goose-d2m executable"

# New timers (Phase 1 — revived/new modules)
NEW_UNITS=(
    "d2m-airline-monitor.service"
    "d2m-airline-monitor.timer"
    "d2m-x-osint.service"
    "d2m-x-osint.timer"
    "d2m-factbook-refresh.service"
    "d2m-factbook-refresh.timer"
)

mkdir -p "$SYSTEMD_USER_DIR"

for unit in "${NEW_UNITS[@]}"; do
    src="$DEPLOY_DIR/$unit"
    dst="$SYSTEMD_USER_DIR/$unit"
    if [[ -f "$src" ]]; then
        cp "$src" "$dst"
        echo "  ✓ Installed $unit"
    else
        echo "  ✗ Missing: $src"
    fi
done

# Reload and enable
systemctl --user daemon-reload
echo "  ✓ daemon-reload"

for timer in d2m-airline-monitor.timer d2m-x-osint.timer d2m-factbook-refresh.timer; do
    systemctl --user enable --now "$timer"
    echo "  ✓ Enabled + started: $timer"
done

echo ""
echo "Active Goose timers:"
systemctl --user list-timers | grep -E "airline|osint|factbook" || echo "  (none found — check systemctl --user list-timers)"

echo ""
echo "Next: verify with 'goose-d2m run --no-session --recipe recipes/airline_monitor.yaml'"
