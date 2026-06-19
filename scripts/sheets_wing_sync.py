#!/usr/bin/env python3
"""
sheets_wing_sync.py — Sync Wing state to Google Sheets.

Writes to three tabs in the Booking Master spreadsheet:
  Wing_Dashboard  — bot health, financial pulse, missions, system health
  Fare Log        — active fare watch results (appended)
  Action_Tracker  — P0/P1 mission items (upserted by mission ID)

Runs via backup_bot (daily). Can also be called manually.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import gspread

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))
from core.booking.booking_master import BookingMasterClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("sheets_wing_sync")

SHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
DASHBOARD_TAB = "Wing_Dashboard"
FARE_LOG_TAB = "Fare Log"
ACTION_TRACKER_TAB = "Action_Tracker"
DANI_TAB = "Dani_Client_Tracker"
SHIP_INTEL_TAB = "Ship Intelligence"


# ──────────────────────────────────────────────────────────────── helpers

def _bmc_spreadsheet():
    c = BookingMasterClient()
    ws = c._worksheet()
    return ws.spreadsheet


def _get_or_create_tab(spreadsheet, title: str, rows: int = 200, cols: int = 20):
    try:
        return spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        log.info("Creating tab: %s", title)
        return spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)


def _now_mt() -> str:
    from datetime import timezone, timedelta
    mt = datetime.now(tz=timezone(timedelta(hours=-6)))
    return mt.strftime("%Y-%m-%d %H:%M MT")


# ──────────────────────────────────────────────────────────── data readers

def _read_bot_health() -> list[dict]:
    bots = [
        "ops_bot", "comms_bot", "infra_bot", "client_bot", "metrics_bot",
        "intel_bot", "mission_bot", "finance_bot", "ai_exec_bot", "backup_bot", "audit_bot",
    ]
    rows = []
    for bot in bots:
        sf = ROOT / f"OpsCenter/supertimer_{bot}_state.json"
        if not sf.exists():
            rows.append({"bot": bot, "status": "NO_STATE", "ok": 0, "fail": 0, "consec": 0})
            continue
        try:
            st = json.loads(sf.read_text())
            tasks = st.get("tasks", {})
            ok = sum(1 for t in tasks.values() if t.get("last_status") == "ok")
            fail = sum(1 for t in tasks.values() if t.get("last_status") == "fail")
            consec = st.get("consecutive_failures", 0)
            status = "RED" if consec >= 3 else ("YELLOW" if consec > 0 else "GREEN")
            rows.append({"bot": bot, "status": status, "ok": ok, "fail": fail, "consec": consec})
        except Exception as e:
            rows.append({"bot": bot, "status": "ERROR", "ok": 0, "fail": 0, "consec": 0})
    return rows


def _read_financial_pulse() -> dict:
    fp = ROOT / "OpsCenter/state/financial_pulse_latest.txt"
    if not fp.exists():
        # Try booking master directly
        try:
            bmc = BookingMasterClient()
            summary = bmc.commission_summary()
            return {
                "bookings": summary.get("total_bookings", 0),
                "commission": summary.get("total_commission", 0),
                "d2m_share": summary.get("total_d2m_share", 0),
                "balance_due": summary.get("total_balance_due", 0),
                "source": "live",
            }
        except Exception:
            return {}
    text = fp.read_text(errors="ignore")
    # Parse the simple txt format
    result = {"source": "file"}
    for line in text.splitlines():
        if "Pipeline:" in line:
            import re
            m = re.search(r"(\d+) bookings", line)
            if m:
                result["bookings"] = int(m.group(1))
        if "Balance due:" in line:
            import re
            m = re.search(r"\$([\d,]+\.\d+)", line)
            if m:
                result["balance_due"] = float(m.group(1).replace(",", ""))
        if "Commission expected:" in line:
            import re
            m = re.search(r"\$([\d,]+\.\d+)", line)
            if m:
                result["commission"] = float(m.group(1).replace(",", ""))
        if "D2M share:" in line:
            import re
            m = re.search(r"\$([\d,]+\.\d+)", line)
            if m:
                result["d2m_share"] = float(m.group(1).replace(",", ""))
    return result


def _read_p0_missions() -> list[dict]:
    mb = ROOT / "OpsCenter/mission_board.json"
    if not mb.exists():
        return []
    try:
        data = json.loads(mb.read_text())
        missions = data.get("missions", data.get("tasks", []))
        return [
            m for m in missions
            if m.get("priority") in ("P0", "P1")
            and m.get("status") not in ("closed", "complete", "completed")
        ]
    except Exception:
        return []


def _read_fare_watches() -> list[dict]:
    fw = ROOT / "core/travel/data/fare_watches.json"
    if not fw.exists():
        return []
    try:
        data = json.loads(fw.read_text())
        return [w for w in data.get("watches", []) if w.get("active")]
    except Exception:
        return []


def _dead_code_count() -> int:
    report = ROOT / "OpsCenter/state/dead_code_report.txt"
    if not report.exists():
        return -1
    for line in report.read_text().splitlines():
        if "Findings:" in line:
            import re
            m = re.search(r"Findings:\s*(\d+)", line)
            if m:
                return int(m.group(1))
    return -1


# ──────────────────────────────────────────────────────────── tab writers

def sync_dashboard(spreadsheet) -> None:
    ws = _get_or_create_tab(spreadsheet, DASHBOARD_TAB, rows=100, cols=8)
    ws.clear()

    now = _now_mt()
    rows = []

    # Header
    rows += [
        ["🦅 THUNDERBIRD WING DASHBOARD", now, "", "", "", "", "", ""],
        ["", "", "", "", "", "", "", ""],
    ]

    # Financial Pulse
    fp = _read_financial_pulse()
    rows += [
        ["📊 FINANCIAL PULSE", "", "", "", "", "", "", ""],
        ["Bookings", str(fp.get("bookings", "?")),
         "Balance Due", f"${fp.get('balance_due', 0):,.2f}",
         "Commission", f"${fp.get('commission', 0):,.2f}",
         "D2M Share", f"${fp.get('d2m_share', 0):,.2f}"],
        ["", "", "", "", "", "", "", ""],
    ]

    # Bot Health
    rows += [["🤖 BOT HEALTH", "Status", "Tasks OK", "Tasks Fail", "Consec Fails", "", "", ""]]
    for b in _read_bot_health():
        rows.append([b["bot"], b["status"], str(b["ok"]), str(b["fail"]), str(b["consec"]), "", "", ""])
    rows += [["", "", "", "", "", "", "", ""]]

    # P0/P1 Missions
    missions = _read_p0_missions()
    rows += [["🎯 ACTIVE MISSIONS (P0/P1)", "Priority", "Status", "Title", "", "", "", ""]]
    for m in missions[:20]:
        rows.append([
            m.get("id", ""), m.get("priority", ""), m.get("status", ""),
            (m.get("title", "") or "")[:80], "", "", "", "",
        ])
    rows += [["", "", "", "", "", "", "", ""]]

    # Fare Watches
    watches = _read_fare_watches()
    rows += [["✈️ FARE WATCHES", "Route", "Best Price", "Alert Below", "Dates", "", "", ""]]
    for w in watches[:10]:
        rows.append([
            w.get("label", w.get("id", ""))[:50],
            w.get("route", ""),
            f"${w.get('current_best_total', 0):,.2f}" if w.get("current_best_total") else "—",
            f"${w.get('alert_below', 0):,.2f}" if w.get("alert_below") else "—",
            f"{w.get('outbound_date','')} → {w.get('return_date','')}",
            "", "", "",
        ])
    rows += [["", "", "", "", "", "", "", ""]]

    # System Health
    dc = _dead_code_count()
    rows += [
        ["🔧 SYSTEM HEALTH", "", "", "", "", "", "", ""],
        ["Dead Code Findings", str(dc) if dc >= 0 else "scan pending", "", "", "", "", "", ""],
    ]

    ws.update("A1", rows, value_input_option="USER_ENTERED")
    log.info("Wing_Dashboard synced: %d rows", len(rows))


def sync_fare_log(spreadsheet) -> None:
    """Append current fare watch state to Fare Log tab."""
    ws = _get_or_create_tab(spreadsheet, FARE_LOG_TAB)
    watches = _read_fare_watches()
    if not watches:
        log.info("No active fare watches to log")
        return

    now_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    time_str = datetime.now(tz=timezone.utc).strftime("%H:%M UTC")

    new_rows = []
    for w in watches:
        best = w.get("current_best_total", 0)
        pax = w.get("passengers", 1)
        pp = best / pax if pax and best else 0
        new_rows.append([
            now_str, time_str,
            f"{pp:.2f}" if pp else "",
            f"{best:.2f}" if best else "",
            "", "", "",
            w.get("current_best_flight", ""),
            w.get("label", w.get("id", ""))[:80],
        ])

    if new_rows:
        ws.append_rows(new_rows, value_input_option="USER_ENTERED")
        log.info("Fare Log: appended %d rows", len(new_rows))


def sync_action_tracker(spreadsheet) -> None:
    """Upsert P0 missions into Action_Tracker."""
    ws = _get_or_create_tab(spreadsheet, ACTION_TRACKER_TAB)
    missions = _read_p0_missions()
    if not missions:
        log.info("No P0/P1 missions to sync")
        return

    # Read existing keys to avoid duplicates
    existing = ws.col_values(1)  # Booking_Key column (repurposing as mission ID)
    now_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

    new_rows = []
    for m in missions:
        mid = m.get("id", "")
        if mid in existing:
            continue  # already tracked
        new_rows.append([
            mid,
            (m.get("title", "") or "")[:80],
            "",  # Anchor_Date
            m.get("priority", ""),
            m.get("status", ""),
            "Wing",  # Updated_By
            now_str,
            (m.get("description", "") or "")[:200],
        ])

    if new_rows:
        ws.append_rows(new_rows, value_input_option="USER_ENTERED")
        log.info("Action_Tracker: added %d new mission rows", len(new_rows))
    else:
        log.info("Action_Tracker: no new missions to add")


# ──────────────────────────────────────────────────────────────────── Dani tracker

def sync_dani_tracker(spreadsheet) -> None:
    """Dani's client operations sheet — one row per active booking."""
    ws = _get_or_create_tab(spreadsheet, DANI_TAB, rows=200, cols=12)
    ws.clear()

    bmc = BookingMasterClient()
    bookings = bmc.list_bookings()
    missions = _read_p0_missions()

    # Build mission lookup by title fragment
    mission_map = {m.get("title", "").lower(): m for m in missions}

    # Load lifecycle state if available
    lc_state = ROOT / "OpsCenter/state/lifecycle_scheduler_latest.json"
    lc_data = {}
    if lc_state.exists():
        try:
            lc_data = json.loads(lc_state.read_text())
        except Exception:
            pass

    rows = [
        ["🎯 DANI CLIENT TRACKER", _now_mt(), "", "", "", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "", "", "", "", "", ""],
        ["Client", "Booking ID", "Ship / Voyage", "Departure", "FPD Status", "Balance Due",
         "Next TP", "Draft Status", "Priority", "Dani Voice Notes", "Last Updated", ""],
    ]

    active = [b for b in bookings if b.get("Status", "").lower() not in ("cancelled", "closed")]
    active.sort(key=lambda b: str(b.get("_parsed_start_date") or "9999-99-99"))

    for b in active:
        client = b.get("Client_Name", "")
        bid = b.get("Booking_ID", "")
        ship = b.get("LEG 3: Ship_Name") or b.get("Ship_Name") or b.get("Supplier", "")
        dep = b.get("Start_Date", "")
        balance = b.get("_parsed_balance_due", 0)
        fpd_status = "PAID" if balance == 0 else f"DUE {b.get('Final_Payment_Date', '?')}"
        fpd_color = "" if balance == 0 else "OVERDUE" if balance > 0 else ""

        # Next TP from lifecycle data if available
        next_tp = lc_data.get(bid, {}).get("next_tp", "—")
        draft_status = lc_data.get(bid, {}).get("draft_status", "—")

        rows.append([
            client[:40], bid, ship[:40], dep,
            fpd_status, f"${balance:,.2f}" if balance else "$0",
            next_tp, draft_status, "", "", _now_mt(), "",
        ])

    rows += [
        ["", "", "", "", "", "", "", "", "", "", "", ""],
        [f"Last sync: {_now_mt()} | {len(active)} active bookings", "", "", "", "", "", "", "", "", "", "", ""],
    ]

    ws.update("A1", rows, value_input_option="USER_ENTERED")
    log.info("Dani_Client_Tracker synced: %d bookings", len(active))


