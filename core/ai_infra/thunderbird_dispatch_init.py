#!/usr/bin/env python3
"""
Thunderbird Dispatch Init — Bulletproof Bootstrap
==================================================
WHAT IT DOES
------------
Single-source-of-truth bootstrap for any process (subprocess, daemon, agent)
that needs to spawn or interact with headless Claude. Loads PYTHONPATH from
deploy/thunderbird_pythonpath.env, injects core/* paths into sys.path, loads
the OAuth token from ~/.claude/.credentials.json, and verifies critical
preconditions BEFORE any module-level imports run.
WHY IT'S NECESSARY
------------------
The original failure mode: a subprocess (or daemon spawned via systemd) starts
without PYTHONPATH set, so `import thunderbird_gmail` fails with ModuleNotFoundError.
The error surfaces as a generic ImportError mid-execution, after side effects
have run, with no breadcrumbs. By the time you see it, the dispatch has already
left a half-written log and a confused user.
This module fixes that root cause by:
  1. Reading deploy/thunderbird_pythonpath.env (the canonical path manifest)
  2. Splicing every entry into both os.environ['PYTHONPATH'] AND sys.path
  3. Doing it idempotently — multiple init calls do not double-inject
  4. Failing FAST and LOUDLY with remediation if anything is broken
  5. Logging every step with timestamps for forensic debugging
HOW IT PREVENTS THE PYTHONPATH BUG
----------------------------------
Every code path that ever touches headless dispatch begins with:
    from thunderbird_dispatch_init import ensure_initialized
    ensure_initialized()
After that call, sys.path is guaranteed to include every core/* directory,
os.environ['PYTHONPATH'] is set so child subprocesses inherit it, and the
OAuth token is verified. If any of that fails, RuntimeError with a specific
remediation step is raised — never a silent ModuleNotFoundError later.
HOW TO USE IT
-------------
At the very top of any dispatch module (BEFORE any thunderbird_* imports):
    import sys
    sys.path.insert(0, "/home/john/Thunderbird/core/ai_infra")
    from thunderbird_dispatch_init import ensure_initialized
    state = ensure_initialized()  # idempotent
    # Now safe to import anything from core/
For subprocess spawns, pass `state.env` as the `env=` argument to Popen so
the child inherits PYTHONPATH and CLAUDE_CODE_OAUTH_TOKEN.
"""
from __future__ import annotations
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
PYTHONPATH_ENV_FILE = THUNDERBIRD_ROOT / "deploy" / "thunderbird_pythonpath.env"
CREDENTIALS_FILE = Path.home() / ".claude" / ".credentials.json"
CLAUDE_BINARY = Path("/home/john/.local/bin/claude")
INIT_LOG = THUNDERBIRD_ROOT / "logs" / "init_dispatch.log"
# Hard-coded fallback paths — used only if deploy/.env file is missing.
# Kept in sync with deploy/thunderbird_pythonpath.env. These are the
# directories that MUST be on sys.path for headless dispatch to work.
FALLBACK_PATHS: List[str] = [
    "/home/john/Thunderbird",
    "/home/john/Thunderbird/api",
    "/home/john/Thunderbird/OpsCenter",
    "/home/john/Thunderbird/agents",
    "/home/john/Thunderbird/business",
    "/home/john/Thunderbird/comms",
    "/home/john/Thunderbird/intel",
    "/home/john/Thunderbird/itinerary",
    "/home/john/Thunderbird/media",
    "/home/john/Thunderbird/ops",
    "/home/john/Thunderbird/core/ai_infra",
    "/home/john/Thunderbird/core/booking",
    "/home/john/Thunderbird/core/client",
    "/home/john/Thunderbird/core/communication",
    "/home/john/Thunderbird/core/crewai",
    "/home/john/Thunderbird/core/email",
    "/home/john/Thunderbird/core/intel",
    "/home/john/Thunderbird/core/learning",
    "/home/john/Thunderbird/core/mcp",
    "/home/john/Thunderbird/core/ops",
    "/home/john/Thunderbird/core/scheduling",
    "/home/john/Thunderbird/core/travel",
    "/home/john/Thunderbird/core/watchtower",
]
# Idempotency guard. Any code path that imports this module multiple times
# only pays the init cost once; subsequent calls return the cached state.
_INIT_STATE: Optional["DispatchState"] = None
# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------
@dataclass
class DispatchState:
    """Result of ensure_initialized(). Pass `env` to subprocess spawns."""
    paths_loaded: List[str] = field(default_factory=list)
    pythonpath: str = ""
    env: Dict[str, str] = field(default_factory=dict)
    oauth_token_loaded: bool = False
    credentials_path: str = str(CREDENTIALS_FILE)
    claude_binary: str = str(CLAUDE_BINARY)
    initialized_at: str = ""
    source: str = ""  # "deploy_env_file" or "fallback_constants"
# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def _ensure_logger() -> logging.Logger:
    """Configure the dispatch init logger. Idempotent."""
    logger = logging.getLogger("thunderbird_dispatch_init")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    INIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(INIT_LOG, mode="a")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(handler)
    logger.propagate = False
    return logger
# ---------------------------------------------------------------------------
# Path loading
# ---------------------------------------------------------------------------
def _read_pythonpath_env_file() -> Optional[List[str]]:
    """
    Parse deploy/thunderbird_pythonpath.env. Returns the list of paths or None
    if the file is missing or malformed. Never raises.
    """
    if not PYTHONPATH_ENV_FILE.exists():
        return None
    try:
        text = PYTHONPATH_ENV_FILE.read_text().strip()
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("PYTHONPATH="):
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                paths = [p.strip() for p in value.split(":") if p.strip()]
                return paths if paths else None
        return None
    except Exception:
        return None
def _inject_paths(paths: List[str], logger: logging.Logger) -> List[str]:
    """
    Inject paths into sys.path (front) and os.environ['PYTHONPATH'].
    Idempotent: skips paths already present.
    Returns the actual paths injected (not the ones already there).
    """
    actually_added: List[str] = []
    for p in paths:
        if not Path(p).exists():
            logger.warning(f"path does not exist on disk, skipping: {p}")
            continue
        if p not in sys.path:
            sys.path.insert(0, p)
            actually_added.append(p)
    # Build PYTHONPATH preserving existing entries (so children inherit
    # anything the parent already had set).
    existing_pp = os.environ.get("PYTHONPATH", "")
    existing_entries = [e for e in existing_pp.split(os.pathsep) if e]
    merged: List[str] = []
    seen = set()
    for p in paths + existing_entries:
        if p and p not in seen:
            merged.append(p)
            seen.add(p)
    os.environ["PYTHONPATH"] = os.pathsep.join(merged)
    return actually_added
# ---------------------------------------------------------------------------
# OAuth token
# ---------------------------------------------------------------------------
def _load_oauth_token(logger: logging.Logger) -> str:
    """
    Read ~/.claude/.credentials.json and return the access token.
    Raises RuntimeError with a remediation step on any failure.
    """
    if not CREDENTIALS_FILE.exists():
        raise RuntimeError(
            f"OAuth credentials file missing: {CREDENTIALS_FILE}\n"
            f"REMEDIATION: open Claude Desktop and sign in. The credentials "
            f"file will be (re)created automatically."
        )
    try:
        creds = json.loads(CREDENTIALS_FILE.read_text())
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"OAuth credentials file is corrupted JSON: {e}\n"
            f"REMEDIATION: rm {CREDENTIALS_FILE} && reauth in Claude Desktop."
        ) from e
    token = creds.get("claudeAiOauth", {}).get("accessToken")
    if not token:
        raise RuntimeError(
            f"OAuth credentials file has no 'claudeAiOauth.accessToken'.\n"
            f"REMEDIATION: open Claude Desktop and sign in to refresh the token."
        )
    return token
# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def ensure_initialized(force: bool = False) -> DispatchState:
    """
    Bulletproof bootstrap. Call at the top of every dispatch script.
    Idempotent: subsequent calls return the cached state without re-injecting.
    Pass force=True to re-run from scratch (rare; mostly used by tests).
    Raises RuntimeError with a specific REMEDIATION line if any precondition
    fails. Never returns a partially-initialized state.
    """
    global _INIT_STATE
    logger = _ensure_logger()
    if _INIT_STATE is not None and not force:
        return _INIT_STATE
    logger.info("=" * 60)
    logger.info("ensure_initialized: starting bootstrap")
    # ----- Step 1: Python version sanity -----
    if sys.version_info < (3, 9):
        raise RuntimeError(
            f"Python 3.9+ required, got {sys.version_info.major}."
            f"{sys.version_info.minor}\n"
            f"REMEDIATION: invoke this script via "
            f"/home/john/Thunderbird/.venv/bin/python"
        )
    logger.info(f"python version OK: {sys.version.split()[0]}")
    # ----- Step 2: Resolve paths (env file first, fallback constants second) -----
    paths_from_file = _read_pythonpath_env_file()
    if paths_from_file:
        paths = paths_from_file
        source = "deploy_env_file"
        logger.info(f"loaded {len(paths)} paths from {PYTHONPATH_ENV_FILE}")
    else:
        paths = FALLBACK_PATHS
        source = "fallback_constants"
        logger.warning(
            f"deploy/thunderbird_pythonpath.env missing or empty, "
            f"using {len(paths)} hard-coded fallback paths"
        )
    # ----- Step 3: Inject into sys.path + os.environ -----
    actually_added = _inject_paths(paths, logger)
    logger.info(f"injected {len(actually_added)} new paths into sys.path "
                f"(rest already present)")
    # ----- Step 4: Verify Claude binary exists -----
    if not CLAUDE_BINARY.exists():
        raise RuntimeError(
            f"Claude binary not found at {CLAUDE_BINARY}\n"
            f"REMEDIATION: install Claude CLI — "
            f"curl -fsSL https://claude.ai/install.sh | bash"
        )
    if not os.access(CLAUDE_BINARY, os.X_OK):
        raise RuntimeError(
            f"Claude binary exists but is not executable: {CLAUDE_BINARY}\n"
            f"REMEDIATION: chmod +x {CLAUDE_BINARY}"
        )
    logger.info(f"claude binary OK: {CLAUDE_BINARY}")
    # ----- Step 5: Load OAuth token -----
    token = _load_oauth_token(logger)
    logger.info(f"oauth token loaded: {len(token)} chars")
    # ----- Step 6: Build child-process env (for subprocess spawns) -----
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)  # force OAuth path, not API key
    env["CLAUDE_CODE_OAUTH_TOKEN"] = token
    env["PYTHONPATH"] = os.environ["PYTHONPATH"]
    # ----- Done -----
    state = DispatchState(
        paths_loaded=paths,
        pythonpath=os.environ["PYTHONPATH"],
        env=env,
        oauth_token_loaded=True,
        credentials_path=str(CREDENTIALS_FILE),
        claude_binary=str(CLAUDE_BINARY),
        initialized_at=datetime.now().isoformat(timespec="seconds"),
        source=source,
    )
    _INIT_STATE = state
    logger.info(f"bootstrap complete (source={source})")
    return state
def get_state() -> Optional[DispatchState]:
    """Return cached state, or None if ensure_initialized() has not run yet."""
    return _INIT_STATE
def reset_for_tests() -> None:
    """Clear the idempotency cache. Tests only — do not call in production."""
    global _INIT_STATE
    _INIT_STATE = None
# ---------------------------------------------------------------------------
# CLI for manual smoke test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        state = ensure_initialized()
    except RuntimeError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"OK initialized at {state.initialized_at}")
    print(f"   source: {state.source}")
    print(f"   paths loaded: {len(state.paths_loaded)}")
    print(f"   oauth token: loaded={state.oauth_token_loaded}")
    print(f"   PYTHONPATH ({len(state.pythonpath)} chars): "
          f"{state.pythonpath[:120]}...")
    sys.exit(0)

