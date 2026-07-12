"""
sections_sync — write Intel / Tech Scans / Next 7 Days to their own tabs.

Same spreadsheet as the main Items sync (id read from
config/tcd_sheet_config.json — run ``python -m tcd.sheet_sync`` at least
once first to create it). Separate script/cadence from the 10-minute Items
sync because Drive-mirroring local files (intel reports, tech-scan outputs)
is heavier than a plain Sheets write — daily is plenty for read-only
dashboard material.

Usage:
    python -m tcd.sections_sync --dry-run [--out rows.json]  # offline, no Google
    python -m tcd.sections_sync                              # live: create/update tabs
"""
import argparse
import json
import sys
from datetime import datetime, timezone

from . import _imports
from .item_model import SHEET_COLUMNS
from .sections import collect_intel, collect_techscans, collect_next7
from .sheet_sync import CONFIG_PATH, _load_config

SECTION_COLLECTORS = {
    "Intel": collect_intel,
    "TechScans": collect_techscans,
    "Next7": collect_next7,
}


def collect_section_rows(name: str, **collector_kwargs) -> list:
    """SHEET_COLUMNS-keyed dicts for one section tab."""
    fn = SECTION_COLLECTORS[name]
    return [item.to_dict() for item in fn(**collector_kwargs)]


def _noop_mirror(path, folder, mime):
    """Dry-run mirror stub — verify local-file discovery/shaping WITHOUT
    writing anything to Drive. Intel/TechScans fall back to
    drive_search_link, same as a real mirror failure would."""
    return ""


def _dry_run(out_path: str) -> int:
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "columns": SHEET_COLUMNS,
               "tabs": {}}
    total_missing = []
    kwargs_by_tab = {"Intel": {"mirror_fn": _noop_mirror},
                     "TechScans": {"mirror_fn": _noop_mirror},
                     "Next7": {}}  # Calendar events are a live READ, not a write — fine in dry-run
    for name in SECTION_COLLECTORS:
        rows = collect_section_rows(name, **kwargs_by_tab[name])
        missing = [r["id"] for r in rows if not r.get("link")]
        total_missing += missing
        payload["tabs"][name] = {"count": len(rows), "rows": rows}
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        for name, tab in payload["tabs"].items():
            print(f"[dry-run] {name}: {tab['count']} rows")
        print(f"[dry-run] rows missing a link across all tabs: {len(total_missing)}"
              + (f" — {total_missing[:5]}" if total_missing else " (all rows linked ✓)"))
    else:
        print(text)
    return 0


def _ensure_tab(sheets, sheet_id: str, tab_name: str) -> None:
    meta = sheets.spreadsheets().get(spreadsheetId=sheet_id, fields="sheets.properties.title").execute()
    existing = {s["properties"]["title"] for s in meta.get("sheets", [])}
    if tab_name not in existing:
        sheets.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": tab_name}}}]},
        ).execute()


def _live_sync() -> int:
    cfg = _load_config()
    sheet_id = cfg.get("spreadsheet_id")
    if not sheet_id:
        print("No Sheet configured yet — run `python -m tcd.sheet_sync` first.",
              file=sys.stderr)
        return 1

    gauth = _imports.load_google_auth()
    sheets = gauth.get_sheets()

    total_missing = []
    for name in SECTION_COLLECTORS:
        _ensure_tab(sheets, sheet_id, name)
        rows = collect_section_rows(name)
        values = [SHEET_COLUMNS] + [[r.get(c, "") for c in SHEET_COLUMNS] for r in rows]
        sheets.spreadsheets().values().clear(spreadsheetId=sheet_id, range=name).execute()
        sheets.spreadsheets().values().update(
            spreadsheetId=sheet_id, range=f"{name}!A1",
            valueInputOption="RAW", body={"values": values}).execute()
        missing = [r["id"] for r in rows if not r.get("link")]
        total_missing += missing
        print(f"Wrote {len(rows)} rows to tab '{name}'.")

    cfg["last_sections_sync_at"] = datetime.now(timezone.utc).isoformat()
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))

    if total_missing:
        print(f"WARNING: {len(total_missing)} rows have no link: {total_missing[:5]}",
              file=sys.stderr)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Sync Intel/TechScans/Next7 tabs.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Collect + enrich, write JSON, touch no Google services.")
    ap.add_argument("--out", default="", help="Dry-run output file (default: stdout).")
    args = ap.parse_args(argv)

    if args.dry_run:
        return _dry_run(args.out)
    return _live_sync()


if __name__ == "__main__":
    raise SystemExit(main())
