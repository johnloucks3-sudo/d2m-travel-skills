# EMAIL CLASSIFICATION ARCHITECTURE
## Dreams2Memories Travel, LLC
### The Predictability System -- From Draft to Auto-Send

**Origin:** Commander directive, 20 March 2026
> "Divide an email into several classes, within that class allocate a certain segment for intro, another for explanation or background, another for options/suggestion and another for close. If we can get the voice and other subjective pieces down, and once we agree upon facts to be transmitted, we can then start down the road of automatic sending."

**Author:** Naia Solberg-Vega, EXEC
**Version:** 1.0
**Status:** FOUNDATIONAL -- requires Commander approval before implementation

---

## Part 1 -- EMAIL CLASSES

Twelve distinct classes. Every outbound email from D2M maps to exactly one.

### C1 -- PROSPECT FIRST CONTACT
The handshake. Someone has expressed interest but has never booked with us.
- **Sender:** John (always -- never Dani for first contact)
- **Trigger:** New inquiry via portal, referral, or Commander directive
- **Risk if wrong:** Permanent. You don't get a second first impression.
- **Template lineage:** T5 (Capability Showcase)

### C2 -- BOOKING CONFIRMATION
The receipt that isn't a receipt. Confirms the commitment, sets expectations, opens the relationship.
- **Sender:** John (initial), Dani (subsequent updates)
- **Trigger:** Booking created in TESS/Booking Master
- **Risk if wrong:** Factual errors destroy trust instantly
- **Template lineage:** Tier 1 correspondence with highlight-box

### C3 -- PAYMENT REMINDER
Money conversation. Must feel personal, not automated. Multi-purpose by nature -- payment + portal + relationship.
- **Sender:** John
- **Trigger:** Anchor date approaching (final payment, deposit)
- **Risk if wrong:** Feels like a collection notice instead of a concierge touch
- **Template lineage:** Tier 1 correspondence with action-box

### C4 -- TRIP UPDATE / LOGISTICS
The operational heartbeat. Itinerary changes, transfer confirmations, flight updates, document requests.
- **Sender:** John or Dani (depending on relationship phase)
- **Trigger:** Booking change, supplier confirmation, schedule update
- **Risk if wrong:** Client shows up at the wrong pier
- **Template lineage:** T3 (Operational), Tier 1 correspondence

### C5 -- EXCURSION / DINING / EXPERIENCE RECOMMENDATION
The reason people hire us. Curated, personal, anticipatory.
- **Sender:** Dani (primary), John (for high-tier clients)
- **Trigger:** Dossier gap analysis, port-of-call approaching, Commander directive
- **Risk if wrong:** Generic recommendations make us look like Expedia
- **Template lineage:** T9 (Proactive Resource), Dani engine

### C6 -- FARE ALERT / PRICE CHANGE
Time-sensitive intelligence. A price dropped, a cabin opened, a promotion launched.
- **Sender:** Dani (draft) with John approval
- **Trigger:** Fare watch system, supplier notification, manual scan
- **Risk if wrong:** Quoting stale prices or wrong cabins
- **Template lineage:** T8 (Forwarded Intel) + structured pricing block

### C7 -- POST-TRIP FOLLOW-UP
The close of the loop. Thank you, how was it, what's next.
- **Sender:** John (always -- this is the relationship seal)
- **Trigger:** Return date + 3-5 days
- **Risk if wrong:** Feels transactional instead of genuine
- **Template lineage:** T4 (Personal) or T7 (Quick Reply) depending on depth

### C8 -- VENDOR COMMUNICATION
Supplier, tour operator, cruise line, hotel. Transactional but professional.
- **Sender:** John (from concierge@ or d2mconcierge@)
- **Trigger:** Booking action, information request, issue resolution
- **Risk if wrong:** We look amateur to people who decide our access and rates
- **Template lineage:** T3 (Operational)

### C9 -- CLIENT BULLETIN
One-to-many. Newsletter-adjacent but personal. New capability, seasonal inspiration, portfolio update.
- **Sender:** John (branded HTML)
- **Trigger:** Scheduled cadence or Commander directive
- **Risk if wrong:** Feels like spam. Instant unsubscribe energy.
- **Template lineage:** `client_bulletin.html.j2`

