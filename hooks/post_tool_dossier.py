#!/usr/bin/env python3
"""
Thunderbird PostToolUse — Dossier Update Reminder
====================================================
Dreams2Memories Travel, LLC

Fires after booking-related tool calls to remind Claude to update the dossier.
Writes a reminder to stderr (visible in Claude's tool output, not sent to user).
"""

import json
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool = data.get("tool_name", "")

BOOKING_TOOLS = {
    "mcp__dreams2memories__tess_get_booking",
    "mcp__dreams2memories__extract_booking_from_pdf",
    "mcp__dreams2memories__extract_pdf_booking_details",
    "mcp__dreams2memories__extract_master_booking_data",
}

if tool in BOOKING_TOOLS:
    print(
        "[DOSSIER REMINDER] Booking data accessed. "
        "Ensure dossier in ~/Thunderbird/dossiers/ is current, "
        "Booking Master sheet is updated, and THUNDERBIRD_MASTER_PLAN.md reflects latest status.",
        file=sys.stderr,
    )

sys.exit(0)
