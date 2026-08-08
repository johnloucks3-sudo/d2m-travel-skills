#!/usr/bin/env python3
"""rt_dispatch.py — War Room seat dispatcher (routing corrected 2026-08-07;
OC lane added 2026-08-08).

Routing (Commander directive):
  AG    -> Gemini 3.6 Flash   via contact_ag.py (deepseek/AG side)
  CC    -> Claude Sonnet (MAX) local `claude -p` --model sonnet
  HAIKU -> Claude Haiku   (MAX) local `claude -p` --model haiku
  OPUS  -> Claude Opus    (MAX) local `claude -p` --model opus
  OC    -> DeepSeek v4 Zen FREE, direct `opencode run` (see below)
Claude lanes hit the LOCAL Claude MAX bucket via the now-fixed headless path
(env-pop ANTHROPIC_API_KEY + CLAUDE_CODE_OAUTH_TOKEN + --mcp-config +
stdin=DEVNULL). NEVER routed to AG — that would overwhelm AG, and routing all
Claude to Haiku would crash Haiku.

OC LANE — deliberately NOT routed through core.relay.dispatch_oc/oc_worker.py's
brain_bridge queue. That path wraps every task in a generic "write your result
summary + end with TASK_COMPLETE" prompt tuned for autonomous CI-remediation
work; for a design/build round it competes with a task-specific deliverable
path and lets the model satisfy the wrapper's own instruction instead of doing
the real work (confirmed live 2026-08-08, see instructor-mode skill). This
lane calls `opencode run` directly instead — synchronous, no polling needed.

Confirmed live (2026-08-08): `opencode run` without `--auto` auto-rejects ALL
access (read AND write) to paths outside this repo — silently, no error
surfaced to the model in a way that stops the run. Any OC-lane prompt that
needs content from outside the repo must have that content embedded directly
by the caller (read it yourself, paste it in) — never assume OC can read or
write an external path. See the instructor-mode skill for the full pattern.

Reports per-response token usage (estimate chars/4).
Usage:
  rt_dispatch.py AG   "<prompt>" [--deliverable <abs>]
  rt_dispatch.py CC   "<prompt>" [--deliverable <abs>]   # sonnet
  rt_dispatch.py HAIKU "<prompt>" [--deliverable <abs>]
  rt_dispatch.py OPUS "<prompt>" [--deliverable <abs>]
  rt_dispatch.py OC   "<prompt>" [--deliverable <abs>]
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLAUDE_BIN = Path.home() / ".local" / "bin" / "claude"
MCP_CONFIG = Path.home() / ".claude" / "mcp.json"
OPENCODE_BIN = Path.home() / ".opencode" / "bin" / "opencode"

AG_MODEL = "gemini-3.6-flash-high"          # AG is Gemini 3.6 Flash ONLY
OC_MODEL = "opencode/deepseek-v4-flash-free"
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

def run_oc(prompt: str, timeout_s: int = 180) -> subprocess.CompletedProcess:
    """Direct opencode dispatch — see module docstring for why this bypasses
    oc_worker.py's queue. Gated by oc_hygiene.before_dispatch() (sweeps stale
    runs, waits for a concurrency slot) so this lane doesn't pile onto an
    already-saturated one and hang for its whole timeout."""
    sys.path.insert(0, str(REPO))
    from core.relay.oc_hygiene import before_dispatch
    gate = before_dispatch()
    if not gate["ok"]:
        return subprocess.CompletedProcess(
            args=["opencode", "run"], returncode=429, stdout="",
            stderr=f"OC lane deferred: {gate['reason']}",
        )
    return subprocess.run(
        [str(OPENCODE_BIN), "run", "--model", OC_MODEL, prompt],
        capture_output=True, text=True, timeout=timeout_s,
        cwd=str(REPO), start_new_session=True,
    )

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
    elif lane == "OC":
        r = run_oc(prompt)
        label, model = "OC", OC_MODEL
        _maybe_write(r.stdout, deliv)
    elif lane in CLAUDE_LANES:
        alias = CLAUDE_LANES[lane]
        r = run_local_claude(prompt, alias)
        label, model = f"{lane}({alias}/MAX)", f"claude:{alias}(MAX)"
        _maybe_write(r.stdout, deliv)
    else:
        print(f"unknown lane {lane!r}; use AG, CC, HAIKU, OPUS, OC"); sys.exit(1)
    tin, tout = est_tokens(prompt), est_tokens(r.stdout or "")
    print(f"[TOKEN] lane={label} model={model} rc={r.returncode} in≈{tin} out≈{tout} total≈{tin+tout}")
    body = (r.stdout or "").strip() or (r.stderr or "").strip()
    print(body[-3000:])

if __name__ == "__main__":
    main()