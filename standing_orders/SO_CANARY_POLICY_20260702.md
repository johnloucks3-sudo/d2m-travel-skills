# STANDING ORDER — CANARY POLICY FOR TOOL REPLACEMENT
## Dreams2Memories Travel, LLC · Thunderbird Wing · Effective 2026-07-02
*Author: Sterling (A7). Hale co-author (gate/recommend chain). Commander directive: Chronicle Event 2026-07-02.*

---

## PURPOSE

Prevent the Wing from killing a working tool before its replacement is validated. Root cause documented in Chronicle 2026-07-02, Lesson L3: the email scanner (`thunderbird_email_intel.py`) was killed rather than replaced because there was no shadow-mode comparator. The fix (email classifier default) would have been identified in days if a canary had been running.

This SO governs the **exit side of tool transitions** — removing an incumbent. Adoption of new tools is governed separately by SO_TECH_VANGUARD_ELEVATION_20260621 and is NOT constrained by this SO (see § Reconciliation below).

Chronicle source: `docs/chronicles/chronicle_2026_0702_email_ai_loop.md` § L3

Does not supersede any prior SO. Extends: SO_TECH_VANGUARD_ELEVATION_20260621.md, SO_CI_RAZOR_SHARP_20260620.md.

---

## CORE PRINCIPLE — FAST IN, CAREFUL OUT

**Adopt at tempo. Kill with evidence.**

The Wing adopts new tools immediately per SO_TECH_VANGUARD_ELEVATION_20260621 — adoption-biased, ELON can override Sterling's gate, client-path canary waived by default (Commander directive 2026-07-01). That posture is unchanged.

This SO governs the opposite direction: **before an incumbent tool is deactivated, disabled, or uninstalled, its replacement must have accumulated ≥7 days of shadow-mode evidence.** The incumbent keeps running while the replacement proves itself. The kill decision follows evidence, not intent.

---

## PROVISION 1 — SHADOW MODE DEFINITION

**Shadow mode** means: the replacement tool processes real Wing inputs, produces outputs, and those outputs are captured and compared — but the outputs are NOT actioned by the Wing's operations.

Requirements for valid shadow mode:

| Requirement | Definition |
|-------------|------------|
| Real inputs | Same live data the incumbent processes — not synthetic test data |
| Output capture | Replacement outputs logged to a scoreboard (see Provision 3) |
| No-action constraint | Replacement outputs drive zero Wing actions during shadow period |
| Parallel operation | Incumbent continues normal operation throughout shadow period |
| Duration | ≥ 7 calendar days from first shadow run |

A replacement that only processes synthetic/test data is not in shadow mode. The 7-day clock starts when real inputs begin.

---

## PROVISION 2 — MINIMUM SHADOW PERIOD

**7 calendar days.** No tool may be killed before its replacement has logged ≥7 days of shadow-mode scoreboard data.

The 7 days are not waivable by any single staff member. Waivers require Commander decision. Sterling flags any proposed kill without 7-day shadow evidence.

**Exception — P0 Security Failure:** If an incumbent tool poses an active security exposure (credential leak, unauthorized external access, known exploit being exploited), it may be killed immediately. The replacement then enters retrospective shadow mode — it continues to log outputs for ≥7 days post-kill, and the scoreboard is used to validate the replacement before treating it as trusted production. Sterling documents the exception within 24 hours.

---

## PROVISION 3 — CANARY SCOREBOARD SCHEMA

The canonical scoreboard pattern is `OpsCenter/email_canary_scoreboard.json` established 2026-07-02. All canaries follow this schema:

```json
{
  "canary_id": "<tool-pair-YYYYMMDD>",
  "incumbent": "<incumbent_tool_name>",
  "replacement": "<replacement_tool_name>",
  "shadow_start": "<ISO-8601>",
  "shadow_end_minimum": "<ISO-8601>",
  "status": "SHADOW | DECISION_READY | INCUMBENT_KILLED | REPLACEMENT_PROMOTED",
  "metrics": {
    "<metric_name>": {
      "description": "<what this measures>",
      "threshold": "<pass/fail threshold or target>",
      "incumbent_results": [],
      "replacement_results": [],
      "winner": null
    }
  },
  "p0_exception_applied": false,
  "p0_exception_reason": null,
  "decision": {
    "sterling_review_date": null,
    "hale_recommendation": null,
    "commander_decision": null,
    "decision_date": null
  }
}
```

