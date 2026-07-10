# Lindy AI Canary Trial Log
*Canary window: 2026-07-02 → 2026-07-09 · Decision gate: 2026-07-09*

---

## 2026-07-06 — Status check (Day 5 of 7)

**Finding:** `OpsCenter/email_canary_scoreboard.json` shows 272 total entries, **0 tagged
`system: "lindy_ai"`**. The n8n/Python path has been running solo the entire canary
window. Lindy AI has not been stood up yet — 3 days remain before the Jul 9 decision gate.

**Root cause:** Steps 1–2 of `docs/lindy_ai_setup_guide.md` require the Commander's own
hands: signing in to lindy.ai with the johnloucks3 Google login, then granting Gmail
OAuth (read+send+draft) on the **d2mconcierge@gmail.com** account to a third-party SaaS.
Both steps go through a Google consent screen tied to human credentials/2FA — not
something the Wing can or should complete on the Commander's behalf. This is a
genuine human-only wall, not a routing gap.

**Staged and ready (no wall):**
- Step 4 system prompt (Hale persona) — already drafted in the setup guide, current as
  of 2026-07-02. Operational-context roster below refreshes it against today's brief.
- Step 5 reply-mode design (auto-reply johnloucks3-only / draft-only everyone else) —
  matches WF-17 doctrine as written, no changes needed.

**Refreshed operational context for Step 4 (2026-07-06, supersedes the Jul 2 block in
the setup guide — paste this version instead):**
```
Active clients: 16. D2M pipeline (Harlan-verified commission share): $18,830.93.
McLeod (Erik McLeod + Melissa McGlasson): Regent Grandeur 2984034, FPD $11,943.15
  due 2026-07-22. Contact hold lifted 2026-07-07 (client back from Silver Muse Jul 6).
Kuklinski Group (6 guests, 3 cabins): Viking Mars, departs 2026-12-17, PAID.
Loucks family (Commander as client): Regent Grandeur, departs 2026-12-29, FPD Aug 1,
  balance ~$24,798, booking 3122006; Silver Nova May 2027, FPD due 2026-12-06, all clear.
Furlow / Ely-Darrow / Nichols: Regent Grandeur, departs 2026-08-29, PAID. Group HTML
  itinerary build due 2026-07-22.
```

**Blocked — needs Commander action directly (not routable):**
1. Sign up at lindy.ai with johnloucks3@gmail.com (login only).
2. Connect Gmail integration as **d2mconcierge@gmail.com**, grant read+send+draft.
3. Create the Email Assistant Lindy per Steps 3–6 of the setup guide, paste the
   refreshed system prompt above.
4. Run the Step 6 test email and confirm in-thread reply.

**Ask surfaced to Commander (via team-lead), 2026-07-06:** Complete lindy.ai signup +
Gmail OAuth grant for d2mconcierge (steps 1–2, ~5 min) so the remaining 3 canary days
aren't lost. Flagged that this grants an external SaaS send+draft access to the
concierge mailbox — confirm that's still acceptable before granting.

**Not yet complete:** Lindy side of the canary has zero data. Recommendation if the
window closes without Lindy data: extend the canary a few days past Jul 9 for Lindy
specifically, rather than declare n8n/Python the winner by default (it never had a
real competitor in the ring).

---
