# CI RAPID REPAIR — Operator Runbook
*Dreams2Memories Travel, LLC · Thunderbird Wing · Sterling (A7) · 2026-07-02*

## What changed (the cutover)

The infra_bot heartbeat used to spawn `core/ci/ci_auto_repair_engine.py`, whose
`main()` fired **every** raw `repair_*` function unattended on every RED
heartbeat — including destructive ones (source-file rewrites, `settings.json`
edits, registry recreation) with **no tier gate**. That was the keystone hazard.

As of 2026-07-02 both live auto-repair paths route through the **safety-contract
runner** instead:

| Path | Trigger | Now routes through |
|---|---|---|
| Heartbeat | `infra_bot` → `ci_auto_repair_integration.trigger_auto_repair()` | spawns `core/ci/repairs/rapid_repair.py` **detached** → `run_all_red()` |
| CI sweep | `scripts/ci_sweep.py` / `ci_daily_routine.py` → `ci_health.sweep()` → `_try_repair()` | `run_capability(..., armed_tiers=policy)` |
| systemd timer | `ci-auto-repair.timer` → `ci-auto-repair.service` | **repointed** `ExecStart` to `core/ci/repairs/rapid_repair.py` (was the raw engine — host config `~/.config/systemd/user/ci-auto-repair.service`, not in repo) |
| notify helper | `core/notify/hale_notify.ci_auto_repair()` (no callers) | `run_capability(..., armed_tiers=policy)` — routed as defense-in-depth |

Both share ONE tier policy (`config/ci_rapid_repair_policy.json`). The old engine
file is **kept intact** — its `repair_*` bodies are imported by the warehouse
capabilities as the `repair()` apply-path. It is simply no longer the unattended
entry point.

## How rapid repair works now

For each RED CI skill, `run_capability(skill_id, apply, armed_tiers)` runs the
full closed loop:

```
explore()   READ-ONLY diagnosis        -> FailureContext  (never mutates)
assess(ctx) classify + set effective tier -> AssessResult  (no side effects)
[TIER GATE + ARMED-TIER GATE decide apply vs stage vs skip]
repair(mode, apply)  the fix; DRY-RUN unless auto-apply is authorized
verify()    independent probe re-run    -> GREEN / RED     (ground truth)
```

Cross-spawn **anti-flap** (durable state file, circuit breaker, cooldown,
per-window cap) is read at the top of every call — it holds even though each
heartbeat spawns a fresh process that resets in-memory breakers.

## Tier policy (CONSERVATIVE CUTOVER — SAFE auto only)

`config/ci_rapid_repair_policy.json` → `armed_tiers: ["SAFE"]`

| Effective tier | Behavior |
|---|---|
| **SAFE** | Auto-applied + verify-after. Escalates if verify stays RED. |
| **CAUTION** | **STAGED** — one-touch confirm required (not auto-applied under SAFE-only policy). |
| **DESTRUCTIVE** | **STAGED unconditionally** — the tier gate ignores `apply` entirely; cannot be bypassed by any caller. |

**Effective** tier = `max(declared tier, tier assess() raised it to)`. A
declared-SAFE skill whose `assess()` escalates to CAUTION/DESTRUCTIVE is gated at
the *effective* tier — the armed-tier gate closes that leak.

**Widening the policy** (arm CAUTION too) is a **Commander/Hale call after
validation**. Edit `armed_tiers` in the policy file to `["SAFE","CAUTION"]`.
No code change. `DESTRUCTIVE` can never be armed — the parser drops it and the
runner stages it regardless.

## Manual one-touch confirmed repair

To apply a single repair yourself (bypasses the SAFE-only auto policy for THIS
call — you are the confirmation):

```python
import sys; sys.path.insert(0, "/home/john/Thunderbird")
import core.ci.repairs.rapid_repair            # loads all clusters -> REGISTRY
from core.ci.repairs.schema import run_capability
r = run_capability("fare-watch-centrav", apply=True)   # armed_tiers=None => legacy: SAFE+CAUTION apply
print(r.decision.value, r.verify_after.value, r.note)
```

Note: `apply=True` with `armed_tiers=None` auto-applies SAFE **and** CAUTION.
DESTRUCTIVE still stages no matter what — to actually run a DESTRUCTIVE fix you
must confirm its staged token (below) and run its `repair_*` deliberately.

## Reviewing / confirming a STAGED token

Staged proposals live in `OpsCenter/ci_staged_repairs.jsonl`, one JSON line each,
`status: STAGED_AWAITING_CONFIRM`, token `CIRPR-XXXXXXXXXXXX`.

