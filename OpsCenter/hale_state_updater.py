"""
Hale State Updater
==================
Pulls live data from MCP tools and writes to hale_state.json.
Run before brief generation to ensure state is current.

Runs as part of hale-brief-generate.service (pre-exec) and on demand.

Author: Col Victoria "Iron Vic" Hale — 2026-04-03
"""

import json
import sys
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
_STATE = _ROOT / "hale_state.json"

load_dotenv(str(_ROOT / ".env"))
load_dotenv(str(_ROOT / ".env.telegram"))

MT = timezone(timedelta(hours=-6))
MCP_URL = "http://127.0.0.1:8765/mcp"


def _mcp(tool: str, args: dict = {}, timeout: int = 20) -> dict:
    """Call MCP tool. Returns parsed result dict or error dict."""
    try:
        resp = requests.post(
            MCP_URL,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                  "params": {"name": tool, "arguments": args}},
            headers={"Content-Type": "application/json",
                     "Accept": "application/json, text/event-stream"},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            return {"error": data["error"].get("message", "MCP error")}
        content = data.get("result", {}).get("content", [])
        text = "\n".join(c.get("text", "") for c in content if c.get("type") == "text")
        return {"ok": True, "text": text}
    except requests.exceptions.ConnectionError:
        return {"error": "MCP offline"}
    except Exception as e:
        return {"error": str(e)}


def load_state() -> dict:
    try:
        return json.loads(_STATE.read_text())
    except Exception:
        return {}


def save_state(state: dict):
    _STATE.write_text(json.dumps(state, indent=2))


def update():
    state = load_state()
    now = datetime.now(MT).isoformat()
    if "_meta" not in state:
        state["_meta"] = {}
    state["_meta"]["last_updated"] = now

    # ── Wing health ──
    if "wing_health" not in state:
        state["wing_health"] = {}
    health = _mcp("system_health_check")
    if health.get("ok"):
        state["wing_health"]["last_health_check"] = now
        text = health["text"].lower()
        state["wing_health"]["mcp_server"] = "ONLINE"
        state["wing_health"]["goose_status"] = "UNKNOWN"
        state["wing_health"]["telegram_bot"] = "ONLINE" if "telegram" in text and "ok" in text else "UNKNOWN"
    else:
        state["wing_health"]["mcp_server"] = f"ERROR: {health.get('error', '?')}"

    # ── Open tasks ──
    tasks_result = _mcp("list_tasks")
    if tasks_result.get("ok"):
        raw = tasks_result["text"].strip()
        state["open_tasks"] = [{"raw": raw[:500]}] if raw and raw != "[]" else []
    else:
        state["open_tasks"] = [{"error": tasks_result.get("error")}]

    # ── Client dossiers ──
    dossier_result = _mcp("scan_dossiers")
    if dossier_result.get("ok"):
        raw = dossier_result["text"]
        # Update each known client with dossier snippet
        for client_key in ["Furlow", "Westbrook", "Lyons"]:
            if client_key.lower() in raw.lower():
                if client_key in state.get("active_clients", {}):
                    # Find the relevant snippet
                    idx = raw.lower().find(client_key.lower())
                    snippet = raw[max(0, idx-50):idx+300].strip()
                    state["active_clients"][client_key]["last_dossier_scan"] = snippet[:200]
                    state["active_clients"][client_key]["scan_at"] = now

    # ── TESS commissions ──
    commissions_result = _mcp("tess_get_commissions", {"limit": 10})
    if commissions_result.get("ok"):
        state["financial_pulse"] = {
            "last_checked": now,
            "raw_snippet": commissions_result["text"][:400],
        }

    # ── Session context update ──
    if "session_context" not in state:
        state["session_context"] = {}
    state["session_context"]["last_checkpoint"] = now

    save_state(state)
    print(f"[hale_state_updater] State updated at {now}")
    return state


if __name__ == "__main__":
    result = update()
    print(json.dumps({
        "wing_health": result.get("wing_health", {}),
        "open_tasks_count": len(result.get("open_tasks", [])),
        "clients": list(result.get("active_clients", {}).keys()),
    }, indent=2))
