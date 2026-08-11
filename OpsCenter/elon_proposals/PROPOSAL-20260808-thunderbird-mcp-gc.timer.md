# PROPOSAL-20260808-thunderbird-mcp-gc.timer
**Event:** INC-20260808T170824Z-ca8cd3 | **Pattern:** recurrence_pattern (3x in 7d) | **Filed by:** ELON (A12)

---

# ROOT CAUSE

Two independent, uncoordinated self-healing systems both react to `thunderbird-mcp-gc.service` and collide. `scripts/generic_remediate.py` (Lane 2, event-driven via the fleet-wide `OnFailure=thunderbird-generic-remediate@%N.service` drop-in) has an explicit cooldown gate (`_cooldown_blocking()`, 3600s) and correctly declined to act throughout the incident window — logs confirm "cooldown active — not re-attempting" at every trigger. `scripts/timer_self_repair.py` (added 2026-08-07, WAR ROOM idea #16, its own `thunderbird-timer-self-repair.timer`) has **no cooldown, no shared state, and no mutex** — its `_repair()` calls `_restart(unit)` (line 141/149: unconditional `systemctl --user restart <unit>`) every time it scans and finds the unit's activated service failed. `thunderbird-mcp-gc.service` is a `Type=oneshot` that completes in ~1s (`ExecStart` backgrounds the real work and sleeps 1s, `TimeoutStartSec=10s`). When `timer_self_repair.py` issues a fresh `restart` while a prior invocation (or `generic_remediate.py`'s own start) is still inside that ~1-10s window, systemd's restart job preempts the running instance with SIGTERM before it finishes — `journalctl` confirms repeated "Main process exited, code=killed, status=15/TERM" in tight 1-2s bursts (11:11:20/22/23/24/26, 11:12:51-56, 11:13:19-41). Each SIGTERM-kill re-fires `OnFailure=` (Lane 2, correctly no-ops on cooldown) but does nothing to stop Lane 1's next cooldown-less retry seconds later — a self-cannibalizing restart storm, not a real fault in the underlying MCP daemon (`thunderbird-mcp.service` itself recovered cleanly and independently at 11:11:25: "recovered — verified active"). The storm burns through `StartLimitBurst=10`/`StartLimitIntervalSec=120s`, systemd marks the unit `start-limit-hit`/`dependency failed`, and `timer_self_repair.py` reports this to the auto-heal pipeline as "repair attempted but FAILED" — which is the page that fired this proposal. The GC unit's actual job (restarting `thunderbird-mcp.service` for memory hygiene) was never the problem; the wrapper restarting itself against its own in-flight restart is.

# PROPOSED FIX
**config_change**

Add a shared cooldown/mutex check to `timer_self_repair.py._repair()` so it never issues a `restart`/`start` on a unit that was already attempted (by itself or by `generic_remediate.py`) within a short window — purely additive, does not touch the async-restart or fleet-wide OnFailure mechanics.

# IMPLEMENTATION
Hale can execute autonomously (infra fix, no client/financial/strategic gate):

1. In `scripts/timer_self_repair.py`, before `_repair()` calls `_restart()`/`_start()` (lines ~141, 149), add a short-window guard (60-90s is enough — the actual restart takes ~1s):
   - Read `logs/timer_self_repair_state.json`'s per-unit `last_attempt` timestamp (state file already exists, just isn't consulted for gating today — only for post-hoc recording).
   - If `now - last_attempt < REPAIR_COOLDOWN_SECONDS`, skip the restart, log "cooldown — not re-attempting" (mirror `generic_remediate.py`'s existing pattern), and let the *next* scheduled scan re-evaluate.
2. Set `REPAIR_COOLDOWN_SECONDS = 60` — long enough to let one restart cycle (~1-10s) fully finish and be reverified before a second attempt, short enough not to blunt the "restart-and-reverify before paging" mission.
3. `systemctl --user daemon-reload` not required (Python-only change); no unit file edits.
4. No change to `generic_remediate.py`, `async-restart.conf`, or `StartLimitBurst` — those are working as designed.

# VERIFICATION TEST
End-to-end, not just `systemctl is-active`:
1. Force-fail the unit: `systemctl --user stop thunderbird-mcp-gc.service` isn't sufficient (oneshot exits clean) — instead run `scripts/timer_self_repair.py` twice back-to-back manually (`python3 scripts/timer_self_repair.py`, then immediately again) against a unit in a genuinely failed state.
2. Confirm the second invocation logs "cooldown — not re-attempting" and does **not** call `systemctl --user restart`.
3. `journalctl --user -u thunderbird-mcp-gc.service --since "-2min"` — confirm no `killed/signal(15)` entries during the double-invocation test.
4. Let the next real `thunderbird-timer-self-repair.timer` cycle run unmodified in production; confirm `logs/timer_self_repair.log` shows at most one restart attempt per unit per cooldown window over the following 24h (grep for repeated "REPAIR ATTEMPTED" on the same unit within 60s).
5. Confirm `thunderbird-mcp-gc.timer`/`.service` show zero new `start-limit-hit` events over the next 7d (`journalctl --user -u thunderbird-mcp-gc.service --since -7d | grep start-limit-hit`).

# HALE DECISION
**APPLY_AUTONOMOUSLY** — infra self-heal bug, no client/financial/strategic gate implicated, fix is additive-only (a missing cooldown check, same pattern already proven in `generic_remediate.py`), and low blast radius (one function in one script). Queuing this for the Commander would just be another instance of asking him to approve routine infra hygiene per standing "fix don't ask infra" doctrine.
