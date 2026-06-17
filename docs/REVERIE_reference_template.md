# REVERIE REFERENCE TEMPLATE
## Dreams2Memories Travel, LLC
### How to Reproduce Gold-Standard Client Communications — Every Time

*Versioned: 2026-06-17 | Authored: Naia (EXEC) | Source: Silver Muse validation build (MISSION-225, PHASE2-04, and all lifecycle arc artifacts)*
*Classification: Internal — Not for client distribution*

---

## PURPOSE

This document extracts the pattern that produced the Wing's gold-standard client communication. It is a repeatable method, not a client-specific artifact. All personal identifiers have been removed. Every section header, design choice, voice rule, and checklist item describes the HOW — so the next build starts from a proven foundation rather than a blank page.

**Canonical HTML asset:** `/home/john/Thunderbird/output/PHASE2_04_Itinerary_Template_Generator_COMPLETE_20260429_140517.txt` — this is the 2200-line buildable HTML with full CSS design system. Reference it for structural code. This document explains what that code is doing and why.

---

## THE FIVE GOLD-STANDARD PRINCIPLES

These are the discriminators. Everything else in this document serves them.

### 1. Emotional Architecture (REVERIE)
Every word is written to a specific emotional register — not a demographic and not a budget tier. Before a single section is drafted, identify the dominant REVERIE pillar for this client at this moment:

- **THE RETURN** — Client is reconnecting with who they were before obligation took over
- **HELD** — Client needs logistics to disappear completely; relief is the luxury
- **WITNESSED** — Client needs the world to confirm their life is worth exactly this
- **EARNED** — Client is claiming a reward they have been building toward
- **THE DREAM THAT HAS A DATE** — The conditional tense ("someday...") has finally become a fact
- **DEPTH** — Client wants genuine encounter, not packaged experience
- **TOGETHER** — The relationship is the reason; the ship is the container

**The rule:** The dominant pillar shapes the opening paragraph. The secondary pillar shapes the close. A validation email for a WITNESSED + EARNED client does not open with logistics — it opens with acknowledgment. The logistics are the body. The emotional frame is the envelope.

**Traveler type identification:** Cross-reference the six types (Achiever, Curator, Connector, Escapist, Witness, Celebrant). This tells you *how* they receive information — whether to be direct about value (Achiever), lead with the rare angle (Curator), or name the occasion first (Celebrant). Full definitions: `/home/john/Thunderbird/intel/REVERIE_EMOTIONAL_ARCHITECTURE.md`.

**Protagonist rule (from WITNESSED):** "The limestone walls catch the first light as your ship slides into a harbor that hasn't changed in five hundred years. *You have arrived.*" — This sentence positions the client as protagonist. Every destination narrative carries this mirror. The client is not a tourist. They are the person for whom this harbor was waiting.

### 2. The Creative Chain — Separate Passes, No Combining

Client-facing products require six domain passes in sequence. No step is optional. No two steps are combined. The chain is what differentiates D2M from a template factory.

| Step | Owner | What they add |
|------|-------|---------------|
| 1. Experience Layer | Reyes (A8) | Excursions, dining, accessibility, upsell flags — the factual substrate of the experience |
| 2. Narrative | Luna (A6) | Port descriptions, evocative copy, emotional beats — the voice of place |
| 3. Brand Pass | Naia (EXEC) | Tone alignment, D2M brand consistency — the envelope the voice lives in |
| 4. Client Voice | Dani (A3) | Final language, client-specific register — the handshake the client actually receives |
| 5. Quality Gate | TALON + JET | Reader impact + process completion; facts and $$ verification runs HERE, on the finished draft, not before creative work begins |
| 6. WF-17 Hold | Hale (COS) | Routing review, draft to Gmail, Commander review label |

**Hale's role in the chain:** Routing and minutes only. She moves the product from step to step. She does not substitute for any domain expert.

