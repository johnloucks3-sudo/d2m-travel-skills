# STAFF PAPER — REDIS PERSISTENT MEMORY SYSTEM
## Option 2 Implementation Plan

**Priority:** P1 — Critical architectural foundation  
**Requestor:** Commander John Loucks  
**Prepared by:** Col Victoria "Iron Vic" Hale, COS  
**Date:** 2026-04-28  
**Budget Status:** ⚠️ **TIGHT** — At 78% Sonnet, 69% all-models. Plan avoids token burn during build.

---

## ISSUE

Five disconnected agents (D2MC2C, Dani, Goose, OpenCode, Claude Code + Gmail) maintain local context but lack unified state. Result:
- Context loss between sessions
- Agent decisions contradict each other
- Commander repeats himself across platforms
- No real-time awareness of open decisions, standing orders, client state

Example: Commander decides in Telegram "McLeod needs new flights." OpenCode doesn't know. Claude Code session later generates a quote without updated flights. Dani sends client outdated info.

---

## DISCUSSION

### Current State (Local Files)
- `hale_state.json` (Claude Code session-local)
- `hale_memory.md` (session-local, not shared)
- `claude_inbox.md` / `opencode_inbox.md` (task queues only, no state)
- Telegram session logs (ephemeral, 30-day purge)
- Gmail labels (app-level, not system-aware)

**Gap:** No single source of truth accessible to all five agents in real-time.

### Option 2: Redis as Central Memory Store

**Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                    YOGA (192.168.1.198)                      │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Redis (port 6379, in-memory cache + RDB persistence)    │ │
│  │ - ACTIVE_CLIENTS                                        │ │
│  │ - OPEN_DECISIONS                                        │ │
│  │ - STANDING_ORDERS                                       │ │
│  │ - STAFF_LOAD                                            │ │
│  │ - SESSION_CONTEXT                                       │ │
│  │ - BUDGET_STATE                                          │ │
│  │ - TIMESTAMPS (all updates logged)                       │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
        ↑         ↑         ↑         ↑         ↑
        │         │         │         │         │
    D2MC2C      Dani      Goose    OpenCode  Claude Code
    (Hale)   (Concierge) (Agent)  (DeepSeek) (Session)
```

**Memory Schema (Redis data structure):**
```
ACTIVE_CLIENTS = {
  "McLeod": {
    "ship": "Silver Muse",
    "depart": "2026-06-23",
    "phase": "PRE-DEPARTURE",
    "open_items": 2,
    "assigned_to": "A3",
    "last_update": "2026-04-28T14:32:15Z"
  },
  ...
}

OPEN_DECISIONS = [
  {
    "id": "d001",
    "question": "Should we rebook McLeod's flights?",
    "context": "Cheaper option found, 2hr earlier departure",
    "options": ["YES", "NO", "MAYBE"],
    "decision": null,
    "owner": "A5",
    "created": "2026-04-28T14:00:00Z",
    "expires": "2026-04-28T18:00:00Z"
  }
]

STANDING_ORDERS = {
  "email_send_gate": "All sends to non-wing require Commander approval",
  "model_routing": "Default Sonnet, Opus on P0 only",
  "budget_limit": "$100/month, pause at 90%",
  ...
}

STAFF_LOAD = {
  "A2_Dembe": {"active_tasks": 3, "overdue": 0, "last_seen": "2026-04-28T12:45:00Z"},
  "A3_Dani": {"active_tasks": 5, "overdue": 1, "last_seen": "2026-04-28T14:15:00Z"},
  ...
}

SESSION_CONTEXT = {
  "current_focus": "Kuklinski lifecycle + Westbrook cancellation",
  "budget_state": {"spent": 30.74, "limit": 100, "pct_used": 31},
  "model_usage": {"sonnet": 78, "opus": 5, "haiku": 17},
  "alerts": ["Sonnet at 78%, Sonnet resets Fri 1:59 PM"],
  "last_update": "2026-04-28T14:30:00Z"
}

