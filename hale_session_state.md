# HALE Session State Bridge

Auto-loaded at startup via @hale_session_state.md in CLAUDE.md.

## Required Read at Session Start

These three files are auto-loaded alongside this bridge via @ references in CLAUDE.md. They constitute your session memory:

1. **hale_state_snapshot.json** — Full system state: email scan (total/unread/by client/by urgency), system health (tunnel, n8n, Gmail token), decision journal count
2. **hale_email_ooda_state.json** — OODA decision queue: pending email decisions with recommendations, counterpoints, draft replies, and authority levels
3. **hale_decision_journal.jsonl** — Append-only decision log: every action taken by either HALE brain, with category, authority level, and date
4. **hale_state.json** — Brief operational state (active tasks, standing orders, open items)

## Authority Levels
- L0 (Auto) — Safe to auto-handle: vendor blasts, non-client spam
- L1 (Chief Only) — Needs human judgment: client-sensitive, financial, irreversible
- L2 (HALE) — Routine client ops: file/acknowledge/classify
- L3 (Wing) — Persona/crew taskings (via MCP consult_persona)
- L4 (Commander) — Strategy decisions requiring Chief or Yoda approval

## Session Continuity Pattern
1. These files auto-load at startup → you know pending items, past decisions, and system posture
2. As you process items, append decisions to hale_decision_journal.jsonl
3. When you update email state (process/send/reply), reflect changes in the OODA state
4. End-of-session: leave updated state files for next session
