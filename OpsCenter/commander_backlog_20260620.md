# COMMANDER EMAIL BACKLOG — d2mconcierge, last 4 days
## Surfaced 2026-06-20 — system falsely labeled all "DirectiveReplied" (replied != done)

| # | Date | Tasking | Type | Status |
|---|---|---|---|---|
| 1 | Thu 18 20:47 | Add May 2027 Silver Nova to Booking Master sheet | TASK | OPEN |
| 2 | Fri 19 17:24 | Amy insurance → dossier + 1-wk suspense + must-book date | TASK | WORKING |
| 3 | Thu 18 05:43 | PE booking PE181149717 → Loucks May 2027 dossier | TASK | OPEN |
| 4 | Wed 17 20:43 | Gemini API key issue — explain + remedy | TASK | OPEN |
| 5 | Wed 17 16:51 | Capture insurance option differences | TASK | OPEN |
| 6 | Wed 17 16:19 | Susan Loucks medical files (Dr Neufer +1) → for Curtis | TASK | OPEN |
| 7 | Tue 16 18:05 | "Roman summer / Ava (HS grad) + fam" — Dani write back | CLIENT (WF-17) | OPEN |
| 8 | Wed 17 06:54 | Silversea / Melissa follow-up | CLIENT-ish | OPEN |
| 9 | Tue 16 22:34 | Susan's eyes — second-opinion options | TASK | OPEN |
| 10 | Thu 18 15:41 | "How many clients do we have?" | QUESTION | ANSWERED below |
| 11 | Sat 20 15:51 | WAR format unreadable (low contrast) — fix + QC | FEEDBACK | OPEN (→ navy template) |
| 12 | Fri 19 20:54 | "33 Claude Code Skills" — ELON eval/integrate | TECH | OPEN (ELON) |
| 13 | Tue 16 22:35 | "Report actions taken, not raw T2" | FEEDBACK | DROVE THE FIX |
| 14 | Tue 16 22:59 | Scanner test — "does wing auto-reply?" | TEST | FAILED (no real reply) |
| 15 | Tue 16 23:05 | Scanner verify 2 — no prefix | TEST | FAILED |
| 16 | Thu 18 09:18 | Fwd briefing 77 action items | FYI | review |
| 17 | Wed 17 08:33 | Fwd Overnight Attack AAR | FYI | review |

**Root cause:** directive sweep applied THUNDERBIRD-DirectiveReplied on reply-sent, not task-done. Idempotency + the false "handled" hid this backlog. Fix: label only after the task is executed + verified; reply with ACTIONS TAKEN (Commander directive #13, Tue 16).
