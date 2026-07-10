# SESSION RESUME — CI Razor-Sharp Gap Scan — 2026-07-09 (RAZORBACK)
**Codeword: `RAZORBACK`** — this session's full triage is now COMPLETE and CLEAN.

## ✅ FIXED THIS PASS (real root causes, independently verified — not self-report)

1. **`/tmp` tmpfs quota exhaustion — THE ACTUAL cause of the prior Bash-tool outage.**
   `/tmp` is tmpfs with a `usrquota`, hard-capped at 6.7GB. Flatpak Google Chrome
   (PID 12460, running since 2026-07-08, your interactive desktop browser — NOT
   automation) was leaking V8/shared-memory cache blobs directly into `/tmp` as
   `.{hash}-00000000.so` files (~13MB each) instead of using `/dev/shm` — almost
   certainly a Flatpak sandbox `/dev/shm` passthrough gap. Found 403 files / 5.2GB,
   verified via `fuser`+`lsof` that NONE were held open by any process (pure garbage),
   deleted all. `/tmp` back to 291M/6.7G (5%). **Did not touch the live Chrome
   process** — it may hold your session/tab state, not worth killing without asking.
   **Will recur** as long as that Chrome instance runs. Real fix options: (a) a safe
   periodic cleanup timer (checks `fuser` before deleting, never touches live files —
   cheap, zero risk), (b) `flatpak override --filesystem=/dev/shm` for this Chrome
   install, (c) you restart Chrome periodically. Recommend (a) — filed to fleet below.

2. **CI registry write-back bug — root cause found and fixed** (the prior session's
   diagnosis of "malformed required field" was WRONG — re-ran the exact check, zero
   missing required fields, `load_registry()` never raised). **Actual bug:**
   `qdrant-memory`'s `last_reeval` field held a full ISO datetime
   (`"2026-07-04T22:19:13.975024+00:00"`) instead of a plain date.
   `core/ci/registry.py::_age_days()` does `d.split("-")` expecting exactly
   `YYYY-MM-DD` — the datetime string crashes `int()` mid-parse. This exception fired
   inside `sweep()`'s per-entry loop, **before** the single end-of-loop registry file
   write — so every entry after the crash point silently never got a fresh
   `last_verified`, going back to the last time the loop completed clean
   (2026-07-04 20:01:52, matching the 34 entries frozen at that exact millisecond).
   This explains why `ci-sweep.timer` fired daily for 5 days with zero visible effect —
   it was crashing every single run. **Fixed:** corrected the field to `"2026-07-04"`.
   Ran a live write-enabled sweep: **exit 0, 39/53 entries freshly stamped** (the other
   14 correctly stay unstamped because their probes are genuinely failing — design,
   not a bug).

3. **`~/.cache` bloat (real, separate from #1)** — 4.2GB vs 2GB probe threshold (not a
   real disk-space risk, `/home` has 754GB free — this is a hygiene policy check).
   Cleared regenerable package caches only (pip, uv, npm) — freed ~470MB, still over
   threshold. Left `camoufox`/`mozilla`/`playwright`/`opencode` caches alone —
   actively used by live tools, re-download cost not worth it for a soft metric.
   Note for Whetstone: the 2GB threshold may be unrealistically low given legitimate
   tool caches in this environment — consider raising it or adding an allowlist rather
   than treating this as CRITICAL daily.

4. **`gmail-accounts` — the "never probed, needs a probe written" note from the prior
   session was WRONG.** It already has a working probe
   (`scripts/ci_probe_gmail_accounts.py`), already RAZOR_SHARP. False alarm, correcting
   the record.

## CARRIED FORWARD FROM PRIOR PASS (still valid)
- Dead proxy `127.0.0.1:43117` cleared from systemd --user env — confirmed still clean.
- `fare-watch-centrav` Playwright browser-path probe bug — fixed, confirmed passing.
- `telegram-relay` — confirmed clean, RAZOR_SHARP.

