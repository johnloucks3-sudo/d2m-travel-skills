# Trip Assembly Model — Specification
## Dreams2Memories Travel · defined with Commander, 2026-06-09 · Opus

> **Doctrine: AI does 99% of the work; the Commander does the irreducible 1%.**
> The 1% is the *terminal commit click* — the keystroke that sends to a client or
> moves money. AI drives everything up to that button (including operating the
> portal), and tracks/documents/captures everything after it.

This spec does **not** invent a lifecycle. The model already exists, in human form,
and was sent to clients. This captures it as canonical and specifies the machine
that finally *executes* it.

---

## 0. The core finding (why this exists)
The Kuklinski Applied Lifecycle Schedule (`docs/KUKLINSKI_LIFECYCLE_SCHEDULE.md`,
generated 2026-04-07) is correct and complete — 35 touchpoints, 6 phases, lead
times, owners. **Yet it flagged Insurance OVERDUE and Excursion "4 weeks late" in
April, and the June audit found the same items still broken.** The design was never
the problem; the machine doesn't run it. The whole build is: *make the system
execute the model you already drew.*

---

## 1. Canonical source artifacts (do not reinvent — consolidate)
- `docs/KUKLINSKI_LIFECYCLE_SCHEDULE.md` — the 35-TP / 6-phase template (CANONICAL)
- `docs/kuklinski_lifecycle_gantt.html` — the visual Gantt
- `portal/lifecycle_portal_kuklinski.html` — client portal view
- `drafts/commander_to_kyle_lifecycle_explanation.html` — the search-lifecycle explainer sent to the client
- `D2M/lifecycle/{Kuklinski,Loucks,McLeod,Morton_Dodge}_*_Lifecycle.md` — 4 per-client lifecycles
- `output/Kuklinski_Timeline_Touchpoint_Email_Library.md` — touchpoint email library
- Client SLAs (Drive): the proposal carries the scope-of-work (Kuklinski "Proposal & Service Agreement" is the template)

---

## 2. The trip lifecycle (Commander's model, in his terms)

**Pre-anchor (unpredictable, proposal-driven):**
```
Inquiry → Pre-booking → PROPOSAL (carries SLA scope)
  → Client-Info form · Demographic/Travel-DNA form
  → TESS portal invite (CC on file + PCI-secure comms, via Outside Agents)
  → Commit / SLA active
  → DEPOSIT [Commander click] → INVOICE → ⚡BAM⚡ (anchors lock: departure, FPD, return)
```

**Post-anchor (the 35-TP lifecycle — adaptable, client-driven):**
6 phases from the Kuklinski template:
- **Phase 0 Onboarding** — booking, dossier, insurance(0.4), guest forms(0.5), welcome
- **Phase 1 Discovery** — air fare watch, hotel fare watch, destination research, voyage preview
- **Phase 2 Momentum** — excursions, air booking, hotel booking, monthly validations, dining, doc audit
- **Phase 3 Pre-Departure** — pre-voyage brief, final confirmation, send-off
- **Phase 4 Voyage** — active monitoring
- **Phase 5 Post-Voyage** — welcome home, survey, referral, next-voyage plant

Secure-data/PII form fires after deposit, before air (passport names → air booking).
**Adaptable:** a client may pull air or hotels forward (Furlow); AI accelerates that
element rather than waiting for its window.

---

## 3. The SLA-becomes-the-clock engine (the keystone)
1. AI produces the **proposal**; it carries the **SLA scope of work** (e.g., "full
   management of airfare routing, hotel vetting, all ground logistics" + the value-
   table commitments: fare-bank tracking, OBC, deposit/insurance windows, re-entry).
2. AI **derives the trip's lifecycle clock** from those promises — a dated schedule
   like the Kuklinski one, instantiated for this trip.
3. **Commander approves the clock once.** (This is the one strategy gate.)
4. From that approval, AI **spoon-feeds**: every scan, proposal, form, and staged
   click on schedule, through post-trip — no further direction needed.

The SLA's scope items *are* the touchpoints. The clock is the SLA on dates.

---

## 4. Element clusters (what a trip assembles — all types, not just cruise)
Air · Hotels · Transfers (6 legs) · Excursions · Dining · Onboard · Documents/Visa/
Insurance · Financial rollup · Forms · Payment rail · Validation reports (internal +
client) · Narrative. Anchor types:
CRUISE / LAND_TOUR / INDEPENDENT / EVENT / FAVOR (element set filtered by anchor).

Per element, track the line item **and the options AI proposed** (not just the pick).

---

## 5. Forms (first-class touchpoints, with a capture loop)
Existing (consolidate — 2 are stubs, 1 is ship-specific):
Client Intro · Guest Profile · Client Profile(stub) · Secure Data Dossier(stub) ·
Regent Explorer Survey(ship-specific).

