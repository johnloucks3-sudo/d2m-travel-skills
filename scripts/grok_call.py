#!/usr/bin/env python3
"""
grok_call.py — dispatch a prompt to the Commander's real Grok account
(grok.com, personal subscription — Fast/Expert/Heavy/Build tiers on Grok 4.5)
via `bsk` (browser-skill), driving the Commander's own logged-in browser.

This is NOT the xAI API key (XAI_API_KEY, already wired into opencode.json's
"xai" provider) — that's a separate, metered, pay-per-token lane. This script
is the personal subscription account, integrated 2026-08-03, same spirit as
the Poe cookie-based integration: use the real account, not a fresh API key.

Requires: `bsk daemon` running with a browser connected (`bsk status` to
check), and the Commander already logged into grok.com in that browser —
this script does not and cannot handle login (human-only wall).

Usage:
  python3 scripts/grok_call.py --prompt "..." [--model fast|expert|heavy|auto]
"""
import argparse
import json
import re
import subprocess
import sys
import time

MODEL_LABELS = {
    "auto": "Auto",
    "fast": "Fast",
    "expert": "Expert",
    "heavy": "Heavy",
    "build": "Build",
}


def run_bsk(*args) -> str:
    result = subprocess.run(["bsk", *args], capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"bsk {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def find_ref(snapshot: str, text_match: str) -> str | None:
    """Find a snapshot ref (@eN) whose line contains text_match."""
    for line in snapshot.splitlines():
        if text_match.lower() in line.lower():
            m = re.search(r"@e\d+", line)
            if m:
                return m.group(0)
    return None


def pick_browser() -> str:
    """Return the first online browser instance id, or '' if none/one not needed."""
    try:
        out = run_bsk("browsers")
    except RuntimeError:
        return ""
    m = re.search(r"\b([0-9a-f]{8})\s+\S+\s+\S+", out, re.I)
    return m.group(1) if m else ""


def start_session(browser: str = "") -> str:
    cmd = ["session", "start"]
    if browser:
        cmd += ["--browser", browser]
    out = run_bsk(*cmd).strip()
    return out


def select_model(session: str, model_key: str) -> None:
    label = MODEL_LABELS.get(model_key, "Fast")
    snap = run_bsk("snapshot", "--session", session)
    model_btn = find_ref(snap, "Model select")
    if not model_btn:
        return  # already on desired model or button not found — proceed anyway
    run_bsk("click", "--session", session, model_btn)
    time.sleep(1)
    snap2 = run_bsk("snapshot", "--session", session)
    item = find_ref(snap2, label)
    if item:
        run_bsk("click", "--session", session, item)
    else:
        run_bsk("press", "--session", session, "Escape")
    time.sleep(1)


def send_prompt(session: str, prompt: str, timeout_s: int = 120) -> str:
    snap = run_bsk("snapshot", "--session", session)
    box = find_ref(snap, "Ask Grok anything")
    if not box:
        for attempt in range(3):
            time.sleep(3)
            snap = run_bsk("snapshot", "--session", session)
            box = find_ref(snap, "Ask Grok anything")
            if box:
                break
    if not box:
        raise RuntimeError("could not find Grok prompt textbox — is grok.com loaded and logged in?")
    run_bsk("fill", "--session", session, box, "--value", prompt)
    run_bsk("press", "--session", session, "Enter")

    # "Copy response" appears immediately, even mid-generation — not a valid
    # done signal (learned the hard way). "Stop model response" is present
    # ONLY while generating and is replaced by "Regenerate" once finished —
    # that transition is the real completion signal.
    deadline = time.time() + timeout_s
    last_snap = ""
    time.sleep(2)  # let generation actually start before the first check
    while time.time() < deadline:
        last_snap = run_bsk("snapshot", "--session", session)
        if "Stop model response" not in last_snap and "Regenerate" in last_snap:
            break
        time.sleep(2)

    # Extract the response block. Grok's DOM: the assistant's reply is one or
    # more `paragraph` blocks directly ABOVE "Copy response"; the user's own
    # prompt sits BELOW it. Status chips ("Working for…", "Connected to…",
    # "Browsed", "Analyzing…") can appear between response chunks — filter
    # them out so the returned text is the actual answer only.
    lines = last_snap.splitlines()
    try:
        idx = next(i for i, l in enumerate(lines) if "Copy response" in l)
    except StopIteration:
        return "[grok_call: no response detected within timeout]"
    response_lines = []
    for i in range(idx - 1, -1, -1):
        m = re.search(r'StaticText "(.*)"', lines[i])
        if m:
            text = m.group(1)
            if not re.match(r'^(Working for|Connected to|Browsed|Analyzing|Drafting|Reasoning|Thinking)', text.strip()):
                response_lines.insert(0, text)
        if "paragraph" in lines[i] and response_lines:
            break
    return " ".join(response_lines) if response_lines else "[grok_call: response text not parsed]"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--model", default="fast", choices=list(MODEL_LABELS.keys()))
    ap.add_argument("--session", help="reuse an existing bsk session id instead of starting a new one")
    ap.add_argument("--browser", help="target a specific bsk browser instance id (auto-picked if omitted)")
    args = ap.parse_args()

    prompt = args.prompt
    try:
        session = args.session or start_session(args.browser or pick_browser())
    except RuntimeError as e:
        print(f"ERROR starting bsk session: {e}\n"
              "If multiple browsers are online, pass --browser <instance-id> "
              "(run `bsk browsers` to list ids).", file=sys.stderr)
        return 1
    owned_session = args.session is None
    try:
        run_bsk("navigate", "--session", session, "https://grok.com")
        # SPA render race: grok.com needs more than 2s for the composer to
        # appear. Poll until the textbox shows (or timeout), so we never fire
        # a prompt into a half-rendered page.
        time.sleep(4)
        for attempt in range(3):
            snap = run_bsk("snapshot", "--session", session)
            if "Ask Grok anything" in snap:
                break
            run_bsk("navigate", "--session", session, "https://grok.com")
            time.sleep(4)
        else:
            raise RuntimeError("could not load Grok composer after retries — is grok.com reachable?")
        select_model(session, args.model)
        response = send_prompt(session, prompt)
        print(response)
        return 0
    finally:
        if owned_session:
            try:
                run_bsk("session", "stop", session)
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
