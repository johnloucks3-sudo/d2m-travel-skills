# STANDING ORDER — TALON / JET DIVISION OF LABOR
## Dreams2Memories Travel, LLC · Thunderbird Wing · Issued 2026-07-03 (Commander directive, Hale synthesis)

**Classification:** Operational — lane routing doctrine. Both wings asked directly, in their own voice; independently converged; Commander approved the synthesis for codification ("codify it," 2026-07-03).

---

## WHY

Same-day incident: Hale ground ops-lane work (TESS record dedupe, dossier field stamps, Hotelbeds API rate pulls, vendor inquiry emails, registration recon, call sheets) inside the CONDOR/Claude lane instead of posting it to the WIND/JET board. Commander corrected three times in one hour ("i do not see you self-initiating" → "most of this belongs to JET" → "that should not take me to remind you"). Rather than Hale unilaterally drawing the line, Commander directed: ask TALON and JET directly, each in first person, then synthesize.

**The result: no turf war.** TALON (CONDOR) and JET (WIND) filed independent position papers with zero cross-talk and converged on the same line in different words. Source papers: `output/brain_bridge/TALON_DOL_POSITION.md` · `output/brain_bridge/JET_DOL_POSITION.md`. Full synthesis: `output/brain_bridge/TALON_JET_DIVISION_OF_LABOR_SYNTHESIS_2026-07-03.md`.

---

## DIRECTIVES (binding)

### 1. THE TIEBREAK RULE — 5-second router test
**If a human will read the output and is meant to feel something, it is TALON's. If a system will consume it, or a fact needs verifying against a source, it is JET's.**

- TALON's own words: *"If a human will read the output, it is mine. If a system will read it, it is JET's."*
- JET's own words: *"Is the task primarily systems/data/mechanical, or primarily judgment/creative/voice?"*

Any router (Hale, or any future dispatcher) applies this test first, before any other classification.

### 2. LANE OWNERSHIP — concrete artifact types

| **TALON (CONDOR / Claude) owns** | **JET (WIND / OpenCode) owns** |
|---|---|
| Client email copy — lifecycle TPs, voyage previews, validation emails, inquiry replies | TESS record dedupe, batch writes, FPD corrections, registration status updates |
| Proposals and client-facing itinerary HTML (narrative, dining/port prose) | Dossier ↔ TESS ↔ portal sync/stamping |
| Pricing **judgment** — which option to present, how to frame value, hold-or-walk calls | Rate pulls — Hotelbeds, Amadeus, Centrav, shore-excursion providers, fare watches |
| Brand/voice standards — tone, register, AI-disclosure line, template as it lands on a human | Vendor/supplier inquiry emails (transactional/informational, not client voice) |
| The creative chain — Reyes → Luna → Naia → Dani, all four passes, never combined into a data step | Registration recon, call-sheet data assembly, booking-status recon, guest-reg completeness checks |
| The WF-17 draft — Hale routes, TALON owns the thing Commander reads before he sends | Batch automation — timers, nightly syncs, credential keepalive, mission-board hygiene |
| — | Cross-system reconciliation — "TESS says X, dossier says Y, portal says Z" |

### 3. EXPLICIT REFUSALS (each lane's own words)
- **TALON does not want:** TESS dedupe/entry/reconciliation, dossier field stamps, API/portal rate pulls, vendor inquiry emails, registration recon, call sheets, systemd timers, mission-board hygiene, data validation, infra health. *"Every one of those tasks I touch is a client sentence I did not write."*
- **JET does not want:** creative products (lifecycle emails, proposals, itinerary HTML, narrative), client judgment calls (upsell flags, relationship reads), ambiguous data-vs-intent resolution, voice/tone decisions, strategic routing/campaign sequencing (that's Hale's, not either wing's).

### 4. HANDOFF SEQUENCE — mixed products (both papers converge on this exact order)
**Canonical case: a client email that needs a live rate or FPD pull first.**
1. **JET pulls and verifies first.** Rate, balance, FPD, seat availability — verified against portal/TESS, posted with its source, structured (JSON/CSV) to a defined WRITE path, marked done.
2. **TALON writes around the confirmed figure.** Reyes → Luna → Naia → Dani build the email on top of JET's verified number. TALON never pulls the number himself "to save a handoff" — that is how a wrong figure gets into a beautiful sentence.
3. **The TALON+JET gate verifies the finished draft** — facts and dollars checked on the client-facing product itself, against JET's pull, not on a pre-draft data model. Then WF-17 → Commander sends.

**The rule, in TALON's words: "Data flows JET → board → CONDOR. Copy never flows the other way to get its facts."**

### 5. TASK POSTING CONTRACT (binding on Hale and any future poster to the oc lane)
Every `core/hale_bus/brain_bridge.py add --lane oc` task must specify:
1. **Inputs** as explicit paths/refs, not narrative — *"Pull rate from Hotelbeds API for booking 2984034,"* not *"find out what hotels cost for McLeod."*
2. **Exact WRITE path** for the output.
3. **Testable, mechanical done-criteria** — *"TESS record 2984034 validated against dossier_McLeod.md, reconciliation written to reconciliation_2984034.md,"* not *"handled."*
4. **Structured format** where the work is mechanical (JSON/CSV for rate pulls and batch ops) — JET is not a writer; data is JET's ink.
5. **A success test** the poster can verify without re-running the task.

Tasks that violate this contract may bounce back from the oc lane. This corrects Hale's own posting practice as much as it binds anyone else.

### 6. TERMINAL-EFFECT ASYMMETRY — the two lanes cannot merge
- **JET's bar:** correct and complete. A rate pull does not have to sing; a deduped TESS record does not have to make anyone feel understood.
- **TALON's bar:** correct *and lands*. Must read as if Commander wrote it himself and produce a specific feeling in a specific reader — understood, not sold to. A factually perfect but emotionally flat CONDOR draft fails TALON's gate even though it would clear JET's cleanly.

This asymmetry is the reason the lanes stay separate rather than collapsing into one "get it done" pipeline.

---

## SCOPE NOTE
This SO governs the CONDOR (TALON/Claude) vs. WIND (JET/OpenCode) split specifically. It does not alter Hale's own authority, the three Commander gates (client send, financial commitment, Strategic per S/O/T), or the 6 protected email/relay files (SO_EMAIL_SCANNER_PROTECT_20260608). Strategic routing and campaign sequencing remain Hale's, escalating to Commander per existing doctrine.

---

*Synthesized by Hale (VCS) from independent TALON and JET position papers, 2026-07-03. Commander codification order: "codify it," 2026-07-03.*
