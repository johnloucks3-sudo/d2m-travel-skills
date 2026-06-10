Proposal written to `OpsCenter/elon_proposals/PROPOSAL-20260610-d2m-tasking-watcher.md`.

**Bottom line:** Not a fault — a theater loop. 7 days of journalctl show every "restart" as a clean `Stopping → Stopped → Started` (no crash exits, no SIGNAL codes). Two supervisors (`inbox_checkpoint_daemon` + `thunderbird_coo_watchdog`) are stacked on top of an event-driven daemon that systemd already supervises. The duplicate's stale-heartbeat probe misfires roughly daily on a watcher whose normal state is idle. Each false heal logs as `auto_healed`/INFO, and ELON's pattern detector counts INFO toward `recurrence_pattern` — so the proposal pipeline fires on its own noise.

**Fix:** config_change, three small edits — heartbeat-file probe in coo_watchdog, retire `restart_watcher()` in inbox_checkpoint_daemon (keep telemetry), filter INFO from ELON pattern detection. Routes to Sterling per PRODUCTION-LOCK. **HALE DECISION: APPLY_AUTONOMOUSLY.**

Note: a prior ELON proposal at the same path hypothesized a Gmail-delivery crash — the journal evidence rules that out, so I superseded it with a header note explaining why.
