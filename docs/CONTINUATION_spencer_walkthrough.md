# CONTINUATION — Spencer walkthrough + lifecycle wiring state
## For the next session · created 2026-06-09

**Use Opus for Spencer** (the hard case — 12 pax, multi-gen, 3 countries). The
`/model` "doesn't exist" errors are just the weekly rate-limit ceiling wrapping a 429;
whatever model lets you through is fine.

## RESUME HERE
We were **walking through the Spencer Grand Tour 2027 timeline** phase by phase,
paused mid–Phase A. Read first:
1. `dossiers/Spencer_GrandTour_2027_TIMELINE.md` — the proposed timeline (THE doc)
2. `Commander_Review/Spencer_Grand_Tour_2027_Working CC edits.md` — Commander's authoritative source
3. (stale — ignore/retire) `dossiers/spencer_bill_family_voyage_2027.md` (Milan/Iceland/Jun-20 = obsolete)

**Two open questions on the table for the Commander (Phase A):**
- Does Phase A look right — anything to add/cut from what fires Jul 7?
- Does he already know any of the 6 gating decisions (Rome apt-vs-hotel, Florence
  2v3 nights, cooking class Florence/Tuscany, Switzerland module order/nights,
  excursion prefs), or do they all wait for the review call with Bill?

Then continue the walkthrough: **Phase B (booking sprint), C (run-up), D (trip+split+post)** —
one phase at a time, let the Commander correct each.

## SPENCER KEY FACTS
12 pax, 3 family groups, ~21 days, Jun 12–Jul 2 2027. Cruise spine = Disney Wish
(Jun 15–23) booked by VTG (Christian Cornell), NOT D2M. D2M builds air (3 groups:
Yaggi 4 Business, Tim's 4 Business, Bill's 8 quote PE+Business) + Rome + Florence +
Switzerland (Zermatt+Interlaken) + Zurich + transfers + excursions + insurance + docs.
**Mid-trip split Jun 23:** Tim's family (4, incl. 5yo+2yo) flies FCO→DEN; remaining 8
continue to Florence→Switzerland→Zurich→ZRH→DEN Jul 2.
- **Phase A delayed to Jul 7, 2026** (Commander). Lunch = NO DATE.
- Celebrations: Bill+Kathleen 50th anniv · Lillianna HS grad · Mike Yaggi 50th b'day ·
  Kathleen 72nd b'day = Jun 12 = departure day.

## SPENCER RISK FLAGS (the "MUST HAVE CONFIDENCE" items)
1. 🔴 **Insurance window** — CFAR/pre-ex waiver likely ties to first payment (~May 4
   deposit); may already be closed. Confirm with Harlan what starts the clock. (Delay
   to Jul 7 doesn't worsen it.)
2. Peak-June premium air for 12 — availability is the risk; book early (Phase B, Fall 2026).
3. 2 minor passports (5yo, 2yo) — audit now; kids' passports age out.
4. VTG commission visibility on the cruise — confirm D2M's position.
5. Jun 23 split — two simultaneous movements with toddlers; pre-stage.
6. Retire the stale Spencer dossier.

## LIFECYCLE WIRING — STATE (done this session, committed)
- **Timing engine: FIXED + tested** (catch-up, dead-man's-switch, completion model,
  POST_DEP) — 37 tests pass. The "barrier" was always the rate limit, not the engine.
- **9 client-trips wired** with their own scheduled clocks + trackers:
  Furlow/Ely/Nichols (Aug Scandinavia group), Kuklinski Dec group + Morton/Dodge,
  Loucks Dec, McLeod ×3 (Dec Grandeur / Mar Princess / Dec-27 Prestige).
- **McLeod split** into per-booking dossiers (engine reads one record/file); Multi hub
  is now a relationship index. Best client now actually scheduled.
- **Morton/Dodge resolved PAID** (Booking Master $0.00, Kyle paid all 3) → false-overdue closed.
- **Spencer** = the last major piece; mid-walkthrough.

## OPEN (non-Spencer)
- McLeod Princess $6,062 vs $6,222 ($160) — Harlan reconcile before Dec 13. Low urgency.
- Soonest deadlines the engine now watches: Jul 7 McLeod hold lifts (FPD Jul 22) ·
  Jul 11 Loucks reminder (FPD Aug 1) · Jul 15 Kuklinski excursion ramp.

## GUARDRAILS (hard-won — carry forward)
- No single authoritative doc; truth is field-by-field, Commander arbitrates conflicts.
  Don't overwrite valid dossier data; surface conflicts, don't guess.
- A false "complete" is worse than a false "overdue" (hides real work).
- $ figures = Harlan, primary-source traced.
- Commit named files only (credential + A7 hooks block `git add -A`).
- Client sends + payments = Commander's 1% (the terminal click).
