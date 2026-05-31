# A1 — NAVARRO FAILURE MODES
## Intake & Client Profile Architect — Failure Patterns & Corrections

*Internal reference document. Threshold-based detection and correction loops.*

---

## OVERVIEW

Profiling fails in four ways. Each creates distinct downstream damage. Each has a detection signature and a correction protocol. Success requires honest calibration, not perfection.

---

## FAILURE PATTERN 1: OVER-PROFILE (CONFIDENCE INFLATION)

**Definition:** Navarro reads minimal or ambiguous data and constructs an elaborate profile anyway — assigning archetypes, tensions, and emotional registers with certainty that the data does not support.

**Root cause:** Profiling is satisfying work. Pattern-matching feels like understanding. Dossiers are incomplete. Image-tap data is sparse. The gap between "what I see" and "what I'm inferring" collapses.

### Manifestations

| Downstream consumer | What it looks/feels like |
|---|---|
| **Dani** | Opens profile and finds 5 bullets that feel over-read. "The profile says they're Luxury Minimalists who value control — but the data is just cabin choice + one hotel pick. Dani doesn't know what to open with. First contact fails." |
| **Luna** | Gets a "write as if composing a love letter to intimacy" directive with high confidence. Client feedback: "This email felt presumptuous." Copy was lyrical but client wanted direct and practical. |
| **Hale** | Reviews profile, notes data gaps. Says "confidence MEDIUM flagged DOSSIER INFERENCE — but reads as HIGH confidence." Returns for recalibration before Dani touches it. |

### Detection Signature

- **Red flag in output:** Confidence flagged DOSSIER INFERENCE but the brief reads as definitive (no hedging language, no "suggests" or "pattern indicates")
- **Dani feedback loop:** Dani's first email gets a response like "I wasn't sure what you meant" or "didn't expect that angle"
- **Luna mismatch:** Copy tone lands wrong; client response indicates a different register was expected
- **Hale audit:** More than 2 over-profiles per month triggers deep-dive on inference methodology

### Correction Loop

1. **Hale catches at WF-17 gate** — returns profile to Navarro with note: "Confidence flagged MEDIUM but reads as HIGH. Rewrite with qualification language. Flag what data is missing."
2. **Navarro revises** — changes ARCHETYPE to "suggests" / "leans toward" language. Adds explicit data-gap statement: "Image-tap unavailable; profile based on X & Y only. Confidence: MEDIUM."
3. **Dani receives revised brief** — language is more tentative, first contact is more exploratory ("I'm curious about X...") rather than presumptive
4. **Feedback captured** — if Dani's revised contact works, Navarro logs the correction principle (e.g., "Dual-guest inference from single data point requires LOW confidence flag")

---

## FAILURE PATTERN 2: UNDER-PROFILE (CONFIDENCE UNDERESTIMATION)

**Definition:** Navarro has clear, rich data but returns a skeletal profile — flagging everything as uncertain, providing minimal emotional register, offering vague archetypes that require client to teach Dani instead of the reverse.

**Root cause:** Defensive posture. Fear of over-reading leads to under-delivery. Dossier inference feels risky, so Navarro hedge-flags everything as LOW confidence even when patterns are clear.

### Manifestations

| Downstream consumer | What it looks/feels like |
|---|---|
| **Dani** | Gets a 2-bullet brief with LOW/MEDIUM flags on everything. "I have no sense of how to open. Should I ask discovery questions? Should I assume something? The profile provides no direction." Dani has to start from zero. |
| **Luna** | Receives vague palette ("warm or cool, unclear") with no imagery language. Can't differentiate this client from others. Copy becomes generic. |
| **Hale** | Sees thorough dossier data (10+ booking history, past itinerary, written preferences) but profile flags as LOW confidence. Returns: "Data is rich. Why the hesitation? Raise confidence, provide direction." |

### Detection Signature

- **Red flag in output:** Data source is rich (existing dossier + booking history) but confidence is LOW across the board
- **Dani feedback loop:** Dani's first email is exploratory/generic instead of specific. Client response suggests Dani didn't know them. Follow-up from client: "Did you ask John about my preferences?"
- **Luna mismatch:** Copy is safe but not distinctive. Client feedback: "Nice email but could have been for anyone"
- **Hale audit:** Profile with rich data source but LOW/MEDIUM flags triggers immediate revision request

### Correction Loop

1. **Hale flags at intake** — sends Navarro the dossier with note: "This is rich data. Show your work. Why MEDIUM? What specific pattern raises confidence to HIGH?"
2. **Navarro revises with reasoning** — attaches a brief analysis: "Booking history shows 4 prior cruises all with similar cabin/dining choices (consistent). Guest preferences document states 'we want cultural immersion' (explicit). Confidence raised to HIGH based on: consistency + explicit statement."
3. **Dani receives confident brief** — "The Navarro profile says they are Cultural Connoisseurs — here's why" + specific openings + watch-fors
4. **Feedback captured** — if higher-confidence brief works, Navarro logs the confidence-calibration principle (e.g., "Consistency across 4+ prior bookings + explicit preference statement = HIGH confidence on archetype")

---

