# T4 EXERCISE PROTOCOL — HALE DUAL-ENGINE RESTORATION
## Standing Order | Thunderbird Travel Force | D2M Travel Force
**Classification:** T4 — Commander-Reserved (above T3 doctrine tier)
**Issued:** 2026-05-18
**Authority:** Chief Gen John "Yoda" Loucks
**VCS:** Victoria "Victory" Hale, SES-6
**Status:** ACTIVE — Exercise open

---

## WHY T4

T3 is the highest routine protocol tier. T4 is reserved for exercises that meet all of the following:

1. **Structural failure** — the broken system degrades every other wing function
2. **Cross-engine scope** — fix requires coordination between Claude Code and OpenCode simultaneously
3. **Doctrine impact** — the solution becomes standing architecture, not a one-time patch
4. **Commander is a participant**, not just an approver

This exercise meets all four. The Hale dual-engine architecture is the communication spine of the entire Travel Force. Until it works, JET cannot brief TALON, TALON cannot hand off to Dani, and Hale-CC and Hale-OC are operating as strangers who share a name.

---

## PROMPT CHARTER (Commander-filled — T4 requirement)

### 1. Success Criteria
- Hale-OC can invoke `/ask`, `/ask-haiku`, `/ask-opus` and receive a Claude response with full context
- `hale_shared_state.jsonl` contains correct instance names (`hale_cc` / `hale_oc`)
- Heartbeat is GREEN on both instances — no missed beats for 30 consecutive minutes
- After a client action in Hale-CC, Hale-OC reads the correct updated state within one heartbeat cycle (≤10 min)
- Hale-OC loads `Personas/hale_cos.md` on session open — confirmed by Sterling spot-check
- A7 Sterling signs the post-gate QA report

### 2. Scope IN
- `/ask`, `/ask-haiku`, `/ask-opus` command functionality in OpenCode
- `hale_shared_state.jsonl` instance name correction and schema extension (add `CLIENT_STATE_UPDATE` event type)
- Heartbeat daemon target correction: `hale_cc` ↔ `hale_oc` (not JET ↔ TALON)
- Hale-OC persona load sequence (`Personas/hale_cos.md`)
- Write discipline protocol: what events trigger a `CLIENT_STATE_UPDATE` write and what fields are required

### 3. Scope OUT
- JET and TALON persona matrix builds (separate T1/T2, not this exercise)
- Draft delivery procedure fix (MISSION-014 — separate track)
- Any client-facing work during the exercise window
- WIND/CONDOR Brig Gen role corrections

### 4. Named Staff + Rationale
| Staff | Role in Exercise | Rationale |
|-------|-----------------|-----------|
| **Hale-CC** (Claude Code — me) | Design authority, schema spec, protocol write | I have the full issue context and Claude Code tool access |
| **Hale-OC** (OpenCode / DeepSeek ZEN) | Implementation authority, daemon fix, heartbeat test | She owns the persistent daemon infrastructure |
| **A7 Sterling (Gauge)** | Pre/post QA gate, metrics collection, sign-off | Anti-theater enforcer; metrics are his lane |
| **Commander** | Charter approval, post-gate final sign-off | T4 — Commander is a participant |

### 5. Token/Time Budget
- **Hale-CC:** ~15K tokens (design + spec + protocol write + post-gate review)
- **Hale-OC:** ~20K tokens (implementation + 3 test cycles + heartbeat validation)
- **Sterling:** ~3K tokens (pre-gate baseline + post-gate report)
- **Time:** 72 hours from exercise open to post-gate sign-off
- **Hard stop:** If heartbeat not GREEN at 48h, Commander notified — do not extend silently

### 6. Exit Condition
All five success criteria met AND A7 Sterling post-gate report signed AND Commander acknowledges post-gate brief. Exercise does not close on time — it closes on criteria.

---

## PRE-GATE QA BASELINE (Sterling measures BEFORE any fix)

