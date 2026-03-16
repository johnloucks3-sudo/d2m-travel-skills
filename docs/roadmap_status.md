# Thunderbird OS — Master Roadmap Status
## Dreams2Memories Travel, LLC
### Last Updated: 2026-03-07
### Source: Consolidated from 19 Google Drive roadmap docs + local build logs

---

## LEGEND
- DONE = Built, tested, working in production
- PARTIAL = Started or partially implemented
- NOT STARTED = Planned but no code written
- SUPERSEDED = Replaced by newer approach or no longer relevant

---

## 1. CORE INFRASTRUCTURE (DONE)

| Item | Status | Notes |
|------|--------|-------|
| MCP Server (travel_mcp_server.py) | DONE | 70 tools, stdio transport |
| PDF Ingestion Engine (thunderbird_v3.py) | DONE | OCR + Groq + Sheets |
| Google Sheets Integration | DONE | Booking Master + Daily Itinerary |
| Service Account Auth | DONE | credentials.json |
| Playwright Stealth Browser | DONE | thunderbird_browser.py |
| Google Drive Operations | DONE | thunderbird_drive.py, cached, retry, pagination |
| Gmail OAuth Integration | DONE | thunderbird_gmail.py, search/read/drafts |
| Branding Assets | DONE | Logo, Headshot, CSS brand tokens |

## 2. INTELLIGENCE MODULES (DONE)

| Item | Status | Notes |
|------|--------|-------|
| Ship Intelligence Scraper | DONE | thunderbird_ship_intel.py, Playwright Stealth |
| World Intelligence (advisories/weather/news) | DONE | thunderbird_world_intel.py |
| Ship Comparison Reports (DOCX/PDF) | DONE | thunderbird_ship_compare.py |
| Weekly Client Intelligence Reports | DONE | thunderbird_weekly_report.py |
| Tech News Monitor | DONE | thunderbird_tech_monitor.py |
| Fare Watch / Price Tracking | DONE | thunderbird_fare_watch.py, 5 MCP tools |

## 3. SEARCH & BOOKING TOOLS (DONE)

| Item | Status | Notes |
|------|--------|-------|
| Hotel Search (Hotelbeds API) | DONE | thunderbird_hotel_search.py |
| Flight Search (Amadeus API) | DONE | thunderbird_flight_search.py, compare, quote |
| Tour Search (Amadeus + Musement + portals) | DONE | Multiple sources, consumer scraping |
| Hotel Quote PDF Template | DONE | D2M branding, WeasyPrint, Jinja2 |
| Itinerary PDF Generation | DONE | itinerary_finishing_pipeline.py |
| Luxury Narrative Generator | DONE | luxury_itinerary_generator.py |

## 4. API & MOBILE ACCESS (DONE)

| Item | Status | Notes |
|------|--------|-------|
| REST API Gateway (FastAPI) | DONE | thunderbird_api.py, port 8766 |
| Cloudflare Tunnel | DONE | d2m-tunnel systemd service |
| Thunderbird HUD v3 (Mobile) | DONE | Apps Script + React, iMessage-style |
| APScheduler Daemon | DONE | thunderbird_scheduler.py, systemd service |
| 12-Persona AI Staff | DONE | thunderbird_personas.py |

## 5. APPS SCRIPT MIGRATION (DONE)

| Old AppScript | Python Replacement | Status |
|---------------|-------------------|--------|
| dreams2memories_ship_intelligence.gs | thunderbird_ship_intel.py | DONE |
| D2M_Ship_Compare | thunderbird_ship_compare.py | DONE |
| Intel_Command / Intel_Expansion | thunderbird_world_intel.py | DONE |
| AllegiantFareTracker.gs | thunderbird_fare_watch.py | DONE |
| Ramrod Chat Interface | Thunderbird HUD v3 | SUPERSEDED |
| EARA Apps Script triggers | Python scheduler + MCP | SUPERSEDED |
| 0_Thunderbird_Command.gs | travel_mcp_server.py | SUPERSEDED |

---

