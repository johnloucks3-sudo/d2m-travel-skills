# n8n Workflow Research — D2M Lifecycle Automation
*Pass 2 Wide Search — 2026-06-04 | Commander: Yoda | Overseer: Hale*
*8 search agents | ~6,000+ unique workflows examined*

---

## TIER 1 — Download & Adapt Immediately (confirmed direct fit)

| ID | Workflow | URL | D2M Initiative | Effort to Adapt |
|----|---------|-----|----------------|-----------------|
| **6082** | Human in the Loop Email Response System (AI + IMAP) | https://n8n.io/workflows/6082 | WF-17 gate — AI drafts, human approves, sends | 1-2h |
| **15973** | Send AI-written invoice emails and payment reminders with Google Sheets, Gmail, Telegram and Groq | https://n8n.io/workflows/15973 | ARC 4 payment reminders — exact stack (Sheets+Gmail+Telegram) | 2h |
| **5506** | Auto-Stop Email Sequences Based on Replies with IMAP and Google Sheets | https://n8n.io/workflows/5506 | Initiative #6 reply parser — stop→flag for Hale review | 2h |
| **16065** | Draft AI follow-up email drafts for stale estimates with Claude and Google Sheets | https://n8n.io/workflows/16065 | Stale-TP detection → Claude draft creation | 2h |
| **14802** | Send personalized birthday and anniversary emails with Google Sheets, Gemini, and Gmail | https://n8n.io/workflows/14802 | TP 21 anniversary touchpoint (12 months post-voyage) | 1h |
| **15428** | Create client onboarding packets with GPT-4.1-mini and Gmail drafts | https://n8n.io/workflows/15428 | ARC 0 guest intake → Gmail draft | 2h |
| **9846** | Travel Itinerary Reminders with Google Calendar, Excel, and SMS/Email Alerts | https://n8n.io/workflows/9846 | Travel-specific reminder sequences | 2h |

## TIER 1 (from Pass 1 — confirmed)

| ID | Workflow | URL | D2M Use |
|----|---------|-----|---------|
| **15204** | Draft and approve client portfolio emails (Gemini+Sheets+Slack+Gmail) | https://n8n.io/workflows/15204 | WF-17 approval gate in n8n — swap Gemini→Claude, Slack→Telegram, send→draft-only |
| **3767** | Update HubSpot engagement by parsing inbox mail with AI | https://n8n.io/workflows/3767 | Initiative #6 reply parser — flag-not-write version |
| **14155** | Send contract renewal reminders 30/60/90 day | https://n8n.io/workflows/14155 | ARC 4 payment reminder pattern |
| **14852** | Triage Gmail inbox, draft replies, alert urgent emails with Claude and Slack | https://n8n.io/workflows/14852 | Claude + Gmail draft + triage, swap Slack→Telegram |

---

## TIER 2 — Strong pattern match, more adaptation

| ID | Workflow | URL | D2M Application |
|----|---------|-----|----------------|
| **8330** | Automate Client Nurture & Testimonial Collection with Notion, Email, Tally & Telegram | https://n8n.io/workflows/8330 | ARC 6 TP 18/19 — post-voyage survey + testimonial ask |
| **9108** | Automated 4-Stage Email Follow-Up System with AI Personalization and Database Tracking | https://n8n.io/workflows/9108 | 4-stage = 4-ARC analog, full lifecycle pattern |
| **10696** | Automate Email Follow-Ups with Gmail & Google Sheets Using Multi-Stage Sequences | https://n8n.io/workflows/10696 | Multi-stage = multi-ARC lifecycle |
| **11337** | Automated lead nurturing with Gemini AI, Telegram, and Gmail reply detection | https://n8n.io/workflows/11337 | Reply detection + Telegram alert = Initiative #6 |
| **13274** | Send post-purchase email sequences with Postgres, Gmail and OpenAI | https://n8n.io/workflows/13274 | Post-booking = ARC 6 analog |
| **8984** | Client Onboarding Email Automation with Google Sheets + Gemini + Gmail | https://n8n.io/workflows/8984 | ARC 0 guest intake automation |
| **15185** | Send timezone-aware drip emails with Gmail and Google Sheets using daily limits | https://n8n.io/workflows/15185 | Lifecycle drip with timing constraints |
| **11586** | Automate Client Lifecycle: Lead Intake to Onboarding with Airtable, Notion & Google Calendar | https://n8n.io/workflows/11586 | Full client lifecycle from lead to onboarding |
| **11860** | GPT 4.1-mini Automated Proposal to Payment Lifecycle Management | https://n8n.io/workflows/11860 | Proposal-to-payment = ARC 0→4 |
| **6316** | Automated Invoice Payment Reminders with Google Sheets and Gmail | https://n8n.io/workflows/6316 | Simple clean ARC 4 reminder |
| **10581** | Automate Bank Statement and Invoice Reconciliation with GPT and Google Sheets | https://n8n.io/workflows/10581 | Commission recon pattern (report-for-Harlan) |
| **12033** | Multi-Platform Revenue Reconciliation across Stripe, PayPal & Bank | https://n8n.io/workflows/12033 | Commission recon across sources |
| **8936** | Automate Invoice-Bank Statement Reconciliation with Mistral AI and OpenAI GPT-4 | https://n8n.io/workflows/8936 | Harlan's audit in workflow form |
| **8055** | Automate Client Communications & Management with Notion, Gmail, and GPT-4o | https://n8n.io/workflows/8055 | Direct analog to D2M lifecycle comms system |
| **6491** | Automated Client Journey Appointment Reminders & Follow-ups with Twilio | https://n8n.io/workflows/6491 | Client journey reminders + follow-ups |
| **3123** | Automatic Reminders For Follow-ups with AI and Human in the loop Gmail | https://n8n.io/workflows/3123 | Human-in-loop + follow-up reminders |
| **9227** | Automate NPS Survey Collection & Response Handling with GoHighLevel, Gmail & Notion | https://n8n.io/workflows/9227 | ARC 6 TP 18 post-voyage NPS survey |

