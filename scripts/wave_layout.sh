#!/usr/bin/env bash
# Wave Terminal — Thunderbird Wing Layout
# Run: wing  (alias in ~/.bashrc)
# Opens: Dashboard web pane + Files web pane alongside this terminal

# Dashboard — D2M Ops
wsh web open "https://itinerary.d2mluxury.quest" &

# File browser — Thunderbird directory (token auth)
wsh web open "https://files.d2mluxury.quest/?t=535277-yoda-grandeur" &

# Color the tab so it stands out
wsh setbg "#003087" --opacity 0.08

echo "Wing layout loaded — Dashboard + Files panes open."
