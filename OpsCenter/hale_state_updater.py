"""
Hale State Updater
==================
Pulls live data from MCP tools and writes to hale_state.json.
Run before brief generation to ensure state is current.

Runs as part of hale-brief-generate.service (pre-exec) and on demand.

Author: Victoria "Victory" Hale, SES-6 — 2026-04-03 (re-roled 2026-05-17)
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
        state["wing_health"]["opencode_status"] = "UNKNOWN"
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

    # ── Unified financial pulse (TESS + Booking Master sheet) ──
    pulse: dict = {"last_checked": now}
    sys.path.insert(0, str(_ROOT / "core" / "booking"))

    # TESS side — what's already in the CRM (Kuklinski, McLeod Dec, Loucks Dec, Westbrook…)
    try:
        from thunderbird_tess import TESSClient
        tc = TESSClient()
        bookings = tc.list_bookings(page_size=200)
        clients = tc.list_clients(page_size=200)
        trips = tc.list_trips(page_size=200)
        summary = tc.get_commission_summary()
        if "error" not in bookings and "error" not in summary:
            pulse["tess_auth_status"] = "ONLINE"
            pulse["tess_trips"] = trips.get("CountUnfiltered", 0)
            pulse["tess_bookings"] = bookings.get("CountUnfiltered", 0)
            pulse["tess_clients"] = clients.get("CountUnfiltered", 0)
            pulse["tess_pkg_total"] = round(sum(
                (b.get("PackagePrice") or 0) for b in (bookings.get("Items") or [])
            ), 2)
            pulse["tess_received"] = round(summary.get("total_received", 0), 2)
            pulse["tess_due"] = round(summary.get("total_due", 0), 2)
            pulse["tess_checks_received"] = summary.get("checks_received_count", 0)
        else:
            pulse["tess_auth_status"] = "ERROR"
            pulse["tess_error"] = bookings.get("error") or summary.get("error")
    except Exception as e:
        pulse["tess_auth_status"] = "EXCEPTION"
        pulse["tess_error"] = str(e)

    # Booking Master sheet — source of truth incl. McLeod June, Ely/Darrow, Nichols, Furlow Aug
    try:
        from booking_master import BookingMasterClient
        bmc = BookingMasterClient()
        bm_summary = bmc.commission_summary()
        upcoming = bmc.upcoming_voyages()
        pulse["sheet_status"] = "ONLINE"
        pulse["sheet_bookings"] = bm_summary.get("booking_count", 0)
        pulse["sheet_commission_expected"] = round(bm_summary.get("total_expected", 0), 2)
        pulse["sheet_d2m_share"] = round(bm_summary.get("total_d2m_share", 0), 2)
        pulse["sheet_upcoming_count"] = len(upcoming)
        # Commission still in pipeline (D2M share of upcoming voyages only)
        pulse["pipeline_d2m_share_upcoming"] = round(sum(
            (b.get("_parsed_d2m_share") or 0) for b in upcoming
        ), 2)
        pulse["pipeline_commission_upcoming"] = round(sum(
            (b.get("_parsed_commission") or 0) for b in upcoming
        ), 2)
    except Exception as e:
        pulse["sheet_status"] = "EXCEPTION"
        pulse["sheet_error"] = str(e)

    # Top-level summary: total D2M commission income waiting (sheet pipeline + TESS due)
    pulse["total_d2m_pipeline"] = round(
        pulse.get("pipeline_d2m_share_upcoming", 0) + pulse.get("tess_due", 0), 2
    )
    pulse["raw_snippet"] = (
        f"D2M pipeline: ${pulse.get('total_d2m_pipeline', 0):,.2f} D2M share "
        f"across {pulse.get('sheet_upcoming_count', 0)} upcoming voyages "
        f"(sheet) + {pulse.get('tess_checks_received', 0)} checks already received "
        f"totaling ${pulse.get('tess_received', 0):,.2f} (TESS)."
    )
    state["financial_pulse"] = pulse

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
