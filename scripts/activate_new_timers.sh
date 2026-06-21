#!/bin/bash
# activate_new_timers.sh — Run once in a terminal to activate all new timers built 2026-06-14
# Usage: bash /home/john/Thunderbird/scripts/activate_new_timers.sh

# Ensure D-Bus user session is reachable
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus

NEW_TIMERS=(
  thunderbird-timer-self-audit
  d2m-commission-watch
  thunderbird-weather-disruption
  d2m-airline-schedule-change
  thunderbird-credential-expiry-forecast
  d2m-perx-trigger-detector
  d2m-dossier-freshness
  d2m-post-trip-followup
  d2m-fdp-reconcile
  d2m-supplier-promo-scan
  thunderbird-mission-board-promoter
  thunderbird-anti-theater-audit
  thunderbird-disk-pressure
  thunderbird-blackboard-conflict-resolver
  thunderbird-lessons-implementation-tracker
  hale-decision-log
  thunderbird-commander-context-restore
)

echo "Reloading systemd user daemon..."
systemctl --user daemon-reload

echo "Activating ${#NEW_TIMERS[@]} new timers..."
FAILED=0
for t in "${NEW_TIMERS[@]}"; do
  if systemctl --user start "${t}.timer" 2>/dev/null; then
    status=$(systemctl --user is-active "${t}.timer" 2>/dev/null)
    echo "  OK: $t ($status)"
  else
    echo "  FAILED: $t"
    FAILED=$((FAILED+1))
  fi
done

echo ""
echo "Done. $((${#NEW_TIMERS[@]} - FAILED)) active, $FAILED failed."
echo "Run: systemctl --user list-timers | grep -E 'commission|weather|airline|perx|dossier|post-trip|fdp|promo|promoter|anti-theater|disk|blackboard|lessons|decision-log|context-restore|timer-self'"
