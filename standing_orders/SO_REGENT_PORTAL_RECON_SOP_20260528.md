# STANDING ORDER — REGENT PORTAL RECONCILIATION SOP
## SO Reference: SO_REGENT_PORTAL_RECON_SOP_20260528
## Thunderbird Wing | Dreams2Memories Travel, LLC
## Effective: 2026-05-28 | Authority: A7 Sterling (SO_A7_OVERSIGHT_AUTHORITY_20260513)

---

## ISSUE

Regent Seven Seas portal balances, dossier FPDs, and Booking Master Sheet (bryana/data.json)
have diverged on multiple active bookings. The T3 Wing Exercise (2026-05-28) identified two
confirmed data errors: McLeod booking 2984034 ($450 balance delta + 41-day FPD drift) and
Loucks booking 3122006 (31-day FPD drift). No standing reconciliation procedure existed.
This SOP closes that gap permanently.

---

## AUTHORITY

- **Owner:** A7 Sterling — sole authority on process gate enforcement
- **Executor:** Hale (COS) routes quarterly execution; Harlan (A9) runs commission spot-checks
- **Commander gate:** Any delta > $50 unresolvable by TESS cross-check escalates to Commander
- **Supersedes:** Ad hoc reconciliation practices pre-2026-05-28

---

## SCOPE

**In scope:**
- All active Regent Seven Seas bookings (personal and Outside Agent portal)
- bryana/data.json (Booking Master Sheet JSON)
- Canonical dossiers in `/home/john/Thunderbird/dossiers/`
- Regent personal portal (cookie-jar access via `creds/regent_cookies.json`)
- Regent Outside Agent portal (cookie-jar access via `creds/regent_cookies_oa.json`)

**Out of scope:**
- Viking, Silversea, Oceania, Ponant — covered by separate line-specific SOPs (pending)
- Archived/completed bookings (departure date past)
- TESS as primary source — TESS is tertiary verification only; portal is authoritative

---

## THREE-SOURCE RECONCILIATION PROTOCOL

Every Regent booking must be reconciled across three sources in priority order:

| Priority | Source | Access Method | Authoritative For |
|----------|--------|---------------|-------------------|
| 1 (Primary) | Regent Live Portal | Cookie-jar (see Section 4) | Balance due, FPD, cabin assignment |
| 2 (Canonical) | Dossier file in `dossiers/` | Direct file read | Client details, timeline, lifecycle |
| 3 (Register) | bryana/data.json | JSON field `fpd_amount` | Dashboard display, payment alerts |

**Rule:** When sources conflict, Portal wins. Dossier and Register must be updated to match
Portal within 24 hours of detection. Do not average. Do not split the difference.

---

## CADENCE

**Quarterly full sweep:** 1st business day of each quarter (Jan, Apr, Jul, Oct).
- All active Regent bookings reconciled
- Stale dossiers flagged, archived, canonical updated
- A7 metrics dashboard updated (`OpsCenter/a7_metrics_dashboard.json`)

**Triggered reconciliation:** Fire immediately on any of:
- New booking confirmation received from Regent
- Payment posted or declined
- FPD within 90 days (yellow tier — see Section 6)
- Commander reports a portal figure that differs from dossier

**Post-booking protocol:** Any new Regent booking — reconcile all three sources within 48 hours
of confirmation receipt. Do not wait for quarterly sweep.

---

## PORTAL ACCESS — COOKIE-JAR PATTERN

Regent portals require authenticated session cookies. Do not use username/password flows
in automated scripts — they trigger CAPTCHA and account lockout.

**Personal portal (MyRegent):**
- Cookie file: `/home/john/Thunderbird/creds/regent_cookies.json`
- Access pattern: Playwright headless with cookie injection before navigation
- URL: `https://www.rssc.com/myregent`

**Outside Agent portal (Regent Partner Central):**
- Cookie file: `/home/john/Thunderbird/creds/regent_cookies_oa.json`
- Access pattern: Playwright headless with cookie injection before navigation
- URL: `https://partners.rssc.com`

**Cookie refresh:** Cookies expire. If portal returns 401 or redirect to login:
1. Commander manually logs in via Firefox
2. Export cookies via browser extension (EditThisCookie or equivalent)
3. Overwrite the appropriate `creds/regent_cookies*.json` file
4. Re-run the reconciliation script
5. Flag cookie refresh date in `OpsCenter/a7_metrics_dashboard.json`

**Security:** Cookie files contain authenticated session tokens. Access restricted to
Thunderbird OS processes. Never log cookie content. Never commit cookie files to git.

---

## FPD ALERT TIERS

