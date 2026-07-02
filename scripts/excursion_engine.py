#!/usr/bin/env python3
"""
excursion_engine.py — E-180 excursion research trigger engine.
For each active booking entering the 180-day window before departure,
triggers cruise_excursion_scan.py and stages a notification draft to johnloucks3.

State: OpsCenter/state/excursion_engine_state.json
"""
import argparse
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, "/home/john/Thunderbird")

THUNDERBIRD = Path("/home/john/Thunderbird")
STATE_FILE = THUNDERBIRD / "OpsCenter" / "state" / "excursion_engine_state.json"
DRAFTS_DIR = THUNDERBIRD / "drafts"
TO_EMAIL = "johnloucks3@gmail.com"


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def build_body_html(
    client_name: str,
    cruise_line: str,
    ship: str,
    departure: date,
    days_to_departure: int,
    scan_status: str,
) -> str:
    dep_str = departure.strftime("%B %-d, %Y")
    return f"""<h2 style="color:#4a90d9;font-family:Georgia,serif;font-size:20px;">Excursion Research — {client_name}</h2>
<p style="color:#a8c4f0;font-family:Georgia,serif;font-size:13px;">{cruise_line} · {ship} · Departing {dep_str} ({days_to_departure} days)</p>
<hr style="border:1px solid #1a3a6b;margin:16px 0;">
<p style="color:#e8f1ff;font-family:Georgia,serif;font-size:14px;">Excursion research has been triggered for {client_name}'s upcoming voyage. This is an internal notification — no client action required.</p>
<table style="width:100%;border-collapse:collapse;">
  <tr>
    <td style="color:#a8c4f0;font-family:Georgia,serif;font-size:13px;padding:6px 0;width:40%;">Client</td>
    <td style="color:#e8f1ff;font-family:Georgia,serif;font-size:13px;padding:6px 0;">{client_name}</td>
  </tr>
  <tr>
    <td style="color:#a8c4f0;font-family:Georgia,serif;font-size:13px;padding:6px 0;">Ship</td>
    <td style="color:#e8f1ff;font-family:Georgia,serif;font-size:13px;padding:6px 0;">{ship}</td>
  </tr>
  <tr>
    <td style="color:#a8c4f0;font-family:Georgia,serif;font-size:13px;padding:6px 0;">Departure</td>
    <td style="color:#e8f1ff;font-family:Georgia,serif;font-size:13px;padding:6px 0;">{dep_str} ({days_to_departure} days)</td>
  </tr>
  <tr>
    <td style="color:#a8c4f0;font-family:Georgia,serif;font-size:13px;padding:6px 0;">Scan Status</td>
    <td style="color:#e8f1ff;font-family:Georgia,serif;font-size:13px;padding:6px 0;">{scan_status}</td>
  </tr>
</table>
<p style="color:#a8c4f0;font-family:Georgia,serif;font-size:12px;margin-top:20px;font-style:italic;">Wing internal. TP 2.1 — E-180 excursion research trigger.</p>"""


def run_engine(window_days: int = 180, dry_run: bool = False, force: bool = False) -> None:
    from core.booking.thunderbird_tp_scheduler import scan_dossiers
    from scripts.d2m_email_builder import build_email_html, stage_draft

    today = date.today()
    state = load_state()
    entries: dict = state.get("entries", {})

    records = scan_dossiers()
    evaluated = 0
    triggered = 0

    in_window = [
        r for r in records
        if r.status == "active"
        and r.departure is not None
        and 0 <= (r.departure - today).days <= window_days
    ]

    for rec in in_window:
        evaluated += 1
        key = str(rec.path)
        days_left = (rec.departure - today).days

        if key in entries and not force:
            print(f"[SKIP] {rec.client} — already processed (use --force to re-run)")
            continue

        # Determine scan log path
        safe_client = "".join(c if c.isalnum() else "_" for c in rec.client)
        log_path = DRAFTS_DIR / f"excursion_scan_{safe_client}_{today.isoformat()}.log"
        DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

        scan_exit = None
        if dry_run:
            scan_status = "Dry run — not executed"
            print(f"[DRY RUN] Would trigger excursion scan for {rec.client} (departs {rec.departure}, {days_left}d)")
        else:
            print(f"[SCAN] Running cruise_excursion_scan.py for {rec.client}...")
            try:
                with open(log_path, "w", encoding="utf-8") as log_fh:
                    result = subprocess.run(
                        [sys.executable, str(THUNDERBIRD / "scripts" / "cruise_excursion_scan.py")],
                        stdout=log_fh,
                        stderr=subprocess.STDOUT,
                        timeout=120,
                        cwd=str(THUNDERBIRD),
                    )
                scan_exit = result.returncode
                if scan_exit == 0:
                    scan_status = "Scan completed (exit 0)"
                else:
                    scan_status = f"Scan failed (exit {scan_exit})"
                print(f"[SCAN] {rec.client}: {scan_status}")
            except subprocess.TimeoutExpired:
                scan_exit = None
                scan_status = "Scan timed out (120s)"
                print(f"[SCAN] {rec.client}: timed out after 120s")
            except Exception as exc:
                scan_exit = None
                scan_status = f"Scan error: {exc}"
                print(f"[SCAN] {rec.client}: error — {exc}")

        # Notification: LOG-ONLY — no Gmail draft.
        # (Commander directive 2026-07-02: these excursion notification drafts were
        # flooding johnloucks3 — 599 accumulated — and are extraneous. The scan above
        # is the useful work; the notification is recorded to a log, not the mailbox.)
        subject = f"[Wing] Excursion Research Triggered — {rec.client} ({days_left}d to departure)"
        notif_log = THUNDERBIRD / "logs" / "excursion_notifications.log"
        notif_log.parent.mkdir(parents=True, exist_ok=True)
        with open(notif_log, "a", encoding="utf-8") as _nf:
            _nf.write(f"{datetime.utcnow().isoformat()} | {subject} | {scan_status}\n")
        print(f"[NOTIFY] {rec.client}: logged (no Gmail draft) — {scan_status}")

        entries[key] = {
            "client": rec.client,
            "departure": str(rec.departure),
            "scan_exit": scan_exit,
            "staged_at": datetime.utcnow().isoformat(),
            "scan_log": str(log_path),
        }
        triggered += 1

    state["last_run"] = datetime.utcnow().isoformat()
    state["evaluated"] = evaluated
    state["triggered"] = triggered
    state["entries"] = entries
    save_state(state)

    print(f"\n[DONE] evaluated={evaluated} triggered={triggered} window={window_days}d dry_run={dry_run}")


def main() -> None:
    parser = argparse.ArgumentParser(description="E-180 excursion research trigger engine")
    parser.add_argument("--dry-run", action="store_true", help="Scan window, build drafts locally, skip Gmail staging and scan")
    parser.add_argument("--force", action="store_true", help="Re-process entries already in state")
    parser.add_argument("--window", type=int, default=180, metavar="DAYS", help="Departure window in days (default 180)")
    args = parser.parse_args()
    run_engine(window_days=args.window, dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
