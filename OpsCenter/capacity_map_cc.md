# CAPACITY MAP — CC (Claude Code / Claude MAX)

**Prepared by:** A7 Sterling ("Gauge") · **Date:** 2026-07-30 12:35 MT
**Method:** read-only investigation. Nothing modified. No prompt-consuming Claude call made.

---

## 1. THE LIVE DATA SOURCE (primary deliverable)

The chyron is `~/.claude/hud/metricc-cc-statusbar.mjs`, wired at
`/home/john/.claude/settings.json:177` (`"statusLine": { "command": "node ~/.claude/hud/metricc-cc-statusbar.mjs" }`).

Its rate-limit numbers come from **one HTTPS call**:

```
GET https://api.anthropic.com/api/oauth/usage
Authorization: Bearer <accessToken from ~/.claude/.credentials.json → claudeAiOauth.accessToken>
anthropic-beta: oauth-2025-04-20
Content-Type: application/json
```

- Source of code: `fetchUsage()` at `metricc-cc-statusbar.mjs:243-264`; token load at
  `getCredentials()` :175-206; orchestration at `getUsage()` :278-316.
- **Cache:** `~/.claude/hud/.usage-cache.json`, TTL **60 s** (15 s on failure). The statusline
  hits the network at most once a minute; every render in between reads the cache file.
- **Token refresh:** if `expiresAt` has passed it POSTs `platform.claude.com/v1/oauth/token`
  (`refreshAccessToken()` :208-241) and **writes back** to `~/.claude/.credentials.json`
  (`writeBackCredentials()` :266-276). ⚠️ This is a second writer on the credential file
  alongside `claude-oauth-keepalive.timer`. Wing code must NEVER replicate the write-back.
- Everything else on the bar is local: context % and model from the stdin JSON Claude Code
  pipes to the statusline; agent/todo counts from tail-reading the session transcript JSONL;
  version from `registry.npmjs.org` (1 h cache in `.version-cache.json`).

**Liveness proof:** `.usage-cache.json` timestamp advanced 1785435870582 → 1785435959432
(89 s) during this investigation, and its `fiveHour` value moved 36 → 37 in lockstep with my
own independent call to the endpoint. This is genuinely live telemetry.

---

## 2. CURRENT REAL VALUES (measured 2026-07-30 12:25 MT)

Raw response, verbatim fields:

| Window | Utilization | Resets at (UTC) | Resets at (MT) |
|---|---|---|---|
| `five_hour` (session) | **37 %** | 2026-07-30T21:00:00Z | **15:00 MDT today (~2 h 35 m out)** |
| `seven_day` (all models) | **4 %** | 2026-07-31T03:00:00Z | **21:00 MDT TONIGHT (~8 h 35 m out)** |
| `weekly_scoped` (model: "Fable") | 0 % | null | — |

Also returned:
- `limit_dollars`, `used_dollars`, `remaining_dollars` = **null on every window.**
- `extra_usage.is_enabled: false`, `user_disabled: true` — pay-as-you-go overflow is OFF.
- `spend.used = $0.00`, `spend.enabled: false`, `can_purchase_credits: false`.
- `seven_day_opus`, `seven_day_sonnet`, `seven_day_cowork` = null (not broken out for this plan).
- `member_dashboard_available: false`.

> ⚠️ **Do not read "7d 4 %" as a fresh week of headroom.** The 7-day window closes at
> **21:00 MDT tonight**. That is Thursday 21:00 MT — independently corroborated by
> `scripts/update_usage.py`, which hard-codes `reset_day: "Thursday", reset_time_mt: "21:00"`.
> Today is Thursday. The 4 % is the *tail* of the expiring week, not the start of a new one.

### The "$32 on 5h" figure — resolved
The wired statusline **cannot** display dollars for a rate-limit window. `Cost` is `false` in
`~/.claude/hud/config.jsonc`, and even enabled it renders `stdin.cost.total_cost_usd` — a
*per-conversation* cost, not a 5-hour figure. The API returns null for all dollar fields on
this plan. The only local tool that produces 5-hour-block dollars is **`ccusage`**
(`/home/john/.local/bin/ccusage`, installed 2026-03-10, has a `statuslineHookJsonSchema`) —
but it is **not wired into any statusline** and it is **currently non-functional on this
machine**: `ccusage blocks --active` OOMs at the default heap and still times out at 240 s
with a 6 GB heap, defeated by the size of the local transcript corpus. Any dollar figure from
ccusage is in any case a *cost estimate* (local JSONL tokens × published prices), not
plan-limit telemetry. **The OAuth endpoint is the authoritative capacity read.**

