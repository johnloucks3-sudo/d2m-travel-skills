# AG Unified Status Board Integration Plan

## Overall Progress
`[████████████████████] 100%` — Implementation Complete

## Objectives
- Integrate persona-composed chyron metrics directly into canonical `scripts/ag_token_cost_dashboard.py`.
- Wire CC section to `check_headroom("CC")` from `core.relay.engine_limits` (which queries `get_cc_capacity()`).
- Delete dead `cc_live_telemetry.json` read path.
- Add an `OPERATIONAL STATUS` section backed by 8 live/checked system sources:
  1. Failed user systemd units (`systemctl --user list-units --state=failed --no-legend`)
  2. Temporal cluster health (`temporal operator cluster health --address 127.0.0.1:7233`)
  3. Active one-shot timers (`task-*.log` mtime/status inspection)
  4. Wing relay inbox count (`core.relay.wing_relay.relay_read`)
  5. BrainBridge pending tasks count/IDs (`core/hale_bus/brain_bridge_board.json`)
  6. OpenRouter spend cap & honest untracked spend status (`core.relay.engine_limits.OPENROUTER_MONTHLY_HARD_CAP`)
  7. Operational posture & roster idle status (labeled as self-reported persona state)
  8. Executive portal health (`urllib.request.urlopen("http://localhost:9090/")`)

## Execution Checklist
- [x] Step 1: Remove `cc_live_telemetry.json` dependency and wire `check_headroom("CC")`.
- [x] Step 2: Implement systemd failed unit check.
- [x] Step 3: Implement Temporal cluster health check.
- [x] Step 4: Implement active timer detection.
- [x] Step 5: Implement Wing relay unread message count via `relay_read()`.
- [x] Step 6: Implement BrainBridge pending task count and ID listing.
- [x] Step 7: Implement OpenRouter cap reporting with honest UNTRACKED spend label.
- [x] Step 8: Wire posture & roster idle status with self-reported labels.
- [x] Step 9: Wire live HTTP status check for Executive Portal.
- [x] Step 10: Validate script output and write walkthrough deliverable.
