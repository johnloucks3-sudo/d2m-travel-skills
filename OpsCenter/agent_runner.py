"""
agent_runner.py — Claude and OpenCode CLI execution wrappers
============================================================
Routes tasks to the correct agent and executes them headlessly.
Returns (success: bool, output: str).
"""

import json
import logging
import os
import subprocess
from pathlib import Path

import sys

log = logging.getLogger(__name__)

WORK_DIR = Path("/home/john/Thunderbird")
sys.path.insert(0, str(WORK_DIR))
MCP_BRIDGE = WORK_DIR / "OpsCenter/mcp_bridge.sh"

# ── Routing table ─────────────────────────────────────────────────────────────
# task_type → agent.  All tasks route to "hale" (Claude) or "opencode" or "api".
ROUTE_TABLE: dict[str, str] = {
    "commander_message": "hale",
    "client_email":      "hale",
    "draft_approval":    "hale",
    "send_draft":        "hale",
    "fpd_alert":         "hale",
    "dossier_check":     "hale",
    "commission_audit":  "hale",
    # OpenCode handles async intel (Gemini 3.1 Flash-Lite via OpenRouter)
    "intel_sweep":       "opencode",
    "world_intel":       "opencode",
    "innovation_scan":   "opencode",
    "ship_intel":        "opencode",
    "morning_briefing":  "opencode",
    "sentinel_sweep":    "opencode",
    "research":          "opencode",
    # Direct API calls — no LLM spin-up needed
    "api_call":          "api",
}


def route(task: dict) -> str:
    """Return 'hale', 'opencode', or 'api' for this task."""
    assigned = task.get("assigned_to", "auto").lower()
    if assigned in ("hale", "claude", "cos", "a3", "dani"):
        return "hale"
    if assigned in ("opencode", "gemini", "a2", "wraith", "research"):
        return "opencode"
    if assigned == "api" or task.get("task_type") == "api_call":
        return "api"
    # auto-route by task_type
    return ROUTE_TABLE.get(task.get("task_type", "general"), "hale")


# ── Agent runners ─────────────────────────────────────────────────────────────

def _base_env() -> dict:
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)   # force Max OAuth for Claude
    env["PYTHONPATH"] = str(WORK_DIR)
    env["HOME"] = "/home/john"
    env["PATH"] = (
        "/home/john/.local/bin"
        ":/home/john/.opencode/bin"
        ":/home/john/.local/share/claude/versions/current/bin"
        ":/usr/local/bin:/usr/bin:/bin"
    )
    return env


def run_claude(
    content: str,
    timeout: int = 300,
    model: str = "claude-sonnet-4-6",
) -> tuple[bool, str]:
    """
    Run Claude Code CLI in headless mode.
    Uses Max plan OAuth — zero API cost.

    The model is pinned explicitly. Headless dispatch MUST NOT inherit the
    interactive `/model` default — that made brain selection non-deterministic
    (brain3 "Opus" silently ran on whatever the CLI default happened to be).
    Pass a full model ID (claude-sonnet-4-6 | claude-opus-4-8 |
    claude-haiku-4-5-20251001).
    """
    env = _base_env()
    try:
        result = subprocess.run(
            ["claude", "--model", model, "--print", content],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(WORK_DIR),
            env=env,
        )
        output = result.stdout.strip()
        error  = result.stderr.strip()
        if result.returncode != 0 and not output:
            return False, error or f"claude exited {result.returncode}"
        return True, output or "(done, no output)"
    except subprocess.TimeoutExpired:
        return False, f"claude timeout after {timeout}s"
    except FileNotFoundError:
        return False, "claude CLI not found — check PATH"
    except Exception as e:
        return False, str(e)


