# WHETSTONE CI CURRENCY TRIAL — EVALUATION REPORT TEMPLATE
## Regent Portal reCAPTCHA Solving: 2Captcha vs Current Baseline

**Trial Name:** Tencent/BrowserSkill Equivalent (2Captcha + Playwright)  
**Evaluator:** Whetstone — A14 Currency & Razor-Sharp  
**Start Date:** 2026-07-06  
**Target Completion:** 2026-07-12 (end of week)

---

## EXECUTIVE SUMMARY
_Completed by end of week_

### Recommendation
- [ ] **FIT:** Adopt 2Captcha for automated Regent portal auth
- [ ] **NO-FIT:** Keep current manual Chrome CDP workaround
- [ ] **CONDITIONAL FIT:** Adopt if [condition] met

### Key Findings
_Summary of fit/no-fit decision with reasoning_

---

## TRIAL DESIGN

### Success Criteria
1. ✅ Portal login automation works (email + password + reCAPTCHA)
2. ✅ Dashboard loads with authenticated session
3. ✅ No rate limiting or blocking
4. ✅ Latency within 15% of manual baseline

### Failure Criteria
1. ❌ reCAPTCHA solving fails (accuracy <95%)
2. ❌ Portal blocks 2Captcha traffic
3. ❌ Latency significantly slower (>20% vs baseline)
4. ❌ Cost exceeds $0.05 per login

### Test Case: Regent Seven Seas OA Portal
- **URL:** https://www.rssc.com/agent/login
- **Auth Gate:** reCAPTCHA v2 (checkbox)
- **Target:** Dashboard load without manual intervention
- **Baseline:** Current Chrome CDP + Commander login

---

## BASELINE MEASUREMENT

### Current State (Manual Chrome CDP)
| Metric | Value | Notes |
|--------|-------|-------|
| **Method** | Chrome CDP (port 9222) + Commander manual login | Authenticated session via Firefox/Chrome |
| **Time to Dashboard** | ~120–180 seconds | Commander interaction + CAPTCHA solve |
| **Cost** | $0.00 | Commander time (unmeasured opportunity cost) |
| **Success Rate** | 100% | Human completion always works |
| **Automation Level** | 0% | Requires manual Commander intervention |
| **Friction** | HIGH | Blocks scripted workflows; manual gate |

_Baseline captured: [date/time]_

---

## TRIAL RESULTS

### 2Captcha + Playwright Configuration
| Component | Setting | Details |
|-----------|---------|---------|
| **Browser** | Playwright (Chromium) | Headless, stealth headers |
| **reCAPTCHA Solver** | 2Captcha API | v2 (checkbox) solver |
| **Integration** | `core/ai_infra/thunderbird_recaptcha_solver.py` | Async/sync wrappers |
| **Cost** | $0.0003–0.001 per solve | Estimated for Regent sitekey |
| **Timeout** | 60 seconds | Max wait for reCAPTCHA solve |

### Test Run #1: Page Load + Captcha Extraction
_[Results populated during trial]_

| Metric | Value | Status |
|--------|-------|--------|
| **Page Load Latency** | TBD | ⏳ |
| **Sitekey Extraction** | TBD | ⏳ |
| **Captcha Present** | TBD | ⏳ |

### Test Run #2: reCAPTCHA Solving
_[Results populated during trial]_

| Metric | Value | Status |
|--------|--------|--------|
| **API Submission** | TBD | ⏳ |
| **Solve Time** | TBD | ⏳ |
| **Token Quality** | TBD | ⏳ |
| **Cost** | TBD | ⏳ |

### Test Run #3: Form Auto-Fill
_[Results populated during trial]_

| Metric | Value | Status |
|--------|--------|--------|
| **Form Detection** | TBD | ⏳ |
| **Field Fill Success** | TBD | ⏳ |
| **Submission Ready** | TBD | ⏳ |

### Test Run #4: Full Portal Login (if authorized)
_[Results populated during trial]_

| Metric | Value | Status |
|--------|--------|--------|
| **End-to-End Latency** | TBD | ⏳ |
| **Dashboard Load** | TBD | ⏳ |
| **Session Persistence** | TBD | ⏳ |
| **Blocking Detected** | TBD | ⏳ |

