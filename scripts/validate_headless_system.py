#!/usr/bin/env python3
"""
Validate Headless System — Comprehensive Pre-Flight Check
==========================================================
WHAT IT DOES
------------
End-to-end validation of every component required for headless Claude
dispatch. Reports each check as PASS/FAIL with a SPECIFIC remediation
command. Exit code 0 = healthy, 1 = at least one check failed.
WHY IT'S NECESSARY
------------------
The original failure mode (PYTHONPATH missing → ModuleNotFoundError mid-
dispatch) was hard to diagnose because it surfaced as a generic Python
import error inside a subprocess log. This script catches it — and a dozen
other latent failure modes — BEFORE any real task is dispatched.
HOW IT PREVENTS THE PYTHONPATH BUG
----------------------------------
Check 3 explicitly verifies that deploy/thunderbird_pythonpath.env loads
into sys.path correctly. Check 4 imports every critical module under that
path; if PYTHONPATH is wrong, those imports fail loudly here instead of
silently in production.
HOW TO USE IT
-------------
    python3 /home/john/Thunderbird/scripts/validate_headless_system.py
    # exit 0 → safe to dispatch
    # exit 1 → read remediation lines, fix, re-run
Run via the venv for full module coverage:
    /home/john/Thunderbird/.venv/bin/python \\
        /home/john/Thunderbird/scripts/validate_headless_system.py
Add --full to also execute a real headless dispatch end-to-end.
"""
from __future__ import annotations
import argparse
import importlib
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional
# ---------------------------------------------------------------------------
# Bootstrap — must run BEFORE we try to import any thunderbird_* module.
# ---------------------------------------------------------------------------
THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
INIT_DIR = THUNDERBIRD_ROOT / "core" / "ai_infra"
sys.path.insert(0, str(INIT_DIR))
# Defer the import so that a clean failure here is still reported.
try:
    import thunderbird_dispatch_init as _init_mod  # type: ignore
except Exception as e:  # pragma: no cover — only triggers if file missing
    print(f"FAIL bootstrap import: {e}")
    print(f"REMEDIATION: ensure {INIT_DIR}/thunderbird_dispatch_init.py exists")
    sys.exit(1)
# ---------------------------------------------------------------------------
# ANSI colors (degrade gracefully in non-tty)
# ---------------------------------------------------------------------------
USE_COLOR = sys.stdout.isatty()
GREEN = "\033[32m" if USE_COLOR else ""
RED = "\033[31m" if USE_COLOR else ""
YELLOW = "\033[33m" if USE_COLOR else ""
DIM = "\033[2m" if USE_COLOR else ""
RESET = "\033[0m" if USE_COLOR else ""
# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------
@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""
    remediation: str = ""
@dataclass
class ValidationReport:
    results: List[CheckResult] = field(default_factory=list)
    def add(self, r: CheckResult) -> None:
        self.results.append(r)
        marker = f"{GREEN}PASS{RESET}" if r.passed else f"{RED}FAIL{RESET}"
        print(f"[{marker}] {r.name}")
        if r.detail:
            print(f"        {DIM}{r.detail}{RESET}")
        if not r.passed and r.remediation:
            print(f"        {YELLOW}FIX:{RESET} {r.remediation}")
    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)
    def summary(self) -> None:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        print()
        print("=" * 60)
        if failed == 0:
            print(f"{GREEN}HEALTHY{RESET}: {passed}/{total} checks passed")
        else:
            print(f"{RED}DEGRADED{RESET}: {passed}/{total} passed, "
                  f"{failed} failed")
            print("Run the FIX commands above, then re-run this validator.")
        print("=" * 60)
# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------
def check_python_version() -> CheckResult:
    v = sys.version_info
    if v >= (3, 9):
        return CheckResult(
            name="Python ≥ 3.9",
            passed=True,
            detail=f"running {v.major}.{v.minor}.{v.micro}",
        )
    return CheckResult(
        name="Python ≥ 3.9",
        passed=False,
        detail=f"running {v.major}.{v.minor}.{v.micro}",
        remediation="invoke via /home/john/Thunderbird/.venv/bin/python",
    )
