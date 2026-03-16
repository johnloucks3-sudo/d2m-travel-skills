# Outside Agents Tech Stack Analysis — March 10, 2026
## A3/A5/A9 Joint Intelligence Assessment

---

### What Outside Agents (OA) Offers

**MAGtap** — Portal hub at `tap.myagentgenie.com`
- Agent portal aggregator — centralizes supplier access
- Quick-launch tiles for cruise lines, hotels, tours
- Functional but generic — no personalization, no AI

**TESS CRM** — `crm.myagentgenie.com`
- Outside Agents' proprietary CRM system
- OAuth 2.0 + PKCE API documented but not ported to Python
- Client management, booking tracking, task reminders
- Standard CRM functionality — nothing AI-powered
- **Task 5.8:** Port TESS OAuth to Python — elevated to Priority 1

**MAGgie** — OA's AI Assistant
- ChatGPT-4o wrapper with travel context
- General Q&A, no operational capability
- Cannot access bookings, clients, or systems
- Not comparable to Thunderbird personas — MAGgie answers questions, our Wing executes missions

---

### A3 (Moreau) Assessment — Operations

"TESS is where our client data lives. Without a Python bridge, every lookup is manual. Task 5.8 isn't a nice-to-have — it's a bottleneck. If I can read TESS programmatically, I can auto-populate dossiers, pull booking statuses, and flag payment deadlines without Commander touching CruisingPower."

**Gap Thunderbird fills:** Automated dossier management, proactive payment alerts, booking lifecycle tracking — TESS stores the data, Thunderbird makes it actionable.

---

### A5 (Castillo) Assessment — Strategy

"MAGtap is a portal launcher. That's a 2015 solution. The gap isn't portal access — it's what happens AFTER you access the portal. Thunderbird's browser automation + MCP pipeline means we can scrape, extract, compare, and quote in one flow. OA gives you the door; we walk through it and bring back intelligence."

**Gap Thunderbird fills:** End-to-end automation from portal access through quoting. OA stops at the login page; we stop at the client's inbox.

---

### A9 (Harlan) Assessment — Finance

"MAGgie costs OA money and gives agents nothing operational. Our model router gives us Groq at $0/month for routine work and Claude only when quality demands it. OA's $25/month or whatever they charge for MAGgie? That's paying for a parrot. We built an operations center."

**Key numbers:**
- OA MAGgie: ~$25/month (estimated, GPT-4o wrapper)
- Thunderbird Groq tier: $0/month (500 free calls)
- Thunderbird Claude escalation: ~$63/day on heavy build days, ~$5-10/day in operations
- Thunderbird ROI: automation saves 2-3 hours/day of manual work

**Gap Thunderbird fills:** Cost-optimized AI that actually operates vs. a chatbot that answers questions.

---

### Strategic Recommendations

1. **TESS OAuth Port (Task 5.8) — Priority 1**
   - Port TESS OAuth 2.0 + PKCE to Python
   - Enable programmatic client/booking data access
   - Feed TESS data into dossier pipeline automatically
   - A3 to submit proposal tomorrow

2. **MAGtap Browser Integration**
   - Already have `thunderbird_browser.py` with stealth Playwright
   - Can automate portal logins and data extraction
   - Lower priority — TESS API is cleaner than scraping

3. **Competitive Positioning**
   - OA provides tools; we provide intelligence
   - Our multi-persona system has no equivalent in the host agency ecosystem
   - Document this gap for commercial pitch (Monetize initiative)

---

*Joint assessment by A3 (Moreau), A5 (Castillo), A9 (Harlan) — March 10, 2026*
