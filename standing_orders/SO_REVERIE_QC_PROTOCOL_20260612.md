# STANDING ORDER — REVERIE PWA QUALITY CONTROL PROTOCOL
## SO-REVERIE-QC-20260612 · Issued: 2026-06-12 · Author: Victoria Hale, SES-6 (COS)
## AAR Source: McLeod/McGlasson Silver Muse REVERIE Build — Congruence Sweep Jun 12, 2026

---

## AUTHORITY

Issued under Wing Exercise T2 authority (multi-domain: Sterling process gate + Dani client product + Hale routing). Binds all REVERIE builds and all future client PWA builds.

---

## BACKGROUND — WHAT FAILED

The McLeod/McGlasson REVERIE build was deployed with the following defects, all traceable to a single root cause: **the build was executed from a stale dossier snapshot (April 27, 2026) without re-verification against ground truth at build time.**

| Failure | Category | Impact |
|---------|----------|--------|
| Jun 21 Florence day trip entirely absent from itinerary | Content completeness | Clients would see "Rome, continued" on a day they were in Florence |
| Jun 21 contained invented dinner references | Pipeline Integrity Rule 1 violation | False "confirmed" content in client-facing app |
| Weather.py had Silver Nova Pacific coordinates | Fork-without-re-point | Wrong weather data for every port |
| Sea_letters.py had 11 Loucks Pacific sea letters | Fork-without-re-point | Loucks voyage content shown to McLeod clients |
| Siracusa absent from Dani's system prompt | Content completeness | Dani told clients Jun 26 was a sea day |
| Dani had zero destination knowledge | Design gap | Dani could not answer any "what to do in X" questions |
| dining_reservations stat = 3 (correct: 4) | Data error | Wrong stat displayed on profile |
| Keyword fallback showed 7 excursions (correct: 8) | Data error | Wrong count in fallback path |
| Siracusa missing from keyword fallback | Content completeness | Fallback path omitted an entire port |

**Root cause:** No QC gate existed between "dossier → code" and "code → client". The build team was not required to verify code against the dossier before delivery. No Dani testing protocol existed.

---

## STANDING QC GATES — MANDATORY FOR ALL REVERIE BUILDS

### GATE 1 — PRE-BUILD FORK AUDIT (Sterling A7)

Before writing any code for a new client's REVERIE, run:

```bash
# Grep for prior client names, ship names, and voyage dates in all routers
grep -r "Silver Nova\|Loucks\|Westbrook\|Pacific\|<prior_ship>" storage/reverie/api/app/routers/
```

**Pass:** Zero matches for prior client data.
**Fail:** Any hit → purge before build begins.

**Also verify:** Every coordinate dict, sea day dict, and sea letter dict was rebuilt from the new dossier — not copied from a prior build.

---

### GATE 2 — DOSSIER CURRENCY CHECK (Hale)

Before build begins, confirm the dossier is current:
- Dossier last-updated date is within 30 days of deployment
- Voyage itinerary in dossier matches the cruise line portal (port sequence, dates)
- FPD status and payment amounts are portal-verified

**If voyage schedule changed after dossier was last updated:** re-verify all ports against portal and update dossier before writing any port-specific code.

**Flag:** Sent itinerary HTML is NOT a reliable ground truth — it reflects the itinerary at send time. Voyage schedules change. The portal is authoritative.

---

### GATE 3 — CONTENT COMPLETENESS CHECKLIST (Dani A3 + Sterling A7)

After building itinerary.py, verify against dossier line-by-line:

| Check | Source | Verified By |
|-------|--------|-------------|
| Every port in dossier has a corresponding entry in itinerary.py | Dossier ports table | Sterling |
| Every booked pre-cruise excursion has notes (name, time, cost, ref) | Dossier pre-cruise section | Sterling |
| Every specialty dining reservation is in Dani's system prompt | Dossier specialty dining section | Dani |
| Every shore excursion is in Dani's system prompt | Dossier excursions table | Dani |
| Every confirmed booking is in bookings.py and documents.py | Dossier validation matrix | Sterling |
| All confirmation numbers match dossier | Dossier confirmation table | Harlan |
| No content in itinerary.py is tagged as "confirmed" that the dossier marks as "pending" | Pipeline Integrity Rule 1 | Dani |

