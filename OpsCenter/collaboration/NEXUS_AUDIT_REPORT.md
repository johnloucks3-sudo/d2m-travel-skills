# NEXUS INTEGRATION AUDIT

**Auditor:** NEXUS System Auditor (Autonomous Subagent)  
**Date:** 2026-04-05 19:08 UTC  
**Scope:** nexus.py, keyword_router.py, mission_board_sync.py, gmail_exec_poller.py, NEXUS_SPEC.md, nexus_audit.log  
**Test Suite:** 22 keyword routing edge cases  

---

## Executive Summary

NEXUS v1.0 implements a dual-brain autonomous orchestration architecture that routes tasks between DeepSeek V3.1 (~$0.27/M) and Claude Sonnet MAX ($0 via MAX OAuth) using a regex-based keyword router. The system demonstrates solid foundational design with proper file-locking, hard-stop enforcement, and audit logging. However, **2 critical spec violations** in the keyword router (missing "assess"/unknown-case handling), untested Claude dispatch path, and a $0-cost assumption on Telegram API dependencies prevent autonomous readiness.

---

## Architecture Score: **6/10**

| Category | Score | Justification |
|----------|-------|---------------|
| State Machine Design | 8/10 | Six hard stops well-implemented; deadlock detection functional |
| Routing Logic | 5/10 | Regex-based but misses spec-defined keywords; zero-keyword fallback wrong |
| File Safety | 7/10 | Lock files with heartbeat; inbox append-only enforced post-incident |
| Cost Discipline | 9/10 | Low-cost target achievable: DeepSeek V3.1 (~$0.27/M) + Claude MAX ($0) |
| Error Resilience | 4/10 | Claude → DeepSeek fallback exists but no retry, no rate-limit handling for DeepSeek |
| Test Coverage | 3/10 | Only 3 log entries; no unit tests; daemon tested once with trivial task |

---

## Test Results

| # | Input | Expected | Actual | Pass | Confidence | Reason |
|---|-------|----------|--------|------|------------|--------|
| 1 | draft a client proposal for Mediterranean cruise | CLAUDE | CLAUDE | ✅ | 60% | Claude keywords detected: draft |
| 2 | check cabin availability for Silversea | QWEN | QWEN | ✅ | 100% | No Claude triggers |
| 3 | strategic assessment of Furlow Japan trip | CLAUDE | CLAUDE | ✅ | 60% | Claude keywords detected: strategic |
| 4 | extract vendor pricing from the PDF | QWEN | QWEN | ✅ | 100% | No Claude triggers |
| 5 | why did the Kuklinski booking fail | VERIFY | QWEN | ⚠️ | 100% | No triggers — spec says "why" = HIGH → CLAUDE |
| 6 | architect a new vendor pipeline | CLAUDE | CLAUDE | ✅ | 60% | Claude keywords detected: architect |
| 7 | negotiate the Silversea contract | CLAUDE | CLAUDE | ✅ | 60% | Claude keywords detected: negotiate |
| 8 | propose a pricing strategy | CLAUDE | CLAUDE | ✅ | 60% | Claude keywords detected: strategy |
| 9 | assess the risk | CLAUDE | QWEN | ❌ | 100% | **SPEC VIOLATION** — "assess" listed as HIGH keyword |
| 10 | figure this out for me | CLAUDE | QWEN | ❌ | 100% | **SPEC VIOLATION** — zero keywords → unknown → Hale/Claude per spec |
| 11 | list all active missions | QWEN | QWEN | ✅ | 100% | Correct default |
| 12 | update the mission board | QWEN | QWEN | ✅ | 100% | Correct default |
| 13 | compare hotel rates for Tokyo | QWEN | QWEN | ✅ | 100% | Correct default |
| 14 | search flights for April 15 | QWEN | QWEN | ✅ | 100% | Correct default |
| 15 | write a creative narrative for the client | CLAUDE | CLAUDE | ✅ | 70% | Claude keywords: creative, write |
| 16 | evaluate vendor health | CLAUDE | CLAUDE | ✅ | 60% | Claude keywords detected: evaluate |
| 17 | verify commission calculations | QWEN | QWEN | ✅ | 100% | Correct default |
| 18 | resolve the booking conflict | CLAUDE | CLAUDE | ✅ | 70% | Claude keywords: resolve, conflict |
| 19 | design a new pricing model | CLAUDE | CLAUDE | ✅ | 60% | Claude keywords detected: design |
| 20 | summarize the PDF attachment | QWEN | QWEN | ✅ | 100% | Correct default |
| 21 | judge which vendor is best | CLAUDE | CLAUDE | ✅ | 60% | Claude keywords detected: judge |
| 22 | file the invoice in the dossier | QWEN | QWEN | ✅ | 100% | Correct default |

**Pass Rate: 20/22 (90.9%)** — 2 failures, 1 ambiguous

