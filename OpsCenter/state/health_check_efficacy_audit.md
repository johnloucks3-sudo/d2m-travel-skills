# Health Check Efficacy Audit — Green-on-Silence Hunt

**Scope:** every `*-health`, `*-watchdog`, `*-monitor`, `*-canary`, `*-probe`, `*-sentinel` unit in `~/.config/systemd/user/`, read-only.
**Run:** 2026-07-30 ~21:00 MDT. **Method:** read every `.service`/`.timer` pair, read the script each one executes, cross-checked claimed status against `systemctl --user is-active` / `is-enabled` ground truth right now.

**Prior art, not re-litigated here:** commit `98009dd1d` (2026-07-29) already fixed a green-on-silence lie in `core/ops/wing_ops_report.py` (rendered "no discrepancies" on an empty denominator). This audit is about the systemd health-check fleet, a different surface.

---

## Headline

- **27 units enumerated.** 3 are meta/remediation tools, not health checks proper (see Out-of-scope). Of the remaining 24:
  - **13 CHECK THE THING** (real probe of the actual dependency) and are currently wired and running.
  - **6 are SUSPECT** (proxy signal, or real check but structurally blind to the thing that actually matters).
  - **5 are BROKEN** (disabled/orphaned, or a check that fabricates success without doing any verification).
