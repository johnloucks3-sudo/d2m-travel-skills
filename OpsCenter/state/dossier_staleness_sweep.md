# Dossier Staleness Sweep — 2026-07-30

Read-only audit of `dossiers/*.md` (88 files, `archive/` and `CLAUDE.md` excluded) following the DoorCounty Sept-2026 incident (dossier said "🔴 NOT BOOKED" on flights that were actually booked, with a false "cancel the $346 hotel by Aug 30" warning sitting on top of the stale field — already withdrawn today per commit `3d5c4ed6a`). Goal: find every other dossier that is probably lying the same way. **No dossier was edited by this sweep.**

## Headline numbers

- **88** dossier files scanned.
- **14** files carry a travel-relevant date (departure/embark/check-in/disembark/FPD) that lands within 90 days of today (by 2026-10-28), found by keyword-anchored search (`depart|embark|sail|check-in|disembark|travel dates|FPD`), not blind date-regex — see Methodology for why that matters.
- Of those 14, they collapse into **4 distinct trips/clusters** (dates repeat across per-client + per-group dossiers for the same voyage):
  1. **Lyons (Nancy & Ken) — Regent Athens, embark Aug 11 → disembark Sep 6, 2026** (3 files)
  2. **Heer (Ann & Shawn) — Japan, departs Aug 16, 2026** (1 file)
  3. **Grandeur Scandinavia group (Furlow / Ely-Darrow / Nichols) — embark Aug 29 → disembark Sep 8, 2026** (8 files)
  4. **Loucks Regent Panama — FPD Sep 30, 2026** (1 file, payment deadline not departure)
  5. DoorCounty Sister Bay, Sep 6-7, 2026 (1 file) — **the original incident, already patched today.**
- **Only 11 of 88 dossiers (12.5%) carry any machine-readable "Last Updated" claim at all.** The other 77 have no as-of date to check staleness against — you cannot tell if they're current without opening each one.
- **Git commit date is not a valid freshness proxy on this repo.** Confirmed root cause below: an automated "Staging Engine" appends cosmetic HTML comment markers to files in bulk commits, making a file's `git log` date look fresh (e.g., "2026-07-28") while its actual content is months old.

## Ranked — most dangerous first (soonest departure × staleness)

### 1. Lyons Nancy & Ken — Athens/Regent — embark Aug 11, 2026 (12 days out) — **CONFIRMED CONTRADICTION**
Two dossiers for the same client, same trip, same date, disagree with each other right now:
- `dossiers/Lyons_Nancy_Ken.md:` `| Check-in | August 10, 2026 (arrival ~noon from AA216) | ✅ Confirmed |`
- `dossiers/Lyons_Nancy_Ken_drive.md:` `| Check-in | August 10, 2026 (night before embarkation) | TBD |`

Same field, same date, opposite status. Neither file has an explicit "Last Updated" date, so there's no way to tell which one is current without asking. Gmail search (`Lyons Grande Bretagne Athens check-in`, both mailboxes) found **no confirmation email** for the Grande Bretagne hotel or the Aug 10 check-in — **this is NOT evidence the check-in is unconfirmed.** Regent-related confirmations route to `jl3lovegrouptravel`, which is not searchable from this session. Status: **UNVERIFIED, not disproven.**

### 2. Heer Ann & Shawn — Japan — departs Aug 16, 2026 (17 days out) — **STALE, UNVERIFIED**
`dossiers/Heer_Ann_Shawn_Japan.md` carries an explicit `Last Updated: 2026-05-21` — **70 days old** for a trip 17 days out. Status flags present: `TBD`, `🔴`. Gmail search (`Heer Japan confirmation flight August`, both mailboxes) returned **zero results** — no confirmation, but also no denial. Same caveat as above: could be sitting in the unreachable third mailbox or under different terms. **Flag for direct Commander/Dani check, do not assume unbooked.**

### 3. Grandeur Scandinavia group — embark Aug 29, 2026 (30 days out) — **CONFIRMED FACTUAL ERROR**
This is the clearest, ground-truthed finding in the sweep.

`dossiers/DOSSIER_Grandeur_Scandinavia_Aug2026.md` (the master group dossier) states `Last Updated: March 26, 2026` — **126 days stale** — and still lists, as current:
> Hotel: Haymarket by Scandic, Stockholm ... Transfers: Private car ARN airport → Haymarket (Bedsonline)

