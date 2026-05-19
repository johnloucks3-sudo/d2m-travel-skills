# PHASE 3A — Redis Error Recovery & Fallback
## Production Hardening for Unified State Architecture
**Status:** IN PROGRESS (Framework deployed)  
**Start Date:** 2026-04-28  
**Target Completion:** 2026-05-05

---

## PROBLEM STATEMENT

Phase 2 deployed a central Redis backend with 5 platform connectors (D2MC2, Dani, OpenCode, OpenCode, Claude). This creates unified state awareness, but introduces a single point of failure:

- If Redis connection is lost, all 5 connectors lose state
- No fallback mechanism → task queues are lost
- No recovery path → state is not restored when Redis comes back online

**Phase 3A goal:** Transparent fallback to local cache + automatic sync on reconnect.

---

## ARCHITECTURE

### Tier 1: Local Cache Layer
```
~/.thunderbird_cache/{connector_name}/
  └─ {REDIS_KEY}.json
     ├─ key: "DANI_DRAFTS:draft123"
     ├─ data: { full state object }
     ├─ cached_at: timestamp
     └─ redis_available: boolean at time of cache
```

### Tier 2: Fallback Logic
```
save_data(key, data):
  1. Try Redis (via redis-cli)
  2. On timeout/error → save to local cache + mark Redis down
  3. Return success/failure to caller

read_data(key):
  1. Try Redis (via redis-cli)
  2. On miss/timeout → read from local cache
  3. Return data if found in either layer
```

### Tier 3: Sync On Reconnect
```
Periodic health check (every 30s via cron):
  1. Test Redis connection
  2. If previously down, now available:
     a. Sync all local cache files back to Redis
     b. Verify sync count
     c. Clean up cache (or keep as archive)
```

---

## IMPLEMENTATION

### Files Deployed
- `core/redis_connector_fallback.py` — Base class for all connectors
  - `RedisConnectorFallback` — Main implementation
  - `DaniRedisConnectorWithFallback` — Example subclass
  - Methods: `_save_to_cache()`, `_read_from_cache()`, `_sync_cache_to_redis()`, `check_redis_health()`

- `core/test_redis_error_recovery.py` — Error recovery test suite
  - Test 1: Redis available (baseline)
  - Test 2: Redis disconnection → fallback to cache
  - Test 3: Cache sync on reconnect
  - Test 4: Periodic health check
  - Test 5: Concurrent cache operations during outage

### Integration Path (Subsequent Phases)
Each of the 5 connectors inherits from `RedisConnectorFallback`:
```python
class D2MC2RedisConnectorWithFallback(RedisConnectorFallback):
    def __init__(self):
        super().__init__(connector_name="d2mc2")
    
    def record_decision(self, ...):
        # Try Redis, fallback to cache automatically
        ...

class GooseRedisConnectorWithFallback(RedisConnectorFallback):
    # Similar pattern
```

---

## TEST SCENARIOS

| Test | Scenario | Expected Result |
|------|----------|-----------------|
| 1 | Redis available, save draft | Data in Redis ✓ |
| 2 | Redis down, save draft | Data in local cache ✓ |
| 3 | Redis reconnect | Cache synced to Redis ✓ |
| 4 | Health check detects recovery | Automatic sync triggered ✓ |
| 5 | Concurrent saves during outage | All N items in cache ✓ |

---

## MONITORING & OBSERVABILITY

### Health Check Cron (Proposed)
```bash
# Run every 30 seconds
*/0.5 * * * * python3 /home/john/Thunderbird/core/health_check_worker.py
```

### Logs
```
/home/john/Thunderbird/logs/phase3a_error_recovery_test.log
/home/john/Thunderbird/logs/redis_fallback_{connector}.log (per-connector)
```

### Metrics
- Cache hit rate: N_cache_hits / (N_redis_attempts + N_cache_fallbacks)
- Sync lag: time from Redis outage to recovery
- Sync success rate: N_synced / N_cached_items

---

## BLOCKERS & DEPENDENCIES

### Blockers
None — framework is self-contained.

### Dependencies
- Phase 2 (Redis + 5 connectors) — **COMPLETE** ✓
- All 5 connectors inherit from fallback class — IN PROGRESS

### Next Phase Dependencies
- Phase 3B (Integration Testing) — requires fallback deployed to all 5
- Phase 3C (Drive Backup) — depends on stable cache/Redis state

---

## SUCCESS CRITERIA (Phase 3A)

- [ ] Fallback class deployed and documented
- [ ] All 5 connectors refactored to inherit from fallback
- [ ] Test suite passes 5/5 scenarios
- [ ] Health check cron deployed and monitoring
- [ ] Cache sync verified on reconnect
- [ ] Zero data loss during Redis outage → recovery cycle
- [ ] Performance impact <5% (cache overhead)

---

## TIMELINE

| Date | Milestone |
|------|-----------|
| 2026-04-28 | Framework deployed + test suite created |
| 2026-04-29 | All 5 connectors refactored |
| 2026-04-30 | Full test suite run + health check cron deployed |
| 2026-05-01 | Integration test with Phase 2 live system |
| 2026-05-05 | Phase 3A COMPLETE, move to Phase 3B |

---

## OWNERSHIP

**Owner:** Hale (COS)  
**Implementation:** Claude Code / OpenCode  
**Review:** Commander (stress test results)

---

*Phase 3A — Production Hardening Begins | 2026-04-28 | Hale, COS*