- **1 PROVEN LIVE LIE right now:** `hale_state.json.wing_health.chrome_debug_port_9222 = "ONLINE"` while `chrome-debug.service` is `inactive` at this moment. The check that would correct it (`chrome-cdp-health.timer`) has been **disabled since on/before 2026-06-28** (log file's last write) — over a month of silent drift.
- **2 more monitors are currently blind to a real, present-tense gap:** `d2m-healthcheck.timer` is disabled while its two of four watched services (`d2m-api.service`, `d2m-scheduler.service`) are `inactive` right now, and nothing else in the fleet checks those two units.
- **1 monitor fabricates a pass unconditionally:** `hale-xo-sentinel`'s `audit_full_google_apps_governance()` returns a hardcoded `"status": "SUCCESS"` dict — it makes zero API calls to Forms/Tasks/Slides/Drive/Keep/Calendar despite the function name and docstring claiming to verify access to all of them.
- **1 canary has zero possible way to ever fail:** `thunderbird-canary-monitor` (`client_path_canary.py`) only evaluates a static local JSON registry; a failure is recorded exclusively via a manual `--defect` CLI flag that **nothing in the entire codebase calls**. It has said "READY_TO_GRADUATE" every day for the last ~29 days regardless of whether the 3 registered client-path tools actually work.
- **1 monitor is completely orphaned:** `poe-burn-monitor.service` references a `.timer` that doesn't exist (`Wants=poe-burn-monitor.timer` — unit not found) and its own `ExecStart` script (`core/cost_dashboard/daemons/poe_burn_monitor.py`) doesn't exist in the working tree at all (only in 3 abandoned `.claude/worktrees/*` copies). Zero journal entries, ever. It has never run.
- **1 structural proxy risk, not currently lying but capable of it:** `thunderbird-telegram-health.timer` (60s) verifies the Telegram **bot token** is valid by calling `getMe` against Telegram's own servers — it never checks whether `thunderbird-telegram-gw.service` (the local process that actually polls/dispatches Commander messages) is running. `getMe` succeeds regardless of whether Thunderbird's own gateway is alive. Right now `thunderbird-telegram-gw.service` happens to be active, so this is not lying at this instant — but it is structurally incapable of ever detecting that service being down. This is the exact pattern from today's `d2m-telegram.service` finding, just not neutralized on this second instance.

---

## Classification table

| Unit | Cadence | Checks | Classification | Timer state | Would-catch-fail-right-now? |
|---|---|---|---|---|---|
| `ai-auth-probe` | 60min | Real Claude CLI round-trip, Telegram `getMe`, MCP HTTP probe | **CHECKS THE THING** | enabled/active | yes |
| `auto-session-monitor` | 10min | `pgrep` process count (proxy), Qdrant `/collections` (real) | SUSPECT (informational heartbeat, not a pass/fail gate) | enabled/active | partial |
| `cf-agent-identity-monitor` | daily | External CF blog content scan | out-of-scope (intel scanner, not a service health check) | enabled/active | n/a |
| `chrome-cdp-health` | 5min (when running) | Real `curl` to CDP port 9222 | **BROKEN** — correct logic, but timer disabled ~1mo; stale `ONLINE` value now false | **disabled/inactive** | **NO — proven live lie** |
| `ci-sentinel` | 10min | Fleet-wide multi-band scan; explicitly refuses to report "clean" if the scanner itself errors (`OverwatchBlind`) | **CHECKS THE THING** (exemplary anti-lie design) | enabled/active | yes |
| `claude-token-monitor` | 30min | Token/session counting (informational, not pass/fail) | out-of-scope | enabled/active | n/a |
| `d2m-airline-monitor` | daily | Goose/LLM recipe scan of airline route changes | SUSPECT (LLM-graded, not deterministic) | **disabled/inactive** | no |
| `d2m-booking-monitor` | 6h | Playwright live navigation to real booking portals | **CHECKS THE THING** | enabled/active | yes |
| `d2m-healthcheck` | 5min (when running) | `systemctl is-active` on 4 named services + 2 HTTPS roundtrips | **BROKEN** (disabled; no state file exists) | **disabled/inactive** | **NO — and 2 of its 4 watched services (`d2m-api`, `d2m-scheduler`) are inactive right now** |
| `d2m-portal-live-probe` | 10min (when running) | Real HTTP probe with session cookies against Centrav/Perx, login-page detection | **CHECKS THE THING** when running | **disabled/inactive** | no — critical B2B session probes unmonitored |
| `d2m-usage-monitor` | 20min (when running) | Real subprocess call into Claude usage data | CHECKS THE THING when running | **disabled/inactive** | no |
| `email-canary-shadow` | 4h (when running) | Gmail classify-only shadow experiment (not a system health check) | out-of-scope | **disabled/inactive** | n/a |
| `hale_brain_monitor` | 12h | Functional dispatch tests: Claude Code native, OpenCode headless, Telegram simulation | CHECKS THE THING (assumed — not deep-audited for internal swallow) | enabled/active | yes |
| `hale-xo-sentinel` | 15min | 3 sub-checks: real Gmail unread scan (good) / local-file-load-only "writeback" check (weak proxy) / **hardcoded-SUCCESS "governance audit" that calls zero APIs** | **BROKEN** (1 of 3 functions is fully decorative) | enabled/active | one-third **NO** |
| `itinerary-watchdog` | 5min | Real `curl` to :8900 + `systemctl is-active cloudflared`, auto-restarts | **CHECKS THE THING** | enabled/active | yes |
| `mythos-monitor` | weekly | Real fetch of external Anthropic-adjacent URLs for a keyword signal | CHECKS THE THING (external content scan) | enabled/active | yes |
| `opencode-spsa-monitor` | continuous (Type=simple) | Not a checker — consumes cases and executes `systemctl restart` remediations | out-of-scope (remediation executor, not a detector) | active | n/a |
| `poe-burn-monitor` | — | N/A | **BROKEN — orphaned.** No `.timer` unit exists; `ExecStart` script absent from the working tree; zero journal entries ever | linked, **never fires** | **NO — has never run once** |
| `router-health-daemon` | 5min | Calls each registered adapter's own `health_probe()` | CHECKS THE THING (trusts adapter implementations to be real; not independently re-verified in this pass) | enabled/active | yes (assuming adapters are honest) |
| `thunderbird-canary-monitor` | daily | Re-evaluates a static local JSON registry; failure only enters via manual `--defect` CLI call | **BROKEN — self-report with zero callers.** `log_defect()` has no call site anywhere in the codebase; `canary_registry.json` doesn't even exist (falls back to defaults every run) | enabled/active | **NO — structurally cannot fail** |
| `thunderbird-coo-watchdog` | 10min | Real `systemctl is-active` + fleet-wide `list-units --state=failed` + auto-recovery | **CHECKS THE THING** (most comprehensive unit in the fleet) | enabled/active | yes |
| `thunderbird-health-check` (Phase 3A) | 5min | Real Redis connectivity via `PersonaRedisConnector` | CHECKS THE THING | enabled/active | yes |
| `thunderbird-oversight-canary` | 4h | Injects synthetic failures into the oversight pipeline itself and asserts they're detected; distinguishes never-run/stale/failing | **CHECKS THE THING** (gold-standard pattern — the opposite of green-on-silence) | enabled/active | yes — last run 6/6 passed |
| `thunderbird-sentinel` | 5min (was) | `ExecStart=/bin/true` — deliberately stubbed | **BROKEN by design, already documented** (Sterling/A7, 2026-06-10) — not a hidden lie, and now also disabled | disabled/inactive | n/a (known, acknowledged) |
| `thunderbird-sla-monitor` | continuous (Type=simple) | Compares `task_audit_log` active-task elapsed time vs SLA | CHECKS THE THING (depends on `task_audit_log` accuracy, reasonable) | active | yes |
| `thunderbird-telegram-health` | 60s | Telegram `getMe` against the bot **token**, not the local gateway process | **SUSPECT — proxy.** Never checks `thunderbird-telegram-gw.service`; would report LIVE indefinitely even if the gateway crashed | enabled/active | **structurally no, though not lying at this instant** (gw.service happens to be up) |
| `thunderbird-watchdog` (OpsCenter) | 2min | Real `systemctl is-active` on 3 named services + real MCP HTTP POST + queue-stuck + disk | **CHECKS THE THING** | enabled/active | yes |

---

## Proven live lie (right now)

**`chrome-cdp-health` → `hale_state.json`**

- `chrome-debug.service` is `inactive` right now (confirmed via `systemctl --user is-active`).
- `hale_state.json` → `wing_health.chrome_debug_port_9222` = `"ONLINE"`.
- `hale_state.json` → `_meta.last_updated` and `wing_health.last_health_check` are both **fresh (today, 20:58)** — because some *other* process touches the file wholesale — which makes the stale `"ONLINE"` value look current to anyone glancing at the timestamp.
- `chrome-cdp-health.timer` is `disabled`/`inactive`; `logs/chrome_cdp_health.log` (5,462 OFFLINE lines vs 51 ONLINE) was last written **2026-06-28** — the check has not run in over a month.
- A human already caught the real state manually: `hale_memory.md:92` notes "Chrome debug service: `chrome-debug.service` — OFFLINE." The systemd health-check layer never caught up to that fact and has no mechanism to.
- **Fix direction:** re-enable `chrome-cdp-health.timer`, or if Chrome-on-demand is now the intended posture, have the writer either delete the stale key or write `"status": "not monitored"` instead of leaving a truthy `"ONLINE"` behind.

## Currently-blind monitors (disabled, with a live gap behind them)

- `d2m-healthcheck.timer` — disabled. Two of its four watched services, `d2m-api.service` and `d2m-scheduler.service`, are `inactive` right now. No other unit in this fleet checks either of those two services by name. If they're supposed to be down, fine — but nothing is verifying that intentionality, and nothing would alert if they were supposed to be up.
- `d2m-portal-live-probe.timer` — disabled. This is the only real live-session check for Centrav (its own docstring: "Dead = no wholesale quotes") and Perx. Currently unmonitored.
- `d2m-usage-monitor.timer`, `d2m-airline-monitor.timer`, `email-canary-shadow.timer` — all disabled; lower blast radius (usage alerting, market-intel scans) but silently off.

## Decorative / fabricated success

- `core/ops/executive_officer_daemon.py::audit_full_google_apps_governance()` (driven by `hale-xo-sentinel.service`, every 15 min) returns:
  ```python
  return {
      "status": "SUCCESS",
      "apps_governed": ["Gmail", "Sheets", "Drive", "Forms", "Tasks", "Slides", "Calendar", "Keep"],
      "johnloucks3_inbox_protection": "STRICT_ZERO_DELETE_ENFORCED",
      "tcd_rules_enforcement": "ACTIVE"
  }
  ```
  with no API call of any kind above it. This is a check that cannot fail because it never checks anything — verbatim the "swallow to success" pattern, just without even a `try/except` to swallow.
- `client_path_canary.py` (driven by `thunderbird-canary-monitor.service`, daily): failure only ever enters the system via a manual `--defect` flag. `grep -rn "log_defect(\|--defect"` across the repo finds only the function definition and its own arg-parser branch — **zero external callers**. `canary_registry.json` doesn't exist, so every run falls back to the same 3 tools enrolled 2026-06-24 with a 7-day window; today (2026-07-30, day 36) it has said `READY_TO_GRADUATE` for ~29 consecutive days with no possibility of ever showing a defect unless a human remembers to run the flag by hand.

## Orphaned / never-runs

- `poe-burn-monitor.service`: `Wants=poe-burn-monitor.timer`, but `poe-burn-monitor.timer could not be found` — the referenced timer unit does not exist anywhere in `~/.config/systemd/user/`. The service is `linked` but has **zero journal entries** — it has never executed once. Its `ExecStart` script (`core/cost_dashboard/daemons/poe_burn_monitor.py`) is also absent from the live working tree; it only exists inside three stale `.claude/worktrees/*` copies. Poe API burn-rate has effectively zero monitoring despite a unit file existing that implies otherwise.

## Structural proxy risk (not lying this second, but the exact class of bug)

- `thunderbird_bot_healthcheck.py` (`core/monitoring/telegram_bot_healthcheck.py`, driven by `thunderbird-telegram-health.timer`, 60s) pings `getMe` on each bot **token** directly against `api.telegram.org`. This proves the token hasn't been revoked — it says nothing about whether `thunderbird-telegram-gw.service` (the process that actually polls updates and can reach the Commander) is alive. `thunderbird-telegram-gw.service` is `active` right now, so this check is not currently lying — but it has no code path that could ever detect that service being dead. Recommend adding `systemctl --user is-active thunderbird-telegram-gw.service` to the health payload, mirroring the exact fix already applied elsewhere for `d2m-telegram.service` today.

## Exception-swallow scan

Targeted grep for `except: pass` / bare-except-to-default-success patterns across the less-reviewed scripts (`thunderbird_coo_watchdog.py`, `opscenter_watchdog.py`, `claude_token_counter.py`, booking/usage/mythos/email-canary monitors) found no instance of a check's *own pass/fail exception* being swallowed into a false "healthy" report — the swallowed excepts found are all incidental (optional-import fallback, best-effort cleanup), not the detection path itself. The one true "checks nothing" pattern found (`audit_full_google_apps_governance`) doesn't even need a swallowed exception — it just never asks the question.

## Not re-classified (already known/acknowledged, included for completeness)

- `thunderbird-sentinel.service` — deliberately stubbed to `/bin/true` since 2026-06-10 per an explicit code comment (Sterling/A7), rebuild scope held by Commander. Not a hidden lie; now also has its timer disabled.

---

## Recommendation (no changes made — read-only audit)

Highest-value fixes, in order:
1. Re-enable `chrome-cdp-health.timer` or retire the stale key it left behind in `hale_state.json` — this is the one proven-live falsehood.
2. Re-enable `d2m-healthcheck.timer` and confirm whether `d2m-api.service` / `d2m-scheduler.service` being down right now is intentional.
3. Wire `audit_full_google_apps_governance()` to real API calls or delete the function — a hardcoded success is worse than no function.
4. Either wire `client_path_canary.py` to an automated test of the 3 registered tools, or stop running it on a timer — a canary nothing can ever kill isn't a canary.
5. Delete or rebuild `poe-burn-monitor` — the unit file implies coverage that has never once existed.
6. Add a `thunderbird-telegram-gw.service` liveness check to `telegram_bot_healthcheck.py` alongside the token `getMe` ping.
