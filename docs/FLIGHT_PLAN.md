# FLIGHT PLAN
## Dreams2Memories Travel, LLC — Thunderbird Wing
**Commander:** John "Yoda" Loucks | **COS:** Hale | **Command Chief:** Silver
**Issued:** 2026-06-01 | **Status:** LIVING DOCUMENT

---

## MISSION

*"To use extraordinary capability to deliver exceptional travel experiences — for friends I'd serve for free, and for clients who deserve better than Pavlus but don't know they can have it."*

---

## SECTION I — CORE ATTRIBUTES
*Every item on this board must satisfy all six.*

| # | Attribute |
|---|-----------|
| **A1** | Conforms to the Mission |
| **A2** | Technically Sound |
| **A3** | Predictable |
| **A4** | Responsive |
| **A5** | Standardized |
| **A6** | Functionally Useful |

---

## SECTION II — PRIORITIES

| # | Item | Friction / Problem | Status |
|---|------|--------------------|--------|
| **P1** | Reliability | System froze; no failover | ✅ DONE — Failover chain live |
| **P2** | Speed Diagnosis | "Too unreliable, takes too long" — bottleneck unidentified | 🔴 OPEN — Commander names the bottleneck |
| **P3** | Model Stack Architecture | Sonnet limits out Mon-Wed; MAX untrusted; $200 Grok still producing outages | ✅ IN PROGRESS — Gemini free tier wired; chain: Sonnet → Haiku → Gemini 2.5 Flash |
| **P4** | INBOX FIRST — WF-17 Visibility | 5 docs stuck in drafts; Commander lives in inbox/Telegram not drafts | 🟡 IN PROGRESS 2026-07-04 — root cause found: `gmail_create_draft_sync` was hard-coded to stage in d2mconcierge (frozen MISSION-180 policy), not johnloucks3 where Commander actually reviews. Fixed: defaults to johnloucks3 now, live-tested. Every staged draft now pages Telegram by default (was opt-in) — closes the "found the Spencer draft by chance" gap. Auto-flag/color-change/hyperlink still open. |
| **P5** | Dossier Ingestion Trust | Data given → no confidence it lands right → can't trust validation output | 🔴 OPEN — Prove the chain: data in → dossier updated → returns on demand |
| **P6** | Brief Noise & Depth | Too many AM comms; headlines only; FPD flagged repeatedly (say once, done) | 🟡 IN PROGRESS 2026-07-04 — 12 duplicate/level-triggered-alert sources found and fixed (mission board, staff-tasking, Gmail drafts/inbox, credentials-health, 5 direct-Telegram scripts, 3 fare-quote scripts, decision-log, 1730 nomination). "Say once, done" is now the enforced default across all of them. Brief *depth/curation* (the other half of P6) not yet addressed. |
| **P7** | OpenCode ≠ Claude Code | Same prompt, different answer depending on engine | 🔴 OPEN — Investigate; standardize results across engines |
| **P8** | Lifecycle as Prison | Touchpoints create pressure; air scans/hotel scans make Commander slower | 🔴 OPEN — Audit signal vs. noise; cut what doesn't help real work |
| **P9** | Helps Me Do Real Work | McLeod itinerary, Furlow/Ely/Nichols validations, Spencer DMC/hotels/tours due this week | 🔴 ACTIVE — Real work blocked by limits and process friction |
| **P10** | Standardization Gate | Email/itinerary/proposal templates drifting | 🔴 OPEN — Lock templates; repeatable quality |
| **P11** | 40-Hour Blackout Resilience | Internet died 40+ hours May 9-11; cruise test case | 🟡 DESIGN — Acceptable degradation undefined |
| **P12** | Cruise-Ready State | Pre-departure: queue all touchpoints, lock commitments, minimize real-time decisions | 🟡 OPEN — Checklist needed |
| **P13** | Simple Front Door | Rondo/Bryana/Stefanie will never navigate 19 personas | 🔴 NOT STARTED — UX: smart friend, not command structure |
| **P14** | Norway 2027 (Rondo) | Best friend, widower; 18-month window starts now | 🟡 OPEN — Perx integration; reliable research layer |
| **P15** | Hawaii 2028 (Family) | Multi-gen logistics; AI invisible; 2-year runway | 🟡 OPEN — Coordination plan needed |

---

## COMMAND CHIEF'S NOTE (added 2026-07-04)

This board is the Commander's — every number, every status, his call. What I added isn't a new priority; it's a habit. When a status here says DONE or IN PROGRESS, I go check it against the code, not the claim, before it sits on this page as settled. P4 said "no build needed" for a month. It needed one. I'd rather find that here, on the Commander's own board, than have him find it.

Hale and I don't split this board — she routes what the staff produces onto it; I hold what's already on it to the standard the status word claims. Same page, different job. If a status here ever looks better than what I can verify, that's the finding, and it goes to the Commander plainly, not smoothed over.

*— Silver, Command Chief*

---

*— Hale, COS | Thunderbird Wing | 2026-06-01*
*Edit by number. Commander approves changes.*
