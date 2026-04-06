#!/bin/bash
# Systemd Fix Script - Generated for Commander to run once with sudo
set -e

echo "=== FIXING SYSTEMD SERVICES ==="

# FPD Alert Service - new path
cat > /etc/systemd/system/thunderbird-fpd-alert.service << 'EOF'
[Unit]
Description=D2M FPD Payment Deadline Scanner
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=john
WorkingDirectory=/home/john/Thunderbird
ExecStart=/usr/bin/python3 /home/john/Thunderbird/core/watchtower/thunderbird_fpd_alert.py
StandardOutput=journal
StandardError=journal

[Timer]
OnCalendar=*:0/5
RandomizedDelaySec=10
Persistent=true

[Install]
WantedBy=timers.target
EOF

echo "✅ FPD Alert service updated"

# Git Commit Alert Service - new path
cat > /etc/systemd/system/thunderbird-git-commit-alert.service << 'EOF'
[Unit]
Description=D2M Git Uncommitted Changes Watchdog
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=john
WorkingDirectory=/home/john/Thunderbird
ExecStart=/usr/bin/python3 /home/john/Thunderbird/core/watchtower/git_commit_alert.py
StandardOutput=journal
StandardError=journal

[Timer]
OnCalendar=*:0/5
RandomizedDelaySec=10
Persistent=true

[Install]
WantedBy=timers.target
EOF

echo "✅ Git Commit Alert service updated"

# Copy Evernote timer to systemd
cp -f /home/john/Thunderbird/deploy/systemd/thunderbird-evernote-backup.timer /etc/systemd/system/thunderbird-evernote-backup.timer
cp -f /home/john/Thunderbird/deploy/systemd/thunderbird-evernote-backup.service /etc/systemd/system/thunderbird-evernote-backup.service 2>/dev/null || true

echo "✅ Evernote timer installed"

# Reload and restart
systemctl daemon-reload
systemctl enable thunderbird-fpd-alert.timer
systemctl enable thunderbird-git-commit-alert.timer
systemctl restart thunderbird-fpd-alert.timer
systemctl restart thunderbird-git-commit-alert.timer
systemctl enable thunderbird-evernote-backup.timer
systemctl start thunderbird-evernote-backup.timer

echo ""
echo "=== STATUS ==="
systemctl list-timers --all | grep thunderbird
echo ""
echo "=== DONE ==="
