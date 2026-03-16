# Travel Business Enhancements with MCP + Claude CLI/Desktop
## Dreams2Memories / Love Group Travel
### What You Have Now vs. What's Possible

---

## WHAT WE JUST DID (AND WHAT IT PROVES)

In this single session, Claude CLI + your MCP server accomplished:

1. **Live hotel search** — Hotelbeds API via MCP, real-time rates for Venice
2. **Neighborhood intelligence** — Context-rich descriptions no booking engine provides
3. **Commission modeling** — Instant 20/22/25% rate cards, agent vs. client copies
4. **Cruise research** — Multi-source intelligence gathering (Ponant, Lindblad, agent promos)
5. **Air research** — Icelandair Saga Premium routing, pricing, seat specs
6. **Document generation** — Client-ready and agent-confidential versions, saved to disk
7. **Stealth browsing** — Playwright scraping of cruise line sites that block standard fetches

**Total time:** ~45 minutes for work that would normally take 4-6 hours.

---

## ENHANCEMENTS BY CATEGORY

---

## 1. CLIENT COMMUNICATION AUTOMATION

### What You Can Do Now
You manually research, write, and format proposals for clients.

### What MCP + Claude Enables

#### A. One-Command Client Proposals
```
You say: "Build a proposal for the Johnsons — Mediterranean cruise,
         October, 2 weeks, Silversea, balcony suite, budget $40K"

Claude: Searches live rates → pulls ship specs → writes neighborhood
        guides for each port → generates commission breakdown →
        creates client PDF + agent summary → saves to Drive
```

**New MCP Tool to Build:** `generate_client_proposal`
- Input: Client name, destination, dates, cruise line, cabin type, budget
- Process: Chain hotel search + cruise research + narrative generation
- Output: Client-facing PDF + agent rate sheet

#### B. Automated Follow-Up Documents
After a client books, auto-generate:
- Pre-departure guide (weather, packing, visa requirements)
- Port-by-port dining recommendations
- Shore excursion comparisons with your recommendations
- Emergency contact cards

**How:** Claude reads the booking data from your Excel/Sheets, then generates personalized documents using your templates.

#### C. Birthday/Anniversary Trip Suggestions
- MCP tool reads your client database
- Claude matches client preferences to upcoming voyages
- Auto-drafts personalized email: "We noticed your anniversary is in May — Silver Nova has a Mediterranean sailing that matches your style..."

---

## 2. PRICING INTELLIGENCE & ALERTS

### What You Have Now
`thunderbird_ship_intel.py` scrapes cruise line sites on a schedule.

### Enhancements

#### A. Price Drop Alert System
```python
# New MCP tool: monitor_price_alerts
# Runs daily via cron, compares against saved baseline
# When price drops >5%, Claude drafts alert email to you
```

**Claude CLI Workflow:**
```bash
# Add to your crontab:
0 7 * * * claude -p "Run ship intel sweep, compare prices against
yesterday's baseline in the tracking sheet. If any priority vessel
shows >5% price drop or <3 suites remaining, draft an alert email
with the details and save to ~/Thunderbird/alerts/"
```

#### B. Competitor Rate Monitoring
- Scrape Vacations To Go, Cruise Compete, CruiseDirect for the same voyages
- Compare your Hotelbeds net rate vs. what competitors advertise
- Flag opportunities where your markup is still below retail

#### C. Historical Price Tracking
- Store every price check in a time-series database
- Claude analyzes trends: "Silver Nova Mediterranean suites have dropped 12% in the last 30 days — historically they rebound in April. Recommend booking now."

---

## 3. GOOGLE WORKSPACE DEEP INTEGRATION

### What You Have Now
`thunderbird_drive.py` for file operations, limited by service account quota.

### Enhancements

#### A. Fix Drive Uploads (OAuth Delegation)
Your current service account can't upload to personal Drive. Fix:
1. Set up Google Workspace domain-wide delegation
2. OR use a Shared Drive (Team Drive) for all generated documents
3. OR switch to OAuth 2.0 user credentials with refresh token

#### B. Gmail Integration for Client Communication
```
You say: "Draft a follow-up email to Margaret about the Venice hotels
         we researched. Attach the client guide. Warm, professional tone."

Claude: Reads Venice_Hotel_Guide_CLIENT_Jul2026.md → drafts email →
        creates Gmail draft with attachment → you review and send
```

**Already Available:** `mcp__claude_ai_Gmail__gmail_create_draft` is in your MCP tools.

#### C. Google Calendar for Booking Deadlines
```
You say: "Add cancellation deadline reminders for all active bookings"

Claude: Reads booking data → creates calendar events for:
        - Free cancellation cutoff dates
        - Final payment due dates
        - Departure dates
        - Client birthday/anniversary milestones
```

**Already Available:** `mcp__claude_ai_Google_Calendar__gcal_create_event` is in your MCP tools.

#### D. Sheets as a Live Dashboard
- Auto-populate a "Pipeline" sheet with all active quotes
- Track: Client, Destination, Quote Amount, Status, Commission, Follow-up Date
- Claude updates status as you work: "Move Johnson Venice quote to 'Presented'"

