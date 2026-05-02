#!/usr/bin/env python3
"""
test_headless_system.py — Integration Tests for Headless Dispatch
===================================================================
WHAT IT DOES
------------
Eight integration tests covering every layer of the headless dispatch
stack: path injection, OAuth loading, critical/optional module imports,
subprocess env construction, error paths for missing creds/token, and a
live end-to-end Sonnet dispatch.
WHY IT'S NECESSARY
------------------
Validates that the bulletproofing actually works under realistic
conditions — not just on the happy path. Tests 6 and 7 deliberately
break the system to confirm errors are RAISED EARLY with CLEAR messages
instead of silently producing a half-broken dispatch.
HOW IT PREVENTS THE PYTHONPATH BUG
----------------------------------
Test 1 asserts that sys.path actually contains every core/* directory
after init. Test 3 asserts that the canonical critical modules import.
Test 5 asserts that the env handed to a subprocess contains PYTHONPATH.
If any of these regress, this suite catches it before production does.
HOW TO USE IT
-------------
    /home/john/Thunderbird/.venv/bin/python \\
        /home/john/Thunderbird/tests/test_headless_system.py
    # Skip the live dispatch (free, ~5s):
    /home/john/Thunderbird/.venv/bin/python \\
        /home/john/Thunderbird/tests/test_headless_system.py --no-live
Tests return True/False (no exceptions escape). Exit 0 = all pass.
"""
from __future__ import annotations
import argparse
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Tuple
# ---------------------------------------------------------------------------
# Bootstrap (must happen BEFORE any thunderbird_* import)
# ---------------------------------------------------------------------------
THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(THUNDERBIRD_ROOT / "core" / "ai_infra"))
import thunderbird_dispatch_init as init_mod  # noqa: E402
# ---------------------------------------------------------------------------
# Pretty printing
# ---------------------------------------------------------------------------
USE_COLOR = sys.stdout.isatty()
GREEN = "\033[32m" if USE_COLOR else ""
RED = "\033[31m" if USE_COLOR else ""
YELLOW = "\033[33m" if USE_COLOR else ""
DIM = "\033[2m" if USE_COLOR else ""
RESET = "\033[0m" if USE_COLOR else ""
def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")
def _say(name: str, passed: bool, detail: str = "", remediation: str = "") -> None:
    marker = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
    print(f"[{_ts()}] [{marker}] {name}")
    if detail:
        print(f"            {DIM}{detail}{RESET}")
    if not passed and remediation:
        print(f"            {YELLOW}FIX:{RESET} {remediation}")
# ---------------------------------------------------------------------------
# Test 1 — sys.path injection
# ---------------------------------------------------------------------------
def test_path_injection() -> bool:
    name = "T1: sys.path injection"
    try:
        init_mod.reset_for_tests()
        state = init_mod.ensure_initialized()
    except Exception as e:
        _say(name, False, f"ensure_initialized() raised: {e}",
             "ensure deploy/thunderbird_pythonpath.env exists and is readable")
        return False
    expected_dirs = [
        "/home/john/Thunderbird/core/ai_infra",
        "/home/john/Thunderbird/core/email",
        "/home/john/Thunderbird/core/mcp",
    ]
    missing = [d for d in expected_dirs if d not in sys.path]
    if missing:
        _say(name, False, f"sys.path missing: {missing}",
             "verify deploy/thunderbird_pythonpath.env contains these dirs")
        return False
    if "PYTHONPATH" not in os.environ:
        _say(name, False, "os.environ['PYTHONPATH'] not set",
             "thunderbird_dispatch_init failed to write PYTHONPATH")
        return False
    _say(name, True,
         f"sys.path has all expected dirs; PYTHONPATH set "
         f"({len(os.environ['PYTHONPATH'])} chars)")
    return True
