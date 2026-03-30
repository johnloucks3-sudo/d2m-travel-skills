# GOOSE TASK MANIFEST — OpsCenter
**Created:** 2026-03-29 22:15 MT
**Updated:** 2026-03-29 22:30 MT
**Author:** Claude Code (Opus) on behalf of Commander
**Status:** ACTIVE — Goose should work these tasks and check them off

---

## INSTRUCTIONS FOR GOOSE

1. Work tasks in order (G1 → G3 → G4 → G5 → G6 → G7 → G8)
2. G2 is DEFERRED — skip it entirely
3. After completing each task, add a completion entry at the bottom of this file
4. Do NOT touch files marked [CLAUDE ONLY] — those need MCP access
5. Test code changes by running: `python3 /home/john/Thunderbird/OpsCenter/opscenter_test_harness.py`
6. Restart the daemon after task_processor.py edits: `systemctl --user restart thunderbird-overwatch.service`

## ⚠️ RATE LIMIT WARNING — GEMINI 2.5 FLASH
You use Gemini 2.5 Flash. The free tier is **10 RPM**. For ANY batch intel run (G4-G8),
set this env var BEFORE running scripts to avoid 429 errors:
```bash
export GEMINI_INTER_CALL_DELAY=6
```
This enforces a 6-second gap between Gemini Flash calls. The model router reads it automatically.
For interactive single calls, no delay needed.

---

## GOOSE TASKS

### G1: Fix Gemini 3.1 Pro MAX_TOKENS Failure + Retry Logic
**File:** `task_processor.py`
**Priority:** HIGH
**Problem:** Test harness shows Gemini 3.1 Pro sometimes returns empty text with `finishReason: MAX_TOKENS`. Passed on retry.

**Fix:**
1. In `_call_hale()` (line ~307), the `maxOutputTokens` defaults to 800 via parameter. The caller `_handle_commander_message()` (line ~746) passes `max_tokens=2500`. Verify this flows through.
2. Add retry logic: if response is empty or `finishReason == "MAX_TOKENS"`, retry once with `maxOutputTokens` doubled (up to 8192).
3. Add response validation: check that `data["candidates"][0]["content"]["parts"][0]["text"]` is non-empty before returning.
4. If retry also fails, fall back to `_call_gemini()` (Flash) as already coded.

**Validation:** Run test harness Phase 3 (Gemini API) — should pass consistently.

---

### G2: Fix TESS Authentication — DEFERRED
**DEFERRED to Monday 30 MAR 2026 afternoon.** Requires browser SSH + Goose ride-along with Commander for interactive OAuth. DO NOT ATTEMPT.

---

### G3: Add Log Rotation for OpsCenter Logs
**File:** `task_processor.py`
**Priority:** MEDIUM
**Problem:** `process.log`, `overwatch.log`, and `hale_chat_log.jsonl` grow unbounded.

**Fix (Python RotatingFileHandler — preferred):**
1. At top of `task_processor.py`, add:
   ```python
   from logging.handlers import RotatingFileHandler
   ```
2. Replace the manual file-append in `_log()` (line ~359) with a proper logger:
   ```python
   _file_handler = RotatingFileHandler(
       str(PROCESS_LOG), maxBytes=5*1024*1024, backupCount=5
   )
   _file_handler.setFormatter(logging.Formatter("%(message)s"))
   _process_logger = logging.getLogger("opscenter.process_log")
   _process_logger.addHandler(_file_handler)
   ```
3. Update `_log()` to use `_process_logger.info(line)` instead of raw file append.
4. Apply same pattern to `hale_chat_log.jsonl` — use RotatingFileHandler with `maxBytes=10MB, backupCount=3`.

**Validation:** After restart, verify logs are created and old logs rotate when they exceed 5MB.

---

### G4: Run Daily Innovation Scan
**Priority:** HIGH — Commander wants all intel/scanning delegated to Goose
**Script:** `python3 /home/john/Thunderbird/thunderbird_innovation_scanner.py --daily`
**What it does:** Scans tech news, AI developments, travel industry innovation. Produces digest.
**Output:** `~/Thunderbird/intel/daily_innovation_digest.md`
**After:** Send digest to Commander via Telegram C2 or queue for email to johnloucks3@gmail.com

---

### G5: Run World Intelligence Sweep
**Priority:** HIGH — All intel sweeps delegated to Goose
**Action:** Use MCP tool `run_world_intelligence_sweep` or run the underlying script directly.
**Scope:** Travel industry news, cruise line updates, airline route changes, geopolitical impacts on travel.
**Target cruise lines:** Silversea, Regent Seven Seas, Cunard, Oceania, Seabourn, Viking, AmaWaterways, Ponant
**Output:** Structured intel report per INTEL_STANDARDS.md — every source gets a clickable hyperlink.
**After:** Send to johnloucks3@gmail.com as full send (Standing Order 27 MAR 2026 — intel = full send, not draft).