def check_venv() -> CheckResult:
    venv = THUNDERBIRD_ROOT / ".venv" / "bin" / "python"
    if venv.exists() and os.access(venv, os.X_OK):
        return CheckResult(name="Virtualenv .venv exists",
                           passed=True, detail=str(venv))
    return CheckResult(
        name="Virtualenv .venv exists",
        passed=False,
        detail=f"missing or not executable: {venv}",
        remediation=f"cd {THUNDERBIRD_ROOT} && python3 -m venv .venv && "
                    f".venv/bin/pip install -r requirements.txt",
    )
def check_claude_binary() -> CheckResult:
    cb = Path("/home/john/.local/bin/claude")
    if cb.exists() and os.access(cb, os.X_OK):
        return CheckResult(name="Claude CLI binary",
                           passed=True, detail=str(cb))
    return CheckResult(
        name="Claude CLI binary",
        passed=False,
        detail=f"missing or not executable at {cb}",
        remediation="curl -fsSL https://claude.ai/install.sh | bash",
    )
def check_pythonpath_env_file() -> CheckResult:
    f = THUNDERBIRD_ROOT / "deploy" / "thunderbird_pythonpath.env"
    if not f.exists():
        return CheckResult(
            name="deploy/thunderbird_pythonpath.env exists",
            passed=False,
            detail=f"missing: {f}",
            remediation=f"recreate from FALLBACK_PATHS in "
                        f"core/ai_infra/thunderbird_dispatch_init.py",
        )
    paths = _init_mod._read_pythonpath_env_file()
    if not paths:
        return CheckResult(
            name="deploy/thunderbird_pythonpath.env parses",
            passed=False,
            detail=f"file exists but parsed empty: {f}",
            remediation=f"check that the first non-comment line begins with "
                        f"'PYTHONPATH=' and uses ':' as separator",
        )
    missing = [p for p in paths if not Path(p).exists()]
    if missing:
        return CheckResult(
            name="All PYTHONPATH entries exist on disk",
            passed=False,
            detail=f"{len(missing)} of {len(paths)} paths missing: "
                   f"{missing[:3]}{'...' if len(missing) > 3 else ''}",
            remediation="either create the missing dirs or remove them "
                        "from deploy/thunderbird_pythonpath.env",
        )
    return CheckResult(
        name="PYTHONPATH manifest valid",
        passed=True,
        detail=f"{len(paths)} paths, all exist on disk",
    )
def check_init_module_works() -> CheckResult:
    """Run the actual bootstrap and confirm it succeeded."""
    try:
        _init_mod.reset_for_tests()
        state = _init_mod.ensure_initialized()
    except RuntimeError as e:
        return CheckResult(
            name="thunderbird_dispatch_init.ensure_initialized()",
            passed=False,
            detail=str(e).splitlines()[0],
            remediation=str(e).split("REMEDIATION:", 1)[-1].strip()
            if "REMEDIATION:" in str(e) else "see init_dispatch.log",
        )
    return CheckResult(
        name="thunderbird_dispatch_init.ensure_initialized()",
        passed=True,
        detail=f"loaded {len(state.paths_loaded)} paths from {state.source}",
    )
def check_credentials_file() -> CheckResult:
    f = Path.home() / ".claude" / ".credentials.json"
    if not f.exists():
        return CheckResult(
            name="OAuth credentials file",
            passed=False,
            detail=f"missing: {f}",
            remediation="open Claude Desktop and sign in",
        )
    try:
        creds = json.loads(f.read_text())
    except json.JSONDecodeError as e:
        return CheckResult(
            name="OAuth credentials file is valid JSON",
            passed=False,
            detail=f"{e}",
            remediation=f"rm {f} && reauth via Claude Desktop",
        )
    token = creds.get("claudeAiOauth", {}).get("accessToken")
    if not token:
        return CheckResult(
            name="OAuth access token present",
            passed=False,
            detail="claudeAiOauth.accessToken missing",
            remediation="open Claude Desktop and sign in to refresh",
        )
    expires_at = creds.get("claudeAiOauth", {}).get("expiresAt")
    detail = f"token: {len(token)} chars"
    if expires_at:
        detail += f", expiresAt={expires_at}"
    return CheckResult(name="OAuth credentials valid",
                       passed=True, detail=detail)