---

## 3. THE LIMIT STRUCTURE

Three independent windows, reported as `limits[]`:

1. **`session` / 5-hour** — a rolling 5 h block. `is_active: true` right now. This is the one
   that bites first in heavy sessions. At 100 % Claude Code refuses new turns until `resets_at`.
2. **`weekly_all` / 7-day** — all-models consumption over the trailing week, resets Thursday
   21:00 MT. Hitting this locks the account out for the remainder of the week regardless of
   5 h headroom. This is the dangerous one — there is no waiting it out in a coffee break.
3. **`weekly_scoped` / 7-day scoped** — a per-model sub-cap (currently scoped to "Fable",
   0 %). Historically the "Sonnet only" weekly line on the claude.ai usage screen.

**The absolute limits are not exposed.** Every denominator (`limit_dollars`, `monthly_limit`)
is null. The server returns a normalized percentage; the underlying quota lives server-side
and is invisible from this machine. With `extra_usage` disabled and `can_purchase_credits:
false`, there is no overflow buffer — 100 % means stop.

---

## 4. WHAT CHANGES AT 20X MAX → 5X MAX

**Not discoverable locally — and I will not guess at the multiplier.** What the evidence does
support:

- **Window structure and reset cadence do not change.** 5 h session, 7 d all-models, 7 d
  scoped, Thursday 21:00 MT reset — these are plan-independent mechanics.
- **Only the denominator moves.** Because the endpoint reports *percent of an unstated quota*,
  identical work will consume a proportionally larger percentage. If the tier name is literal
  (20X → 5X), the same session that reads 37 % today would read on the order of ~4× that
  after the drop — i.e. today's 37 % becomes a limit-hit. Treat that as the planning
  assumption, not a measured fact.
- **The tier string itself is readable in exactly one local place, and it is broken.**
  `scripts/push_claude_usage.py` scrapes `max\s*\(\d+x\)` off the claude.ai settings page via
  Chrome CDP. That path is dead (see §6). Once the Commander's plan changes, **the only
  way to confirm the new tier from this machine is that scraper** — or the Commander reading
  the settings page directly.
- **Operational consequence:** at 5X the 7-day window becomes the binding constraint far
  earlier. Current burn (4 % over a near-complete week) would land near ~16 % at 5X — still
  safe — but a heavy build week that reads 60 % today would read ~100 % and hard-stop.

---

## 5. RECOMMENDED PROGRAMMATIC READ PATH

**Authoritative:** the OAuth usage endpoint. Wing code should not re-invent the transport.

Recommended shape for a new `core/relay/cc_capacity.py`:

1. Read `~/.claude/hud/.usage-cache.json`. If `Date.now() - timestamp < 60_000`, **use it** —
   the statusline already paid for that call. Free, zero network, zero risk.
2. Only if stale, make the GET yourself with the token from
   `~/.claude/.credentials.json` → `claudeAiOauth.accessToken`.
3. **If the token is expired, fail soft** and return `UNKNOWN`. Do **not** refresh, and do
   **not** write `.credentials.json` — `claude-oauth-keepalive.timer` owns that file, and
   metricc is already a second writer. A third writer is a credential-corruption path.
4. Write your own cache to `OpsCenter/`. Do not write `~/.claude/hud/.usage-cache.json` —
   that file is owned by a third-party tool.
5. Expose `{five_hour_pct, five_hour_resets_at, seven_day_pct, seven_day_resets_at,
   source: "oauth"|"hud_cache"|"unknown"}`. Never emit a fabricated number when the read
   fails — `UNKNOWN` is a valid, honest state.

### Verdict on the existing files