# ---------------------------------------------------------------------------
# Test 2 — OAuth token loading
# ---------------------------------------------------------------------------
def test_oauth_loading() -> bool:
    name = "T2: OAuth token loading"
    try:
        init_mod.reset_for_tests()
        state = init_mod.ensure_initialized()
    except Exception as e:
        _say(name, False, f"ensure_initialized() raised: {e}",
             "open Claude Desktop and sign in to refresh credentials")
        return False
    if not state.oauth_token_loaded:
        _say(name, False, "state.oauth_token_loaded is False",
             "open Claude Desktop and sign in")
        return False
    if "CLAUDE_CODE_OAUTH_TOKEN" not in state.env:
        _say(name, False, "CLAUDE_CODE_OAUTH_TOKEN missing from state.env",
             "thunderbird_dispatch_init.ensure_initialized has a bug")
        return False
    if "ANTHROPIC_API_KEY" in state.env:
        _say(name, False, "ANTHROPIC_API_KEY still in state.env (forces "
             "API-key path instead of OAuth)",
             "ensure_initialized must pop ANTHROPIC_API_KEY")
        return False
    token = state.env["CLAUDE_CODE_OAUTH_TOKEN"]
    _say(name, True, f"token present, {len(token)} chars; "
                     f"ANTHROPIC_API_KEY stripped")
    return True
# ---------------------------------------------------------------------------
# Test 3 — Critical modules import
# ---------------------------------------------------------------------------
CRITICAL_MODULES = [
    "thunderbird_headless_claude",
    "thunderbird_mcp_connector",
    "thunderbird_gmail",
]
def test_critical_imports() -> bool:
    name = "T3: critical modules import"
    init_mod.ensure_initialized()
    failed: List[Tuple[str, str]] = []
    for mod in CRITICAL_MODULES:
        try:
            importlib.import_module(mod)
        except Exception as e:
            failed.append((mod, f"{type(e).__name__}: {e}"))
    if failed:
        for m, err in failed:
            print(f"            {RED}- {m}: {err}{RESET}")
        _say(name, False, f"{len(failed)}/{len(CRITICAL_MODULES)} failed",
             "check the module exists and its top-level imports are valid")
        return False
    _say(name, True, f"all {len(CRITICAL_MODULES)} modules imported")
    return True
# ---------------------------------------------------------------------------
# Test 4 — Optional module fails gracefully
# ---------------------------------------------------------------------------
def test_optional_import_graceful() -> bool:
    """
    A missing optional module must NOT crash the system. Instead it should
    raise ImportError that the caller can catch. This test confirms
    importlib gives us a clean, catchable exception.
    """
    name = "T4: optional module fails gracefully"
    init_mod.ensure_initialized()
    bogus_name = "thunderbird_definitely_not_a_real_module_xyz"
    try:
        importlib.import_module(bogus_name)
    except ImportError:
        _say(name, True, f"ImportError raised cleanly for {bogus_name}")
        return True
    except Exception as e:
        _say(name, False, f"got {type(e).__name__} instead of ImportError",
             "callers expect a catchable ImportError for missing optional deps")
        return False
    _say(name, False, f"import of {bogus_name} unexpectedly succeeded",
         "this should never happen — investigate sys.modules pollution")
    return False