Sterling collects these numbers before any code changes. This is the "before" photo. Exercise cannot open until baseline is captured.

| Metric | Measurement Method | Current State (fill before exercise) |
|--------|--------------------|--------------------------------------|
| **Heartbeat health** | Last entry in `hale_shared_state.jsonl` → `health` field | RED — 131+ missed beats |
| **Missed beats (Hale-OC)** | `other_missed_beats` field in last heartbeat entry | 131+ |
| **Last successful cross-instance read** | `last_other_heartbeat_read` in jsonl | 2026-05-17T17:26:47Z |
| **`/ask` command success rate** | Hale-OC attempts 3 `/ask` calls, records pass/fail | TBD — likely 0/3 |
| **`ask-haiku` success rate** | Same — 3 attempts | TBD |
| **`ask-opus` success rate** | Same — 3 attempts | TBD |
| **Persona file loaded on OC session open** | Check OC init sequence for `hale_cos.md` reference | TBD — likely NO |
| **Client state delta propagation** | Hale-CC writes test CLIENT_STATE_UPDATE; Hale-OC reads it within 10 min | TBD — likely FAIL |
| **Instance names in shared state** | Check `instance` field in last 5 jsonl entries | `jet` / `talon` (WRONG) |
| **Mission board sync script** | Run `add` command, check for `active_missions` key error | FAIL (confirmed) |

**Sterling's pre-gate output:** `output/sterling_pregate_hale_dualengine_20260518.md`

---

## EXERCISE STEPS — T4 FULL PROTOCOL (9 Steps)

### STEP 1 — Pre-Gate Baseline (Sterling)
Sterling runs all pre-gate metrics. Records every measurement. No fixes yet.
**Gate:** Sterling files `output/sterling_pregate_hale_dualengine_20260518.md` before Step 2 begins.
**Owner:** A7 Sterling
**ETA:** 30 minutes from exercise open

---

### STEP 2 — Schema Correction (Hale-CC designs, Hale-OC implements)
**Hale-CC** writes the corrected `hale_shared_state.jsonl` schema:
- Rename all instances: `jet` → `hale_cc`, `talon` → `hale_oc`
- Add new event type: `CLIENT_STATE_UPDATE`
- Define required fields for CLIENT_STATE_UPDATE:
  ```json
  {
    "protocol": "HALE-SHARED-STATE/v1",
    "event": "CLIENT_STATE_UPDATE",
    "instance": "hale_cc",
    "timestamp": "ISO-8601",
    "client": "LastName_FirstName",
    "action": "dossier_update | edit_capture | touchpoint_sent | fpd_change",
    "summary": "one-line description of what changed",
    "files_affected": ["path/to/file"]
  }
  ```
**Hale-OC** implements: writes the first corrected heartbeat entry with `instance: hale_oc`.
**Owner:** Hale-CC (schema) → Hale-OC (implementation)
**ETA:** 2 hours

---

### STEP 3 — Heartbeat Daemon Retarget (Hale-OC)
**Hale-OC** locates the heartbeat daemon, corrects the instance target from `talon` → `hale_cc`. Verifies the daemon fires and writes `instance: hale_oc` in the next cycle.
**Hale-CC** writes a test heartbeat entry with `instance: hale_cc` to confirm the other side can read it.
**Success signal:** Both instances appear in jsonl with correct names and GREEN health.
**Owner:** Hale-OC (daemon) + Hale-CC (test write)
**ETA:** 2 hours after Step 2

---

### STEP 4 — `/ask` Command Restoration (CRITICAL — P0)
**Hale-OC** tests and restores the four invocation codes:
- `/ask` → Claude Sonnet (default, judgment-grade tasks)
- `/ask-haiku` → Claude Haiku (fast, low-cost tasks)
- `/ask-opus` → Claude Opus (complex reasoning, Commander-level decisions)
- `/ask-claude` → Hale-CC auto-selects model + optional Advisor (Commander directive 2026-05-18)