| File | Status | Finding |
|---|---|---|
| `OpsCenter/claude_usage_status.json` | **DEAD — do not read** | Last written 2026-06-18; all counters 0; `last_message_at` 2026-03-31. Models a retired regime (message counts: 225/session, 1500/week, 25 Sonnet/day) that no longer matches how the plan is metered. Consumed by `OpsCenter/harlan_cost_monitor.py` — which is therefore reporting on a corpse. |
| `OpsCenter/claude_usage_tracker.py` | **DEAD** | Last modified 2026-03-31. Writer of the above. Referenced only by itself and `core/ops/thunderbird_ai_metrics_dashboard.py`. |
| `scripts/push_claude_usage.py` | **LIVE TIMER, ZERO OUTPUT** | See §6. |
| `core/relay/engine_limits.py` | **CORRECT BUT OUT OF SCOPE** | Tracks OC and AG only, by counting dispatches in a local JSONL ledger against Wing-invented caps (`OC 30/h`, `AG 20/h`). It has **no CC concept at all** and no notion of server-side quota. Extend it with a `CC` branch that delegates to `cc_capacity.py` — do not try to model CC by counting calls; the server's percentage is ground truth. |
| `~/.claude/hud/.usage-cache.json` | **LIVE, AUTHORITATIVE (60 s)** | The only live CC telemetry artifact on this machine. |

---

## 6. FINDINGS (metric · threshold · owner)

**F-1 — `claude-usage-push.service` is a false-green no-op burning resources.**
The timer fires **every 2 minutes** (720×/day). Every run fails: `[push_usage] CDP not
reachable: connect ECONNREFUSED ::1:9222`. The unit declares `SuccessExitStatus=2 3 5`, so
systemd reports **"Finished"** on every failure and no alert ever fires. Each run costs
~725 ms CPU and a 168.4 MB memory peak (it spins up Playwright/Chromium bindings to fail).
Root cause is systemic, not operator error: Chrome on this box is **Flatpak**, so the
`--remote-debugging-port=9222` flag is silently dropped — a known, already-documented trap.
The design also requires a human to keep a browser tab parked, which is not a process, it is
a hope.
- *Metric:* `push_usage_success_rate` — successful pushes ÷ timer firings, 24 h rolling.
- *Threshold:* < 90 % = RED. **Current: 0 %.**
- *Fix:* retire the script and its timer; replace with the OAuth read in §5, which needs no
  browser, no tab, and no human. Retain the `max\s*\(\d+x\)` tier-scrape logic only as the
  documented manual fallback for §4.
- *Owner:* A7 (Sterling).

**F-2 — `SuccessExitStatus` whitelisting of dependency failures is a fleet-wide anti-pattern.**
This unit converts "my dependency is gone" into "success." Any unit that whitelists a
failure exit code must emit a metric instead, or the failure is structurally invisible.
- *Metric:* `units_with_success_exit_whitelist` — count across `~/.config/systemd/user/`.
- *Threshold:* any unit whitelisting a code without a companion health metric = finding.
- *Owner:* A7 — fold into the weekly Baldrige sweep as a permanent rule, not a one-time fix.

**F-3 — Three CC-usage code paths, zero of them authoritative, all disagreeing.**
`claude_usage_status.json` (zeros, message-count model), `push_claude_usage.py` (browser
scrape, 0 % success), and `engine_limits.py` (call-counting, no CC branch) coexist while the
one live source is a third-party statusline cache nobody in Wing code reads.
- *Metric:* `cc_capacity_readers_on_authoritative_source` ÷ total CC-capacity readers.
- *Threshold:* < 100 % = finding. **Current: 0/3.**
- *Fix:* build `cc_capacity.py` per §5; delete F-3's dead paths; repoint
  `harlan_cost_monitor.py` and `thunderbird_ai_metrics_dashboard.py`.
- *Owner:* A7, with CC implementing.

**F-4 — `ccusage` is installed but cannot run to completion.**
OOM at default heap; times out at 240 s with 6 GB. The transcript corpus has outgrown it.
Not load-bearing (nothing is wired to it), so this is INFO, not RED — but it should not be
counted as an available cost-telemetry tool in any plan.
- *Owner:* A7 — flag for retirement in the next tech-debt scan.

---

## 7. SAFETY STATEMENT

Read-only throughout. No file in `~/.claude/`, no `settings.json`, and no live data file was
modified by this investigation. One GET to `/api/oauth/usage` was made — that endpoint reports
the meter and does not move it. No Claude prompt was consumed.

*— A7 · Brig Gen (Ret.) Thomas "Gauge" Sterling · 2026-07-30 12:35 MT*
