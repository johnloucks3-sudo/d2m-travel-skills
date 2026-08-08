BLUF: Commander forwarded a real alert — 3 "FAILED" services (thunderbird-mcp, thunderbird-tunnel, thunderbird-scheduler), 11:10 AM. Two threads, genuinely different: (1) thunderbird-mcp.service had a real crash-and-hang around 11:08-11:11, self-healed, now running fine — needs root cause. (2) tunnel/scheduler are FALSE POSITIVES from a stale health checker that's been watching the wrong canonical unit name — confirmed via the checker's own code comments, which show this exact confusion has flip-flopped before. Commander wants this run as a proper War Room this time (OC + AG), not solo CC.

## Thread 1 — thunderbird-mcp.service, real crash, needs root cause
Journal excerpt (already pulled, don't re-derive):
```
11:08:16-21  5 rapid restart cycles in 5 seconds (Stopping/Stopped/Starting/Started x5)
11:09:49     Stopping...
11:11:19     State 'stop-sigterm' timed out. Killing. SIGKILL. Failed with result 'timeout'.
             Triggering OnFailure= dependencies.
11:11:19-20  Restarted cleanly, has run fine since (currently 48+ min uptime, no further issues)
```
Memory config: `service.d/thunderbird-mcp-memory-override.conf` sets `MemoryMax=1073741824` (1GB), `MemoryHigh=536870912` (512MB). Recorded peak at the 11:08 crash was 253.9M — under both limits, so this does NOT look like a straightforward OOM-kill. Something else caused the rapid restart cycle and the later stop-timeout/hang.

**Question for the room:** what caused (a) 5 restarts in 5 seconds at 11:08, and (b) a stop that hung 90s and needed SIGKILL at 11:09-11:11? Investigate: was anything else touching port 8765 or this unit around that time (another process, a competing daemon-reload, a client connection storm)? Check `logs/mcp_stdout.log` / `logs/mcp_stderr.log` for the same window.

## Thread 2 — tunnel/scheduler, false positives, checker watching the wrong unit
`deploy/health_check.py`'s own code comments (read directly, not inferred) show this EXACT confusion has flip-flopped before:
- A 2026-07-30 note claimed `d2m-scheduler.service` was "a dead duplicate" and `thunderbird-scheduler.service` was "the live unit."
- **Tonight (2026-08-08), CC found and fixed the OPPOSITE, verified with live evidence** (journal showing `thunderbird-scheduler.service` losing a lock race to `d2m-scheduler.service` on every single boot, wasting ~7s CPU/118MB memory for nothing) — `d2m-scheduler.service` is the real, hardened, currently-active one; `thunderbird-scheduler.service` was correctly disabled.
- Same pattern for tunnel: `cloudflared.service` (full multi-hostname ingress config) is real; `thunderbird-tunnel.service`/`d2m-tunnel.service` were a bare duplicate running the SAME tunnel ID simultaneously — confirmed via `ps` + `cloudflared tunnel list` cross-reference, also fixed tonight.
- `deploy/health_check.py`'s `SERVICES` list (line 26-31) still watches the OLD names (`thunderbird-tunnel.service`, `thunderbird-scheduler.service`), and `check_service()` (line 62) ONLY checks `systemctl is-active` — never `is-enabled` — so ANY intentionally-disabled unit alerts as "FAILED" forever, with no way to distinguish "should be running but isn't" from "correctly turned off."

**Question for the room:** (1) confirm CC's read is right — don't just trust it, check `systemctl --user is-enabled` + `is-active` on all 4 units (thunderbird-tunnel/scheduler, d2m-tunnel/scheduler-if-it-still-exists, cloudflared) yourselves. (2) Propose the fix: update `SERVICES` list to the TRUE canonical names, AND/OR add an is-enabled check so an intentionally-disabled unit never alerts as failed again — this exact confusion has now happened at least twice, needs to stop recurring.

## What NOT to do
- Do not re-enable thunderbird-tunnel.service or thunderbird-scheduler.service — that would recreate the duplicate-process conflict CC fixed and verified tonight (git commits from earlier this session document the live-process evidence).
- Do not guess at the MCP crash cause without checking the actual logs named above.

## Format
Point paper, BLUF first, ≤300 words each. Write to this session's own `{oc,ag}_hale_input.md`.