## REAL, VERIFIED GAP LIST (post-fix, live sweep, 2026-07-09 23:11 UTC)

**53 total: 20 RAZOR_SHARP · 15 DULL (currency-stale, probe passes) · 18 REPLACE (genuine failures) · 0 RED**

### REPLACE-tier (real, needs actual engineering — the fleet's target list)
| Tool | Script | Failure pattern |
|---|---|---|
| credential-keepalive | `scripts/keepalive_supervisor.py` | 50 consecutive fails — KNOWN, Regent cookies expired, Commander-gated (manual Firefox re-auth past Akamai), not fleet-fixable |
| email-handling | `scripts/d2m_commander_digest.py` | 50 consecutive fails |
| fare-watch-centrav | `scripts/fare_watch_centrav.py` | 47 fails/7d |
| fare-watch-ita | `scripts/ita_fare_watch_poll.py` | 50 consecutive fails |
| fare-watch-amadeus | `scripts/amadeus_fare_watch.py` | 42 fails/7d — API key gate, Commander-owned |
| supertimer-bot-health | `supertimer/leader.py` | 50 consecutive fails, Firefox dependency |
| cruise-intelligence | `intel/cruise_critic_monitor.py` | 50 consecutive fails |
| github-actions | GitHub Actions + GITHUB_TOKEN | 50 consecutive fails — API key gate, Commander-owned |
| lifecycle-dossiers | `core/ops/dossier_freshness.py` | 50 consecutive fails |
| lifecycle-travel-surveys | `scripts/travel_survey_generator.py` | 50 consecutive fails |
| lifecycle-booking-surveys | `scripts/booking_survey_generator.py` | 50 consecutive fails |
| lifecycle-excursion-engine | `scripts/excursion_engine.py` | 50 consecutive fails, Chrome:9222 dependency (soft-fail, already noted) |
| hotel-scan | `scripts/hotel_scan.py` | 50 consecutive fails |
| transfer-scan | `scripts/transfer_scan.py` | 50 consecutive fails |
| infisical | docker: infisical+postgres+redis :8899 | 25 fails/7d — 7-day file-based-creds canary in progress, expected |
| home-dir-health | `scripts/home_dir_ci_probe.py` | 50 consecutive fails — `~/.cache` threshold, see #3 above |
| d2m-inbox-triage | `scripts/d2m_inbox_triage.py` | 3 consecutive fails (just crossed threshold) |
| tech-adoption | `api/thunderbird_power_harvest.py` | 6 fails/7d — probe itself passes (`ok`), REPLACE fired on trailing history only |

### Already-accepted, not new gaps
`fare-watch-amadeus`, `github-actions` — Commander API-key gate. `lifecycle-excursion-engine` —
Chrome:9222 soft-fail. `infisical` — 7-day canary in progress. `credential-keepalive` —
MISSION-820/1563, Commander-gated Regent re-auth.

### DULL-tier (currency/re-eval window passed, underlying tool actually works —
lower priority, self-clears now that `ci-sweep.timer` runs clean daily)
self-observability, client-path-canary, dani-identity-layer, pii-governance,
regent-portal-live, n8n, cloudflared-tunnel, ttyd, tailscale, gdrive-mx, evernote-mx,
cruise-db-site, reverie-app, qdrant (docker), litellm-gateway.

## FLEET COMMISSIONED (this session, per Commander's standing "burn hot, don't wait")
Dispatched a14-whetstone (razor-sharp/replacement fleet owner) + a7-sterling (process
gate) against the REPLACE-tier list above, background. Client-affecting item
(credential-keepalive/Regent) stays Commander-gated, not touched by the fleet.

## CLEANUP DONE
- `core/ci/_tmp_missing_fields_check.py` + `_result.json` — deleted (superseded by real fix).
- 403 leaked `/tmp/.*-00000000.so` files — deleted (5.2GB freed).
- pip/uv/npm caches — purged (~470MB freed).
