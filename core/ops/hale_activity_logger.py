#!/usr/bin/env python3
"""
Hale Activity Logger — structured event sink for COS dashboard and email summaries.
Write events from any wing module via: from core.ops.hale_activity_logger import log_event
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path("/home/john/Thunderbird/hale_activity_log.jsonl")

CATEGORIES = {
    "MISSION":   "🎯",
    "DECISION":  "⚡",
    "ERROR":     "🔴",
    "BLOCKER":   "🚧",
    "TASK":      "📋",
    "HEALTH":    "💚",
    "DISPATCH":  "🚀",
    "COMPLETE":  "✅",
    "INTEL":     "🔍",
    "CLIENT":    "👤",
}

def log_event(category: str, title: str, detail: str = "", source: str = "", level: str = "INFO"):
    """Append one structured event to the activity log."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "ts_local": datetime.now().strftime("%Y-%m-%d %H:%M MT"),
        "category": category.upper(),
        "icon": CATEGORIES.get(category.upper(), "•"),
        "title": title,
        "detail": detail,
        "source": source or "hale",
        "level": level,
    }
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # Never let logging crash the caller
    return entry


def read_recent(n: int = 100) -> list[dict]:
    """Return the last n events from the log, newest first."""
    if not LOG_PATH.exists():
        return []
    try:
        lines = LOG_PATH.read_text(encoding="utf-8").strip().splitlines()
        events = []
        for line in reversed(lines):
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
            if len(events) >= n:
                break
        return events
    except Exception:
        return []


def read_since(hours: int = 1) -> list[dict]:
    """Return all events in the last N hours, oldest first."""
    if not LOG_PATH.exists():
        return []
    cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600
    events = []
    try:
        for line in LOG_PATH.read_text(encoding="utf-8").strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                ts = datetime.fromisoformat(ev["ts"]).timestamp()
                if ts >= cutoff:
                    events.append(ev)
            except Exception:
                pass
    except Exception:
        pass
    return events


# Convenience wrappers used by other modules
def mission_start(mission_id: str, title: str, source: str = ""):
    log_event("MISSION", f"Started: {mission_id} — {title}", source=source)

def mission_complete(mission_id: str, title: str, source: str = ""):
    log_event("COMPLETE", f"Done: {mission_id} — {title}", source=source)

def autonomous_decision(title: str, detail: str = "", source: str = ""):
    log_event("DECISION", title, detail=detail, source=source)

def task_dispatched(task: str, model: str = "", source: str = ""):
    log_event("DISPATCH", task, detail=f"model={model}" if model else "", source=source)

def error_logged(title: str, detail: str = "", source: str = ""):
    log_event("ERROR", title, detail=detail, source=source, level="ERROR")

def blocker_logged(title: str, detail: str = "", source: str = ""):
    log_event("BLOCKER", title, detail=detail, source=source, level="WARN")

def health_check(status: str, detail: str = "", source: str = ""):
    log_event("HEALTH", f"Health: {status}", detail=detail, source=source)
