#!/bin/bash
# Kill dv7 health check cron and disable services
# Runs in a loop, waiting for dv7 to come online

DV7_IPS=("10.0.0.64" "192.168.1.128")
TIMEOUT=2
LOG="/home/john/Thunderbird/logs/dv7_kill_healthcheck.log"

echo "[$(date)] Waiting for dv7 to become reachable..." | tee -a "$LOG"

while true; do
    for IP in "${DV7_IPS[@]}"; do
        if ping -c 1 -W $TIMEOUT "$IP" &>/dev/null; then
            echo "[$(date)] dv7 reachable at $IP — attempting fix..." | tee -a "$LOG"

            # Disable health check cron
            ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "john@$IP" bash -s <<'REMOTE_SCRIPT'
echo "=== Disabling dv7 health check ==="

# Show current crontab
echo "Current crontab:"
crontab -l 2>/dev/null

# Remove health check entries from crontab
crontab -l 2>/dev/null | grep -v 'health_check' | crontab -
echo "Health check removed from crontab"

# Show updated crontab
echo "Updated crontab:"
crontab -l 2>/dev/null

# Disable d2m services so they don't restart
systemctl --user disable d2m-mcp.service 2>/dev/null
systemctl --user disable d2m-api.service 2>/dev/null
systemctl --user disable d2m-tunnel.service 2>/dev/null
systemctl --user disable d2m-scheduler.service 2>/dev/null
echo "All d2m services disabled"

# Stop any running health check
pkill -f health_check.py 2>/dev/null
echo "Done"
REMOTE_SCRIPT

            if [ $? -eq 0 ]; then
                echo "[$(date)] SUCCESS — dv7 health check disabled" | tee -a "$LOG"
                exit 0
            else
                echo "[$(date)] SSH connected but commands failed — retrying in 30s" | tee -a "$LOG"
            fi
        fi
    done
    sleep 30
done
