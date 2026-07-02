#!/usr/bin/env python3
"""
CI EFFICACY PROBE — MCP Server Registry
=======================================
Checks that MCP tools are live in Thunderbird's plugin-only architecture.

Thunderbird loads MCP via enabledPlugins, NOT mcpServers in settings.json.
mcpServers is intentionally empty — this is canonical, not degraded.

Checks:
  1. enabledPlugins count >= 1 in ~/.claude/settings.json
  2. permissions.allow contains >= 1 entry matching mcp__*

Exit 0 = GREEN, 1 = RED, 2 = ERROR
"""
import json
import sys
from pathlib import Path

GLOBAL_SETTINGS = Path.home() / ".claude" / "settings.json"
ID = "mcp-registry"


def main():
    if not GLOBAL_SETTINGS.exists():
        print(f"ERROR {ID}: {GLOBAL_SETTINGS} not found")
        sys.exit(2)

    try:
        data = json.loads(GLOBAL_SETTINGS.read_text())
    except Exception as e:
        print(f"ERROR {ID}: failed to parse {GLOBAL_SETTINGS}: {e}")
        sys.exit(2)

    plugins = data.get("enabledPlugins", [])
    plugin_count = len(plugins)

    allow = data.get("permissions", {}).get("allow", [])
    mcp_perms = [p for p in allow if isinstance(p, str) and p.startswith("mcp__")]
    mcp_perm_count = len(mcp_perms)

    failures = []
    if plugin_count < 1:
        failures.append("enabledPlugins is empty — no plugins registered")
    if mcp_perm_count < 1:
        failures.append("permissions.allow has no mcp__* entries — MCP tools not permitted")

    if failures:
        for f in failures:
            print(f"RED {ID}: {f}")
        sys.exit(1)

    print(f"MCP_REGISTRY: GREEN | plugins={plugin_count}, mcp_perms={mcp_perm_count}")
    sys.exit(0)


if __name__ == "__main__":
    main()