| Form | Fires | Feeds |
|---|---|---|
| Client Information | first contact/commit | the record |
| Demographic / Travel DNA | intake | excursion/dining/cabin recommendations |
| Secure Data (PII) | after deposit, before air | air booking + guest registration (avoids $500 name fees) |
| Trip Survey | pre-trip | sharpens scans |
| Post-Trip Survey | after home | referral + rebook |

**Capture loop (non-negotiable):** form sent → response captured into dossier/DB →
that data is what the downstream element actually uses. A form nobody reads back is
the write-without-read failure (see §8).

---

## 5.5 Validation reports (internal + client) — the biggest pain point
Two outputs from ONE monthly per-trip assessment:
- **Internal validation** — every active trip reviewed monthly (Kuklinski TP 2.5,
  "Monthly Validations ×8," 15th of month). Assess progress/problems. NO send. This
  is where overdue/at-risk elements surface — driven by the §8 dead-man's-switch.
- **Client validation** — sent at key points (the Kuklinski / Furlow / Ely / Nichols
  reports the Commander had to force out, "VERY painful"). Staged draft → Commander click.

**Why it was painful and won't be again:** a validation report is just a *rendering
of current element state.* It hurt because state was scattered (dossier + sheet +
portal + inbox) and assembled by hand, per client, every time. With the canonical
store (§9) + capture loop (§5/§8), the report writes itself:
- Internal = render all elements + flag stale/overdue/at-risk.
- Client = render the curated, reassuring subset → staged → click.

Existing machinery to consolidate (don't reinvent): `validation_email_generator.py`,
`storage/output/validation_emails/`, `sterling_validate_lifecycle.py`, the
`D2M_TenWeeksLater` series. The same applies to **every drafted touchpoint email** —
the manual drafting burden is the 99% the clock carries.

## 6. The payment rail & the 1%
- **TESS client portal invite** (Outside Agents, PCI): AI tees up the email; Commander
  sends; client enters CC into the compliant portal. **AI never touches card data** —
  it tracks status (`invite sent / CC on file`) only. One-time setup unblocks deposit
  AND FPD.
- **Commit surfaces (where the 1% click happens):**
  - Money → vendor portal (Regent/Viking/Silversea/Princess/Centrav). AI drives the
    browser to the **Pay button**; Commander clicks.
  - Client-facing → Gmail (Commander-Review). AI stages the complete draft; Commander
    clicks Send.
- Every element terminates at `STAGED_FOR_COMMIT` / `STAGED_FOR_SEND` → Commander's
  single click → AI books-confirms-documents-captures.
  *(Open decision: full portal-drive-to-button vs. AI-preps-deep-link for some portals.)*

---

## 7. Element states (maps SCHEDULE→CONDUCT→DOCUMENT→CAPTURE)
```
DORMANT →(window opens) DUE →(scan) RESEARCHING → OPTIONS_READY
  → STAGED_FOR_SEND/COMMIT →[Commander click]→ BOOKED → CONFIRMED → DOCUMENTED
            ↘ EXPIRED (window closed unactioned → PAGES; never silent)
```

---

## 8. Non-negotiables (from the 3-subsystem audit, 2026-06-09)
1. **Dead-man's-switch everywhere** — any scan that checks 0 / errors / hasn't
   succeeded in N hours PAGES. No more silent zeros (the Insurance/Excursion failures;
   air blind 12-26 days; lifecycle 0 drafts 3 days).
2. **One scheduler, one store per domain** — retire the 4 lifecycle schedulers / 4
   fare stacks down to the best one each; migrate the good dedup/completion logic.
3. **Write connects to read** — every scan result + form response lands in a queryable
   store AND is read back by the next element. (The MISSION-172 discarded-votes lesson,
   the 2.8 MB unread `tp_alerts.jsonl`, the arc_price_dispatcher JSONs with no reader.)
4. **No committed secrets** — the @D2MC2C token + Centrav cookies are in git; rotate +
   .gitignore (the D4 lesson).
5. **Completion model** — a done TP is marked done; no more 97 false-OVERDUE alerts.

---

## 9. Data model (hybrid)
- **DB (SQLite, the working `fare_watch_db` pattern):** `trips · elements ·
  element_options · element_events`. Queryable: "what did the air scan for McLeod
  TP4.2 find on date Y." Read path proven.
- **Dossier (markdown):** the human-facing narrative, *projected from* the DB. DB is
  state-of-record; dossier is the readable view; Booking Master sheet is the financial
  ground-truth (Harlan).

---

## 10. The Adasek guarantee
The SLA exists because a supplier (Personalized Services) went silent on John —
late disclosure, missed deadlines, forced emergency re-planning
(`ANALYSIS OF CORE SERVICE FAILURE`, Drive). The audit shows Thunderbird is currently
at risk of repeating it. **A lifecycle clock that executes autonomously, with a
dead-man's-switch, is the structural guarantee that the Adasek failure cannot happen
on the Commander's watch.** That is the point of the whole system.

---

*Status: model defined with Commander 2026-06-09. Milestones to be laid on this spec
after Commander review. Nothing built yet — this is the agreed target.*