**Anti-combining rule:** Reyes and Luna are not the same pass. A dining recommendation written by Luna without Reyes' input skips the experience-layer fact-check. A Dani draft that hasn't had a Naia brand pass may be warm but off-brand. The quality of each step depends on the one before it arriving intact.

### 3. Structure That Reassures (The HELD Principle)

The information architecture is itself an emotional gesture. The gold standard produces this reader feeling at the end of a validation email: "I can put this down. Everything is handled."

This requires:
- **Front-loaded confidence statement** — first paragraph states that the foundation is solid, before any details appear
- **"Everything else is handled" close on the body** — logistics section ends with explicit release
- **Action boxes that isolate asks** — the dark-background call-to-action block signals visually: everything outside this box is handled; the only thing in your court is inside here
- **Running totals** — show confirmed spend as a sum, so the client is never adding numbers themselves
- **"Your pace this evening" on arrival days** — respect that the first day is theirs; logistics lead, then release

### 4. Voice — Seven Rules

These come directly from the gold-standard build. They are inviolable.

1. **"You booked." Never "we booked."** — Their achievement, their trip.
2. **Honest comparative assessment.** For included excursions, name why it beats the obvious alternative ("quieter than [the famous site], better-preserved, frankly more moving"). Praise that explains is more credible than praise that inflates.
3. **Minimal exclamations.** One, possibly two, in an entire long-form email. Enthusiasm is structural, not punctuational.
4. **Confirmation register, not sales register.** At the validation stage, the client has committed. The copy should feel like a trusted friend who has read the whole file, not a concierge trying to impress them. "The pace is right. The reservations are in."
5. **Parenthetical asides for personality.** Brief, specific, earned. "The Dome Climb is the move." "This one is going to be wonderful." These are the sentences the client rereads.
6. **Detail as signature.** The La Dame dinner on the first night at sea is positioned as *the* moment — not just "specialty dining confirmed." The detail doesn't just inform; it anticipates. The client should feel that someone read the whole file and cared.
7. **Emotional close, then signature.** The last paragraph before the signature is not a recap and not a CTA. It is a human sentence that lands the relationship. "I'll be here for anything that comes up between now and departure." Two sentences maximum.

### 5. Visual System + Fact Discipline

These are the two things that stop a great email from becoming a risk.

**Visual system (D2M standard):**
- Background: cream `#f7f3ea`
- Ink: bright blue `#0000ff` for section headers and highlights
- Banner: navy `#1a2744` (or `#003087` depending on cruise line)
- Accent: gold `#c9b99a` for table borders, rule lines
- Font: Georgia serif throughout
- Named components: banner → body → h2 headers → data tables → action-box (dark bg) → sig → footer
- **CSS pre-processing required:** Run `python3 scripts/gmail_template_stripper.py input.html output.html` before creating the Gmail draft. This inlines all CSS and converts divs to tables for Gmail compatibility.

**Fact discipline (Pipeline Integrity Rules 1, 4, 5 — SO-PIPELINE-INTEGRITY-20260528):**
- **Negative-Space Rule:** If a fact is not confirmed in a primary source, it does not appear. "Likely," "pending," "probably" are banned in client copy.
- **Primary sources (in priority order):** Cruise line portal (verified same session) → TESS booking record → Client dossier
- **Financial Hard-Source Rule:** Dollar amounts, balances, FPDs trace to portal, TESS, or dossier — never to a memo
- **Harlan sign-off required** on any email containing a dollar figure

---

## EMOTIONAL BRIEF (Run Before Every Build)

Before any chain step starts, complete this brief. Hand it to Reyes as the first input.

