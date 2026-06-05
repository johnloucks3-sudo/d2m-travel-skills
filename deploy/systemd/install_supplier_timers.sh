#!/bin/bash
# Install all supplier lifecycle management timers on YOGA
# Run as: bash ~/Thunderbird/deploy/systemd/install_supplier_timers.sh
set -e

SYSTEMD_DIR="/etc/systemd/system"
SRC_DIR="$(dirname "$(realpath "$0")")"

echo "=== Installing D2M Supplier Lifecycle Management timers ==="

UNITS=(
    d2m-rssc-session-keepalive.service
    d2m-rssc-session-keepalive.timer
    d2m-centrav-session-keepalive.service
    d2m-centrav-session-keepalive.timer
    d2m-perx-session-keepalive.service
    d2m-perx-session-keepalive.timer
    d2m-portal-keepalive.service
    d2m-portal-keepalive.timer
    d2m-site-sentinel.service
    d2m-site-sentinel.timer
    sterling-lifecycle-validate.service
    sterling-lifecycle-validate.timer
)

for unit in "${UNITS[@]}"; do
    echo "  Copying $unit → $SYSTEMD_DIR/"
    sudo cp "$SRC_DIR/$unit" "$SYSTEMD_DIR/$unit"
    sudo chmod 644 "$SYSTEMD_DIR/$unit"
done

sudo systemctl daemon-reload

TIMERS=(
    d2m-rssc-session-keepalive.timer
    d2m-centrav-session-keepalive.timer
    d2m-perx-session-keepalive.timer
    d2m-portal-keepalive.timer
    d2m-site-sentinel.timer
    sterling-lifecycle-validate.timer
)

for timer in "${TIMERS[@]}"; do
    echo "  Enabling + starting $timer"
    sudo systemctl enable "$timer"
    sudo systemctl start "$timer"
done

echo ""
echo "=== Status ==="
for timer in "${TIMERS[@]}"; do
    systemctl status "$timer" --no-pager | head -5
    echo ""
done

echo "=== Next fire times ==="
systemctl list-timers --no-pager | grep "d2m-"