## 6. CLIENT LIFECYCLE AUTOMATION (NOT STARTED)

These items appear in multiple roadmaps (Feb 7, Feb 9, Feb 19, Feb 27, Jan 22) and represent the biggest gap.

| Item | Status | Source Doc |
|------|--------|-----------|
| Anchor Date / T-minus Timeline | NOT STARTED | EARA Roadmap, Staff Ideas, Action Plan V3 |
| Welcome Kit (auto-generated) | NOT STARTED | Staff Ideas (A6), Action Plan V3 Phase III |
| Bon Voyage Dossier (T-21 days) | NOT STARTED | Staff Ideas (A6), Action Plan V3 Phase III |
| Pre-Cruise Gift trigger | NOT STARTED | Action Plan V3 Phase III |
| Insurance reminder trigger | NOT STARTED | Action Plan V3 Phase III |
| Welcome Home follow-up | NOT STARTED | EARA Roadmap (A3) |
| Client Life-Cycle Protocol (10 touchpoints) | NOT STARTED | EARA Roadmap (A6) |
| VIP Arrival Email automation | NOT STARTED | Tools Summary (Jan 21) |

### Why This Matters
The T-minus system would automate:
- T-270: Verify deposit, insurance waiver
- T-150: Audit air routing, pre-cruise hotel window
- T-120: Book specialty dining
- T-90: Collect final payment, commission audit
- T-21: Generate final itinerary docs
- T-0: "Client on ship" calendar event
- T+1: Satisfaction check-in
- T+10: Welcome home, future cruise credit offer

## 7. QUOTE & PROPOSAL ENGINE (NOT STARTED)

| Item | Status | Source Doc |
|------|--------|-----------|
| Sheets-to-Slides Quote Engine | NOT STARTED | Staff Ideas (A9), EARA Roadmap |
| Master Quote Sheet | NOT STARTED | Task Prioritization Roadmap |
| One-click Proposal PDF Builder | NOT STARTED | Phased Implementation Plan Phase 1 |
| Pricing Database sheet | NOT STARTED | Phased Implementation Plan |

### Notes
The hotel quote PDF template (d2m_hotel_guide_schema.py) exists and works for hotels.
Could be extended to cruise/flight proposals. The Slides approach may be superseded
by the working WeasyPrint PDF pipeline.

## 8. COMMISSION & FINANCIAL (NOT STARTED)

| Item | Status | Source Doc |
|------|--------|-----------|
| Commission Audit Trigger (T+30) | NOT STARTED | Staff Ideas (A4), Task Prioritization |
| Revenue Pipeline Dashboard | NOT STARTED | Phased Plan Phase 4, Staff Ideas (COS) |
| Looker Studio integration | KILLED — Sheets dashboard sufficient at scale | Staff Ideas (COS War Room) |
| API Cost Tracking | NOT STARTED | Phased Plan Phase 0 |

## 9. AI & RAG ENHANCEMENTS

| Item | Status | Source Doc |
|------|--------|-----------|
| Client Dossier (Sheets-based preferences) | NOT STARTED | A12 Roadmap Review 2026-03-06 |
| Anticipation Engine (pre-trip content drip) | NOT STARTED | A12 Roadmap Review 2026-03-06 |
| Client Newsletters / Briefs | NOT STARTED | A12 Roadmap Review 2026-03-06 |
| Pinecone Vector Database | KILLED — revisit at 100+ bookings | Phase 4 Tech |
| Vertex AI / GCP Grounding | KILLED — Claude + Groq sufficient | Staff Ideas (A5) |
| LlamaIndex RAG (chat with PDFs) | KILLED — revisit at 100+ bookings | Phase 4 Tech |
| Instructor (structured JSON) | KILLED — not needed at current scale | Phase 4 Tech |
| LangChain Agents | KILLED — unnecessary framework complexity | Phase 4 Tech |
| AutoGen Multi-Agents | KILLED — unnecessary framework complexity | Phase 4 Tech |
| Ollama Local LLMs | KILLED — Claude + Groq sufficient | Phase 4 Tech |