```
CLIENT: {{CLIENT_NAMES}}
VOYAGE: {{SHIP}} · {{CRUISE_LINE}} · {{ROUTE}} · {{DATES}}
BOOKING REF: {{BOOKING_REF}}

DOMINANT REVERIE PILLAR: [THE RETURN / HELD / WITNESSED / EARNED / THE DREAM THAT HAS A DATE / DEPTH / TOGETHER]
SECONDARY PILLAR: [pick one or "none"]
TRAVELER TYPE: [Achiever / Curator / Connector / Escapist / Witness / Celebrant]
TRAVEL ARCHETYPE: [Expedition / Cultural Immersion / Grand Tour / Return / Sea Journey / Slow Stay]

OCCASION NOTE: [Anniversary? Retirement? Milestone? None?]
SPECIAL MOMENT: [The single most emotionally significant element — e.g., a birthday dinner, first-time port, long-deferred trip]
CLIENT COMMUNICATION STYLE: [Detail-oriented and research-heavy? Delegate-and-trust? Connector (drives decisions for others)?]

OPENING PARAGRAPH REGISTER: [Describe the emotional note the email should open on — one sentence]
```

---

## SECTION SKELETON

This is the generalized structure of a complete validation email. Section order matters; it is itself a message about how the client should receive the information.

### 1. Banner
- D2M name, navy background, cream text
- Tagline: "Luxury Travel · Curated Experiences · Lasting Memories"
- No client name in the banner — banner is brand, not greeting

### 2. Salutation + Opening Paragraph
- Both names, "Dear {{FIRST_NAME_1}} and {{FIRST_NAME_2}}"
- First sentence: confidence statement ("Your foundation is rock-solid." / "Everything that can be confirmed is confirmed.")
- Second sentence: scope statement — what follows covers (flights, hotel, cruise, post-cruise)
- Third sentence: countdown and release — "{{N}} days. Read through at your leisure. Everything else is handled."
- NO emotional opener before the confidence statement in validation emails. Clients under any anxiety about their booking need the reassurance first.

### 3. Flights Section
```
h2: ✈  Flights — Both PNRs Confirmed
Table 1: Outbound — {{ORIGIN}} → {{DESTINATION}} · PNR: {{PNR}}
  Flight / Departure / Arrival / Seats
Table 2: Return — {{DESTINATION}} → {{ORIGIN}} · PNR: {{PNR}}
  Leg 1 / Leg 2 (if connecting)
Follow-up note: connection time + bag transfer policy
```

### 4. Pre-Cruise Stay (if applicable)
```
h2: {{CITY}} — {{DATES}} ({{N}} Nights)
Table: Hotel name · Rate/points note · Location context
Activity table: Date | Experience | Time
Dining section: Table with restaurant name | character + notes | booking urgency
Action box (if dining needs client choice): dark background, bulleted asks
```

### 5. Cruise Section
```
h2: {{SHIP_NAME}} — {{DATES}} ({{N}} Nights)
Booking confirmation table: Reference | Suite | Route | Payment status | Transfers
2-3 prose sentences: Position the ship's all-inclusive or value structure; cabin character; shipboard culture
```

### 6. Complete Itinerary At a Glance
```
h2: Your Complete Itinerary
Table: Date | Port / Location | What's Confirmed
  — One row per day including travel days
  — "Confirmed" column is the discipline: only what is actually locked appears
  — Sea days use "At sea — rest, read, the horizon" or equivalent
```

### 7. Shore Excursions
```
h2: Shore Excursions — All Confirmed ({{N}} Reservations Each)
Table: Date & Port | Excursion Name | Time | Level | Cost
  — Subtotal row in bold at bottom
Follow-up prose: 1-2 sentences per excursion that gave the client a choice or that merits comparative context
  Pattern: "{{EXCURSION}} is {{honest comparative assessment}}. {{One sentence on why this port day works.}}"
```

### 8. Specialty Dining
```
h2: Specialty Dining — All Confirmed ({{N}} Reservations Each)
Table: Date | Restaurant | Seating Times | Character | Cost
  — "Character" column is voice, not brochure copy
  — Subtotal row in bold at bottom
1-2 follow-up sentences: Position the first dinner as tone-setter; name the one premium spend and affirm it
```

### 9. Spend Summary
```
h2: Total Confirmed Onboard Spend
Simple two-column table: Category | Amount
Total row: bold, highlighted background
1-2 sentences: What else is covered and why the onboard account will be light
```

