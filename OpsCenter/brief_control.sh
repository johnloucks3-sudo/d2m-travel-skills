#!/bin/bash
# Hale Morning Brief Control
# Usage: ./brief_control.sh [status|test|logs|enable|disable]

case "${1:-status}" in
    status)
        echo "🦅 Hale Morning Brief Status"
        systemctl --user status hale-morning-brief.timer
        echo ""
        systemctl --user list-timers hale-morning-brief.timer
        ;;
    test)
        echo "Running test brief generation..."
        python3 /home/john/Thunderbird/OpsCenter/hale_morning_brief.py
        ;;
    logs)
        echo "Last 50 lines of brief log:"
        tail -50 /home/john/Thunderbird/OpsCenter/hale_brief.log
        ;;
    enable)
        systemctl --user enable hale-morning-brief.timer
        systemctl --user start hale-morning-brief.timer
        echo "✅ Morning brief enabled"
        ;;
    disable)
        systemctl --user stop hale-morning-brief.timer
        systemctl --user disable hale-morning-brief.timer
        echo "✅ Morning brief disabled"
        ;;
    *)
        echo "Usage: $0 [status|test|logs|enable|disable]"
        exit 1
        ;;
esac
