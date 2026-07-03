# CI Rapid-Repair Warehouse — Schema & Authoring Guide
## Dreams2Memories Travel, LLC · Thunderbird Wing
**Author:** Brig Gen (Ret.) Thomas "Gauge" Sterling (A7) · **Date:** 2026-07-02
**Status:** Framework built ALONGSIDE the live engine. NON-BREAKING. Integrate phase does the cutover.

---

## 1. What this is (and what it is not)

The **CI Rapid-Repair Warehouse** is a typed, safety-gated framework for auto-repair.
It replaces the hazardous behavior of the live engine — which auto-fires all 45 repairs,
unattended, on any RED probe, with **no circuit breaker, no risk gate, no diagnose phase** —
with a contract that makes every repair prove it is safe before it mutates anything.

- **Files:**
  - `core/ci/repairs/schema.py` — the `RepairSpec`, `RiskTier`, `FailureContext`, the
    `@repair_capability(...)` self-registering decorator, the `REGISTRY`, and the
    `run_capability(skill_id, apply=False)` RUNNER.
  - `core/ci/repairs/_worked_examples.py` — TWO reference templates (one SAFE, one DESTRUCTIVE)
    that build agents copy.
  - `core/ci/repairs/__init__.py` — package marker.

- **It does NOT touch the live engine.** `core/ci/ci_auto_repair_engine.py` and
  `core/ci/ci_auto_repair_integration.py` are unchanged. The warehouse uses its OWN durable
  state files. The live engine keeps working exactly as before until the integrate phase.

