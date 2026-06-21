#!/usr/bin/env python3
"""
generate_wing_status.py
D2M Thunderbird OS — Wing Status Auto-Regen
Runs daily at 05:30 MT via cron.

Reads: dossiers/*.md + hale_state.json
Writes:
  - hale_brief.md          (flat markdown, <600 tokens, AI-readable)
  - docs/executive_gantt_all_clients.html  (Commander's visual)
  - storage/output/executive_gantt_all_clients.html  (tunnel copy)
"""

import json
import os
import re
import shutil
import subprocess
from datetime import date, datetime, timedelta

BASE = "/home/john/Thunderbird"
BRIEF_OUT = f"{BASE}/hale_brief.md"
GANTT_SRC = f"{BASE}/docs/executive_gantt_all_clients.html"
GANTT_DST = f"{BASE}/storage/output/executive_gantt_all_clients.html"
DOSSIER_DIR = f"{BASE}/dossiers"
STATE_FILE  = f"{BASE}/hale_state.json"

TODAY = date.today()
TODAY_STR = TODAY.strftime("%Y-%m-%d")
TODAY_HUMAN = TODAY.strftime("%Y-%m-%d")

# ─── Client definitions (static; update here when new bookings added) ──────────
# MANUAL — update when client status changes (phase, open items, fpd_status, cancelled)
# departure: ISO date string
# phase: ONBOARDING / RESEARCH / MOMENTUM / PRE-DEPARTURE / VOYAGE / CANCELLED
# fpd_status: "PAID" | "PAID $X,XXX" | "DUE MMDD" | "PENDING"
# open: list of open item strings
CLIENTS = [
    {
        "name": "McLeod / McGlasson",
        "ship": "Silver Muse · Silversea · Med",
        "departure": "2026-06-23",
        "phase": "PRE-DEPARTURE",
        "fpd_status": "PAID",
        "fpd_paid": True,
        "open": ["transfer dispute", "return flights TBD"],
        "owner": "A3",
        "cancelled": False,
    },
    {
        "name": "Lyons, Nancy & Ken",
        "ship": "Regent Splendor · Athens→NY",
        "departure": "2026-08-11",
        "phase": "PRO BONO — advisory only",
        # PRO BONO / friend service. FPD PAID 2026-03-14 (booked via Pavlus, D2M does not touch booking).
        # Commander confirmed pro-bono 5+ times — NEVER flag FPD/payment/commission for Lyons. (Fixed 2026-06-15)
        "fpd_status": "PAID (pro bono)",
        "fpd_paid": True,
        "fpd_due": None,
        "open": [],
        "owner": "Commander (friend service)",
        "probono": True,
        "cancelled": False,
    },
    {
        "name": "Furlow, Missy & John",
        "ship": "Regent Grandeur · Scandinavia",
        "departure": "2026-08-29",
        "phase": "PRE-DEPARTURE",
        "fpd_status": "PAID $15,486",
        "fpd_paid": True,
        "open": ["flights TBD"],
        "owner": "A3",
        "cancelled": False,
    },
    {
        "name": "Nichols, Larry",
        "ship": "Regent Grandeur · Scandinavia",
        "departure": "2026-08-29",
        "phase": "PRE-DEPARTURE",
        "fpd_status": "PAID",
        "fpd_paid": True,
        "open": ["flights TBD"],
        "owner": "A3",
        "cancelled": False,
    },
    {
        "name": "Ely / Darrow",
        "ship": "Regent Grandeur · Scandinavia",
        "departure": "2026-08-29",
        "phase": "PRE-DEPARTURE",
        "fpd_status": "PAID",
        "fpd_paid": True,
        "open": ["flights TBD", "pre/post hotel TBD"],
        "owner": "A3",
        "cancelled": False,
    },
    {
        "name": "Kuklinski · 3 couples",
        "ship": "Viking Mars · Panama Canal",
        "departure": "2026-12-17",
        "phase": "RESEARCH",
        "fpd_status": "PAID $21,244",
        "fpd_paid": True,
        "open": ["air fare watch (A2, Jun 17)", "hotel 3+3 search (A2, Jun 17)",
                 "validation email (HOLD → Jul 15)", "insurance email (HOLD → Jul 15)",
                 "Josh Morton guest form (HOLD → Jul 15)"],
        "owner": "A6→A9→A3",
        "cancelled": False,
    },
    {
        "name": "Westbrook, Ron & Lindy",
        "ship": "Silver Nova · Pacific",
        "departure": "2026-04-23",
        "phase": "CANCELLED",
        "fpd_status": "CANCELLED",
        "fpd_paid": False,
        "open": ["CLOSED 2026-06-13 — Allianz claim is Ron's personal matter (Commander directive)"],
        "owner": "COS",
        "cancelled": True,
        "cancel_note": "Medical emergency 2026-04-20 · Booking 566904-25",
    },
]

