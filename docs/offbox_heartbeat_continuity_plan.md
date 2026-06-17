# MISSION-220 — Off-Box Heartbeat Continuity Plan
**Owner:** Sterling (A7) | **Status:** DEPLOY-READY — ONE COMMANDER ACTION REQUIRED
**Authored:** 2026-06-17 | **Source SO:** A7 MTBF charter, Baldrige continuity standard

---

## EXECUTIVE SUMMARY

The off-box prober is **already in production**. It is NOT missing. The gap is that
the Telegram alert cannot fire — `TELEGRAM_BOT_TOKEN` is absent from GitHub Actions
Secrets. The prober probes every 15 minutes, detects death correctly, then silently
discards the alert. Green runs in the Actions log prove only the happy path (wing alive).
The failure branch has never executed.

One Commander action closes this. The continuity cert is a forced-failure test
(already staged) that proves the bell rings, not just that the probe runs.

---

## CURRENT STATE — WHAT EXISTS ON-BOX

### hale-cc-heartbeat (on-box, internal)
- **File:** `/home/john/Thunderbird/OpsCenter/hale_cc_heartbeat.py`
- **Timer:** `hale-cc-heartbeat.timer` — fires every 10 min
- **What it does:** Writes a proof-of-life entry to `OpsCenter/hale_shared_state.jsonl`.
  Cross-checks HALE-OC liveness. Satisfies CR-3 in `thunderbird_coo_watchdog.py`
  (threshold: 15 min).
- **Limitation:** Runs ON Yoga. If Yoga dies, this timer dies with it. It cannot detect
  total host failure. It is a within-box health check, not an outage detector.

### jet-heartbeat (on-box, internal)
- **Timer:** `jet-heartbeat.timer` — 10-min interval
- Same on-box limitation.

### thunderbird-watchdog, thunderbird-sentinel, etc.
All 30+ systemd timers listed by `systemctl --user list-timers` are on-box processes.
None survive a Yoga shutdown, power loss, or tunnel death.

---

## CURRENT STATE — WHAT EXISTS OFF-BOX (ALREADY DEPLOYED)

### GitHub Actions — Off-box Wing Heartbeat
- **File:** `/home/john/Thunderbird/.github/workflows/offbox_heartbeat.yml`
- **Schedule:** Every 15 minutes (`*/15 * * * *`), plus `workflow_dispatch`.
- **Architecture (PULL model):** GitHub's runners (external to Yoga) probe
  `https://api.d2mluxury.quest/health` from the public internet. Any HTTP response
  (including 401) = host + tunnel alive. HTTP 000 = unreachable.
- **Debounce:** 3 consecutive probes ~1 min apart before alerting — filters transient
  blips.
- **Recent runs:** 5 consecutive green (wing alive). Probe logic confirmed functional.

---

## THE GAP — ALERT LEG IS SILENTLY BROKEN

From the GitHub Actions run log (run `27640186059`, `27671101352`, and all others):

```
env:
  BOT:       ← empty string
```

`gh secret list` returns empty. `TELEGRAM_BOT_TOKEN` has never been set as a
GitHub Actions secret.

**Consequence:** When the probe detects death, the `curl` alert call fires against
`https://api.telegram.org/bot/sendMessage` (bare slash, no token). The Telegram API
rejects it. The script swallows the error (`|| true`). No page is ever delivered.
The Commander does not know Yoga is down.

The dead-man's switch is installed. The bell is disconnected.

**Verified:** The token for bot ID `8754681793` (D2MC2C bot) exists in
`/home/john/Thunderbird/.env` as `TELEGRAM_BOT_TOKEN`. It has never been loaded into
GitHub Actions Secrets.

---

## ARCHITECTURE DECISION — PULL VS PUSH VS BOTH

