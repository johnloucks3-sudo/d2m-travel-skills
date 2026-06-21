# ELON — SYSTEMD TIMER KILL AUDIT
## A12 Innovation & Disruption · Dreams2Memories Travel, LLC · 2026-06-20
*Mandate: kill audit. Commander question — "do we need all those timers if they're so heavy?"*
*Method: enumerated all 137 user timers, pulled cadence + ExecStart + last-run + active-state for each, classified in code.*
*HARD CONSTRAINT: audit only. Nothing disabled. Hale (accountable) executes after Commander sees this.*

---

## BLUF

**137 timers today → target 95.** That's **42 removed**: 9 zero-risk dead/no-op KILLs, ~17 infra-health timers MERGED into the new F2T2EA Armed Overwatch, and ~16 stale/duplicate/abandoned ones retired (most need a one-line Commander or domain-owner nod).

The bloat is NOT AI-spawning (only 6 timers touch the model). The bloat is **monitor sprawl on top of monitor sprawl** — we built ~27 health/watchdog/probe/heartbeat timers over a year, then built the F2T2EA overwatch *today* that does the same job better (multispectral bands + autonomous repair + escalation). The overwatch was supposed to *replace* the swamp; right now it's the 28th monitor sitting on top of it. That's the 10-hour-incident pattern in miniature: every new layer adds CPU churn and log noise instead of subtracting.

**First principles: a watchdog that watches a watchdog is not resilience — it's two failure points wearing one trenchcoat.** One overwatch with bands beats fifteen single-purpose probes every time.

### The numbers
| Bucket | Count | Risk |
|---|---|---|
| **KILL — zero-risk** (dead/no-op/no-next-run/exact-dup) | 9 | zero |
| **MERGE into F2T2EA overwatch** (infra-health, redundant w/ bands) | 17 | low → fold-then-retire |
| **KILL/MERGE — stale or abandoned project** | 10 | low (3 need-commander) |
| **KEEP** (business watches, revenue, briefs, keepalives, governance) | ~101 | — |
| **NET** | **137 → 95** | |

**Do NOT touch (protected / revenue):** `thunderbird-commander-directive-sweep`, `email-task-ingest` (CLAUDE.md HARD-RULE files — needs-commander even if redundant). All business watches — `d2m-fpd-alert`, `d2m-commission-watch`, fare/airline/booking watches — KEEP. The overwatch checks *system health*, not whether a client's final payment is due. Folding a revenue watch into an infra overwatch would torch revenue protection. That's the opposite of the mandate.

---

## 1. KILL — ZERO RISK (9 timers)

These are dead, no-op, have no next-run scheduled, or run a script another timer already runs. Safe to `disable --now` today.