## 10. MARKETING & SOCIAL (NOT STARTED)

| Item | Status | Source Doc |
|------|--------|-----------|
| Auto-draft social posts on trip complete | NOT STARTED | Staff Ideas (A8) |
| Gmail star -> auto-create contact | NOT STARTED | Staff Ideas (A5 Headhunter) |
| GTM webhooks for "Book Now" alerts | NOT STARTED | EARA Roadmap (A9) |

## 11. NOTIFICATIONS & COMMUNICATIONS (NOT STARTED)

| Item | Status | Source Doc |
|------|--------|-----------|
| SMS/WhatsApp via Twilio | DONE | thunderbird_sms.py + thunderbird_whatsapp.py (sandbox) |
| Hold expiring nudges | NOT STARTED | Phased Plan Phase 2 |
| QA tone/policy checker | KILLED — solo operator, you ARE the tone | Phased Plan Phase 5 |
| DOCX-driven playbooks | KILLED — CLAUDE.md IS the playbook | Phased Plan Phase 7 |
| Client Portal (read-only itinerary page) | NOT STARTED | Phased Plan Phase 8 |

## 12. VISUAL & DESIGN

| Item | Status | Source Doc |
|------|--------|-----------|
| FLUX.1 / Imagen 3 AI imagery | KILLED — real supplier photos preferred | Action Plan V3 Phase II |
| Canva API integration | NOT STARTED | Phase 4 Tech |
| Outside Agents Portal integration | NOT STARTED — host agency, keep exploring | Action Plan V3 Phase II |

## 13. SUPERSEDED / DEAD WEIGHT

| Item | Why | Recommendation |
|------|-----|----------------|
| Apps Script trigger system | Replaced by Python MCP + scheduler | REMOVE from roadmaps |
| Ramrod Chat Interface | Replaced by Thunderbird HUD v3 | REMOVE |
| 0_Thunderbird_Command.gs | Replaced by travel_mcp_server.py | REMOVE |
| Unito sync to Trello/Asana | MCP + HUD approach is better | REMOVE |
| Outside Agents Portal | No clear value vs existing PDF pipeline | DEPRIORITIZE |
| Looker Studio dashboard | Overkill at current scale | DEFER to Phase V |
| Windsor.ai supplier scanning | Niche, low ROI | DEFER |
| Nano Banana 2 imagery | Unclear tooling status | DEFER |

---

## PRIORITY RECOMMENDATIONS (updated 2026-03-06 — A12 Roadmap Review)

### Tier 0 — Recently Completed (2026-03-07)
1. **Dining/Experience Curation Pipeline** — DONE. `thunderbird_dining.py` — Groq research + branded PDF render. Tested Stockholm. MCP tools: `dining_research`, `dining_render_proposal`.
2. **Persona Code Update** — DONE. 9-persona roster wired into `thunderbird_personas.py`. Legacy ID mapping (A1->COS, etc.). Rich backstories + Two Pillars in all prompts.
3. **Browser Login Handoff** — DONE. Persistent profiles in `~/Thunderbird/browser_profiles/`. MCP tools: `browse_login`, `browse_list_profiles`. `browse_url`/`browse_and_click` accept `profile` param.
4. **Star Protocol v3** — DONE. Green Star replaced by self-email `[PERSONA]` routing. Draft replies on thread.
5. **Restaurant Image Cache** — DONE. `~/Thunderbird/restaurant_images/` created.

### Tier 0 — Still In Progress
6. **render_proposal() Pipeline** — One-command proposal generation (image source → HTML → PDF → Gmail draft → Drive archive)
7. **Gmail Draft Management** — Add delete_draft / replace_draft tools to avoid clutter

### Tier 1 — Build Now (client experience + revenue)
7. **T-minus Client Lifecycle** — Anchor date automation, 10 touchpoints T-270 to T+10, Commission Audit as T+30 touchpoint
8. **Client Dossier** — Sheets-based preference memory per client (room prefs, allergies, anniversaries, favorites)
9. **Client Newsletters / Briefs** — Regular curated travel intel sent to clients
10. **Anticipation Engine** — Pre-trip content drip starting T-90 (destination videos, wine recs, playlists, history)

