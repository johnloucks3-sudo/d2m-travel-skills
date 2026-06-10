# SCRAPING METRICS FRAMEWORK
## Owner: A7 Sterling | Enforced By: Hale | Effective: 2026-06-10
## Standing Order: Commander directive 2026-06-10 — "Sterling start metrics for scraping"

---

## MANDATE

Every scraping session produces an AAR. Metrics are tracked per portal, not per scrape.
Goal: improve time, accuracy, efficiency. Eliminate recurring obstacles. Measure improvement.

---

## TIER 1 — TIME METRICS (Speed)

| Metric | Definition | Target | Source |
|---|---|---|---|
| `session_wall_time_s` | Total seconds from first page hit to last result saved | Regent: ≤90s / 6 bkg | session AAR |
| `time_per_booking_s` | Avg seconds per booking page (parallel wall / booking count) | ≤15s avg | session AAR |
| `speedup_vs_sequential_pct` | (sequential_est - actual) / sequential_est × 100 | ≥70% | session AAR |
| `login_time_s` | Seconds from start to first authenticated page load | ≤20s | session AAR |
| `cookie_inject_time_s` | Seconds to inject cookies and reach authenticated state | ≤5s | session AAR |

**Why:** Wall-clock is the only metric that matters operationally. If a scrape takes 4 minutes, Commander gets stale data while waiting.

---

## TIER 2 — ACCURACY METRICS (Data Quality)

| Metric | Definition | Target | Source |
|---|---|---|---|
| `fields_populated_pct` | % of expected fields with non-empty values (booking_id, amount_due, voyage_name, ship) | ≥85% | per-session validation |
| `amount_due_accuracy_pct` | Portal $ matches dossier $/Harlan figure — cross-verified | 100% | Harlan sign-off |
| `false_zero_count` | Times `amount_due = 0` when booking is NOT paid in full | 0 | manual review after session |
| `page_parse_miss_rate` | % of bookings where parser returned empty for known-present fields | ≤5% | session AAR |

**Why:** A "0" amount_due is the worst failure mode — looks like paid when it isn't. False zeros must be caught every session.

---

## TIER 3 — EFFICIENCY METRICS (Waste Elimination)

