#!/usr/bin/env python3
"""
client_gdoc_sync.py — GENERIC Google-Doc → portal sync for every client in
config/client_portals.json (the multi-client successor to spencer_gdoc_sync.py).

Per client dir (registry "dir"): client/_gdoc_links.json (title→doc URL),
client/portal.json (doc_titles title→stem + build title/subtitle/out).
Exports each working copy as markdown, hash-compares against
client/.gdoc_sync_state.json, folds changes into client/<stem>.md (.bak kept),
rebuilds that client's portal page.

Usage: --check | --apply | --baseline   (all clients in one pass)
Timer: client-gdoc-sync.timer (daily 06:35 MT)

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
REGISTRY = ROOT / "config/client_portals.json"
TOKEN = ROOT / "creds/drive_token.json"


def drive():
    creds = Credentials.from_authorized_user_file(str(TOKEN), ["https://www.googleapis.com/auth/drive"])
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN.write_text(creds.to_json())
    return build("drive", "v3", credentials=creds)


def sync_client(svc, host, entry, mode):
    cdir = ROOT / entry["dir"] / "client"
    links_f, cfg_f, state_f = cdir / "_gdoc_links.json", cdir / "portal.json", cdir / ".gdoc_sync_state.json"
    if not (links_f.exists() and cfg_f.exists()):
        return
    cfg = json.loads(cfg_f.read_text())
    title_to_stem = {v: k for k, v in cfg.get("doc_titles", {}).items()}
    links = json.loads(links_f.read_text())["docs"]
    state = json.loads(state_f.read_text()) if state_f.exists() else {}

    exports, changed = {}, []
    for title, url in links.items():
        stem = title_to_stem.get(title)
        if not stem:
            continue
        gid = url.split("/d/")[1].split("/")[0]
        md = svc.files().export(fileId=gid, mimeType="text/markdown").execute().decode("utf-8")
        h = hashlib.sha256(md.encode()).hexdigest()
        exports[stem] = (md, h)
        if state.get(stem) != h:
            changed.append(stem)

    if mode == "baseline":
        state_f.write_text(json.dumps({s: h for s, (_, h) in exports.items()}, indent=2))
        print(f"{host}: baseline recorded ({len(exports)} docs)")
        return
    if not changed:
        print(f"{host}: in sync")
        return
    print(f"{host}: changed — {', '.join(changed)}")
    if mode == "check":
        return
    for stem in changed:
        md, h = exports[stem]
        tgt = cdir / f"{stem}.md"
        if tgt.exists():
            tgt.with_suffix(".md.bak").write_text(tgt.read_text())
        tgt.write_text(md)
        state[stem] = h
    state_f.write_text(json.dumps(state, indent=2))
    b = cfg.get("build", {})
    subprocess.run([sys.executable, str(ROOT / "scripts/build_client_portal.py"),
                    "--dir", str(cdir), "--out", str(ROOT / b["out"]),
                    "--title", b.get("title", entry["name"]),
                    "--subtitle", b.get("subtitle", "")], check=True)
    print(f"{host}: portal rebuilt — family edits live")


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--apply", action="store_true")
    g.add_argument("--baseline", action="store_true")
    a = ap.parse_args()
    mode = "check" if a.check else "apply" if a.apply else "baseline"
    svc = drive()
    reg = json.loads(REGISTRY.read_text())
    for host, entry in reg.items():
        if host.startswith("_"):
            continue
        sync_client(svc, host, entry, mode)


if __name__ == "__main__":
    main()
