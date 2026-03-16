# Client Dossier System — Blueprint for Review
## Dreams2Memories Travel, LLC
### Date: 2026-03-06

---

## ARCHITECTURE OVERVIEW

Two-layer system: **Sheet** (structured, quick lookup) + **Doc** (rich, detailed dossier).

Rule: If a field would exceed 3-5 lines in a cell, it lives in the Doc.

```
Google Drive:
  CLIENT_DOSSIERS/
    └── Furlow_Family/
         ├── Furlow_Dossier (Google Doc)
         ├── Furlow_Regent_Quote.pdf
         ├── Furlow_Booking_Confirmation.pdf
             Furlow Hotel Booking
             Furlow Excursions
             Furlow Dining
             Furlow Transportation
         └── (any related files)
    └── Kuklinski_Family/
         ├── Kuklinski_Dossier (Google Doc)
         └── ...

Booking Master Google Sheet:
  └── Booking Master (existing tab)
  └── Daily Itinerary (existing tab)
  └── Client Profiles (NEW tab)
```

---

## LAYER 1: Client Profiles Tab (Google Sheet)

One row per client/household. Quick-reference structured data.

### Column Schema

| Column | Example | Notes |
|--------|---------|-------|
| Client ID | FURLOW-001 | Auto-generated, links to dossier |
| Household Name | Furlow Family | Primary grouping |
| Primary Contact | John Furlow | Decision-maker |
| Email | sarah.furlow@email.com | |
| Phone | 555-123-4567 | |
| Secondary Contact | Missy Furlow | Spouse/partner |
| Secondary Email | mike.furlow@email.com | |
| Address | 123 Oak St, Denver, CO 80202 | Mailing for cards/gifts |
| Anniversary | 10/14 | For personalized touches |
| Birthdays | Sarah 6/15, Mike 9/22 | |
| Referral Source | Website / Referral / Event | How they found D2M |
| Referred By | (client name if referral) | For referral tracking |
| Preferred Cabin Type | Balcony / Suite / Veranda | |
| Deck Preference | Mid-ship / High / Starboard | |
| Airline Preference | United / Delta / No pref | |
| Seat Preference | Aisle / Window / Business | |
| Dietary Restrictions | Shellfish allergy, vegetarian | |
| Drink Preferences | Veuve Clicquot, no red wine | |
| Mobility Notes | Wheelchair accessible needed | |
| Loyalty Programs | Marriott Bonvoy Gold, UA MileagePlus | |
| Passport Expiry | Sarah: 2028-03-15, Mike: 2029-01-20 | Critical for intl travel |
| Travel Style | Luxury / Adventure / Cultural / Relaxation | |
| Budget Range | $10K-15K per trip | General guidance |
| Past Trips | Regent Mediterranean 2025, Viking Rhine 2024 | Summary only — detail in Doc |
| Active Bookings | Regent 2026 Booking #RS-44521 | Links to Booking Master |
| Dossier Link | (Google Doc URL) | Direct link to full dossier |
| Notes | Prefers morning excursions, no group tours | Short notes only |
| Status | Active / Prospect / Past | |
| Created | 2026-03-06 | |
| Last Updated | 2026-03-06 | |

---

## LAYER 2: Client Dossier (Google Doc)

Rich document per client/household. This is the deep file — everything that won't fit in 5 lines.

### Dossier Doc Template Structure

---

**[D2M HEADER — branded navy/gold banner]**

# CLIENT DOSSIER: {Household Name}
**Dreams2Memories Travel, LLC**
*Prepared by John Loucks | Last Updated: {date}*

---

## 1. CLIENT PROFILE

| Field | Detail |
|-------|--------|
| Primary Contact | {name} |
| Email / Phone | {email} / {phone} |
| Secondary Contact | {name} |
| Address | {full address} |
| Anniversary | {date} |
| Birthdays | {list} |
| Passport Expiry | {list with dates} |
| Loyalty Programs | {detailed list with numbers} |
| Referral Source | {how they found D2M} |

### Personal Preferences
- **Cabin**: {type, deck, side preferences with context}
- **Dining**: {allergies, favorites, wine preferences, reservation style}
- **Excursions**: {morning vs afternoon, group vs private, activity level}
- **Travel Style**: {luxury/adventure/cultural — expanded narrative}
- **Special Occasions**: {upcoming milestones, celebration ideas}
- **Pet Peeves**: {things to avoid — crowded ports, early departures, etc.}

---

## 2. TRAVEL HISTORY

### Trip: {Cruise Line / Destination} — {Month Year}
- **Booking ID**: {id}
- **Ship/Hotel**: {name}
- **Stateroom/Room**: {category + number}
- **Dates**: {embark — disembark}
- **Highlights**: {what they loved}
- **Issues**: {what went wrong, supplier notes}
- **Commission**: {amount, status paid/pending}