---

## TIER 3 — Inspect for components (partial fit)

| ID | Workflow | URL | What's useful |
|----|---------|-----|--------------|
| **13453** | Validate concert ticket bookings and orchestrate fan experience | https://n8n.io/workflows/13453 | Booking validation + orchestration = TP 0.5 structure |
| **7856** | Cost-Free Email Follow-Up Sequence with Google Sheets and Gmail | https://n8n.io/workflows/7856 | No-cost follow-up sequence baseline |
| **5391** | Smart Invoice Collection System with GPT-4.1, Gmail & Google Sheets | https://n8n.io/workflows/5391 | Payment collection intelligence |
| **12841** | Send AI-generated stale lead nudges from Notion CRM to Telegram with OpenAI | https://n8n.io/workflows/12841 | Stale-TP nudge → Telegram pattern |
| **4612** | Personal Budget & Expense Tracker with Google Sheets and Alerts MCP | https://n8n.io/workflows/4612 | MCP integration pattern for financial tracking |
| **13545** | Host a static HTML KPI dashboard from Google Sheets with CustomJS | https://n8n.io/workflows/13545 | Dashboard enhancement — Sheets data source |
| **5879** | Automated New Hire Appointment Letters with Google Docs, HR Approval & Gmail | https://n8n.io/workflows/5879 | Approval letter + Gmail = WF-17 structural analog |
| **15969** | Send AI patient follow-ups and rebooking emails with Claude, Gmail, Slack and Sheets | https://n8n.io/workflows/15969 | ARC 6 TP 20 — "next voyage seed" pattern |
| **6192** | Automated Invoice Follow-ups with Smart Response Tones via Google Sheets & Email | https://n8n.io/workflows/6192 | Tone-aware follow-ups = Dani voice-matching |

---

## COVERAGE MAP — 7 Initiatives vs. Downloadable Workflows

| Initiative | Status | Best Downloads |
|-----------|--------|---------------|
| #1 Fare watch re-auth | Code fix, not workflow | N/A — Sterling executes |
| #2 Timer audit | Code audit, not workflow | N/A — Sterling executes |
| #3 Guest intake auto-processing | ✅ COVERED | #15428, #8984, #11586 |
| #4 Commission report-for-Harlan | ✅ COVERED | #10581, #12033, #8936 |
| #5 ARC 6 post-voyage extension | ✅ COVERED | #8330, #13274, #9227, #14802 |
| #6 Client reply flag-for-Hale parser | ✅ COVERED | #5506, #6082, #11337, #15725 |
| #7 Auto-enrich (pending source audit) | Partial | #3767 (after Sterling audits source) |

**WF-17 gate (bonus):** #6082, #15204, #2861 — the human-approval loop is a downloadable workflow, not a build.

---

## STACK ALIGNMENT — D2M vs. n8n Workflows

D2M runs: Gmail OAuth + Google Sheets + Telegram + Claude/Groq

The following workflows use **our exact stack** with zero infrastructure changes:
- #15973 (Sheets + Gmail + Telegram + Groq)
- #14852 (Gmail + Claude + Slack→swap Telegram)
- #16065 (Claude + Google Sheets)
- #6082 (AI + IMAP + human approval)
- #5506 (IMAP + Google Sheets)
- #14802 (Google Sheets + Gemini→swap Claude + Gmail)
- #15185 (Gmail + Google Sheets + daily limits)

---

## SEARCH SCOPE SUMMARY

| Agent | Category/Keywords | Workflows examined |
|-------|------------------|--------------------|
| email-comm | Email search (1,326) + Communication (4) | 1,330 |
| marketing-sales | Marketing (3,106) + Sales (1,428) | 4,533 (file: .playwright-mcp/) |
| productivity-IT | Productivity + IT Ops + Data/Storage | Pending |
| finance-HR | HR (228) + Document Ops/Finance (1,199) | 1,427 |
| keywords-1 | schedule, reminder, date-trigger, approval, draft, lifecycle | 40 |
| keywords-2 | onboarding, booking, travel, payment, reconciliation | 366 |
| gmail-IMAP | Gmail, IMAP, inbox, reply, sequence, drip, nurture | 67 |
| dashboard-reporting | dashboard, Airtable, Notion, Google Sheets, pipeline | 88 |
| **TOTAL** | | **~7,851+** |

---

*Generated: 2026-06-04 | T2 Wing Exercise follow-on | For Sterling implementation*