### 10. Post-Cruise Stay (if applicable)
```
h2: {{CITY}} — {{DATES}} ({{N}} Nights)
Table: Hotel | Arrival transfer | First-order suggestion | Location context | Departure logistics
Dining section (if applicable): Table with seafood/preference priority called out if relevant
Action box: Dining reservations that need client choice
```

### 11. Open Items / Action Box
```
Dark-background action box
h3: Open Items — What's In Your Court
Bulleted list: Each item is a specific ask with enough context to act on it immediately
  Pattern: "{{Task}}: {{Why it matters or deadline}}. {{Specific ask.}}"
No open items that are the Wing's responsibility. This box contains ONLY client action items.
```

### 12. Emotional Close
```
2-3 sentences — not a recap, not a CTA
Sentence 1: Land the whole trip as a picture (the arc — city, ship, post-cruise close)
Sentence 2: Affirm the pacing / confirm readiness ("The pace is right. The reservations are in.")
Sentence 3: Availability statement ("I'll be here for anything that comes up.")
```

### 13. Signature Block
- Dani sig block first (avatar 64x64px circular + name + title + D2M + email)
- Commander sig block second, very bottom
- D2M footer: navy background, cream text, address, email
- Full spec: `storage/signatures/dani_sig.html` + `storage/signatures/commander_d2m_sig.html`

---

## VOICE GUIDANCE — FOR EACH CHAIN STEP

### Reyes (A8) — Experience Layer Input

Deliver structured notes, not prose. For each booked experience:
- Item name and status (confirmed / pending / noted)
- Talking point (1-2 lines, factually grounded — WHY this experience at this port)
- The special moment: identify the single highest emotional-weight item (birthday dinner, milestone, long-deferred port) and name it explicitly for Luna

**Reyes never writes prose. Reyes writes the substrate that lets Luna write prose.**

### Luna (A6) — Narrative Pass

Luna writes to the REVERIE pillar identified in the emotional brief. Every destination section has a mirror — the client should see themselves in it, not a generic tourist.

**What Luna writes:**
- Opening paragraph (emotional register set in brief)
- Port sections: each port gets 1 confident sentence of honest comparison, 1 sentence of why this port day works for THIS client, and the sensory detail that makes it real
- Special-moment positioning: the single highest-weight experience gets 2-3 sentences that carry the full emotional weight without over-writing it
- Post-cruise city: "arrival ritual" framing — the first thing they do should be written as the right arrival

**What Luna avoids:**
- Generic superlatives ("breathtaking," "unforgettable," "world-class")
- Future-tense promise ("you will see...") — use present/conditional instead
- Over-writing the special moment — one precise, well-observed sentence outperforms three effusive ones

### Naia (EXEC) — Brand Pass

Check four things, in this order:
1. **Tone:** Is it personal without being casual? Expert without being pedantic? Warm without being effusive?
2. **D2M markers:** Does it sound like John's voice (via Dani's polish)? Does "you" appear far more often than "we"?
3. **Structure:** Does the email flow naturally from confidence statement → details → action → emotional close?
4. **Language flags:** Eliminate "happy to help," "feel free to reach out," "as always," and any phrase that could appear in an Orbitz confirmation. Replace with the specific.

**Brand stationery check:** Cream #f7f3ea, blue #0000ff ink on section headers and highlights, navy banner, gold rule lines, Georgia font. If any section reads as a commodity email in any color scheme, the brand pass has not been applied.

### Dani (A3) — Client Voice (Final Pass)

Dani is the last creative voice. The email that leaves Dani's hands is the email the client reads. No more editing passes after Dani.

**Dani's primary discipline:**
- Clarity: every sentence lands exactly as intended; no ambiguity on confirmations
- Warmth as texture, not structure: warmth is in the parenthetical aside, the precise choice, the honest assessment — not in additional words
- The call to action is implicit in the action box; Dani does not add a separate "please let me know" at the close

### TALON + JET — Quality Gate