# ---------------------------------------------------------------------------
# Test 5 — Subprocess environment carries PYTHONPATH and OAuth token
# ---------------------------------------------------------------------------
def test_subprocess_env() -> bool:
    name = "T5: subprocess env carries PYTHONPATH + token"
    state = init_mod.ensure_initialized()
    # Spawn `python -c` with state.env and have it dump the relevant vars.
    probe = (
        "import os, json, sys; "
        "print(json.dumps({"
        "'PYTHONPATH': os.environ.get('PYTHONPATH', ''), "
        "'TOKEN_LEN': len(os.environ.get('CLAUDE_CODE_OAUTH_TOKEN', '')), "
        "'HAS_API_KEY': 'ANTHROPIC_API_KEY' in os.environ"
        "}))"
    )
    try:
        rc = subprocess.run(
            [sys.executable, "-c", probe],
            env=state.env,
            capture_output=True, text=True, timeout=10,
        )
    except Exception as e:
        _say(name, False, f"subprocess failed: {e}", "debug locally")
        return False
    if rc.returncode != 0:
        _say(name, False, f"rc={rc.returncode} stderr={rc.stderr[:200]}",
             "investigate subprocess invocation")
        return False
    try:
        d = json.loads(rc.stdout.strip())
    except Exception as e:
        _say(name, False, f"could not parse probe output: {e}",
             "subprocess emitted unexpected stdout")
        return False
    if "/home/john/Thunderbird/core/ai_infra" not in d["PYTHONPATH"]:
        _say(name, False,
             f"child PYTHONPATH missing core/ai_infra: {d['PYTHONPATH'][:200]}",
             "thunderbird_dispatch_init.ensure_initialized failed to inject")
        return False
    if d["TOKEN_LEN"] < 10:
        _say(name, False, f"TOKEN_LEN={d['TOKEN_LEN']} (too short)",
             "OAuth token did not propagate to child env")
        return False
    if d["HAS_API_KEY"]:
        _say(name, False, "child still sees ANTHROPIC_API_KEY",
             "ensure_initialized must pop ANTHROPIC_API_KEY")
        return False
    _say(name, True,
         f"child PYTHONPATH={len(d['PYTHONPATH'])} chars, "
         f"token={d['TOKEN_LEN']} chars, no api-key leak")
    return True
# ---------------------------------------------------------------------------
# Test 6 — Missing credentials.json fails with clear error
# ---------------------------------------------------------------------------
def test_missing_credentials_fails_clearly() -> bool:
    name = "T6: missing credentials → clear RuntimeError"
    creds_path = Path.home() / ".claude" / ".credentials.json"
    if not creds_path.exists():
        _say(name, False, "credentials file already missing — cannot test",
             "open Claude Desktop and sign in, then re-run")
        return False
    # Move the real file aside, run init, restore.
    backup = creds_path.with_suffix(".test-backup")
    shutil.move(str(creds_path), str(backup))
    try:
        init_mod.reset_for_tests()
        try:
            init_mod.ensure_initialized()
        except RuntimeError as e:
            msg = str(e)
            if "credentials file missing" in msg.lower() and "REMEDIATION" in msg:
                _say(name, True,
                     "RuntimeError raised with REMEDIATION line")
                return True
            _say(name, False,
                 f"RuntimeError raised but message lacks expected wording: "
                 f"{msg[:200]}",
                 "update _load_oauth_token to include 'credentials file missing' "
                 "and 'REMEDIATION:'")
            return False
        except Exception as e:
            _say(name, False,
                 f"got {type(e).__name__} instead of RuntimeError: {e}",
                 "ensure_initialized must convert credential errors to RuntimeError")
            return False
        _say(name, False,
             "ensure_initialized succeeded with no credentials file (!)",
             "credential check is not running")
        return False
    finally:
        # Always restore the real file. Critical.
        shutil.move(str(backup), str(creds_path))
        init_mod.reset_for_tests()
# ---------------------------------------------------------------------------
# Test 7 — Empty token in credentials.json fails with clear error
# ---------------------------------------------------------------------------
def test_empty_token_fails_clearly() -> bool:
    name = "T7: empty OAuth token → clear RuntimeError"
    creds_path = Path.home() / ".claude" / ".credentials.json"
    if not creds_path.exists():
        _say(name, False, "credentials file missing — cannot test",
             "sign in via Claude Desktop")
        return False
    real = creds_path.read_text()
    backup = creds_path.with_suffix(".test-backup")
    shutil.copy(str(creds_path), str(backup))
    try:
        # Write a valid-JSON file with no token
        creds_path.write_text(json.dumps({"claudeAiOauth": {}}))
        init_mod.reset_for_tests()
        try:
            init_mod.ensure_initialized()
        except RuntimeError as e:
            msg = str(e)
            if "accessToken" in msg and "REMEDIATION" in msg:
                _say(name, True, "RuntimeError raised with REMEDIATION line")
                return True
            _say(name, False, f"RuntimeError lacks expected wording: {msg[:200]}",
                 "update _load_oauth_token error message")
            return False
        except Exception as e:
            _say(name, False, f"got {type(e).__name__} not RuntimeError: {e}",
                 "ensure_initialized must convert token errors to RuntimeError")
            return False
        _say(name, False, "ensure_initialized succeeded with empty token (!)",
             "token validation is not running")
        return False
    finally:
        # Always restore the real credentials file
        creds_path.write_text(real)
        try:
            backup.unlink()
        except Exception:
            pass
        init_mod.reset_for_tests()
