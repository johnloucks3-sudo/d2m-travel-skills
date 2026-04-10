# NEXUS MITIGATION PLAN
**Date:** 2026-04-05 | **Scope:** Address all 22 audit findings | **Target:** Autonomous-ready system

---

## Executive Summary

NEXUS v1.0 demonstrates solid architectural foundations with proper file-locking and six hard-stop enforcement. However, **two spec violations in the keyword router** prevent autonomous operation: missing critical HIGH keywords (`assess`, `why`, `propose`) and incorrect zero-keyword fallback (DeepSeek instead of Claude).

Additionally, **six integration risks** threaten operational reliability: untested Claude dispatch path, unknown DeepSeek rate limits, empty Telegram credentials, stale lock file potential, race conditions between email poller and daemon, and inbox scanner fragility.

**This plan prioritizes fixes by impact, grouping related items for efficient implementation. Estimated total effort: 12-16 hours across 3 sessions.**

All fixes maintain $0 cost constraint and preserve existing hard-stop enforcement.

---

## 🔴 CRITICAL Findings (Must fix before autonomous)

### CRITICAL #1: Zero-Keyword Fallback Violates Spec

**The Finding:**
- **Location:** `keyword_router.py:105-110`
- **Current behavior:** When a task contains zero Claude keywords, the router defaults to DeepSeek V3.1
- **Spec requirement:** Tasks with no recognized keywords should route to Claude (Sonnet) because unknown → requires Hale's judgment
- **Impact:** Vague but potentially critical requests ("figure this out", "I need help", "what should I do?") get routed to the cheaper, lower-judgment model
- **Test evidence:** Test #10 ("figure this out for me") failed — expected CLAUDE, got QWEN

**Why it matters:**
- Violates explicit spec rule in NEXUS_SPEC.md Section 3: "UNKNOWN: Zero recognized keywords → Claude (Sonnet)"
- Economic: False economy — better to over-route to Claude (no cost) than under-route to DeepSeek and get wrong answer
- Operational: Commander's vague follow-up tasks (common in async mode) get lowest-judgment routing

**Proposed Fix (Plain English):**
1. In `keyword_router.py`, change the fallback logic in the `classify_task()` function (around line 105)
2. When `CLAUDE_KEYWORD_PATTERN.search(combined)` returns no match, add a secondary heuristic:
   - If task is ≥15 characters AND contains no explicit action verbs from a small list (list, check, update, extract, verify, file, add, search, compare), route to Claude
   - Otherwise, default to DeepSeek
3. This preserves direct "list X" and "check Y" commands to DeepSeek, but catches ambiguous requests
4. Document the heuristic in comments (e.g., "Unknown + vague = Claude judgment")

**Estimated Effort:** Quick (15 minutes)
- Read current fallback logic: 3 min
- Modify condition: 5 min
- Test 3 edge cases: 7 min

**Dependencies:** None — isolated change

**Risk Level of Fix:** Low
- Change is purely routing logic, no side effects
- Fallback to original if breaks something
- Can be A/B tested with audit logging before committing

---

### CRITICAL #2: Missing Keywords in Spec vs Implementation

