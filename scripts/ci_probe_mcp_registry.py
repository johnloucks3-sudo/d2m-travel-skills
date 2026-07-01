#!/usr/bin/env python3
"""
CI EFFICACY PROBE — MCP Server Registry
=======================================
MISSION-334/386: Verify MCP servers are registered and accessible to Claude Code.

MCP servers in Thunderbird are loaded via Claude Code plugins (context-mode,
claude-mem, playwright, etc.), NOT via ~/.claude/settings.json mcpServers.
The settings.json mcpServers key is intentionally empty — plugins are the
registration mechanism.

This probe checks BOTH canonical locations for MCP server config:
  1. ~/.claude/settings.json  (global settings; mcpServers key)
  2. /home/john/Thunderbird/.mcp.json  (project-level MCP config)

If neither location has any registered servers, RED is reported honestly.
A zero-server state is not a false alarm — it means Claude Code has no
explicitly configured MCP servers and relies on plugins alone.

Exit 0 = RAZOR_SHARP, 1 = degraded.
"""
import json
import sys
from pathlib import Path

GLOBAL_SETTINGS = Path.home() / ".claude" / "settings.json"
PROJECT_MCP = Path("/home/john/Thunderbird/.mcp.json")

ID = "mcp-registry"


def fail(m):
    print(f"RED {ID}: {m}")
    sys.exit(1)


def load_servers(path: Path) -> dict:
    """Load mcpServers dict from a JSON file, return {} on any error."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except Exception:
        return {}
    return data.get("mcpServers", {})


def main():
    global_servers = load_servers(GLOBAL_SETTINGS)
    project_servers = load_servers(PROJECT_MCP)

    total = len(global_servers) + len(project_servers)

    if total == 0:
        # Neither location has any registered MCP servers.
        # This is honest RED — Claude Code relies on plugins; no explicit
        # mcpServers config exists in either ~/.claude/settings.json or
        # /home/john/Thunderbird/.mcp.json.
        fail(
            "no mcpServers configured in ~/.claude/settings.json or "
            f"{PROJECT_MCP} — MCP access depends on plugins only "
            "(filesystem/playwright/sequential-thinking loaded via plugin registry, not settings)"
        )

    sources = []
    if global_servers:
        sources.append(f"{len(global_servers)} in settings.json: {list(global_servers)[:5]}")
    if project_servers:
        sources.append(f"{len(project_servers)} in .mcp.json: {list(project_servers)[:5]}")

    print(f"RAZOR_SHARP {ID}: {total} MCP server(s) registered — " + "; ".join(sources))
    sys.exit(0)


if __name__ == "__main__":
    main()
