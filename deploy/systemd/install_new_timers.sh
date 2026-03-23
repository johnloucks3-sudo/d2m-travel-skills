#!/bin/bash
# Install FPD Alert + Git Commit Alert systemd timers on YOGA
# Run as: bash ~/Thunderbird/deploy/systemd/install_new_timers.sh

set -e
SYSTEMD_DIR="/etc/systemd/system"
SRC_DIR="$(dirname "$(realpath "$0")")"

echo "=== Installing D2M FPD + Git Commit Alert timers ==="

for unit in \
    thunderbird-fpd-alert.service \
    thunderbird-fpd-alert.timer \
    thunderbird-git-commit-alert.service \
    thunderbird-git-commit-alert.timer; do
    echo "  Copying $unit → $SYSTEMD_DIR/"
    sudo cp "$SRC_DIR/$unit" "$SYSTEMD_DIR/$unit"
    sudo chmod 644 "$SYSTEMD_DIR/$unit"
done

sudo systemctl daemon-reload

for timer in thunderbird-fpd-alert.timer thunderbird-git-commit-alert.timer; do
    echo "  Enabling + starting $timer"
    sudo systemctl enable "$timer"
    sudo systemctl start "$timer"
done

echo ""
echo "=== Status ==="
systemctl status thunderbird-fpd-alert.timer --no-pager
systemctl status thunderbird-git-commit-alert.timer --no-pager

echo ""
echo "=== Next fire times ==="
systemctl list-timers thunderbird-fpd-alert.timer thunderbird-git-commit-alert.timer --no-pager
