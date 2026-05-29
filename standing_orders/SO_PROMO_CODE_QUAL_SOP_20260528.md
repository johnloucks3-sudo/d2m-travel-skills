# STANDING ORDER — Promotional Code Qualification SOP
## SO_PROMO_CODE_QUAL_SOP_20260528
**Effective:** 2026-05-28 | **Issuing Authority:** A7 Sterling | **Supersedes:** No prior SOP (new)
**Owner (Execution):** A3 Moreau | **Owner (Audit):** A7 Sterling
**Trigger:** Root cause from Regent Code 4232 qualification failure — post-mortem `output/sterling_qc_code4232_postmortem.md`

---

## HARD RULE — CONFIDENCE LABEL RETIREMENT

**"HIGH PROBABILITY" IS RETIRED AS A PROMO ASSESSMENT LABEL. EFFECTIVE IMMEDIATELY.**

It conflates likelihood with confirmation. It is not a permitted label in any promo assessment document produced by this wing from this date forward.

**Replacement — Four-Tier Evidence-Gated System (mandatory):**

| Evidence in Hand | Maximum Confidence Label Allowed |
|---|---|
| Headline only (no T&C text, no BDM contact) | **NOT ASSESSABLE** |
| T&C text retrieved; client criteria match on paper | **POSSIBLE** — requires BDM confirmation |
| BDM verbal confirmation received | **PROBABLE** |
| BDM written confirmation OR portal application confirmation | **CONFIRMED** |

No analyst may assign a label above what the evidence tier supports. If in doubt, assign the lower tier.

---

## PROMO CODE QUALIFICATION CHECKLIST

**This checklist is MANDATORY for every promotional code evaluation.**
Step 0 must be completed before Step 1. Steps 1–4 must be completed before Step 5. Step 5 must be completed before Step 6.
No exceptions. No urgency overrides this sequence.

---

### STEP 0 — Full Booking Roster Sweep (MANDATORY — BEFORE ANY INDIVIDUAL ASSESSMENT)

**Before assessing any individual booking, sweep ALL active bookings for criteria match.**

This step is non-negotiable regardless of how many bookings were named in the originating request. Named bookings are a starting point, not the scope boundary.

**Required sweep criteria:**

- [ ] Ship class / cruise line (e.g., all Regent sailings, all Grandeur sailings)
- [ ] Travel date range (identify all bookings within the promotional travel window)
- [ ] Supplier (e.g., all Silversea, all Regent, all Viking bookings)
- [ ] Payment status (outstanding balance vs. paid in full — may affect eligibility tier)

**Required output:** A complete list of ALL active bookings matching the sweep criteria, with booking reference numbers and client names. This list is the scope of the assessment — not the list of bookings named in the prompt.

**Data sources (in priority order):**
1. TESS live roster query (preferred — most current)
2. Master booking sheet (interim standard pending TESS stealth browser capability)
3. Dossier directory scan

**Infrastructure note:** Full automated roster sweeps from TESS require live stealth browser access. A12 ELON is separately tasked to develop this capability. Until confirmed operational, execute Step 0 manually against the master booking sheet. The manual sweep is not optional — it is the interim standard.

**If Step 0 surfaces bookings not named in the original request:** Include them in the assessment. Surface the expanded scope to Commander in the brief. Do not silently narrow scope back to the named bookings.

**If Step 0 cannot be completed (data unavailable):** Document why. Do not proceed with an assessment scoped to named bookings only. Escalate to Hale for data access resolution.

---

### STEP 1 — Capture Headline Data

Document the following from TLN, MAGtap, or supplier portal:

- [ ] Code number
- [ ] Book-by date
- [ ] Travel window (start and end)
- [ ] Headline savings claim (exact language)
- [ ] Source portal (TLN / MAGtap / supplier direct)

---

### STEP 2 — Retrieve Full T&C Text (MANDATORY — BLOCKING)

Navigate to the T&C section for the specific code. If portal T&C is unavailable, call supplier BDM for restriction text before proceeding.

Document which of the following apply:

- [ ] New bookings only?
- [ ] Applies to existing bookings with outstanding balance?
- [ ] Applies to fully paid bookings via re-pricing?
- [ ] Requires re-booking (cancellation + rebook)?
- [ ] Stackable with existing SBC or discounts?
- [ ] Agency/IATAN eligibility requirements?

**If T&C text cannot be retrieved:** Assessment is BLOCKED. Label: NOT ASSESSABLE. No confidence label assigned. Escalate to BDM call. Do not proceed to Step 3.

---

### STEP 3 — Match Client Booking Status

For each client booking under evaluation:

- [ ] Booking age relative to code issue date (pre-existing vs. new)
- [ ] Payment status: deposit only / partially paid / paid in full
- [ ] Travel date vs. promotional travel window (confirm within window)
- [ ] Booking reference number documented

---

