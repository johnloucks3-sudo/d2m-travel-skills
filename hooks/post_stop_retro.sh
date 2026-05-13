#!/bin/bash
# Stop hook — generate structured session retro stub
# Fires on every Claude Code session Stop
# COS loads _latest.md at next session open for continuity bridging

RETRO_DIR="/home/john/Thunderbird/docs/retros"
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M)
TS=$(date +%Y%m%d_%H%M%S)

# Check if a retro already exists for today (avoid duplicates)
EXISTING=$(ls "${RETRO_DIR}/${DATE}-"*.md 2>/dev/null | head -1)

if [ -n "$EXISTING" ]; then
  # Update the _latest symlink to existing today's file
  ln -sf "$EXISTING" "${RETRO_DIR}/_latest.md" 2>/dev/null
  exit 0
fi

# Determine topic from last git commit message (best available signal)
LAST_COMMIT=$(cd /home/john/Thunderbird && git log -1 --pretty=format:"%s" 2>/dev/null || echo "general")
TOPIC=$(echo "$LAST_COMMIT" | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]//g' | cut -c1-40)
[ -z "$TOPIC" ] && TOPIC="general"

RETRO_FILE="${RETRO_DIR}/${DATE}-${TOPIC}.md"

cat > "$RETRO_FILE" << EOF
# Session Retro — ${DATE} — ${TOPIC}
*Generated: ${DATE} ${TIME} MT | Thunderbird Wing*

---

## Date / Focus
- **Date:** ${DATE}
- **Topic:** ${LAST_COMMIT}

---

## What Worked
<!-- Fill in: approaches, tools, patterns that succeeded -->
-

---

## What Didn't Work / Blockers
<!-- Fill in: errors hit, wrong turns, time sinks -->
-

---

## Lessons Learned (→ Standing Orders / Memory)
<!-- Extract rules, not just descriptions. Each bullet = a potential SO or memory entry. -->
-

---

## Open Loops
<!-- Unfinished items to pick up next session -->
-

---

## Next Session Priorities
1.
2.
3.

---
*— Iron Vic | Auto-stub generated at session stop*
EOF

# Update _latest symlink
ln -sf "$RETRO_FILE" "${RETRO_DIR}/_latest.md" 2>/dev/null

echo "📋 Retro stub: docs/retros/${DATE}-${TOPIC}.md — fill in before closing."
