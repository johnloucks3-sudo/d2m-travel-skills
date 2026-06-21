#!/usr/bin/env python3
"""
Telegram async-delegation worker — MISSION-180.

Runs a FULL-MCP headless Hale agent in the background and delivers the result
back to the originating Telegram chat. Spawned detached by the gateway so the
message poll loop never blocks (this is the fix for the disabled in-loop
dispatcher: tool work happens off the hot path).

Flow:
  gateway detects a tool-needing request → sends instant "Wilco" ack →
  Popen(this script, start_new_session=True) → returns immediately.
  This worker then: wraps the task in Hale persona + live state, runs headless
  Claude with the full ~/.claude/mcp.json toolset (Gmail/Drive/TESS/wing tools),
  and posts the answer back to the chat via the bot API.

Usage:
  python3 telegram_async_agent.py --token <bot_token> --chat-id <id> \
      --task "<commander request>" [--model claude-sonnet-4-6]
"""

import argparse
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def tg_send(token: str, chat_id: str, text: str) -> None:
    """Send plain-text message to a Telegram chat, chunked to Telegram's 4096 limit.
    Plain text (no parse_mode) so arbitrary agent output never trips HTML parsing."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    if not text:
        text = "🦅 Agent finished but produced no output."
    for i in range(0, len(text), 3900):
        chunk = text[i:i + 3900]
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": chunk}).encode()
        try:
            urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=25)
        except Exception as e:  # delivery failure must not crash the worker
            print(f"[tg_send] failed: {e}", flush=True)


def main() -> int:
    p = argparse.ArgumentParser()
    # Token comes from the env (TG_AGENT_BOT_TOKEN), NOT argv — argv is world-readable
    # in ps/proc (MISSION-258). --token kept only as a deprecated fallback.
    p.add_argument("--token", default=None, help="DEPRECATED — use TG_AGENT_BOT_TOKEN env")
    p.add_argument("--chat-id", required=True, dest="chat_id")
    p.add_argument("--task", required=True)
    p.add_argument("--model", default="claude-sonnet-4-6")
    args = p.parse_args()

    args.token = os.environ.get("TG_AGENT_BOT_TOKEN") or args.token
    if not args.token:
        print("[agent] no bot token (set TG_AGENT_BOT_TOKEN env)", flush=True)
        return 1

    try:
        from core.ai_infra.hale_persona_loader import wrap_with_persona, load_state_summary
        from core.ai_infra.thunderbird_headless_spawn import spawn_headless_claude
    except Exception as e:
        tg_send(args.token, args.chat_id, f"🦅 Agent init failed: {e}")
        return 1

    # Build the agent prompt: full persona (gates + brevity), live state, the task,
    # and a tool-use directive. Compact persona keeps the prompt lean; the agent has
    # the full MCP toolset to actually do the work.
    state = load_state_summary()
    state_block = f"{state}\n\n" if state else ""
    task_prompt = (
        f"{state_block}Commander sent this via Telegram and it needs real tools "
        f"(you are in full-MCP agent mode — Gmail, Drive, TESS, wing tools all available):\n\n"
        f"\"{args.task}\"\n\n"
        f"Do the actual work with your tools, then reply with a tight, Telegram-ready answer "
        f"(plain text, scannable, under ~1500 chars). Lead with Wilco/Roger/Done and restate "
        f"what you did. If a client/figure isn't in a primary source, say so — never substitute."
    )
    prompt = wrap_with_persona(task_prompt, channel="telegram", compact=True)

    out_path = ROOT / "output" / f"tg_agent_{os.getpid()}.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        result = spawn_headless_claude(
            prompt=prompt,
            output_file=str(out_path),
            model=args.model,
            task_name="tg_async_agent",
            background=False,          # block inside this already-detached worker
            timeout=600,               # 10 min ceiling for tool work
            mcp_config="/home/john/.claude/mcp.json",   # full toolset — parity with Claude Code
            policy_pre_cleared=True,   # gateway already checked raw task before persona-wrap
        )
    except Exception as e:
        tg_send(args.token, args.chat_id, f"🦅 Agent error: {e}")
        return 1

    # Resolve the answer text: prefer the written output file, fall back to the
    # return dict's common result keys.
    text = ""
    if out_path.exists():
        text = out_path.read_text(encoding="utf-8", errors="replace").strip()
    if not text and isinstance(result, dict):
        text = (result.get("output") or result.get("result") or result.get("stdout") or "").strip()
    if not text:
        status = result.get("status") if isinstance(result, dict) else "unknown"
        text = f"🦅 Agent finished (status: {status}) but produced no readable output — check logs."

    tg_send(args.token, args.chat_id, text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