# ─── Overdue actions (manual; update when resolved) ─────────────────────────
# HOLDS in effect (see hale_state.json project_tracking + hale_decisions.md):
#   Kuklinski all emails → HOLD until 2026-07-15 (Commander directive 2026-06-12)
#   McLeod all lifecycle → HOLD until 2026-07-07 (Commander directive 2026-06-13)
# REMOVE hold entries from here; restore when holds lift on those dates.
OVERDUE = [
    {"item": "Silversea cancel booking 566904-25","client": "Westbrook", "days": 0, "owner": "COS — awaiting Commander confirm"},
]

# ─── Next-30-day items ────────────────────────────────────────────────────────
# MANUAL — roll forward as items complete or new deadlines emerge
NEXT_30 = [
    {"item": "Kuklinski air fare watch + hotel 3+3 search", "client": "Kuklinski", "due": "Jun 17", "owner": "A2 Dembe"},
    {"item": "McLeod lifecycle + FPD contact ($11,943)",    "client": "McLeod",     "due": "Jul 7",  "owner": "Hale"},
    {"item": "Kuklinski emails reactivation (all)",         "client": "Kuklinski",  "due": "Jul 15", "owner": "Hale"},
    {"item": "Loucks Grandeur FPD $24,798",                 "client": "Loucks",     "due": "Aug 1",  "owner": "Commander pays"},
]

# ─── Staff assignments ────────────────────────────────────────────────────────
# MANUAL — update when task load shifts between sessions
STAFF = [
    {"name": "A2 Dembe (Wraith)", "workload": "Kuklinski air/hotel search (Jun 17 delivery), Panama Canal research"},
    {"name": "A3 Dani",           "workload": "Kuklinski emails HOLD until Jul 15"},
    {"name": "A9 Harlan",         "workload": "Commission tracking, Loucks FPD Aug 1 watch"},
    {"name": "COS Hale",          "workload": "Westbrook cancellation pending; McLeod/Kuklinski holds monitoring"},
]

# ─── System health (read from hale_state.json if available) ──────────────────
DEFAULT_SYS = {
    "d2m-tasking-watcher": "RUNNING (V6 inotify)",
    "MCP server":          "RUNNING port 8765",
    "Telegram gateway":    "RUNNING 3 bots",
    "OAuth cache":         "LIVE (auto-refresh)",
    "Chrome debug":        "OFFLINE (port 9222)",
}

def load_system_health():
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
        sh = state.get("system_health", {})
        return {
            "d2m-tasking-watcher": sh.get("d2m-tasking-watcher", DEFAULT_SYS["d2m-tasking-watcher"]),
            "MCP server":          sh.get("mcp_server",          DEFAULT_SYS["MCP server"]),
            "Telegram gateway":    sh.get("telegram_gw",         DEFAULT_SYS["Telegram gateway"]),
            "OAuth cache":         sh.get("oauth_cache",         DEFAULT_SYS["OAuth cache"]),
            "Chrome debug":        sh.get("chrome_debug",        DEFAULT_SYS["Chrome debug"]),
        }
    except Exception:
        return DEFAULT_SYS


def load_keepalive_health():
    """Read OpsCenter/keepalive_health.json (MISSION-211 supervisor output).

    Returns (status_line, escalation_lines). Fully defensive — a missing or
    malformed file never breaks the brief; it just yields an UNKNOWN line.
    """
    kh_path = "/home/john/Thunderbird/OpsCenter/keepalive_health.json"
    try:
        with open(kh_path) as f:
            kh = json.load(f)
        overall = kh.get("overall_status", "UNKNOWN")
        c = kh.get("counts", {})
        gen = kh.get("generated_mt", "?")
        flag = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴", "UNKNOWN": "⚪"}.get(overall, "⚪")
        status_line = (f"{flag} {overall} "
                       f"(G{c.get('GREEN',0)}/Y{c.get('YELLOW',0)}/"
                       f"R{c.get('RED',0)}/U{c.get('UNKNOWN',0)}) · {gen}")
        esc_lines = []
        for e in kh.get("escalations", []) or []:
            esc_lines.append(f"- ⚠️ **{e.get('credential','?')}** needs re-auth: "
                             f"`{e.get('command','(no command)')}`")
        return status_line, esc_lines
    except Exception:
        return "⚪ UNKNOWN (keepalive_health.json not readable)", []