### Tier 2 — High Value (conversion + operations)
11. **Master Proposal PDF** — Combined flight+hotel+tour+cruise in one document, one "yes"
12. **Referral Automation** — Post-trip referral touchpoint, track referrals, handwritten thank-you cards
13. **One-Call Close Workflow** — Orchestrate search→quote→email in a single client call
14. **Outside Agents Portal** — Better integration with host agency

### Tier 3 — Future
9. Revenue dashboard (simple Sheets-based)
10. SMS/WhatsApp production (Twilio Business approval)
11. Social media auto-posting
12. Canva API integration

---

## DRIVE DOC INDEX (for reference)

| Doc Name | Drive ID | Date |
|----------|----------|------|
| THUNDERBIRD OS PHASE 4 | 1QTkHA0VFd0wKKiBs-W9JvVFhAkKr3xQBnuTjO0iSciA | Mar 4 |
| Complete Project Summary | 18WjwXBuxeDpJl4VIspx9dOlTq9TNh3S4OGVoFCieSOw | Mar 4 |
| THUNDERBIRD OS v4 | 17jwBnGVr1kfpT0BzMGB5g9cvPRlkm-jt9E1Owv6gz94 | Mar 4 |
| V2.1 Roadmap | 1zEieIwgwrI7gUNNetBpQPV1-6A9tQmwXlrjcZ6i1otE | Feb 28 |
| D2M Action Plan V3 | 16W3v5r71g1us5NYoQ8uvRKHj3OLOfAjho0kMpq_vDzk | Feb 27 |
| MCP Travel Agent Plan | 1SeuI0F-wq4V7XBOTQuteOxi--Imko0xWBF484mObmhA | Feb 21 |
| 3rd Party Add-ons | 1PUrcBHq6aGA8cjwGXsZz-X8jdaJH-vui8WhnFyOSySU | Feb 20 |
| AI Roadmap for Travel | 1wPe3Cns6_OkAZWSYqLb0Rgh7xOaekbOwHs3vEF6oWuc | Feb 20 |
| Groq API Integration | 1qJSa-xMtPY7PkcZzArQ19Tdl1sMSKpCydMElnvj7eJc | Feb 20 |
| Groq Offerings | 1DY_Zm_a8fExqfVXgVY8pJWJ2XI3b99Abl6IvR1XLA6M | Feb 20 |
| Trigger Fix & Staff Roadmap | 1hRRL9OEfe3wFcXtYaL0k6KjoxwOAAhdi3DAK_HRfnnM | Feb 19 |
| AI Roadmap Task Prioritization | 1AQlXVRwB9pxhBjgDXhOq7ht6sygaWUDIqnRzpJWlBKw | Feb 19 |
| Staff Ideas & Roadmaps | 13olYbLv_dpT3qhmefIkAlT5nYfgchbYGTZbr_zwv6ho | Feb 9 |
| EARA Roadmap | 100kp8_SsGm5N30pSyIi0FVGgNa-U2_GKmVBHTp7UqTo | Feb 7 |
| TITAN Implementation Plan | 1QSa6PrggA4vRgjzkmuPFXy2IPTYdlOWCDI2F6lxiuls | Feb 8 |
| Phased Implementation Plan | 1lAb1GCKKDpFBHoebN5LBQuSkrCWAA5AlvT18GYQ_F3E | Jan 22 |
| Tools Summary | 1ciwyjfqb59vANIm_bA6qPzzDGfywoIeGFetcQNuITMk | Jan 21 |
| Claude D2M Chat Interface | 1KLKfA1Nz1oxiAeb9JbkwsPtkRpLcomeSBf-1YCN9H2E | Feb 13 |
| Operation Titan Initiation | 1pHxCA5yyibkpxyxvCQ8wpsfVPyuZuTDysVIwkL_I0bM | Feb 16 |
