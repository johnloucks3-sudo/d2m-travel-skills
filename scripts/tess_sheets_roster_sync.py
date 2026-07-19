"""
tess_sheets_roster_sync — sync the TESS CRM client roster to a Google Sheet.

Usage:
    python3 scripts/tess_sheets_roster_sync.py --dry-run [--out rows.json]
    python3 scripts/tess_sheets_roster_sync.py

Dry-run: fetches clients from TESS (if reachable) and emits JSON to --out or
stdout.  If TESS is unreachable (no token, network error) emits an empty-but-
valid JSON object and a clear stderr note — never crashes, never fabricates rows.

Live run: creates the spreadsheet on first use (id persisted to
config/tess_roster_sheet_config.json) then does an idempotent full
clear+rewrite of the "Client Roster" tab keyed by clientID.  Re-running is
always safe.  TESS is the system of record; this script is read-only against it.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "tess_roster_sheet_config.json"
SHEET_TITLE = "D2M Client Roster"
TAB_NAME = "Client Roster"

# Stable column order; clientID is the idempotent key column.
SHEET_COLUMNS = [
    "clientID",
    "firstName",
    "lastName",
    "email",
    "phone",
    "city",
    "state",
    "country",
    "birthDate",
    "anniversaryDate",
    "marketable",
    "createdDate",
    "modifiedDate",
]

def _safe(val) -> str:
    """Coerce a value to str, returning '' for None/empty."""
    return "" if val is None else str(val)


def _normalize_client(raw: dict) -> dict:
    """Map a nested TESS client record to our canonical SHEET_COLUMNS shape.

    TESS response shape (actual):
      ClientID         → {'ID': int, '$ProtectedEncrypted': str}
      Contact          → {'FirstName', 'LastName', 'Address', 'Telephones',
                          'EmailAddresses', ...}
      BirthDate        → ISO datetime str or None
      AnniversaryDate  → ISO datetime str or None
      Marketable       → bool
      CreatedDateTimeUTC → ISO datetime str
    """
    row: dict = {col: "" for col in SHEET_COLUMNS}

    # clientID — extract numeric ID from the ProtectedEncrypted wrapper
    cid = raw.get("ClientID")
    if isinstance(cid, dict):
        row["clientID"] = _safe(cid.get("ID"))
    elif cid is not None:
        row["clientID"] = _safe(cid)

    # name, address, contact details live under Contact
    contact = raw.get("Contact") or {}
    row["firstName"] = _safe(contact.get("FirstName"))
    row["lastName"] = _safe(contact.get("LastName"))

    addr = contact.get("Address") or {}
    row["city"] = _safe(addr.get("City"))
    row["state"] = _safe(addr.get("State"))
    country_info = (addr.get("PostalCode") or {}).get("Country") or {}
    row["country"] = _safe(country_info.get("CountryCode") or addr.get("Country"))

    # primary email
    try:
        row["email"] = _safe(
            contact["EmailAddresses"]["Primary"]["ContactDetailValue"]["Value"]
        )
    except (KeyError, TypeError):
        pass

    # primary phone
    try:
        row["phone"] = _safe(
            contact["Telephones"]["Primary"]["ContactDetailValue"]["Value"]
        )
    except (KeyError, TypeError):
        pass

    # top-level scalar fields
    row["birthDate"] = _safe(raw.get("BirthDate"))
    row["anniversaryDate"] = _safe(raw.get("AnniversaryDate"))
    row["marketable"] = _safe(raw.get("Marketable"))
    row["createdDate"] = _safe(raw.get("CreatedDateTimeUTC"))
    row["modifiedDate"] = _safe(raw.get("ModifiedDateTimeUTC") or raw.get("LastModifiedDateTimeUTC"))

    return row


def _fetch_all_clients() -> list:
    """Pull all clients from TESS via paginated list_clients().  Read-only."""
    from core.booking.thunderbird_tess import TESSClient
    client = TESSClient()
    rows = []
    page = 1
    page_size = 100
    while True:
        resp = client.list_clients(page_number=page, page_size=page_size)
        items = resp.get("Items") or resp.get("items") or []
        if not items:
            break
        rows.extend(items)
        total = (resp.get("CountFiltered") or resp.get("countFiltered")
                 or resp.get("CountUnfiltered") or resp.get("countUnfiltered") or 0)
        if not total or len(rows) >= total or len(items) < page_size:
            break
        page += 1
    return [_normalize_client(r) for r in rows]


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------

def _dry_run(out_path: str) -> int:
    try:
        rows = _fetch_all_clients()
    except Exception as e:
        print(
            f"[dry-run] TESS unreachable ({e}); emitting empty-but-valid roster.",
            file=sys.stderr,
        )
        rows = []

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "columns": SHEET_COLUMNS,
        "count": len(rows),
        "rows": rows,
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[dry-run] {len(rows)} rows → {out_path}")
    else:
        print(text)
    return 0


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


# ---------------------------------------------------------------------------
# Sheet helpers
# ---------------------------------------------------------------------------

def _create_sheet(sheets):
    body = {
        "properties": {"title": SHEET_TITLE},
        "sheets": [{"properties": {"title": TAB_NAME}}],
    }
    ss = sheets.spreadsheets().create(
        body=body, fields="spreadsheetId,spreadsheetUrl"
    ).execute()
    return ss["spreadsheetId"], ss["spreadsheetUrl"]


def _ensure_tab_exists(sheets, sheet_id: str) -> None:
    """Add TAB_NAME if the sheet was created externally without it."""
    meta = sheets.spreadsheets().get(
        spreadsheetId=sheet_id, fields="sheets.properties.title"
    ).execute()
    existing = {s["properties"]["title"] for s in meta.get("sheets", [])}
    if TAB_NAME not in existing:
        sheets.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": TAB_NAME}}}]},
        ).execute()


# ---------------------------------------------------------------------------
# Live sync
# ---------------------------------------------------------------------------

def _live_sync() -> int:
    from api.thunderbird_google_auth import get_sheets
    sheets = get_sheets()

    cfg = _load_config()
    sheet_id = cfg.get("spreadsheet_id")
    url = cfg.get("spreadsheet_url", "")
    created = False

    if not sheet_id:
        sheet_id, url = _create_sheet(sheets)
        cfg.update({
            "spreadsheet_id": sheet_id,
            "spreadsheet_url": url,
            "tab": TAB_NAME,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        _save_config(cfg)
        created = True
    else:
        _ensure_tab_exists(sheets, sheet_id)

    rows = _fetch_all_clients()
    values = [SHEET_COLUMNS] + [
        [r.get(c, "") for c in SHEET_COLUMNS] for r in rows
    ]

    # Idempotent full rewrite: clear the tab, then write header + data rows.
    sheets.spreadsheets().values().clear(
        spreadsheetId=sheet_id, range=TAB_NAME
    ).execute()
    sheets.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{TAB_NAME}!A1",
        valueInputOption="RAW",
        body={"values": values},
    ).execute()

    cfg["last_sync_at"] = datetime.now(timezone.utc).isoformat()
    cfg["last_row_count"] = len(rows)
    _save_config(cfg)

    print(f"{'Created' if created else 'Updated'} Sheet: {url}")
    print(f"Wrote {len(rows)} rows to tab '{TAB_NAME}'.")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Sync TESS CRM client roster to the Google Sheet 'Client Roster' tab. "
            "Read-only against TESS; idempotent against Google Sheets."
        )
    )
    ap.add_argument(
        "--dry-run", action="store_true",
        help="Fetch clients from TESS and emit JSON — no Google credentials needed.",
    )
    ap.add_argument(
        "--out", default="",
        help="Dry-run output file path (default: stdout).",
    )
    args = ap.parse_args(argv)

    if args.dry_run:
        return _dry_run(args.out)
    return _live_sync()


if __name__ == "__main__":
    raise SystemExit(main())