def days_overdue(due_date_str: str) -> int:
    """Return days since due_date (positive = overdue)."""
    try:
        due = date.fromisoformat(due_date_str)
        return (TODAY - due).days
    except Exception:
        return 0


def build_hale_brief(sys_health: dict) -> str:
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")

    lines = [
        f"# WING STATUS — {TODAY_HUMAN} · Dreams2Memories Travel, LLC",
        "*Auto-generated · Read this first · Source of truth for session orientation*",
        "",
        "---",
        "",
        "## 🔴 OVERDUE — ACTION REQUIRED NOW",
        "",
        "| Item | Client | Days Over | Owner |",
        "|------|--------|-----------|-------|",
    ]

    # HOLDS / CLOSED (Commander directives — see hale_decisions.md for dates):
    #   Kuklinski all emails → HOLD Jul 15 (2026-06-12)
    #   McLeod all lifecycle → HOLD Jul 7  (2026-06-13)
    #   Westbrook → CLOSED   (2026-06-13) — Allianz claim is Ron's personal matter
    #   Lyons → CLOSED until Aug (2026-06-14) — FPD paid, reactivate Jul 25 (T-14)
    active_overdue = []  # nothing overdue — update when new items surface
    for o in active_overdue:
        lines.append(f"| {o['item']} | {o['client']} | {o['days_over']} | {o['owner']} |")

    lines += [
        "",
        "---",
        "",
        "## 🟡 NEXT 30 DAYS",
        "",
        "| Item | Client | Due | Owner |",
        "|------|--------|-----|-------|",
    ]
    for n in NEXT_30:
        lines.append(f"| {n['item']} | {n['client']} | {n['due']} | {n['owner']} |")

    lines += [
        "",
        "---",
        "",
        "## CLIENTS — sorted by departure",
        "",
        "| Client | Ship / Line | Depart | Phase | FPD | Open Items |",
        "|--------|------------|--------|-------|-----|------------|",
    ]

    for c in CLIENTS:
        open_str = str(len(c["open"])) if c["open"] else "0"
        if c["open"]:
            open_str += f" ({', '.join(c['open'][:2])}{'...' if len(c['open'])>2 else ''})"
        if c["cancelled"]:
            row = (f"| ~~{c['name']}~~ | ~~{c['ship']}~~ | ~~{c['departure']}~~ "
                   f"| **CANCELLED — {c.get('cancel_note','')}** | — "
                   f"| {open_str} |")
        else:
            fpd_display = ("✅ PAID" if c["fpd_paid"] else f"⚠️ **{c['fpd_status']}**")
            # Add dollar amount if present
            if c["fpd_paid"] and "$" in c["fpd_status"]:
                fpd_display = f"✅ {c['fpd_status']}"
            row = (f"| {c['name']} | {c['ship']} | {c['departure']} "
                   f"| {c['phase']} | {fpd_display} | {open_str} |")
        lines.append(row)

    lines += [
        "",
        "---",
        "",
        "## KUKLINSKI — DETAIL (most complex active client)",
        "",
        "- **Booking:** 9593880 / 9593873 / 9595029 · Viking Mars · Panama City → Ft Lauderdale · Dec 17–27",
        "- **Guests:** Kyle + Rosalie, Roger + Nick, Josh + Erica — 6 pax, 3 couples",
        "- **Active search windows:** Air (A2, open now), Hotel pre/post (A2, open now)",
        "- **Excursion window opens:** Aug 2, 2026 (Viking portal)",
        "- **Dining window opens:** Sep 18, 2026 (T-90)",
        "- **ON HOLD until Jul 15:** Validation email, insurance email, Josh guest form (Commander directive 2026-06-12)",
        "- **Next delivery:** Air fare watch — Jun 17; Hotel 3+3 search — Jun 17",
        "",
        "---",
        "",
        "## WESTBROOK — CANCELLATION STATUS",
        "",
        "- Booking 566904-25 (Silver Nova, $10,800) — CANCELLED medical emergency",
        "- Both transfers already cancelled and refunded (2026-04-19)",
        "- Allianz Annual Premier Conf E2549991663 ($15K policy) — claim scope $11,280",
        "- **Pending:** Commander approval to contact Jenna Woodcock (Perx, +1 512-691-4501) and Zoro L (SkyLux) to initiate cruise cancellation",
        "- Hilton Tokyo 33S2013960 (~$480) — Allianz claim also pending",
        "",
        "---",
        "",
        "## STAFF ASSIGNMENTS — ACTIVE",
        "",
        "| Staff | Active Workload |",
        "|-------|----------------|",
    ]
    for s in STAFF:
        lines.append(f"| {s['name']} | {s['workload']} |")

    lines += [
        "",
        "---",
        "",
        "## SYSTEM HEALTH",
        "",
        "| Service | Status |",
        "|---------|--------|",
    ]
    for svc, status in sys_health.items():
        lines.append(f"| {svc} | {status} |")

    # MISSION-211 — keepalive supervisor health + any human re-auth escalations.
    ka_status, ka_esc = load_keepalive_health()
    lines.append(f"| Keepalive supervisor | {ka_status} |")
    if ka_esc:
        lines += [
            "",
            "### 🔑 CREDENTIAL RE-AUTH NEEDED (keepalive supervisor)",
            "",
        ]
        lines += ka_esc

    lines += [
        "",
        "---",
        "",
        f"*Source files: dossiers/ · hale_state.json · THUNDERBIRD_MASTER_PLAN.md*",
        f"*Auto-regen target: 05:30 MT daily via scripts/generate_wing_status.py*",
        f"*Token count target: <600 · Timestamp: {ts}*",
        "",
    ]

    return "\n".join(lines)


