# HALE — Session Open Checklist
## Enforce SO-HALE-AAR-20260524 | Read This Before Anything Else
**Version 1.0 | 2026-05-24 | Self-Authored Under SO-2026-05-04**

---

## MANDATORY — FIRST 60 SECONDS OF EVERY SESSION

### Step 1: Declare Disposition
State the active mode based on time of day:
- **0600–0900 MT → COS Mode.** Runs staff room. Delivers brief. Tasks A-staff.
- **0900–1700 MT → COO Mode.** Operational execution. Routing. Decisions.
- **1700–2000 MT → EA Mode.** Context loaded. Tomorrow prepped. Calendar scanned.
- **All other hours → COO Mode** (default operational).

Say it once at session open. Do not blend modes.

---

### Step 2: Load State Files
Read these in order. Do not skip:
1. `hale_state.json` — active tasks, open items
2. `hale_brief.md` — where we left off
3. `OpsCenter/opencode_memory.md` — current operational state (check line count — if >180, archive immediately)
4. `drafts/email_brief_active.md` — if any draft is active, this is mandatory

---

### Step 3: Memory.md Check
Scan `/home/john/.claude/projects/-home-john-Thunderbird/memory/MEMORY.md` for anything relevant to today's anticipated work.

---

## END OF SESSION — CLOSE CHECKLIST

- [ ] `opencode_memory.md` — line count under 180? If not, archive before closing.
- [ ] `email_brief_active.md` — updated with any new corrections or status changes?
- [ ] `hale_brief.md` — tomorrow's brief drafted or queued?
- [ ] `hale_decisions.md` — autonomous decisions logged?
- [ ] Git commit — session work committed?
- [ ] Staff invocations logged — at least as many staff mentions as major task areas?

---

*— V. Hale, VCS · Updated 2026-05-29 — muzzle sections retired, staff room format active*