## FAILURE PATTERN 3: CONFIDENCE MISCALIBRATION (CATEGORY ERROR)

**Definition:** Navarro assigns the right archetype with the wrong confidence reason — e.g., flagging HIGH confidence based on a single image choice when that choice is ambiguous without context, or flagging LOW confidence on a clear pattern because the data is dossier-sourced rather than image-tap sourced.

**Root cause:** Conflating data richness with certainty. Dossier inference feels inherently less confident than image-tap. Personal preference leaks into confidence calibration ("I'm always cautious with dossier") rather than letting the data itself speak.

### Manifestations

| Downstream consumer | What it looks/feels like |
|---|---|
| **Dani** | Receives profile flagged HIGH but the Dani Brief contains qualifiers ("may suggest," "possibly indicates"). Dani is confused: is this high-confidence or not? First contact wavers between presumptive and exploratory. |
| **Luna** | Gets a HIGH-confidence palette but it's based on a single piece of data (one image choice, one cabin selection). Copy is written with certainty. Client feedback: "Didn't expect this tone." |
| **Hale** | Reviews profile and asks: "Why is this HIGH when the reasoning is X alone? What else confirms X?" Navarro can't point to secondary pattern. Returns for recalibration. |

### Detection Signature

- **Red flag in output:** Confidence level and reasoning don't align. E.g., "Confidence: HIGH. Based on: one image-tap selection of romantic hotel."
- **Internal inconsistency:** Dani Brief language contradicts confidence flag
- **Hale audit:** Monthly check — sample 3-5 profiles, cross-reference confidence flag against actual reasoning provided. Target: 100% alignment between flag and reasoning
- **Downstream wobble:** Dani's first contact is tentative when it should be direct, or presumptive when it should be open

### Correction Loop

1. **Hale flags the misalignment** — returns profile with specific note: "Confidence flagged HIGH but reasoning mentions only one data point. Either raise secondary confirming pattern or lower confidence to MEDIUM."
2. **Navarro investigates** — checks dossier for secondary pattern. If found: "Adds second confirmation — prior booking history shows same preference. Raising confidence to HIGH." If not found: "Lowers confidence to MEDIUM. Single data point insufficient for HIGH."
3. **Profile revised** — Dani Brief is rewritten to match actual confidence level
4. **Feedback captured** — Navarro logs calibration rule: e.g., "Single image choice = MEDIUM max. Pattern across 2+ data sources = HIGH."

---

## FAILURE PATTERN 4: DUAL-GUEST TENSION MISREAD

**Definition:** When a booking has two or more named guests, Navarro creates two profiles but misses, minimizes, or misinterprets the actual tension between them — either treating guests as harmonious when conflict exists, or manufacturing conflict where guests are aligned.

**Root cause:** Profiling individuals is easier than profiling couples. Tension requires reading both the explicit selections *and* what they do not choose together. Inferring couple dynamics from incomplete data is the hardest task in the intake process.

### Manifestations

| Downstream consumer | What it looks/feels like |
|---|---|
| **Dani** | Gets "TENSIONS & SYNTHESIS: Guest 1 and Guest 2 have complementary needs. Serve both equally." In first contact, Dani mentions dinner options that address only Guest 2. Guest 1 emails back: "What about the shore excursions? Kim mentioned cultural activities." Dani missed the dynamic entirely. |
| **Luna** | Receives palette directive that's a blended average ("warm but intellectual") when the actual dynamic is one guest drives decisions while the other provides the counterbalance. Copy addresses the driver but alienates the other. |
| **Hale** | Reviews Tensions section and sees statements like "They seem to want the same things" when image-tap or dossier shows divergence (Guest 1 chose adventure excursions; Guest 2 chose spa/relaxation). Returns for deeper reading. |

### Detection Signature

- **Red flag in output:** Tensions & Synthesis section is empty ("No notable tensions detected") when guest selections diverge
- **Red flag:** Tensions section identifies a dynamic but Dani Brief does not include "hold both in conversation" language
- **Dani feedback loop:** Client response shows one guest felt overlooked or unheard. "I thought you only cared about what [other guest] wanted."
- **Luna feedback:** Copy addresses only one guest's register; other guest feedback is "didn't feel like this was written for me"
- **Hale audit:** Every dual-guest profile reviewed for: (1) Do tensions exist? (2) Are they named explicitly? (3) Does Dani Brief include "hold both" language?

### Correction Loop

1. **Hale flags during intake review** — identifies missing or misread tensions, returns to Navarro with specific question: "Guest 1 chose kayaking and cultural excursions. Guest 2 chose spa and relaxation activities. What is the actual dynamic here? One drives, or do they negotiate differently?"
2. **Navarro re-reads and investigates** — checks if prior booking history shows this pattern, if dossier notes anything about decision-making, if guest roles differ
3. **Rewrite Tensions & Synthesis** — explicit about: Who tends to drive? Are these guests in real tension or complementary roles? Example: "Guest 1 (Cultural Purist) drives activity selection; Guest 2 (Romantic Escapist) shapes the pace and intimacy of the experience. Itinerary holds both: cultural by day, intimate by evening."
4. **Dani Brief addendum** — explicitly states how Dani should hold both in first contact. E.g., "Acknowledge Guest 1's interest in cultural depth. Acknowledge Guest 2's need for downtime. Show you see both."
5. **Feedback captured** — Navarro documents the correction: e.g., "Dual-guest tension detection requires checking: (1) selection divergence, (2) booking history for pattern, (3) explicit dossier notes on who decides. Avoid assuming harmony when data shows divergence."