This is **wrong**. Cross-checked against three independent sources that all agree with each other:
- `GROUP_Grandeur_Scandinavia_Aug2026_TRACKER.md` ("CURRENT TRUTH" doc): `~~Haymarket By Scandic~~ ... superseded by At Six ... ✅ CANCELLED` and all three Haymarket transfers `✅ CANCELLED ×3`.
- All three individual client dossiers (`Furlow_Regent_3071222.md`, `Ely_Darrow_Regent_3096289.md`, `Nichols_Regent_3078056.md`, each substantively edited 2026-07-28 — verified via `git show`, not just touched) show the client-directed switch to **At Six Stockholm**, with new transfers **confirmed via Project Expedition** (PE184710612 / PE184711812 / PE184712212).
- Gmail (`d2mconcierge`): Project Expedition confirmation emails dated **2026-07-12**, plus a client Voyage Preview email sent 2026-06-27 stating "Your Seven Seas Grandeur itinerary is locked in — Suite 827, Deck 8, specialty dining confirmed, excursions booked."

So the master dossier is telling whoever reads it to send this group of 3 couples, embarking in 30 days, to a hotel that was cancelled a month ago, via a transfer that was also cancelled. Same failure class as the DoorCounty hotel-cancel warning: a stale field sitting where someone would act on it.

**Secondary find in the same cluster:** `grandeur_group_logistics_matrix_20260702.md` was substantively edited 2026-07-28 (transfer decision recorded), but still contains a stale contradicting line further down: `ARN → At Six transfer | ❌ NOT BOOKED` for all three couples — even though the individual dossiers and Gmail confirm all three transfers were booked 2026-07-12. Same file, two different truths.

**Not stale, for contrast:** the three individual client dossiers themselves (Furlow/Ely-Darrow/Nichols) and the GROUP_TRACKER are current and internally consistent — this is specifically a "master/summary doc lagging behind the per-client dossiers" failure, not a wing-wide one.

**Cosmetic-touch-only files (git date is fresh, content unverified beyond header):** `MISSION-087_FIRE_ON_GO_RUNBOOK.md` and `grandeur_group_schengen_verification_2026.md` both show a 2026-07-28 git date, but `git show` on that commit reveals the only change was appending two HTML comment markers (`<!-- PHASE4_LIFECYCLE_STAGED_V1 -->` etc.) — no content update. Their actual status content was not deep-verified in this pass.

### 4. Loucks Regent Grandeur Panama — FPD Sep 30, 2026 (62 days out)
`DOSSIER_Regent_Loucks_Dec2026_UPDATED.md` flags itself: `ERROR: Final Payment Date recorded as 2026-09-30`. This is a **known, self-flagged** issue already on the record, not a silent staleness case — but it's inside the 90-day window and unresolved, so it belongs on the list.

### 5. DoorCounty Sister Bay — Sep 6-7, 2026 (38 days out) — RESOLVED
`DOSSIER_DoorCounty_SisterBay_Sep2026.md` — the original incident. Confirmed already patched: git date 2026-07-30, content now reads `✅ BOOKED ... Confirmed by Commander 2026-07-30`. Included here only as the baseline/proof the fix landed.

## Root cause confirmed: git date ≠ content date

Commit `0d3af2a4b` ("dossier: update Loucks Dec 2026 Grandeur hotel details from portal", 2026-07-28) touched dozens of unrelated dossier files. On `DOSSIER_Grandeur_Scandinavia_Aug2026.md`, `MISSION-087_FIRE_ON_GO_RUNBOOK.md`, and `grandeur_group_schengen_verification_2026.md` the *entire diff* was appending two autonomous-staging HTML comments (`EXCURSIONS_STAGED_TRUE`, `PHASE4_LIFECYCLE_STAGED_V1`) — no content change. That's why `git log -1` on these files reports "2026-07-28" (2 days old, looks fine) while the actual booking/status content is 70-126 days old. **Any future staleness sweep that uses `git log` or filesystem mtime as the freshness signal will produce false negatives exactly like this one.** Only 11/88 dossiers carry an explicit in-document "Last Updated" field to check against instead.

## What this sweep could NOT verify

Per the standing gap: Regent confirmations route to `jl3lovegrouptravel@...`, which has no MCP token in this session. Every "no confirmation email found" result above (Lyons Grande Bretagne, Heer Japan) is an **absence of evidence, not evidence of absence** — it is explicitly not being reported as "unbooked." The only positive confirmations found came from `d2mconcierge` (Project Expedition, client emails) and `johnloucks3` (forwarded itineraries), both of which were reachable.

## Recommendation

1. Fix `DOSSIER_Grandeur_Scandinavia_Aug2026.md` Section 2 (hotel/transfer) and the flight-gap note — both are actively wrong for a trip 30 days out. (Not done — this sweep is read-only per instructions.)
2. Fix the stale "NOT BOOKED" transfer line in `grandeur_group_logistics_matrix_20260702.md`.
3. Resolve the Lyons Aug 10 check-in contradiction — pull one of the two conflicting files or reconcile them.
4. Confirm Heer Japan Aug 16 booking status directly (Commander/Dani) rather than by email search — the unreachable mailbox makes this sweep blind here.
5. Systemic: stop trusting git/mtime for staleness; require the 77 dossiers with no "Last Updated" field to get one, and treat "touched by staging engine" commits as non-substantive.
