"""
Post-Booking Materials Pipeline
================================

Auto-generates the 4-document post-booking packet the moment a TESS booking
is confirmed, and uploads it to the client's Drive folder.

Docs (business/d2m_client_materials.py::generate_post_booking_packet):
  1. Pre-departure guide   (weather, packing, visas, health)
  2. Port-by-port dining   (3 recs per port)
  3. Excursion comparison  (GYG vs PE vs SS vs SEG, D2M pick)
  4. Emergency contact card (printable, laminate-ready)

Trigger: TESS `bookingStatus=confirmed` poll, diffed against a state file
(no TESS webhook exists — see docs/tess_and_tokens_raw.md). Runs on a timer
(systemd/post_booking_materials.timer, every 15 min) or on demand.

Drive upload target resolution:
  1. config/client_portals.json — match by client slug -> drive_folder
  2. Fallback shared folder (config/post_booking_fallback_folder.json), created
     on first run if it doesn't exist.

State file: OpsCenter/state/post_booking_materials_state.json
  {"<booking_id>": {"generated_at": iso, "client": str, "drive_uploaded": bool}}

CLI:
  python3 post_booking_materials_pipeline.py --poll                (TESS-driven, cron mode)
  python3 post_booking_materials_pipeline.py --client-test NAME --dossier PATH  (manual test, bypasses TESS)
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
sys.path.insert(0, str(THUNDERBIRD_DIR))

from business.d2m_client_materials import (
    generate_post_booking_packet,
    save_post_booking_packet,
    MaterialType,
)

logger = logging.getLogger("post_booking_pipeline")

STATE_FILE = THUNDERBIRD_DIR / "OpsCenter" / "state" / "post_booking_materials_state.json"
CLIENT_PORTALS_FILE = THUNDERBIRD_DIR / "config" / "client_portals.json"
FALLBACK_FOLDER_FILE = THUNDERBIRD_DIR / "config" / "post_booking_fallback_folder.json"
LOG_FILE = THUNDERBIRD_DIR / "logs" / "post_booking_pipeline.log"
OUTPUT_ROOT = THUNDERBIRD_DIR / "output" / "client_materials" / "post_booking"


# ============================================================================
# State
# ============================================================================

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


# ============================================================================
# Drive upload (direct googleapiclient — same pattern as scripts/drive_upload_robust.py)
# ============================================================================

_drive_service = None


def get_drive_service():
    global _drive_service
    if _drive_service is not None:
        return _drive_service
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    token_file = THUNDERBIRD_DIR / "drive_token.json"
    if not token_file.exists():
        raise RuntimeError(f"Drive token not found at {token_file}")

    creds = Credentials.from_authorized_user_file(str(token_file),
                                                    ["https://www.googleapis.com/auth/drive"])
    if creds.expired:
        creds.refresh(Request())
        token_file.write_text(creds.to_json())

    _drive_service = build("drive", "v3", credentials=creds)
    return _drive_service


def upload_to_drive(local_path: str, folder_id: str, name: Optional[str] = None) -> dict:
    import mimetypes
    from googleapiclient.http import MediaFileUpload

    path = Path(local_path)
    service = get_drive_service()
    metadata = {"name": name or path.name, "parents": [folder_id]}
    mime_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    media = MediaFileUpload(str(path), mimetype=mime_type, resumable=True)
    uploaded = (
        service.files()
        .create(body=metadata, media_body=media, fields="id, name, webViewLink")
        .execute()
    )
    return uploaded


def verify_drive_upload(folder_id: str, file_name: str) -> bool:
    """Independent verification: list the folder and confirm the file is actually there.

    Per Obstacle-Routing & Independent Verification Protocol — never trust the
    upload API's own "success" response alone.
    """
    service = get_drive_service()
    resp = service.files().list(
        q=f"'{folder_id}' in parents and name = '{file_name}' and trashed = false",
        fields="files(id, name)",
    ).execute()
    return len(resp.get("files", [])) > 0


def resolve_drive_folder(client_slug: str) -> str:
    """Match client to a registered Drive folder; fall back to a shared holding folder."""
    if CLIENT_PORTALS_FILE.exists():
        registry = json.loads(CLIENT_PORTALS_FILE.read_text())
        for _, entry in registry.items():
            if not isinstance(entry, dict):
                continue
            if entry.get("slug", "").lower() == client_slug.lower() or \
               client_slug.lower() in entry.get("slug", "").lower():
                folder_id = entry.get("drive_folder")
                if folder_id:
                    return folder_id

    # Fallback: shared "Post-Booking Materials" folder, created once and cached.
    if FALLBACK_FOLDER_FILE.exists():
        fallback = json.loads(FALLBACK_FOLDER_FILE.read_text())
        if fallback.get("drive_folder"):
            return fallback["drive_folder"]

    service = get_drive_service()
    folder = service.files().create(
        body={"name": "D2M Post-Booking Materials", "mimeType": "application/vnd.google-apps.folder"},
        fields="id",
    ).execute()
    folder_id = folder["id"]
    FALLBACK_FOLDER_FILE.parent.mkdir(parents=True, exist_ok=True)
    FALLBACK_FOLDER_FILE.write_text(json.dumps({
        "drive_folder": folder_id,
        "created_at": datetime.now().isoformat(),
        "note": "Auto-created holding folder — client not yet in config/client_portals.json",
    }, indent=2))
    logger.info(f"Created fallback Drive folder: {folder_id}")
    return folder_id


# ============================================================================
# Core pipeline
# ============================================================================

def run_for_booking(client_name: str, client_slug: str, booking_id: str,
                     booking_data: dict, upload: bool = True) -> dict:
    """Generate the 4-doc packet for one confirmed booking and (optionally) push to Drive.

    Returns a result dict: {docs: {...}, uploaded: {...}, errors: [...]}.
    """
    result = {"client": client_name, "booking_id": booking_id, "docs": {}, "uploaded": {}, "errors": []}

    materials = generate_post_booking_packet(client_name, booking_data)
    output_dir = OUTPUT_ROOT / client_slug
    saved = save_post_booking_packet(client_name, materials, output_dir=str(output_dir))
    result["docs"] = saved

    expected = [MaterialType.PRE_DEPARTURE.value, MaterialType.PORT_DINING_GUIDE.value,
                MaterialType.EXCURSION_GRID.value, MaterialType.EMERGENCY_CARD.value]
    missing = [m for m in expected if not saved.get(m)]
    if missing:
        result["errors"].append(f"Missing docs: {missing}")

    if upload:
        try:
            folder_id = resolve_drive_folder(client_slug)
            for mat_type, files in saved.items():
                html_path = files.get("html")
                if not html_path:
                    continue
                uploaded = upload_to_drive(html_path, folder_id)
                verified = verify_drive_upload(folder_id, uploaded["name"])
                result["uploaded"][mat_type] = {
                    "file_id": uploaded["id"],
                    "web_link": uploaded.get("webViewLink"),
                    "verified": verified,
                }
                if files.get("pdf"):
                    uploaded_pdf = upload_to_drive(files["pdf"], folder_id)
                    verified_pdf = verify_drive_upload(folder_id, uploaded_pdf["name"])
                    result["uploaded"][f"{mat_type}_pdf"] = {
                        "file_id": uploaded_pdf["id"],
                        "web_link": uploaded_pdf.get("webViewLink"),
                        "verified": verified_pdf,
                    }
        except Exception as e:
            result["errors"].append(f"Drive upload failed: {e}")
            logger.error(f"Drive upload failed for {client_name}: {e}")

    return result


def poll_tess_confirmed_bookings(lookback_pages: int = 3) -> dict:
    """Poll TESS for confirmed bookings, diff against state, process new ones.

    Requires a valid tess_token.json (see core/booking/thunderbird_tess.py --authorize).
    Booking->trip resolution and port extraction is best-effort from TESS trip data;
    where TESS lacks port-level granularity (typical for cruise line-items), the
    dossier is the fallback source — this poll mode only handles what TESS itself
    can supply and flags anything requiring a dossier cross-reference.
    """
    from core.booking.thunderbird_tess import TESSClient

    client = TESSClient()
    state = load_state()
    results = {"processed": [], "skipped_already_done": 0, "errors": []}

    for page in range(1, lookback_pages + 1):
        resp = client.list_bookings(page_number=page, page_size=50, bookingStatus="confirmed")
        if resp.get("error"):
            results["errors"].append(resp["error"])
            logger.error(f"TESS poll error: {resp['error']}")
            break

        items = resp.get("Items", [])
        if not items:
            break

        for booking in items:
            booking_id = str(booking.get("BookingID") or booking.get("bookingID") or booking.get("id", ""))
            if not booking_id:
                continue
            if booking_id in state:
                results["skipped_already_done"] += 1
                continue

            client_name = booking.get("ClientName") or booking.get("clientName") or "Unknown Client"
            client_slug = client_name.lower().replace(" ", "-").replace(",", "")
            booking_data = {
                "destination": booking.get("TripDescription", ""),
                "start_date": booking.get("StartDate", ""),
                "end_date": booking.get("EndDate", ""),
                "ship": booking.get("SupplierName", ""),
                "booking_number": booking.get("BookingNumber", booking_id),
                "ports": [],  # TESS line items don't carry port granularity — needs dossier cross-ref
                "confirmed_excursions": [],
            }

            result = run_for_booking(client_name, client_slug, booking_id, booking_data)
            results["processed"].append(result)

            state[booking_id] = {
                "generated_at": datetime.now().isoformat(),
                "client": client_name,
                "drive_uploaded": bool(result["uploaded"]),
                "errors": result["errors"],
            }

        if len(items) < 50:
            break

    save_state(state)
    return results


# ============================================================================
# CLI
# ============================================================================

def main():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
    )

    parser = argparse.ArgumentParser(description="Post-Booking Materials Pipeline")
    parser.add_argument("--poll", action="store_true", help="Poll TESS for new confirmed bookings")
    parser.add_argument("--client-test", metavar="NAME", help="Manually run the pipeline for one client")
    parser.add_argument("--booking-data-json", metavar="PATH", help="Path to a JSON file with booking_data (for --client-test)")
    parser.add_argument("--booking-id", default=None, help="Booking ID/number for --client-test")
    parser.add_argument("--no-upload", action="store_true", help="Skip Drive upload (local generation only)")
    args = parser.parse_args()

    if args.poll:
        results = poll_tess_confirmed_bookings()
        print(json.dumps(results, indent=2, default=str))
    elif args.client_test:
        if not args.booking_data_json:
            print("--client-test requires --booking-data-json PATH", file=sys.stderr)
            sys.exit(1)
        booking_data = json.loads(Path(args.booking_data_json).read_text())
        slug = args.client_test.lower().replace(" ", "-").replace(",", "").replace("&", "and")
        booking_id = args.booking_id or f"TEST-{slug}"
        result = run_for_booking(args.client_test, slug, booking_id, booking_data,
                                  upload=not args.no_upload)
        print(json.dumps(result, indent=2, default=str))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
