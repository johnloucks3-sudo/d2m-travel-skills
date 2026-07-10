#!/usr/bin/env python3
"""
fare_watch_artifacts_daily_refresh.py — keeps all 3 fare-watch HTML artifacts
current and re-uploads them to Drive (update-in-place, stable links), then
writes a state file the morning brief reads for its Fare Watch section.

Runs as ExecStartPre on thunderbird-morning-brief.service, after the Loucks
(04:30 MT) and Spencer (05:00 MT) daily recheck timers have already run and
before the 06:00 MT brief generates -- so results are same-day fresh.

Artifacts:
  1. output/loucks_silvernova_2027_flight_options.html
  2. output/spencer_grandtour_2027_flight_options.html
  3. output/airfare_dashboard.html (regenerated here from fare_watches.json
     cache -- cheap, no live rescan)

Never raises: a Drive/network hiccup must not block the morning brief from
generating. Partial results (some artifacts uploaded, some not) are still
written to the state file with per-artifact status.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))

STATE_FILE = ROOT / "OpsCenter" / "state" / "fare_watch_artifacts_latest.json"
LOG_FILE = ROOT / "logs" / "fare_watch_artifacts_daily_refresh.log"

ARTIFACTS = [
    {
        "key": "loucks_silvernova",
        "label": "Loucks Silver Nova 2027 — Flight Routing Options",
        "path": ROOT / "output" / "loucks_silvernova_2027_flight_options.html",
        "drive_name": "Loucks Silver Nova 2027 - Flight Routing Options.html",
        "watch_ids": {"den-muc-vce", "ath-ist-den", "ath-muc-den", "den-vce-direct"},
    },
    {
        "key": "spencer_grandtour",
        "label": "Spencer Grand Tour 2027 — Flight Options All Legs",
        "path": ROOT / "output" / "spencer_grandtour_2027_flight_options.html",
        "drive_name": "Spencer Grand Tour 2027 - Flight Options All Legs.html",
        "watch_ids": {
            "spencer-leg1-den-fco-tim-business-jun2027",
            "spencer-leg1-den-fco-yaggispencer-pe-jun2027",
            "spencer-leg2-fco-den-tim-business-jun2027",
            "spencer-leg3-zrh-den-yaggispencer-pe-jul2027",
        },
    },
    {
        "key": "airfare_dashboard",
        "label": "Thunderbird Airfare Dashboard",
        "path": ROOT / "output" / "airfare_dashboard.html",
        "drive_name": "Thunderbird Airfare Dashboard.html",
        "watch_ids": None,  # all watches
    },
]


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}] {msg}\n")


def _regenerate_dashboard() -> bool:
    """Cheap regeneration from fare_watches.json cache -- no live rescan."""
    try:
        from scripts.daily_airfare_scan import _load_watches, _infer_cabin, _generate_dashboard
        watches = _load_watches()
        all_results = [
            {
                "watch": w,
                "prices": {
                    "source": "fare_watches.json (cached)",
                    "cabin": _infer_cabin(w),
                    "best_price_pp": w.get("current_price_pp"),
                    "duration_min": None, "airline": None, "stops": None,
                    "url": "", "history": [],
                },
                "centrav_ok": False, "centrav_url": "",
            }
            for w in watches
        ]
        _generate_dashboard(all_results)
        _log(f"dashboard regenerated from {len(watches)} watches")
        return True
    except Exception as e:
        _log(f"dashboard regeneration FAILED: {e}")
        return False


def _latest_prices(watch_ids: set | None) -> list[dict]:
    """Pull the most recent fare_history.json entry per relevant watch_id."""
    hist_file = ROOT / "core" / "travel" / "data" / "fare_history.json"
    if not hist_file.exists():
        return []
    try:
        history = json.loads(hist_file.read_text())
    except Exception:
        return []
    latest: dict[str, dict] = {}
    for e in history:
        wid = e.get("watch_id")
        if watch_ids is not None and wid not in watch_ids:
            continue
        if wid not in latest or e.get("timestamp", "") > latest[wid].get("timestamp", ""):
            latest[wid] = e
    return sorted(latest.values(), key=lambda e: e.get("watch_id", ""))


def _upload_or_update(local_path: Path, drive_name: str) -> dict:
    """Update-in-place if a file with this name already exists in Drive root
    (keeps the link stable across days); otherwise create it. Never raises --
    returns {"ok": False, "error": ...} on any failure."""
    try:
        from core.booking.post_booking_materials_pipeline import get_drive_service
        import mimetypes
        from googleapiclient.http import MediaFileUpload

        service = get_drive_service()
        mime_type = mimetypes.guess_type(str(local_path))[0] or "text/html"
        media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=True)

        existing = service.files().list(
            q=f"name = '{drive_name}' and trashed = false",
            fields="files(id, name)",
        ).execute().get("files", [])

        if existing:
            file_id = existing[0]["id"]
            updated = service.files().update(
                fileId=file_id, media_body=media, fields="id, name, webViewLink",
            ).execute()
        else:
            updated = service.files().create(
                body={"name": drive_name}, media_body=media, fields="id, name, webViewLink",
            ).execute()

        return {"ok": True, "id": updated["id"], "link": updated.get("webViewLink")}
    except Exception as e:
        _log(f"Drive upload FAILED for {drive_name}: {e}")
        return {"ok": False, "error": str(e)}


def main() -> None:
    _regenerate_dashboard()

    results = {}
    for a in ARTIFACTS:
        entry = {"label": a["label"], "as_of": datetime.now(timezone.utc).isoformat()}
        if not a["path"].exists():
            entry["upload"] = {"ok": False, "error": "local file not found"}
        else:
            entry["upload"] = _upload_or_update(a["path"], a["drive_name"])
        entry["latest_prices"] = _latest_prices(a["watch_ids"])
        results[a["key"]] = entry
        _log(f"{a['key']}: upload_ok={entry['upload'].get('ok')} "
             f"latest_prices_count={len(entry['latest_prices'])}")

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(results, indent=2, default=str))
    tmp.replace(STATE_FILE)
    _log(f"state written to {STATE_FILE}")


if __name__ == "__main__":
    main()
