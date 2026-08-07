#!/usr/bin/env python3
"""rt_dispatch.py — War Room seat dispatcher (routing corrected 2026-08-07).

Routing (Commander directive):
  AG    -> Gemini 3.6 Flash   via contact_ag.py (deepseek/AG side)
  CC    -> Claude Sonnet (MAX) local `claude -p` --model sonnet
  HAIKU -> Claude Haiku   (MAX) local `claude -p` --model haiku
  OPUS  -> Claude Opus    (MAX) local `claude -p` --model opus
Claude lanes hit the LOCAL Claude MAX bucket via the now-fixed headless path
(env-pop ANTHROPIC_API_KEY + CLAUDE_CODE_OAUTH_TOKEN + --mcp-config +
stdin=DEVNULL). NEVER routed to AG — that would overwhelm AG, and routing all
Claude to Haiku would crash Haiku.

Reports per-response token usage (estimate chars/4).
Usage:
  rt_dispatch.py AG   "<prompt>" [--deliverable <abs>]
  rt_dispatch.py CC   "<prompt>" [--deliverable <abs>]   # sonnet
  rt_dispatch.py HAIKU "<prompt>" [--deliverable <abs>]
  rt_dispatch.py OPUS "<prompt>" [--deliverable <abs>]
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLAUDE_BIN = Path.home() / ".local" / "bin" / "claude"
MCP_CONFIG = Path.home() / ".claude" / "mcp.json"

AG_MODEL = "gemini-3.6-flash-high"          # AG is Gemini 3.6 Flash ONLY
CLAUDE_LANES = {"CC": "sonnet", "HAIKU": "haiku", "OPUS": "opus"}

def est_tokens(text: str) -> int:
    return max(1, len(text) // 4)

def _claude_oauth_token() -> str:
    creds = json.loads((Path.home() / ".claude" / ".credentials.json").read_text())
    return creds["claudeAiOauth"]["accessToken"]

def run_local_claude(prompt: str, alias: str, timeout_s: int = 600) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)            # else it overrides OAuth -> hang
    env["CLAUDE_CODE_OAUTH_TOKEN"] = _claude_oauth_token()
    cmd = [str(CLAUDE_BIN), "-p", prompt, "--model", alias,
           "--output-format", "text", "--mcp-config", str(MCP_CONFIG)]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s,
                          env=env, stdin=subprocess.DEVNULL)

def run_ag(prompt: str, deliverable: str = "") -> subprocess.CompletedProcess:
    args = [sys.executable, str(REPO / "core" / "relay" / "contact_ag.py"),
            prompt, "--from", "OC", "--tag", "RT-DISPATCH", "--model", AG_MODEL]
    if deliverable:
        args += ["--deliverable", deliverable]
    return subprocess.run(args, capture_output=True, text=True, timeout=900)

def _maybe_write(out: str, deliverable: str):
    if deliverable and out.strip():
        Path(deliverable).write_text(out.strip() + "\n")

def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    lane = sys.argv[1].upper()
    prompt = sys.argv[2]
    deliv = sys.argv[sys.argv.index("--deliverable") + 1] if "--deliverable" in sys.argv else ""
    if lane == "AG":
        r = run_ag(prompt, deliv)
        label, model = "AG", AG_MODEL
    elif lane in CLAUDE_LANES:
        alias = CLAUDE_LANES[lane]
        r = run_local_claude(prompt, alias)
        label, model = f"{lane}({alias}/MAX)", f"claude:{alias}(MAX)"
        _maybe_write(r.stdout, deliv)
    else:
        print(f"unknown lane {lane!r}; use AG, CC, HAIKU, OPUS"); sys.exit(1)
    tin, tout = est_tokens(prompt), est_tokens(r.stdout or "")
    print(f"[TOKEN] lane={label} model={model} rc={r.returncode} in≈{tin} out≈{tout} total≈{tin+tout}")
    body = (r.stdout or "").strip() or (r.stderr or "").strip()
    print(body[-3000:])

if __name__ == "__main__":
    main()