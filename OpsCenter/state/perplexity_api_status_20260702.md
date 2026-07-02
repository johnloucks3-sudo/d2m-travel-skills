# MISSION-438 — Perplexity API Key Diagnosis
**A7 Sterling | 2026-07-02 | Status: PENDING_COMMANDER**

---

## Finding

The key in `.env` begins `pplx-TbGO...` (added 2026-06-14, full value redacted from this report — visible in `.env` line `PERPLEXITY_API_KEY`).
HTTP probe against `api.perplexity.ai/chat/completions` returns **401 Unauthorized** — key is revoked or expired. Consistent with ELON fleet 401 logs first logged 2026-06-24.

Key is NOT in Infisical (no `.infisical_token` or `.infisical_project_id` on disk — Infisical self-hosted but not configured for secrets injection here). Single source of truth is `.env`.

---

## Key Location

| Location | Path | Notes |
|---|---|---|
| Primary | `/home/john/Thunderbird/.env` line `PERPLEXITY_API_KEY=pplx-TbGO...` | Only copy |
| Infisical | Not present | No project binding found |
| Environment | Loaded at runtime from `.env` by `_get_key()` in `core/search/perplexity_search.py` | |

---

## Dependent Scripts (5 production consumers)

| Script | Use |
|---|---|
| `intel/daily_search/thunderbird_daily_search.py` | Daily intel sweeps (ELON fleet) |
| `intel/daily_search/daily_intel_runner.py` | Orchestrates daily search waves |
| `intel/cruise_line_intel_sweep.py` | Cruise line competitive intel |
| `core/ci/ci_auto_repair_engine.py` | CI auto-repair lookups |
| `scripts/ai_price_fetcher.py` | AI price lookup fallback |

All 5 are non-blocking failures with Serper fallback active, per prior MISSION-438 note. Quality degrades but Wing does not halt.

---

## Commander Action Required

1. Go to **https://www.perplexity.ai/settings/api**
2. Delete or ignore the old key (`pplx-TbGO...`)
3. Click **Generate** → copy the new `pplx-...` key
4. On YOGA, edit `.env`:
   ```
   PERPLEXITY_API_KEY=pplx-<new-key-here>
   ```
5. No service restart required — key is loaded per-call from `.env`

**Estimated time: 3 minutes.**

---

## Success Metric

Post-replacement test:
```bash
python3 -c "from core.search.perplexity_search import search; print(search('test', max_results=1))"
```
Expected: list with 1 result dict, no exception. Threshold: HTTP 200 within 10 seconds.

**Measurement cadence:** Next daily intel sweep will confirm (runs 0900 MT daily via `daily_intel_runner.py`).

**Owner:** Commander (key generation) → A7 (verification after update)
