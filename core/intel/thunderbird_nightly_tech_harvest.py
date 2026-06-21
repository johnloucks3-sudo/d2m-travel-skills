#!/usr/bin/env python3
"""
THUNDERBIRD NIGHTLY TECH HARVEST — Document Sculptor Track
D2M Dreams2Memories Travel, LLC
Version: 1.0.0 · 2026-03-23

Runs nightly at 20:13 MT. Searches for zero-cost AI/writing tools that
reduce Commander editing burden on tone, format, focus, attitude.

Cron: 13 20 * * * /usr/bin/python3 /home/john/Thunderbird/thunderbird_nightly_tech_harvest.py
"""

import json
import os
import subprocess
from pathlib import Path
from datetime import datetime, date

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
LOGS_DIR        = THUNDERBIRD_DIR / "logs"
DATA_DIR        = THUNDERBIRD_DIR / "data"
HARVEST_LOG     = LOGS_DIR / "tech_harvest.log"
HARVEST_DB      = DATA_DIR / "discovered_tools.json"

SEARCH_QUERIES = [
    "free AI email rewriter tone format 2026",
    "zero cost AI writing style transfer open source",
    "AI draft polish voice matching no subscription 2026",
    "open source LLM writing coach tone correction free",
    "free tier AI correspondence editing business email 2026",
]

EVAL_CRITERIA = """
Score each tool 0-10 against D2M needs:
  1. ZERO COST — free tier, open source, or in existing subscriptions (Max/Google)
  2. TONE MATCHING — learns / applies a specific communication style
  3. FORMAT CONTROL — enforces structure, length, sign-off rules
  4. AUTOMATION — callable from Python / REST API
  5. PRIVACY — self-hostable or safe for business correspondence data
  6. EMAIL INTEGRATION — Gmail or standalone

Flag:
  INTEGRATE_NOW  if score >= 7
  MONITOR        if 4-6
  SKIP           if < 4
"""


def load_known_tools() -> set:
    if HARVEST_DB.exists():
        try:
            with open(HARVEST_DB) as f:
                data = json.load(f)
            return {t.get("name", "").lower() for t in data}
        except Exception:
            pass
    return set()


def save_tools(tools: list):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    existing = []
    if HARVEST_DB.exists():
        try:
            with open(HARVEST_DB) as f:
                existing = json.load(f)
        except Exception:
            pass
    today = date.today().isoformat()
    for t in tools:
        existing.append({**t, "discovered": today})
    with open(HARVEST_DB, "w") as f:
        json.dump(existing, f, indent=2)


def run_harvest() -> dict:
    today = date.today().strftime("%B %d, %Y")

    prompt = f"""Today is {today}. You are the D2M Nightly Tech Harvest Agent.

MISSION: Find zero-cost AI / writing tools that could reduce travel
advisor John Loucks' time spent editing correspondence for tone, format,
focus, and attitude of client emails and proposals.

SEARCH the following queries using your web search capability:
{chr(10).join(f'  • {q}' for q in SEARCH_QUERIES)}

EVALUATION CRITERIA:
{EVAL_CRITERIA}

For each promising tool (max 5), return:
{{
  "date": "{today}",
  "tools": [
    {{
      "name":             "tool name",
      "url":              "official URL",
      "cost":             "exact cost / free tier limits",
      "capability":       "one sentence what it does",
      "d2m_score":        0,
      "integration_path": "how to wire into Python pipeline",
      "flag":             "INTEGRATE_NOW | MONITOR | SKIP"
    }}
  ],
  "top_find": "name of best tool found today or 'none'",
  "summary":  "one sentence for Commander"
}}

Return ONLY zero-cost options. If nothing new found, return tools: [] with honest summary."""

    try:
        result = subprocess.run(
            ["claude", "--print", "--output-format", "json", "-p", prompt],
            capture_output=True, text=True, timeout=120,
            env={**os.environ, "ANTHROPIC_LOG": "error"},
        )
        out = result.stdout.strip()
        # `--output-format json` wraps the agent reply in an envelope:
        #   {"type":"result","result":"<agent text>", ...}
        # The old code json.loads'd the whole envelope and looked for "tools" on
        # it — which never exists — so every run reported 0 tools. Unwrap first.
        inner = out
        try:
            env = json.loads(out)
            if isinstance(env, dict) and "result" in env:
                inner = env["result"]
        except Exception:
            pass
        start = inner.find("{")
        end   = inner.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(inner[start:end])
        return {"tools": [], "summary": "Harvest returned no structured data."}
    except subprocess.TimeoutExpired:
        return {"tools": [], "summary": "Harvest timed out (120s)."}
    except Exception as e:
        return {"tools": [], "summary": f"Harvest error: {e}"}