---

## COMPARATIVE ANALYSIS

### Latency: 2Captcha vs Baseline
```
Baseline (manual):           ████████████████████ ~120–180s
2Captcha + Playwright:       ████████ ~20–30s (estimated)
Improvement:                 [TBD]% faster
```

### Cost: 2Captcha vs Baseline
```
Baseline (manual):           $0.00 (Commander time, opportunity cost TBD)
2Captcha + Playwright:       ~$0.0005 per login (~$50/year @ 100 logins)
Net ROI:                     [TBD]
```

### Automation: 2Captcha vs Baseline
```
Baseline:                    0% automated (requires manual intervention)
2Captcha + Playwright:       100% automated (full workflow, no manual gate)
Friction Reduction:          [TBD]
```

---

## FIT/NO-FIT ANALYSIS

### Fit Criteria Assessment
| Criterion | Status | Evidence |
|-----------|--------|----------|
| **Accuracy (reCAPTCHA solve ≥95%)** | ⏳ TBD | [populated during trial] |
| **Not Rate-Limited / Blocked** | ⏳ TBD | [populated during trial] |
| **Latency vs Baseline (≤15% degradation)** | ⏳ TBD | [populated during trial] |
| **Cost Acceptable (≤$0.05/login)** | ⏳ TBD | [populated during trial] |

### No-Fit Risks
- 🔴 **reCAPTCHA v3:** 2Captcha cannot solve v3 (needs user interaction detection). If Regent upgrades, solution breaks.
- 🔴 **Bot Detection:** Playwright + 2Captcha combo might trigger anti-bot (IP + behavior). Requires real residential IP or proxy.
- 🔴 **Portal Updates:** Regent portal changes (form selectors, reCAPTCHA version) require code updates. Not "set and forget."
- 🟡 **Operator Lock-in:** 2Captcha is a third-party dependency. Service outages block automation.

### Adoption Path (if FIT)
1. Integrate 2Captcha API key into secrets management
2. Replace `regent_oa_reauth.py` Chrome CDP manual step with `thunderbird_recaptcha_solver.py`
3. Add CI health probe for 2Captcha API availability
4. Monitor cost + usage in monthly budget reviews
5. Document fallback (revert to manual Chrome CDP if 2Captcha fails)

---

## DECISION MATRIX

### If BLAZING (All criteria met)
**RECOMMENDATION:** ✅ **ADOPT 2Captcha**
- Full portal automation (removes manual Commander gate)
- Cost-effective (~$50/year)
- High accuracy + reliability
- Clear adoption path + fallback strategy

**Action:** 
- Merge `thunderbird_recaptcha_solver.py` into core CI lane
- Update `regent_oa_reauth.py` to use API-based solving
- Add 2Captcha API key to credentials vault
- Set cost budget to $100/year (buffer)

### If CONDITIONAL (Some criteria unmet but fixable)
**RECOMMENDATION:** 🟡 **CONDITIONAL FIT**
- Requires: [specific condition] to resolve
- Cost/benefit acceptable if [condition met]
- Timeline: Re-evaluate [when condition changes]

**Action:**
- Document condition + re-evaluation trigger
- Keep trial infrastructure + benchmarks active
- Plan for contingency (e.g., bot detection workaround)

### If NO (Fit criteria failed)
**RECOMMENDATION:** ❌ **NO-FIT — Keep Baseline**
- 2Captcha does not solve [specific problem]
- Risk level unacceptable: [specific risk]
- Alternative recommendation: [fallback strategy]

**Action:**
- Archive trial code (keep for future reference)
- Continue current manual Chrome CDP workflow
- Escalate to Dembe (A2) if portal automation is needed

---

## APPENDICES

### A. Cost Breakdown
_[Populated during trial]_

### B. Test Logs & Latency Traces
_[Populated during trial]_

### C. Playwright Sitekey Extraction Debugging
_[Populated during trial]_

### D. 2Captcha API Response Examples
_[Populated during trial]_

---

**Report Status:** 🔴 IN PROGRESS (started 2026-07-06 12:30 MT)  
**ETA:** 2026-07-12 (end of week)

---

**Whetstone — A14**  
*Currency & Razor-Sharp · Co-equal tech principal*
