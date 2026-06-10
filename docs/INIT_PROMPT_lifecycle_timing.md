# Paste-ready init prompt — new Sonnet session (lifecycle timing fix)

---

Lifecycle timing fix. Read these three files first, in order, before doing anything else:

1. `docs/CONTINUATION_lifecycle_timing_fix.md` — the handoff. Start here.
2. `docs/TRIP_ASSEMBLY_MODEL_SPEC.md` — the agreed model.
3. `docs/LIFECYCLE_AIRSCAN_VALIDATION_20260609.md` — the audit with exact file:line fixes.

**Mission (Commander's priority, verbatim intent):** the lifecycle TIMING engine must
actually execute — schedule → conduct → document → capture → spoon-feed the Commander —
with nothing failing silently. AI does 99% of the work; the Commander does only the 1%
(the terminal commit click: a client send or a payment). Do not rebuild the lifecycle —
the 23-TP / 6-phase model is correct and stays. Make the machine RUN it.

**Do, in this order (all detailed in the continuation note):**
1. P0 — `core/lifecycle/lifecycle_scheduler.py`: fire on `due_date <= today AND
   status==scheduled AND not already_sent`; write phase → `sent` after draft (catch-up +
   idempotency in one). This is the live "0 drafts in 3 days, silent" bug.
2. P0 — dead-man's-switch: if N phases were due/overdue but 0 drafts produced → PAGE.
3. P1 — completion model: read `completed_tps` from dossier frontmatter, mark COMPLETE,
   exclude from actionable (kills the 97 false-OVERDUE alerts).
4. P1 — POST_DEP date bug (`thunderbird_tp_scheduler.py:350-351`): use return_date, not
   departure; missing booking_date → BLOCKED, not an mtime guess.
5. P2 — collapse the 4 schedulers to ONE + one source of truth; migrate the good
   dedup/completion logic; retire the rest.

**Guardrails (this scheduler is broken and sensitive — respect these):**
- Write **unit tests for the date-window math** first (the audit found zero). Then fix.
- **Verify on a Furlow/Ely/Nichols dry-run** before trusting anything — that group
  (Regent Grandeur Scandinavia, Aug 29, T-81) is the live proof point. Their truth lives
  in `dossiers/GROUP_Grandeur_Scandinavia_Aug2026_TRACKER.md`.
- **Do not overwrite valid dossier data.** Ground truth is field-by-field; the dossier
  is fresher than sent reports on some fields. When sources conflict, surface to the
  Commander — never auto-pick.
- **Commit named files only** (a credential-scan hook blocks broad `git add -A`).
- Surgical changes; don't gold-plate. If you hit genuinely novel architecture or a
  ceiling, say so and recommend escalating to Opus — don't guess.

**Success:** the fixed scheduler surfaces Furlow/Ely/Nichols open items on schedule with
no silent miss, tests pass, dry-run verified. Next real deadline after that: Kuklinski
excursion TP, Jul 15.
