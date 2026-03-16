# End-of-Session Protocol
## Thunderbird OS — Standard Operating Procedure

At the end of every work session, Claude MUST execute these steps before signing off:

### 1. Session Summary
- Create `Plans/YYYY-MM-DD_Session_Summary.md` (or `_Evening_Session_Summary.md` if second session)
- Include: What was built, files modified/created, key findings, open items
- Keep it factual — no fluff, no emotional language

### 2. Update Roadmap Status
- If any roadmap items were completed, update `~/Thunderbird/roadmap_status.md`
- Change status from NOT STARTED → IN PROGRESS or DONE as appropriate

### 3. Update Memory
- Update `~/.claude/projects/-home-john-Thunderbird/memory/MEMORY.md` with any new stable patterns, file paths, or conventions discovered
- Remove or correct any outdated entries

### 4. Upload Session Summary to Drive
- Upload the session summary to Google Drive (Thunderbird_Intel or Plans folder)
- This makes it available to the HUD staff meeting context

### 5. Morning Briefing Prep
- If it's an evening session, note any items that need attention in the morning
- Ensure the scheduler and API services are in the correct state

### Trigger
- User says: "wrap up", "end of session", "session summary", "goodnight", or similar
- Or when a natural stopping point is reached and it's late

### Format
- Plain prose, scannable tables, no walls of text
- Include service status check
- List open items as checkboxes for next session