# ──────────────────────────────────────────────────────────────────── Ship intel

def sync_ship_intelligence(spreadsheet) -> None:
    """Populate Ship Intelligence tab from local dossier files."""
    ws = _get_or_create_tab(spreadsheet, SHIP_INTEL_TAB, rows=200, cols=10)

    # Read existing rows to avoid duplicates
    existing = ws.get_all_values()
    existing_ships = {r[1] for r in existing[1:] if len(r) > 1 and r[1]}

    ship_rows = []
    now_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    dossier_dir = ROOT / "dossiers"
    import re
    for f in sorted(dossier_dir.glob("DOSSIER_*.md")):
        text = f.read_text(errors="ignore")
        # Extract ship name from filename or content
        ship_match = re.search(r"(?:Ship|Vessel|Cruise Ship):\s*(.+?)[\n\r]", text, re.IGNORECASE)
        ship_name = ship_match.group(1).strip() if ship_match else None
        if not ship_name:
            # Try to infer from filename
            parts = f.stem.replace("DOSSIER_", "").replace("_", " ")
            if any(kw in parts.lower() for kw in ["muse", "nova", "grandeur", "mars", "prestige", "discovery"]):
                ship_name = parts.split(" ")[1] if len(parts.split()) > 1 else parts

        if not ship_name or ship_name in existing_ships:
            continue

        line_name_match = re.search(r"(?:Cruise Line|Line|Supplier):\s*(.+?)[\n\r]", text, re.IGNORECASE)
        line_name = line_name_match.group(1).strip() if line_name_match else ""
        voyage_match = re.search(r"(?:Voyage|Itinerary|Route):\s*(.+?)[\n\r]", text, re.IGNORECASE)
        voyage = voyage_match.group(1).strip() if voyage_match else f.stem
        dep_match = re.search(r"(?:Departure|Sail Date|Departs?):\s*(.+?)[\n\r]", text, re.IGNORECASE)
        dep = dep_match.group(1).strip()[:30] if dep_match else ""

        ship_rows.append([line_name, ship_name, voyage[:60], dep, "", "", "", now_str, f.name, ""])
        existing_ships.add(ship_name)

    if ship_rows:
        # Ensure headers exist
        if len(existing) <= 1:
            ws.update("A1", [["Cruise Line", "Ship", "Voyage", "Departure", "Days", "Price",
                              "Availability", "Scraped At", "Source", "Notes"]])
        ws.append_rows(ship_rows, value_input_option="USER_ENTERED")
        log.info("Ship Intelligence: added %d new ships", len(ship_rows))
    else:
        log.info("Ship Intelligence: no new ships to add")


# ──────────────────────────────────────────────────────────────────── main

def main() -> int:
    log.info("sheets_wing_sync starting")
    try:
        spreadsheet = _bmc_spreadsheet()
        sync_dashboard(spreadsheet)
        sync_fare_log(spreadsheet)
        sync_action_tracker(spreadsheet)
        sync_dani_tracker(spreadsheet)
        sync_ship_intelligence(spreadsheet)
        log.info("sheets_wing_sync complete")
        return 0
    except Exception as e:
        log.error("sheets_wing_sync FAILED: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