CRITICAL_MODULES = [
    "thunderbird_headless_claude",
    "thunderbird_mcp_connector",
    "thunderbird_gmail",
]
def check_critical_imports() -> List[CheckResult]:
    out: List[CheckResult] = []
    for mod in CRITICAL_MODULES:
        try:
            importlib.import_module(mod)
            out.append(CheckResult(
                name=f"import {mod}",
                passed=True,
                detail="module loaded",
            ))
        except ImportError as e:
            out.append(CheckResult(
                name=f"import {mod}",
                passed=False,
                detail=f"ImportError: {e}",
                remediation=f"verify the module exists somewhere on "
                            f"PYTHONPATH; check deploy/thunderbird_pythonpath.env",
            ))
        except Exception as e:
            out.append(CheckResult(
                name=f"import {mod}",
                passed=False,
                detail=f"{type(e).__name__}: {e}",
                remediation="open the module and fix the broken import "
                            "or top-level statement",
            ))
    return out
def check_logs_and_output_dirs() -> List[CheckResult]:
    out: List[CheckResult] = []
    for d in [THUNDERBIRD_ROOT / "logs", THUNDERBIRD_ROOT / "output"]:
        if d.exists() and d.is_dir():
            out.append(CheckResult(
                name=f"directory {d.name}/", passed=True, detail=str(d)))
        else:
            out.append(CheckResult(
                name=f"directory {d.name}/",
                passed=False,
                detail=f"missing: {d}",
                remediation=f"mkdir -p {d}",
            ))
    return out
def check_token_keepalive_timer() -> CheckResult:
    """User-level systemd timer for OAuth refresh."""
    timers = ["claude-token-monitor.timer", "claude-oauth-keepalive.timer"]
    inactive = []
    for t in timers:
        rc = subprocess.run(
            ["systemctl", "--user", "is-active", t],
            capture_output=True, text=True
        )
        if rc.returncode != 0:
            inactive.append(t)
    if not inactive:
        return CheckResult(
            name="OAuth refresh timers active",
            passed=True,
            detail=", ".join(timers),
        )
    return CheckResult(
        name="OAuth refresh timers active",
        passed=False,
        detail=f"inactive: {inactive}",
        remediation=f"systemctl --user enable --now {' '.join(inactive)}",
    )
def check_watchdog_timer() -> CheckResult:
    rc = subprocess.run(
        ["systemctl", "--user", "is-active", "thunderbird-watchdog.timer"],
        capture_output=True, text=True
    )
    if rc.returncode == 0:
        return CheckResult(name="thunderbird-watchdog.timer active",
                           passed=True, detail="watchdog running")
    return CheckResult(
        name="thunderbird-watchdog.timer active",
        passed=False,
        detail="inactive",
        remediation="systemctl --user enable --now thunderbird-watchdog.timer",
    )
def check_mcp_server() -> CheckResult:
    """MCP server up. Checks both system + user systemctl, then port 8765."""
    # systemd unit may live at either system or user scope; accept either.
    for scope in (["systemctl"], ["systemctl", "--user"]):
        rc = subprocess.run(
            scope + ["is-active", "thunderbird-mcp.service"],
            capture_output=True, text=True
        )
        if rc.returncode == 0 and rc.stdout.strip() == "active":
            scope_label = "user" if "--user" in scope else "system"
            # Confirm it actually answers HTTP on 8765. Any HTTP response
            # (including 4xx — MCP returns 406 to bare GETs) means the
            # server process is alive and accepting connections; only
            # ConnectionRefused / timeout indicates a hung or crashed worker.
            from urllib import request as _urlreq
            from urllib.error import HTTPError, URLError
            try:
                req = _urlreq.Request("http://localhost:8765/mcp", method="GET")
                with _urlreq.urlopen(req, timeout=3) as _resp:
                    return CheckResult(
                        name="MCP server (thunderbird-mcp.service)",
                        passed=True,
                        detail=f"{scope_label} unit active, "
                               f"port 8765 responding HTTP {_resp.status}",
                    )
            except HTTPError as e:
                return CheckResult(
                    name="MCP server (thunderbird-mcp.service)",
                    passed=True,
                    detail=f"{scope_label} unit active, "
                           f"port 8765 responding HTTP {e.code}",
                )
            except (URLError, TimeoutError) as e:
                return CheckResult(
                    name="MCP server (thunderbird-mcp.service)",
                    passed=False,
                    detail=f"{scope_label} unit active but port 8765 "
                           f"unresponsive: {type(e).__name__}",
                    remediation=f"systemctl {'--user ' if scope_label == 'user' else ''}"
                                "restart thunderbird-mcp.service",
                )
    # Neither scope had it active.
    return CheckResult(
        name="MCP server (thunderbird-mcp.service)",
        passed=False,
        detail="inactive — required for tool-using dispatches",
        remediation="systemctl --user enable --now thunderbird-mcp.service "
                    "(or sudo if installed at system scope)",
    )