```bash
# list open staged tokens
python3 -c "import json;[print(e['token'],e['skill_id'],e['risk_tier'],e['mode']) \
  for e in map(json.loads, open('/home/john/Thunderbird/OpsCenter/ci_staged_repairs.jsonl')) \
  if e['status']=='STAGED_AWAITING_CONFIRM']"
```

To confirm: review the entry's `planned_actions` + `context`, decide, then run
the repair manually via `run_capability(skill_id, apply=True)` (for CAUTION) or
deliberately invoke the DESTRUCTIVE `repair_*` body after human review. Then mark
the token consumed (append a line with the same token and
`status: CONFIRMED_APPLIED` or edit the file). A staged token stops re-staging /
re-paging for that skill+mode within its anti-flap window.

## Where things are

| Thing | Path |
|---|---|
| Live dispatch | `core/ci/repairs/rapid_repair.py` (`run_all_red`, CLI) |
| Safety runner + registry | `core/ci/repairs/schema.py` (`run_capability`, `REGISTRY`) |
| Capabilities (48) | `core/ci/repairs/cluster_a..g.py` + `_worked_examples.py` |
| Armed-tier policy | `config/ci_rapid_repair_policy.json` |
| Heartbeat cutover | `core/ci/ci_auto_repair_integration.py` |
| Sweep cutover | `core/ci/ci_health.py` `_try_repair()` |
| Audit (every decision) | `OpsCenter/ci_repair_warehouse_audit.jsonl` |
| Staged proposals | `OpsCenter/ci_staged_repairs.jsonl` |
| Durable anti-flap state | `OpsCenter/.ci_repair_warehouse_state.json` |
| Dispatch log | `logs/ci_rapid_repair.log` |
| Old engine (kept, no longer unattended entry) | `core/ci/ci_auto_repair_engine.py` |

## CLI

```bash
# Full dry-run of ALL 48 (zero mutation, no RED filter) — the safety proof
python3 core/ci/repairs/rapid_repair.py --dry-run-all

# Live dispatch (what the heartbeat spawns); --no-notify to suppress Telegram
python3 core/ci/repairs/rapid_repair.py --no-notify

# Override armed tiers for one run (does NOT change the policy file)
python3 core/ci/repairs/rapid_repair.py --arm SAFE,CAUTION
```

## 48-skill index

Tier = **declared** baseline (assess() may raise the effective tier at runtime).
Under the SAFE-only policy: SAFE → auto; CAUTION/DESTRUCTIVE → staged.