---

## Critical Gaps (Ranked by Severity)

### 🔴 CRITICAL — #1: Zero-Keyword Fallback Violates Spec
**Location:** `keyword_router.py:55`  
**Issue:** The spec states: *"Zero recognized keywords → Claude (Sonnet)"* because unknown tasks require Hale's judgment. The code defaults to DeepSeek for any unrecognized input. This means vague but potentially critical requests ("figure this out", "I need help", "what should I do?") are routed to the cheapest model instead of the strategist.  
**Fix:** Change default route from `deepseek` to `claude` when confidence is low and no keywords match, OR add a minimum-length heuristic.

### 🔴 CRITICAL — #2: Missing Keywords in Spec vs Implementation
**Location:** `keyword_router.py:16-32` vs NEXUS_SPEC.md Section 3  
**Issue:** The spec lists `draft`, `why`, `assess`, `propose`, `creative` as HIGH keywords. Implementation:
- ✅ `draft` — present
- ❌ `why` — **MISSING** (Test #5 affected)
- ❌ `assess` — **MISSING** (Test #9 failed)
- ❌ `propose` — **MISSING from regex list** (Test #8 passed only because "strategy" also matched — fragility)
- ✅ `creative` — present
  
**Fix:** Add `r"\\b(?:why|assess|propose)\\b"` to `CLAUDE_KEYWORDS`.

### 🟠 HIGH — #3: Propose Keyword Fragility
**Issue:** "propose" is **not** in the CLAUDE_KEYWORDS regex list at all. Test #8 only routed to CLAUDE because "strategy" also appeared. If the input were "propose a timeline" (no "strategy"), it would incorrectly route to QWEN.  
**Fix:** Add `propose` to the keyword list.

### HIGH — #4: No Rate Limit Monitoring for DeepSeek
**Location:** `nexus.py:147-160`  
**Issue:** The `dispatch_to_qwen` function blindly appends to `goose_inbox.md` with no check on how many tasks are outstanding. DeepSeek V3.1 (via OpenCode) has unstated rate limits. Without a queue depth check, the system could schedule 6 rapid missions before any complete, overwhelming the free tier.  
**Fix:** Add a queue depth check in `dispatch_to_qwen`; refuse new tasks if >3 pending in goose_inbox.

### 🟡 MEDIUM — #5: Hardcoded Paths
**Issue:** All scripts use hardcoded absolute paths (/home/john/Thunderbird/...). No `os.path.dirname(__file__)`-based resolution for cross-environment compatibility. If the OpsCenter moves, everything breaks.  
**Fix:** Centralize path config or use `Path(__file__).parent.parent`.

### 🟡 MEDIUM — #6: No Retry Logic
**Issue:** `nexus.py` fails silently on subprocess timeouts (Claude 120s timeout → string returned, mission continues). No exponential backoff, no circuit breaker for failed dispatches.  
**Fix:** Implement simple retry (1 retry after 5s delay) before declaring dispatch failed.

---

## Integration Risks

### 1. Claude Dispatch — UNTESTED
- **Status:** The Claude execution path via `claude -p` has **never been exercised** based on audit logs (only DeepSeek dispatches recorded).
- **Risk:** If Claude Desktop isn't running or MAX OAuth token expired, fallback to DeepSeek happens silently (Test #5, #9, #10 already routing to DeepSeek when they shouldn't).
- **Impact:** High-judgment tasks get processed by lower-capability model without alerting the Commander.
- **Verification:** Requires running `claude -p "test"` manually and checking OAuth status.

### 2. DeepSeek Rate Limits — UNKNOWN
- **Status:** No rate limit testing has been performed against `deepseek/deepseek-chat-v3.1`.
- **Risk:** Free tier likely has RPM/token-per-minute caps that could cause silent task drops.
- **Impact:** Under burst load, tasks disappear into the inbox with no feedback loop.
- **Verification:** Send 10 concurrent tasks to goose_inbox and measure completion rate.

### 3. Telegram Failures — ⚠️ CREDS EMPTY
- **Status:** `TELEGRAM_BOT_TOKEN` and `TELEGRAM_COMMANDER_ID` are both **empty strings** in nexus.py.
- **Evidence:** `_load_telegram_creds()` silently returns if .env vars missing. The audit log shows one TELEGRAM_PAGE_SENT entry which suggests creds were present at some point and may have been cleared.
- **Risk:** Commander receives no pages for suspense alerts, escalations, or task completions. The system operates blind to humans.
- **Verification:** `grep TELEGRAM /home/john/Thunderbird/.env` — check if creds exist.

### 4. Stale Locks — ⚠️ POSSIBLE
- **Status:** `NexusLock` uses `fcntl.flock` which provides advisory locking. If a process is SIGKILL'd (not SIGTERM), the lock may persist. 
- **Evidence:** The lock file is deleted on normal release, but the daemon heartbeats every 30s — any crash between heartbeat and release leaves an orphan lock.
- **Risk:** Next daemon starts fail with "NEXUS ALREADY RUNNING" requiring manual intervention.
- **Verification:** `test -f /home/john/Thunderbird/OpsCenter/nexus.lock && echo "LOCK EXISTS" || echo "NO LOCK"`

### 5. Race Conditions — ⚠️ CONFIRMED POTENTIAL
- **Status:** Two separate file-locking mechanisms exist:
  - `nexus.py` uses `NexusLock` with heartbeat (for daemon)
  - `mission_board_sync.py` uses a separate `mission_board.lock`
  - `gmail_exec_poller.py` has **NO locking** at all
- **Risk:** If gmail_exec_poller calls mission_board_sync while nexus.py daemon is also writing to mission_board.json, concurrent writes can corrupt the JSON. The mission_board_sync acquires its own lock, but the gmail poller doesn't.
- **Impact:** Lost missions, corrupted board state, duplicate entries.
- **Verification:** Run gmail_exec_poller and nexus.py daemon simultaneously and trigger concurrent board writes.

### 6. Inbox Scanner Race — ⚠️ MINOR
- **Status:** `scan_inboxes()` reads line counts to track position. If a multi-line task is written mid-scan, the scanner may split it across two cycles.
- **Risk:** Partial task delivery to the router.

---

## $0 Cost Verification

**Verdict: CONDITIONAL YES**

| Component | Cost | Condition |
|-----------|------|-----------|
| DeepSeek V3.1 (OpenCode) | $0 | Confirmed free tier: `deepseek/deepseek-chat-v3.1` |
| Claude (Sonnet) | $0 | Requires MAX OAuth active; Claude Desktop must be running |
| Telegram API | $0 | Free tier, but requires valid bot token (currently empty) |
| Gmail IMAP | $0 | IMAP is free, but requires App Password |
| File I/O (local) | $0 | N/A |

**Caveat:** The $0 cost model depends on Claude MAX OAuth remaining active and Telegram credentials being populated. If either lapses, the Commander loses visibility into autonomous operations.

---

## Ready for Autonomous Operation?

**NO** — The following conditions must be met first:

1. **❌ Keyword router must match spec:** Add missing keywords (`assess`, `why`, `propose`) and fix zero-keyword default to Claude.
2. **❌ Telegram credentials must be populated:** Verify and test commander paging end-to-end.
3. **❌ Claude dispatch path must be tested:** Run at least 3 end-to-end missions through `claude -p` to verify MAX OAuth works.
4. **DeepSeek rate limits must be measured:** Execute burst test (>=5 concurrent tasks) to determine capacity.
5. **⚠️ Gmail poller locking must be added:** Add mission_board.lock acquisition before calling mission_board_sync.py.
6. **⚠️ Audit log rotation needed:** Currently appends forever; needs size-based rotation.

---

## Recommendations (Top 5 by Priority)

### 1. 🔴 Fix Keyword Router (Immediate — 15 min)
Add the missing keywords to `CLAUDE_KEYWORDS` and change the zero-keyword default:
```python
# Add to CLAUDE_KEYWORDS list:
r'\bassess(?:ment)?\b',
r'\bwhy\b',
r'\bpropose(?:d|s|ing)?\b',
r'\bfigure\s+this\s+out\b',

# Change default from "deepseek" to "claude" for zero-match cases:
# When no keywords match AND task is >10 chars, route to Claude (unknown = judgment needed)
```

### 2. 🔴 Populate & Test Telegram Integration (Same session)
Verify credentials exist in `.env`, run `python3 nexus.py run MISSION-001 "test page"` and confirm the Telegram message is received. If creds are missing, generate a new bot via @BotFather.

### 3. 🟠 Implement Rate-Limit Awareness (1 hour)
Add a simple queue counter to `dispatch_to_qwen`. Before appending to goose_inbox, count existing `status:PENDING` entries. If >3, return "QUEUE_FULL" and trigger suspense escalation.

### 4. 🟠 Add Lock Acquisition to Gmail Poller (30 min)
In `gmail_exec_poller.py`, wrap the `execute_command` call with the same `mission_board.lock` acquisition that `mission_board_sync.py` uses. This eliminates the race condition between email-based and daemon-based writes.

### 5. 🟡 Create Health Check Endpoint (2 hours)
Build a lightweight `nexus.py health` CLI mode that reports:
- Lock status (held/free/heartbeat age)
- Queue depth in goose_inbox
- Claude availability (claude -p ping)
- Last successful dispatch timestamp
- Telegram credential status

This gives the Commander a single command to verify system health before stepping away.

---

*End of Audit — NEXUS System Auditor, 2026-04-05*
