# STANDING ORDER — SESSION COMPRESSION & CONTEXT WINDOW LIMITS
**Effective:** 2026-05-31  
**Authority:** Commander (context bloat blocker)  
**Owner:** Hale (COS) + Sterling (A7, implementation)

---

## PROBLEM STATEMENT

Context rising 100%+ per session. Conversation history compounds without limit. Current state:
- Session depth: 100–200+ messages
- Per-turn context overhead: ~400–600 tokens (old messages + history)
- Total per-session token cost: 40K–80K tokens on top of payload
- No conversation window limit → unbounded growth

**Root cause:** No window cap. Old turns stay in context indefinitely.

---

## SOLUTION: Session Compression Protocol

### Phase 1 — Immediate Procedural Limits (ACTIVE NOW)

**Session boundaries:**
- Max duration: **2 hours** (wall clock)
- Max messages: **100 turns** (whichever comes first)
- At boundary: issue `/clear` → new session
- Archive old session: `session_autosave_YYYYMMDD_compressed.md`

**Per-turn context discipline:**
- CLAUDE.md auto-load: 20KB (locked via Strategy 3)
- MEMORY.md auto-load: 26KB (locked via Strategy 4)
- Conversation window: last 20 messages (200KB max)
- Dossier freshness: 12-hour cache, refresh on request

**Target:** reduce per-session context overhead from 80K to 30K tokens.

### Phase 2 — Session Compression Script (Code — Sterling, Tier 3)

Path: `scripts/compress_session_history.py`

**What it does:**
- At session boundary, run compression
- Summarize old turns (>20 back) into single "compressed history" message
- Keep recent 20 turns verbatim
- Archive compressed session to Drive for later reference

**Integration:**
- Hook into `/clear` command → auto-compress before exit
- Output: `session_autosave_YYYYMMDD_compressed.md` (compressed structure)
- New session starts fresh: zero old messages, zero compounding

**Estimated savings:** 60–80% context reduction (40K–65K tokens/session)

---

## MODEL SELECTION GUIDANCE

**DO NOT switch to Sonnet to fix this.** Switching models treats the symptom, not the disease:
- Sonnet = 2.5x more expensive
- Sonnet context window = 200K (we're at 100%+, larger window won't help)
- **Problem is the WINDOW, not the MODEL capacity**

**When to switch to Sonnet:**
1. Execute Phase 1 (2-hour boundary discipline) for 5 sessions
2. Measure context overhead AFTER compression
3. If still >100K tokens/session after compression → upgrade to Sonnet
4. If <100K tokens/session after compression → stay Haiku (save ~$15–20/day)

**Expected outcome:** Compression + window limits should drop context to 50–80K tokens/session (Haiku-tier). No model switch needed.

---

## ENFORCEMENT

- **Hale** monitors session duration; warns at 1.5hr mark
- **Hale** enforces `/clear` at 2hr or 100-message boundary
- **Sterling** owns compression script deployment (target: 2026-06-04)
- **Audit cadence:** weekly context metrics (SLA: avg ≤60K tokens/session)

---

## RELATED

- SO-TOKEN-DISCIPLINE (2026-05-29): Model routing
- CLAUDE.md Strategy 3 (2026-05-31): Reference table pruning
- MEMORY.md Strategy 4 (2026-05-31): Session log archival
- MCP Tier 1 Pruning (2026-05-31): Dead-weight tool removal