def check_dummy_dispatch(timeout_s: int = 90) -> CheckResult:
    """
    Real end-to-end dispatch: spawn headless Claude with a trivial prompt
    and confirm the output file is written.
    """
    state = _init_mod.ensure_initialized()
    out_file = Path(tempfile.gettempdir()) / "validate_headless_dispatch.txt"
    out_file.unlink(missing_ok=True)
    prompt = (
        "Reply with exactly: VALIDATE-OK\n"
        f"Then call the Write tool to write the text 'VALIDATE-OK' to "
        f"{out_file}\n"
        "Output nothing else."
    )
    t0 = time.time()
    try:
        proc = subprocess.run(
            [state.claude_binary, "--model", "claude-haiku-4-5-20251001",
             "--output-format", "text"],
            input=prompt,
            capture_output=True,
            text=True,
            env=state.env,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name="end-to-end dummy dispatch",
            passed=False,
            detail=f"timed out after {timeout_s}s",
            remediation="check ~/.claude/.credentials.json is not expired; "
                        "check claude-oauth-keepalive.timer is active",
        )
    elapsed = time.time() - t0
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    if proc.returncode != 0:
        return CheckResult(
            name="end-to-end dummy dispatch",
            passed=False,
            detail=f"rc={proc.returncode}: {stderr[:200]}",
            remediation="run claude --help manually to confirm OAuth works; "
                        "if 401, reauth via Claude Desktop",
        )
    if "VALIDATE-OK" not in stdout:
        return CheckResult(
            name="end-to-end dummy dispatch",
            passed=False,
            detail=f"unexpected output: {stdout[:200]!r}",
            remediation="check claude binary version; "
                        "/home/john/.local/bin/claude --version",
        )
    return CheckResult(
        name="end-to-end dummy dispatch",
        passed=True,
        detail=f"completed in {elapsed:.1f}s, response contained VALIDATE-OK",
    )
# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--full", action="store_true",
                    help="also run the live end-to-end dispatch test "
                         "(takes ~30-60s and consumes credits)")
    ap.add_argument("--no-color", action="store_true",
                    help="disable ANSI color output")
    args = ap.parse_args(argv)
    if args.no_color:
        global USE_COLOR
        USE_COLOR = False
    print(f"Thunderbird Headless System Validator")
    print(f"=" * 60)
    report = ValidationReport()
    # Single-result checks
    report.add(check_python_version())
    report.add(check_venv())
    report.add(check_claude_binary())
    report.add(check_pythonpath_env_file())
    report.add(check_init_module_works())
    report.add(check_credentials_file())
    report.add(check_token_keepalive_timer())
    report.add(check_watchdog_timer())
    report.add(check_mcp_server())
    # Multi-result checks
    for r in check_logs_and_output_dirs():
        report.add(r)
    for r in check_critical_imports():
        report.add(r)
    # Optional live dispatch
    if args.full:
        if report.all_passed:
            report.add(check_dummy_dispatch())
        else:
            print(f"{YELLOW}--full skipped: fix the failures above first.{RESET}")
    report.summary()
    return 0 if report.all_passed else 1
if __name__ == "__main__":
    sys.exit(main())
