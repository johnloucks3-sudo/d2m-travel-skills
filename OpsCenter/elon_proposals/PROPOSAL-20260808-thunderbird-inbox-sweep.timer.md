**Proposal complete:** `thunderbird-inbox-sweep.timer` is failing 3x/7d because the underlying service has a persistent fault, not because the timer is misconfigured. Restart-only repair is insufficient.

**Issue:** The service is crashing on each activation, but we don't yet know why—could be a missing dependency, expired credential, code bug, or resource constraint.

**Path:** Hale runs a diagnostic suite (journal pull, dependency check, resource check), classifies the error, and either applies an autonomous fix (if clear and safe) or escalates to Commander with logs + recommendation.

Proposal saved. Ready for Commander approval to execute diagnostics, or Commander can request priority on this if inbox-sweep is mission-critical.
