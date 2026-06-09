# CONTINUATION — Lifecycle Timing Fix
## For the next session · created 2026-06-09 (prior session hit ~700K tokens)

**START HERE. Read these 3 files first (they hold all the context — the design
conversation does NOT need to be reloaded):**
1. `docs/TRIP_ASSEMBLY_MODEL_SPEC.md` — the agreed trip-assembly model (Commander-defined)
2. `docs/LIFECYCLE_AIRSCAN_VALIDATION_20260609.md` — the 3-agent audit + ranked fixes
3. `dossiers/GROUP_Grandeur_Scandinavia_Aug2026_TRACKER.md` — Furlow/Ely/Nichols live tracker

---

## COMMANDER'S DIRECTIVE (verbatim intent)
> "Even more important than the ground truth (since I know it for each client in my
> head) is the lifecycle timing — so let's fix this ASAP and move ahead."

The ground-truth/data work is largely done. **The priority is making the lifecycle
TIMING engine actually execute** — schedule → conduct → document → capture → spoon-feed,
with nothing silent. AI does 99%; Commander does the 1% (the terminal commit click).

## THE TIMING FIXES (from the audit — precise, file:line)
Active scheduler is `core/lifecycle/lifecycle_scheduler.py` (timer fires 0600, but
produces 0 drafts silently). Fix, in priority order:

1. **Catch-up + idempotency (P0).** `calculate_due_phases` (~:366) fires only on exact
   `phase_date == today`. Change to fire on `due_date <= today AND status==scheduled AND
   not already_sent`; after creating a draft, write phase status → `sent`. (One change =
   catch-up + dedup.) This is the live "0 drafts in 3 days / silent zeros" bug.
2. **Dead-man's-switch (P0).** Scheduler logs `drafts_created:0`, exits 0, no alert.
   Add: if N phases were due/overdue but 0 drafts produced → PAGE Commander. (~:495 only
   pages on `errors`.)
3. **Completion model (P1).** `TPStatus.COMPLETE` defined but never set → 97 false
   OVERDUE alerts (TP 0.5 at −481d). Read `completed_tps` from dossier frontmatter
   (logic exists in `lifecycle_calendar_engine._read_dossier_meta`); mark COMPLETE;
   exclude from `get_actionable_tps`.
4. **POST_DEP date bug (P1).** `thunderbird_tp_scheduler.py:350-351` uses `rec.departure`
   not `rec.return_date` → "Welcome Home" fires mid-voyage. Route POST_DEP through
   return_date. And `:286` uses file mtime when booking_date missing → make it BLOCKED,
   not an mtime guess.
5. **Collapse schedulers (P2).** 4 lifecycle schedulers, 3 data sources; the 2 best
   (`D2M/d2m_lifecycle_scheduler.py`, `scripts/lifecycle_calendar_engine.py`) are
   DISABLED, the weakest runs. Pick ONE + one source of truth; migrate good dedup/
   completion logic; retire the rest.
6. **Write→read capture (P2).** `tp_alerts.jsonl` (2.8MB) + arc_price_dispatcher result
   JSONs have NO readers. Add the `scan_results` store (model `fare_watch_db.py`) keyed
   (client, tp, category, date, source, results_json) + a read API. Prove read path runs.

## PROOF POINT
Furlow/Ely/Nichols (Regent Grandeur Scandinavia, Aug 29, T-81) is the live test. If the
fixed scheduler correctly surfaces their open items (At Six booking, ARN→At Six transfer,
HEL→ARN seats, E-30 itinerary Jul 30, monthly validation) on schedule with no silent
miss, the timing engine works. Next live deadline: **Kuklinski excursion TP, Jul 15.**

## DONE THIS SESSION (do not redo)
- MISSION-172 fully fixed (D1–D6) + validated
- Booking Master deduped; Harlan reader + Sunday audit dedup wired
- Model-routing fix (max_proxy opus→4-8; run_claude pins model)
- TRIP_ASSEMBLY_MODEL_SPEC written; 3-subsystem audit done
- Furlow/Ely/Nichols: archived dead Celebrity-voucher file; reconciled hotel→At Six
  (Commander-arbitrated); insurance marked moot (all 3); refund receivables logged to
  tracker (Harlan to confirm amounts)

## STILL OPEN (besides the timing engine)
- Furlow/Nichols dossiers: a few descriptive insurance status lines (matrix/gap) still
  say deferred/CFAR — tracker supersedes (moot); clean up if reconciling fully.
- Spencer (Step 2): 12-pax multi-gen group, group air, DMC — the hard case; design after
  Furlow group is wired. "MUST HAVE CONFIDENCE."