**TALON checks:** Does the email feel like it came from someone who read the whole file? Are the special moments positioned with appropriate weight? Is there any wasted space that adds words without adding value?

**JET checks:**
- All financial figures traced to a named primary source
- All booking references verified against dossier
- All "confirmed" items in the itinerary table actually confirmed (not pending, assumed, or hoped)
- No open items left that belong in the Wing's court
- Chain completion checklist complete (all five creative passes documented)

**Kill condition:** JET kills the draft if any figure is untraced. TALON kills the draft if the special moment is buried or absent.

---

## VISUAL DESIGN SYSTEM (COMPACT SPEC)

For the full buildable CSS, see: `/home/john/Thunderbird/output/PHASE2_04_Itinerary_Template_Generator_COMPLETE_20260429_140517.txt`

### Design Token Reference

```
--cream:         #f7f3ea  (body background, email background)
--navy:          #1a2744  (banner, table headers, action box, footer)
--blue:          #0000ff  (section h2 headers, highlighted text, links)
--gold:          #c9b99a  (border accents, rule lines, section labels)
--gold-light:    lighter gold for secondary banner text
--charcoal:      #1a1a1a  (body text)
--muted:         for secondary labels and meta text
Font: Georgia, 'Times New Roman', serif — throughout
```

### Named Components

| Component | Purpose | Key CSS notes |
|-----------|---------|---------------|
| `.banner` | Navy top header with D2M name | cream text, centered, uppercase letter-spacing |
| `.body` | Main content container | 36-40px padding, max-width 680px |
| `h2` | Section headers | Blue #0000ff, bold, gold bottom border |
| `table` | Data grids | Navy header rows, alternating cream/white rows, gold bottom borders |
| `.action-box` | Client asks / CTA | Dark navy background, cream text, gold h3 label — visually separates action from information |
| `.total-row` | Sum rows in tables | Bold, slightly darker cream background, gold top border |
| `.sig` | Signature block | Gold rule above, Georgia, name in blue bold |
| `.footer` | Bottom strip | Navy, cream text, centered |
| `.day-card` (itinerary PDFs) | Day-by-day sections | Gold left border, day number in gold caps — sea days and embark days get variant colors |

### Gmail Compatibility Gate

Run before creating draft:
```bash
python3 /home/john/Thunderbird/scripts/gmail_template_stripper.py input.html output.html
```
This inlines all CSS, strips `<style>` blocks, converts divs to tables. Cream and blue survive Gmail's parser only when preprocessed. Raw CSS in `<style>` tags will be stripped.

Direct draft creation:
```bash
python3 /home/john/Thunderbird/scripts/create_gmail_draft_direct.py --html output.html --to {{CLIENT_EMAIL}} --subject "{{SUBJECT}}"
```

---

## CRUISE-LINE ADAPTATION NOTES

The skeleton above is cruise-line-agnostic. Two adaptations required per cruise line:

**Silversea:**
- All-inclusive framing: "no bill-signing culture on this ship" — open bar, gratuities, specialty dining included except premium restaurants (La Dame = $60/person)
- Positioning note: "butler service" is a Silversea differentiator and can be named in cabin description
- Color accent: Silversea branding leans silver/navy — keep D2M cream/gold system, do not adopt Silversea brand colors

**Regent Seven Seas:**
- All-inclusive framing: "every specialty restaurant, every shore excursion, every glass of wine — included"
- Positioning note: the "all-included" distinction is Regent's central differentiator; name it once in the cruise section
- Color accent: Regent teal (`#006d73`) can be used as a status badge color (green pill for confirmed, teal for paid-in-full) — it reads as cruise-line-aware without overriding D2M brand

**All other lines:**
- Identify what is and is not included; make the included/not-included distinction explicit in the dining and excursions tables
- The "Total Confirmed Onboard Spend" section should reflect any surprises (gratuities not included, specialty dining surcharges)

---

## REPRODUCTION CHECKLIST

This checklist is a gate. All items must be complete before the draft advances to WF-17.

