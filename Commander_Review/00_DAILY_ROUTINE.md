# D2M THUNDERBIRD — COMMANDER'S DAILY ROUTINE
## Effective March 8, 2026

---

## AUTOMATED REPORTS SCHEDULE

### 0630 — MORNING BRIEFING (Daily)
| | |
|---|---|
| **Delivery** | Email to johnloucks3@gmail.com |
| **OPR** | A2-Dembe (Intelligence) |
| **Module** | thunderbird_morning_briefing.py |
| **Contains** | |
| | Executive summary with alert banner (RED/GOLD/GREEN) |
| | Stats bar: action items, this-week items, intel count, fare watches |
| | Anchor dates — upcoming deadlines with DONE/SNOOZE buttons |
| | World intel — travel advisories, destination news |
| | Ship intel — cruise line pricing, availability changes |
| | Tech news digest |
| | Fare watch alerts — tracked flight price changes |
| **Dedup** | Items not repeated within 5-day window |
| **Action** | Tap DONE or SNOOZE on any anchor date item from your phone |

### 0700 — PAYMENT ALERTS (Daily)
| | |
|---|---|
| **Delivery** | SMS to 719-291-0742 (T-Mobile gateway) |
| **OPR** | A3-Moreau (Operations) |
| **Module** | thunderbird_payment_alerts.py |
| **Contains** | |
| | Payment reminders at FPD-21, FPD-14, FPD-7, FPD-3, FPD-1 |
| | Client name, booking ID, amount due, days remaining |
| **Active bookings** | |
| | Viking: Kuklinski x2, Morton — FPD Mar 31 |
| | Regent: Furlow, Ely/Darrow, Nichols — FPD Apr 1 |
| **Action** | Review, then reach out to clients as needed |

### 0700 MONDAY — WEEKLY INTELLIGENCE DIGEST
| | |
|---|---|
| **Delivery** | Email to johnloucks3@gmail.com |
| **OPR** | A2-Dembe (Intelligence) |
| **Module** | thunderbird_morning_briefing.py --weekly |
| **Contains** | |
| | Full week roll-up of all intel sources |
| | Consolidated anchor dates for the week ahead |
| | Fare watch trends (week-over-week) |
| | World + ship intel digest |
| **Action** | Plan your week — identify calls, follow-ups, deadlines |

### EVERY 15 MINUTES — STAR PROTOCOL SWEEP
| | |
|---|---|
| **Delivery** | Gmail drafts (replies to starred/self-emails) |
| **OPR** | COS-Hale (Chief of Staff) |
| **Module** | thunderbird_star_protocol.py --sweep |
| **Processes** | |
| | Red bang starred emails → COS extracts intent, routes action |
| | Green check starred emails → EXEC + COS execute |
| | Blue star emails → EXEC drafts reply in Yoda's voice |
| | Self-emails with [PERSONA] tag → routes to that persona |
| | [STAFF] tag → full 9-persona staff meeting |
| | DONE/SNOOZE commands → updates Action_Tracker sheet |
| **Action** | Star an email or email yourself to trigger |

---

## COMMANDER'S MORNING FLOW

```
0630  Morning Briefing lands in inbox
      → Scan alert banner (RED = action needed, GOLD = this week, GREEN = clear)
      → Review anchor dates — tap DONE/SNOOZE as needed
      → Note any intel that affects client conversations

0700  Payment alerts arrive via SMS (if any due)
      → Check which clients need a nudge

0700  (Mondays) Weekly digest arrives
      → Plan the week: calls, follow-ups, deadlines

0715  Check Gmail drafts
      → Star Protocol may have created draft replies overnight
      → Review, edit voice, send or discard

0730  Commander Review folder
      → ~/Thunderbird/Commander_Review/
      → Staged email drafts, briefings, action trackers
      → Review, approve, send
```

---

## NOT YET AUTOMATED (Manual / Next Session)

| Item | Status | OPR |
|------|--------|-----|
| Dining milestone anchors (E-120, E-90, E-60) | NOTED — Yellow Keep note | A5-Castillo |
| A3 anchor date scan cron | Needs wiring | A3-Moreau |
| World intel sweep (scheduled) | Tool exists, no cron | A2-Dembe |
| Ship intel sweep (scheduled) | Tool exists, no cron | A2-Dembe |

---

## HOW TO TRIGGER THINGS MANUALLY

| Want to... | Do this |
|------------|---------|
| Get a briefing NOW | Star Protocol: email yourself `[A2] Send me a briefing` |
| Ask a persona | Email yourself: `[COS] Should I call Larry today?` |
| Run a staff meeting | Email yourself: `[STAFF] Prep me for the Ely call` |
| Mark something done | Tap DONE button in morning briefing email |
| Snooze an item 7 days | Tap SNOOZE button in morning briefing email |
| Flag an email for action | Star it RED in Gmail — COS picks it up within 15 min |
| Request a draft reply | Star it BLUE in Gmail — EXEC drafts in your voice |
| End a session | Say **"Land this bird"** — COS runs EOD debrief |

---

*OPR = Office of Primary Responsibility*
*FPD = Final Payment Date*
*All times Mountain Time (MT)*
