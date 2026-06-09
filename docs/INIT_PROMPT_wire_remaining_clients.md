# Paste-ready init prompt — wire remaining clients into the lifecycle

> Two ways to use this: run the **Booked-Trips block** (Sonnet) once the timing engine
> is fixed; run the **Spencer block** as its own **Opus** session (it's the hard case).

---

## PREREQUISITE (read first)
The lifecycle TIMING engine must already be fixed (see
`docs/CONTINUATION_lifecycle_timing_fix.md`). Wiring clients onto a broken scheduler is
pointless — verify the scheduler does catch-up, honors completion, and pages on silent
zeros BEFORE wiring. If it isn't fixed yet, do that first.

Read before starting:
1. `docs/TRIP_ASSEMBLY_MODEL_SPEC.md` — the model (SLA→clock, 99%/1%, 35-TP/6-phase).
2. `dossiers/GROUP_Grandeur_Scandinavia_Aug2026_TRACKER.md` — the PATTERN. Furlow/Ely/
   Nichols (Aug 29) are already wired; copy that tracker shape for each trip below.
3. Each client's existing lifecycle doc in `D2M/lifecycle/` and dossier in `dossiers/`.

## HARD-WON GUARDRAILS (from the 2026-06-09 session — non-negotiable)
- **Do not overwrite valid dossier data.** Ground truth is FIELD-BY-FIELD; the dossier
  is fresher than sent reports on some fields, staler on others. When sources conflict,
  surface to the Commander — never auto-pick. (This session: Ely suite was 1212 in the
  dossier and 961 in the sent report + RSSC — the dossier was right.)
- **$ figures = Harlan, traced to primary source** (invoice in `storage/output/`, portal,
  or TESS). All six bookings below were Harlan-verified 2026-06-09 — reuse those.
- **Client sends + payments are the Commander's 1%** — AI stages, Commander clicks.
- **Commit named files only** (credential-scan hook blocks `git add -A`).
- Surgical; verify each clock on a dry-run before trusting; don't gold-plate.

---

## BOOKED-TRIPS BLOCK (Sonnet) — 5 post-anchor trips, anchors locked

Wire each: (a) reconcile dossier to verified truth, (b) instantiate its 35-TP clock from
the booking anchor dates, (c) build a tracker like the Grandeur Scandinavia one
(open items + suspense calendar + per-element status), (d) register it with the fixed
scheduler. Urgency order:

**1. Kuklinski Dec — Viking Mars, Classic Panama Canal (embark Dec 17 2026 → Dec 27).**
   3 bookings: 9593873 (Roger & Nicholas), 9593880 (Kyle & Rosalie), 9595029 (Morton &
   Dodge). ALL PAID (Kyle pays all 3; FPD was Mar 31). Already has the most complete
   model: `docs/KUKLINSKI_LIFECYCLE_SCHEDULE.md` (35 TPs) + `D2M/lifecycle/Kuklinski_Viking_Panama_Lifecycle.md`
   + gantt + portal. **Soonest live deadline: excursion TP ~Jul 15** — this is the first
   real proof the wired engine fires a scan on time. Treat as a 3-couple group like the
   Scandinavia group.

**2. McLeod Dec — Regent SS Grandeur 2984034, Lesser Antilles (embark Dec 19 2026 → Dec 29).**
   FPD **Jul 22 2026, balance $11,943.15**. ⛔ **CONTACT HOLD until Jul 7** — client is on
   Silver Muse Jun 23–Jul 6; no client touch before Jul 7 (Commander directive). Suite 863
   E-Concierge (upgraded). Lifecycle doc: `D2M/lifecycle/McLeod_Grandeur_LesserAntilles_Lifecycle.md`.
   Hub dossier: `dossiers/McLeod_McGlasson_Multi.md` (all 4 McLeod trips).

**3. Loucks Dec — Regent SS Grandeur 3122006, Panama Canal & Pacific Gems (embark Dec 29
   2026 Miami → Jan 14 2027 LA, 16 nts). COMMANDER'S OWN TRIP** (internal handling).
   FPD **Aug 1 2026, balance $24,798** — nearest real FPD (~T-53). Suite 658 E-Concierge
   (upgraded). Lifecycle doc: `D2M/lifecycle/Loucks_Grandeur_PanamaPacific_Lifecycle.md`.

**4. McLeod Mar 2027 — Princess Discovery, Mexico Riviera (embark Mar 13 2027 LA → Mar 20).**
   Booking 8X6PGQ. FPD **Dec 13 2026, ~$6,062** ($200 FCC deposit paid). Cabin D727.
   In the McLeod_McGlasson_Multi hub (booking_3).

**5. McLeod Dec 2027 — Regent SS Prestige 3114500, Season to Cheer (embark Dec 18 2027 →
   Dec 28).** FPD **Jul 21 2027, balance $14,598** ($500 deposit). Suite 820 D-Concierge.
   Lowest urgency. In the Multi hub (booking_4). NOTE: a prior $6,462 balance in the
   sheet was a Princess-total contamination — corrected to $14,598 this session.

McLeod has FOUR trips total (Silver Muse Jun 23 = current/departing + the 3 above). Use
`McLeod_McGlasson_Multi.md` as the hub; instantiate three separate clocks. He is the
best client — wire him airtight.

---

## SPENCER BLOCK (Opus — run separately, this is the hard case)

**Spencer Grand Tour — 12 pax, multi-generational, group air, DMC/tour-operator, Italy.**
PRE-ANCHOR: deposit placed ~May 4 2026, **no FPD/invoice yet → anchor dates not locked.**
TESS Trip 1718870 / Booking 2399739. Commander: *"new thing for me… need closer
monitoring and MUST HAVE CONFIDENCE."*

This is NOT a mechanical wire. It exercises parts of the model the booked trips don't:
- **Pre-anchor lifecycle** (proposal → SLA → commit → deposit/invoice → BAM) — the front
  half of the spec, before the 35-TP clock has fixed dates.
- **Group-scale complexity**: 12 pax across generations (accessibility, pace, kids/elders),
  a **group air block** (12 seats, coordinated), and a **DMC** relationship (on-ground
  logistics handled by a third party — a new coordination surface).
- **Confidence layer**: closer monitoring; the validation/dead-man's-switch matters most here.

Recommended approach for Spencer:
1. Build the **pre-anchor clock** from the proposal/SLA scope (not departure-relative yet).
2. Model group-level elements (group air, group rooming, DMC coordination) + per-pax
   sub-tracking (12 × passports/forms/preferences/dietary).
3. Run it through **devils-advocate** and/or **wing-exercise** review before committing —
   it's novel architecture and high-stakes; adversarial review earns the confidence.
4. Surface the design to the Commander before wiring; this is a strategy-gate trip.

Use Opus for Spencer. The five booked trips above are Sonnet work.

---

## DELIVERABLE PER TRIP
A tracker (Scandinavia-pattern) + a reconciled dossier + an instantiated 35-TP clock
registered with the scheduler + a verified dry-run showing the right items surface on
schedule with nothing silent. Then the Commander is spoon-fed each trip to its clicks.