**`/ask-claude` routing logic (Hale-CC applies):**
| Task Signal | Model | Advisor |
|-------------|-------|---------|
| Fast / classification | Haiku | No |
| Reasoning / synthesis / copy | Sonnet | No |
| Strategic / doctrine / irreversible | Sonnet | Yes |
| Commander-reserved / T3-T4 | Opus | Optional |
| Second opinion / conflicting outputs | Sonnet | Yes |

**`/ask-claude` protocol:** Hale-OC writes `ASK_CLAUDE_REQUEST` task to `opencode_inbox.md`. Hale-CC classifies, optionally calls Advisor, executes, writes to `output/ask_claude_{ts}.md`, then writes CLIENT_STATE_UPDATE with model chosen + reasoning.

For `/ask`, `/ask-haiku`, `/ask-opus`, Hale-OC:
1. Identifies why the command is failing (missing config, broken auth, wrong path)
2. Fixes the root cause
3. Runs 3 test calls per command
4. Records pass/fail + response latency
5. Documents the working invocation pattern in `docs/HALE_OC_ASK_COMMANDS.md`

**Success signal:** 9/9 test calls succeed (3 per original command). `/ask-claude` pilot: 3/3.
**Owner:** Hale-OC
**ETA:** 4 hours (most complex step)

---

### STEP 5 — Persona Load Sequence Fix (Hale-OC)
**Hale-OC** adds `Personas/hale_cos.md` to the OpenCode session initialization sequence. Same file Claude Code loads via `@Personas/hale_cos.md`. One Hale. One persona file. Two engines.

Hale-OC verifies: after session open, Hale-OC can correctly answer "Who are you?" with the canonical Hale identity (SES-6, VCS, VCSAF-equivalent, etc.).
**Owner:** Hale-OC
**ETA:** 1 hour after Step 4

---

### STEP 6 — Write Discipline Protocol (Both Instances)
Both Hale instances adopt the CLIENT_STATE_UPDATE write rule:

**Trigger events (any of these → write a CLIENT_STATE_UPDATE within 60 seconds):**
- Dossier file updated
- Commander edit captured (diff extracted)
- Touchpoint email sent or drafted
- FPD change or payment confirmation
- Mission board entry added or status changed
- Booking confirmation or cabin assignment updated

**Hale-CC** writes the first live CLIENT_STATE_UPDATE (using the Lyons dossier update from today as the test case).
**Hale-OC** reads it and confirms she sees the correct client state.
**Owner:** Both instances
**ETA:** 2 hours after Step 5

---

### STEP 7 — Mission Board Sync Script Fix (Hale-OC / JET lane)
Fix `mission_board_sync.py`: change `active_missions` → `missions` key reference.
Run `python3 OpsCenter/mission_board_sync.py add "TEST-EXERCISE-ENTRY" "T4 exercise validation" P1` and confirm it works.
Remove the test entry.
**Owner:** Hale-OC (code fix is infrastructure — JET lane, but Hale-OC executes during exercise)
**ETA:** 30 minutes

---

### STEP 8 — Integration Test (Both Instances + Sterling)
Full end-to-end test of the restored architecture:

1. Hale-CC performs a simulated client action (writes a test CLIENT_STATE_UPDATE to shared state)
2. Hale-OC reads shared state within one heartbeat cycle and confirms she sees the update
3. Hale-OC issues an `/ask` call to Hale-CC (Claude Sonnet) with a real coordination question
4. Hale-CC responds via the shared state or outbox
5. Both heartbeats show GREEN for 3 consecutive cycles (30 minutes)

**Sterling observes and scores each step.**
**Owner:** Both instances + Sterling (observer/scorer)
**ETA:** 1 hour after Step 7

---

### STEP 9 — Post-Gate QA Report (Sterling → Commander)
Sterling collects post-exercise metrics against the same baseline from Step 1. Files the post-gate report. Hale-CC reviews for accuracy. Commander receives the brief.