---

## 4. CANVA INTEGRATION FOR VISUAL PROPOSALS

### What You Have Now
Markdown documents. Professional but text-heavy.

### What's Possible

**Already Available:** You have the full Canva MCP toolkit:
- `mcp__claude_ai_Canva__generate-design` — AI-generated designs
- `mcp__claude_ai_Canva__create-design-from-candidate` — Template-based
- `mcp__claude_ai_Canva__export-design` — Export to PDF/PNG

#### A. Branded Itinerary Designs
```
You say: "Create a visual itinerary for the Venice trip using our
         brand template"

Claude: Takes hotel data + photos → generates Canva design with
        your Dreams2Memories branding → exports as PDF →
        saves to Thunderbird
```

#### B. Social Media Content
- Generate Instagram/Facebook posts for featured voyages
- "Just booked this stunning Mediterranean sailing on Silver Nova..."
- Canva creates the visual, Claude writes the caption

#### C. Client Gift: Custom Travel Postcards
- After a trip, generate a "memory card" with their itinerary highlights
- Personal touch that drives referrals

---

## 5. MULTI-SOURCE BOOKING CONSOLIDATION

### What You Have Now
`consolidate_booking_sources` tool (stub — needs implementation).

### Full Implementation Vision

#### A. PDF → Structured Data Pipeline
```
You say: "I just received the Silversea confirmation PDF for the
         Thompson booking. Process it."

Claude: Reads PDF → extracts all booking fields → validates against
        schema → syncs to Excel master workbook → creates calendar
        reminders → drafts confirmation email to client → files
        PDF in Drive
```

**Requires:** Implementing the PDF extraction in `extract_pdf_booking_details` with pdfplumber or PyPDF2.

#### B. Email → Booking Detection
- Monitor Gmail for booking confirmation emails (from cruise lines, airlines, hotels)
- Auto-extract booking data
- Flag discrepancies: "The airline confirmation shows different dates than the cruise booking"

#### C. Master Booking Dashboard
- Single Excel/Sheets workbook with all active bookings
- Auto-updated when new confirmations arrive
- Commission tracking: expected vs. received
- Payment milestone tracking

---

## 6. CRUISE LINE RESEARCH AUTOMATION

### What You Have Now
`thunderbird_ship_intel.py`, `thunderbird_ship_compare.py`, stealth browser.

### Enhancements

#### A. "Find Me a Cruise" Natural Language Search
```
You say: "Find me a luxury cruise for a couple in their 70s,
         Mediterranean, 2 weeks, October 2026, balcony suite,
         under $15K per person, with included excursions"

Claude: Searches Ponant, Silversea, Regent, Viking, Oceania →
        compares itineraries, pricing, inclusions → ranks by
        value → presents top 5 with your commission on each
```

**New MCP Tool:** `search_all_cruise_lines` — Orchestrates multiple stealth browser searches in parallel.

#### B. Ship Comparison on Demand
```
You say: "Compare Silver Nova vs Seven Seas Grandeur for the
         Mediterranean in October"

Claude: Pulls specs from ship database → scrapes current pricing →
        generates side-by-side DOCX/PDF → includes your recommendation
```

**Already Built:** `thunderbird_ship_compare.py` — just needs Claude CLI integration.

#### C. Voyage Availability Watchlist
- Client wants a specific sailing that's sold out or waitlisted
- Add to watchlist → MCP checks daily → alerts when cabin opens up
- "Regent Suite on Seven Seas Grandeur June 15 just became available — 1 cabin"

---

## 7. HOTEL SEARCH ENHANCEMENTS

### What You Have Now
Hotelbeds API search (working — we used it today).

### Enhancements

#### A. Multi-Source Hotel Comparison
- Search Hotelbeds API (net rates) + Bedsonline browser (visual) simultaneously
- Compare against Booking.com/Expedia published rates
- Show the client your value: "Published rate: $2,500 → Our rate: $1,850"

#### B. Pre/Post Cruise Hotel Packages
```
You say: "Find pre-cruise hotels in Barcelona for the Thompsons,
         2 nights before their Silversea sailing on Oct 5"

Claude: Searches Oct 3-5, Barcelona, 5-star, breakfast →
        filters for port proximity → adds transfer recommendations →
        generates package quote with cruise + hotel + transfers
```

#### C. Hotel Photo Gallery Generation
- Pull all Hotelbeds photos for shortlisted hotels
- Generate a visual comparison document
- Client sees rooms, lobby, pool, restaurant side by side

---

## 8. FINANCIAL & COMMISSION TRACKING

### New Capability

#### A. Commission Calculator MCP Tool
```python
# New tool: calculate_commission
# Input: Cruise line, fare, cabin category
# Output: Net cost, commission rate, commission $, client rate
# Accounts for: line-specific rates, CLIA bonuses, volume tiers
```

