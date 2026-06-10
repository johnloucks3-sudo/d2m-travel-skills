# SESSION AAR — [PORTAL] — [DATE]
## Owner: Sterling (A7) | Trigger: Every scraping session (not every scrape)

---

## 1. SESSION SUMMARY

| Field | Value |
|---|---|
| Date | YYYY-MM-DD |
| Portal(s) | [Regent / Silversea / Centrav / TESS] |
| Bookings targeted | [count] |
| Bookings retrieved | [count] |
| Session wall time | [X]s |
| Conducted by | [Hale / Sterling / script] |

---

## 2. METRICS — THIS SESSION

| Metric | Value | Target | Delta |
|---|---|---|---|
| session_wall_time_s | | | |
| time_per_booking_s | | ≤15s | |
| speedup_vs_sequential_pct | | ≥70% | |
| fields_populated_pct | | ≥85% | |
| amount_due_accuracy_pct | | 100% | |
| false_zero_count | | 0 | |
| retry_count | | ≤1 | |
| manual_fallback_count | | 0 | |
| cookie_ttl_hours_remaining | | ≥24h | |
| obstacles_encountered | | 0 | |
| recurring_obstacle_count | | 0 | |

---

## 3. DATA EXTRACTED

| Booking | Client | Amount Due | FPD | Accuracy Check |
|---|---|---|---|---|
| [id] | [name] | $[amount] | [date] | [portal confirmed / discrepancy: $X] |

---

## 4. OBSTACLES ENCOUNTERED

| ID | Description | Time Lost (s) | Fix Applied | SCRAPING_METRICS.md Status |
|---|---|---|---|---|
| [OBS-###] | [description] | [s] | [fix] | [CLOSED/OPEN] |

---

## 5. WHAT WORKED

- [Bullet: technique or approach that saved time or improved accuracy]

---

## 6. WHAT FAILED / COST TIME

- [Bullet: what went wrong, estimated time cost, root cause]

---

## 7. IMPROVEMENTS ACTIONED THIS SESSION

- [Bullet: change made as a result of prior AAR finding]

---

## 8. IMPROVEMENTS TO ACTION NEXT SESSION

| Item | Owner | Priority |
|---|---|---|
| [description] | Sterling / Hale / Commander | P0/P1/P2 |

---

## 9. BASELINE UPDATE

If session establishes a new best time or reveals a new obstacle, update `SCRAPING_METRICS.md`:
- [ ] Portal baseline table updated
- [ ] Obstacle log updated (new entries added, CLOSED entries marked)
- [ ] Improvement strategies updated

---

*Sterling A7 signs off. Filed to `output/scraping_aar/`.*