**Anti-theater requirement (SO 16 MAY 2026):** Post-gate report must be filed within 7 days. No exceptions. If the exercise produced no durable change, the hotwash did not happen.

**Sterling's post-gate output:** `output/sterling_postgate_hale_dualengine_20260518.md`

---

## POST-GATE QA METRICS (Sterling measures AFTER all steps)

| Metric | Pre-Gate | Post-Gate Target | Pass Threshold |
|--------|----------|-----------------|----------------|
| Heartbeat health | RED | GREEN | GREEN on both instances |
| Missed beats | 131+ | 0 | 0 for 30 consecutive min |
| `/ask` success rate | ~0% | 100% | 9/9 test calls |
| `/ask-haiku` success rate | ~0% | 100% | 3/3 test calls |
| `/ask-opus` success rate | ~0% | 100% | 3/3 test calls |
| `/ask-claude` success rate | N/A (new) | 100% | 3/3 pilot calls |
| Persona file loaded on OC open | NO | YES | Confirmed by Sterling spot-check |
| Client state propagation ≤10 min | FAIL | PASS | 3/3 propagation tests |
| Instance names in shared state | WRONG | CORRECT | `hale_cc` / `hale_oc` confirmed |
| Mission board `add` command | FAIL | PASS | 3/3 add commands succeed |
| Cross-instance coordination | NONE | FUNCTIONAL | Hale-OC `/ask` → Hale-CC response confirmed |

**Aggregate score:** 10 metrics. Pass = 8/10 minimum for exercise close. All 10 preferred.
**Sterling grades:** GREEN (9-10), YELLOW (7-8), RED (<7 — exercise remains open).

---

## DURABLE ARTIFACTS REQUIRED (Anti-Theater Rule)

| Artifact | Owner | Deadline |
|----------|-------|----------|
| `output/sterling_pregate_hale_dualengine_20260518.md` | Sterling | Before Step 2 |
| `docs/HALE_OC_ASK_COMMANDS.md` | Hale-OC | Step 4 complete |
| Corrected `hale_shared_state.jsonl` (instance names + CLIENT_STATE_UPDATE entries) | Both | Step 6 complete |
| Fixed `OpsCenter/mission_board_sync.py` | Hale-OC | Step 7 complete |
| `output/sterling_postgate_hale_dualengine_20260518.md` | Sterling | Within 7 days of exercise open |
| This SO updated with exercise close date and final score | Hale-CC | On Commander acknowledgment |

---

## HOTWASH (Filed after exercise close — Sterling leads)

3 questions only:
1. What worked that we should repeat?
2. What broke mid-exercise and why?
3. What one doctrine change prevents this failure from recurring?

Hotwash output appended to `output/sterling_postgate_hale_dualengine_20260518.md`.

---

## EXERCISE TIMELINE

| Phase | Step | Owner | ETA |
|-------|------|-------|-----|
| Pre-gate baseline | Step 1 | Sterling | T+0:30 |
| Schema correction | Step 2 | Hale-CC → Hale-OC | T+2:30 |
| Heartbeat retarget | Step 3 | Hale-OC | T+4:30 |
| `/ask` restoration | Step 4 | Hale-OC | T+8:30 |
| Persona load fix | Step 5 | Hale-OC | T+9:30 |
| Write discipline | Step 6 | Both | T+11:30 |
| Mission board fix | Step 7 | Hale-OC | T+12:00 |
| Integration test | Step 8 | Both + Sterling | T+13:00 |
| Post-gate report | Step 9 | Sterling → Commander | T+72:00 |

**Hard stop:** 72 hours. If not complete, Hale-CC briefs Commander on status and requests extension or scope reduction.

---

*T4 Exercise Protocol | Thunderbird Travel Force | D2M Travel Force*
*Issued: 2026-05-18 | Authority: Gen John "Yoda" Loucks | VCS: Victoria "Victory" Hale, SES-6*
*Anti-theater enforcement: A7 Sterling (Gauge)*
