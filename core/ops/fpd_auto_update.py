#!/usr/bin/env python3
"""
FPD Auto-Update — M-041
Polls TESS bookings for payment status changes and updates dossier frontmatter.
Runs every 15 minutes via systemd timer.

What it does:
  1. Calls TESS /Booking endpoint (when auth is live)
  2. Looks for bookings with recent payment events (balance change, status change)
  3. Updates the matching dossier's fpd_status / fpd_paid fields in frontmatter
  4. Logs the change to logs/fpd_events.jsonl
  5. Triggers bryana_dashboard generator so the dashboard reflects the change
"""
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

THUNDERBIRD = Path("/home/john/Thunderbird")
DOSSIER_DIR = THUNDERBIRD / "dossiers"
FPD_LOG = THUNDERBIRD / "logs" / "fpd_events.jsonl"
VENV_PYTHON = THUNDERBIRD / ".venv" / "bin" / "python3"


def log_event(event: dict):
    FPD_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(FPD_LOG, "a") as f:
        f.write(json.dumps({**event, "ts": datetime.now().isoformat()}) + "\n")
    print(f"[FPD] {event}")


def get_tess_bookings() -> list[dict]:
    """Pull bookings from TESS. Returns list of booking dicts or empty list on auth failure."""
    try:
        from core.booking.thunderbird_tess import TESSClient
        t = TESSClient()
        result = t.list_bookings(page_size=100)
        if "error" in result:
            print(f"[FPD] TESS auth offline: {result['error']}")
            return []
        items = result.get("Items", [])
        print(f"[FPD] Pulled {len(items)} bookings from TESS")
        return items
    except Exception as e:
        print(f"[FPD] TESS error: {e}")
        return []


def extract_booking_payment_state(booking: dict) -> dict:
    """Extract relevant payment fields from a TESS booking object."""
    return {
        "booking_id": booking.get("BookingId") or booking.get("bookingId"),
        "booking_number": booking.get("BookingNumber") or booking.get("bookingNumber"),
        "status": booking.get("BookingStatus") or booking.get("bookingStatus"),
        "balance_due": booking.get("BalanceDue") or booking.get("balanceDue"),
        "total_price": booking.get("TotalPrice") or booking.get("totalPrice"),
        "final_payment_date": booking.get("FinalPaymentDate") or booking.get("finalPaymentDate"),
        "tour_operator": booking.get("TourOperatorName") or booking.get("tourOperatorName", ""),
        "trip_description": booking.get("TripDescription") or booking.get("tripDescription", ""),
    }


def read_dossier_frontmatter(path: Path) -> tuple[dict, str]:
    """Read frontmatter + body. Returns (fm_dict, full_text)."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.startswith("---"):
        return {}, text
    end = text.find("---", 3)
    if end == -1:
        return {}, text
    fm_raw = text[3:end].strip()
    fm = {}
    for line in fm_raw.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm, text


def update_dossier_frontmatter(path: Path, updates: dict) -> bool:
    """Update specific frontmatter fields in a dossier. Returns True if changed."""
    fm, text = read_dossier_frontmatter(path)
    if not fm:
        return False

    changed = False
    for k, v in updates.items():
        old = fm.get(k)
        if str(old) != str(v):
            fm[k] = str(v)
            changed = True

    if not changed:
        return False

    # Rebuild frontmatter block
    fm_lines = [f"{k}: {v}" for k, v in fm.items()]
    fm_block = "---\n" + "\n".join(fm_lines) + "\n---"

    # Replace existing frontmatter in text
    end = text.find("---", 3)
    new_text = fm_block + text[end + 3:]
    path.write_text(new_text, encoding="utf-8")
    return True


def match_booking_to_dossier(booking_state: dict) -> Path | None:
    """Try to find the dossier that matches this TESS booking."""
    booking_num = str(booking_state.get("booking_number") or "").strip()
    if not booking_num:
        return None

    for md in DOSSIER_DIR.glob("*.md"):
        if md.name == "CLAUDE.md":
            continue
        try:
            text = md.read_text(encoding="utf-8", errors="ignore")
            if booking_num in text:
                return md
        except Exception:
            continue
    return None


def check_payment_events(bookings: list[dict]) -> int:
    """Process bookings, update dossiers when payment changes detected. Returns event count."""
    events = 0
    for booking in bookings:
        state = extract_booking_payment_state(booking)
        balance = state.get("balance_due")
        status = state.get("status", "")

        # Detect a paid booking (balance = 0 or status contains paid/complete)
        is_paid = (
            (balance is not None and float(str(balance).replace(",", "") or "1") <= 0)
            or any(word in str(status).lower() for word in ("paid", "complete", "confirmed"))
        )

        dossier = match_booking_to_dossier(state)
        if not dossier:
            continue

        updates = {}
        if is_paid:
            updates["fpd_status"] = "PAID"
            updates["fpd_paid_confirmed"] = datetime.now().strftime("%Y-%m-%d")
        else:
            updates["fpd_status"] = "PENDING"
            updates["balance_due"] = state.get("balance_due", "")

        if updates:
            changed = update_dossier_frontmatter(dossier, updates)
            if changed:
                log_event({
                    "booking_id": state["booking_id"],
                    "booking_number": state["booking_number"],
                    "dossier": dossier.name,
                    "updates": updates,
                    "trip": state.get("trip_description", ""),
                })
                events += 1

    return events


def trigger_dashboard_refresh():
    """Regenerate bryana/data.json so dashboard reflects latest state."""
    try:
        result = subprocess.run(
            [str(VENV_PYTHON), str(THUNDERBIRD / "core" / "ops" / "bryana_dashboard.py")],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            print("[FPD] Dashboard refresh triggered")
        else:
            print(f"[FPD] Dashboard refresh failed: {result.stderr[:200]}")
    except Exception as e:
        print(f"[FPD] Dashboard refresh error: {e}")


def main():
    print(f"[FPD Auto-Update] Starting — {datetime.now().isoformat()}")

    bookings = get_tess_bookings()
    if not bookings:
        print("[FPD] No TESS data available — skipping payment scan. Run TESS re-auth to enable.")
        # Still refresh the dashboard (shows TESS OFFLINE status)
        trigger_dashboard_refresh()
        return 0

    events = check_payment_events(bookings)
    print(f"[FPD] Payment scan complete — {events} dossier updates")

    trigger_dashboard_refresh()

    if events > 0:
        # Write a marker so the dashboard can show "payment confirmed today"
        marker = THUNDERBIRD / "logs" / "last_fpd_event.json"
        marker.write_text(json.dumps({
            "ts": datetime.now().isoformat(),
            "events_count": events,
        }))

    return 0


if __name__ == "__main__":
    sys.exit(main())