### Path A — GitHub Actions PULL prober (CURRENT, already deployed)
- External runner probes Yoga every 15 min. Alerts on sustained unreachability.
- Pros: zero on-box cost, no emitter script needed, debounced.
- Cons: GitHub disables scheduled workflows after 60 days of repo inactivity. A dead
  prober is silent — the same failure mode as no prober.

### Path B — Yoga emits a push heartbeat to an external dead-man service
- Yoga pings out to a URL (e.g., healthchecks.io, ntfy.sh, or a Cloudflare Worker)
  every 10 min. If pings stop, the external service alerts.
- Pros: inverts the failure mode — silence = alarm (vs. silence = unknown). Survives
  GitHub workflow inactivity suspension.
- Cons: requires standing up and maintaining a second external service; one more
  credential to rotate.
- Status: `yoga_heartbeat_check.sh` in `deploy/offbox_heartbeat/` is a richer probe
  script (public + tailscale fallback, edge-triggered alerts, recovery message). It is
  NOT the push emitter — it is a pull prober designed to run on a SECOND HOST (not Yoga).
  It is not staged for deployment here.

### RECOMMENDED ARCHITECTURE

**Layer 1 (immediate):** Fix the GitHub Actions pull prober — set the secret. Enforces
the minimum bar: off-box detection that alerts.

**Layer 2 (next cycle, P3):** Add a Yoga-side push emitter to healthchecks.io (free tier,
no infrastructure cost). This inverts the failure mode and guards against GitHub
workflow suspension. Script is easy — a one-line curl in a systemd timer. Build only
after Layer 1 is certified.

**Layer 3 (future):** If a second always-on host (VPS, Chromebook on, etc.) becomes
available, `yoga_heartbeat_check.sh` can run there as a dedicated pull prober with
richer logic (Tailscale fallback, recovery pages).

---

## STAGED ARTIFACT — FORCED-FAILURE CERT TEST WORKFLOW

File staged (inert — never auto-runs, `workflow_dispatch` only):

```
/home/john/Thunderbird/.github/workflows/offbox_heartbeat_force_fail_test.yml
```

What it does:
1. Points the probe at `http://192.0.2.1/health` (RFC 5737 TEST-NET — guaranteed
   unreachable from any GitHub runner, never routes anywhere).
2. Asserts all 3 checks return HTTP 000.
3. Fires the Telegram alert path against the real Commander chat (7554895206).
4. Checks the Telegram API response — fails the workflow if `ok != true`.
5. If the Commander receives a Telegram message from this test, the alert leg is
   operational.

Protection: requires `confirm: CERT` input to prevent accidental trigger. Never scheduled.

---

## COMMANDER DEPLOY ACTIONS (THREE STEPS, IN ORDER)

The cert workflow is staged locally but not yet on GitHub — `workflow_dispatch` only
finds workflows on the default branch. Step 1 pushes it. Steps 2-3 activate and
certify.

### Step 1 — Push the cert-test workflow to GitHub (the only non-secret push tonight)
```bash
cd /home/john/Thunderbird
git add .github/workflows/offbox_heartbeat_force_fail_test.yml
git commit -m "stage: MISSION-220 forced-failure cert test workflow (inert, dispatch-only)"
git push origin master
```
This is the only file going in. The workflow is never auto-scheduled. It can only run
when you invoke it.

### Step 2 — Set the missing secret (interactive — never embed in shell)
```bash
gh secret set TELEGRAM_BOT_TOKEN
# When prompted, paste the value of TELEGRAM_BOT_TOKEN from /home/john/Thunderbird/.env
# Do NOT copy-paste from shell history or a command line — type/paste interactively.
```
This is the alert activation. Until this step completes, the prober runs but cannot page.

### Step 3 — Run the forced-failure cert test (see Certification Procedure below)
```bash
gh workflow run offbox_heartbeat_force_fail_test.yml -f confirm=CERT
```
Confirm a Telegram page arrives. That is the cert.

---

## CONTINUITY CERTIFICATION PROCEDURE

**Run this sequence AFTER setting the secret.**

