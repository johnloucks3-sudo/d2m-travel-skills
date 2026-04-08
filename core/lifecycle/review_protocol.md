# Claude Code Review Protocol (7a)
## Lifecycle System & OpenCode Work Verification

**Author:** Claude (Development Task P0)  
**Date:** 2026-04-07  
**Status:** ACTIVE  

---

## PURPOSE

Define code review requirements and standards for all Lifecycle System development and OpenCode work to ensure:
- ✅ Correctness of phase determination algorithm
- ✅ Completeness of anchor date validation
- ✅ Test coverage adequacy
- ✅ Production readiness

---

## CODE REVIEW GATES

### GATE 1: Structural Review (Pre-Integration)
**Reviewer:** Claude  
**Trigger:** Any new module in `core/lifecycle/` or `testing/`

**Checklist:**
- [ ] Module has docstring with purpose, author, date
- [ ] All functions have parameter types and return types documented
- [ ] No circular imports or dependency issues
- [ ] Logging configured (use Python `logging` module, not print)
- [ ] Error handling for missing/invalid inputs
- [ ] No hardcoded paths — use `os.path` or configurable paths

**Pass Criteria:** 6/7 checks pass, no critical issues

---

### GATE 2: Algorithm Review (Correctness)
**Reviewer:** Claude  
**Trigger:** Changes to `determine_phase()` or `validate_anchor_dates()`

**Checklist:**
- [ ] Phase transitions tested with known dates (Furlow, McLeod, Westbrook cases)
- [ ] Payment status correctly influences phase (e.g., unpaid at FPD = PHASE_2 flag)
- [ ] Anchor date logic matches Phase_Standardization.md (6 phases)
- [ ] Edge cases handled: FPD on embark day, payment exactly on FPD, etc.
- [ ] Temporal boundary conditions correct (T-7 days to embark, etc.)

**Pass Criteria:** All 5 checks pass

**Test Evidence Required:**
```python
# Example: Phase should be PHASE_3 for Furlow on 2026-03-31
furlow_phase = determine_phase(
    booking_date=date(2025, 9, 15),
    embark_date=date(2026, 8, 29),
    disembark_date=date(2026, 9, 8),
    fpd=date(2026, 4, 1),
    payment_status="paid",
    payment_date=date(2026, 3, 25)
)
assert furlow_phase == ("PHASE_3", "Polish")
```

---

### GATE 3: Test Coverage Review (7b)
**Reviewer:** Claude  
**Trigger:** Any changes to test suite

**Checklist:**
- [ ] All 6 phases have at least one test case
- [ ] Edge cases covered: FPD on embark, payment delays, missing anchors
- [ ] Anchor validator tests both valid and invalid inputs
- [ ] All test cases have descriptive names
- [ ] Test assertions are specific (not just True/False)
- [ ] >80% branch coverage in core logic

**Pass Criteria:** 6/6 checks pass

**Coverage Target:**
```
core/lifecycle/client_ingester.py:
  determine_phase():        100% coverage
  validate_anchor_dates():  95%+ coverage
  assign_phases_from_dossier(): 80%+ coverage
```

---

### GATE 4: Integration Review (Data)
**Reviewer:** Claude  
**Trigger:** Changes that affect client data flow

**Checklist:**
- [ ] Output JSON schema matches expected format (see below)
- [ ] All 7 test clients produce valid phase assignments
- [ ] Output file paths correct and writable
- [ ] No PII leakage in logs
- [ ] Performance acceptable (<1s for 7 clients)

**Output JSON Schema:**
```json
{
  "ClientName": {
    "phase_code": "PHASE_X",
    "phase_name": "NameHere",
    "booking_date": "2026-01-01",
    "embark_date": "2026-08-29",
    "disembark_date": "2026-09-08",
    "fpd": "2026-04-01",
    "payment_status": "paid|pending|partial",
    "ship": "SS Grandeur",
    "voyage": "Scandinavia",
    "days_to_embark": 145,
    "anchor_validation": {
      "valid": true,
      "errors": [],
      "warnings": [],
      "anchor_count": 4
    }
  }
}
```

**Pass Criteria:** All checks pass, output validates against schema

---

### GATE 5: Production Readiness (Final)
**Reviewer:** Claude  
**Trigger:** Before shipping to production

**Checklist:**
- [ ] No debug statements or TODO comments left
- [ ] All imports available in production environment
- [ ] Error messages are user-readable (not stack traces)
- [ ] Logging level set appropriately (INFO for normal, ERROR for failures)
- [ ] Documentation updated (README, docstrings)
- [ ] Performance tested with all 7 clients

**Pass Criteria:** 7/7 checks pass

---

## REVIEW WORKFLOW

### For Claude Implementation:
1. **Write code** with full type hints and docstrings
2. **Add tests** before declaring feature complete
3. **Run tests locally** → verify all pass
4. **Document algorithm** in code comments for complex logic
5. **Create summary** of changes, test results, gate status

### For OpenCode Integration:
1. **OpenCode submits code** to review
2. **Claude runs GATE 1-5** sequentially
3. **Claude provides feedback** with specific line numbers if issues
4. **OpenCode addresses feedback** → resubmits
5. **Claude approves** with sign-off: ✅ REVIEW PASS

---

## APPROVAL AUTHORITY

- **GATE 1-3:** Claude (algorithmic correctness)
- **GATE 4:** Claude (data integrity)
- **GATE 5:** Claude + Commander (production readiness)

**Sign-off Format:**
```
✅ REVIEW PASS (all gates)
  Reviewer: Claude
  Date: 2026-04-07
  Gates: 1✅ 2✅ 3✅ 4✅ 5✅
  Notes: [optional notes on close calls or special handling]
```

---

## ESCALATION PATH

If Claude identifies issues that require Commander input:

```
🔴 GATE FAILED: [gate number]
  Issue: [specific problem]
  Location: [file]:[line]
  Recommendation: [fix or defer]
  Escalated to: Commander
```

Examples:
- Phase definition conflict with existing system → escalate
- Data schema mismatch with downstream consumers → escalate
- Performance concern on large datasets → escalate
- Architectural question on scope → escalate

---

## QUICK REFERENCE

| Gate | What | Who | When |
|------|------|-----|------|
| 1 | Structure | Claude | Pre-integration |
| 2 | Algorithm | Claude | Phase logic changes |
| 3 | Tests | Claude | Test suite changes |
| 4 | Data | Claude | Data schema/output changes |
| 5 | Production | Claude + Cmd | Before ship |

---

## VERSION HISTORY

| Date | Author | Change |
|------|--------|--------|
| 2026-04-07 | Claude | Initial protocol (v1.0) |

---

*Thunderbird Lifecycle System · Dreams2Memories Travel, LLC*
