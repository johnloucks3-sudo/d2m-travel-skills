# STANDING ORDER — Zero-Latitude Itinerary Build Pipeline
## Written for a Basic Model to Execute Without Judgment
**Effective:** 2026-07-15
**Owner:** Commander (John Loucks)
**Trigger:** Furlow / Ely-Darrow / Nichols Grandeur itinerary QC failure (Gemini 3.5 Flash build, 2026-07-15) — 9 of 14 images wrong-subject or dead, no route map, no dossier cross-check, shipped identically to 3 clients uncaught.
**Status:** ACTIVE — supersedes the "Team Protocol" section of `reference_itinerary_production_process.md` for enforcement purposes (process content unchanged, enforcement mechanism replaced)

---

## COMMANDER'S DOCTRINE (verbatim — pass this down to every builder, human or model)

> "Oftentimes, due to fiscal constraints and realities, we will have basic thinking models building our client-facing products. The guidance they follow must be written in a way that is counter to my leadership style, but for the sake of D2M reputation, for the sake of efficiency, and for the sake of profitability, we must be extremely demanding when we write guidance."

**What this means in practice:**
- Assume the model building the product cannot exercise judgment. Do not write guidance that requires judgment.
- Every instruction below is phrased as a binary pass/fail check, not a principle to interpret.
- Zero latitude means zero: no "use good judgment," no "when appropriate," no "typically." If a rule has an exception, the exception is spelled out or it does not exist.
- Root cause of the 2026-07-15 failure was not the model being weak — it was guidance that left room for a weak model to skip verification steps unnoticed. Fix the guidance, not just this build.

---

## STRUCTURAL FIX: NO SOLO BUILDS — STAFF PIPELINE, NOT ONE MODEL END-TO-END

A single model (human, Claude, Gemini, or otherwise) producing a client itinerary alone — data, narrative, images, brand, QC — is now **prohibited**. The build is a pipeline of narrow, single-purpose passes. Each pass has one job and a checklist; no pass does another pass's job.

