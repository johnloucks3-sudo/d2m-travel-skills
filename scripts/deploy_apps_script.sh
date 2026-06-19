#!/bin/bash
# deploy_apps_script.sh — Deploy wing_dashboard.gs to Google Sheets
# Run ONCE manually after clasp login to set scriptId, then automate
set -e

SCRIPT_DIR="/home/john/Thunderbird/scripts/apps_script"
cd "$SCRIPT_DIR"

# Step 1: Check auth
if [ ! -f ~/.clasprc.json ]; then
    echo "AUTH REQUIRED: Run 'clasp login' in a browser-connected terminal first"
    echo "Then re-run this script"
    exit 1
fi

# Step 2: Check if scriptId is set
SCRIPT_ID=$(cat .clasp.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('scriptId',''))" 2>/dev/null)
if [ "$SCRIPT_ID" = "PLACEHOLDER" ] || [ -z "$SCRIPT_ID" ]; then
    echo "No scriptId set. Getting bound script for Sheet..."
    # List scripts bound to the sheet (requires Drive API)
    echo "Run: clasp list"
    echo "Find the script bound to sheet 1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
    echo "Then: clasp clone SCRIPT_ID"
    exit 1
fi

# Step 3: Push script
echo "Pushing wing_dashboard.gs to Apps Script project $SCRIPT_ID..."
clasp push

echo "Deployed successfully!"
echo "Open https://script.google.com/d/$SCRIPT_ID/edit to verify"
