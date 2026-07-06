#!/usr/bin/env python3
"""Console vs Email capability parity audit.

Quarterly check (SO: Parity Audit) that Console (Claude Code, driven by
~/.claude/mcp.json) and Email (core/email/hale_email_responder.py, which
spawns a headless agent) still point at the identical MCP config and the
same CLAUDE.md/Personas doctrine. Baseline: docs/CONSOLE_VS_EMAIL_CAPABILITY_BASELINE_20260706.md
— both are supposed to be architecturally forced onto the same config, so
this audit exists to catch DRIFT (someone editing one path without the
other), not to enumerate tools by hand each time.

Usage: python3 scripts/parity_audit.py
Writes: docs/parity_audit_results_{YYYY-MM-DD}.md
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path("/home/john/Thunderbird")
CONSOLE_MCP_CONFIG = Path.home() / ".claude" / "mcp.json"
EMAIL_RESPONDER_SRC = REPO_ROOT / "core" / "email" / "hale_email_responder.py"
CONSOLE_CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
CONSOLE_HALE_PERSONA = REPO_ROOT / "Personas" / "hale_cos.md"
OUTPUT_DIR = REPO_ROOT / "docs"


def load_console_mcp_config() -> dict:
    return json.loads(CONSOLE_MCP_CONFIG.read_text())


def load_email_mcp_config_path() -> str | None:
    """Extract the MCP config path the email responder spawns headless agents with."""
    src = EMAIL_RESPONDER_SRC.read_text()
    m = re.search(r'GLOBAL_MCP_CONFIG\s*=\s*"([^"]+)"', src)
    return m.group(1) if m else None


def console_server_names(config: dict) -> set:
    """Named MCP servers only — skip the underscore-prefixed disabled/doc entries."""
    return {
        name
        for name in config.get("mcpServers", {})
        if not name.startswith("_")
    }


def check_doctrine_inheritance() -> dict:
    """Email responder spawns claude via subprocess with inherited cwd (no --cwd
    override in thunderbird_headless_spawn.py), so it loads the same CLAUDE.md /
    Personas/hale_cos.md as Console. Verify those files exist and the spawn
    wrapper doesn't override cwd."""
    spawn_src = (REPO_ROOT / "core" / "ai_infra" / "thunderbird_headless_spawn.py").read_text()
    overrides_cwd = bool(re.search(r'cwd\s*=', spawn_src)) and "inherits cwd" not in spawn_src
    return {
        "claude_md_exists": CONSOLE_CLAUDE_MD.exists(),
        "hale_persona_exists": CONSOLE_HALE_PERSONA.exists(),
        "spawn_overrides_cwd": overrides_cwd,
    }


def run_audit() -> dict:
    console_config = load_console_mcp_config()
    console_servers = console_server_names(console_config)

    email_config_path_str = load_email_mcp_config_path()
    email_config_path = Path(email_config_path_str) if email_config_path_str else None
    email_config_resolved = (
        email_config_path.expanduser().resolve() if email_config_path else None
    )
    console_config_resolved = CONSOLE_MCP_CONFIG.resolve()

    same_file = email_config_resolved == console_config_resolved

    if same_file:
        email_servers = console_servers  # same file, same tool list by definition
        missing_in_email: set = set()
        missing_in_console: set = set()
    else:
        # Fallback: independently load and diff, in case the email path ever
        # diverges from Console's config to a separate (but intended-identical) file.
        email_config = json.loads(email_config_resolved.read_text()) if email_config_resolved and email_config_resolved.exists() else {}
        email_servers = console_server_names(email_config)
        missing_in_email = console_servers - email_servers
        missing_in_console = email_servers - console_servers

    doctrine = check_doctrine_inheritance()

    return {
        "console_mcp_config": str(CONSOLE_MCP_CONFIG),
        "email_mcp_config": email_config_path_str,
        "same_config_file": same_file,
        "console_servers": sorted(console_servers),
        "email_servers": sorted(email_servers),
        "missing_in_email": sorted(missing_in_email),
        "missing_in_console": sorted(missing_in_console),
        "parity": same_file and not missing_in_email and not missing_in_console,
        "doctrine": doctrine,
    }


def render_report(result: dict, today: str) -> str:
    parity_line = "PARITY CONFIRMED" if result["parity"] else "DIVERGENCE FOUND"
    lines = [
        f"# Console vs Email Parity Audit — {today}",
        "",
        f"**Result: {parity_line}**",
        "",
        "## Config sources",
        f"- Console MCP config: `{result['console_mcp_config']}`",
        f"- Email responder MCP config: `{result['email_mcp_config']}`",
        f"- Same file: {'yes' if result['same_config_file'] else 'NO — separate files, diffed independently'}",
        "",
        f"## Tool list ({len(result['console_servers'])} servers, Console)",
        ", ".join(result["console_servers"]) or "(none)",
        "",
    ]
    if result["missing_in_email"] or result["missing_in_console"]:
        lines += [
            "## Divergence",
            f"- In Console, missing from Email: {sorted(result['missing_in_email']) or 'none'}",
            f"- In Email, missing from Console: {sorted(result['missing_in_console']) or 'none'}",
            "",
        ]
    else:
        lines += ["## Divergence", "None. Zero tool differences.", ""]

    d = result["doctrine"]
    lines += [
        "## Doctrine inheritance",
        f"- CLAUDE.md exists: {d['claude_md_exists']}",
        f"- Personas/hale_cos.md exists: {d['hale_persona_exists']}",
        f"- Headless spawn overrides cwd (would break doctrine inheritance): {d['spawn_overrides_cwd']}",
        "",
        "---",
        "*Generated by scripts/parity_audit.py — see CLAUDE.md 'Parity Audit — Quarterly'.*",
    ]
    return "\n".join(lines) + "\n"


def main():
    today = date.today().isoformat()
    result = run_audit()
    report = render_report(result, today)

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"parity_audit_results_{today}.md"
    out_path.write_text(report)

    print(report)
    print(f"Written to {out_path}")

    if not result["parity"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
