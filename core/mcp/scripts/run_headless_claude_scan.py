#!/usr/bin/env python3
"""
OpenCode Headless Claude Technical Scan
Runs the audit and outputs a full report to stdout + file.
"""

import subprocess, os, datetime, sys
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
out_path = OUTPUT_DIR / f"opencode_headless_scan_{timestamp}.txt"

dirs = ["OpsCenter", "agents", "core/ai_infra", "core/mcp"]

patterns = {
    "subprocess.Popen": r"subprocess\.Popen",
    "spawn_headless_claude": r"spawn_headless_claude",
    "dispatch_to_headless_claude": r"dispatch_to_headless_claude",
    "dispatch_with_fallback": r"dispatch_with_fallback",
    "claude_binary_spawn": r"(/usr/bin/env claude|claude |/home/john/.local/bin/claude|/bin/claude)",
    "start_new_session": r"start_new_session\s*=\s*True",
    "write_path_in_prompt": r"WRITE\s*\[.*\]",
    "legacy_print_flag": r"-p\s+|--print\s+",
}

results = {k: [] for k in patterns}
all_py = []

for d in dirs:
    base = ROOT / d
    for root, _, files in os.walk(base):
        for f in files:
            if f.endswith(".py"):
                fp = Path(root) / f
                all_py.append(str(fp))
                for tag, pat in patterns.items():
                    out = subprocess.run(
                        ["grep", "-n", "-I", pat, str(fp)],
                        capture_output=True, text=True
                    )
                    if out.stdout.strip():
                        for line in out.stdout.strip().split("\n"):
                            results[tag].append((str(fp), line))

total_files = len(all_py)

compliant_tools = []
warnings = []
violations = []
critical = []

def rel(p):
    return os.path.relpath(p, str(ROOT))

for tag, hits in results.items():
    for fp, line in hits:
        rfp = rel(fp)
        if tag == "subprocess.Popen":
            if "thunderbird_headless_spawn.py" in fp or "opencode_headless_claude_dispatch.py" in fp:
                compliant_tools.append((rfp, line))
            else:
                violations.append(("VIOLATION", "RED", rfp, tag, line,
                    "Direct subprocess.Popen — may bypass OAuth/daemon checks.",
                    "Use spawn_headless_claude() or dispatch_to_headless_claude()."))
                critical.append(rfp)

        elif tag == "spawn_headless_claude":
            compliant_tools.append((rfp, line))

        elif tag == "dispatch_to_headless_claude":
            compliant_tools.append((rfp, line))

        elif tag == "start_new_session":
            compliant_tools.append((rfp, line))

        elif tag == "write_path_in_prompt":
            compliant_tools.append((rfp, line))

        elif tag == "legacy_print_flag":
            warnings.append(("WARNING", "YELLOW", rfp, tag, line,
                "Legacy -p/--print may disable OAuth.",
                "Remove -p/--print; use WRITE [PATH] or wrapper redirection."))

        elif tag == "claude_binary_spawn":
            if "opencode_headless_claude_dispatch.py" in fp or "thunderbird_headless_spawn.py" in fp:
                compliant_tools.append((rfp, line))
            else:
                violations.append(("VIOLATION", "RED", rfp, tag, line,
                    "Ad-hoc Claude binary invocation bypassing wrappers.",
                    "Use dispatch_to_headless_claude() for OpenCode tasks."))
                critical.append(rfp)

compliant_count = len(set(c[0] for c in compliant_tools))
warning_count = len(warnings)
violation_count = len(violations)
critical_count = len(set(critical))

lines = []
lines.append("=== OPENCODE HEADLESS CLAUDE TECHNICAL SCAN ===")
lines.append(f"Scan Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
lines.append("Scope: OpenCode modules + core AI infrastructure")
lines.append("Auditor: Sonnet (DeepSeek V3.1)")
lines.append("")
lines.append("EXECUTIVE SUMMARY:")
lines.append(f"  - Total files scanned: {total_files}")
lines.append(f"  - Compliant patterns found: {compliant_count}")
lines.append(f"  - Warnings: {warning_count}")
lines.append(f"  - Violations: {violation_count}")
lines.append(f"  - Critical violations: {critical_count}")
lines.append("")
lines.append("VIOLATION DETAILS (sorted by risk level):")
for sev, color, fp, tag, line, issue, fix in sorted(violations, key=lambda x: (0 if x[1] == "RED" else 1, x[2])):
    lines.append(f"  [{sev}] {fp}")
    lines.append(f"    Line: {line.strip()}")
    lines.append(f"    Issue: {issue}")
    lines.append(f"    Remediation: {fix}")
    lines.append("")

lines.append("COMPLIANT TOOLS (reference):")
for fp, _ in sorted(set(compliant_tools)):
    lines.append(f"  {fp}")
lines.append("")

lines.append("RECOMMENDATIONS:")
lines.append("  1. Replace all direct subprocess.Popen / raw claude binary invocations with spawn_headless_claude() (Layer 1) or dispatch_to_headless_claude() (OpenCode Layer 2).")
lines.append("  2. Remove -p/--print flags; enforce WRITE [PATH] in prompts.")
lines.append("  3. Ensure start_new_session=True for daemonized Claude processes.")
lines.append("  4. Verify OAuth token refresh timer: sudo systemctl enable --now claude-token-refresh.timer.")
lines.append("  5. Add pre-commit lint rule to block non-approved claude spawning.")
lines.append("")
lines.append("===")

report = "\n".join(lines)
print(report)
Path(out_path).write_text(report)
print(f"\nReport saved to {out_path}", file=sys.stderr)