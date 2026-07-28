# ELON PROPOSAL — thunderbird-generic-remediate@thunderbird-continuity
**Event:** INC-20260715T232023Z-8b7ae3 | recurrence_pattern (4x in 7d) | 2026-07-15
**Supersedes:** prior draft filed 2026-07-15T23:26 UTC in this file (zombie-reaper theory) — corrected below after direct verification against live cgroup tree + journal. Zombies carry near-zero RSS; they cannot account for a 1G MemoryMax breach or an 8.1G swap peak. The processes actually found resident in the cgroup were fully live, running MCP subprocess trees, not zombies.

---

# ROOT CAUSE

`thunderbird-continuity.service` (continuity_executor.py) runs inside the fleet-default systemd cgroup — `MemoryMax=1073741824` (1GiB) via `~/.config/systemd/user/service.d/thunderbird-default-memory.conf`, since continuity has no dedicated override like qdrant/opencode-spsa-monitor do. Its job loop spawns headless Claude agents through the wing-mandated `spawn_headless_claude()` helper (`core/ai_infra/thunderbird_headless_spawn.py`), which detaches each spawn with `subprocess.Popen(..., start_new_session=True)`. `start_new_session=True` only calls `setsid()` — it creates a new process group/session; it does **not** move the child into a new cgroup. Under cgroups v2 (this host), a forked/exec'd child always inherits its parent's cgroup unless something explicitly re-parents it (`systemd-run --scope`, a `cgroup.procs` write, etc.).

Live verification: `systemctl --user status thunderbird-continuity.service` at the moment of today's OOM showed two spawned `claude` processes (`--model haiku`, `--model claude-haiku-4-5-20251001`) still nested directly under `thunderbird-continuity.service`'s own CGroup, each dragging its own claude-mem plugin subprocess tree (bun `worker-service.cjs`, node `mcp-server.cjs` ×2-3, `chroma-mcp` via uvx with onnxruntime) — a stack that costs 300-700MB per spawn per the live `ps` sample taken this session. None of that is a zombie; it's real resident memory for MCP servers that stay alive for the life of the spawned session. Because every headless spawn's full MCP stack piles up inside the *parent's* 1GiB ceiling instead of getting its own cgroup, and several of those helper processes are persistent (not one-shot), memory climbs monotonically across the service's uptime — `Memory: 761.7M` (`swap: 197.9M, swap peak: 8.1G`) at the moment `journalctl` recorded `Result: oom-kill` at 17:28:52 MDT today, 127 tasks in the cgroup. `generic_remediate.log` shows the identical signature recurring at 04:17, 08:36-08:58 (three in a row), 13:53, and 15:54-17:00 on 2026-07-15 alone — exactly the "4x in 7d" pattern, cadence tracking how fast continuity's spawn volume refills the ceiling, not any fixed interval.

`Restart=always` brings the unit back up clean — which is exactly why the COO watchdog reports `auto_heal_succeeded: true` — but the leak resets to zero and refills at the same rate on the next batch of spawns. **The watchdog is verifying the symptom (unit active again), not the root cause (cgroup mis-accounting of detached spawn children), which is why this keeps recurring instead of resolving.** A memory-limit bump or a zombie reaper (the prior draft's fix) would not address this: the memory is real, in live processes, correctly attributed by the kernel to the cgroup they're actually running in — the bug is that they're running in the *wrong* cgroup.

# PROPOSED FIX
`code_diff`

# IMPLEMENTATION

1. **Root-cause fix — `core/ai_infra/thunderbird_headless_spawn.py`:** replace both `subprocess.Popen([...claude...], start_new_session=True)` call sites with a `systemd-run --user --scope --unit=thunderbird-headless-<alert_id>-<ts> --slice=thunderbird-headless.slice -- <claude argv>` wrapper. This gives every headless spawn its own transient scope/cgroup with independent memory accounting, off the calling service's ledger. Keep the existing `Popen(start_new_session=True)` path as fallback if `systemd-run` is unavailable.
2. **New slice:** add `~/.config/systemd/user/thunderbird-headless.slice` (or a drop-in) with its own `MemoryMax` (e.g. 4-6GiB, matching the qdrant precedent) so runaway headless spawns are bounded independently instead of exploding unbounded against whichever service triggered them.
3. `systemctl --user daemon-reload`.
4. **Immediate stopgap** (apply now, ahead of the code fix, to stop today's flapping): add `~/.config/systemd/user/service.d/thunderbird-continuity-memory.conf` with `MemoryMax=2147483648` / `MemoryHigh=1610612736` — same pattern already used for `opencode-spsa-monitor`. This buys time; it does not fix the leak, since the cgroup will still fill, just slower.
5. Correct `docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md` and the mandatory-pattern note in `.claude/CLAUDE.md`: `start_new_session=True` detaches the process **session**, not the **cgroup**. This affects every persona/service that calls `spawn_headless_claude()` from a long-running unit, not just continuity — same failure mode is latent anywhere else a persistent systemd service spawns headless Claude.

Hale can execute all five steps autonomously — infra fix, no client-send/financial/strategic gate involved.

# VERIFICATION TEST

- Trigger 3 consecutive headless spawns from `thunderbird-continuity` (or a disposable canary unit looping `spawn_headless_claude`).
- `systemctl --user status thunderbird-continuity.service` immediately after each spawn — confirm the spawned `claude` PID and its child MCP processes do **not** appear under `thunderbird-continuity.service`'s CGroup tree; they should appear under their own `thunderbird-headless-*.scope`.
- Watch `systemctl --user show thunderbird-continuity.service -p MemoryCurrent` across the 3 spawns — memory should stay flat/proportional to `continuity_executor.py`'s own footprint, not climb by the ~300-700MB each spawned Claude+MCP stack currently costs.
- Run 24h post-fix; confirm zero `oom-kill` entries for `thunderbird-continuity` in `journalctl --user -u thunderbird-continuity.service`, versus the 2+/day baseline observed today (04:17 and 17:28 MDT on 2026-07-15 alone).

# HALE DECISION
`APPLY_AUTONOMOUSLY`

---
**Filed by:** ELON (A12 Innovation & Disruption)
**Date:** 2026-07-15T23:30 UTC
**Priority:** P1 (blocking 4x/7d failures, root cause was misdiagnosed in first pass — corrected here)
