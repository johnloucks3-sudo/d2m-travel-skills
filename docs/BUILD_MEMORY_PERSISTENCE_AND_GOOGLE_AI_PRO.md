# BUILD RECORD — Memory Persistence, Staying Time, and Google AI Pro Integration
## Thunderbird Wing · 2026-06-05 · A7 Sterling, HALE, ELON, DEMBE

---

## WHAT WAS BUILT

### 1. HALE Memory Persistence + Staying Time (4 Critical Fixes)

**Root cause:** HALE was loading cold every session despite 2+ months of infrastructure investment.
Four systems were built but broken or disconnected.

#### Fix 1 — `OpsCenter/auto_session_monitor.sh`
- **Problem:** Service was failing every 10 minutes (status 203/EXEC) for 2.5 months. The script it called did not exist.
- **Fix:** Rewrote the monitor. Now: detects active sessions (`pgrep -c`), checks Qdrant health, reads active task count, appends heartbeat to `Personas/memory/COS/session_notes.md`, **regenerates session context blast hourly**.
- **pipefail safety:** Session count check wrapped to suppress false non-zero exits.

#### Fix 2 — Qdrant Health Check Endpoint
- **Problem:** Monitor checked `/health` (404). Correct endpoint is `/collections` (200). Qdrant was always UP but reported as DOWN for 2+ months.
- **Fix:** Health check updated to `/collections` in both `auto_session_monitor.sh` and `core/memory/qdrant_memory.py`.
- **State:** Qdrant running, 221 files / 448 chunks indexed. Collection: `thunderbird_memories`.

#### Fix 3 — Mission Board Task Count
- **Problem:** Monitor read `tasks` key; mission board uses `missions` key. Always reported 0 active tasks.
- **Fix:** Monitor now reads `missions` key. Correctly surfaces 56 active missions.

#### Fix 4 — `core/memory/session_context_blast.py` (NEW FILE)
- **What it does:** Queries Qdrant (semantic search) + mission board (P0/P1 active) + `hale_state.json` (project tracking, financial pulse, WF-17 gate) → writes `OpsCenter/session_context_latest.md`.
- **Wired into:** `CLAUDE.md` `@` auto-load — every new session gets a dynamic, project-aware brief instead of stale static text.
- **Auto-triggered by:** `auto_session_monitor.sh` hourly, and `systemd` timer daily at 05:30 MT.
- **Usage:**
  ```bash
  python3 core/memory/session_context_blast.py
  python3 core/memory/session_context_blast.py --query "Kuklinski dining"
  python3 core/memory/session_context_blast.py --top-missions 10
  ```

#### Side effect — MEMORY.md compression
- Compressed from 235 → 160 lines. Below the 200-line truncation limit. Critical entries at the bottom (Qdrant, OC MAX config, scraping intel) are now always visible.
- Added `Memory System` section documenting Qdrant + session blast locations.

---

### 2. Google AI Pro Integration

**Trigger:** Commander subscribed to Google AI Pro ($20.60/mo) — Gemini 2.5 Pro, NotebookLM Plus, 5TB Drive, AI Inbox.

#### `core/ai_infra/adapters/google_gemini_flash.py` — Re-enabled
- Was disabled 2026-05-29. Re-wired through canonical `gemini_client.py` (rate limits, Harlan logging, allowlist enforcement).
- Allowlist: `gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-2.5-pro`.
- `GEMINI_PAID_TIER_APPROVED` flag gates any non-allowlist model. Currently `false`.

#### `core/ai_infra/thunderbird_model_router.py` — GEMINI_LARGE_CONTEXT tier added
- New tier: `GEMINI_LARGE_CONTEXT` — Gemini 2.5 Pro direct API, 1M context window.
- **Auto-routing:** Any task with `content_size > 100_000` tokens routes here automatically.
- **A2/Dembe upgraded:** Default model tier for Dembe is now `GEMINI_LARGE_CONTEXT`. Full cruise brochures in one shot instead of chunked scrapes.
- **New dispatch helper:** `call_gemini_large_context(task, content, context_size_hint)` available to all personas.

#### `core/ai_infra/gemini_file_reader.py` — NEW FILE
- **What it does:** Upload any PDF/document to Google AI File API → Gemini reads natively (up to 1M tokens) → returns structured JSON.
- **No chunking, no preprocessing.** Entire cruise brochure in one API call.
- **Supported extract types:**
  | Type | Output |
  |------|--------|
  | `cruise_brochure` | Dining venues, excursions, ports, cabin categories, inclusions |
  | `hotel_listing` | Room types, amenities, dining, location, pricing tiers |
  | `tour_guide` | Activity options, timing, group sizes, booking requirements |
  | `rail_schedule` | Routes, departure times, classes, reservation requirements |
  | `generic` | Raw summary + key facts |
- **File API notes:** Files persist 48h on Google servers (auto-deleted). Max 2GB. No additional cost.
- **Usage:**
  ```python
  from core.ai_infra.gemini_file_reader import extract_from_pdf, ask_about_pdf

  data = extract_from_pdf("/path/to/silversea_med.pdf", extract_type="cruise_brochure",
                          voyage_name="Silver Muse Mediterranean")

  answer = ask_about_pdf("/path/to/brochure.pdf",
                         "What specialty dining venues are available?")
  ```

---

### 3. Missions Added to Board

| Mission | Title | Status | Deadline |
|---------|-------|--------|----------|
| MISSION-127 | Google AI Pro Integration | IN_PROGRESS | — |
| MISSION-128 | Spencer Air Quote | IN_PROGRESS | 2026-06-10 |

---

## ELON CAPABILITY AUDIT — Full Findings

The ELON audit identified 10 dormant/underexploited systems:

| # | System | Now |
|---|--------|-----|
| 1 | Qdrant semantic memory | FIXED — running, queried at session start |
| 2 | `thunderbird_shared_memory.py` Mem0 | Available — needs active use in personas |
| 3 | Persona memory dirs (`Personas/memory/`) | WRITTEN — COS session notes current |
| 4 | `auto-session-monitor.service` | FIXED — runs clean every 10 min |
| 5 | `thunderbird_session_checkpoint.py` | Available — not yet wired to monitor |
| 6 | Mission board (56 active missions) | FIXED — correct key read |
| 7 | Commander Directive Sweep service | Available — not yet activated |
| 8 | `mcps/` (apify, foursquare, mapbox, yelp) | Downloaded — not yet in mcp.json |
| 9 | `thunderbird_multi_agent.py` | Available — unused |
| 10 | `context7` MCP | In mcp.json — unused |

---

## REMAINING ACTIONS (STERLING BACKLOG)

1. **Persona memory active use** — Wire Mem0 `wing_memory_add` / `wing_memory_search` into session flows
2. **checkpoint integration** — Wire `thunderbird_session_checkpoint.py` into monitor for mid-session state saves
3. **NotebookLM Plus workspace** — Commander must create at `notebooklm.google.com` and upload cruise PDFs. After that, Dembe workflow wiring can proceed.
4. **Google Sheets MCP** — Commission tracking sheet accessible via Drive MCP today; dedicated Sheets MCP would improve structured reads

---

## BILLING SAFETY NOTE

| Bucket | Rate | Risk |
|--------|------|------|
| Google AI Pro subscription | $20.60/mo flat | None — no overages |
| Gemini API (GCP project "D2M Python Pipeline") | Free tier | Monitor at `console.cloud.google.com` |

Local call log: `core/ai_infra/data/gemini_usage.jsonl` — every Gemini API call logged with model, tokens, cost tier.

---

*Build record authored by Hale / Sterling — 2026-06-05*
