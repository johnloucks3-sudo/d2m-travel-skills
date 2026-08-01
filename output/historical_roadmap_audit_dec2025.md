# Historical Roadmap & Capability Archeology Audit (Dec 2025 – Aug 2026)

## Executive Summary
Audited 238 roadmap, specification, and memory documents across EARA, TITAN, and Thunderbird Wing repositories.

### Total Capability Findings:
- **Verified Built & Live Items:** 1142
- **Open / Unbuilt / Pending Items:** 1101

---

## Key Built Capabilities (Sample Audit)
- # Test Weekly Report (Interactive)
- python thunderbird_weekly_report.py --interactive
- # Generate weekly client report (interactive)
- python thunderbird.py --weekly-report --interactive
- # Generate weekly report (non-interactive)
- # Interactive mode (easiest)
- python thunderbird.py --weekly-report --interactive
- # Non-interactive mode
- | **E-30** (1 month out) | Start - 30 | Final itinerary PDF delivered, all docs confirmed |
- - Guest Information Form: verify completed on my.silversea.com
- - DONE = Built, tested, working in production
- ## 1. CORE INFRASTRUCTURE (DONE)
- | MCP Server (travel_mcp_server.py) | DONE | 70 tools, stdio transport |
- | PDF Ingestion Engine (thunderbird_v3.py) | DONE | OCR + Groq + Sheets |
- | Google Sheets Integration | DONE | Booking Master + Daily Itinerary |

---

## Key Open / Candidate Capabilities (Sample Audit)
- Your Google Sheet (`1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU`) needs these tabs:
- ### **Step 5: Get OpenWeather API Key (Optional)**
- 1. Go to https://openweathermap.org/api
- 1. Open Task Scheduler
- schedule.run_pending()
- 3. **Get OpenWeather API key** for weather forecasts
- | **E-120** (2 months out) | Start - 60 | Pre-trip call scheduled, specialty dining opens--no this is based on invoice |
- | **Excursion_Selection_Opens** | Per supplier | Book shore excursions |
- | **Specialty_Dining_Opens** | Per supplier | Book onboard dining |
- | Feb 23, 2026 | Specialty Dining Reservations open | Invoice p5 |
- | **HARD: Specialty Dining Opens** | **Feb 23** | **PAST — verify selections made** |
- | Post-cruise Venice stay | Jul 3-6 | PENDING — hotel NOT selected (3 options evaluated) |
- - Venice hotel: STILL PENDING — Sina Centurion Palace, JW Marriott, or NH Palazzo dei Dogi
- | Insurance | Declined | Declined | Declined (CFAR question open) |
- | Jan 31, 2026 | Shore Excursions open for selection | Invoice p3 |
