#!/bin/bash
# Stop hook — warn if uncommitted changes exist in Thunderbird repo
cd /home/john/Thunderbird
STATUS=$(git status --porcelain 2>/dev/null)
if [ -n "$STATUS" ]; then
  COUNT=$(echo "$STATUS" | wc -l)
  echo "⚠️  GIT: $COUNT uncommitted change(s) in Thunderbird — run a commit before closing."
fi
