# Google AI Pro / Gemini Integration — Status

**Mission:** MISSION-127 (P1) · **Owner:** HALE/Sterling (A7)
**Last verified:** 2026-06-11 · **Subscription:** Google AI Pro (~$20.60/mo)
**Verdict:** Direct-API path GREEN and verified. File API (PDF) GREEN and verified. One bug found and fixed. Only remaining work is NotebookLM, which requires Commander action (cannot be automated).

---

## What was verified this session

| Component | File | Result |
|---|---|---|
| Direct Gemini API (text) | `core/ai_infra/gemini_client.py` | ✅ PASS — live smoke test returned `THUNDERBIRD_OK` |
| File API (PDF native read) | `core/ai_infra/gemini_file_reader.py` | ✅ PASS — uploaded a real PDF, got a correct one-sentence summary |
| Flash adapter wiring | `core/ai_infra/adapters/google_gemini_flash.py` | ✅ routes through `gemini_client` (no direct API calls); parses clean |
| Router tier registration | `core/ai_infra/thunderbird_model_router.py` | ✅ `GEMINI_LARGE_CONTEXT` tier registered, assigned to Dembe for PDF/destination research |
| Safeguards / cost guard | `core/learning/model_safeguards.py` | ✅ `gemini` / `gemini_lite` models registered with pricing |
| API key present & valid | `.env` → `GOOGLE_AI_API_KEY` | ✅ valid `AIzaSy...` key (39 chars); legacy alias `GEMINI_API_KEY` also present |

**Key delivery to production callers:** `task_processor.py` loads via `load_dotenv(.env)`; systemd service units load the same `.env` via `EnvironmentFile`. No gap.

---

## Architecture

`gemini_client.py` is the **single chokepoint** for all Gemini text calls. Three tiers map to the Claude tiers:

| Function | Model | Equivalent | Free-tier limits |
|---|---|---|---|
| `call_gemini()` | `gemini-2.5-flash` | Sonnet | 15 RPM / 1M TPM / 1500 RPD |
| `call_gemini_lite()` | `gemini-2.5-flash-lite` | Haiku | higher RPM, lower quality |
| `call_gemini_pro()` | `gemini-2.5-pro` | Opus | 5 RPM / 250K TPD |

Guards enforced on every call: free-tier allowlist (non-allowlisted models require `GEMINI_PAID_TIER_APPROVED=true`), rate limiting (`GEMINI_INTER_CALL_DELAY`), and Harlan usage logging to `core/ai_infra/data/gemini_usage.jsonl`. `_lite` and `_pro` auto-fall-back to flash on failure.

`gemini_file_reader.py` provides native PDF/document reading (up to 1M tokens, no chunking) via the Google AI File API. Used by Dembe (A2) for cruise brochures, hotel listings, tour guides, rail schedules. Files persist 48h on Google servers, max 2 GB. Entry points: `ask_about_pdf()`, `extract_from_pdf()`, `batch_extract()`.

---

## Bug found & fixed this session

**Symptom:** `ask_about_pdf()` / `extract_from_pdf()` returned `RuntimeError: Empty response from gemini-2.5-pro` on short questions.

**Root cause:** `gemini-2.5-pro` (the file reader's default model) spends a variable, sometimes large "thinking" budget before emitting output — observed consuming up to ~509 tokens. With a small `max_tokens` (e.g. the original default of some call paths, or 80 in testing), the thinking budget consumed the entire output window, leaving `finishReason=MAX_TOKENS` and no text.

**Fix (`gemini_file_reader.py`, `ask_about_pdf`):**
1. Floor `max_tokens` to 1024 so output always has room.
2. Cap thinking via `generationConfig.thinkingConfig.thinkingBudget = 256` so thoughts can't eat the whole window.
3. Improved the empty-response error to report `finishReason`, `thoughtsTokenCount`, and `maxOutputTokens` — so any future occurrence is self-diagnosing.

**Verified:** the previously-failing `max_tokens=80` call now returns a correct answer.

---

## How to use

```python
# Text (Sonnet/Haiku/Opus equivalents)
from core.ai_infra.gemini_client import call_gemini, call_gemini_lite, call_gemini_pro
text = call_gemini("You are Dani.", "Draft a welcome email.", caller="dani")

# PDF native read (Dembe / research)
from core.ai_infra.gemini_file_reader import ask_about_pdf, extract_from_pdf
answer = ask_about_pdf("/path/brochure.pdf", "What specialty dining requires reservations?")
data   = extract_from_pdf("/path/brochure.pdf", extract_type="cruise_brochure",
                          voyage_name="Silver Muse Mediterranean")
```

**Smoke test (run any time the key changes):**
```bash
/home/john/Thunderbird/.venv/bin/python core/ai_infra/gemini_client.py   # → [PASS]
```

---

## STILL NEEDS COMMANDER ACTION (cannot be automated)

- [x] **Drive source corpus staged 2026-07-05** — folder `Thunderbird NotebookLM Source Corpus` created in Drive (id `1pU1Ru7dnBj_AN9OvKWPz_EK39ZBoenVd`), two subfolders populated: `Standing Orders` (all 37 current SOs, for Sterling/Harlan primary-source grounding per Rule 1/Rule 3) and `Destination Research (Brochures, Port Guides)` (3 Silversea tour programme PDFs + the Regent Insider Tips Guide). Ready for one-click "Add sources → Google Drive → this folder" once the notebook exists.
- [ ] **NotebookLM D2M workspace** — set up at <https://notebooklm.google.com>. NotebookLM has no public API; creating the notebook and linking the Drive folder above are the only remaining manual Commander steps (~2 min): (1) New Notebook → (2) Add source → Google Drive → select `Thunderbird NotebookLM Source Corpus` (pulls in both subfolders) → (3) name it "Thunderbird Wing". Intended users: Dembe (A2) for destination/brochure research, Sterling/Harlan for primary-source fact verification. *This is the only open item on MISSION-127 that the Wing cannot finish autonomously — no login delegation possible.*
- [x] **Google Sheets MCP wire — verified 2026-07-05.** `api/thunderbird_sheets_mcp.py` (`thunderbird_google_auth.get_sheets()`) was already built; confirmed live end-to-end against the Booking Master spreadsheet: `sheets_list_sheets` (25 tabs), `sheets_read_data` (Booking Master + Wing_Dashboard), `sheets_append_row` (proof row in `Action_Tracker!A811`). No code changes needed — prior "IN PROGRESS" status was stale. MISSION-127 closed.
  - **Open finding (not fixed here, routed to Harlan):** `Wing_Dashboard` tab reports D2M Share **$30,117.57**, which does not match the Harlan-verified pipeline figure of **$18,830.93** in `hale_state.json` (same naive flat-rate bug identified in MISSION-426). This is a third stale commission-total source — same family as the open `MISSION-1540` (Harlan: correct stale `fpd_status` in KNOWN_BOOKINGS).

---

## Free-tier / cost notes

- All three default models are on the free tier of the D2M Python Pipeline GCP project. Paid/experimental models are code-blocked unless `GEMINI_PAID_TIER_APPROVED=true`.
- Every call is logged for Harlan tracking (`data/gemini_usage.jsonl`, `data/gemini_file_usage.jsonl`).
- This integration is a **fallback path** when Claude limits are approached — not the primary engine.