- **Warehouse-private state (never the live engine's `.ci_repair_state.json`):**
  - `OpsCenter/.ci_repair_warehouse_state.json` — durable breaker/cooldown/window state.
  - `OpsCenter/ci_staged_repairs.jsonl` — DESTRUCTIVE proposals + one-touch confirm tokens.
  - `OpsCenter/ci_repair_warehouse_audit.jsonl` — append-only audit of every decision.

---

## 2. The mandatory safety contract (baked into `RepairSpec`)

Every repair capability is a typed `RepairSpec` with four callables and a safety envelope.

| Field | Contract |
|---|---|
| `explore()` | **READ-ONLY** diagnosis. `systemctl is-active`, file exists, token expiry, probe stderr, log tail. **NEVER mutates.** Returns a `FailureContext`. |
| `assess(context)` | Classify the failure **MODE**. **No side effects.** Returns `AssessResult(mode, repairable, effective_tier, reason)`. |
| `repair(mode, apply=False)` | The fix. **DRY-RUN BY DEFAULT** — `apply=False` returns the planned actions and does nothing. Only mutates when `apply=True`. |
| `verify()` | Re-run the skill's probe **independently**. Returns `GREEN`/`RED` — ground truth, not the repair's self-report. |
| `risk_tier` | `SAFE` (idempotent → auto-apply OK) / `CAUTION` (auto-apply + notify) / `DESTRUCTIVE` (**NEVER** auto-apply → stage for one-touch confirm). |
| bounded | `timeout_seconds`, `max_attempts` (tenacity in-cycle), backoff, `circuit_fail_max` + `circuit_reset_seconds` (pybreaker semantics, **durably persisted**), `cooldown_seconds`, `max_repairs_per_window` / `window_seconds` (anti-flap). |
| `sources[]` | Provenance from ELON's `research_world_patterns.md` / Dembe's `research_domain_recipes.md`. |

### The three invariants that make it safe

1. **KEYSTONE — the anti-flap gate is DURABLE, not in-memory.**
   The live engine is spawned *fresh per heartbeat* (`integration.py` → `subprocess.Popen`
   on RED). An in-memory `pybreaker` breaker resets to zero every spawn, so `fail_max`
   never accumulates — the guardrail would be **theater**. The runner therefore persists
   consecutive-fail count, last-attempt timestamp, open-until timestamp, and rolling-window
   count to `OpsCenter/.ci_repair_warehouse_state.json`, and reads that file at the TOP of
   `run_capability`. This is the gate that actually holds across spawns. `pybreaker`/`tenacity`
   handle the *in-cycle* retry; the JSON file is the *cross-spawn* truth.

2. **The tier gate lives in the RUNNER, not the spec.**
   For `DESTRUCTIVE`, `run_capability` calls `repair(mode, apply=False)` ONLY, captures the
   plan, writes plan + a `CIRPR-…` token to `OpsCenter/ci_staged_repairs.jsonl`, and **never
   calls `apply=True`** — even when the caller passed `apply=True`. No `RepairSpec` and no
   caller can bypass this. That is the "cannot be overridden by code" invariant.

3. **Fail-safe default tier = DESTRUCTIVE.**
   `@repair_capability(...)` defaults `risk_tier=DESTRUCTIVE`. Anything an author is unsure
   about stages rather than auto-fires. `assess()` may only *raise* the effective tier
   (`_max_tier`), never lower it below the declared baseline.

### `NOT_REPAIRABLE` vs `STAGED` — the distinction authors must get right
- `assess()` returns **`repairable=False`** when *no wing action exists* (creds file gone,
  DORMANT, needs Commander/@BotFather/sudo). The runner returns `NOT_REPAIRABLE` and escalates.
  Nothing is staged — there is nothing to run.
- `assess()` returns **`repairable=True` + `DESTRUCTIVE`** when *a real action exists but is
  too dangerous to auto-fire*. The runner **STAGES** it with a one-touch token. This is the
  branch that produces a staged repair.

### Runner decision states (`Decision`)
`AUTO_APPLIED` · `STAGED` · `DRY_RUN` · `SKIPPED_HEALTHY` · `BLOCKED_CIRCUIT` ·
`BLOCKED_COOLDOWN` · `NOT_REPAIRABLE` · `NO_CAPABILITY` · `ERROR`

### The closed loop (`run_capability`)
```
read durable state → circuit/cooldown/window gates (cross-spawn)
  → explore()  (read-only; if probe GREEN → SKIPPED_HEALTHY, don't repair what isn't broken)
  → assess()   (classify mode; not repairable → NOT_REPAIRABLE + escalate)
  → decide by effective tier:
       DESTRUCTIVE → repair(apply=False) → STAGE plan+token (apply ignored)   [STAGED]
       apply=False → repair(apply=False) → return plan                        [DRY_RUN]
       SAFE/CAUTION + apply=True → (CAUTION notifies) → repair(apply=True)
                                    via tenacity retry → verify()             [AUTO_APPLIED]
  → record attempt to durable state → append audit
```

### Verification of the keystone (run, don't trust)
`_worked_examples.py` + the runner were proven with:
- `run_capability("dani-identity-layer", apply=False)` → `DRY_RUN`, **zero mutation** (sentinel never flips).
- `run_capability("credential-keepalive", apply=True)` (repairable DESTRUCTIVE) → `STAGED` with a
  `CIRPR-…` token, apply-body **never called**, staging file `STAGED_AWAITING_CONFIRM`.
- creds-missing DESTRUCTIVE → `NOT_REPAIRABLE`, no token, nothing staged.
- two back-to-back applies → attempt #2 `BLOCKED_COOLDOWN`; after `circuit_fail_max` fails →
  `BLOCKED_CIRCUIT`; state persisted to file (proves the gate survives a simulated respawn).

---

## 3. How to write a `RepairSpec` for a skill

Build agents each take one cluster (Section 4) and author one capability per skill.
**Copy a worked example from `core/ci/repairs/_worked_examples.py`** and follow this recipe.

1. **Pick your template:**
   - Skill has an existing `repair_<skill>` in `ci_auto_repair_engine.py` and its fix is an
     idempotent restart/reinstall/cache-recreate → copy the **SAFE** template
     (`_dani_identity_layer`).
   - Skill's fix writes/deletes/rotates creds/recreates a registry, or you are unsure →
     copy the **DESTRUCTIVE** template (`_credential_keepalive`). Default to DESTRUCTIVE.

2. **Wrap the existing body BY IMPORT — do not copy the body.**
   ```python
   from core.ci.ci_auto_repair_engine import repair_<skill>
   ```
   In `repair(mode, apply=False)`, the `apply=True` path calls `repair_<skill>()`. This
   preserves every tested internal (single source of truth, no drift). The 45 existing
   functions are the reference — wrap, never rewrite.
   For the 3 skills with **no coded repair** (`cloak-browser-regent`, `litellm-gateway`,
   `home-dir-health`), author the apply-path from Dembe's recipe (`research_domain_recipes.md`).
   `home-dir-health` is intentionally **diagnostic-only** — its capability should be
   `repairable=False` (escalate, never auto-mutate).

3. **Write a real `explore()` (NEW code — this is the point).**
   Use the helpers in `schema.py`: `probe_context(skill_id, probe_file, extra_signals=...)`,
   `systemctl_is_active(unit)`, `run_probe(probe_file)`. **Read only.** Put every
   distinguishing signal you need for `assess()` into `FailureContext.signals`
   (unit active? token expiry? file present? stderr contains 401?).

4. **Write a side-effect-free `assess()`.**
   Map the `FailureContext` to a named **mode** from Dembe's failure-mode column for that
   skill. Set `repairable` and `effective_tier` per the recipe's risk class. **A single skill
   spans tiers** (dani: restart = SAFE, token-revoked = DESTRUCTIVE/MANUAL) — branch on the
   signals and raise the tier accordingly. **Default any unrecognized mode to DESTRUCTIVE.**

5. **Make `repair(mode, apply=False)` branch on mode and honor dry-run.**
   Always build the `RepairPlan.actions` list (human-readable steps). Return it unchanged when
   `apply=False`. Only on `apply=True` call the wrapped body and set `plan.apply_ok`.

6. **`verify()` = `run_probe("ci_probe_<skill>.py")`.** Independent ground truth.

7. **Register with the decorator, cite sources, set the envelope.**
   ```python
   @repair_capability("skill-id", risk_tier=RiskTier.SAFE,
                      sources=["research_domain_recipes.md §X.Y", "ci_auto_repair_engine.py::repair_x"],
                      cooldown_seconds=300, verify_settle_seconds=5)
   def _skill_id():
       def explore(): ...
       def assess(ctx): ...
       def repair(mode, apply=False): ...
       def verify(): ...
       return explore, assess, repair, verify
   ```

8. **Prove it.** `py_compile` is not enough (it won't catch import errors). Import your module
   and run `run_capability("skill-id", apply=False)` — confirm it returns a plan and mutates
   nothing. Then confirm the tier routes correctly (SAFE auto-applies in a safe sandbox;
   DESTRUCTIVE stages). **Also run the same RED skill twice** and confirm the second call is
   `BLOCKED_COOLDOWN`/dedup — the anti-flap budget must be consumed on the STAGED and
   NOT_REPAIRABLE lanes too, not just the apply lane (see §2 keystone).

### ⚠️ Two authoring cautions (learned from the worked examples)
- **Replace, do not co-register, a worked-example skill.** `_worked_examples.py` permanently
  registers the real ids `dani-identity-layer` (cluster C) and `credential-keepalive`
  (cluster B) with *template-grade* specs. When those clusters' agents author the production
  capabilities, they must ensure the real module is the one imported (last import wins,
  silently). Either remove the worked-example registration for that skill or guarantee the
  production module loads after it. Do not leave two live registrations for the same id.
- **`credential_rotation` mode in the DESTRUCTIVE template is illustrative.** Its wrapped
  apply-body (`repair_credential_keepalive`) only kicks timers (a SAFE action). It is pinned
  DESTRUCTIVE purely to demonstrate the staging mechanism. A real capability must match the
  apply-body's actual blast radius to the tier — do not inherit this mismatch.

---

## 4. Seven-cluster assignment table — ALL 48 skills

Each build agent takes ONE cluster. Assignment is **complete and disjoint**: verified
programmatically against `config/ci_registry.json` — union = 48, no duplicates, no gaps,
exact id-string match (9 + 3 + 7 + 4 + 9 + 11 + 5 = 48). `litellm-gateway` uses the registry
key `skill` (not `id`) — authors must use the exact string `litellm-gateway`.

Risk hints below are the *declared baseline*; `assess()` may raise the effective tier per mode.

### Cluster A — Web / portal / scrape (9)
| Skill | Existing `repair_`? | Baseline tier hint |
|---|---|---|
| portal-access | yes | CAUTION (session warm) / DESTRUCTIVE (reCAPTCHA MANUAL) |
| web-fetch | yes | SAFE (pip reinstall) |
| regent-portal-live | yes | CAUTION (keepalive) / DESTRUCTIVE (Akamai MANUAL) |
| competitive-intel-apis | yes | SAFE / DESTRUCTIVE (API key) |
| cruise-intelligence | yes | SAFE (cache recreate) |
| nominatim-geocoding | yes | SAFE |
| hotel-scan | yes (DORMANT) | DESTRUCTIVE (no data source) |
| transfer-scan | yes (DORMANT) | DESTRUCTIVE (no data source) |
| cloak-browser-regent | **NO** — author from recipe | SAFE (npm reinstall) / DESTRUCTIVE (Akamai change) |

### Cluster B — Credentials / secrets / PII (3)
| Skill | Existing `repair_`? | Baseline tier hint |
|---|---|---|
| credential-keepalive | yes | SAFE (timer restart) / DESTRUCTIVE (creds file) — **worked example** |
| pii-governance | yes | SAFE (deps) / DESTRUCTIVE (breach) |
| infisical | yes | SAFE (docker restart) / DESTRUCTIVE (token/sudo) |

### Cluster C — AI-dispatch / routing / MCP (7)
| Skill | Existing `repair_`? | Baseline tier hint |
|---|---|---|
| headless-dispatch | yes | SAFE (timer/binary) / DESTRUCTIVE (creds) |
| litellm-routing | yes | SAFE (pip) / DESTRUCTIVE (API key) |
| mcp-registry | yes | SAFE (idempotent key add) |
| opencode-integration | yes | SAFE (service restart) |
| tech-adoption | yes | SAFE (cache recreate) |
| client-path-canary | yes | SAFE (registry recreate) |
| dani-identity-layer | yes | SAFE (restart) / DESTRUCTIVE (bot token) — **worked example** |

### Cluster D — Fare / travel-data (4)
| Skill | Existing `repair_`? | Baseline tier hint |
|---|---|---|
| fare-watch-centrav | yes | CAUTION (relogin) / DESTRUCTIVE (reCAPTCHA) |
| fare-watch-ita | yes | SAFE (playwright install) |
| fare-watch-amadeus | yes | DESTRUCTIVE (API keys DORMANT) |
| supertimer-bot-health | yes | SAFE (service restart) |

### Cluster E — Lifecycle (9)
| Skill | Existing `repair_`? | Baseline tier hint |
|---|---|---|
| lifecycle-dossiers | yes | CAUTION (TESS sync writes state) |
| lifecycle-tp | yes | CAUTION (writes schedule json) |
| lifecycle-arc | yes | SAFE (validate) |
| lifecycle-validations | yes | CAUTION (renders drafts) |
| lifecycle-itineraries | yes | DESTRUCTIVE (in-place source patch) |
| lifecycle-travel-surveys | yes | CAUTION (generates) |
| lifecycle-booking-surveys | yes | CAUTION (generates) |
| lifecycle-proposal-engine | yes | SAFE (self-test) |
| lifecycle-excursion-engine | yes | CAUTION (re-scrapes/writes) |

### Cluster F — Infra / services / tunnel (11)
| Skill | Existing `repair_`? | Baseline tier hint |
|---|---|---|
| self-observability | yes | SAFE (timer/service restart) |
| n8n | yes | SAFE (service restart) |
| cloudflared-tunnel | yes | SAFE (restart) / DESTRUCTIVE (token/DNS MANUAL) |
| ttyd | yes | SAFE (restart) |
| tailscale | yes | DESTRUCTIVE (system unit, needs sudo) |
| cruise-db-site | yes | CAUTION (DB rebuild, ~300s) |
| reverie-app | yes | SAFE (service restart) |
| github-actions | yes | DESTRUCTIVE (PAT / branch protection) |
| healthchecks | yes | SAFE (docker restart) |
| litellm-gateway | **NO** — author from recipe (`skill` key) | SAFE (`systemctl --user restart d2m-litellm-gateway.service`) |
| home-dir-health | **NO** — diagnostic-only | DESTRUCTIVE / `repairable=False` (never auto-mutate) |

### Cluster G — Data-stores / comms / identity (5)
| Skill | Existing `repair_`? | Baseline tier hint |
|---|---|---|
| qdrant | yes | SAFE (docker start) / DESTRUCTIVE (volume/dim) |
| email-handling | yes | SAFE (timer restart) / DESTRUCTIVE (creds file) |
| gdrive-mx | yes | SAFE (probe = token refresh) / DESTRUCTIVE (creds) |
| evernote-mx | yes | CAUTION (backup script) / DESTRUCTIVE (SDK EOL) |
| klaviyo-canary | yes | SAFE (deps) / DESTRUCTIVE (API key) |

**Coverage:** A(9) + B(3) + C(7) + D(4) + E(9) + F(11) + G(5) = **48**. Verified disjoint and
complete against the registry.

---

## 5. Integrate phase (later — NOT part of this build)
- Wire `run_capability` into `ci_auto_repair_integration.py` in place of the run-all engine.
- Build the confirm-consumer that reads `ci_staged_repairs.jsonl`, matches a `CIRPR-…` token
  on Commander one-touch approval, and calls `repair(mode, apply=True)` for the staged action.
- Wire `_notify()` to the Telegram gateway for CAUTION-tier pre-execution notification.
- Retire the live engine's blind run-all path once all 48 capabilities are authored + proven.

*Sterling (A7) · Process / Metrics / Code & Schematic Oversight · Dreams2Memories Travel, LLC · 2026-07-02*
