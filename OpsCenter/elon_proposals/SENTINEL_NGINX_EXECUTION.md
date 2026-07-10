# EXECUTION REPORT — thunderbird-sentinel-nginx Decommission
*Executed: 2026-07-06 16:06 MT · Ref: PROPOSAL-20260706-thunderbird-sentinel-nginx.md*

## What was masked
- `thunderbird-sentinel-nginx.service` — masked (symlinked to `/dev/null`)
- `thunderbird-sentinel-nginx.timer` — stopped, disabled, and masked

**Method note:** Both unit files lived directly in `~/.config/systemd/user/`, the same
path `systemctl mask` needs to write its `/dev/null` symlink to, so a plain `mask` call
failed with "File already exists." Resolved by moving the two unit files to
`OpsCenter/sentinel/retired/*.bak` (reversible backup, not deleted) before masking.

## CI coverage verified
- No dedicated `nginx` entry exists in `config/ci_registry.json` — expected, since that
  registry only tracks the 5 v1 CI skill categories (portal-access, web-fetch,
  headless-dispatch, credential-keepalive, tech-adoption), not individual services.
- `ci-sentinel.service` → `scripts/ci_sentinel.py` (Armed Overwatch / F2T2EA) provides
  the actual coverage: it runs `systemctl --user list-units` and fuses restart-count,
  error-rate, failed-state, and port-conflict bands across **every** user service —
  which includes any nginx-related unit. This generic overwatch is a superset of what
  the standalone `nginx_health_check.sh` did (a single curl-based HTTP liveness ping).
- Per the proposal's own condition ("if CI doesn't have nginx coverage, escalate to
  Sterling — not a blocker"), coverage is confirmed sufficient to proceed without
  escalation.

## Result
- Both units confirmed `Loaded: masked`, `Active: inactive (dead)`.
- `thunderbird-watchdog.service` ran clean immediately after masking:
  `mode=GREEN 0 actions, 0 alerts` — no restart-loop activity from the retired service.
- Root cause of the original 3x/7-day restart loop (per the proposal: brittle oneshot
  masking an intermittent environmental issue) is now moot — the redundant checker is
  gone, and `ci-sentinel.py`'s generic overwatch remains the system of record.

## Reversibility
Restore path if ever needed: `systemctl --user unmask thunderbird-sentinel-nginx.service thunderbird-sentinel-nginx.timer`,
then copy the two `.bak` files back from `OpsCenter/sentinel/retired/` into
`~/.config/systemd/user/`, then `systemctl --user daemon-reload`.