| Metric | Definition | Target | Source |
|---|---|---|---|
| `retry_count` | Total page retries this session | ≤1 | session AAR |
| `manual_fallback_count` | Times human had to intervene (wrong URL, expired cookie, CAPTCHA) | 0 (target) | session AAR |
| `session_setup_overhead_s` | Time from session open to first authenticated page hit | ≤30s | session AAR |
| `cookie_ttl_hours` | Remaining TTL on cookies at session end | Regent: ≥24h | creds/*.json expires |
| `parallel_efficiency_pct` | actual_time / (max_single_booking_time) × 100 — 100% = perfect parallel | ≥80% | session AAR |

---

## TIER 4 — OBSTACLE METRICS (Friction Registry)

| Metric | Definition | Target | Source |
|---|---|---|---|
| `obstacles_encountered` | Count of distinct blockers hit this session | 0 (habitual) | obstacle log |
| `recurring_obstacle_count` | Count of obstacles flagged in prior AAR that hit again | 0 (after fix) | obstacle log cross-ref |
| `obstacle_ttff_s` | Time To First Fix — seconds from obstacle identification to workaround applied | ≤120s | session AAR |
| `obstacle_elimination_rate_pct` | % of prior-session obstacles that did NOT recur (proof of fix) | ≥80% / quarter | quarterly roll-up |

---

## PORTAL BASELINES (Updated Per Session)

| Portal | Login Method | Cookie TTL | Best Session Time | Obstacles On File |
|---|---|---|---|---|
| **Regent Direct** (`rssc.com/agent`) | Headful Firefox + cookie inject | ~40-48h (Akamai) | 46s / 6 bkg (2026-06-10) | Wrong URL (agent/login 404); headless blocked by Akamai Bot Manager |
| **Regent OA** (`rssc.com/agent`) | Same as direct, different account | Same | Same session | Same as direct |
| **Centrav** (`centrav.com`) | Session cookie | Unknown | TBD | reCAPTCHA required for fresh login |
| **Silversea** (`my.silversea.com`) | Unknown | Unknown | FAILED 2026-06-10 | Login URL 404; agent portal path unknown; CTU host bookings may not appear in direct portal |
| **TESS** | JWT bearer token | ~90min | ≤5s | Auth refresh required if >90min since last use |

---

## OBSTACLE LOG

Each obstacle gets a unique ID. Cross-reference in session AARs.

| ID | Portal | Date | Description | Status | Fix Applied |
|---|---|---|---|---|---|
| OBS-001 | Regent | 2026-06-10 | Wrong login URL: `agent/login` → 404. Correct: `agent/default.aspx` | CLOSED | Updated scripts to use correct URL |
| OBS-002 | Regent | 2026-06-10 | Akamai Bot Manager blocks headless Playwright | CLOSED (workaround) | Headful Firefox via XvfbDriver for cookie refresh; headless OK for cookie injection |
| OBS-003 | Regent | 2026-06-10 | `regent_connector.py` is inventory scraper (rssc.com/cruises), NOT booking status | OPEN | Separate `regent_parallel_scrape.py` built; inventory connector marked broken |
| OBS-004 | Regent | 2026-06-10 | Sequential scrape timed out at 240s (6 bookings × ~40s each) | CLOSED | Parallel asyncio.gather() → 46s |
| OBS-005 | Regent | 2026-06-10 | Cookie TTL ~40-48h — requires headful refresh every ~2 days | OPEN (architectural) | Manual refresh via `regent_headful_login.py`; auto-keepalive not yet built |
| OBS-006 | Silversea | 2026-06-10 | `my.silversea.com/Account/Login` → 404 | OPEN | Correct URL unknown; CTU agent portal path needed |
| OBS-007 | Silversea | 2026-06-10 | Booking 506101-26 made via CTU host agency — may not appear in direct portal | OPEN | Need CTU portal URL/login flow |

---

## IMPROVEMENT STRATEGIES

### S1 — Cookie Auto-Refresh (Regent)
**Problem:** Akamai cookies expire in ~40-48h. Every 2 days requires manual headful login.
**Strategy:** Build systemd timer or cron job that runs headful Firefox login every 36h (before expiry).
**Owner:** Sterling (A7)
**ETA:** Next scraping sprint

### S2 — Parser Coverage Improvement
**Problem:** Many fields return empty despite data being on page (guest_name → "DETAILS"; due_date → empty).
**Strategy:** Add text-based extraction for all key fields. Build field-specific regex patterns from actual page `innerText`. Validate against known-good data.
**Owner:** Sterling (A7)
**ETA:** Next scraping sprint

### S3 — Silversea Portal Discovery
**Problem:** No working login URL for Silversea via CTU host agency.
**Strategy:** Manually navigate via browser, document correct URL + selector flow, add to portal registry.
**Owner:** Commander (manually) + Sterling (document)
**ETA:** When Commander can check portal on desktop

### S4 — Regent inventory connector repair or retirement
**Problem:** `regent_connector.py` scrapes cruise inventory, not bookings. Currently 0 rows.
**Strategy:** Either (a) fix selectors for cruise inventory page, or (b) retire it and use `regent_parallel_scrape.py` as the booking data source.
**Owner:** Sterling
**ETA:** Next sprint

---

## QUARTERLY ROLL-UP SCHEDULE

| Date | Action |
|---|---|
| 2026-07-01 | First quarterly roll-up: aggregate session AARs, compute `obstacle_elimination_rate_pct` |
| 2026-10-01 | Second quarterly roll-up |

---

*Sterling A7 owns this document. Hale accountable for not having this before 2026-06-10.*
*Updated after every scraping session.*