| Days Until FPD | Tier | Color | Action Required |
|----------------|------|-------|-----------------|
| > 90 | Nominal | GREEN | No action — monitoring only |
| 60–90 | Watch | YELLOW | Surface in morning brief; verify portal balance matches dossier |
| 30–59 | Elevated | ORANGE | Telegram alert to Commander; Dani sends payment reminder email to client |
| 0–29 | Critical | RED | Daily Telegram page until payment confirmed; Commander notified same day |
| Past FPD | OVERDUE | RED/FLASH | Immediate Commander escalation; contact Regent to hold booking |

**FPD source of truth:** Always the Regent portal booking detail page, not the dossier.
Dossier FPD is informational only until verified against portal within the current quarter.

---

## BALANCE DELTA THRESHOLDS

| Delta Size | Action |
|------------|--------|
| < $50 | Auto-correct: update bryana/data.json and dossier to match portal. Log in A7 metrics. |
| $50–$500 | Flag to Commander via Telegram before updating. Include root cause hypothesis. Wait for Commander confirmation before writing to dossier. Update bryana/data.json immediately with portal figure. |
| > $500 | STOP. Escalate to Commander immediately. Do not update any file until Commander reviews portal directly. Open financial commit gate. |

**TESS offline protocol:** If TESS cannot confirm root cause of a delta > $50, flag as
"TESS VERIFICATION PENDING" in the dossier comment. Update portal figure to Register.
Do not block Commander on TESS downtime — portal is authoritative regardless.

---

## COMMISSION CALCULATION METHOD

**D2M markup rate for Regent Seven Seas: 22% (Premium cruise line)**

Formula direction (mandatory — no exceptions):

```
net_usd = client_balance / 1.22
d2m_commission = net_usd * 0.22
```

**Example:** Client balance $11,943.15
```
net_usd        = $11,943.15 / 1.22  = $9,789.47
d2m_commission = $9,789.47  * 0.22  = $2,153.68
```

**QC check:** Commission should equal approximately 18.03% of client balance
($2,153.68 / $11,943.15 = 18.03%). Use this as a sanity gate on Harlan's commission memos.

**Never calculate:** `commission = client_balance * 0.22` — this overstates commission by
applying the 22% to the gross figure rather than the net. Any commission memo showing
commission > 19% of client balance must be returned to Harlan for recheck.

---

## STALE DOSSIER PROTOCOL

A dossier is **stale** when any of the following are true:
- FPD in dossier differs from portal by more than 7 days
- Balance in dossier differs from portal by more than $50
- Dossier last-updated date is more than 90 days old and booking is active
- A newer canonical dossier file exists for the same booking

**Detection:** Quarterly sweep compares portal data to all active dossier files.

**Remediation sequence (mandatory order):**
1. **Banner first:** Prepend STALE/SUPERSEDED HTML comment block to stale file.
   Include: error description, correct figures, superseding file name, A7 authority, date.
2. **Archive:** Move stale file to `dossiers/archive/` directory (or rename with `_STALE` suffix
   if archive move is impractical).
3. **Update canonical:** Update the authoritative dossier with correct portal figures.
4. **Update Register:** Update `bryana/data.json` with corrected `fpd_amount` and `fpd` fields.
5. **Log:** Record stale file detection in `OpsCenter/a7_metrics_dashboard.json` under
   `dossier_sync_success_pct` metric.

**Do NOT delete stale files.** They are evidence of system state at a point in time.
Banner-flag and archive. A7 audits archives quarterly for pattern analysis.

---

## SUCCESS METRICS

| Metric | Target | Red Threshold | Measurement Cadence |
|--------|--------|---------------|---------------------|
| `dossier_sync_success_pct` | >= 95% | < 80% | Quarterly sweep |
| Portal-to-Register delta (open bookings) | $0 | > $50 unresolved >24h | Triggered |
| FPD accuracy (portal vs dossier, days) | <= 7 days | > 30 days | Quarterly |
| Stale dossiers (active bookings) | 0 | > 1 | Quarterly |
| Cookie refresh lag | < 30 days | > 60 days | Monthly |

All metrics written to `OpsCenter/a7_metrics_dashboard.json` after each sweep.
RED items flagged to Hale before 07:00 daily brief.

---

## COMPOUNDING RULE (A7 STANDING)

Every finding from a reconciliation sweep becomes a permanent enforcement rule here —
not a one-time fix. This SOP is a living document. A7 appends new rules after each
quarterly sweep. COS Hale is required to read the current version at each quarterly execution.

---

## T&Q COMPLIANCE

This SOP follows AFH 33-337 Tongue and Quill Staff Paper format:
**ISSUE — AUTHORITY — SCOPE — PROTOCOL — CADENCE — THRESHOLDS — METRICS**

---

*A7 Sterling — Thunderbird Wing — Dreams2Memories Travel, LLC*
*Issued: 2026-05-28 | Next review: 2026-08-01 (Q3 quarterly sweep)*
*Under: SO_A7_OVERSIGHT_AUTHORITY_20260513 | T3 Wing Exercise durable artifact*