Scoreboard lives in `OpsCenter/` and is named `<tool-pair>_canary_scoreboard.json`. The email canary (`OpsCenter/email_canary_scoreboard.json`) is the first instance.

---

## PROVISION 4 — DECISION GATE

When the 7-day shadow period completes:

1. **Sterling** reviews the scoreboard — validates data completeness, checks whether thresholds were met, flags any anomalies. Sterling does not make the kill/keep call; Sterling certifies the evidence is sufficient to decide.

2. **Hale** reviews Sterling's findings and issues a recommendation: promote the replacement (kill the incumbent), extend the shadow period, or retain the incumbent. Hale's recommendation is explicit — not implied.

3. **Commander** decides. Sterling's review + Hale's recommendation are presented together. Commander approves the kill, extends the shadow, or keeps the incumbent.

No tool may be killed without Commander decision except under the P0 Security Failure exception (Provision 2).

---

## PROVISION 5 — RECONCILIATION WITH ADOPTION POSTURE

SO_TECH_VANGUARD_ELEVATION_20260621 (Commander directive 2026-06-21) established that Sterling's gate is adoption-biased, ELON may override Sterling on adoption, and the client-path canary is waived by default (Commander amended 2026-07-01). That doctrine governs **bringing tools in**.

This SO governs **taking tools out**.

The two SOs are complementary, not in conflict:

- **ADOPT at tempo** (SO_TECH_VANGUARD, unchanged): trial a new tool immediately, no canary required to start using it alongside the incumbent.
- **KILL with evidence** (this SO): before the incumbent is removed, the replacement must have ≥7 days shadow data. The incumbent stays alive until the decision gate passes.

ELON's override authority (SO_TECH_VANGUARD) applies to adoption decisions. Kill decisions go through the Sterling → Hale → Commander chain regardless of ELON's view on adoption.

---

## PROVISION 6 — ACTIVE CANARIES REGISTRY

Sterling maintains a live registry of active canaries in `OpsCenter/state/active_canaries.json`:

```json
{
  "active_canaries": [
    {
      "canary_id": "<id>",
      "scoreboard_path": "<path>",
      "shadow_end_minimum": "<ISO-8601>",
      "decision_due": "<ISO-8601>",
      "owner": "<Sterling|Whetstone|ELON>"
    }
  ]
}
```

Sterling surfaces active canaries in the daily brief (morning, 06:30 MT) when any canary's `decision_due` is ≤ 3 days out.

First active canary: n8n/Python vs Lindy AI. Decision due: 2026-07-09.

---

## METRICS & ENFORCEMENT

| Metric | Threshold | Cadence | Owner |
|--------|-----------|---------|-------|
| Kill decisions without completed 7-day shadow | 0 (P0 exception documented) | Per-event | Sterling (A7) |
| Canary scoreboards with all metrics populated at decision | 100% | Per canary | Sterling (A7) |
| Decision gate chain complete (Sterling+Hale+Commander) before kill | 100% | Per canary | Sterling (A7) |
| P0 exceptions documented within 24h | 100% | Per-event | Sterling (A7) |
| Active canaries surfaced in brief when ≤3 days to decision | 100% | Daily | Sterling (A7) |

`lessons_implementation_rate_pct` (tracked in `hale_state.json`) applies. This SO's provisions are permanent rules, not one-time fixes — per Compounding Rule, A7 Charter.

---

*Canonical: this SO + `OpsCenter/email_canary_scoreboard.json` (schema instance) + `OpsCenter/state/active_canaries.json` (live registry).*
*— Thomas "Gauge" Sterling, Brig Gen (Ret.), A7 · Thunderbird Wing · 2026-07-02*
