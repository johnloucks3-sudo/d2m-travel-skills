#!/bin/bash
# clasp_init.sh — Run ONCE after 'clasp login' to wire up the Apps Script project
# This creates a new Apps Script project bound to the Booking Master sheet
set -e

SHEET_ID="1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
SCRIPT_DIR="/home/john/Thunderbird/scripts/apps_script"

cd "$SCRIPT_DIR"

# Create new Apps Script project bound to the sheet
echo "Creating Apps Script project bound to Sheet $SHEET_ID..."
clasp create --title "Thunderbird Wing Dashboard" --type sheets --parentId "$SHEET_ID"

# This creates .clasp.json with the real scriptId
echo "Project created. Script ID:"
cat .clasp.json

# Push the dashboard script
clasp push

echo ""
echo "wing_dashboard.gs deployed!"
echo "Open the sheet and look for the Wing Ops menu"
echo ""
echo "Run this to enable hourly formatting trigger:"
echo "  clasp run createHourlyTrigger"