TIMESTAMPS = {
  "ACTIVE_CLIENTS:McLeod": "2026-04-28T14:32:15Z",
  "OPEN_DECISIONS:d001": "2026-04-28T14:00:00Z",
  "SESSION_CONTEXT": "2026-04-28T14:30:00Z"
}
```

**Data Freshness:**
- Real-time reads: All agents get <50ms response from Redis
- Writes: Atomic (Redis INCR/SET commands)
- Persistence: RDB snapshots every 5 min → `/home/john/Thunderbird/redis/dump.rdb`
- Backup: Daily sync to Google Drive

**Concurrency Handling:**
- Redis is single-threaded, handles all concurrent writes safely
- No race conditions (unlike file-based shared state)
- Lock-free: Agents read, update independently, Redis guarantees atomicity
- Conflict resolution: Last-write-wins (timestamps for audit trail)

**Failure Modes & Recovery:**
| Failure | Impact | Recovery |
|---------|--------|----------|
| Redis down | All agents lose state, operate on last cached copy | Restart systemd service, auto-restore from dump.rdb |
| Network partition (YOGA unreachable) | Agents use last known state | Automatic fallback to local file state, sync when network restored |
| Data corruption | RDB file unreadable | Restore from Drive backup |
| Concurrent write collision | Last update wins, earlier update lost | Timestamps logged for audit; rare (different agents typically update different keys) |

---

## RESOURCE IMPACT & CONSTRAINTS

### Infrastructure (YOGA)
- **Redis memory:** ~50MB (all system state fits easily)
- **CPU:** Negligible (<1% for this volume)
- **Disk:** RDB snapshots 1-5MB, dump every 5 min
- **Network:** 3-5 agents * <50ms per read = no bottleneck

### Token Budget (CRITICAL)
**Current state:** 78% Sonnet, 69% all-models, $30.74 spent/$100 limit
- Redis setup: 0 token cost (Python standard library, no LLM calls)
- Agent integration: Light (1-2 Redis calls per agent operation)
- **Estimated token impact:** <2% increase (mostly from logging/audit trail)

**Mitigation:** Redis read operations are non-token-generating. Agents spend tokens on decisions, not memory lookups.

### Development Time & Expertise
- **Redis setup:** 30 min (install, configure, systemd service)
- **Agent integration:** Each agent needs Redis connector library (redis-py, Node.js redis, Python subprocess env var)
- **Testing:** 2 hours (concurrent read/write stress test, failover scenarios)
- **Deployment:** 1 hour (systemd timers, backups, monitoring)
- **Total:** ~6 hours hands-on work

---

## IMPLEMENTATION PHASES

### Phase 1: Redis Infrastructure (2 hours)
1. SSH to YOGA, install Redis: `sudo apt install redis-server`
2. Configure: `/etc/redis/redis.conf` (bind to localhost, RDB snapshots)
3. Enable systemd: `sudo systemctl enable --now redis-server`
4. Verify: `redis-cli ping` → PONG
5. Create backup directory: `/home/john/Thunderbird/redis/`

**Owner:** A7 (Gauge Sterling) — infrastructure/devops

### Phase 2: Agent Connectors (3 hours)
Each agent needs a lightweight connector to Redis:

**D2MC2C (Hale bot):**
- Read standing orders, client state before responding
- Write session context, decisions made
- File: `core/redis/hale_redis_connector.py`

**Dani (Concierge bot):**
- Read active clients, standing orders, staff assignments
- Write client interactions, handoff notes
- File: `core/redis/dani_redis_connector.py`

**Goose (OpenCode interface):**
- Read ACTIVE_CLIENTS to avoid duplicate work
- Write task status, decisions
- File: `OpsCenter/goose_redis_connector.py`

**OpenCode (DeepSeek dispatcher):**
- Read SESSION_CONTEXT to avoid expensive context-loading
- Write status updates
- File: `OpsCenter/opencode_redis_connector.py`

**Claude Code (this session):**
- Read/write via Python `redis` library (already available)
- Automatic on session start

**Owner:** A12 (ELON) — first-principles integration design + OpenCode wiring

### Phase 3: Testing & Validation (2 hours)
1. Concurrent writes test: 5 agents write simultaneously, verify no data loss
2. Failover test: Kill Redis, agents fall back to local state
3. Restore test: Redis comes back online, agents re-sync
4. Load test: Simulate 30 days of writes, verify RDB < 10MB

**Owner:** A7 (Gauge Sterling) — QA, metrics, lessons learned

### Phase 4: Deployment & Monitoring (1 hour)
1. Enable RDB snapshots: `BGSAVE` every 5 min via cron
2. Daily backup to Drive: `gs://d2m-redis-backups/dump-YYYY-MM-DD.rdb`
3. Monitoring: Alert if Redis down or RDB snapshot fails
4. Audit logging: Every write logged to `redis_audit.log`

**Owner:** A7 (Gauge Sterling) — ongoing operations

---

## STAFF ASSESSMENT & SIGN-OFF

### A7 (Gauge Sterling) — Process, Infrastructure, Metrics
**Assessment required:**
- ✓ Redis deployment on YOGA (feasible, low risk)
- ✓ RDB snapshot strategy (every 5 min, daily Drive backup)
- ✓ Failure mode documentation (see table above)
- ? What monitoring/alerting do we need?
- ? Audit trail format for regulatory compliance?

