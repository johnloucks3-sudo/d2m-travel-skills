# systemd --user memory drop-ins (A7 Sterling, 2026-07-16)

Durable copy of the per-service memory limits. Mirrors the live layout under
`~/.config/systemd/user/`. Re-apply after a reinstall / config wipe:

```bash
cp -r config/staged/systemd_memory_dropins/* ~/.config/systemd/user/
systemctl --user daemon-reload
```

## Root cause this fixes (fleet-wide OOM, 2026-07-16)

The per-service memory `*.conf` files previously all lived in the SHARED top-level
`~/.config/systemd/user/service.d/` directory. A bare `service.d/` (not
`<unit>.service.d/`) is systemd's "drop-in for a unit TYPE" — it applies to EVERY
`.service` unit. systemd on this host merges all drop-ins (top-level AND per-unit)
sorted by **basename across directories**, and for single-value keys like
`MemoryMax` the lexically-last basename wins. Per-unit directories do NOT get
directory precedence (verified empirically 2026-07-16).

`thunderbird-default-memory.conf` sorted LAST, so its `MemoryMax=1G` silently
clobbered every intended per-service limit — qdrant (4G), opencode-spsa (2G),
gmail-bridge (1.5G) were all actually capped at 1G. That was the fleet-wide OOM
root cause. `systemctl --user show qdrant.service -p MemoryMax` proved it: conf
claimed 4G, kernel enforced 1G.

## The fix

- `service.d/00-thunderbird-default-memory.conf` — the fleet default (1G), renamed
  with a `00-` prefix so it sorts FIRST and is the base layer every per-unit
  override beats. **Do not add other `MemoryMax` confs to `service.d/`.**
- `<unit>.service.d/override.conf` — one per service that needs a distinct limit.
  `override.conf` sorts after `00-*` so it wins for that unit only.

## Verify after install

```bash
systemctl --user show qdrant.service -p MemoryMax          # 4294967296 (4G)
systemctl --user show thunderbird-continuity.service -p MemoryMax   # 1610612736 (1.5G)
systemctl --user show ci-sentinel.service -p MemoryMax     # 1073741824 (1G fallback)
```
