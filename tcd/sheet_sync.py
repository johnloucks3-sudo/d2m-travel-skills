"""
sheet_sync — write the current TCD dataset to the Google Sheet data plane.

Usage:
    python -m tcd.sheet_sync --dry-run [--out rows.json]   # offline, no Google
    python -m tcd.sheet_sync                               # live: create/update Sheet

Dry-run collects every item, enriches it (stage + source deep-link), and writes
the rows as JSON (to --out or stdout) so you can confirm coverage and that every
row has a link — no credentials, no writes to Google.

Live run creates the Sheet on first use (id persisted to
config/tcd_sheet_config.json) and thereafter does an idempotent full
clear+rewrite of the ``Items`` tab keyed by ``id`` — re-running is always safe.
"""
import argparse
import json
import sys
from datetime import datetime, timezone

from . import _imports
from .collectors import collect_all
from .item_model import SHEET_COLUMNS

ROOT = _imports.ROOT
CONFIG_PATH = ROOT / "config" / "tcd_sheet_config.json"
SHEET_TITLE = "Thunderbird Commander Desktop — Items"
TAB_NAME = "Items"

# Phase 3 — Intel / Tech Scans / Next 7 Days read-only dashboard tabs, same
# spreadsheet, same SHEET_COLUMNS shape (so Looker Studio reads them exactly
# like the Items tab). Each entry: (tab name, section.collect_* function).
SECTION_TABS = ("Intel", "TechScans", "Next7")


def collect_rows(include_gmail: bool = True, include_keep: bool = True,
                 include_sms: bool = True) -> list:
    """List of SHEET_COLUMNS-keyed dicts, one per item."""
    return [item.to_dict() for item in
            collect_all(include_gmail=include_gmail, include_keep=include_keep,
                       include_sms=include_sms)]


def _dry_run(out_path: str, include_gmail: bool, include_keep: bool, include_sms: bool) -> int:
    rows = collect_rows(include_gmail=include_gmail, include_keep=include_keep,
                        include_sms=include_sms)
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
        missing = [r["id"] for r in rows if not r.get("link")]
        print(f"[dry-run] {len(rows)} rows → {out_path}")
        print(f"[dry-run] rows missing a link: {len(missing)}"
              + (f" — {missing[:5]}" if missing else " (all rows linked ✓)"))
    else:
        print(text)
    return 0


def _load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


def _create_sheet(sheets):
    body = {
        "properties": {"title": SHEET_TITLE},
        "sheets": [{"properties": {"title": TAB_NAME}}],
    }
    ss = sheets.spreadsheets().create(
        body=body, fields="spreadsheetId,spreadsheetUrl").execute()
    return ss["spreadsheetId"], ss["spreadsheetUrl"]


def _live_sync(include_gmail: bool, include_keep: bool = True, include_sms: bool = True,
               skip_writeback: bool = False) -> int:
    gauth = _imports.load_google_auth()
    sheets = gauth.get_sheets()

    cfg = _load_config()
    sheet_id = cfg.get("spreadsheet_id")
    url = cfg.get("spreadsheet_url", "")
    created = False
    if not sheet_id:
        sheet_id, url = _create_sheet(sheets)
        cfg.update({"spreadsheet_id": sheet_id, "spreadsheet_url": url,
                    "tab": TAB_NAME, "created_at": datetime.now(timezone.utc).isoformat()})
        _save_config(cfg)
        created = True
    elif not skip_writeback:
        # Close the loop BEFORE overwriting: act on whatever the Commander/
        # staff changed in AppSheet since the last sync (dispose-at-source,
        # stage moves, comments) so the fresh collect below reflects it —
        # e.g. a disposed item's source is already gone, so it won't be
        # re-emitted by collect_rows.
        from . import writeback
        wb = writeback.process_once()
        if wb["disposed"] or wb["staged"] or wb["commented"]:
            print(f"[writeback] disposed={len(wb['disposed'])} "
                  f"staged={len(wb['staged'])} commented={len(wb['commented'])}")
        if wb["errors"]:
            print(f"[writeback] WARNING {len(wb['errors'])} action(s) failed: "
                  f"{wb['errors'][:3]}", file=sys.stderr)

    rows = collect_rows(include_gmail=include_gmail, include_keep=include_keep,
                        include_sms=include_sms)
    values = [SHEET_COLUMNS] + [[r.get(c, "") for c in SHEET_COLUMNS] for r in rows]

    # Idempotent full rewrite: clear the tab, then write header + rows.
    sheets.spreadsheets().values().clear(
        spreadsheetId=sheet_id, range=TAB_NAME).execute()
    sheets.spreadsheets().values().update(
        spreadsheetId=sheet_id, range=f"{TAB_NAME}!A1",
        valueInputOption="RAW", body={"values": values}).execute()

    gid = cfg.get("spreadsheet_gid")
    if gid is None:
        ss = sheets.spreadsheets().get(spreadsheetId=sheet_id, fields="sheets.properties").execute()
        for sheet in ss.get("sheets", []):
            props = sheet.get("properties", {})
            if props.get("title") == TAB_NAME:
                gid = props.get("sheetId")
                cfg["spreadsheet_gid"] = gid
                break

    cfg["last_sync_at"] = datetime.now(timezone.utc).isoformat()
    cfg["last_row_count"] = len(rows)
    cfg["item_rows"] = {r.get("id"): idx + 2 for idx, r in enumerate(rows) if r.get("id")}
    _save_config(cfg)

    print(f"{'Created' if created else 'Updated'} Sheet: {url}")
    print(f"Wrote {len(rows)} rows to tab '{TAB_NAME}'.")
    missing = [r["id"] for r in rows if not r.get("link")]
    if missing:
        print(f"WARNING: {len(missing)} rows have no link: {missing[:5]}", file=sys.stderr)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Sync TCD items to the Google Sheet data plane.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Collect + enrich, write JSON, touch no Google services.")
    ap.add_argument("--out", default="", help="Dry-run output file (default: stdout).")
    ap.add_argument("--no-gmail", action="store_true",
                    help="Skip the Gmail collectors (local sources only).")
    ap.add_argument("--no-keep", action="store_true",
                    help="Skip the Keep collector.")
    ap.add_argument("--no-sms", action="store_true",
                    help="Skip the SMS gateway collector.")
    ap.add_argument("--no-writeback", action="store_true",
                    help="Skip the write-back pass (collect+push only).")
    args = ap.parse_args(argv)

    include_gmail = not args.no_gmail
    include_keep = not args.no_keep
    include_sms = not args.no_sms
    if args.dry_run:
        return _dry_run(args.out, include_gmail, include_keep, include_sms)
    return _live_sync(include_gmail, include_keep=include_keep, include_sms=include_sms,
                      skip_writeback=args.no_writeback)


if __name__ == "__main__":
    raise SystemExit(main())
