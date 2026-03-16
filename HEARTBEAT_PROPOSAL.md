# THUNDERBIRD HEARTBEAT SYSTEM — Proposal
## COS (Hale) + EXEC (Solberg-Vega) | 10 March 2026

---

## Commander's Intent
Personas anticipate what the Commander needs and deliver it BEFORE he asks. He reviews, edits lightly, and turns it around for clients. Clients see the value instantly. Not everything routes through COS — some go direct.

## Delivery Channels
| Channel | When to Use | How |
|---------|-------------|-----|
| **SMS** | Urgent, time-sensitive, needs action NOW | T-Mobile gateway via Gmail |
| **Gmail Draft** | Action needed today, needs Commander's edit/approval | Create draft + SMS notification "Draft ready: [subject]" |
| **Commander Review** | FYI, background prep, reference material | Gmail label: `THUNDERBIRD-Commander-Review` |
| **Direct to Client** | Pre-approved templates only (portal activations, confirmations) | Draft in Commander Review for one-click send |

---

## 1. COS-EXEC Synced Heartbeat (The Command Pair)

**Cadence:** Every 2 hours, 0600-2000 MT. Joint scan — COS handles ops/scheduling, EXEC handles client-facing/tone.

**What they scan together:**
- Google Calendar: meetings in next 48 hours
- Dossier action items: anything due today or tomorrow
- Gmail inbox: new client/supplier emails since last scan
- Payment deadlines: anything within 14 days

**What "leaning forward" looks like:**

| Trigger | Output | Channel | Example |
|---------|--------|---------|---------|
| Meeting in next 24h | Pre-brief packet | Draft + SMS | "Draft ready: Nichols Pre-Call Brief — Regent Scandinavia status, FPD Apr 1 ($14,986), suite 939, dining opens Apr 15. Talking points included." |
| Client email received | Summary + suggested reply | Draft | "Erik McLeod sent Rome excursion picks. Draft reply acknowledges, confirms GetYourGuide 10% discount, suggests 3 private tour alternatives." |
| Payment due within 7 days | Action reminder with context | SMS | "Kuklinski $21,244 due Mar 31 — 21 days. Need CC from Kyle (804-801-4762) and Josh (818-317-9843). Draft reminder emails ready." |
| Forms/docs overdue | Reminder draft for client | Draft + SMS | "Guest Info Forms due Mar 15 for 6 Kuklinski guests. Portal activation emails still unsent. Drafts ready for your review." |
| Insurance discussion due | Prep packet | Draft | "Draft ready: Kuklinski Travel Protection — comparison of 3 plans, recommendation, talking points for Mar 25 call." |
| Supplier update detected | Impact assessment | Commander Review | "Viking sent fare change alert for Panama Canal Dec 2026. No impact on Kuklinski bookings — locked rate confirmed." |
| No client contact in 10+ days | Follow-up draft | Draft + SMS | "No contact with Furlows since Feb 28 (10 days). Draft check-in email ready — mentions Regent dining opening soon." |

**COS owns:** scheduling, deadlines, task tracking, staff coordination
**EXEC owns:** tone, client draft quality, brand consistency, supplier relationship reads

---

## 2. A3 — Moreau (Booking Operations)

**Cadence:** 0700 daily scan + event-driven (new email triggers)

| Trigger | Output | Channel |
|---------|--------|---------|
| Payment due within 14 days | Payment status + collection script | SMS (7 days) / Draft (14 days) |
| Booking milestone approaching | Checklist of what's needed | Commander Review |
| Guest info forms not submitted | Pre-written reminder to client | Draft |
| Shore excursion window opening | Options summary + recommendations | Draft |
| Dining reservation window opening | Reminder + restaurant guide | Draft |
| Embarkation within 45 days | Pre-trip logistics checklist | Draft |
| New booking confirmation received | Dossier created/updated, summary to Commander | SMS |

**Real example for THIS WEEK:**
- "Kuklinski portal activation — 6 emails drafted, in Commander Review. Kyle gave green light Mar 6."
- "Guest Info Forms due Mar 15 — 5 days. Template reminder emails ready for 6 guests."
- "McLeod Rome/Florence excursions — Erik sent picks Mar 6. Price comparison draft (GetYourGuide vs Silversea vs private) ready."

---

## 3. A9 — Harlan (Finance)

**Cadence:** 0900 daily + weekly summary Monday

| Trigger | Output | Channel |
|---------|--------|---------|
| API spend crosses $5/day any provider | Cost alert | SMS |
| Commission payment expected | Track + remind | Commander Review |
| FPD amount confirmed/changed | Update payment alerts + dossier | Commander Review |
| Monthly spend summary | Breakdown by provider | Draft (1st of month) |
| Client payment received | Confirmation + commission calc | SMS |