### Step 1 — Verify secret is set
```bash
gh secret list
# Expected: TELEGRAM_BOT_TOKEN  Updated: <today>
```

### Step 2 — Run the forced-failure cert test
```bash
gh workflow run offbox_heartbeat_force_fail_test.yml -f confirm=CERT
```

### Step 3 — Confirm Telegram page arrives
Check Commander's Telegram chat (D2MC2C bot). The cert message will read:

> "CERT TEST — Off-box heartbeat alert path is CONFIRMED LIVE. If you see this
> Telegram message, the dead-man switch will ring when Yoga goes down. — Sterling/A7
> MISSION-220 continuity cert"

### Step 4 — Review the workflow run log
```bash
gh run list --workflow=offbox_heartbeat_force_fail_test.yml --limit=1
gh run view <run_id> --log | tail -20
# Expected: "CERT PASSED: Telegram page delivered. Alert leg is operational."
```

### PASS CRITERIA (all four must be true)
| Criterion | Verify how |
|-----------|-----------|
| All 3 probes returned HTTP 000 (forced dead URL) | run log |
| Telegram API returned ok=True | run log |
| Commander received the Telegram message | Commander confirms |
| Workflow exit code 0 | gh run status |

**CERT FAILS if:** secret is empty, Telegram API rejects the call, or Commander
does not receive the message. Do not close MISSION-220 on a partial pass.

---

## KNOWN RISKS AND MITIGATIONS

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| GitHub disables scheduled workflow after 60 days repo inactivity | MEDIUM — if no commits for 60d | Layer 2 push emitter (healthchecks.io) inverts failure mode. Next cycle. |
| GitHub cron jobs delayed up to 10+ min under load | LOW — real outage detected within 25-30 min | Acceptable. Alert latency < 30 min is the target. |
| Bot token rotation — secret goes stale | LOW — bot tokens don't auto-expire | Add to quarterly credential rotation checklist. |
| Tailscale fallback not covered | LOW — primary probe is public HTTPS | `yoga_heartbeat_check.sh` has tailscale probe for future Layer 3. |
| Alert path failure is silent (was our bug) | NOW CLOSED — cert test makes it visible | Re-run cert test whenever bot token is rotated. |

---

## COMPOUNDING RULE (A7 Standing — SO Compounding Protocol)

**"Any alerting or monitoring path must be proven with a forced-failure test before
it is counted as deployed. Green runs in the happy path are not a deployment cert."**

This rule applies permanently to:
- Any new monitoring workflow added to `.github/workflows/`
- Any new Telegram alert hook (fare-watch, lifecycle, sentinel)
- Any watchdog that uses `|| true` swallowing

Owner: Sterling (A7). Enforcement: add forced-failure test workflow alongside every
new alerting workflow, run it at deployment time, log pass/fail in `a7_metrics_dashboard.json`.

Metric: `alerting_paths_certified_pct` — target 100%. A path that has never fired its
alert is NOT certified regardless of green runs.

---

## KPI IMPACT

| KPI | Current | After cert |
|-----|---------|-----------|
| `mtbf_per_service` — off-box detection coverage | 0% (alert broken) | 100% (alert proven) |
| `alerting_paths_certified_pct` | 0% | 100% for off-box path |
| Max alert latency on total Yoga failure | INFINITE (silent) | ≤30 min |

---

## WHAT IS NOT STAGED (BY DESIGN)

- **Secret value** — not committed anywhere. Commander sets interactively.
- **Layer 2 push emitter** — not built tonight. Next cycle after cert.
- **`yoga_heartbeat_check.sh` deployment** — not wired. Requires a second host.
  File remains in `deploy/offbox_heartbeat/` as a future Layer 3 artifact.
- **No changes to mission_board.json** — per Commander directive this cycle.
- **No changes to the 6 protected email/relay files.**

---

*A7 Sterling — MISSION-220 Continuity Assessment*
*Path to cert: 1 Commander action + 1 forced-failure test run*