| Skill | Cluster | Declared tier | Repairable | Probe |
|---|---|---|---|---|
| client-path-canary | cluster_c | SAFE | yes | ci_probe_client_path_canary.py |
| cloak-browser-regent | cluster_a | SAFE | yes | ci_probe_cloak_browser_regent.py |
| cloudflared-tunnel | cluster_f | SAFE | yes | ci_probe_cloudflared-tunnel.py |
| competitive-intel-apis | cluster_a | SAFE | yes | ci_probe_competitive_intel_apis.py |
| credential-keepalive | _worked_examples | DESTRUCTIVE | yes | ci_probe_credential_keepalive.py |
| cruise-db-site | cluster_f | CAUTION | yes | ci_probe_cruise-db-site.py |
| cruise-intelligence | cluster_a | SAFE | yes | ci_probe_cruise_intelligence.py |
| dani-identity-layer | _worked_examples | SAFE | yes | ci_probe_dani_identity.py |
| email-handling | cluster_g | SAFE | yes | ci_probe_email_handling.py |
| evernote-mx | cluster_g | CAUTION | yes | ci_probe_evernote-mx.py |
| fare-watch-amadeus | cluster_d | DESTRUCTIVE | yes | ci_probe_fare_watch_amadeus.py |
| fare-watch-centrav | cluster_d | CAUTION | yes | ci_probe_fare_watch_centrav.py |
| fare-watch-ita | cluster_d | SAFE | yes | ci_probe_fare_watch_ita.py |
| gdrive-mx | cluster_g | SAFE | yes | ci_probe_gdrive-mx.py |
| github-actions | cluster_f | DESTRUCTIVE | yes | ci_probe_github_actions.py |
| headless-dispatch | cluster_c | SAFE | yes | ci_probe_headless_dispatch.py |
| healthchecks | cluster_f | SAFE | yes | ci_probe_healthchecks.py |
| home-dir-health | cluster_f | DESTRUCTIVE | yes | home_dir_ci_probe.py |
| hotel-scan | cluster_a | DESTRUCTIVE | yes | ci_probe_hotel_scan.py |
| infisical | cluster_b | SAFE | yes | ci_probe_infisical.py |
| klaviyo-canary | cluster_g | SAFE | yes | ci_probe_klaviyo_canary.py |
| lifecycle-arc | cluster_e | SAFE | yes | ci_probe_lifecycle_arc.py |
| lifecycle-booking-surveys | cluster_e | CAUTION | yes | ci_probe_lifecycle-booking-surveys.py |
| lifecycle-dossiers | cluster_e | CAUTION | yes | ci_probe_lifecycle_dossiers.py |
| lifecycle-excursion-engine | cluster_e | CAUTION | yes | ci_probe_lifecycle-excursion-engine.py |
| lifecycle-itineraries | cluster_e | DESTRUCTIVE | yes | ci_probe_lifecycle_itineraries.py |
| lifecycle-proposal-engine | cluster_e | SAFE | yes | ci_probe_lifecycle-proposal-engine.py |
| lifecycle-tp | cluster_e | CAUTION | yes | ci_probe_lifecycle_tp.py |
| lifecycle-travel-surveys | cluster_e | CAUTION | yes | ci_probe_lifecycle-travel-surveys.py |
| lifecycle-validations | cluster_e | CAUTION | yes | ci_probe_lifecycle_validations.py |
| litellm-gateway | cluster_f | SAFE | yes | ci_probe_litellm_gateway.py |
| litellm-routing | cluster_c | SAFE | yes | ci_probe_litellm_routing.py |
| mcp-registry | cluster_c | SAFE | yes | ci_probe_mcp_registry.py |
| n8n | cluster_f | SAFE | yes | ci_probe_n8n.py |
| nominatim-geocoding | cluster_a | SAFE | yes | ci_probe_nominatim_geocoding.py |
| opencode-integration | cluster_c | SAFE | yes | ci_probe_opencode_integration.py |
| pii-governance | cluster_b | SAFE | yes | ci_probe_pii_governance.py |
| portal-access | cluster_a | CAUTION | yes | ci_probe_portal_access.py |
| qdrant | cluster_g | SAFE | yes | ci_probe_qdrant.py |
| regent-portal-live | cluster_a | CAUTION | yes | ci_probe_regent_portal_live.py |
| reverie-app | cluster_f | SAFE | yes | ci_probe_reverie-app.py |
| self-observability | cluster_f | SAFE | yes | ci_probe_self_observability.py |
| supertimer-bot-health | cluster_d | SAFE | yes | ci_probe_supertimer_health.py |
| tailscale | cluster_f | DESTRUCTIVE | yes | ci_probe_tailscale.py |
| tech-adoption | cluster_c | SAFE | yes | ci_probe_tech_harvest.py |
| transfer-scan | cluster_a | DESTRUCTIVE | yes | ci_probe_transfer_scan.py |
| ttyd | cluster_f | SAFE | yes | ci_probe_ttyd.py |
| web-fetch | cluster_a | SAFE | yes | ci_probe_web_fetch.py |

**Declared-tier count: 29 SAFE · 11 CAUTION · 8 DESTRUCTIVE.**
Note: `assess()` can raise the effective tier at runtime (e.g. klaviyo-canary,
litellm-gateway are declared SAFE but escalate to DESTRUCTIVE when an API key is
missing — correctly staged, never auto-fired).

## Known open items (flagged, not fixed here)

- **Registry schema inconsistency:** `config/ci_registry.json` has two entries
  (`home-dir-health`, `litellm-gateway`) using a `skill`/`probe_script` schema
  instead of `id`/`health_probe`. `core.ci.registry.load_registry()` **raises**
  on them today, which means `ci_health.sweep()` is currently inert. Rapid repair
  reads the registry **defensively** (raw JSON, both schemas) so it works anyway.
  **Do not "fix" the registry in isolation** — un-breaking it reactivates
  `sweep()`; that path is now safe (routes through `_try_repair` → safe runner),
  but validate the sweep end-to-end before relying on it.
- **Two capabilities have an `explore()` defect** (`lifecycle-arc`,
  `lifecycle-proposal-engine` raise `FailureContext has no attribute ...`). The
  runner contains this as a graceful `ERROR` decision — no crash, no mutation —
  but those two cannot self-diagnose until the cluster body is fixed.
