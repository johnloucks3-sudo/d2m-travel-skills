#!/usr/bin/env python3
"""
A7 Pre-Commit Gate — Sterling's three compliance checks.
Called from .git/hooks/pre-commit with staged file list.
Exit 0 = pass. Exit 1 = block with explanation.
"""
import sys
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path("/home/john/Thunderbird")

# Approved files that MAY call subprocess.Popen with claude binary
CLAUDE_SPAWN_WHITELIST = {
    "core/ai_infra/thunderbird_headless_spawn.py",
    "OpsCenter/opencode_headless_claude_dispatch.py",
    "OpsCenter/headless_claude_fallback.py",
    # Tasking watcher spawns opencode (not claude) — false positive due to CLAUDE_INBOX variable
    "core/watchtower/thunderbird_tasking_watcher.py",
    "OpsCenter/thunderbird_tasking_watcher.py",
    # This gate script itself — uses subprocess.Popen for git, not claude
    "OpsCenter/a7_pre_commit_gate.py",
    # Metronome spawns Python (intel_keeper.py), not the claude binary.
    # "claude" string comes from DISPATCH_SCRIPT path reference, not a spawn target.
    "OpsCenter/metronome.py",
    # MAX proxy IS the approved Claude CLI wrapper for OpenCode — exempted by design.
    "OpsCenter/max_proxy.py",
    # dispatch_opencode.py spawns the opencode binary (not claude). "claude" appears only
    # in comments referencing "Claude Code" (the tool name). False positive on line-56 pattern.
    "OpsCenter/dispatch_opencode.py",
    # self_observability.py: primary strike = managed-agent API (no spawn); the FALLBACK
    # shells out to the APPROVED dispatch_claude.py wrapper (which routes through
    # thunderbird_headless_spawn). Compliant — false positive on the Popen+"claude" heuristic.
    "core/ci/self_observability.py",
    # slot_router/dispatcher.py: Popen spawns opencode_sonnet_inline.py (Python script),
    # NOT the claude binary. "claude" appears only in model ID string constants
    # ('claude-sonnet-4-6' etc.) — false positive on the heuristic.
    "OpsCenter/slot_router/dispatcher.py",
    # elon_daily_synthesis.py: spawns the claude CLI for EOD synthesis sessions.
    # Uses approved token injection pattern (CLAUDE_CODE_OAUTH_TOKEN in env)
    # and start_new_session=True. Exempted by Hale override authority (PRODUCTION-LOCK retired
    # 2026-06-10) with post-hoc Sterling notification. Upgrade to headless_spawn wrapper
    # tracked as MISSION-436.
    "intel/daily_search/elon_daily_synthesis.py",
}

# Functions that must NOT call _wrap_body_html or _wrap_staff_html
DRAFT_PATTERNS = re.compile(r'def\s+\w*(draft|create_draft)\w*', re.IGNORECASE)
WRAP_CALL = re.compile(r'_wrap_body_html\(|_wrap_staff_html\(')


def get_staged_files():
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    return [f.strip() for f in result.stdout.splitlines() if f.strip()]


def check_claude_spawn_whitelist(staged_files):
    """Block subprocess.Popen(['claude'...]) outside approved wrappers."""
    violations = []
    for rel_path in staged_files:
        if rel_path in CLAUDE_SPAWN_WHITELIST:
            continue
        if not rel_path.endswith(".py"):
            continue
        full = REPO_ROOT / rel_path
        if not full.exists():
            continue
        content = full.read_text(errors="replace")
        if "subprocess.Popen" in content and ("claude" in content or "CLAUDE_BIN" in content):
            violations.append(rel_path)
    return violations


def check_two_lane_pipeline(staged_files):
    """Block _wrap_body_html/_wrap_staff_html inside draft-creation functions."""
    violations = []
    for rel_path in staged_files:
        if not rel_path.endswith(".py"):
            continue
        full = REPO_ROOT / rel_path
        if not full.exists():
            continue
        content = full.read_text(errors="replace")
        lines = content.splitlines()
        in_draft_fn = False
        for i, line in enumerate(lines):
            if DRAFT_PATTERNS.search(line):
                in_draft_fn = True
            if in_draft_fn and WRAP_CALL.search(line):
                violations.append(f"{rel_path}:{i+1}")
            if in_draft_fn and re.match(r'\s*(async\s+)?def\s+', line) and i > 0:
                in_draft_fn = False  # new function started (handles both def and async def)
    return violations


def check_duplicate_scripts(staged_files):
    """Flag if any directory now has 3+ versioned scripts (*_v[0-9]*.py)."""
    from collections import defaultdict
    dirs_checked = set()
    violations = []
    for rel_path in staged_files:
        parent = (REPO_ROOT / rel_path).parent
        if parent in dirs_checked:
            continue
        dirs_checked.add(parent)
        versioned = list(parent.glob("*_v[0-9]*.py")) + list(parent.glob("*_v[0-9][0-9]*.py"))
        if len(versioned) >= 3:
            names = ", ".join(p.name for p in sorted(versioned))
            violations.append(f"{parent.relative_to(REPO_ROOT)}: {names}")
    return violations


def main():
    staged = get_staged_files()
    if not staged:
        sys.exit(0)

    errors = []

    spawn_violations = check_claude_spawn_whitelist(staged)
    if spawn_violations:
        errors.append(
            "A7 GATE — Headless Claude Spawn Pattern (SO 24 APR 2026):\n"
            "  Direct subprocess.Popen of claude binary outside approved wrappers.\n"
            "  Use core/ai_infra/thunderbird_headless_spawn.py instead.\n"
            "  Violations: " + ", ".join(spawn_violations)
        )

    pipeline_violations = check_two_lane_pipeline(staged)
    if pipeline_violations:
        errors.append(
            "A7 GATE — Two-Lane Email Pipeline (SO 07 MAY 2026):\n"
            "  _wrap_body_html()/_wrap_staff_html() called inside a draft-creation function.\n"
            "  Apply stationery at publish time only (publish_draft()), never at draft creation.\n"
            "  Violations: " + ", ".join(pipeline_violations)
        )

    dup_violations = check_duplicate_scripts(staged)
    if dup_violations:
        errors.append(
            "A7 GATE — Duplicate Script Sprawl:\n"
            "  3+ versioned scripts in the same directory. Retire old versions before adding new.\n"
            "  Directories: " + "; ".join(dup_violations)
        )

    if errors:
        print("\n" + "="*60, file=sys.stderr)
        print("A7 STERLING PRE-COMMIT GATE — BLOCKED", file=sys.stderr)
        print("="*60, file=sys.stderr)
        for e in errors:
            print(f"\n{e}", file=sys.stderr)
        print("\nFix violations above, then re-commit.", file=sys.stderr)
        print("="*60 + "\n", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