**Recommendation:** Proceed. Infrastructure is standard, risk is low.

---

### A12 (ELON) — Innovation, First-Principles Design
**Assessment required:**
- ✓ Agent connector architecture (is Redis the right choice vs. message queue?)
- ✓ Memory schema design (is this structure complete? Any missing pieces?)
- ✓ Data consistency model (eventual consistency vs. strong consistency?)
- ? Should we add Pub/Sub for real-time event broadcasting? (agents notified when state changes)
- ? Should we compress old state or archive it elsewhere?

**Recommendation:** Build connectors incrementally, test Phase by Phase.

---

### A5 (Viper Castillo) — Strategy, Business Impact
**Assessment required:**
- ✓ Does Redis solve the context-loss problem? (yes, single source of truth)
- ✓ What's the business impact of outages? (low — agents fall back to local cache)
- ? How does this affect decision-making speed? (faster — no session context reloads)
- ? Are there compliance/audit implications? (audit trail needed for financial decisions)

**Recommendation:** Proceed. Improves operational efficiency, minimal business risk.

---

### A9 (Harlan) — Finance, Cost Analysis
**Assessment required:**
- ✓ Token budget impact (negligible, <2%)
- ✓ Infrastructure cost on YOGA (zero — already paid)
- ? Should we meter/charge internal agents for Redis access? (probably not)
- ? How long do we keep audit logs before archival? (affects storage)

**Recommendation:** Budget-neutral. Proceed.

---

### Commander (Yoda)
**Decisions needed:**
1. Approve Phase 1 (Redis setup)?
2. Timeline — start immediately or after Sonnet resets (Fri)?
3. Scope — all five agents (D2MC2C, Dani, Goose, OpenCode, Claude Code) or phased?
4. Audit trail level — detailed (every write) or summary only?

---

## OPTIONS

**A) Full Deployment (Recommended)**
- All 5 agents → Redis immediately
- Complete memory schema
- Full audit trail
- Timeline: Start now, Phase 1 complete by Wed 5pm

**B) Phased Deployment (Risk-Aware)**
- Phase 1: Redis setup (no risk)
- Phase 2: Hale (D2MC2C) only, test thoroughly
- Phase 3: Add Dani, Goose, OpenCode
- Phase 4: Claude Code auto-integration
- Timeline: Slower, lower risk, deploy over 2 weeks

**C) Delay Until Budget Reset (Conservative)**
- Wait until Fri (weekly reset on Sonnet)
- Build plan, staff review, full design review
- Deploy fresh on Fri
- Timeline: Slower, safest, allows full team input

---

## ACTIONS

**Immediate (by EOD 2026-04-28):**
1. ☐ Commander: Choose Option A/B/C
2. ☐ A7 (Gauge): Review infrastructure, sign off
3. ☐ A12 (ELON): Review architecture, flagged questions above
4. ☐ A5 (Viper): Review business impact
5. ☐ A9 (Harlan): Review budget impact, sign off

**Phase 1 (if approved):**
1. ☐ A7: SSH to YOGA, deploy Redis
2. ☐ A7: Verify systemd service running
3. ☐ Hale: Test connectivity from Claude Code

**Phase 2 (upon Phase 1 completion):**
1. ☐ A12: Design connector architecture
2. ☐ A12: Build D2MC2C connector (Hale bot)
3. ☐ OpenCode lead: Wire OpenCode connector
4. ☐ A3 (Dani): Assess client-bot integration impact

---

## APPENDIX: Redis Configuration Template

```ini
# /etc/redis/redis.conf — key settings
bind 127.0.0.1
port 6379
databases 16
save 300 10          # RDB snapshot every 300s (5 min) if 10+ keys changed
appendonly no        # No AOF log (RDB sufficient)
maxmemory 256mb      # Reasonable limit, won't be hit
maxmemory-policy allkeys-lru  # Evict old keys if limit exceeded
```

---

## APPENDIX: Redis Commands Reference

```bash
# Read
redis-cli GET "ACTIVE_CLIENTS"
redis-cli HGETALL "SESSION_CONTEXT"

# Write
redis-cli SET "OPEN_DECISIONS" "[...]"
redis-cli INCR "BUDGET_STATE:spent"

# Monitor
redis-cli MONITOR  # Watch all commands in real-time
redis-cli INFO stats  # Memory, connections, operations

# Backup
redis-cli BGSAVE  # Background snapshot (non-blocking)
redis-cli LASTSAVE  # Timestamp of last snapshot
```

---

*Col Victoria "Iron Vic" Hale, COS*  
*Thunderbird Wing | Dreams2Memories Travel, LLC*  
*Prepared 2026-04-28 · Standing by for staff review and Commander decision*