*(Repeat for each past trip)*

---

## 3. ACTIVE BOOKING: {Trip Name}

### Booking Summary
| Field | Detail |
|-------|--------|
| Supplier | {cruise line / hotel} |
| Booking ID | {confirmation number} |
| Ship/Property | {name} |
| Stateroom/Room | {category + number} |
| Embarkation | {date, port} |
| Disembarkation | {date, port} |
| Total Cost | {net + markup} |
| Commission | {expected amount} |
| Deposit Paid | {date, amount} |
| Final Payment Due | {date, amount} |
| Insurance | {provider, policy #, or WAIVED} |

### T-minus Timeline Status
| Milestone | Target Date | Status |
|-----------|-------------|--------|
| T-270: Deposit + insurance | {date} | Done / Pending |
| T-150: Air routing audit | {date} | |
| T-120: Specialty dining | {date} | |
| T-90: Final payment | {date} | |
| T-21: Final docs | {date} | |
| T-0: Client on ship | {date} | |
| T+1: Check-in | {date} | |
| T+10: Welcome home | {date} | |
| T+30: Commission audit | {date} | |

---

## 4. RECOMMENDED ITINERARY (Pre-Confirmation)

*This section starts as a curated recommendation. Once confirmed, it converts to the official itinerary.*

**Status: RECOMMENDED / CONFIRMED**

### Day 1 — {Date} — {Port/City}
**Arrival**: {time} | **Departure**: {time}

**Morning**
- {Activity/excursion} — {duration, price, booking status}
- {Notes: why this was chosen for this client}

**Afternoon**
- {Activity/excursion}

**Dining**
- Lunch: {restaurant recommendation + reservation status}
- Dinner: {restaurant + notes on cuisine match to preferences}

**Notes**: {weather forecast, dress code, mobility considerations}

### Day 2 — {Date} — {Port/City}
*(Repeat structure for up to 20+ days)*

---

## 5. TOURS & EXCURSIONS MASTER LIST

| Day | Port | Activity | Provider | Duration | Price/pp | Status |
|-----|------|----------|----------|----------|----------|--------|
| 3 | Santorini | Private wine tour | Viator | 4hr | $185 | Recommended |
| 5 | Dubrovnik | Old Town walking tour | Local guide | 3hr | $95 | Confirmed |
| 8 | Venice | Gondola + Murano glass | GetYourGuide | 5hr | $210 | Recommended |

---

## 6. DINING PLANNER

| Day | Meal | Restaurant/Venue | Cuisine | Reservation | Notes |
|-----|------|------------------|---------|-------------|-------|
| 1 | Dinner | Compass Rose (ship) | French | 7:30 PM | Window table requested |
| 3 | Lunch | Ammoudi Fish Taverna | Greek seafood | Walk-in | No shellfish — order grilled fish |
| 5 | Dinner | Nautika (Dubrovnik) | Mediterranean | 8 PM | Anniversary dinner — cake ordered |

---

## 7. LOGISTICS & TRANSPORT

| Segment | Detail | Status |
|---------|--------|--------|
| Outbound Flight | UA 1234 DEN-FCO 6/10 dep 5:45p | Confirmed |
| Pre-cruise Hotel | Hotel de Russie, Rome — 2 nights | Confirmed |
| Airport Transfer | Private car FCO to hotel | Booked |
| Hotel to Port | Private car Rome to Civitavecchia | Recommended |
| Return Flight | UA 5678 FCO-DEN 6/30 dep 10:15a | Confirmed |

---

## 8. ANTICIPATION ENGINE LOG

Content drip tracker — what has been sent to this client pre-trip.

| Date Sent | T-minus | Content | Channel |
|-----------|---------|---------|---------|
| 2026-04-01 | T-90 | "Your Mediterranean Adventure Awaits" intro | Email |
| 2026-04-08 | T-83 | Santorini wine region guide | Email |
| 2026-04-15 | T-76 | Dubrovnik history + Game of Thrones spots | Email |
| 2026-04-22 | T-69 | Spotify playlist: Mediterranean Evenings | Email |

---

## 9. COMMUNICATION LOG

| Date | Type | Summary |
|------|------|---------|
| 2026-03-01 | Phone | Initial inquiry — interested in Mediterranean cruise |
| 2026-03-05 | Email | Sent 3-option quote PDF |
| 2026-03-08 | Phone | Selected Regent option, deposit paid |

---

## 10. REFERRAL TRACKING

| Referred Client | Date | Trip Booked | Status |
|-----------------|------|-------------|--------|
| Johnson Family | 2026-02-15 | Viking Rhine 2026 | Booked |

**Thank You Sent**: Handwrytten card 2026-02-20

---

*Document auto-generated by Thunderbird OS | Dreams2Memories Travel, LLC*
*Template Version 1.0*
