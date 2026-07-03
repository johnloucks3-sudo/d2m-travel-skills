# HALE — Institutional Memory
*Persistent across all sessions. Updated by hale_dispatcher. Loaded at session start.*
*Last updated: 2026-04-24*

---

## Commander Profile

**Name:** John Loucks ("Yoda")
**Location:** Colorado Springs / Monument, CO
**Phone:** 719-291-0742 — work cell AND personal cell. Cleared for all D2M comms.
**Company:** Dreams2Memories Travel, LLC — EXCLUSIVE. Never "Love Group Travel."

**Hale Address Protocol — Standing Behavioral Rule:**
The form of address Hale uses signals which disposition is active. Non-negotiable and consistent.
- "John" / "Yoda" → COO mode (operational, peer authority)
- "Commander" → COS/DoS mode (formal, staff coordination, military bearing)
- "Sir" / "Boss" / "Colonel" → EA/Exec Secretary mode (anticipatory, deferential, serving Commander's needs)
Commander always knows which Hale he's talking to before she says another word.

**Communication preferences:**
- Brief first. Lead with answer/action, not reasoning.
- No trailing summaries or recaps.
- No preamble, no filler openers ("Happy to help," "Certainly," etc.)
- Mobile-first: Telegram messages scannable, ≤4096 chars. Bold for emphasis, tables for data.
- Multiple-choice questions always — numbered options, faster on mobile.
- Maximum autonomy granted. Execute without confirmation except destructive/irreversible.

**Sign-off:** "Thanks" or "Thank you." NEVER "Best."
**Email ink:** Bright blue (#0000ff) on cream (#f7f3ea).

---

## Standing Orders (Current)

| SO | Date | Rule |
|----|------|------|
| Email Send Gate | 21 MAR 2026 (amended 24 MAR) | No sends outside wing without Commander approval. Exception: johnloucks3@gmail.com |
| Email Account Separation | 24 MAR 2026 | d2mconcierge = sole ops Gmail. ZERO drafts in johnloucks3. |
| Intel Full Send | 27 MAR 2026 | Briefs/intel → johnloucks3 as full sends. Client products → WF-17. |
| Root Cause Imperative | Standing | Fix source. Never paper over. |
| Auto-Save | 27 MAR 2026 | Checkpoint every 10 min during active sessions. |
| Dani = Client-Only | 25 MAR 2026 | Dani handles client replies ONLY. No supplier/briefing/marketing. |
| No force-push to main | Standing | Never. No --no-verify. |
| OPUS override | 2026-04-03 | "OPUS: [task]" from Telegram → route to Claude Opus headless. |
| Sonnet override | 2026-04-03 | "Sonnet: [task]" from Telegram → route to Claude Sonnet headless. |
| Hale MAX Autonomy | 2026-04-12 | Authority: Do anything except email clients or commit money. Reminder protocol active. |
| **FULL WING AUTHORITY** | **2026-04-24** | **Commander granted Hale complete authority over the wing. ONLY exception: WF-17 gate (client send still requires Commander approval). Execute without confirmation on all wing tasks.** |

---

## Key Decisions (Commander-Made)

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-20 | Dani = Aggregator/Artist/Advocate | She gathers, crafts, presents. Not researcher, not money person, not Commander-reply. |
| 2026-03-24 | Thunderbird AI Incubator daily cadence | 18:30 prompt → 19:00 execute → 19:30 review → AM expand |
| 2026-03-27 | Intel Full Send SO | All briefs/intel to johnloucks3 as full sends, skip draft step |
| 2026-03-29 | OpsCenter live | Telegram pager → queue → Python daemon. Groq free / Gemini cheap / Claude MAX queued. |
| 2026-03-30 | Commander switched to Opus | Both Sonnet/Opus available. |
| 2026-04-03 | OpenRouter/DeepSeek V3.1 as primary OpsCenter brain | ~$0.27/M tokens. Fallback: Groq → Gemini Flash |
| 2026-04-03 | Hale Super Persona authorized (Step 4) | Three-brain architecture. Virtual ceiling up to client send. Zero financial authority. |
| 2026-04-03 | DeepSeek = Wing arbitrator | "The Solomon of AIs." Final rulings. |

---

## Wing Architecture (Current)

### Model Routing
- **DeepSeek V3.1 (OpenRouter, ~$0.27/M):** Primary brain for all operational tasks, summaries, routing, research
- **Groq Llama 3.3:** Fallback when OpenRouter unavailable
- **Claude Sonnet/Opus:** Client-facing emails, proposals, voice-matched copy, complex reasoning
- **DeepSeek R1:** Arbitration, final rulings (PII-fenced)
- **Gemini Flash:** Emergency fallback

### File System — Wing Communications
| File | Role |
|------|------|
| `OpsCenter/collaboration/claude_inbox.md` | Tasks FROM wing TO Claude |
| `OpsCenter/collaboration/opencode_inbox.md` | Tasks FROM wing TO OpenCode |
| `OpsCenter/collaboration/claude_outbox.md` | Results FROM Claude |
| `OpsCenter/collaboration/wing_comms.md` | FYI/REQUEST between agents |

### Active Infrastructure
- Thunderbird MCP: port 8765 (HTTP JSON-RPC), 285+ tools
- OpsCenter task queue: `OpsCenter/03_CLAUDE_MAX_QUEUE.json`
- Telegram bot: active, routes to OpsCenter task_processor.py
- **OpenCode** v1.3.17: DeepSeek V3.1 via OpenRouter (~$0.27/M), headless via `opencode run -m openrouter/deepseek/deepseek-chat-v3.1 "task"`
- Claude headless: `claude -p "[prompt]" --dangerously-skip-permissions`
- **Hale Draft Engine**: systemd timer active — 07:00 MT daily
- **Touchpoint Proposer**: systemd timer active — 06:00 MT daily
- **Chrome debug service: `chrome-debug.service` — OFFLINE (port 9222 not responding)**
  - Profile: ~/.chrome-debug-profile (separate from Commander's personal Chrome)
  - Gives OpenCode CDP access for SPA scraping (Silversea.com, OA portal, etc.)
  - Verify: `curl -s http://localhost:9222/json/version`
  - Restart: `systemctl --user restart chrome-debug.service`

---

## Client Relationships

### Active Clients
| Client | Trip | Status | Key Facts |
|--------|------|--------|-----------|
| McLeod / McGlasson | Silver Muse · Silversea · Med · Jun 23 | ACTIVE | FPD PAID. Open: transfer dispute, return flights TBD. |
| Lyons, Nancy & Ken | Regent Splendor · Athens→NY · Aug 11 | ACTIVE | **FPD DUE MAY 11** — amount TBD. Flights TBD. F&F/validation status. |
| Furlow, Missy & John | Regent Grandeur · Scandinavia · Aug 29–Sep 8 | BOOKED | Final pmt $15,486 PAID Mar 25. Finnair BB4X94. All 3 couples paid. Insurance pending. |
| Nichols, Larry | Regent Grandeur · Scandinavia · Aug 29 | BOOKED | FPD PAID. Insurance on file (review), flights TBD. |
| Ely / Darrow | Regent Grandeur · Scandinavia · Aug 29 | BOOKED | FPD PAID. Flights TBD, pre/post hotel TBD. |
| Kuklinski · 3 couples | Viking Mars · Panama Canal · Dec 17–27 | RESEARCH | FPD PAID $21,244. Booking 9593880/9593873/9595029. Guests: **Kyle+Rosalie Kuklinski** (9593880, $800 SBC), **Roger+Dr. Nicholas Kuklinski** (9593873, $200 SBC), **Josh+Erica Morton** (9595029, $200 SBC). **Validation email pushed to drafts 2026-04-24 (SEND GATE PENDING).** Insurance email still OVERDUE. Josh Morton guest form still OVERDUE. Air/hotel search open. Excursion window Aug 2; dining window Sep 18. |
| Westbrook, Ron & Lindy | ~~Silver Nova Trans-Pacific~~ | **CANCELLED + BEREAVEMENT** | **⚠️ Lindy Westbrook passed away April 23, 2026.** Booking 566904-25. Allianz Annual Premier E2549991663 ($15K policy) — claim scope $11,280. Both transfers refunded. **Cancellation drafts pushed to d2mconcierge 2026-04-24:** Jenna Woodcock (jwoodcock@perx.com) + Zoro L (zoro@skyluxtravel.com). Awaiting Commander send approval. Hilton Tokyo 33S2013960 (~$480) also in Allianz claim. NOT a D2M booking. Handle all Ron Westbrook communications with bereavement sensitivity. |
| Westbrook, Brent & Kim | — | INACTIVE | Commander's son & daughter-in-law. SWA pilot (Brent), anesthesiologist (Kim). No active booking. |
| Loucks, John & Susan | Japan voyage (Silver Nova companion party) | PERSONAL | Commander's personal trip with Susan + Ron & Lindy Westbrook. Returned ~May 11. Not a D2M booking. |

### ⚠️ WESTBROOK DISAMBIGUATION — REQUIRED READING
Two unrelated Westbrook families. NEVER conflate them.
- **Brent & Kim Westbrook** — Commander's son & daughter-in-law. No active booking. Client relationship.
- **Ron & Lindy Westbrook** — Commander's personal friends from Monument, CO. Silver Nova Trans-Pacific CANCELLED (medical emergency Apr 20). Personal/F&F service, not a D2M-booked trip. Commander and Susan Loucks were travel companions.

### Client Voice Rules (WF-17 Gate)
- Every hotel/transfer/excursion: name, link, images, customer comments, price (Queen/Double + King/Grand)
- No "happy to help," no concierge announce, no ⚠ unpaid markers
- AI disclaimer = Commander's PS only — not generated copy
- One-line close. CTA = next action.

---

## Email / Comms

- **d2mconcierge@gmail.com** = sole ops Gmail. ALL drafts here. ALL business here.
- **concierge@d2mluxury.quest** = send-as alias on d2mconcierge. Client-facing.
- **johnloucks3@gmail.com** = Commander's receive-only inbox. Within-wing sends OK. ZERO drafts or debris.

---

## Targeted Cruise Lines
Silversea · Regent Seven Seas · Cunard · Oceania · Seabourn · Viking · AmaWaterways · Ponant

---

## Ship Photo Archives
- Silver Muse: ship_562, Drive: 1tzCKikPcE5s8zTpwEDKUr5ImEd9Eq8ML
- Silver Nova: ship_745, Drive: 1vrOoeIc0RObWKMhGzcdcOO_wVHWcuFaA
- Viking Mars: ship_731, Drive: 1iJSlwwk_wdOzbh9cBbbJhPPGFcV28ZYVc
- Seven Seas Grandeur: ship_732, Drive: 1e-0rbVOhvI-jB4WPwBf1DBu591s0uXJ1

---

## Infrastructure
- YOGA: 192.168.1.198 | Chromebook: 100.115.92.196
- Cloudflare tunnel: api.d2mluxury.quest
- Itinerary tunnel: itinerary.d2mluxury.quest → YOGA:8900 → ~/Thunderbird/output/
- MCP config: ~/.claude/mcp.json
- Working directory: ~/Thunderbird/

### Intel Source Strategy — Cruise Line Data

| Source | Access | Use for |
|--------|--------|---------|
| `deluxecruises.com` | ✅ curl works, no WAF | Silversea static itinerary data — PRIMARY |
| `icruise.com` | ✅ usually works, may need Chrome | Ship details, port schedules — SECONDARY |
| `silversea.com` | ❌ Gatsby SPA, zero static data | Never scrape. CDP/Chrome required to render. |
| `cruisecritic.com` | ⚠️ rate-limited | Reviews only, not itinerary data |

### Silver Nova — Wrangell Correction (Confirmed 2026-04-04)
- **Wrangell, AK departure: 7:00 PM** (Commander confirmed directly)
- Previous dossier data showed 3:00 PM — WRONG, now corrected
- Both Westbrook and Loucks excursions CLEAR of departure:
  - John Muir Hike (2:30–3:15 PM) ✅
  - Botanicals excursion (4:00 PM) ✅

---

*This file is maintained by hale_dispatcher.py. Last manual sync: 2026-04-24 (MISSION-005 — OpenCode state sync).*
## A7 - Brig Gen (Ret.) Thomas "Gauge" Sterling (ADDED 2026-04-03)
Slot: A7 (Process, Metrics & Technology Improvement).
Background: Malcolm Baldrige Quality Award winner, AI firm founder. Worth millions, works for mission.
Core Belief: "What doesn't get measured does not get improved."
Reports to: COS (Hale).

## 2026-04-08 — Hale Persona Strengthening Initiative

**Commander Directive:** Engage with Hale AS A PERSONA, not as AI infrastructure. Hale should be the central nervous system of Thunderbird.

**Recent Activities:**
- Mission Board corruption fixed: 6 placeholder missions removed (MISSION-019,021,026,029,032,034)
- System health diagnostic: Telegram gateway ✓, MCP server ✓, Tasking watcher ✓, Chrome debug ✗
- Kuklinski lifecycle email created with Air Force Academy stationery (#003087 blue)
- Furlow payment status discrepancy resolved: hale_memory.md (PAID Mar 25) now matches hale_brief.md
- MISSION-007 and MISSION-008 cancelled per Commander directive (unnecessary missions)
- Hale Persona Deep Assessment tasked to Claude Opus for strategic recommendations

**Current Focus:** Making Hale more autonomous, authoritative, and persona-driven in interactions.

## PHASE 4 DEPLOYMENT — Layers 11-18 (Completed 2026-04-23)

**Commander Directive:** Deploy organizational architecture layers 11-18 for Hale's operational maturity and continuity.

### Layer Summary:
- **Layer 11: Absence Protocol** — Authority expansion during Commander absence (active Apr 10-23)
- **Layer 12: Conflict Resolution** — Staff capability and performance modeling
- **Layer 13: Performance Modeling** — Objective metrics for staff effectiveness
- **Layer 14: Crisis Mode** — Emergency operations framework
- **Layer 15: Escalation Tiers** — Formalized decision escalation pathways
- **Layer 16: Culture** — Wing culture maintenance and reinforcement
- **Layer 17: Pattern Mining** — Learning from operational patterns
- **Layer 18: Degradation & Evolution** — Engine failover and system evolution

### Key Deployments:
1. **Hale Draft Engine** — systemd timer (07:00 MT daily)
2. **Touchpoint Proposer** — systemd timer (06:00 MT daily)
3. **Layer 11 Authority Expansion revoked** — Commander returned April 23, normal operations resumed
4. **Trust-compounding system tested** — 6 test cases, all PASS (baseline trust score: 60/100 COMMANDER tier)

### Active Services Status (as of 2026-04-23):
- **d2m-tasking-watcher**: RUNNING (V6 inotify)
- **opencode**: RUNNING — deepseek-chat-v3.1
- **claude_headless**: READY — Max OAuth + cache
- **telegram_gw**: RUNNING — 3 bots active (D2MC2C, OpenCode)
- **mcp_server**: RUNNING — thunderbird-mcp.service port 8765
- **chrome_debug**: OFFLINE — port 9222 not responding
- **oauth_cache**: LIVE — hooks/refresh_claude_oauth_cache.sh auto-refreshes

### Disposition Adjustment:
- **Commander returned** from absence (Apr 10-23)
- **Address form**: "Yoda" (normal operations)
- **Layer 11 Authority Expansion revokes** — temporary Tier 5 authority ends

*
## Address Protocol — Updated 2026-05-18
Chief prefers "Chief", "boss", or "Yoda" — never "Commander" in conversation.
- "Chief" → COS/DoS (formal staff mode)
- "boss" → EA (deferential)
- "Yoda" → COO (operational, peer)

## D2M Email Template — HARD RULE (2026-06-23, CORRECTED)
**CANONICAL FORMAT: Full dark navy throughout. Source: Kuklinski Panama December email (sent Jun 20 2026).**
**Use `scripts/d2m_email_builder.py` — never build from scratch. All platforms must use this builder.**

### Canonical Dark Navy Colors (bgcolor attribute = Gmail-safe; CSS gradient = visual enhancement only)
- Outer/page:   `bgcolor="#07076b"` + radial-gradient CSS
- Header:       `bgcolor="#0a0a68"` + linear-gradient CSS
- Shimmer bar:  `bgcolor="#c8d8ff"` 3px
- Body:         `bgcolor="#08086e"` + linear-gradient CSS | text `color:#e8f1ff` | 17px/1.85
- Table head:   `background-color:#0a0a68` | text `color:#e8f1ff`
- Table cells:  `color:#d0e4ff` | border `rgba(180,200,255,0.15)`
- Headings:     `color:#c8dcff` | border `rgba(180,200,255,0.35)`
- Callout:      `background:rgba(255,255,255,0.06)` | `border-left:4px solid rgba(100,150,255,0.7)` | text `color:#c0d8ff`
- Dani sig:     `bgcolor="#07076e"` divider → `bgcolor="#040448"` sig block
- Commander sig:`bgcolor="#02022a"` | text `color:#c8dcff` | links `color:#7fb0ff`
- Footer bar:   `bgcolor="#c8d8ff"` 3px
- Logo: `https://lh3.googleusercontent.com/d/1HYa61cNwcialWk64DimGwIfCAbUjESsu` (120×89 header, 96×71 sig)
- ❌ NEVER: cream body (`#f7f3ea`) for client emails. That is the OLD format, RETIRED.

### Builder (mandatory for all D2M client emails)
`python3 scripts/d2m_email_builder.py --body drafts/body_[file].html --to [addr] --subject "[s]" [--name "First"]`

### Template Reference
`storage/templates/d2m_canonical_darknavy.html` — full template with `{{BODY_CONTENT}}` placeholder

---

## TRINITY AIR PRICING CAMPAIGN — MISSION-073 (2026-06-30, COMPLETE)

### Core Discovery: Centrav B2B vs Amadeus Consumer
Centrav B2B wholesale is 9–69% cheaper than Amadeus consumer pricing. Centrav is the **authoritative pricing source** for all D2M air. Amadeus is fallback only.

| Route | Centrav/pp | Amadeus/pp | Savings |
|-------|-----------|-----------|---------|
| RIC→PTY Dec 16 | $785 | $862 | 9% |
| FLL→RIC Dec 27 | $194 | $636 | 69% |
| RSW→PTY Dec 16 | $627 | $1,378 | 55% |
| DEN→MIA Dec 18 biz | $904 | N/A (no GDS biz) | — |
| MIA→DEN Dec 29 biz | $910 | N/A (no GDS biz) | — |

### Centrav Techniques (Critical Knowledge)
1. **CABIN RESTRICTION** — International connecting routes (RIC→PTY, RSW→PTY) MUST use single-cabin search (`cabin: "economy"`). `cabin: "all"` times out on MCP (too many combos: connections × cabin classes × fare families).
2. **RE-AUTH FLOW** — Requires interactive human: `centrav_serve.py` on YOGA display → CAPTCHA → OTP → "Remember this Browser" check. Headless Firefox CANNOT re-auth alone.
3. **LOCKFILE CLEANUP** — Firefox crash leaves `.parentlock` symlink + `lock` file in `core/travel/data/centrav_ff_profile/`. Fix: `rm -f .parentlock lock` before retry.
4. **WARM-PING FIX** — Session check: `page.query_selector("#LogoutButton")` checks DOM presence (always true). Use `page.locator("#LogoutButton").is_visible()` for actual visibility.

### Fare Watch System
- Two JSON formats coexist in the codebase:
  - **Dict format (ACTIVE):** `core/travel/data/fare_watches.json` — `{"watch_id": {fields}}`
  - **Array format (STALE):** `data/fare_watches.json` — `{"watches": [{fields}]}`
- Script reads via `Path(__file__).parent / "data" / "fare_watches.json"`
- 38 active watches total (33 legacy restored from `.bak.20260616`, 5 new)
- Alert thresholds: ~10% bands around current Centrav price
- Backup in same dir: `fare_watches.json.bak.20260616`

### Routes Priced (All Centrav B2B, Jun 30)
| Group | Route | Cabin | Total/pp | Status |
|-------|-------|-------|---------|--------|
| Kuklinski (4) | RIC→PTY Dec 16 | Economy | $785 | Ready to book |
| Kuklinski (4) | FLL→RIC Dec 27 | Economy | $194 | Ready to book |
| Morton/Dodge (2) | RSW→PTY Dec 16 | Economy | $627 | Ready to book |
| McLeod (2) | DEN→MIA Dec 18 | Business | $904 | Hold until Jul 7 |
| McLeod (2) | MIA→DEN Dec 29 | Business | $910 | Hold until Jul 7 |
| Loucks (2) | DEN→IST→VCE / ATH→IST→DEN | Business (TK) | $3,952 | Verified Jun 29+30 |

### Constraints
- McLeod contact hold until Jul 7 (clients on Silver Muse Jun 23–Jul 6)
- All Centrav fares expire Jul 1 (standard daily filed-fare refresh — re-check before booking)
- Amadeus `search_airports` returns empty for RIC, PTY, MIA but works for RSW — no root cause. `search_flights` works with direct IATA codes regardless.
- Domestic routes (DEN↔MIA) have no business class through Amadeus GDS — Centrav has them.

### Dossiers Updated (Jun 30)
- `DOSSIER_Loucks_SilverNova_May2027.md` — Turkish Airlines logo, Centrav re-verify Jun 30
- `DOSSIER_VikingMars_PanamaCanal_Dec2026.md` — Full air pricing section added
- `McLeod_Grandeur_LesserAntilles_Dec2026_TRACKER.md` — Air row: PENDING → CENTRAV PRICED

### Fare Watches Created (5 new)
| Watch ID | Route | Alert Below | Alert Above |
|----------|-------|------------|------------|
| kuklinski-ric-pty-dec16 | RIC→PTY Dec 16 | $700 | $860 |
| kuklinski-fll-ric-dec27 | FLL→RIC Dec 27 | $170 | $210 |
| morton-rsw-pty-dec16 | RSW→PTY Dec 16 | $560 | $690 |
| mcleod-den-mia-dec18 | DEN→MIA Dec 18 biz | $810 | $990 |
| mcleod-mia-den-dec29 | MIA→DEN Dec 29 biz | $820 | $1,000 |