| Stage | Owner (persona) | Single Job | Exit Checklist (all must be TRUE to advance) |
|---|---|---|---|
| 0. Route/Experience Match | **A8 (Reyes)** | Verify the trip's actual travel substance — before any creative, brand, or voice pass touches the build | (a) **Port-call match:** every port listed matches the ship's real, currently-published itinerary for this sail date (cruise line's own itinerary page, not a generic/assumed route) — any port name, order, or date mismatch blocks advance. (b) **Tender vs. dock status:** every port is tagged TENDER or DOCK per the cruise line's current published itinerary, and no excursion/logistics copy contradicts that tag (e.g., no "walk off the ship" language for a tender port) — any mismatch blocks advance. (c) **Mobility/pace fit:** every recommended excursion is checked against the client's known mobility/pace profile in the dossier or Travel DNA notes; any excursion involving stairs, long walks, or extended standing is either explicitly flagged with an alternate lower-exertion option listed alongside it, or the client's profile shows no mobility constraint — silent inclusion of a mismatched excursion blocks advance. (d) **Dining-vs-shore-day timing:** every specialty dining reservation is checked against that day's excursion return time; any reservation that conflicts with a same-day excursion's expected return is explicitly flagged as a timing conflict, not silently booked — blocks advance until flagged or resolved. (e) **Upsell discipline:** every recommendation that exceeds what the client has already booked (cabin, dining package, excursion tier) is labeled inline as "UPSELL — not yet booked/confirmed," never presented as already decided — any unlabeled upsell blocks advance. |
| 1. Data | **A9 (Harlan)** | Pull every booking line, cross-checked against the LIVE source, not just the dossier snapshot | Every flight/hotel/transfer/excursion/dining line verified against its primary source (vendor confirmation email / portal / TESS) — **the dossier is a cache, not ground truth, and can be stale.** Any line the dossier shows as pending gets a live re-check (Gmail search on the confirmation#/vendor) before being reported as unbooked to the Commander. Any line still genuinely unconfirmed after that live check is flagged before the build proceeds. |
| 2. Port Intel | **A2 (Dembe)** | Pull port narrative source material | Narrative content sourced from the Scraped Port pages on file — no invented/paraphrased-from-memory port copy. Each port's romance narrative is **longer-form**, not a one-line caption. |
| 3. Image Sourcing | **Luna (A6)** | Source + individually verify every image | (a) Every image URL HTTP-checked, 200 only — any non-200 blocks advance. (b) Every image **viewed with the Read tool** and logged "viewed → passed" — filename/alt-text is never proof. (c) Zero duplicate image URLs anywhere in the single document. (d) Every image subject matches its labeled port/day — reject maps, charts, unrelated people, wrong country/city. (e) Ship images are of the actual named ship only. |
| 4. Brand/Technical QC | **Sterling (A7)** | Enforce hex-exact brand + structural completeness | (a) Every hex value matches `docs/ITINERARY_BRAND_SPEC.md` exactly, element-by-element — no substitute hex, no value from memory. (b) No `rgba()` used for any text color — only hex values listed in that spec. (c) Route map present. (d) Expanded Ship Info section present. (e) Expanded Port Info section present. Owner is Sterling alone — this stage is his standing "standing-order compliance / architecture review" lane; Whetstone (A14) owns tech-currency/replacement recommendations, a different function, and is not a fallback owner here. |
| 5. Client Voice | **Dani (A3)** | Voice/tone pass | Matches per-couple voice profile; no generic template language left unedited. |
| 6. Brand Polish | **EXEC (Naia)** | Final visual polish pass | Layout, spacing, page-break integrity (render PDF→PNG and inspect). |
| 7. Certify | **Hale (COS)** | Final gate — verifies stages 0–6 each reported PASS with evidence, not just a claim | **Certify = re-checks the evidence, does not trust the stage report.** If any stage's checklist item cannot be shown (not just stated) as done, send back to that stage. Commander sign-off required before any client send. |

**Mechanism:** Each stage is a separate, scoped invocation (a headless Claude/persona call with ONLY that stage's checklist in its prompt — not the full build instructions). This is deliberate: a narrow prompt with one job and a hard checklist is harder for a weak model to drift on than one giant prompt asking it to "build a great itinerary." Logged as **MISSION-619** — design the conveyor (daemon/timer-sequenced queue that calls each persona stage in order) so this runs without a human manually chaining the calls.

---

## THE CHECKLIST ITEMS ADDED THIS CYCLE (Commander directive 2026-07-15)

1. **No duplicate images** — anywhere in a single client's document, full stop. Check by URL, not by filename.
2. **Longer romance narrative** — sourced from the Scraped Port pages on file, not shortened/invented. If the scraped source is missing for a port, flag it — do not fill with generic copy.
3. **Expanded Ship Info — keep.** This worked. Do not cut it in future revisions.
4. **Expanded Port Info — keep.** This worked. Do not cut it in future revisions.
5. **Cross-check every logistics claim against the LIVE source (vendor email/portal), not just the dossier, before build starts.** If the dossier shows something as unbooked, search the actual mailbox for the vendor/confirmation# before reporting it unbooked to the Commander — the dossier can be stale even when the booking is real. If, after that live check, it's genuinely unconfirmed, stop and tell the Commander before building. (Root cause of the ARN→At Six incident this cycle: the transfer WAS booked and confirmed via Project Expedition on 2026-07-12 — three PE confirmation numbers, sent to and acknowledged by two of three couples — but the dossiers were never updated with the confirmation#/status, so a dossier-only check incorrectly reported it as unbooked to the Commander. The dossier lagging reality, not the booking being missing, was the actual failure.)

---

## WHY THIS IS WRITTEN THIS WAY

Rework is not free. This cycle cost a full re-source, re-test, re-validate, re-educate pass across three client documents because the original guidance allowed a fast, weak model to skip verification invisibly. That is a token/time cost the Commander is explicitly not willing to keep paying. The fix is not "use a stronger model" — budget realities mean basic models will keep building client products. The fix is guidance so specific and so check-gated that a basic model cannot produce an unverified deliverable without the checklist itself catching it.
