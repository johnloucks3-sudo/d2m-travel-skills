Proposal written to `OpsCenter/elon_proposals/PROPOSAL-20260727-thunderbird-generic-remediate@d2m-icelandair-warm.md`.

**Root cause:** An earlier same-day ELON pass (09:55 MT) already fixed one remediation path — it added `d2m-icelandair-warm.service` to `SELF_ALERTING_UNITS` in `scripts/generic_remediate.py` (confirmed live at line 99). But this incident's event came from `source: coo_watchdog`, a second, fully independent restart loop in `OpsCenter/thunderbird_coo_watchdog.py` that has no knowledge of that exclusion list and blindly restarts any failed unit. That's why the recurrence pattern persisted despite the earlier "fix."

**Fix proposed:** extract `SELF_ALERTING_UNITS`/`LANE1_OWNED_UNITS` into a shared `core/ops/remediation_exclusions.py` module and wire `thunderbird_coo_watchdog.py`'s `attempt_recovery()` call site to respect it, so it stops logging false `auto_healed` events for a session that only a Commander manual re-login can actually fix.

**Decision:** APPLY_AUTONOMOUSLY — internal infra reliability fix, no gate applies.
