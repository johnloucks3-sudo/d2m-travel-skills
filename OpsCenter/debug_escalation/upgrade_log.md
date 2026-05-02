# Upgrade Log: Wing Autonomy and Self-Healing

- [2026-05-01] Initiated audit for "death spiral" retry patterns.
- [2026-05-01] Created `core/self_healing.py` with `SelfHealingLoop` decorator.
- [2026-05-01] Applied `SelfHealingLoop` to `OpsCenter/nexus.py` (`dispatch_to_claude` and `dispatch_to_opencode`).
- [2026-05-01] Next: Auditing `core/mcp/travel_mcp_server.py`.
