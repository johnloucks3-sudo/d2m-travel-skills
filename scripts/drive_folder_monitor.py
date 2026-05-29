#!/usr/bin/env python3
"""Drive Folder Inotify Monitor — MISSION-045.
Watches ~/Thunderbird/output/ and ~/Thunderbird_Proposals/ for file changes.
Flags new/modified files to hale_shared_state.jsonl within 30s.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pyinotify

ROOT = Path.home() / "Thunderbird"
WATCH_DIRS = [
    str(ROOT / "output"),
    str(Path.home() / "Thunderbird_Proposals"),
]
SHARED_STATE = ROOT / "OpsCenter" / "hale_shared_state.jsonl"

class EventHandler(pyinotify.ProcessEvent):
    def process_IN_CLOSE_WRITE(self, event):
        self._log_event(event, "modified")
    def process_IN_MOVED_TO(self, event):
        self._log_event(event, "created")
    def process_IN_CREATE(self, event):
        self._log_event(event, "created")

    def _log_event(self, event, action):
        if event.dir:
            return
        entry = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "drive_folder_monitor",
            "event": action,
            "path": os.path.join(event.path, event.name),
            "type": "file",
        }
        with open(SHARED_STATE, "a") as f:
            f.write(json.dumps(entry) + "\n")

def main():
    for d in WATCH_DIRS:
        os.makedirs(d, exist_ok=True)

    wm = pyinotify.WatchManager()
    handler = EventHandler()
    notifier = pyinotify.Notifier(wm, handler)

    mask = pyinotify.IN_CLOSE_WRITE | pyinotify.IN_MOVED_TO | pyinotify.IN_CREATE
    for d in WATCH_DIRS:
        if os.path.isdir(d):
            wdd = wm.add_watch(d, mask, rec=True, auto_add=True)
            print(f"Watching: {d} (inodes: {len(wdd)})", flush=True)

    print(f"Monitor active. Writing to: {SHARED_STATE}", flush=True)
    try:
        notifier.loop()
    except KeyboardInterrupt:
        print("Monitor stopped.", flush=True)

if __name__ == "__main__":
    main()
