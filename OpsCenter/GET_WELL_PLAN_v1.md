# THUNDERBIRD GET-WELL PLAN v1.0
## COL Victoria "Iron Vic" Hale, COS — 2026-04-04 07:25 MT

> *"Fix foundations. Arm the staff. Ship the system."*

---

## EXECUTIVE ASSESSMENT
**Overall Status:** 🟡 YELLOW — Functional but degraded

Thunderbird is alive and capable, but suffering from degraded services, missing pipeline, and sprawl.
Core architecture (Watcher v3 + MCP + headless spawn) is **solid**. The failures are fixable.

**Strengths:**
- Watcher v3 (inotify + headless spawn) zero-code task routing — WORKS
- MCP connector healthy (Port 8767 full Travel MCP with OSINT)
- All 5 email conditioning JSONs well-designed and ready
- Background tasks functional (worldwide intel sweep completed)
- 180+ Python scripts = rich capability (but needs pruning)

---

## 🔴 CRITICAL — Fix Within 24 Hours

| # | Issue | Status | Fix | Owner |
|---|-------|--------|-----|-------|
| 1 | **Email Maintenance Engine** — old script uses broken `mcp_bridge.sh` | ⚠️ Stub needs rewrite | Rewrite with direct MCP tool usage | **Hale** |
| 2 | **FPD Alert FAILED** — `status=203/EXEC` | ⚠️ 19 min down | Fix exec path / .venv Python, restart | **Hale/A12** |
| 3 | **Git Watchdog FAILED** | ⚠️ Down | Find error, restart | **Hale/A12** |
| 4 | **Scheduler auto-restart** | ✅ Running (07:22) but fragile | Verify stability 24h, check logs | **A12** |
| 5 | **Grok API 403 — zero credits** | ⚠️ Every scan fails | Remove from sweep paths, use MCP/Web | **A2** |

## 🟡 HIGH — Fix Within 72 Hours

| # | Issue | Fix | Owner |
|---|-------|-----|-------|
| 6 | **25 stale Gmail drafts** (test artifacts mixed with real) | Archive tests, keep client-facing | **EXEC** |
| 7 | **Incubator degeneration** (empty categories → garbage queries) | Validate min query length, skip empties | **A12** |
| 8 | **Credential security** (plaintext .env, no file perms) | chmod 600, isolate Personal/Credentials | **Hale** |
| 9 | **No health dashboard** | systemctl summary → Telegram | **A12** |
| 10 | **Learning Compiler underutilized** | Enable diff→principle auto-capture pipeline | **EXEC** |

## 🟢 MEDIUM — Fix Within 1 Week

| # | Issue | Fix | Owner |
|---|-------|-----|-------|
| 11 | **180+ .py files, no organization** | Archive dead code, sort by domain | **A2** |
| 12 | **A2A protocol untested** | Full COS→persona→response flow test | **A5** |
| 13 | **Temporal memory gaps** | Populate remaining client prefs from dossiers | **A3** |
| 14 | **Grant compiler** | Complete SBIR/STTR narrative for submission | **A12** |
| 15 | **Competitive surveillance** | Schedule weekly, feed to A2 memory | **A2** |
| 16 | **Innovation scanner** | Schedule daily + weekly cron | **A12** |
| 17 | **Hale Blueprint coordination** | Validate flow with all staff | **Hale** |

---

## SUCCEED / FAIL CONDITIONS
**SUCCEED:** All 17 done, 🟢 GREEN for 7 consecutive days, Commander reports "zero manual intervention" for 48h.
**FAIL:** Any 🔴 unresolved >72h, OR Commander manually tasks something the system should have caught.

---
*Plan v1.0 — Hale, COS | Awaiting Commander approval*