def build_telegram_message(harvest: dict) -> str:
    tools     = harvest.get("tools", [])
    summary   = harvest.get("summary", "No findings.")
    top       = harvest.get("top_find", "")
    today_str = date.today().strftime("%d %b %Y")

    integrate = [t for t in tools if t.get("flag") == "INTEGRATE_NOW"]
    monitor   = [t for t in tools if t.get("flag") == "MONITOR"]

    msg = f"*THUNDERBIRD C2 · TECH HARVEST*\n*{today_str} · 20:13 MT*\n\n---\n\n"
    msg += "*ZERO-COST DOC TOOLS — NIGHTLY SCAN*\n\n"

    if not tools:
        msg += f"Nothing new to report.\n_{summary}_"
        return msg

    if integrate:
        msg += "*🎯 INTEGRATE NOW:*\n"
        for t in integrate:
            msg += f"• *{t['name']}* — score {t['d2m_score']}/10\n"
            msg += f"  {t['capability']}\n"
            msg += f"  Cost: {t['cost']}\n"
            msg += f"  Wire-in: {t['integration_path']}\n"
            msg += f"  URL: {t['url']}\n\n"

    if monitor:
        msg += "*📡 MONITOR:*\n"
        for t in monitor:
            msg += f"• *{t['name']}* ({t['d2m_score']}/10) — {t['capability']}\n"

    msg += f"\n*Summary:* {summary}"
    if top and top.lower() != "none":
        msg += f"\n*Top find:* {top}"

    return msg


def send_telegram(msg: str) -> bool:
    """Send via local Thunderbird API. Queue if API down."""
    try:
        r = subprocess.run(
            ["curl", "-s", "-X", "POST",
             "http://localhost:8766/telegram/send",
             "-H", "Content-Type: application/json",
             "-d", json.dumps({"message": msg, "parse_mode": "Markdown"})],
            capture_output=True, text=True, timeout=10,
        )
        return r.returncode == 0 and '"ok":true' in r.stdout
    except Exception:
        pass

    # Fallback — write to pending queue
    pending = DATA_DIR / "pending_telegram_messages.json"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    msgs = []
    if pending.exists():
        try:
            with open(pending) as f:
                msgs = json.load(f)
        except Exception:
            pass
    msgs.append({"message": msg, "ts": datetime.now().isoformat()})
    with open(pending, "w") as f:
        json.dump(msgs, f, indent=2)
    return False


def _log(harvest: dict, sent: bool):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts":             datetime.now().isoformat(),
        "tools_found":    len(harvest.get("tools", [])),
        "integrate_now":  sum(1 for t in harvest.get("tools", []) if t.get("flag") == "INTEGRATE_NOW"),
        "telegram_sent":  sent,
    }
    with open(HARVEST_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


if __name__ == "__main__":
    print(f"[{datetime.now().isoformat()}] TECH HARVEST starting…")

    harvest  = run_harvest()
    known    = load_known_tools()
    new_tools = [t for t in harvest.get("tools", []) if t.get("name", "").lower() not in known]

    if new_tools:
        save_tools(new_tools)

    msg  = build_telegram_message(harvest)
    sent = send_telegram(msg)
    _log(harvest, sent)

    n = len(harvest.get("tools", []))
    i = sum(1 for t in harvest.get("tools", []) if t.get("flag") == "INTEGRATE_NOW")
    print(f"[{datetime.now().isoformat()}] COMPLETE — {n} tools, {i} INTEGRATE_NOW, Telegram {'sent' if sent else 'queued'}")
