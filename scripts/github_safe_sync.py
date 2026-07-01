#!/usr/bin/env python3
"""
github_safe_sync.py — gated box→GitHub push (Commander directive 2026-07-01).

WHY: GitHub (origin) froze at 2026-06-12 while the box advanced ~3 weeks.
Every cloud/Ultraplan session starts from GitHub, so stale origin makes cloud
execution useless-or-dangerous (a cloud PR from the June-12 base would silently
revert weeks of fixes). This script keeps origin current — but ONLY through a
secrets gate, because MISSION-SEC-05 records that live secrets were pushed to
this repo once before.

THE GATE (all must pass before any push):
  1. gitleaks scan of the unpushed range (rule-based).
  2. Path/pattern scan of the TRACKED tree for credential-shaped files gitleaks
     misses (cookies.json with live values, credentials.json, token files) —
     this is the check that caught config/poe_cookies.json on 2026-07-01.
  3. Valid GitHub PAT (from Infisical GITHUB_TOKEN → env fallback).
  4. One-time history acknowledgment: unpushed history contains the now-untracked
     config/poe_cookies.json blob (added 2026-06-25). Push is allowed only when
     the Commander has rotated the Poe cookie (state flag below) OR explicitly
     forces. State: config/github_sync_state.json {"poe_cookie_rotated": bool}.

Exit: 0 pushed/clean-noop · 2 gate blocked · 3 auth failed.
Usage:
  .venv/bin/python3 scripts/github_safe_sync.py            # gate + push
  .venv/bin/python3 scripts/github_safe_sync.py --check    # gate only, no push
  .venv/bin/python3 scripts/github_safe_sync.py --ack-poe-rotated  # Commander rotated Poe login
"""
from __future__ import annotations
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
STATE = ROOT / "config" / "github_sync_state.json"
REMOTE = "origin"
BRANCH = "master"
# Credential-shaped tracked-file patterns gitleaks does not reliably catch.
SUSPECT_PATTERNS = ("cookie", "credentials.json", ".env", "gmail-mcp", "_token.json",
                    "session.json", "creds/")
SUSPECT_ALLOW = (".example", ".template", ".md", "cookie_refresh_status",
                 "cookie_alert_dedup", "SOP",
                 # verified clean 2026-07-01 (code/status only, no credential values):
                 "grab_regent_cookies_cdp.py", "regent_firefox_cookie_capture.py",
                 "silversea_cookie_refresh.py", "vtg_cookie_refresh.py",
                 "silversea_session.json")


def _run(cmd: list[str] | str, **kw) -> subprocess.CompletedProcess:
    shell = isinstance(cmd, str)
    return subprocess.run(cmd, shell=shell, capture_output=True, text=True,
                          cwd=str(ROOT), timeout=kw.pop("timeout", 300), **kw)


def _load_state() -> dict:
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def _save_state(d: dict) -> None:
    STATE.write_text(json.dumps(d, indent=2) + "\n")


def _token() -> str:
    try:
        sys.path.insert(0, str(ROOT))
        from core.secrets.infisical_client import get_secret
        return get_secret("GITHUB_TOKEN") or ""
    except Exception:
        import os
        return os.environ.get("GITHUB_TOKEN", "")


def gate() -> tuple[bool, list[str]]:
    problems: list[str] = []

    # 1. gitleaks over the unpushed range (fall back to since-date if no remote ref)
    has_remote_ref = _run(["git", "rev-parse", "--verify", f"{REMOTE}/{BRANCH}"]).returncode == 0
    log_opts = f"{REMOTE}/{BRANCH}..HEAD" if has_remote_ref else "--since=2026-06-12"
    r = _run(["gitleaks", "detect", "--source", ".", f"--log-opts={log_opts}",
              "--no-banner", "--redact"])
    if r.returncode != 0:
        problems.append(f"gitleaks found leaks in range ({log_opts}) — run gitleaks -v to inspect")

    # 2. credential-shaped TRACKED files (the gitleaks blind spot)
    tracked = _run(["git", "ls-files"]).stdout.splitlines()
    for f in tracked:
        low = f.lower()
        if any(p in low for p in SUSPECT_PATTERNS) and not any(a.lower() in low for a in SUSPECT_ALLOW):
            problems.append(f"credential-shaped tracked file: {f} — untrack or allowlist before push")

    # 3. poe-cookie history acknowledgment (one-time; blob sits in unpushed history)
    st = _load_state()
    if not st.get("poe_cookie_rotated"):
        problems.append("unpushed history contains config/poe_cookies.json (live Poe login, added "
                        "2026-06-25). Rotate Poe login (log out/in at poe.com) then run "
                        "--ack-poe-rotated. History then carries only a dead credential.")
    return (not problems), problems


def push() -> int:
    tok = _token()
    if not tok:
        print("BLOCKED(auth): no GITHUB_TOKEN available")
        return 3
    # GitHub HTTPS uses Basic auth (token as password via x-access-token), NOT a
    # Bearer header — the Bearer form returns "invalid credentials" even on a valid
    # token (diagnosed 2026-07-01). Inject via an ephemeral credential URL.
    push_url = f"https://x-access-token:{tok}@github.com/johnloucks3-sudo/thunderbird-os.git"
    r = _run(["git", "push", push_url, f"{BRANCH}:{BRANCH}"], timeout=600)
    if r.returncode != 0:
        err = ((r.stderr or r.stdout)[-300:]).replace(tok, "***")   # never print the token
        print(f"BLOCKED(auth/push): {err}")
        return 3
    print(f"PUSHED {BRANCH} → {REMOTE}. {(r.stderr.strip()[-160:] or 'ok').replace(tok, '***')}")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if "--ack-poe-rotated" in args:
        st = _load_state()
        st["poe_cookie_rotated"] = True
        st["acked_at"] = datetime.now(timezone.utc).isoformat()
        _save_state(st)
        print("acknowledged: Poe cookie rotated — history gate cleared")
        return 0

    ok, problems = gate()
    st = _load_state()
    st["last_gate"] = {"ts": datetime.now(timezone.utc).isoformat(), "clean": ok,
                       "problems": problems}
    _save_state(st)

    if not ok:
        print("GATE BLOCKED — will not push:")
        for p in problems:
            print(f"  🔴 {p}")
        return 2
    print("GATE CLEAN ✅")
    if "--check" in args:
        return 0
    return push()


if __name__ == "__main__":
    sys.exit(main())