**Real example:** "Commission tracker: McLeod Silversea $2,594.54 expected. Regent Scandinavia 3 bookings = ~$4,700 estimated. Viking Panama 3 bookings = ~$1,700 estimated. Total pipeline: ~$9,000."

---

## 4. A2 — Dembe (Research & Intel)

**Cadence:** 0630 daily (with morning intel) + event-driven

| Trigger | Output | Channel |
|---------|--------|---------|
| Client trip within 60 days | Destination brief (weather, advisories, events) | Commander Review |
| Supplier price change detected | Impact analysis on active bookings | SMS if affects client / Commander Review if general |
| Travel advisory change for booked destination | Alert with rebooking options if needed | SMS |
| New cruise itinerary matching client interests | Opportunity brief | Commander Review |
| Competitor intel (new agency offering, market shift) | Quick analysis | Commander Review (weekly) |

**Real example:** "McLeod Mediterranean — 104 days out. Rome weather in June: avg 82°F, low rain. Florence: 2 major exhibitions running. Vatican skip-the-line booking window opens Apr 1. Draft advisory ready."

---

## 5. A6 — Luna (Creative Director)

**Cadence:** Event-driven (triggered by COS-EXEC when client deliverable needed)

| Trigger | Output | Channel |
|---------|--------|---------|
| New proposal requested | Cover image + narrative draft | Draft with images attached |
| Itinerary approaching completion | Destination hero images generated | Commander Review |
| Client birthday/anniversary detected | Personalized card draft | Draft |
| Pre-trip excitement window (30 days out) | "Your Journey Awaits" teaser email | Draft |
| Post-trip follow-up (7 days after return) | Thank you + memory preservation guide | Draft |

**Real example:** "McLeod Silver Muse — 104 days. Generated Rome, Florence, and Venice hero images for itinerary PDF. Pre-trip teaser email drafted for May 23 send (30 days out). In Commander Review."

---

## 6. A12 — ELON (Nova + Innovation)

**Cadence:** Sunday 2000 (Nova audit) + ad-hoc disruption proposals

| Trigger | Output | Channel |
|---------|--------|---------|
| Weekly Nova audit | Tickets + improvement proposals | Commander Review |
| Manual process detected (ELON watching patterns) | Automation proposal | Commander Review |
| New API/tool opportunity | Build vs buy analysis | Commander Review |
| System health anomaly | Fix-it ticket + suggested code | SMS if critical |

**Stays weekly.** ELON's value is depth, not frequency.

---

## 7. A10 — Ikeda (Crisis & Logistics)

**Cadence:** DORMANT until activated. Monitors flight status for booked clients.

| Trigger | Output | Channel |
|---------|--------|---------|
| Flight delay/cancel for booked client | Rebooking options + draft to client | SMS + Draft |
| Weather event at destination within 7 days of client travel | Impact assessment | SMS |
| Supplier system outage (booking portal down) | Workaround + timeline | Commander Review |
| Connection time under 90 min on booked itinerary | Risk alert | Commander Review |

**Real example:** "UA177 DEN→FCO Jun 18 (McLeod) — monitoring. AC817/AC1041 return Jul 6 — 1h55m connection YYZ, within tolerance but monitoring."

---

## 8. CH — Washington (Wisdom & Morale)

**Cadence:** Weekly Friday 1500 + triggered by ethical edge cases

| Trigger | Output | Channel |
|---------|--------|---------|
| Client complaint or negative feedback | Tone check + response guidance | Commander Review |
| Commander working past 2200 more than 3 days/week | Burnout check-in | SMS (gentle) |
| Pricing decision that exceeds 30% markup | Ethics gut-check | Commander Review |
| Client cancellation or booking loss | Morale support + lessons learned | Commander Review |

---

## Implementation Priority

| Phase | What | When |
|-------|------|------|
| **Phase 1** | COS-EXEC synced heartbeat + A3 Moreau | BUILD NOW — highest client impact |
| **Phase 2** | A9 Harlan cost dashboard + A2 Dembe destination briefs | This week |
| **Phase 3** | Luna creative triggers + A10 flight monitoring | Next week |
| **Phase 4** | CH morale sensing + ELON pattern detection | Ongoing refinement |

---

*Prepared by: COS (Hale) + EXEC (Solberg-Vega)*
*For: Commander John "Yoda" Loucks*
*Classification: INTERNAL — Thunderbird Wing Operations*