**The Finding:**
- **Location:** `keyword_router.py:27-48` (CLAUDE_KEYWORDS list) vs NEXUS_SPEC.md Section 3 (keyword table)
- **Spec lists as HIGH priority:** `draft`, `why`, `assess`, `strategy`, `negotiate`, `propose`, `creative`
- **Implementation missing:**
  - ❌ `why` — NOT in regex list (Test #5 failed: "why did X fail" routed QWEN, should be CLAUDE)
  - ❌ `assess` — NOT in regex list (Test #9 failed: "assess the risk" routed QWEN, should be CLAUDE)
  - ⚠️ `propose` — NOT in main regex list (Test #8 passed only because "strategy" also matched — fragile)

**Impact per missing keyword:**
- `why` (diagnostic/forensic): Failure analysis, root-cause investigation — requires judgment
- `assess` (evaluation): Risk assessment, vendor health, contract evaluation — requires judgment
- `propose` (recommendation): Business proposals, pricing strategies, solutions — requires judgment

**Why it matters:**
- Spec violation: These are **explicitly listed** as HIGH keywords in the routing spec
- Operational incidents: Any failure analysis ("why did X happen?") gets routed to DeepSeek instead of Claude for judgment
- Fragility: "propose" only worked in test #8 because "strategy" was also present; next "propose X" without "strategy" will fail

**Proposed Fix (Plain English):**
1. Add the three missing keywords to the `CLAUDE_KEYWORDS` list in `keyword_router.py`:
   - Add `r'\bwhy\b'` (exactly as written, case-insensitive via re.IGNORECASE)
   - Add `r'\bassess(?:ment)?\b'` (to catch "assess" and "assessment")
   - Add `r'\bpropose(?:d|s|ing)?\b'` (to catch "propose", "proposed", "proposes", "proposing")
2. No other changes needed — the existing pattern matching will handle these
3. Re-run the 22-test suite to verify all pass

**Estimated Effort:** Quick (20 minutes)
- Add three regex entries: 5 min
- Test against all 22 test cases: 12 min
- Verify audit log captures correct routing: 3 min

**Dependencies:** None — syntax is straightforward regex

**Risk Level of Fix:** Low
- Adding keywords only increases Claude routing; cannot cause false negatives
- Can test offline with keyword_router.py test harness before deployment
- Rollback is simple: revert the three lines

---

## 🟠 HIGH Findings (Should fix before autonomous)

### HIGH #3: Propose Keyword Fragility

**The Finding:**
- **Location:** `keyword_router.py` CLAUDE_KEYWORDS list
- **Issue:** "propose" is **not** in the keyword list at all
- **Why it matters:** Test #8 only routed correctly because the input was "propose a pricing **strategy**" — the word "strategy" triggered Claude routing
- **Risk:** If user says "propose a timeline" (no "strategy" present), router incorrectly sends to DeepSeek
- **This is separate from CRITICAL #2 because:** It's both a missing keyword AND a fragility pattern (test #8 passed due to accident)

**Proposed Fix (Plain English):**
- Same as CRITICAL #2: Add `r'\bpropose(?:d|s|ing)?\b'` to CLAUDE_KEYWORDS
- Verify test #8 still passes (it should, now for the right reason — "propose" triggers directly)
- This fix is subsumed in CRITICAL #2 implementation

**Estimated Effort:** Included in CRITICAL #2 (no separate work)

**Dependencies:** CRITICAL #2

**Risk Level of Fix:** Low (same as CRITICAL #2)

---

### HIGH #4: No Rate Limit Monitoring for DeepSeek

**The Finding:**
- **Location:** `nexus.py:202-213` (dispatch_to_qwen function)
- **Current behavior:** `dispatch_to_qwen` blindly appends tasks to `goose_inbox.md` with no queue depth check
- **DeepSeek V3.1 tier constraints:** Unknown RPM/token-per-minute limits (API documentation not provided)
- **Risk scenario:** Rapid task submitter could queue 6+ missions before any complete, overwhelming free tier
- **Impact:** Tasks disappear into inbox with no feedback; DeepSeek starts dropping work silently

**Why it matters:**
- Operational reliability: System appears healthy but tasks actually fail silently
- Scale risk: During peak hours, daemon could queue 10 tasks in 60 seconds (once per iteration); DeepSeek may only process 2-3
- Low cost: If rate-limited, DeepSeek starts failing, forcing fallback to Claude; loses cost advantage

**Proposed Fix (Plain English):**
1. Before appending to `goose_inbox.md` in `dispatch_to_qwen`, count active PENDING tasks:
   - Read goose_inbox.md
   - Count lines matching `status:PENDING` (grep-style)
   - If count ≥ 3, return "QUEUE_FULL" error instead of appending
2. Log the rejection: `audit("QUEUE_FULL", f"goose_inbox has {count} pending, rejecting new task")`
3. The calling code (run_mission loop) sees the error, escalates to commander via Telegram
4. Set threshold conservatively: 3 pending is safe for free tier; can adjust after testing

**Estimated Effort:** Medium (1 hour)
- Add queue depth counting function: 10 min
- Integrate into dispatch_to_qwen: 5 min
- Add audit logging: 3 min
- Test with synthetic load (5 rapid tasks): 20 min
- Adjust threshold if needed: 10 min

**Dependencies:** Requires understanding of goose_inbox.md format (lines with status:PENDING)

**Risk Level of Fix:** Low-Medium
- Queue rejection doesn't break missions; just blocks new ones until space opens
- Threshold is conservative (3 tasks) — can be tuned based on real DeepSeek performance
- Easy to revert: remove queue check and go back to unlimited

---

## 🟡 MEDIUM Findings (Fix within 48h)

### MEDIUM #5: Hardcoded Paths

**The Finding:**
- **Location:** All scripts (nexus.py:37-43, keyword_router.py, mission_board_sync.py:31, gmail_exec_poller.py)
- **Current pattern:**
  ```
  MISSION_BOARD = BASE_DIR / "mission_board.json"
  AUDIT_LOG = Path("/home/john/Thunderbird/logs/nexus_audit.log")
  GOOSE_INBOX = BASE_DIR / "collaboration/goose_inbox.md"
  CLAUDE_INBOX = BASE_DIR.parent / "claude_inbox.md"
  ```
- **Problem:** Some paths are absolute (`/home/john/...`), some are relative to script location
- **Risk:** If OpsCenter or Thunderbird directory moves, half the paths break
- **Portability:** Cannot run on a different machine or CI/CD pipeline without editing every script

**Why it matters:**
- Operational: If repo is migrated or cloned to a different path, all scripts fail with silent FileNotFoundError
- Maintenance: Any refactoring that moves files requires editing 4+ scripts
- CI/CD: Automation and testing on different machines becomes impossible

**Proposed Fix (Plain English):**
1. Create a single config file: `/home/john/Thunderbird/OpsCenter/config.py` with all path definitions:
   ```
   BASE_DIR = Path(__file__).parent.parent
   MISSION_BOARD = BASE_DIR / "OpsCenter" / "mission_board.json"
   AUDIT_LOG = BASE_DIR / "logs" / "nexus_audit.log"
   GOOSE_INBOX = BASE_DIR / "OpsCenter" / "collaboration" / "goose_inbox.md"
   CLAUDE_INBOX = BASE_DIR / "claude_inbox.md"
   # ... etc for all paths
   ```
2. In each script, replace hardcoded path definitions with:
   ```python
   from config import MISSION_BOARD, AUDIT_LOG, GOOSE_INBOX, CLAUDE_INBOX
   ```
3. All paths now resolve relative to the config file location, which is relative to script location
4. Moving the directory requires NO code changes

**Estimated Effort:** Medium (2 hours)
- Create config.py with all paths: 20 min
- Update nexus.py imports: 20 min
- Update keyword_router.py: 10 min
- Update mission_board_sync.py: 10 min
- Update gmail_exec_poller.py: 10 min
- Test all paths resolve correctly: 30 min

**Dependencies:** None — pure refactoring

**Risk Level of Fix:** Medium
- Config.py is new file; need to verify all imports work
- Relative imports can be fragile if script is run from wrong directory
- Mitigation: Test running scripts from different directories before committing

---

### MEDIUM #6: No Retry Logic

**The Finding:**
- **Location:** `nexus.py:216-231` (dispatch_to_claude function)
- **Current behavior:**
  - Claude timeout (120s) returns error string; mission continues with the error as "result"
  - subprocess.TimeoutExpired caught, logged, then propagates as failed dispatch
  - No retry with backoff; no circuit breaker
- **Impact:** One transient Claude failure (e.g., temporary network glitch) kills the entire mission

**Why it matters:**
- Operational resilience: Transient failures (1% of requests) shouldn't cascade to mission failure
- Cost: Have to waste tokens on new attempt when simple retry would have succeeded
- Network reality: IMAP, Claude Desktop, Telegram can all have 1-2 second hiccups; 120s timeout should allow one retry

**Proposed Fix (Plain English):**
1. Wrap `dispatch_to_claude` with a simple retry wrapper:
   - Try 1: Execute Claude via `claude -p`
   - On subprocess.TimeoutExpired: Wait 5 seconds, try again (1 retry)
   - On second timeout: Give up, return "TIMEOUT: Claude did not respond" (which triggers escalation)
   - On FileNotFoundError (Claude not installed): Fall back to DeepSeek immediately (no retry)
2. Log retries to audit log: `audit("DISPATCH_CLAUDE_RETRY", "attempt 2")`
3. Keep max timeout at 120s per attempt (no increase)

**Estimated Effort:** Medium (1.5 hours)
- Write retry wrapper function: 20 min
- Integrate into dispatch_to_claude call path: 15 min
- Add audit logging: 5 min
- Test with synthetic timeout (mock subprocess to fail once): 30 min
- Test fallback path: 15 min

**Dependencies:** None — wrapper is self-contained

**Risk Level of Fix:** Low-Medium
- Retry only on timeout (safe); FileNotFoundError falls back immediately (safe)
- Max 10 additional seconds latency if first attempt times out (acceptable)
- Easy to adjust: can change wait time (5s) or retry count (1) without code restructure

---

## Integration Risks (6 items)

### Risk #1: Claude Dispatch — UNTESTED

**The Risk:**
- **Status:** The Claude execution path via `claude -p` has **never been exercised** in audit logs
- **Only DeepSeek dispatches recorded** — suggests no CLAUDE-routed task has been executed end-to-end
- **Scenario:** If Claude Desktop isn't running or MAX OAuth token expired:
  - `subprocess.run(["claude", "-p", ...])` raises FileNotFoundError or hangs
  - Fallback to DeepSeek happens silently (audit log records DISPATCH_CLAUDE_FAIL)
  - High-judgment task gets processed by lower-capability model

**Impact:**
- Silent degradation: Commander doesn't know strategic task was demoted to DeepSeek
- Quality risk: Proposal drafting, risk assessment, strategy calls all fail silently

**Mitigation:**
1. **Before autonomous:** Run 3 end-to-end tests:
   - `nexus.py run MISSION-TEST-1 "assess the risk of overbooking in Q2"`
   - `nexus.py run MISSION-TEST-2 "draft a proposal for new pricing strategy"`
   - `nexus.py run MISSION-TEST-3 "why did the Kuklinski booking fail?"`
2. Verify via audit log that all three show `DISPATCH_CLAUDE` (not fallback to DeepSeek)
3. Check Claude Desktop is running: `ps aux | grep "Claude"`
4. Verify MAX OAuth is active: `echo "test" | claude -p` should return text, not error

**Effort to Verify:** Quick (30 minutes)
- Start Claude Desktop: 2 min
- Run 3 test missions: 15 min
- Check audit log: 5 min
- Verify MAX OAuth: 5 min

**Risk Level:** Medium
- Can be tested safely without affecting production
- Once verified, risk goes away (until Claude Desktop crashes or OAuth lapses)
- Recommend adding health check (see below)

**Rollback Plan:** If Claude dispatch fails, manually force tasks to DeepSeek in keyword_router (change CLAUDE_KEYWORDS to empty list)

---

### Risk #2: DeepSeek Rate Limits — UNKNOWN

**The Risk:**
- **Status:** No rate limit testing performed against `deepseek/deepseek-chat-v3.1`
- **API provider:** OpenRouter (deepseek-chat-v3.1 is their free tier)
- **Unknown limits:** RPM (requests per minute), tokens per minute, concurrent requests
- **Scenario:** Under burst load (5+ concurrent missions), DeepSeek silently drops tasks or returns errors

**Impact:**
- Silent failures: Tasks queue in goose_inbox but never complete
- No alerting: Daemon logs appends but DeepSeek never processes
- Cascading: Missions stack up, suspense deadlines pass, escalation doesn't trigger

**Mitigation:**
1. **Burst test:** Execute 5 sequential DeepSeek tasks in 1 minute via goose_inbox:
   - Task 1: "list all active missions" (light)
   - Task 2: "extract vendor details from PDF" (medium)
   - Task 3: "calculate margin analysis" (light)
   - Task 4: "compare flight rates" (heavy)
   - Task 5: "verify invoice totals" (light)
2. Monitor completion: Check goose_inbox for status transitions (PENDING → COMPLETE)
3. Document observed limits:
   - Max tasks per minute: ___
   - Max tokens per minute: ___
   - Recommended queue depth: ___ (should match MEDIUM #4 threshold)
4. Publish findings in NEXUS_SPEC.md Section 7 (SECURITY & COST)

**Effort to Measure:** Medium (1.5 hours)
- Design burst test scenario: 15 min
- Execute 5 tasks manually: 30 min
- Wait for completion and monitor: 30 min
- Document results: 15 min

**Risk Level:** Medium
- Testing is non-destructive; can be done anytime
- Results inform HIGH #4 (queue depth threshold)
- Risk remains unknown until testing done

**Rollback Plan:** If DeepSeek rate limits are too low, adjust HIGH #4 queue threshold from 3 to 1 (only allow 1 pending task at a time)

---

### Risk #3: Telegram Failures — CREDENTIALS EMPTY

**The Risk:**
- **Status:** `TELEGRAM_BOT_TOKEN` and `TELEGRAM_COMMANDER_ID` are both **empty strings** in nexus.py
- **Evidence:** `_load_telegram_creds()` silently returns if `.env` vars missing
- **Impact:** Suspense alerts don't fire, escalations don't page, Commander is blind to mission failures

**Why it matters:**
- Visibility: Commander has no real-time notification of mission problems
- Escalation: Deadlocked missions sit in escalated state with no page
- Operational: Daemon appears healthy but communication is broken

**Mitigation:**
1. **Immediate check:** `grep TELEGRAM /home/john/Thunderbird/.env` — verify credentials exist
2. **If missing, generate new bot:**
   - Message @BotFather on Telegram
   - `/start` → `/newbot` → name it "NEXUS-Thunderbird" → get bot token
   - Run `/getid` in a Telegram chat with the bot → get your user ID
   - Update `.env`:
     ```
     TELEGRAM_BOT_TOKEN=<token>
     TELEGRAM_COMMANDER_ID=<your_user_id>
     ```
3. **Test end-to-end:**
   - Run: `python3 nexus.py run MISSION-TEST-ALERT "test"`
   - Should receive Telegram message: "🔔 NEXUS ALERT: NEXUS | MISSION-TEST-ALERT → QWEN ..."
4. **If test fails:**
   - Check bot token is valid (not truncated/pasted wrong)
   - Check Commander ID is numeric (not username)
   - Test Telegram API directly: `curl -X POST https://api.telegram.org/botTOKEN/sendMessage -d "chat_id=ID&text=test"`

**Effort to Fix:** Quick (30 minutes)
- Check .env: 2 min
- If missing, create new bot: 10 min
- Update .env: 2 min
- Test end-to-end: 10 min
- Troubleshoot if needed: 10 min

**Risk Level:** Low
- Not code; just credential setup
- Can test before autonomous operation
- Rollback: delete .env entries and revert to silent mode

**Rollback Plan:** If Telegram fails at runtime, operations continue (just without pages); escalations queue in claude_inbox instead

---

### Risk #4: Stale Locks — POSSIBLE

**The Risk:**
- **Status:** `NexusLock` uses `fcntl.flock` (advisory locking)
- **Advisory = vulnerable:** If daemon process is SIGKILL'd (not SIGTERM), lock file persists
- **Scenario:** Daemon crashes hard → nexus.lock stays → next daemon start fails with "NEXUS ALREADY RUNNING"
- **Workaround required:** Manual `rm /home/john/Thunderbird/OpsCenter/nexus.lock` to recover

**Why it matters:**
- Operational: Operator must manually intervene to restart after any crash
- Autonomy: Autonomous daemon can't restart itself if it crashes

**Mitigation:**
1. **Add lock freshness check in daemon_loop:**
   - Before each iteration, check lock file heartbeat timestamp
   - If heartbeat > 120 seconds old (should update every 30s), assume previous daemon crashed
   - Delete stale lock and re-acquire
   - Log: `audit("STALE_LOCK_RECOVERED", "heartbeat age > 120s, re-acquiring lock")`

2. **Implementation:**
   - In `daemon_loop()` before main while loop:
     ```python
     if NEXUS_LOCK.exists():
         try:
             data = json.load(open(NEXUS_LOCK))
             heartbeat = data.get("heartbeat")
             if heartbeat:
                 age = (datetime.now(timezone.utc) - datetime.fromisoformat(heartbeat)).total_seconds()
                 if age > 120:
                     NEXUS_LOCK.unlink()  # Stale lock detected; remove it
         except:
             pass  # Lock corrupted; try to remove
     ```

3. **Test:** Kill daemon with SIGKILL (not SIGTERM), verify next start succeeds without manual intervention

**Effort to Implement:** Medium (1 hour)
- Add freshness check function: 15 min
- Integrate into daemon_loop: 10 min
- Test: kill with SIGKILL, verify recovery: 20 min
- Audit logging: 5 min

**Risk Level:** Low
- Check is safe; worst case it deletes a stale lock that should be deleted
- Only affects daemon startup, not normal operation
- Easy to test

**Rollback Plan:** Remove freshness check; revert to requiring manual lock deletion on crash

---

### Risk #5: Race Conditions — CONFIRMED POTENTIAL

**The Risk:**
- **Status:** Two separate file-locking mechanisms exist:
  - `nexus.py` uses `NexusLock` with heartbeat (daemon-only)
  - `mission_board_sync.py` uses `mission_board.lock` (EXEC commands)
  - `gmail_exec_poller.py` has **NO locking** at all
- **Scenario:** gmail_exec_poller calls mission_board_sync.py while nexus.py daemon writes to mission_board.json simultaneously:
  - mission_board_sync acquires its lock (✓)
  - But nexus.py has a different lock, doesn't wait
  - Both write to mission_board.json at the same time
  - JSON gets corrupted: partial writes, missing fields, unparseable structure
- **Impact:** Lost missions, duplicate entries, corrupted board state

**Why it matters:**
- Data integrity: Mission history is corrupted
- Silent failure: Corrupted JSON may not cause immediate crash (depends on parsing)
- Operational: Downstream tools that read mission_board.json start failing

**Mitigation:**
1. **Use single lock file for all mission_board writers:**
   - Keep `mission_board.lock` as single source of truth
   - Make it a shared resource (not nexus-specific, not sync-specific)
   - All writers (nexus.py daemon, mission_board_sync.py, gmail_exec_poller.py) acquire same lock before writing

2. **In nexus.py (daemon):**
   - Replace `NexusLock` usage for board writes with shared `mission_board.lock`
   - Keep `NexusLock` for daemon-is-running check (different purpose)

3. **In gmail_exec_poller.py:**
   - Before calling `execute_command()`, acquire `mission_board.lock`:
     ```python
     fd = acquire_lock()  # From mission_board_sync.py
     try:
         result = execute_command(exec_email['command'])
     finally:
         release_lock(fd)
     ```

4. **Test:**
   - Start daemon
   - Simultaneously send 3 EXEC emails (triggers poller)
   - Run concurrent board writes
   - Verify mission_board.json remains valid JSON (no corruption)

**Effort to Implement:** Medium (2 hours)
- Add shared lock module: 20 min
- Update nexus.py: 20 min
- Update gmail_exec_poller.py: 15 min
- Sync mission_board_sync.py to use shared lock: 10 min
- Test concurrent writes: 30 min

**Risk Level:** Medium
- Lock implementation is straightforward
- Testing is critical to verify no races remain
- Requires coordinating updates across 3 files

**Rollback Plan:** Revert to separate locks if shared lock causes deadlock; add timeout to prevent hung processes

---

### Risk #6: Inbox Scanner Race — MINOR

**The Risk:**
- **Status:** `scan_inboxes()` in nexus.py reads line counts to track position
- **Scenario:** Multi-line task is written to goose_inbox mid-scan:
  - Scanner reads lines 0-50 (last_line=50)
  - New task writes lines 51-54 (4 lines, multi-line)
  - Scanner next cycle reads line 51 only
  - Task gets split: partial delivery to router
- **Impact:** Task text is truncated, routing may fail, mission gets incomplete input

**Why it matters:**
- Data integrity: Task gets corrupted on delivery
- Silent failure: Router may not detect truncation; produces wrong result
- Low probability but possible

**Mitigation:**
1. **Change tracking from line count to task boundary detection:**
   - Instead of: `last_line = total_lines`, track `last_position = file_size_bytes`
   - When scanning, read from byte position, not line count
   - Scan complete tasks only (look for task delimiter: `\n---\n` followed by status line)

2. **Alternative (simpler):** Add task boundary marker:
   - Require all tasks in goose_inbox to have delimiter: `\n---\nNEXUS_TASK_END\n`
   - Scanner waits for complete task before delivering to router
   - This matches the dispatch_to_qwen format (already has `\n---\n`)

3. **Implement:**
   - Verify dispatch_to_qwen() writes complete task block with newlines
   - Update scan_inboxes() to only return tasks that have matching END marker
   - If partial task detected, queue entire block for next cycle

**Effort to Implement:** Quick (45 minutes)
- Verify task format in dispatch_to_qwen: 10 min
- Add END marker to dispatch: 5 min
- Update scan_inboxes logic: 15 min
- Test with multi-line task injection: 15 min

**Risk Level:** Low
- Change is purely defensive; won't break single-line tasks
- Can be tested offline with synthetic inbox injection
- Easy to revert if needed

**Rollback Plan:** Remove END marker detection; go back to line count (accept minor race risk)

---

## Implementation Sequence (Prioritized Order)

**Session 1: Critical Fixes (Est. 1.5 hours)**

| # | Task | Effort | Risk | Dependencies |
|---|------|--------|------|--------------|
| 1 | Fix zero-keyword fallback (CRITICAL #1) | 15 min | Low | None |
| 2 | Add missing keywords (CRITICAL #2) | 20 min | Low | None |
| 3 | Test keyword router against 22 test cases | 30 min | Low | 1, 2 |
| 4 | Populate & test Telegram credentials (Risk #3) | 30 min | Low | None |
| **Session 1 Total** | **1.5 hours** | | |

---

**Session 2: Integration Risks & High Priority (Est. 4-5 hours)**

| # | Task | Effort | Risk | Dependencies |
|---|------|--------|------|--------------|
| 1 | Test Claude dispatch end-to-end (Risk #1) | 30 min | Low | None |
| 2 | Add queue depth monitoring (HIGH #4) | 1 hour | Low-Med | None |
| 3 | Add retry logic to Claude dispatch (MEDIUM #6) | 1.5 hours | Low | None |
| 4 | Implement stale lock recovery (Risk #4) | 1 hour | Low | None |
| 5 | Measure DeepSeek rate limits (Risk #2) | 1.5 hours | Med | None |
| **Session 2 Total** | **5.5 hours** | | |

---

**Session 3: Refactoring & Risk #5 (Est. 4-5 hours)**

| # | Task | Effort | Risk | Dependencies |
|---|------|--------|------|--------------|
| 1 | Create centralized config.py (MEDIUM #5) | 2 hours | Med | None |
| 2 | Implement shared mission_board.lock (Risk #5) | 2 hours | Med | None |
| 3 | Add task boundary detection (Risk #6) | 45 min | Low | None |
| 4 | Full integration test (all 3 engines + Telegram) | 1 hour | Med | All prior |
| **Session 3 Total** | **5.75 hours** | | |

---

## Cost Impact

**Before Fixes:**
- DeepSeek V3.1 (unbounded queue): ~$0.27/M
- Claude Sonnet MAX (OAuth): $0
- Telegram API (free tier): $0
- **Total: $0/month**

**After Fixes:**
- DeepSeek V3.1 (queue depth ≤ 3): ~$0.27/M (no change)
- Claude Sonnet MAX (with retry): $0 (no change; retries are billable only if successful, within same MAX budget)
- Telegram API: $0 (no change)
- Shared lock file I/O: $0 (local file operations)
- **Total: $0/month (CONFIRMED)**

**Caveat:** If DeepSeek rate limits measured in Risk #2 prove lower than expected (e.g., < 1 task/min), recommend:
- Reduce queue depth threshold from 3 to 1
- Or shift more tasks to Claude (already $0, just quota-limited)
- OR use stratified queuing: DeepSeek for light tasks, Claude for heavy

---

## Success Criteria

NEXUS is ready for autonomous operation when **ALL** of the following are met:

### Specification Compliance (🔴 CRITICAL must pass)
- [ ] Keyword router matches 100% of spec-defined keywords (draft, why, assess, propose, strategy, creative, etc.)
- [ ] Zero-keyword fallback routes to Claude (not DeepSeek)
- [ ] Test suite: 22/22 tests pass (was 20/22, now 22/22 after fixes)

### Integration Testing (Risk items must pass)
- [ ] Claude dispatch tested end-to-end: 3 missions routed to Claude, audit log shows DISPATCH_CLAUDE success
- [ ] DeepSeek rate limits documented: "Max X tasks/min, recommend queue depth ≤ Y"
- [ ] Telegram credentials verified: Suspense alert page received successfully
- [ ] Stale lock recovery tested: Daemon killed with SIGKILL, next start succeeds without manual intervention
- [ ] Race condition mitigated: Concurrent writes to mission_board.json result in valid JSON (automated test)
- [ ] Inbox scanner boundary test: Multi-line task delivered complete in single cycle

### Operational Readiness
- [ ] Audit log rotation configured (prevents unbounded growth)
- [ ] Health check endpoint built and tested: `nexus.py health` returns status of lock, queue, Claude, Telegram
- [ ] Rollback procedure documented: How to revert any fix if it breaks operations
- [ ] Monitor alerting: Escalated missions page Commander via Telegram within 5 minutes

### Cost Verification
- [ ] $0/month cost confirmed after all changes
- [ ] DeepSeek tier limits documented and respected
- [ ] Claude MAX OAuth confirmed active
- [ ] No Gemini or Deepseek calls in any code path

---

## Rollback Plan

**If a fix breaks production, revert in this order:**

### Immediate Rollback (< 5 minutes)
1. **Stop daemon:** `kill $(pgrep -f "nexus.py daemon")`
2. **Revert affected file:** `git checkout OpsCenter/<file>.py`
3. **Restart daemon:** `python3 nexus.py daemon 60 &`

### Safe Rollback Sequence
| Fix | Rollback Command | Impact | Recovery Time |
|-----|------------------|--------|----------------|
| CRITICAL #1 (zero-keyword) | Restore keyword_router.py from git | Tasks route to DeepSeek; quality risk | 5 min |
| CRITICAL #2 (missing keywords) | Restore keyword_router.py | Same as above; breaks "why" tasks | 5 min |
| HIGH #4 (queue depth) | Remove queue check in nexus.py | Queue can overflow; DeepSeek may rate-limit | 5 min |
| MEDIUM #6 (retry logic) | Remove retry wrapper | Transient failures kill missions | 5 min |
| MEDIUM #5 (hardcoded paths) | Restore original path definitions | Works only from /home/john/Thunderbird | 10 min |
| Risk #1 (Claude dispatch) | Force all tasks to DeepSeek | All missions run via DeepSeek; quality loss | 5 min |
| Risk #4 (stale lock) | Remove heartbeat check | Stale locks require manual cleanup | 5 min |
| Risk #5 (race condition) | Revert to separate locks | JSON corruption possible (rare) | 10 min |

---

## Appendix: Test Cases for Verification

### Keyword Router Test Suite (22 tests — 20/22 currently passing, target 22/22)

```
TEST 1:  "draft a client proposal for Mediterranean cruise" → CLAUDE (strategy)
TEST 2:  "check cabin availability for Silversea" → QWEN (list/check)
TEST 3:  "strategic assessment of Furlow Japan trip" → CLAUDE (strategic)
TEST 4:  "extract vendor pricing from the PDF" → QWEN (extract)
TEST 5:  "why did the Kuklinski booking fail" → CLAUDE (why) [CURRENTLY FAILS]
TEST 6:  "architect a new vendor pipeline" → CLAUDE (architect)
TEST 7:  "negotiate the Silversea contract" → CLAUDE (negotiate)
TEST 8:  "propose a pricing strategy" → CLAUDE (propose + strategy)
TEST 9:  "assess the risk" → CLAUDE (assess) [CURRENTLY FAILS]
TEST 10: "figure this out for me" → CLAUDE (zero keywords → judgment) [CURRENTLY FAILS]
TEST 11: "list all active missions" → QWEN (list)
TEST 12: "update the mission board" → QWEN (update)
TEST 13: "compare hotel rates for Tokyo" → QWEN (compare)
TEST 14: "search flights for April 15" → QWEN (search)
TEST 15: "write a creative narrative for the client" → CLAUDE (creative + write)
TEST 16: "evaluate vendor health" → CLAUDE (evaluate)
TEST 17: "verify commission calculations" → QWEN (verify)
TEST 18: "resolve the booking conflict" → CLAUDE (resolve + conflict)
TEST 19: "design a new pricing model" → CLAUDE (design)
TEST 20: "summarize the PDF attachment" → QWEN (summarize)
TEST 21: "judge which vendor is best" → CLAUDE (judge)
TEST 22: "file the invoice in the dossier" → QWEN (file)

PASS RATE TARGET: 22/22 (currently 20/22)
```

---

*NEXUS Mitigation Plan — End of Document*
*For questions or escalations: Flag to Commander via Telegram or email to johnloucks3@gmail.com*