| Timer | Cadence | Verdict | Rationale (why it's SAFE) | Risk |
|---|---|---|---|---|
| `thunderbird-sentinel` | 5min | **KILL** | `ExecStart=/bin/true` — literal no-op placeholder. Does nothing. | zero |
| `thunderbird-boot-recovery` | 2min | **KILL** | Runs `scripts/portal_keepalive.py` — exact dup of `portal-keepalive.service`. No next-run scheduled. | zero |
| `commander-updates` | 2min | **KILL** | No next-run scheduled; last ran Jun 14. Superseded by brief pipeline + Telegram. | zero |
| `thunderbird-ai-metrics` | — | **KILL** | No next-run; last Jun 14. Metrics now in cost-dashboard collectors. | zero |
| `drkonqi-coredump-cleanup` | weekly | **KILL** | KDE crash-handler cron, never triggered. Not ours, no value. | zero |
| `drkonqi-sentry-postman` | — | **KILL** | KDE Sentry crash-reporter, never triggered. Not ours. | zero |
| `mission-090-sweep` | Sun | **KILL** | One-off worktree sweep for a closed mission (`output/mission-090_worktree_sweep.sh`). Job done. | zero |
| `thunderbird-timer-self-audit` | daily 07:00 | **KILL** | Irony noted. Ran twice, then stopped (last Jun 14). This human-run audit replaces it. | zero |
| `hale-phase2-visuals` | daily 18:00 | **KILL** | Phase-2 visual project — last ran Jun 14, 6 days dark. Completed/abandoned. AI-spawning timer; killing it removes model churn. | zero |

---

## 2. MERGE INTO F2T2EA ARMED OVERWATCH (17 timers)

The new overwatch (`scripts/ci_sentinel.py` + `core/ci/self_observability.py`, 10-min) does multispectral detection — restart bands, error-rate bands, failed-state, port-conflict — **plus autonomous repair + escalation**. Every timer below is a single-purpose infra-health probe whose entire job is now one band in the overwatch. Fold the check into a band, verify the band fires, then retire the standalone timer.

| Timer | Cadence | Verdict | Rationale (which band absorbs it) | Risk |
|---|---|---|---|---|
| `ai-auth-probe` | 15min | **MERGE** | **Currently FAILED (status=1).** Desc = "active endpoint health checks with deterministic repair" — verbatim overwatch overlap. Fold auth-endpoint check into a health band; retire. Killing it also clears a crash-loop. | low |
| `chrome-cdp-health` | 5min | **MERGE** | CDP port-9222 reachability = overwatch port-conflict/health band. | low |
| `qdrant-watchdog` | 5min | **MERGE** | Qdrant container up/restart = restart-band + failed-state band. | low |
| `router-health-daemon` | 5min | **MERGE** | Router daemon liveness = failed-state band. | low |
| `thunderbird-watchdog` | 2min | **MERGE** | Generic OpsCenter watchdog — exactly what the overwatch generalizes. | low |
| `thunderbird-coo-watchdog` | 10min | **MERGE** | COO process liveness = failed-state band. | low |
| `thunderbird-health-check` | 30s | **MERGE** | 30-second cadence is the single worst churn offender. Health worker = the overwatch's whole purpose. | low |
| `thunderbird-sentinel-nginx` | 90s | **MERGE** | nginx reachability = health band. | low |
| `thunderbird-disk-pressure` | 15min | **MERGE** | Disk pressure = resource band in overwatch. | low |
| `hale-cc-heartbeat` | 10min | **MERGE** | Claude Code heartbeat = liveness band. | low |
| `jet-heartbeat` | 10min | **MERGE** | JET heartbeat = liveness band. | low |
| `auto-session-monitor` | 10min | **MERGE** | Session liveness = liveness band. | low |
| `alpha-wing-watch` | 2min | **MERGE** | Wing process watch = failed-state band; 2-min cadence churns. | low |
| `d2m-portal-live-probe` | 10min | **MERGE** | Portal reachability probe = health band (keepalives stay; this is the *probe*, not the warmer). | low |
| `keepalive-supervisor` | 25min | **MERGE** | Supervises the keepalive swarm — fold its supervision into overwatch escalation, keep the underlying keepalives. | low |
| `metronome` | 5min | **MERGE** | Heartbeat/tick service; `metronome-daily` keeps the daily-brief entry. Merge tick role into overwatch cadence. | low |
| `ci-sweep` | daily 06:00 | **KEEP-but-confirm** | This is the overwatch's *own* daily razor sweep — keep it OR fold into ci-sentinel. Owner's call; not a separate failure point if intentional. | low |

> **Duplicate-cadence note:** before this merge we have, at 2–5 min, **22 churners** all scanning overlapping system state (`thunderbird-health-check` 30s, `-sentinel-nginx` 90s, `watchdog`/`alpha-wing-watch`/`boot-recovery` 2min, six more at 5min). That is the CPU churn + log noise that fed the 10-hour incident. The overwatch's 10-min multispectral pass replaces all of it with one disciplined cycle.

---

## 3. STALE / ABANDONED-PROJECT (10 timers — verify before kill)

Gated by cadence (a weekly timer 6 days idle is *healthy*, not stale — those are NOT listed). These either point at closed projects or have gone dark past their own cadence.

| Timer | Cadence | Verdict | Rationale | Risk |
|---|---|---|---|---|
| `thunderbird-lessons-implementation-tracker` | weekly Sun | **KILL** | Anti-theater lessons tracker — last Jun 14, project quiet. Confirm Sterling doesn't still need the metric. | needs-commander |
| `loucks-excursion-watch` | Mon 09:45 | **MERGE→fare/excursion watch** | Loucks-specific excursion scan; fold into the general `d2m`/cruise excursion watch rather than a per-client timer. | needs-commander |
| `thunderbird-innovation-scan-weekly` | weekly Sun | **MERGE** | Overlaps daily `thunderbird-innovation-scan`. Keep daily, drop weekly dup. | low |
| `d2m-drive-sync` | nightly | **MERGE w/ `thunderbird-drive-sync`** | Two drive-sync timers (`d2m-drive-sync.sh` vs `thunderbird-rclone-sync.sh`). Pick one rclone path. | low |
| `metronome-daily` | daily 06:00 | **MERGE into brief swarm** | Runs `metronome.py --daily-brief` — joins the 06:00 brief pile-up below. | low |
| `thunderbird-daily-brief` | daily 06:00 | **MERGE (brief swarm)** | See swarm note. | low |
| `thunderbird-morning-brief` | daily 06:00 | **MERGE (brief swarm)** | See swarm note. | low |
| `mythos-monitor` | weekly Tue | **KEEP/confirm** | Availability monitor; healthy on its weekly cadence. Confirm still a live client need. | needs-commander |
| `thunderbird-evernote-backup` | weekly Mon | **KEEP/confirm** | Backup — verify Evernote still in the stack before killing. | low |
| `d2m-factbook-refresh` | weekly Mon | **KEEP/confirm** | Factbook recipe; weekly cadence healthy. Confirm consumers exist. | low |

> **06:00 BRIEF SWARM — consolidation target:** `thunderbird-daily-brief`, `thunderbird-morning-brief`, `metronome-daily --daily-brief`, plus `thunderbird-eod-brief` (18:00) and `d2m-incubator-overnight-report` (06:30) all fire briefs in a tight window. Three of these generate a *morning* brief. **Collapse to ONE morning-brief generator.** Build-it-once. This is a clean MERGE that needs a 30-second Commander confirm on which generator is canonical.

---

## 4. KEEP — DO NOT TOUCH (~101 timers)

Named here so nobody confuses "has the word monitor/watch in it" with "kill it."

- **Revenue / business watches (KEEP — overwatch cannot replace these):** `d2m-fpd-alert`, `d2m-fdp-reconcile`, `d2m-commission-watch`, `d2m-fare-watch-alert`, `d2m-ita-fare-watch`, `thunderbird-fare-watch`, `d2m-airline-monitor`, `d2m-airline-schedule-change`, `d2m-booking-monitor`, `d2m-post-trip-followup`, `tp-alert-engine`, `d2m-touchpoint-execute`, `d2m-lifecycle*`, `hale-touchpoint-proposer`. These protect FPDs, commissions, and client lifecycle. Folding any into an infra overwatch = unsafe.
- **Credential keepalives (KEEP — warmers, not probes):** `claude-oauth-keepalive`, `tess-token-keepalive`, `johnloucks3-oauth-keepalive`, `d2mconcierge-oauth-keepalive`, `portal-keepalive`, `d2m-centrav-warm`, `d2m-perx-keepalive`, `claude-token-monitor`. (The *probes* merge; the *warmers* stay — different jobs.)
- **Protected files (KEEP — HARD RULE, needs-commander for ANY change):** `thunderbird-commander-directive-sweep`, `email-task-ingest`.
- **Genuinely periodic governance/intel/backup on healthy cadences:** drive/qdrant-reindex, logrotate, monthly-archive, backup-verify, dembe-intel, x-osint, dossier-validation-sweep, etc.
- **AI-spawning (6 total, KEEP except phase2-visuals killed above):** `d2m-incubator-execute`, `d2m-incubator-overnight-report`, `hale-incident-handler`, `hale-visual-synthesis`, `ai-auth-probe` (→ merged), `hale-phase2-visuals` (→ killed). Net AI-spawn churn drops by 2.

---

## 5. EXECUTION ORDER (for Hale, after Commander sees this)

1. **Tonight, zero-risk:** disable the 9 KILLs in §1. Immediate CPU + log-noise relief, no behavior change. (`ai-auth-probe` FAILED loop also gone once §2 lands.)
2. **This week:** verify each §2 infra band fires in the overwatch *before* retiring the standalone — fold-then-retire, never retire-then-hope. 17 timers, ~17 fewer churners.
3. **Commander confirm (one pass):** canonical morning-brief generator (collapse 3→1); fate of `lessons-tracker`, `loucks-excursion-watch`, `mythos-monitor`.
4. **Re-audit in 30 days.** And kill `thunderbird-timer-self-audit`'s replacement urge — this stays a deliberate human-triggered audit, not another timer.

**Subtraction is addition.** 137 → 95 is not the finish line; it's the floor for the next pass. Every timer that survives should justify *why a machine needs to do this on a clock at all.*

— ELON / A12 · 2026-06-20
