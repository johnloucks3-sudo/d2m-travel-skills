# STANDING ORDER — INSTALLED-BUT-INACTIVE TOOL AUDIT & ACTIVATION DISCIPLINE
## Dreams2Memories Travel, LLC · Thunderbird Wing · Effective 2026-07-02
*Author: Sterling (A7). ELON (A12) activation owner. Whetstone (A14) currency owner. Commander directive: Chronicle Event 2026-07-02.*

---

## PURPOSE

Eliminate the pattern where a capable tool sits installed and unactivated while the Wing builds workarounds around it. Root cause documented in Chronicle 2026-07-02, Lesson L1: n8n was installed at `/usr/local/bin/n8n` with 17 workflows staged and never activated. The wing spent months building Python workarounds for capabilities n8n could have provided natively.

Waste is theft from the client experience. An installed but dormant tool is a process design defect.

Chronicle source: `docs/chronicles/chronicle_2026_0702_email_ai_loop.md` § L1

Does not supersede any prior SO. Extends: SO_TECH_VANGUARD_ELEVATION_20260621.md, SO_CI_RAZOR_SHARP_20260620.md.

---

## PROVISION 1 — THE ACTIVATION WINDOW RULE

Any tool that is installed on the Wing's infrastructure (binaries present, packages installed, services defined) but NOT running in an active, purposeful state MUST be resolved within **7 calendar days** of discovery.

Resolution options (exactly one must be chosen within 7 days):

| Option | Action Required |
|--------|----------------|
| ACTIVATE | Bring to running state with defined purpose. Register in `config/ci_registry.json` if CI-adjacent. Document activation in `OpsCenter/state/tool_activation_audit_YYYYMM.md`. |
| DOCUMENTED KILL | Deliberate decision that the tool is not needed. Document: reason, alternatives in use, who decided. Uninstall or disable cleanly. Verify no orphaned callers. Update registry. |

A tool in limbo — installed, not running, no decision — beyond 7 days is a policy violation. Sterling flags it. ELON activates or Whetstone kills.

---

## PROVISION 2 — DISCOVERY TRIGGER

This audit triggers when ANY of the following occur:

1. A Wing member discovers a tool "already installed" during a new capability build (the L1 trigger: discovered n8n while building the email loop).
2. A `find` / `which` / `pip list` / `npm list -g` / `systemctl list-unit-files` sweep surfaces a service or binary not in the active registry.
3. A new installation is proposed for a capability — ELON checks first whether it already exists.
4. The monthly sweep (see Provision 4) fires.

**Check-before-install rule:** Before any `apt install`, `pip install`, `npm install -g`, or equivalent, ELON fleet runs a 5-minute check: does this capability (or equivalent) already exist on the system? Document the check in the activation log.

---

## PROVISION 3 — AUDIT ARTIFACT

On each discovery event, ELON (A12) produces or updates the audit artifact:

**Path:** `OpsCenter/state/tool_activation_audit_YYYYMM.md`

**Required schema per entry:**

```markdown
## [Tool Name] — [Status: ACTIVATED | KILLED | PENDING (days remaining)]
- **Discovered:** [ISO date]
- **Discovery trigger:** [L1-type build discovery | monthly sweep | check-before-install]
- **Location:** [binary path / package name]
- **Prior state:** [installed since? workflows staged? partially configured?]
- **Capability:** [what it does]
- **Decision:** [ACTIVATE / KILL / PENDING]
- **Decision date:** [ISO date or PENDING deadline]
- **Decision owner:** [ELON / Whetstone / Hale / Commander]
- **Resolution:** [what was done — or PENDING]
- **Verification:** [how we confirmed it's running or cleanly removed]
```

---

## PROVISION 4 — MONTHLY SWEEP

**Cadence: First business day of each month.**

ELON fleet runs the following sweep against the Wing's infrastructure (yoga, 192.168.1.198):

```bash
# Services with defined units but not running
systemctl list-unit-files --state=disabled,masked,static | grep -v '@'

# Globally installed npm packages
npm list -g --depth=0 2>/dev/null

# Python packages with CLI entry points
pip list 2>/dev/null | grep -iE "(workflow|agent|bot|monitor|watch|daemon|server)"

# Binaries in known tool paths not in active use
ls /usr/local/bin/ | while read b; do systemctl is-active "$b" 2>/dev/null || true; done
```

Output → `OpsCenter/state/tool_activation_audit_YYYYMM.md`. Whetstone verifies currency (tool is still the right choice, not just running). Sterling reviews for compliance gaps. Hale receives summary in first-of-month brief.

---

## PROVISION 5 — OWNERSHIP

| Role | Responsibility |
|------|---------------|
| ELON (A12) | Runs activation audits. Nominates tools for activation. Executes the monthly sweep. Checks before installing. |
| Whetstone (A14) | Verifies currency — is the tool still the right choice? Owns clean kill (uninstall, orphan-check). |
| Sterling (A7) | Flags policy violations (>7 days unresolved). Gates activation cost/complexity. Reviews audit artifact for completeness. |
| Hale | Receives monthly summary. Escalates to Commander on strategic capability gaps or spend decisions. |
| Commander | Decides on spend commitments. Final call on KILL when there is disagreement. |

---

## METRICS & ENFORCEMENT

| Metric | Threshold | Cadence | Owner |
|--------|-----------|---------|-------|
| Tools in limbo (installed, no decision, >7 days) | 0 | Weekly, Sterling sweep | Sterling (A7) |
| Check-before-install compliance (documented check on every new install) | 100% | Per-event spot audit | ELON (A12) |
| Monthly sweep executed | ≤ 3 business days after first of month | Monthly | ELON (A12) |
| Audit artifact completeness (all required fields present) | 100% of entries | Sterling review | Sterling (A7) |

First monthly sweep due: 2026-08-03 (first business day of August). Results surface in morning brief.

---

*Canonical: this SO + `OpsCenter/state/tool_activation_audit_YYYYMM.md` + `config/ci_registry.json`.*
*— Thomas "Gauge" Sterling, Brig Gen (Ret.), A7 · Thunderbird Wing · 2026-07-02*