### Creative Chain Completion
- [ ] Emotional brief completed and handed to Reyes as first input
- [ ] Reyes (A8) experience layer notes returned and reviewed
- [ ] Luna (A6) narrative sections written and handed to Naia
- [ ] Naia (EXEC) brand pass complete — tone, D2M markers, structure, language flags resolved
- [ ] Dani (A3) client voice pass complete — this is the final creative touch
- [ ] TALON reader-impact pass complete — special moment positioned, no wasted space
- [ ] JET process completion pass complete — chain documented, all items verified

### Fact Discipline
- [ ] All dollar figures traced to: portal (primary) / TESS / dossier (in that priority order)
- [ ] All booking references verified (not assumed from a prior email or memo)
- [ ] All "confirmed" items in itinerary table verified as actually confirmed
- [ ] Harlan sign-off obtained on any email containing a dollar figure
- [ ] Negative-Space Rule: no "likely," "pending," "probably" in client-facing copy

### PII Verification
- [ ] No client full names (first or last) outside of the salutation and document header
- [ ] No personal email addresses in the body (signature email is acceptable)
- [ ] No booking reference numbers in this template document
- [ ] No PNR numbers in this template document
- [ ] No seat or cabin numbers linked to specific clients in this template document

### Brand Standards
- [ ] Cream #f7f3ea background applied
- [ ] Blue #0000ff section headers applied
- [ ] Navy banner and footer applied
- [ ] Georgia font applied throughout
- [ ] CSS pre-processed through gmail_template_stripper.py
- [ ] Dani signature block present and above Commander signature block
- [ ] Commander signature block at very bottom

### WF-17 Gate
- [ ] Draft pushed to Gmail with label: `THUNDERBIRD-Commander-Review`
- [ ] Commander notified: "{{CLIENT_NAME}} email is ready in your drafts for review and send"
- [ ] No send authority exercised by Wing — Commander sends

---

## QUICK REFERENCE — THE 5 GOLD-STANDARD DISCRIMINATORS

These are the five things that made the Thunderbird's first gold-standard build what it was. They are listed here because future builders will be tempted to skip them under time pressure. Do not skip them.

1. **Emotional architecture first.** The REVERIE pillar is identified before Reyes starts. The opening paragraph is written to a pillar, not to "being warm." The emotional register is the editorial brief, and it governs every word choice in every chain step.

2. **Separate domain passes — no combining.** The reason the voice is distinctive is that four different domain experts touched it with four different intentions. The experience layer is factual. The narrative layer is evocative. The brand pass is disciplined. The client voice pass is personal. Combining any two steps produces a draft that is generically competent and distinctively nothing.

3. **Structure as reassurance.** The email's information architecture — confidence statement first, action box visually isolated, running totals, "everything else is handled" close — is an emotional gesture. A client who trusts D2M after reading the validation email trusts D2M because the email told them, structurally, that they can. Logistics that make the client work harder to find what's confirmed undermine the product regardless of the prose quality.

4. **Voice rules enforced.** "You booked." Honest comparative assessments that name the alternative. Minimal exclamations. Confirmation register, not sales register. The parenthetical aside as personality ("This one is going to be wonderful"). Detail that anticipates, not just informs. These are not stylistic preferences. They are what separates the email that gets read once from the email the client keeps.

5. **Facts first, always.** The quality gate runs on the finished draft, after all creative work. But the fact discipline is present from Reyes' first input forward. No claim without a primary source. Harlan's sign-off on every dollar figure. The email that is beautifully written and factually wrong is worse than no email.

---

*REVERIE Reference Template v1.0 · Dreams2Memories Travel, LLC · Internal use only*
*Cross-references: `/home/john/Thunderbird/intel/REVERIE_EMOTIONAL_ARCHITECTURE.md` · `/home/john/Thunderbird/output/PHASE2_04_Itinerary_Template_Generator_COMPLETE_20260429_140517.txt` · `CLAUDE.md` § Creative Chain*