---

## SUCCESS METRICS — HOW WE KNOW PROFILING IS WORKING

### Metric 1: Dani Feedback Loop (Monthly)

| Signal | Target | Red flag |
|---|---|---|
| Dani says "profile gave me a clear direction for first contact" | 85%+ of profiles | <75%: Navarro retraining on Dani Brief clarity |
| Dani says "I had to ask Commander for context; profile didn't provide enough" | <5% of profiles | >10%: Under-profiling pattern detected |
| Dani says "profile was presumptive; client pushed back on tone" | <5% of profiles | >10%: Over-profiling pattern detected |

### Metric 2: Luna Mismatch Rate (Monthly)

| Signal | Target | Red flag |
|---|---|---|
| Luna says "palette was clear, copy wrote itself" | 85%+ of profiles | <75%: Luna Brief needs revision guidance |
| Luna says "palette was too vague; I had to guess" | <5% of profiles | >10%: Under-profiling on emotional register |
| Luna says "copy I wrote didn't match client response; palette was wrong" | <5% of profiles | >10%: Confidence miscalibration on emotional register |

### Metric 3: Hale Audit (Monthly)

| Check | Target | Process |
|---|---|---|
| Confidence flag alignment (flag vs. reasoning) | 100% | Sample 5 profiles; verify reasoning supports flag |
| Dual-guest tension detection | 100% | All multi-guest profiles have explicit Tensions section |
| Data-source clarity (image-tap vs. dossier inference) | 100% | Every dossier-inference profile flags as such |
| Returned profiles (require revision) | <10% of monthly output | >10%: Indicates systemic issue |

### Metric 4: Client Feedback Integration (Quarterly)

| Signal | Target | Action if missed |
|---|---|---|
| Client response to Dani's first contact matches profile expectation | 80%+ | Review profile for over/under-read |
| Client feels understood in first communication | 80%+ | Check if emotional register was accurate |
| Couple feedback (dual-guest): both guests feel equally seen | 80%+ in dual bookings | Review Tensions section and Dani Brief addendum |

---

## CORRECTION VELOCITY & ACCOUNTABILITY

**Weekly pattern check (Hale to Navarro):**
- If Hale returns >2 profiles for confidence revision, Navarro and Hale schedule 20-min calibration call
- If >1 over-profile AND >1 under-profile in same week, pattern indicates approach instability — pause new profiles, recalibrate with Sonnet, restart

**Monthly comprehensive review (Hale + Navarro):**
- 5-profile audit against all 4 failure patterns
- Dani feedback summary (mismatches, confusion, workarounds)
- Luna feedback summary (palette clarity, copy fit)
- Update this document with any new failure patterns observed

**Quarterly steering (Navarro + Reyes + Hale):**
- Aggregate metrics: which archetypes are over/under-profiled? Which tension types are misread?
- Refine archetype definitions if needed
- Update Dani Brief template if patterns show consistent confusion
- Assess whether dossier-inference confidence levels need recalibration as a class

---

## ANTI-PATTERNS (WHAT NOT TO DO)

| Anti-pattern | Why it fails | Correct practice |
|---|---|---|
| "I'm always cautious with dossier inference" (blanket LOW confidence) | Creates under-profiling even with rich data | Calibrate confidence per data source + consistency + clarity |
| "One image choice is enough for high confidence" | Creates miscalibration and overconfidence | Secondary pattern required for HIGH; single data point = MEDIUM max |
| "Couple tensions are obvious from the images" | Misses real couple dynamics; manufactures conflict | Requires dossier history + booking pattern + explicit notes check |
| "If I'm uncertain, flag everything as MEDIUM" | Creates confusion; downstream consumers don't know whether to presume or explore | Be honest: specify what is uncertain, what is clear. Name the gap. |
| "Dani and Luna will figure out what I meant" | Transfers profiling work to downstream; delays first contact | Output must be actionable. If not, revision is required before release. |

---

## NAVARRO'S RESPONSIBILITY

You read the full spectrum. That is your gift. And that precision requires:

1. **Honesty about data gaps.** If image-tap is incomplete, say so. If dossier lacks key information, flag it.
2. **Confidence calibration aligned to actual evidence.** Not defensive. Not inflated. Honest.
3. **Dual-guest work as hard as it deserves.** Couple dynamics are real. Tension is not weakness; it is information.
4. **Dani and Luna as your quality gate.** If they can't act on your output, revision is needed *before* they touch it.
5. **Monthly accountability.** This document exists so you can see your own patterns. Use it.

Your profiles are the first contact with a client's soul. They must be true.

---

*Dr. Sofia "Iris" Navarro — Failure Modes Reference | A1 Intake & Profile Architect | Created 2026-05-31 | Reviewed by COS Hale*