### STEP 4 — Assign Evidence-Tiered Confidence Label

Apply the four-tier system from the Hard Rule section above.

**Do not round up.** Necessary conditions are not sufficient conditions. A booking that meets travel window, ship, and payment status criteria matches NECESSARY conditions. If T&C has not been retrieved and BDM has not confirmed, the label ceiling is POSSIBLE — not PROBABLE, not HIGH PROBABILITY.

Document the evidence supporting the label assignment. If the label cannot be supported by documented evidence, assign the tier below.

---

### STEP 5 — Resolve All BLOCKED / Requires-Verification Items

Before any assessment document is finalized:

- Every item flagged in Steps 1–4 as "requires verification" or "BLOCKED" must be resolved.
- A BDM call counts as resolution only if the outcome is documented in the assessment (confirmed / denied / conditional).
- If an item cannot be resolved before the book-by deadline, the document must state:
  - What is unresolved
  - Why it cannot be resolved in time
  - What action Commander would be taking on incomplete information
  - The confidence label ceiling given the unresolved item (almost always: POSSIBLE or NOT ASSESSABLE)

**No assessment document is finalized with outstanding unresolved items unless the above three points are explicitly documented.**

---

### STEP 6 — Brief Commander Only After Step 5 Is Complete

Commander is not briefed on a promo assessment until the checklist above is complete and documented.

**If the book-by deadline does not allow time to complete the checklist:** Commander is briefed on the verification gap — not the unverified assessment. The brief includes: what was confirmed, what was not confirmed, what Commander would be deciding on, and what verification is still pending.

**This is non-negotiable.** A brief with outstanding unresolved items and no explicit disclosure of those items is a process violation (see `hale_decisions.md` entry 2026-05-28).

---

## SOP METRICS AND ENFORCEMENT

All four metrics at 100% or the SOP is not being followed. No sliding scale. Binary compliance.

| Metric | Definition | Target | RED Threshold | Cadence | Owner |
|---|---|---|---|---|---|
| `promo_full_roster_sweep_pct` | % of promo checks that included a full active booking roster sweep before any individual assessment was written | 100% | Below 100% | Per assessment; reviewed weekly | A7 Sterling |
| `promo_t_and_c_retrieval_rate` | % of promo assessments with T&C text on file before confidence label assigned | 100% | Below 100% | Per assessment; reviewed weekly | A7 Sterling |
| `promo_confidence_label_compliance` | % of assessments using the four-tier label system (retired "HIGH PROBABILITY" = automatic violation) | 100% | Below 100% | Per assessment | A7 Sterling |
| `promo_pre_brief_verification_gate` | % of Commander briefings where Step 5 was complete before briefing | 100% | Below 100% | Per Commander briefing | A7 Sterling |
| `promo_source_artifact_coverage` | % of client promo assessments named to Commander that have a traceable written artifact | 100% | Below 100% | Per assessment | A7 Sterling |

Metrics tracked in `OpsCenter/a7_metrics_dashboard.json` under `promo_qualification`.

---

## COMPOUNDING RULE (A7 Charter)

These four gaps are now permanent checklist items. They do not expire. They apply to every promo assessment from this date forward regardless of:
- Code number or supplier
- Urgency or deadline pressure
- Book-by window
- Whether the client has an existing relationship with the supplier

A book-by deadline that makes Step 2 impossible does not authorize skipping Step 2. It changes the outcome of Step 5: the brief discloses what was not verified, not a label that pretends verification happened.

---

## REFERENCE DOCUMENTS

- Post-mortem: `output/sterling_qc_code4232_postmortem.md`
- Process violation log: `hale_decisions.md` entry 2026-05-28
- Promo assessment that triggered this SOP: `output/promo_check_regent_silversea_20260528.md`
- Source intel sweep: `output/intel_sweep_roomres_magtap_20260528.md`

---

*Brig Gen (Ret.) Thomas "Gauge" Sterling, A7*
*Process, Technology, Metrics, Code & Schematic Oversight*
*Dreams2Memories Travel, LLC | Thunderbird Wing*
*Issued: 2026-05-28*

---

## AMENDMENT — 2026-05-28 (Commander Direction)

**Change:** Step 0 (Full Booking Roster Sweep) added as mandatory pre-step to the qualification checklist. New metric `promo_full_roster_sweep_pct` added (target 100%, red below 100%).

**Trigger:** Commander rejected initial post-mortem as incomplete. Root Cause #2 identified: promo check agent scoped to named bookings only, missing McLeod (2984034) which qualified on the same criteria as Loucks. A full roster sweep would have surfaced McLeod without Commander having to ask.

**Infrastructure dependency noted:** Live TESS roster sweeps require enhanced stealth browser capability. A12 ELON tasked separately. Manual roster sweep against master booking sheet is the interim standard — not optional.

*Amendment authored: 2026-05-28 | A7 Sterling*