def run_opencode(content: str, timeout: int = 300) -> tuple[bool, str]:
    """
    Run OpenCode in headless mode using Gemini 3.1 Flash-Lite via OpenRouter.
    Primary async intel/research node — low cost.
    """
    env = _base_env()
    try:
        result = subprocess.run(
            [
                "opencode", "run",
                "-m", "opencode/big-pickle",
                "--dir", str(WORK_DIR),
                "--dangerously-skip-permissions",
                content,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(WORK_DIR),
            env=env,
        )
        output = result.stdout.strip()
        error  = result.stderr.strip()
        if result.returncode != 0 and not output:
            return False, error or f"opencode exited {result.returncode}"
        return True, output or "(done, no output)"
    except subprocess.TimeoutExpired:
        return False, f"opencode timeout after {timeout}s"
    except FileNotFoundError:
        return False, "opencode CLI not found — check PATH or run: export PATH=/home/john/.opencode/bin:$PATH"
    except Exception as e:
        return False, str(e)


def run_mcp_tool(tool_name: str, args_json: str = "{}") -> tuple[bool, str]:
    """
    Call an MCP tool directly via mcp_bridge.sh — zero LLM cost.
    Use for mechanical tasks (health checks, calendar sync, etc.)
    """
    if not MCP_BRIDGE.exists():
        return False, f"mcp_bridge.sh not found at {MCP_BRIDGE}"
    try:
        result = subprocess.run(
            ["bash", str(MCP_BRIDGE), tool_name, args_json],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(WORK_DIR),
            env=_base_env(),
        )
        return result.returncode == 0, result.stdout.strip() or result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, f"mcp_bridge timeout for {tool_name}"
    except Exception as e:
        return False, str(e)


# ── Direct API execution (no LLM) ─────────────────────────────────────────────

def run_api_direct(task: dict) -> tuple[bool, str]:
    """
    Execute a direct API call using api_registry.py — zero LLM cost.

    Task fields used:
      api_target  (str)  — registry key, e.g. "amadeus", "serper", "n8n"
      api_method  (str)  — hint for the request type, e.g. "search_flights"
      api_params  (str)  — JSON string of request parameters
      content     (str)  — fallback prompt / description if no structured params

    Routes:
      - APIs with mcp_tool → runs via claude --print with tool invocation prompt
      - APIs with mcp_url  → POSTs to n8n/MCP endpoint directly
      - All others         → falls back to run_claude with a structured prompt
    """
    try:
        from OpsCenter.api_registry import get_api
    except ImportError:
        return False, "api_registry not found — check PYTHONPATH"

    api_name = task.get("api_target", "")
    api_cfg  = get_api(api_name)

    if not api_cfg:
        return False, f"Unknown api_target: '{api_name}'. Check api_registry.py."

    params_raw = task.get("api_params") or "{}"
    try:
        params = json.loads(params_raw)
    except json.JSONDecodeError:
        params = {}

    method    = task.get("api_method", "")
    content   = task.get("content", "")
    mcp_tool  = api_cfg.get("mcp_tool")
    mcp_url   = api_cfg.get("mcp_url")

    log.info("direct_api target=%s method=%s mcp_tool=%s", api_name, method, mcp_tool)

    # Path 1: n8n / MCP HTTP endpoint — call it directly
    if mcp_url and method:
        try:
            import requests  # type: ignore
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": method, "arguments": params},
            }
            resp = requests.post(
                mcp_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            if resp.ok:
                return True, resp.text[:4096]
            return False, f"HTTP {resp.status_code}: {resp.text[:512]}"
        except Exception as e:
            return False, f"MCP HTTP call failed: {e}"

    # Path 2: MCP tool available — delegate to Claude which has full MCP access
    if mcp_tool:
        prompt = (
            f"Use the MCP tool `{mcp_tool}` to {method or content}.\n"
            f"Parameters: {json.dumps(params) if params else 'use your judgment'}.\n"
            f"Return the raw result."
        )
        return run_claude(prompt, timeout=int(task.get("timeout_sec", 120)))

    # Path 3: No MCP tool — build a structured prompt for Claude
    prompt = (
        f"Call the {api_cfg['label']} API ({api_cfg['base_url']}).\n"
        f"Method: {method or 'best judgment'}\n"
        f"Params: {json.dumps(params)}\n"
        f"Task: {content}\n"
        f"Auth env var: {api_cfg['env_key']}\n"
        f"Return the result."
    )
    return run_claude(prompt, timeout=int(task.get("timeout_sec", 120)))


# ── Public entry point ────────────────────────────────────────────────────────

def execute_task(task: dict) -> tuple[bool, str]:
    """Route and execute a task. Returns (success, result_or_error)."""
    agent   = route(task)
    content = task["content"]
    timeout = int(task.get("timeout_sec", 300))

    log.info("task=%s agent=%s type=%s", task["id"], agent, task.get("task_type"))

    if agent == "api":
        return run_api_direct(task)
    elif agent == "opencode":
        return run_opencode(content, timeout)
    else:
        return run_claude(content, timeout)
