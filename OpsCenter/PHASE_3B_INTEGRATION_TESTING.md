# Phase 3B — End-to-End Integration Testing
## Thunderbird Phase 3 Production Hardening | Version 1.0 | 2026-04-28

---

## OVERVIEW

Phase 3B validates that all 5 Redis connectors work correctly in real operational workflows with the error recovery framework deployed. Tests run FULL workflows from user input → system response, with Redis failures injected mid-workflow.

**Status:** READY FOR EXECUTION  
**Target completion:** 2026-05-05  
**Dependencies:** Phase 3A framework complete (all 5 connectors refactored, health check deployed)

---

## TEST SCENARIO 1: Telegram Command → D2MC2 → Redis → Email Draft

**Workflow:**
1. Commander sends Telegram message to C2 bot: `/prepare_validation_email kuklinski`
2. C2 bot parses command, creates task in D2MC2 connector (decision state)
3. D2MC2 saves decision to Redis (or local cache if Redis unavailable)
4. Dani workflow triggered: reads D2MC2 state, drafts validation email, saves to Gmail drafts
5. COS reviews draft and approves/edits
6. Email sent to client

**Test Steps:**
- [ ] Send test command: `/prepare_validation_email kuklinski` via Telegram
- [ ] Verify D2MC2 state recorded (check health check status.json)
- [ ] Verify Dani draft created in Gmail
- [ ] Simulate Redis outage mid-workflow (stop redis-server)
- [ ] Verify fallback: D2MC2 uses local cache
- [ ] Verify Dani can still read state and draft email
- [ ] Restart Redis and verify health check detects recovery
- [ ] Verify cache synced back to Redis
- [ ] Confirm email draft still available for approval

**Expected result:**  
✅ Full workflow completes with zero data loss despite mid-workflow Redis failure

---

## TEST SCENARIO 2: Cross-Platform Coordination — OpenCode → Goose → Research → Hale

**Workflow:**
1. OpenCode creates intelligence mission on mission board (via OpenCode connector)
2. Mission status published to Redis
3. Goose watches Redis for new missions, picks up mission, starts research
4. Goose saves research results to Redis (via Goose connector)
5. Hale polling on Redis detects results, aggregates into morning brief
6. Brief sent to Commander

**Test Steps:**
- [ ] Create mission via OpenCode: `MISSION-TEST-20260428 "Test ship intelligence sweep"`
- [ ] Verify mission appears on mission board
- [ ] Verify Goose detects mission (check Goose connector state)
- [ ] Simulate Redis outage during Goose research
- [ ] Verify Goose saves research to local cache
- [ ] Verify Hale health check detects Redis outage
- [ ] Verify Hale can still aggregate mission results from cache
- [ ] Restart Redis and verify health check syncs Goose research back to Redis
- [ ] Confirm brief generation includes results from fallback period

**Expected result:**  
✅ OpenCode → Goose → Hale chain completes with Redis outage absorbed

---

## SUCCESS CRITERIA

All 5 scenarios MUST meet these criteria:

✅ **Availability:** Workflow completes even if Redis is unavailable mid-workflow  
✅ **Data integrity:** No lost writes, no corrupted state, no duplicate operations  
✅ **Recovery:** Health check detects Redis recovery and syncs cache correctly  
✅ **Consistency:** Cache and Redis have identical data after recovery  
✅ **Performance:** Fallback operations complete in <500ms per operation  

**Pass/Fail threshold:** 5/5 scenarios pass → Phase 3B complete, proceed to Phase 3C  

---

## NEXT STEPS (Phase 3C)

After Phase 3B completion:

**Phase 3C — Drive Backup Verification**
- Test RDB snapshot → Drive archival
- Test backup trigger on state changes
- Test recovery from backup
- Test concurrent backup during active operations

---

*Phase 3B Integration Testing Plan | Updated 2026-04-28 | Hale, COS*
