"""
core/relay/deepseek_claude_code.py — run the real `claude` CLI against DeepSeek
v4 instead of Anthropic, for cheap/high-volume work that doesn't need Sonnet
or Opus quality.

Why this exists (Commander tasking 2026-07-19, via reddit.com/r/ClaudeCode
running_claude_code_with_deepseek): DeepSeek now serves a native
Anthropic-Messages-compatible endpoint (api.deepseek.com/anthropic). Pointing
Claude Code's ANTHROPIC_BASE_URL/ANTHROPIC_AUTH_TOKEN at it swaps the backend
model while keeping the FULL Claude Code tool surface (Edit/Write/MultiEdit/
Agent/WebFetch/etc) — unlike the poe-deepseek subagent (Bash/Read/Glob/Grep
only) or OpenCode's deepseek-v4-flash-free (separate CLI entirely). This does
NOT touch the Claude MAX OAuth seat — it's a fully separate, API-key-billed
process, invoked only when explicitly dispatched via this module.

Verified 2026-07-19 21:xx MT: the routing mechanism itself works — Claude
Code accepts the DeepSeek endpoint and gets a real API-level response. Live
dispatch is currently BLOCKED: `API Error: 402 Insufficient Balance` on the
DEEPSEEK_API_KEY in .env. A 402 is a pre-flight rejection (DeepSeek never
processes the request), so testing this is free — the balance top-up itself
is a financial commitment and sits behind the Commander-only gate (THREE
GATES, CLAUDE.md). Nothing here spends money on its own.

Usage (from any Hale seat):
    from core.relay.deepseek_claude_code import dispatch_deepseek
    r = dispatch_deepseek("Summarize this log file: ...", deliverable_path="/abs/out.md")
    if r["ok"]:
        ...

CLI:
    python3 core/relay/deepseek_claude_code.py "<prompt>" [--deliverable /abs/path] [--model deepseek-v4-flash]
"""
from __future__ import annotations

import os
import re
import subprocess
from typing import Optional

REPO = "/home/john/Thunderbird"
ENV_FILE = os.path.join(REPO, ".env")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/anthropic"

# deepseek-v4-pro ~ Sonnet-class reasoning; deepseek-v4-flash ~ Haiku-class, cheaper/faster.
DEFAULT_MODEL = "deepseek-v4-pro"
FALLBACK_MODEL = "deepseek-v4-flash"

_MODEL_RE = re.compile(r"^[A-Za-z0-9.\-]+$")


def _validate_model(model: str) -> str:
    m = (model or "").strip()
    if not m or m.startswith("-") or not _MODEL_RE.match(m):
        raise ValueError(f"invalid model {model!r} — must match {_MODEL_RE.pattern}")
    return m


def _load_deepseek_key() -> str:
    """Read DEEPSEEK_API_KEY straight out of .env (no dotenv dependency in this repo)."""
    if not os.path.isfile(ENV_FILE):
        raise RuntimeError(f".env not found at {ENV_FILE}")
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line.startswith("DEEPSEEK_API_KEY="):
                key = line.split("=", 1)[1].strip()
                if key:
                    return key
    raise RuntimeError("DEEPSEEK_API_KEY not set in .env")


def dispatch_deepseek(
    prompt: str,
    *,
    deliverable_path: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    timeout: int = 300,
    add_dir: str = REPO,
) -> dict:
    """Run `claude -p <prompt>` with the backend swapped to DeepSeek v4.

    Synchronous, mirrors contact_ag.contact_ag()'s shape. Never raises on a
    DeepSeek/API failure — inspect `ok` and `stderr` (a 402 there means the
    account needs funding, not a code bug). Returns {ok, returncode, model,
    stdout, stderr, deliverable_path, deliverable_written}.
    """
    model = _validate_model(model)
    key = _load_deepseek_key()
    cmd = [
        "/home/john/.local/bin/claude", "-p", prompt,
        "--model", model,
    ]
    env = dict(os.environ)
    env.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
    env.pop("ANTHROPIC_API_KEY", None)
    env["ANTHROPIC_BASE_URL"] = DEEPSEEK_BASE_URL
    env["ANTHROPIC_AUTH_TOKEN"] = key
    env["ANTHROPIC_MODEL"] = model

    before = os.path.exists(deliverable_path) if deliverable_path else False
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              cwd=add_dir, env=env)
        rc, out, err = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as e:
        rc, out, err = 124, (e.stdout or ""), f"timeout after {timeout}s"
    except FileNotFoundError:
        rc, out, err = 127, "", "claude CLI not found on PATH"
    written = bool(deliverable_path) and os.path.exists(deliverable_path) and (
        not before or os.path.getsize(deliverable_path) > 0)
    return {
        "ok": rc == 0,
        "returncode": rc,
        "model": model,
        "stdout": out,
        "stderr": err,
        "deliverable_path": deliverable_path,
        "deliverable_written": written,
    }


if __name__ == "__main__":
    import argparse, json, sys
    ap = argparse.ArgumentParser(description="Run Claude Code against DeepSeek v4 instead of Anthropic.")
    ap.add_argument("prompt", help="Task prompt")
    ap.add_argument("--deliverable", help="ABSOLUTE path the run should write to")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--timeout", type=int, default=300)
    a = ap.parse_args()
    r = dispatch_deepseek(a.prompt, deliverable_path=a.deliverable, model=a.model, timeout=a.timeout)
    print(json.dumps({k: v for k, v in r.items() if k != "stdout"}, indent=2))
    print("\n--- stdout ---\n" + r["stdout"])
    sys.exit(0 if r["ok"] else 1)