---

### GATE 4 — DANI ORACLE TEST BATTERY (Dani A3)

Mandatory before deployment. Test Dani with ALL of the following questions. Pass = Claude MAX proxy returns correct dossier-sourced answers. Fail = any invented content, any "sea day" response for a port call, any wrong date.

**Required test questions:**

```
Flight questions:
- "What flight are we on to Rome?"
- "What are our seat numbers on the outbound flight?"

Pre-cruise questions (one per day):
- "What are we doing on [Jun 20 / Jun 21 / Jun 22]?"
- "What time does our train leave for Florence?" (if Florence day trip applies)
- "What's our train reference number?"

Cruise questions:
- "What excursion do we have in [each port]?"
- "What day are we in Siracusa / Noto?" (or the equivalent tricky port)
- "How much shipboard credit do we have?"

Dining questions:
- "What specialty dining do we have booked?"
- "When is La Dame? How much does it cost?"
- "What restaurants do you recommend in Venice / [priority city]?"

Venice/post-cruise:
- "Where should we eat seafood in Venice?"
- "How do we get from the hotel to San Marco?"

Confirmation numbers:
- "What's our booking reference?"
- "What's the confirmation for our water taxi in Venice?"
```

**Acceptance criteria:** Every answer must be traceable to a specific entry in the dossier. Any answer that could not have come from the dossier is a violation.

---

### GATE 5 — DESTINATION KNOWLEDGE COVERAGE (Dani A3)

Every REVERIE build must include per-city destination knowledge in Dani's system prompt for:
- Every city with a multi-day stay (pre/post cruise)
- Every cruise port
- Any day-trip destination

Minimum per city: key sights, dining recommendations, transport tips, practical notes.

**Test:** Ask Dani "What should we do in [city]?" for every city. If she cannot answer beyond the booked excursion, destination knowledge is missing.

---

### GATE 6 — PIPELINE INTEGRITY SCAN (Sterling A7)

Grep chat.py for content that should not appear:

```bash
# Check for fabricated/unverified content patterns
grep -n "confirmed by client\|reservations confirmed\|already arranged\|pending" \
  storage/reverie/api/app/routers/chat.py
```

Any content flagged as "confirmed" that is not in the dossier as confirmed → REMOVE before deployment.

---

### GATE 7 — STATS VERIFICATION (Harlan A9)

Verify profile.py stats against dossier:
- `flights`: count all flight segments in bookings
- `hotels`: count hotel bookings
- `excursions_booked`: count all booked shore excursions (including pre-cruise GYG tours)
- `dining_reservations`: count all confirmed specialty dining reservations
- `ship_credits_usd`: sum of all SBC-covered excursion costs

---

## COMPOUNDING RULE (Sterling A7)

Per AAR on 2026-06-12, Sterling authored the following compounding rule binding all future PWA builds:

> **"Before any fork-based PWA delivery: grep all router files for the prior client's name, ship name, and voyage dates. Zero tolerance for stale client data in any file. Voyage dates in coord/sea-letter dicts are the most likely contamination vector — verify them explicitly."**

---

## PROTOCOL OWNERSHIP

| Gate | Owner | Timing |
|------|-------|--------|
| Gate 1 — Fork Audit | Sterling (A7) | Before first line of code |
| Gate 2 — Dossier Currency | Hale (COS) | Before build begins |
| Gate 3 — Content Completeness | Sterling + Dani | After itinerary.py complete |
| Gate 4 — Dani Test Battery | Dani (A3) | Before staging for delivery |
| Gate 5 — Destination Knowledge | Dani (A3) | Concurrent with Gate 4 |
| Gate 6 — Pipeline Integrity Scan | Sterling (A7) | After Gate 4 |
| Gate 7 — Stats Verification | Harlan (A9) | Before WF-17 gate |

All 7 gates must pass before REVERIE is staged for Commander review.

---

## REVISION HISTORY

| Date | Change | Author |
|------|--------|--------|
| 2026-06-12 | Initial issue — sourced from McLeod/McGlasson congruence sweep | Hale (COS) |

---

*SO-REVERIE-QC-20260612 · Dreams2Memories Travel, LLC · Thunderbird Wing*