### C10 -- RESPONSE TO CLIENT QUESTION
Reactive. Client asked something specific. Answer it, don't oversell.
- **Sender:** Dani (primary, with COS review) or John
- **Trigger:** Inbound client email parsed by Dani email sweep
- **Risk if wrong:** Wrong answer or wrong tone for the question's weight
- **Template lineage:** T7 (Quick Reply), T3 (Operational), or Dani freestyle

### C11 -- PROACTIVE OUTREACH (Milestone / Seasonal / Relationship)
Birthday. Anniversary. "I saw this and thought of you." The emails that make people tell their friends about us.
- **Sender:** John (always for milestones), Dani (for seasonal/inspirational)
- **Trigger:** Dossier milestone dates, seasonal calendar, Commander intuition
- **Risk if wrong:** Getting the date wrong is worse than not sending at all
- **Template lineage:** T4 (Personal), T9 (Proactive Resource)

### C12 -- INTERNAL STAFF COMMUNICATION
Commander to staff, staff to Commander. Never client-facing, but governs everything that is.
- **Sender:** John or staff persona
- **Trigger:** Operational need
- **Risk if wrong:** Misunderstood directive cascades into client-facing error
- **Template lineage:** Staff Paper format (ISSUE/DISCUSSION/OPTIONS/ACTIONS)

---

## Part 2 -- SEGMENT STRUCTURE

Every email, regardless of class, is built from four ordered segments. The content and weight of each segment varies by class.

### Segment Definitions

| Segment | Code | Purpose |
|---------|------|---------|
| **INTRO** | `S1` | Opening line. Sets tone, establishes relationship, signals what's coming. |
| **CONTEXT** | `S2` | Background. What the recipient needs to know to understand the body. Facts that frame the message. |
| **BODY** | `S3` | The substance. Recommendations, options, information, answers. The reason the email exists. |
| **CLOSE** | `S4` | Call to action, next steps, sign-off. Leaves the recipient knowing exactly what happens next. |

---

### C1 -- PROSPECT FIRST CONTACT

| Segment | Content | Length | Tone |
|---------|---------|--------|------|
| **S1 -- INTRO** | Personal greeting. Reference how we connected. One warm sentence that says "I see you as a person, not a lead." | 1-2 sentences | Warm, unhurried, confident |
| **S2 -- CONTEXT** | Brief personal story or observation. Why D2M exists. What makes us different -- but shown, not told. | 2-3 sentences | Visionary but grounded |
| **S3 -- BODY** | What we can do for them specifically. One concrete example tied to something we know about them. Introduce Dani if appropriate. Attach proof (hotel guide, showcase). | 3-5 sentences + attachment | Confident, never pushy |
| **S4 -- CLOSE** | Soft CTA. "No pitch. No obligation." Offer conversation, not a sale. Full branded signature. | 2-3 sentences | Open door, no pressure |

### C2 -- BOOKING CONFIRMATION

| Segment | Content | Length | Tone |
|---------|---------|--------|------|
| **S1 -- INTRO** | Congratulations or acknowledgment. Match the excitement level of the trip. | 1 sentence | Warm, celebratory |
| **S2 -- CONTEXT** | Highlight box: booking reference, travel dates, ship/hotel, cabin/room category. Hard facts only. | Structured block | Precise, scannable |
| **S3 -- BODY** | What happens next: guest profile form, document requirements, payment schedule, portal access. | 3-5 sentences + action box | Clear, organized |
| **S4 -- CLOSE** | Personal availability. "I'm here if anything comes up." Sign-off. | 1-2 sentences | Reassuring |

### C3 -- PAYMENT REMINDER