# ---------------------------------------------------------------------------
# Test 8 — End-to-end live dispatch via Sonnet
# ---------------------------------------------------------------------------
def test_live_dispatch_sonnet(timeout_s: int = 120) -> bool:
    name = "T8: live end-to-end dispatch via Sonnet"
    state = init_mod.ensure_initialized()
    out_file = Path(tempfile.gettempdir()) / "test_headless_sonnet_output.txt"
    out_file.unlink(missing_ok=True)
    prompt = (
        "Write exactly 100 words about why the Caribbean is a great cruise "
        "destination. Begin your response with the marker 'BEGIN-CARIBBEAN' "
        "and end with the marker 'END-CARIBBEAN'. Output nothing else."
    )
    t0 = time.time()
    try:
        rc = subprocess.run(
            [state.claude_binary, "--model", "claude-sonnet-4-6",
             "--output-format", "text"],
            input=prompt,
            capture_output=True, text=True,
            env=state.env,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        _say(name, False, f"timed out after {timeout_s}s",
             "check OAuth token freshness and network connectivity")
        return False
    elapsed = time.time() - t0
    if rc.returncode != 0:
        _say(name, False,
             f"rc={rc.returncode} stderr={rc.stderr[:200]}",
             "run `/home/john/.local/bin/claude --version` manually; "
             "if 401, reauth via Claude Desktop")
        return False
    out = (rc.stdout or "").strip()
    if "BEGIN-CARIBBEAN" not in out or "END-CARIBBEAN" not in out:
        _say(name, False,
             f"response missing markers: {out[:200]!r}",
             "model may have ignored the marker instructions; rerun")
        return False
    out_file.write_text(out)
    _say(name, True,
         f"completed in {elapsed:.1f}s, "
         f"{len(out)} chars written to {out_file}")
    return True
# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
ALL_TESTS: List[Tuple[str, Callable[[], bool], bool]] = [
    ("T1", test_path_injection, False),
    ("T2", test_oauth_loading, False),
    ("T3", test_critical_imports, False),
    ("T4", test_optional_import_graceful, False),
    ("T5", test_subprocess_env, False),
    ("T6", test_missing_credentials_fails_clearly, False),
    ("T7", test_empty_token_fails_clearly, False),
    ("T8", test_live_dispatch_sonnet, True),  # `live=True`
]
def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-live", action="store_true",
                    help="skip tests that hit the real Claude API")
    ap.add_argument("--only", help="comma-separated test ids (e.g. T1,T3)")
    args = ap.parse_args(argv)
    only = set(s.strip() for s in args.only.split(",")) if args.only else None
    print(f"Thunderbird Headless Dispatch — Integration Test Suite")
    print(f"=" * 60)
    results: List[Tuple[str, bool]] = []
    for tid, fn, is_live in ALL_TESTS:
        if only and tid not in only:
            continue
        if is_live and args.no_live:
            print(f"[{_ts()}] [{YELLOW}SKIP{RESET}] {tid}: --no-live")
            continue
        try:
            ok = fn()
        except Exception as e:
            print(f"[{_ts()}] [{RED}CRASH{RESET}] {tid}: "
                  f"unhandled {type(e).__name__}: {e}")
            ok = False
        results.append((tid, ok))
    print()
    print("=" * 60)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    if passed == total:
        print(f"{GREEN}ALL PASS{RESET}: {passed}/{total}")
        return 0
    print(f"{RED}FAILURES{RESET}: {passed}/{total} passed")
    for tid, ok in results:
        if not ok:
            print(f"   - {tid}")
    return 1
if __name__ == "__main__":
    sys.exit(main())

