#!/usr/bin/env python3
"""
Dembe Intel Sweep — Daily Wing Intel Brief via Telegram
========================================================
Dreams2Memories Travel, LLC | scripts/dembe_intel_sweep.py

A2 Dembe's daily operational intel sweep. Synthesizes:
- Upcoming TP deadlines (7-day window)
- Client departure countdowns
- FPD alerts
- Draft queue status
- Wing system health
Posts to Commander via D2MC2C_bot Telegram.

Usage:
    python3 scripts/dembe_intel_sweep.py          # Run sweep + Telegram post
    python3 scripts/dembe_intel_sweep.py --local  # Print only, no Telegram
    python3 scripts/dembe_intel_sweep.py --timer  # Silent systemd mode
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
import yaml

THUNDERBIRD = Path.home() / "Thunderbird"
sys.path.insert(0, str(THUNDERBIRD))
sys.path.insert(0, str(THUNDERBIRD / "core" / "booking"))

from thunderbird_tp_scheduler import (
    scan_all_actionable,
    TPStatus,
)

ENV_FILE = THUNDERBIRD / ".env"
STATE_FILE = THUNDERBIRD / "hale_state.json"
QUEUE_LOG = THUNDERBIRD / "storage" / "lifecycle_draft_queue.jsonl"
DEDUP_FILE = THUNDERBIRD / "OpsCenter" / "dembe_intel_dedup.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s DEMBE %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(THUNDERBIRD / "logs" / "dembe_intel_sweep.log"), mode="a"),
    ],
)
logger = logging.getLogger("dembe")

SKIP_FILES = {"CLAUDE.md", "DOSSIER_Regent_Tips_Guide.md", "DANI_TESTER_BRIEFINGS.md"}


def _load_dedup() -> dict:
    """Load dedup state from JSON file."""
    if not DEDUP_FILE.exists():
        return {}
    try:
        with open(DEDUP_FILE) as f:
            return json.load(f)
    except Exception as exc:
        logger.warning(f"Failed to load dedup state: {exc}")
        return {}


def _save_dedup(state: dict) -> None:
    """Save dedup state to JSON file."""
    try:
        with open(DEDUP_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as exc:
        logger.error(f"Failed to save dedup state: {exc}")


def _urgency_tier(tp, today: date) -> str:
    """Bucket a hot TP into an urgency tier so escalation still alerts but a
    static unchanged item goes quiet."""
    if tp.status == TPStatus.OVERDUE:
        days_overdue = (today - tp.deadline).days if tp.deadline else 0
        if days_overdue <= 3:
            return "overdue-1-3"
        elif days_overdue <= 7:
            return "overdue-4-7"
        elif days_overdue <= 14:
            return "overdue-8-14"
        elif days_overdue <= 30:
            return "overdue-15-30"
        else:
            return "overdue-31plus"
    return "in-window"


def compute_hot_tp_alerts(actionable_tps: list, dedup_state: dict, today: date) -> tuple[list, bool, dict]:
    """
    Determine the hot (overdue/in-window) TPs and whether any are new-or-
    changed since the last dedup-tracked run.

    Returns (hot_tps, has_new_or_changed, updated_dedup_state). Caller is
    responsible for persisting updated_dedup_state via _save_dedup() only
    when the message is actually sent.
    """
    hot_tps = [tp for tp in actionable_tps if tp.status in (TPStatus.OVERDUE, TPStatus.IN_WINDOW)][:6]
    updated_state = dict(dedup_state)
    has_new = False
    for tp in hot_tps:
        key = f"{tp.tp_id}|{tp.client}|{_urgency_tier(tp, today)}"
        if key not in dedup_state:
            has_new = True
        updated_state[key] = today.isoformat()
    return hot_tps, has_new, updated_state


def _load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _tg_send(token: str, chat_id: int, text: str) -> bool:
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=15,
        )
        return resp.ok
    except Exception as exc:
        logger.error(f"Telegram send failed: {exc}")
        return False


def _tg_send_chunked(token: str, chat_id: int, text: str) -> bool:
    CHUNK = 4000
    if len(text) <= CHUNK:
        return _tg_send(token, chat_id, text)
    chunks = [text[i:i+CHUNK] for i in range(0, len(text), CHUNK)]
    ok = True
    for chunk in chunks:
        if not _tg_send(token, chat_id, chunk):
            ok = False
    return ok


def get_client_departure_radar() -> list[dict]:
    """Clients departing within 90 days, sorted ascending."""
    today = date.today()
    radar = []
    for path in sorted(THUNDERBIRD.glob("dossiers/*.md")):
        if path.name in SKIP_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
            m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
            if not m:
                continue
            fm = yaml.safe_load(m.group(1)) or {}
            if str(fm.get("status", "")).lower() not in ("active", "prospect"):
                continue
            dep_raw = fm.get("departure")
            if not dep_raw:
                continue
            dep = date.fromisoformat(str(dep_raw)) if isinstance(dep_raw, str) else dep_raw
            days = (dep - today).days
            if 0 <= days <= 90:
                radar.append({
                    "client": fm.get("full_name", fm.get("client", path.stem)),
                    "ship": f"{fm.get('cruise_line','')} {fm.get('ship','')}".strip(),
                    "departure": dep.strftime("%-d %b %Y"),
                    "days": days,
                    "payment": fm.get("payment_status", ""),
                })
        except Exception:
            pass
    return sorted(radar, key=lambda r: r["days"])


def get_fpd_alerts() -> list[dict]:
    today = date.today()
    alerts = []
    for path in sorted(THUNDERBIRD.glob("dossiers/*.md")):
        if path.name in SKIP_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
            m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
            if not m:
                continue
            fm = yaml.safe_load(m.group(1)) or {}
            if str(fm.get("status", "")).lower() != "active":
                continue
            if fm.get("payment_status") in ("paid_in_full", "paid", "complete"):
                continue
            fpd_raw = fm.get("fpd")
            if not fpd_raw:
                continue
            fpd = date.fromisoformat(str(fpd_raw)) if isinstance(fpd_raw, str) else fpd_raw
            days = (fpd - today).days
            if days <= 30:
                icon = "🔴" if days < 0 else ("🟡" if days <= 14 else "🟠")
                alerts.append({
                    "client": fm.get("full_name", fm.get("client", path.stem)),
                    "fpd": fpd.strftime("%-d %b %Y"),
                    "days": days,
                    "icon": icon,
                    "amount": fm.get("fpd_amount", "?"),
                })
        except Exception:
            pass
    return sorted(alerts, key=lambda a: a["days"])


def build_intel_message(
    today: date,
    actionable_tps: list,
    radar: list[dict],
    fpd_alerts: list[dict],
    queue_count: int,
    state: dict,
    hot_tps: list | None = None,
) -> str:
    now_str = datetime.now().strftime("%H:%M MT")
    lines = [
        f"🦅 <b>A2 DEMBE — DAILY INTEL SWEEP</b>",
        f"<i>{today.isoformat()} · {now_str}</i>",
        "",
    ]

    # Departure radar
    if radar:
        lines.append("📍 <b>DEPARTURE RADAR (next 90d)</b>")
        for r in radar[:6]:
            paid_tag = " ✅" if r["payment"] in ("paid_in_full", "paid", "complete") else ""
            lines.append(f"  T-{r['days']:>3}d  {r['client']} — {r['ship']} · {r['departure']}{paid_tag}")
        lines.append("")

    # FPD alerts
    if fpd_alerts:
        lines.append("💳 <b>FPD ALERTS</b>")
        for a in fpd_alerts:
            rel = f"T-{a['days']}d" if a["days"] >= 0 else f"OVERDUE {abs(a['days'])}d"
            lines.append(f"  {a['icon']} {a['client']} — {a['fpd']} ({rel})")
        lines.append("")

    # Upcoming TPs (overdue + in-window)
    if hot_tps is None:
        hot_tps = [tp for tp in actionable_tps if tp.status in (TPStatus.OVERDUE, TPStatus.IN_WINDOW)][:6]
    if hot_tps:
        lines.append("📋 <b>HOT TPs (overdue / in window)</b>")
        for tp in hot_tps:
            icon = "🔴" if tp.status == TPStatus.OVERDUE else "🟡"
            dl = tp.deadline.strftime("%-d %b") if tp.deadline else "?"
            lines.append(f"  {icon} TP {tp.tp_id} [{tp.client}] — {tp.label} · {dl}")
        lines.append("")

    # WF-17 queue
    if queue_count > 0:
        lines.append(f"📥 <b>WF-17 GATE</b>: {queue_count} draft(s) awaiting Commander review")
        lines.append("   → Run <code>/drafts</code> in Claude Code to review")
        lines.append("")

    # System health
    health = state.get("wing_health", {})
    mcp = health.get("mcp_server", "?")
    tg = "LIVE" if "LIVE" in str(health.get("telegram_bots", "")) else health.get("telegram_bot", "?")
    opencode = health.get("opencode", "?")
    lines.append(f"⚙️ <b>WING HEALTH</b>: MCP {mcp} · Telegram {tg} · OC {str(opencode)[:20]}")
    lines.append("")
    lines.append(f"<i>— A2 Dembe · Thunderbird Wing</i>")

    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description="Dembe Intel Sweep")
    p.add_argument("--local", action="store_true", help="Print only, no Telegram")
    p.add_argument("--timer", action="store_true", help="Silent systemd timer mode")
    args = p.parse_args()

    today = date.today()
    env = _load_env()
    token = env.get("TELEGRAM_D2MC2C_TOKEN", os.environ.get("TELEGRAM_D2MC2C_TOKEN", ""))
    commander_id = int(env.get("TELEGRAM_COMMANDER_ID", "7554895206"))

    try:
        state = json.loads(STATE_FILE.read_text())
    except Exception:
        state = {}

    try:
        actionable = scan_all_actionable(horizon_days=7, today=today)
    except Exception as exc:
        logger.error(f"TP scan failed: {exc}")
        actionable = []

    radar = get_client_departure_radar()
    fpd_alerts = get_fpd_alerts()

    queue_count = 0
    if QUEUE_LOG.exists():
        for line in QUEUE_LOG.read_text().splitlines():
            try:
                e = json.loads(line)
                if e.get("status") in ("queued", "voice_drafted"):
                    queue_count += 1
            except Exception:
                pass

    dedup_state = _load_dedup()
    hot_tps, has_new_or_changed, updated_dedup_state = compute_hot_tp_alerts(actionable, dedup_state, today)

    msg = build_intel_message(today, actionable, radar, fpd_alerts, queue_count, state, hot_tps=hot_tps)

    try:
        from core.staffing.sss_render import render_info_text
        msg = render_info_text(
            subject=f"Daily Intel Sweep — {today.isoformat()}",
            opr="Dembe (A2)", staffed_by=["Dembe (A2)"],
            purpose="Daily touchpoint/departure/FPD intelligence sweep.",
            discussion=msg,
            tag="Intel",
        )
    except Exception as e:
        logger.error(f"sss_render wrap failed (non-fatal, sending unwrapped): {e}")

    if args.local or not token:
        print(msg)
        if not token:
            logger.warning("No TELEGRAM_D2MC2C_TOKEN — printed only")
    elif not has_new_or_changed:
        logger.info("Hot TP list unchanged since last run — skipping Telegram send (dedup)")
        if not args.timer:
            print("  ⏭️  Skipped Telegram send — no new/changed hot TP items (dedup)")
    else:
        ok = _tg_send_chunked(token, commander_id, msg)
        logger.info(f"Intel sweep sent to Telegram: {ok}")
        _save_dedup(updated_dedup_state)
        if not args.timer:
            print(f"  {'✅' if ok else '❌'} Intel sweep posted to Telegram")

    # Post INTEL signal to staff_signal_bus (Agent-to-Agent substrate)
    try:
        from core.ai_infra.staff_signal_bus import post as post_signal
        pri = "high" if any(a.get("days", 99) < 0 for a in fpd_alerts) else ("med" if fpd_alerts else "low")
        sig_id = post_signal(
            from_persona="dembe",
            type="INTEL",
            subject=f"Daily Intel Sweep {today.isoformat()} — {len(radar)} departures, {len(fpd_alerts)} FPD alerts",
            detail=f"Departures in 90d: {len(radar)}, FPD alerts: {len(fpd_alerts)}, Hot TPs: {len(hot_tps)}, WF-17 queue: {queue_count}",
            priority=pri,
        )
        logger.info(f"Staff signal bus: posted #{sig_id} [INTEL] from dembe")
    except Exception as exc:
        logger.warning(f"Staff signal bus post failed: {exc}")


if __name__ == "__main__":
    main()

