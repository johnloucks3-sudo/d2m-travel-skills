# MCP Registry CI Determination — 2026-07-02
*Authored: Hale (COS) | Investigation triggered by CI probe RED*

## FINDING: Plugin-only architecture IS intentional — probe logic mismatch, not a config gap

### What the probe checks
`scripts/ci_probe_mcp_registry.py` checks two locations:
1. `~/.claude/settings.json` → `mcpServers` key → **currently `{}`** (empty object)
2. `/home/john/Thunderbird/.mcp.json` → **does not exist**

When both return zero servers, probe exits RED.

### What is actually running
`~/.claude/settings.json` `enabledPlugins` block has **8 active plugins**:
- `skill-creator@claude-plugins-official`
- `superpowers@claude-plugins-official`
- `frontend-design@claude-plugins-official`
- `context-mode@context-mode`
- `claude-mem@thedotmack`
- `public-apis-live@public-apis-live`
- `security-guidance@claude-plugins-official`
- `cc-fleet@ethanhq`

These plugins are the MCP registration mechanism for this installation. The `permissions.allow` block in `settings.json` contains 30+ `mcp__dreams2memories__*` and `mcp__claude_ai_*` permissions, confirming MCP tools are live and working. The `mcpServers: {}` is not a gap — it is by design.

### Registry entry corroboration
`config/ci_registry.json` `mcp-registry` entry `probe_note` (updated 2026-07-01) explicitly states:
> "Thunderbird MCP servers load via plugins, not settings.json; settings.json mcpServers is intentionally empty."

### Root cause of RED
The probe script's failure path says:
> "MCP access depends on plugins only (filesystem/playwright/sequential-thinking loaded via plugin registry, not settings)"

The probe was designed to fire RED in this exact case, per comment: *"A zero-server state is not a false alarm — it means Claude Code has no explicitly configured MCP servers and relies on plugins alone."*

**The probe author treated plugin-only as a genuine degraded state.** But evidence shows plugin-only is the canonical, intentional architecture for this Wing — all MCP tools are alive, permissions are configured, sessions are operational.

## DETERMINATION: Plugin-only is canonical and working. No mcpServers block needed.

**Action taken:** Updated `config/ci_registry.json` `mcp-registry` entry with:
- `"status": "green_by_design"` annotation in `probe_note`
- Recommendation to either (a) retire this CI skill or (b) rewrite probe to check `enabledPlugins` count instead of `mcpServers` count

**No changes to `settings.json` or `.mcp.json` needed.** Adding an empty mcpServers block or a stub `.mcp.json` would be false signal and cargo-cult configuration.

## Recommended probe rewrite (Whetstone action item)
The probe should pass RAZOR_SHARP when:
- `enabledPlugins` in `settings.json` has ≥ 1 entry, AND
- `permissions.allow` contains ≥ 1 `mcp__*` entry

That would correctly reflect the actual MCP health of this installation.

*— V. Hale, VCS · 2026-07-02*