#### B. Monthly Revenue Dashboard
- Track all bookings, commissions earned vs. pending
- Auto-generate monthly P&L
- Forecast upcoming commission payments by date

#### C. Supplier Payment Reconciliation
- Match received commission checks against expected amounts
- Flag discrepancies: "Ponant paid $3,200 but expected $3,751 — investigate"

---

## 9. CLAUDE DESKTOP vs. CLI — WHEN TO USE WHICH

| Task | Best Tool | Why |
|------|-----------|-----|
| Quick hotel search | **Claude Desktop** | Conversational, visual |
| Batch processing 10 bookings | **Claude CLI** | Scriptable, automatable |
| Client proposal generation | **Either** | Desktop for drafting, CLI for templates |
| Daily intel sweeps | **Claude CLI + cron** | Automated, no human needed |
| Research deep-dive (like today) | **Claude CLI** | MCP tools, file access, long sessions |
| Email drafting | **Claude Desktop** | Gmail MCP, review before send |
| Canva design work | **Claude Desktop** | Visual review needed |
| Price alert monitoring | **Claude CLI + cron** | Background automation |

---

## 10. AUTOMATION WORKFLOWS (CRON + CLAUDE CLI)

### Daily Morning Briefing (6 AM)
```bash
0 6 * * * claude -p "Run morning briefing:
  1. Check ship intel for price changes on priority vessels
  2. Check world intel for travel advisories affecting active bookings
  3. Check upcoming cancellation deadlines (next 7 days)
  4. Check client birthdays/anniversaries this month
  Save briefing to ~/Thunderbird/daily_briefings/" --dangerously-skip-permissions
```

### Weekly Report (Monday 7 AM)
```bash
0 7 * * 1 claude -p "Generate weekly report:
  1. New bookings this week
  2. Commission earned/pending
  3. Price movements on watched voyages
  4. Upcoming deadlines
  5. Market intelligence summary
  Save to ~/Thunderbird/weekly_reports/" --dangerously-skip-permissions
```

### On-Demand Client Proposal
```bash
claude -p "Build proposal for [client]: [destination], [dates],
  [cruise line], [cabin type], [budget]. Include hotel pre/post,
  flights, commission analysis. Save client + agent copies to
  ~/Thunderbird/proposals/"
```

---

## IMPLEMENTATION PRIORITY

### Quick Wins (This Week)
| # | Enhancement | Effort | Impact |
|---|-------------|--------|--------|
| 1 | Gmail draft integration (already available as MCP tool) | Low | High |
| 2 | Calendar reminders for booking deadlines (already available) | Low | High |
| 3 | Canva visual proposals (already available as MCP tool) | Low | High |
| 4 | Commission calculator MCP tool | Medium | High |

### Medium-Term (This Month)
| # | Enhancement | Effort | Impact |
|---|-------------|--------|--------|
| 5 | Fix Drive uploads (OAuth or Shared Drive) | Medium | High |
| 6 | PDF booking extraction (implement pdfplumber) | Medium | High |
| 7 | Daily morning briefing automation (cron + CLI) | Medium | High |
| 8 | Multi-cruise-line search tool | Medium | High |

### Longer-Term (This Quarter)
| # | Enhancement | Effort | Impact |
|---|-------------|--------|--------|
| 9 | Price drop alert system | Medium | Medium |
| 10 | Master booking dashboard | High | High |
| 11 | Voyage availability watchlist | High | Medium |
| 12 | Historical price trend analysis | High | Medium |

---

## YOUR UNTAPPED MCP TOOLS

You already have these connected but may not be using them fully:

| Tool | What It Does | Business Use |
|------|-------------|--------------|
| `gmail_create_draft` | Draft emails in Gmail | Client proposals, follow-ups |
| `gmail_search_messages` | Search inbox | Find booking confirmations |
| `gcal_create_event` | Create calendar events | Deadline reminders |
| `gcal_find_my_free_time` | Find open slots | Schedule client calls |
| `Canva generate-design` | AI-generated designs | Visual proposals |
| `Canva export-design` | Export to PDF | Client-ready documents |
| `drive_search` | Search Google Drive | Find past proposals |
| `drive_list_files` | Browse folders | Audit file organization |
| `browse_url` | Stealth browser | Any website research |
| `browse_and_click` | Interactive browsing | Fill forms, navigate portals |

---

## THE BIG PICTURE

**Before MCP + Claude CLI:**
- 4-6 hours researching one client trip
- Manual rate comparisons across browser tabs
- Copy-paste into Word documents
- Separate spreadsheet for commission tracking
- Hope you didn't miss a deadline

**After MCP + Claude CLI:**
- 30-45 minutes for a complete researched proposal
- Live API rates with automatic commission modeling
- Branded documents generated instantly
- Automated deadline tracking and alerts
- Morning briefing waiting for you at 6 AM

**ROI:** If you handle 10 client inquiries per week and save 3 hours each, that's **30 hours/week** back — time for more clients, better service, or actual vacation.

---
*Saved to ~/Thunderbird/ — March 4, 2026*
