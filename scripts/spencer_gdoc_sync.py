#!/usr/bin/env python3
"""
spencer_gdoc_sync.py — Sync family edits from the Spencer Google Doc working copies
into the client portal (spencer.d2mluxury.quest).

Flow: export each Google Doc as markdown → compare against last-known hash →
on change, write to client/<stem>.md (previous version kept as .bak) → rebuild portal.

Docs whose Google copy is unchanged are never touched, so D2M-side edits to the
local md (pushed to the web only) are never clobbered by an idle working copy.

Usage:
  python3 scripts/spencer_gdoc_sync.py --check     # report changes only
  python3 scripts/spencer_gdoc_sync.py --apply     # fold changes + rebuild portal
  python3 scripts/spencer_gdoc_sync.py --baseline  # record current state as synced

Dreams2Memories Travel, LLC · 2026-07-03
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

ROOT = Path.home() / "Thunderbird"
TOKEN = ROOT / "creds" / "drive_token.json"
CLIENT = ROOT / "output/Spencer_GrandTour_2027/client"
STATE = CLIENT / ".gdoc_sync_state.json"

# Google Doc title -> local markdown stem (portal section source)
TITLE_TO_STEM = {
    "Spencer Grand Tour — Trip Book (Overview)": "00_Trip_Book",
    "Spencer Grand Tour — Day-by-Day Itinerary": "01_Day_by_Day_Itinerary",
    "Spencer Grand Tour — Shore Excursion Menu": "02_Shore_Excursion_Menu",
    "Spencer Grand Tour — Florence & Tuscany Options": "03_Florence_and_Tuscany_Options",
    "Spencer Grand Tour — Swiss Alps Journey": "04_Swiss_Alps_Journey",
    "Spencer Grand Tour — Your Options & Investment": "05_Your_Options_and_Investment",
    "Spencer Grand Tour — Build Your Journey (Investment Guide)": "06_Build_Your_Journey_Investment_Guide",
}

REBUILD = [
    sys.executable, str(ROOT / "scripts/build_client_portal.py"),
    "--dir", str(CLIENT),
    "--out", str(CLIENT / "html/index.html"),
    "--title", "The Spencer Family Grand Tour",
    "--subtitle", "June 12 – July 2, 2027 · Your Private Travel Portal",
]


def drive_service():
    creds = Credentials.from_authorized_user_file(str(TOKEN), ["https://www.googleapis.com/auth/drive"])
    if creds.expired:
        creds.refresh(Request())
        TOKEN.write_text(creds.to_json())
    return build("drive", "v3", credentials=creds)


def main():
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--baseline", action="store_true")
    a = ap.parse_args()

    links = json.loads((CLIENT / "_gdoc_links.json").read_text())["docs"]
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    svc = drive_service()

    changed = []
    exports = {}
    for title, url in links.items():
        stem = TITLE_TO_STEM.get(title)
        if not stem:
            print(f"  ? no stem mapping for: {title} — skipped")
            continue
        gid = url.split("/d/")[1].split("/")[0]
        md = svc.files().export(fileId=gid, mimeType="text/markdown").execute().decode("utf-8")
        h = hashlib.sha256(md.encode()).hexdigest()
        exports[stem] = (md, h)
        if state.get(stem) != h:
            changed.append(stem)

    if a.baseline:
        STATE.write_text(json.dumps({s: h for s, (_, h) in exports.items()}, indent=2))
        print(f"Baseline recorded for {len(exports)} docs → {STATE.name}")
        return

    if not changed:
        print("In sync — no working-copy edits since last sync.")
        return

    print(f"Changed working copies: {', '.join(changed)}")
    if a.check:
        return

    for stem in changed:
        md, h = exports[stem]
        target = CLIENT / f"{stem}.md"
        if target.exists():
            target.with_suffix(".md.bak").write_text(target.read_text())
        target.write_text(md)
        state[stem] = h
        print(f"  folded: {stem}.md (previous saved as .bak)")
    STATE.write_text(json.dumps(state, indent=2))
    subprocess.run(REBUILD, check=True)
    print("Portal rebuilt — family edits are live.")


if __name__ == "__main__":
    main()