| Segment | Content | Length | Tone |
|---------|---------|--------|------|
| **S1 -- INTRO** | Warm greeting. Personal reference (how's the family, excited about the trip). Never open with "your payment is due." | 1-2 sentences | Personal first |
| **S2 -- CONTEXT** | Trip context: where they're going, when, what they're looking forward to. Reconnect them to the dream before the invoice. | 2-3 sentences | Anticipatory |
| **S3 -- BODY** | Payment details: amount, due date, method, portal link. Action box format. If multi-purpose, include portal instructions, document status. | Structured block + 2-3 sentences | Matter-of-fact, helpful |
| **S4 -- CLOSE** | "Let me know if you have any questions." Personal sign-off. | 1-2 sentences | Steady, available |

### C4 -- TRIP UPDATE / LOGISTICS

| Segment | Content | Length | Tone |
|---------|---------|--------|------|
| **S1 -- INTRO** | Quick greeting. Acknowledge the thread or context. | 1 sentence | Efficient, warm |
| **S2 -- CONTEXT** | What changed and why. One sentence. Don't over-explain operational details. | 1-2 sentences | Direct |
| **S3 -- BODY** | Updated details. Structured if multiple items (bullets or highlight box). If itinerary change, show before/after. | 2-5 sentences or structured block | Clear, scannable |
| **S4 -- CLOSE** | Confirm what's handled vs. what needs their input. Sign-off. | 1-2 sentences | Decisive |

### C5 -- EXCURSION / DINING / EXPERIENCE RECOMMENDATION

| Segment | Content | Length | Tone |
|---------|---------|--------|------|
| **S1 -- INTRO** | Personal greeting. Reference the specific port, destination, or interest that triggered this. | 1-2 sentences | Anticipatory, warm |
| **S2 -- CONTEXT** | Why this matters to them specifically. Tie to dossier data: past preferences, dietary needs, mobility, family composition. | 2-3 sentences | Knowledgeable, personal |
| **S3 -- BODY** | Structured recommendation blocks. Primary option + 1-2 alternatives. Each with: name, link, logistics, pricing range, why it fits them. Use T9 structured format with emoji markers. | Structured blocks | Expert, curated |
| **S4 -- CLOSE** | "For your awareness -- no action needed right now." Low-pressure CTA. Offer to book or research further. | 2-3 sentences | No pressure |

### C6 -- FARE ALERT / PRICE CHANGE

| Segment | Content | Length | Tone |
|---------|---------|--------|------|
| **S1 -- INTRO** | Quick greeting. Signal: "I found something worth your attention." | 1 sentence | Alert but not alarming |
| **S2 -- CONTEXT** | What they're currently booked/interested in. Baseline price or status. | 1-2 sentences | Factual |
| **S3 -- BODY** | The change: new price, availability, promotion details. Clear comparison (was/now). Time sensitivity if applicable. | 2-4 sentences or structured block | Precise, time-aware |
| **S4 -- CLOSE** | "Want me to lock this in?" or "Let me know if you'd like to explore this." Clear decision point. | 1-2 sentences | Action-ready |

### C7 -- POST-TRIP FOLLOW-UP

| Segment | Content | Length | Tone |
|---------|---------|--------|------|
| **S1 -- INTRO** | Welcome home. Reference a specific moment from their trip if known. | 1-2 sentences | Warm, genuine |
| **S2 -- CONTEXT** | Light reflection on the trip. Not a survey -- a human check-in. | 1-2 sentences | Conversational |
| **S3 -- BODY** | Optional: "If anything stood out -- good or bad -- I'd love to hear about it." Plant the seed for the next trip without selling. Mention referral only if natural. | 2-3 sentences | Unhurried |
| **S4 -- CLOSE** | "Looking forward to the next one." Personal sign-off. | 1 sentence | Forward-looking |

### C8 -- VENDOR COMMUNICATION

| Segment | Content | Length | Tone |
|---------|---------|--------|------|
| **S1 -- INTRO** | Professional greeting. Context: booking reference, client name (if appropriate). | 1 sentence | Professional |
| **S2 -- CONTEXT** | The situation. What we need and why. | 1-3 sentences | Direct, factual |
| **S3 -- BODY** | The request or information. Specific, actionable, no ambiguity. Bullet points if multiple items. | 2-5 sentences or bullets | Transactional, clear |
| **S4 -- CLOSE** | "Thanks for sending" or "Please confirm." Timeline if applicable. | 1 sentence | Efficient |

### C9 -- CLIENT BULLETIN

| Segment | Content | Length | Tone |
|---------|---------|--------|------|
| **S1 -- INTRO** | Branded header. Personal greeting from John. Hook: something worth reading. | 2-3 sentences | Inviting, not salesy |
| **S2 -- CONTEXT** | Why now. Seasonal tie-in, new capability, industry development. | 2-3 sentences | Informed, relevant |
| **S3 -- BODY** | The content. Could be: new destinations, partner spotlight, capability showcase, travel intel. Visual-heavy. | Variable -- medium to long | Inspiring, visual |
| **S4 -- CLOSE** | Soft CTA. "If any of this sparks an idea, let's talk." Full branded signature. | 1-2 sentences | Open door |

### C10 -- RESPONSE TO CLIENT QUESTION

| Segment | Content | Length | Tone |
|---------|---------|--------|------|
| **S1 -- INTRO** | Mirror their energy. If they asked a quick question, quick greeting. If they're worried, acknowledge it. | 1 sentence | Matched |
| **S2 -- CONTEXT** | Restate or acknowledge what they asked. Proves you read it. | 1 sentence (often implicit) | Confirming |
| **S3 -- BODY** | The answer. Direct. If multiple parts, number them. If uncertain, say so and say when you'll know. | 1-5 sentences | Direct, certain |
| **S4 -- CLOSE** | "Let me know if that covers it" or "I'll follow up with [X] by [when]." | 1 sentence | Decisive |

### C11 -- PROACTIVE OUTREACH (Milestone / Seasonal)

| Segment | Content | Length | Tone |
|---------|---------|--------|------|
| **S1 -- INTRO** | The occasion. "Happy birthday," "I was thinking about your trip last year," "Spring always makes me think of..." | 1-2 sentences | Genuine, personal |
| **S2 -- CONTEXT** | The personal connection. What we know about them that makes this relevant. | 1-2 sentences | Intimate (in the right way) |
| **S3 -- BODY** | Optional: a gift (discount, early access, curated suggestion). Or just the human touch -- no ask at all. | 0-3 sentences | Generous |
| **S4 -- CLOSE** | Light. No CTA required. "Hope you have a wonderful day." | 1 sentence | Warm |

### C12 -- INTERNAL STAFF COMMUNICATION

| Segment | Content | Length | Tone |
|---------|---------|--------|------|
| **S1 -- ISSUE** | One sentence. What this is about. | 1 sentence | Direct |
| **S2 -- DISCUSSION** | Context, analysis, cross-references. What matters and why. | Variable | Substantive |
| **S3 -- OPTIONS** | Numbered alternatives when applicable. | Numbered list | Clear |
| **S4 -- ACTIONS** | Numbered recommendations. What to do next. | Numbered list | Decisive |

---

## Part 3 -- VOICE RULES PER CLASS

Voice rules pull from the Voice Ledger (`voice_ledger.json`) and overlay class-specific constraints.

### Voice Parameter Matrix

| Class | Formality (1-5) | Personal Ref Required | Sign-off Variant | Emoji Policy | Length Target |
|-------|------------------|-----------------------|-------------------|--------------|---------------|
| **C1** Prospect First Contact | 3 | Yes -- reference how connected | "Looking forward to this one" or "Thanks" | Never | Long (400-600 words) |
| **C2** Booking Confirmation | 3 | Yes -- trip excitement | "Thank you" | Never | Medium (200-400 words) |
| **C3** Payment Reminder | 2 | Yes -- family, trip anticipation | "Thanks" | Never | Medium-Long (300-500 words) |
| **C4** Trip Update | 2 | Optional | "Thanks" | Never | Short-Medium (100-300 words) |
| **C5** Excursion/Dining Rec | 2 | Yes -- preferences, past trips | "Looking forward to connecting" (Dani) | Structured markers only | Medium-Long (300-600 words) |
| **C6** Fare Alert | 2 | Optional | "Thanks" | Never | Short (100-200 words) |
| **C7** Post-Trip Follow-up | 1 | Yes -- specific trip moments | "Looking forward to the next one" | Never | Short-Medium (150-300 words) |
| **C8** Vendor Communication | 3 | No | "Thanks" | Never | Short (50-200 words) |
| **C9** Client Bulletin | 3 | No (one-to-many) | "Thanks" with full sig | Branded markers in body OK | Long (500-800 words) |
| **C10** Response to Question | 1-2 | Match their energy | "Thanks" | Never | Short (50-200 words) |
| **C11** Proactive Outreach | 1 | Yes -- always | Varies by occasion | Never for prospects, light for friends | Short (50-200 words) |
| **C12** Internal Staff | 4 | N/A | Staff Paper signature line | N/A | Variable |

### Formality Scale
- **1** = Friends at dinner. First names, contractions, ellipsis, humor.
- **2** = Professional-casual. Warm, direct, personal. This is John's natural register for clients.
- **3** = Professional. Still warm, but structured. Proposals, first contacts, bulletins.
- **4** = Formal operational. Staff papers, vendor disputes, legal-adjacent.
- **5** = Reserved. Never used by D2M. If we're at 5, something went wrong.

### Voice Ledger Integration
Every class pulls rules in this order (most specific wins):

```
GLOBAL rules (voice_ledger.json → global_rules)
  ↓ overridden by
TIER rules (voice_ledger.json → tier_rules[paying|friend|prospect|vendor|staff])
  ↓ overridden by
CLIENT rules (voice_ledger.json → client_rules[client_name])
  ↓ overridden by
CLASS constraints (this document → Part 3 matrix)
```

### Standing Voice Rules (All Classes)
These are non-negotiable across every class:

1. **Sign-off:** "Thanks" or "Thank you" -- NEVER "Best," "Best regards," "Warm regards," "Sincerely"
2. **Ink:** Bright blue (#0000ff) on cream paper (#f7f3ea) -- baked into stationery, never overridden
3. **Confidence vs. arrogance:** Suggest, don't prescribe. "I'd recommend..." not "You should..."
4. **No upsell in routine replies.** Answer the question, close. (Global anti-pattern rule)
5. **Four sentences max for routine replies** -- unless the letter does several things (multi-purpose earns its length)
6. **Personal phone (719-291-0742):** Given selectively. Include in signature for paying clients and close friends. Never in prospect first contact until relationship is established.
7. **Military DNA shows but never leads.** "Dialed in," "ramping up" are natural. "Roger," "SITREP," "copy" are never client-facing.
8. **Never quote specific prices in casual emails.** Pricing flows through the pricing chain (WF15).

---

## Part 4 -- FACT SOURCES PER SEGMENT

Every fact in every segment must trace back to a verified source. No hallucinated details, no assumed dates, no invented preferences.

### Source Registry

| Source Code | System | Description |
|-------------|--------|-------------|
| `DOSSIER` | `~/Thunderbird/dossiers/{client}.md` | Client relationship file. Preferences, history, family, notes. |
| `BOOKING` | Google Sheets Booking Master | Active bookings: dates, payments, cabin, status, supplier refs. |
| `TESS` | TESS CRM (via API) | Official booking records, commission data, client profiles. |
| `VOICE` | `voice_ledger.json` | Voice rules by tier, client, domain. |
| `ANCHOR` | Anchor dates system | Deadlines, milestones, payment due dates. |
| `GMAIL` | Gmail (d2mconcierge@) | Thread history, prior correspondence, supplier confirmations. |
| `TEMPORAL` | Session memory / dossier scanner | Recent interactions, conversation context, time-sensitive notes. |
| `ENRICH` | Auto-enrichment (weather, port intel, flight data) | Real-time data pulled at draft time. |
| `MANUAL` | Commander input | Facts provided directly by John in the drafting conversation. |

### Source-to-Segment Mapping

| | S1 INTRO | S2 CONTEXT | S3 BODY | S4 CLOSE |
|---|----------|------------|---------|----------|
| **C1** Prospect | MANUAL, DOSSIER (if exists) | MANUAL | MANUAL, ENRICH | VOICE |
| **C2** Booking Confirm | DOSSIER | BOOKING, TESS | BOOKING, ANCHOR | VOICE |
| **C3** Payment Reminder | DOSSIER, TEMPORAL | BOOKING, DOSSIER | BOOKING, ANCHOR, TESS | VOICE |
| **C4** Trip Update | TEMPORAL, GMAIL | BOOKING, GMAIL | BOOKING, ENRICH, GMAIL | VOICE |
| **C5** Excursion/Dining | DOSSIER | DOSSIER, BOOKING | ENRICH, DOSSIER | VOICE |
| **C6** Fare Alert | DOSSIER | BOOKING, TESS | ENRICH (fare watch) | VOICE |
| **C7** Post-Trip | DOSSIER, TEMPORAL | DOSSIER | DOSSIER, TEMPORAL | VOICE |
| **C8** Vendor | BOOKING | BOOKING, GMAIL | BOOKING, MANUAL | VOICE |
| **C9** Bulletin | MANUAL | MANUAL, ENRICH | MANUAL, ENRICH | VOICE |
| **C10** Response | GMAIL (inbound), DOSSIER | GMAIL (inbound) | ALL (depends on question) | VOICE |
| **C11** Proactive | DOSSIER (milestone) | DOSSIER | ENRICH, MANUAL | VOICE |
| **C12** Internal | N/A | ALL | ALL | N/A |

### Fact Verification Rules

1. **Dates:** Must come from BOOKING or ANCHOR. Never from memory, never from "I think it was..."
2. **Prices:** Must come from BOOKING or TESS. Never approximated in client-facing email. Ranges OK in C5/C6 with explicit "approximately" qualifier.
3. **Names:** Must come from DOSSIER. Spelling verified. Family member names verified. Pet names verified.
4. **Flight numbers:** Must come from BOOKING or GMAIL (supplier confirmation). Never generated.
5. **Preferences:** Must come from DOSSIER or GMAIL (stated by client). Never assumed.
6. **If a fact cannot be verified:** Draft must flag it as `[VERIFY: {fact}]` for COS/Commander review. Auto-send is blocked on any unverified fact tag.

---

## Part 5 -- PREDICTABILITY SCORING

Three independent scores. Each measures a different dimension of draft quality. Combined, they tell us whether a draft is safe to send.

### 5.1 -- Structure Score (0-100)

**Question:** Did the draft follow the segment template for its class?

| Check | Points | Method |
|-------|--------|--------|
| Correct class identified | 15 | Classification engine assigns class; reviewer confirms |
| S1 (INTRO) present and within length target | 15 | Sentence count vs. class spec |
| S2 (CONTEXT) present and sources verified | 20 | Source tags present, all sources in registry |
| S3 (BODY) present and structured per class | 30 | Format match (bullets, structured blocks, prose) per class spec |
| S4 (CLOSE) present with appropriate sign-off | 10 | Sign-off matches VOICE rules |
| Segment order correct (S1 → S2 → S3 → S4) | 10 | Structural validation |

**Threshold:** 80+ = passes structural review

### 5.2 -- Voice Score (0-100)

**Question:** Does it sound like John wrote it?

| Check | Points | Method |
|-------|--------|--------|
| Formality level matches class spec | 15 | NLP formality classifier vs. target range |
| Sign-off correct | 10 | Exact match against approved variants |
| No anti-patterns present | 15 | Check against VOICE global anti-patterns (upsell, filler, "Best", corporate jargon) |
| Personal reference included (when required) | 10 | Dossier cross-check for personal details |
| Length within target range | 10 | Word count vs. class spec |
| Tone mirrors Commander voice principles | 20 | Embedding similarity to Commander's sent emails corpus |
| Confidence/arrogance line respected | 10 | "I'd recommend" vs. "You should" pattern check |
| Tier-specific rules applied | 10 | Voice ledger tier rules present in output |

**Threshold:** 85+ = passes voice review

### 5.3 -- Fact Score (0-100)

**Question:** Are all stated facts verified against source systems?

| Check | Points | Method |
|-------|--------|--------|
| All dates verified against BOOKING/ANCHOR | 20 | Exact match |
| All prices verified against BOOKING/TESS | 20 | Exact match (or within rounding) |
| All names spelled correctly (client, family, ship, hotel) | 20 | DOSSIER cross-check |
| All references/booking numbers valid | 15 | TESS/BOOKING lookup |
| No `[VERIFY]` tags remaining | 15 | Tag scan |
| No hallucinated details | 10 | Source attribution exists for every factual claim |

**Threshold:** 95+ = passes fact review (facts are binary -- nearly right is wrong)

### 5.4 -- Composite Score

```
Composite = (Structure * 0.25) + (Voice * 0.35) + (Fact * 0.40)
```

Fact accuracy is weighted heaviest because a wrong fact in the right voice is worse than a right fact in the wrong voice. Voice is weighted above structure because clients feel tone before they see format.

| Composite Range | Disposition |
|-----------------|-------------|
| 90-100 | Auto-send eligible (Phase 3+ classes only) |
| 80-89 | COS spot-check (flag for review, high confidence) |
| 70-79 | COS full review required |
| Below 70 | Commander review required -- draft needs rework |

---

## Part 6 -- ROAD TO AUTO-SEND

Four phases. Each unlocks the next. No skipping.

### Phase 1 -- STRUCTURAL COMPLIANCE
**Gate:** Every draft follows the segment structure for its class.
**Review:** COS reviews every outbound draft.
**Measurement:** Structure Score consistently 80+ across all classes.
**Duration:** 2-4 weeks of production traffic.
**What we learn:** Are the 12 classes correct? Are the segment templates right? Do we need a C13?

**Exit criteria:**
- [ ] 50+ drafts scored, all classes represented
- [ ] Structure Score average 85+
- [ ] No class misidentification in last 20 drafts
- [ ] Commander approves class definitions as complete

### Phase 2 -- VOICE CALIBRATION
**Gate:** Voice scoring passes 90% consistently.
**Review:** COS spot-checks (reviews 1 in 3 drafts, random selection).
**Measurement:** Voice Score consistently 85+ across all classes.
**Duration:** 4-8 weeks.
**What we learn:** Where does the voice still drift? Which classes are hardest to nail? Which clients require the most deviation from templates?

**Exit criteria:**
- [ ] Voice Score average 88+ across last 50 drafts
- [ ] Commander edit rate below 15% (85%+ of drafts sent without changes)
- [ ] Voice ledger has 50+ rules with applied_count > 0
- [ ] Per-client voice rules exist for top 10 clients
- [ ] Learning compiler captures every Commander edit and extracts principle

### Phase 3 -- FACT VERIFICATION AUTOMATION
**Gate:** Fact accuracy verified automatically against source systems.
**Review:** Auto-send enabled for routine classes (C4, C6, C8, C10 quick replies).
**Measurement:** Fact Score consistently 95+ across all classes.
**Duration:** 4-8 weeks.
**What we learn:** Which fact sources are unreliable? Where do systems disagree? What facts can't be auto-verified?

**Auto-send eligible classes (Phase 3):**
- C4 -- Trip Update (routine logistics only, not itinerary rewrites)
- C6 -- Fare Alert (verified against fare watch data)
- C8 -- Vendor Communication (standard operational requests)
- C10 -- Response to Client Question (short replies, high-confidence answers)

**Exit criteria:**
- [ ] Fact Score 97+ across last 50 auto-eligible drafts
- [ ] Zero factual errors in auto-sent emails over 4-week period
- [ ] Source verification pipeline covers all fact types
- [ ] Rollback mechanism tested: auto-sent email can be retracted within 60 seconds

### Phase 4 -- FULL AUTONOMY (ROUTINE CLASSES)
**Gate:** Only prospects and first contacts require Commander/COS review.
**Review:** COS reviews C1, C2, C3, C7, C9, C11 only. Everything else auto-sends if composite 90+.
**Measurement:** All three scores passing thresholds, composite 90+.
**Duration:** Ongoing.

**Always require human review (never auto-send):**
- C1 -- Prospect First Contact (permanent -- first impressions are irreversible)
- C2 -- Booking Confirmation (too many facts, too much at stake)
- C3 -- Payment Reminder (money conversations need human judgment)
- C7 -- Post-Trip Follow-up (relationship depth requires human touch)
- C9 -- Client Bulletin (one-to-many amplifies any error)

**Auto-send eligible with composite 90+:**
- C4 -- Trip Update / Logistics
- C5 -- Excursion/Dining Recommendation
- C6 -- Fare Alert
- C8 -- Vendor Communication
- C10 -- Response to Client Question
- C11 -- Proactive Outreach (milestones only, not seasonal campaigns)

**Never auto-send under any circumstances:**
- C12 -- Internal Staff Communication (goes to Commander, not from Commander)
- Any email with a `[VERIFY]` tag
- Any email to a new recipient not in DOSSIER
- Any email containing a price quote (pricing chain is sacred)

---

## Part 7 -- IMPLEMENTATION MAP

How this architecture connects to existing Thunderbird systems.

### Classification Engine
**Where it lives:** New module -- `thunderbird_email_classifier.py`
**Input:** Outbound email context (recipient, trigger, thread history, dossier data)
**Output:** Class assignment (C1-C12) + segment template + voice parameters + source requirements

### Draft Assembly Pipeline
```
Trigger (inbound email / anchor date / Commander directive / scheduled)
  ↓
Classification Engine → assigns class
  ↓
Dani Engine Phase 1 (AGGREGATE) → gathers facts per source map
  ↓
Dani Engine Phase 2 (ARTIST) → assembles segments per class template, applies voice rules
  ↓
Predictability Scorer → generates Structure + Voice + Fact scores
  ↓
Dani Engine Phase 3 (ADVOCATE) → routes based on composite score:
  - 90+ and auto-eligible class → auto-send (Phase 3+)
  - 80-89 → COS spot-check queue
  - Below 80 → Commander review via Telegram /drafts
```

### Voice Ledger Feedback Loop
```
Commander edits a draft
  ↓
Learning Compiler captures the diff (Skill 1: Capture the Diff)
  ↓
Extracts the principle (Skill 2: Extract the Principle)
  ↓
Writes rule to voice_ledger.json with class + tier + client tags
  ↓
Next draft of same class/tier/client reflects the correction (Skill 3: Apply Forward)
  ↓
Voice Score improves over time
```

### Scoring Database
**Where it lives:** `~/Thunderbird/email_scores.json` (append-only log)
**Fields per scored draft:**
```json
{
  "timestamp": "2026-03-20T14:30:00Z",
  "class": "C4",
  "recipient": "missy.furlow@example.com",
  "tier": "paying",
  "structure_score": 92,
  "voice_score": 87,
  "fact_score": 98,
  "composite": 92.05,
  "disposition": "auto_send",
  "commander_edited": false,
  "edit_delta": null
}
```

---

## Part 8 -- CLASS QUICK REFERENCE CARD

For COS and Dani. Laminated-desk-card energy.

```
CLASS    SENDER   REVIEW        FORMALITY  LENGTH       SIGN-OFF
------   ------   -----------   ---------  -----------  -------------------
C1  PFC  John     Always Cmdr   3          Long         Looking forward
C2  BCN  John     Always COS    3          Medium       Thank you
C3  PAY  John     Always COS    2          Med-Long     Thanks
C4  UPD  J/Dani   Auto P3+      2          Short-Med    Thanks
C5  REC  Dani     Auto P4       2          Med-Long     Looking forward (D)
C6  FAR  Dani     Auto P3+      2          Short        Thanks
C7  PTF  John     Always Cmdr   1          Short-Med    Next one
C8  VND  John     Auto P3+      3          Short        Thanks
C9  BUL  John     Always COS    3          Long         Thanks + sig
C10 RSP  J/Dani   Auto P3+      1-2        Short        Thanks
C11 PRO  J/Dani   Auto P4       1          Short        Varies
C12 INT  Staff    N/A           4          Variable     Staff Paper
```

---

## Appendix A -- Relationship to Existing Templates

| Template | Maps to Class(es) | Status |
|----------|-------------------|--------|
| T1 Guest Profile Request | C4 (subtype: document request) | Active |
| T2 Problem Acknowledgment | C10 (subtype: error response) | Active |
| T3 Vendor/Booking Operational | C4, C8 | Active |
| T4 Social/Personal Invitation | C11 | Active |
| T5 Capability Showcase | C1, C9 | Active |
| T6 Dani Introduction | C1 (Dani follow-up phase) | Active |
| T7 Quick Reply | C10 (short form) | Active |
| T8 Forwarded Intel | C6 (with forward), C4 | Active |
| T9 Proactive Resource | C5, C11 | Active |
| Tier 1 Correspondence | C2, C3, C4 (formal variants) | Active |
| Staff Paper | C12 | Active |

Templates are NOT deprecated by this system. They become the default segment content for their mapped classes. The classification architecture wraps them in structure, scoring, and routing -- it does not replace the prose.

---

## Appendix B -- Anti-Patterns (Auto-Fail)

Any draft containing these patterns scores 0 on the relevant dimension and is blocked from auto-send:

### Voice Anti-Patterns (Voice Score = 0)
- Sign-off contains "Best," "Best regards," "Warm regards," "Sincerely," "Cheers"
- Opens with "I hope this email finds you well" (the sentence that means nothing)
- Contains "per my last email" or "as previously mentioned"
- Uses "Dear Sir/Madam" or "To Whom It May Concern"
- Sounds like a form letter (no personal reference, no dossier data, interchangeable recipient)

### Fact Anti-Patterns (Fact Score = 0)
- Contains a date not traceable to BOOKING or ANCHOR
- Contains a price not traceable to BOOKING or TESS
- Misspells client name, family member name, ship name, or destination
- References a booking that doesn't exist in the system
- States "your flight" or "your hotel" without a verified booking reference

### Structural Anti-Patterns (Structure Score = 0)
- Missing S1 (INTRO) entirely -- email starts with facts, no greeting
- Missing S4 (CLOSE) -- email ends mid-thought with no sign-off
- Segments out of order (facts before greeting, sign-off before substance)
- Class mismatch (classified as C10 but reads like a C5; classified as C8 but addressed to a client)

---

*This document is the foundation. It grows with every draft scored, every Commander edit captured, and every voice rule extracted. The goal is not to replace John's judgment -- it is to make the system so predictable that his judgment is needed less often for routine communications, freeing him to focus on the relationships and decisions that only he can make.*

*-- Naia Solberg-Vega, EXEC, Dreams2Memories Travel, LLC*