---

### G6: Run Tech Monitor / Innovation News Scan
**Priority:** HIGH — All tech scanning delegated to Goose
**Action:** Use MCP tool `run_tech_monitor` or run underlying scripts.
**Scope:** AI/ML developments, travel tech, automation tools, API updates, ***REMOVED-SECRET*** news.
**Output:** Structured tech briefing with D2M relevance assessment.
**After:** Send to johnloucks3@gmail.com as full send.

---

### G8: Run Weekly Deep Innovation Scan — TONIGHT 01:30 MDT
**Priority:** HIGH — Commander order 2026-03-29
**Run at:** Mon 30 MAR 2026 01:30 MDT (tonight)
**Problem:** Weekly scan normally fires Sun Apr 5. Commander wants it tonight.

**Fix (pick one):**
```bash
# Option A — one-shot systemd-run (preferred)
systemd-run --user --on-calendar="2026-03-30 01:30:00 MDT" \
  systemctl --user start thunderbird-innovation-scan-weekly.service

# Option B — trigger manually at 01:30
systemctl --user start thunderbird-innovation-scan-weekly.service
```
**After:** Send output to johnloucks3@gmail.com as full send (not draft). Every source gets a clickable hyperlink.

---

### G7: Run Ship Intelligence Sweep
**Priority:** MEDIUM
**Action:** Use MCP tool `run_ship_intelligence_sweep` or underlying scripts.
**Scope:** New ship announcements, itinerary changes, pricing updates, cabin availability for targeted cruise lines.
**Target lines:** Silversea, Regent Seven Seas, Cunard, Oceania, Seabourn, Viking, AmaWaterways, Ponant
**Output:** Structured ship intel report.
**After:** Send to johnloucks3@gmail.com as full send.

---

## STANDING ORDERS FOR GOOSE INTEL WORK

1. **All intel reports go to johnloucks3@gmail.com as FULL SENDS** — not drafts (SO 27 MAR 2026)
2. **Send FROM d2mconcierge@gmail.com** — never create drafts in johnloucks3
3. **Every source gets a clickable hyperlink** — no exceptions
4. **Report structure:** D2M Relevance Summary → Analysis → Raw Intel (per INTEL_STANDARDS.md)
5. **Targeted cruise lines:** Silversea, Regent Seven Seas, Cunard, Oceania, Seabourn, Viking, AmaWaterways, Ponant

---

## [CLAUDE ONLY — DO NOT TOUCH]

These tasks require Claude Code MCP access. Goose must not attempt them.

- ~~**C1:** ELON/A12 — COMPLETED~~
- **C2:** Process Claude MAX queue — drain 03_CLAUDE_MAX_QUEUE.json with MCP gmail tools
- **C3:** Commit all OpsCenter changes to git (after all work complete)

---

## COMPLETION LOG

Goose: After completing each task, add an entry here:

```
[TIMESTAMP] G1 — DONE/BLOCKED/PARTIAL — Notes
[TIMESTAMP] G2 — DEFERRED to Monday 30 MAR — Commander order
[TIMESTAMP] G3 — DONE/BLOCKED/PARTIAL — Notes
[TIMESTAMP] G4 — DONE/BLOCKED/PARTIAL — Notes
[TIMESTAMP] G5 — DONE/BLOCKED/PARTIAL — Notes
[TIMESTAMP] G6 — DONE/BLOCKED/PARTIAL — Notes
[TIMESTAMP] G7 — DONE/BLOCKED/PARTIAL — Notes
[TIMESTAMP] G8 — DONE/BLOCKED/PARTIAL — Notes (deep innovation scan, target 01:30 MDT Mon 30 MAR)
```

[2026-03-29 22:54 MT] G1 — DONE — Fixed Gemini 3.1 Pro MAX_TOKENS retry logic and doubling tokens
[2026-03-29 22:54 MT] G3 — DONE — Replaced manual logging with RotatingFileHandler for both process and chat logs
[2026-03-29 22:55 MT] G8 — DONE — Scheduled weekly scan via systemd-run for 01:30 MDT tonight
[2026-03-29 22:55 MT] G4 — DONE — Ran daily innovation scan and emailed digest
[2026-03-29 22:56 MT] G5 — DONE — Ran world intelligence sweep and full-sent email
[2026-03-29 22:56 MT] G6 — DONE — Ran tech monitor and full-sent email
[2026-03-29 22:56 MT] G7 — DONE — Ran ship intelligence sweep and full-sent email