def update_gantt_today_date():
    """Update TODAY date in executive_gantt_all_clients.html."""
    try:
        with open(GANTT_SRC, "r") as f:
            content = f.read()

        # Replace the TODAY constant in the script
        today_iso = TODAY_STR
        today_human = TODAY.strftime("%b %-d, %Y")

        content = re.sub(
            r"const TODAY\s*=\s*new Date\('[^']+'\);",
            f"const TODAY    = new Date('{today_iso}');",
            content,
        )
        # Update the status bar "TODAY: ..." badge
        content = re.sub(
            r"TODAY: [A-Za-z]+ \d+, \d+",
            f"TODAY: {today_human}",
            content,
        )
        # Update the generated date in footer
        content = re.sub(
            r"Generated [A-Za-z]+ \d+, \d{4}",
            f"Generated {today_human}",
            content,
        )
        # Update the header generated badge
        content = re.sub(
            r"GENERATED: [A-Z]+ \d+, \d{4}",
            f"GENERATED: {TODAY.strftime('%b %-d, %Y').upper()}",
            content,
        )

        with open(GANTT_SRC, "w") as f:
            f.write(content)
        print(f"  [gantt] Updated TODAY date to {today_iso}")
    except Exception as e:
        print(f"  [gantt] WARNING — date update failed: {e}")


def main():
    print(f"\n{'='*60}")
    print(f"  D2M Wing Status Regen — {TODAY_STR}")
    print(f"{'='*60}\n")

    # 1. Load system health from state file
    sys_health = load_system_health()
    print(f"  [state] System health loaded from {STATE_FILE}")

    # 2. Write hale_brief.md
    brief_content = build_hale_brief(sys_health)
    with open(BRIEF_OUT, "w") as f:
        f.write(brief_content)
    token_est = len(brief_content.split()) * 1.3  # rough estimate
    print(f"  [brief] hale_brief.md written (~{int(token_est)} tokens estimated)")

    # 3. Update today's date in executive gantt
    update_gantt_today_date()

    # 4. Copy gantt to tunnel output directory
    shutil.copy2(GANTT_SRC, GANTT_DST)
    print(f"  [gantt] Copied to storage/output/")

    # 5. Report summary
    active = [c for c in CLIENTS if not c["cancelled"]]
    cancelled = [c for c in CLIENTS if c["cancelled"]]
    open_total = sum(len(c["open"]) for c in active)

    print(f"\n  Summary:")
    print(f"    Active clients:  {len(active)}")
    print(f"    Cancelled:       {len(cancelled)}")
    print(f"    Total open items:{open_total}")
    print(f"    Overdue actions: {len(OVERDUE)}")
    print(f"\n  Outputs:")
    print(f"    {BRIEF_OUT}")
    print(f"    {GANTT_SRC}")
    print(f"    {GANTT_DST}")
    print(f"\n  Tunnel URL: https://itinerary.d2mluxury.quest/executive_gantt_all_clients.html")
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
