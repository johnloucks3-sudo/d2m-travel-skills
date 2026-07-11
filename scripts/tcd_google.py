#!/usr/bin/env python3
"""
tcd_google.py — Google Suite panels for Thunderbird Commander Desktop (TCD) v4.

Mounted into scripts/tcd_server.py via a minimal hook (2 dispatch lines —
see GOOGLE ROUTES comment there). Owns everything under /api/google/*.

Auth: unified OAuth token via api/thunderbird_google_auth.py (gmail_token.json)
— same credential the rest of Thunderbird uses for Calendar / Drive / Tasks /
Sheets. Keep uses the separate gkeepapi master-token credential
(keep_credentials.json, api/thunderbird_keep.py) since Keep has no official API.

Endpoints:
  GET  /api/google/calendar?days=7         upcoming Calendar events
  GET  /api/google/drive/list?folder=&q=   Drive file listing / search
  GET  /api/google/tasks/lists             all Google Task list names
  GET  /api/google/tasks?list=&completed=  tasks in a list (overdue-flagged)
  POST /api/google/tasks                   create a task {title, listName, dueDate, notes}
  GET  /api/google/sheets/decisionlog      link-out info for Commander_Decision_Log_2026
  GET  /api/google/keep?q=&pinned=         Keep notes (list or search)
  POST /api/google/keep                    create a Keep note {title, body, pinned}
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

import thunderbird_google_auth as gauth  # noqa: E402

DECISION_LOG_SHEET_ID = "1pnf8slR1qF5g5pOyARd1qkPyd7HW4306UgZ9NQhOD2c"
D2M_TASK_LIST = "D2M Client Tasks"

_svc_cache = {}


def _svc(kind, builder):
    if kind not in _svc_cache:
        _svc_cache[kind] = builder()
    return _svc_cache[kind]


def _calendar():
    return _svc("calendar", gauth.get_calendar)


def _drive():
    return _svc("drive", gauth.get_drive)


def _tasks():
    return _svc("tasks", gauth.get_tasks)


def _query(full_path):
    return parse_qs(urlparse(full_path).query)


# --------------------------------------------------------------- Calendar
def calendar_events(days=7):
    svc = _calendar()
    now = datetime.now(timezone.utc)
    res = svc.events().list(
        calendarId="primary", timeMin=now.isoformat(),
        timeMax=(now + timedelta(days=days)).isoformat(),
        maxResults=25, singleEvents=True, orderBy="startTime",
    ).execute()
    events = []
    for e in res.get("items", []):
        s = e.get("start", {})
        events.append({
            "id": e.get("id"), "summary": e.get("summary", "(no title)"),
            "start": s.get("dateTime", s.get("date", "")),
            "allDay": "date" in s and "dateTime" not in s,
            "location": e.get("location", ""),
            "htmlLink": e.get("htmlLink", ""),
        })
    return {"ok": True, "days": days, "count": len(events), "events": events}


# ------------------------------------------------------------------ Drive
def drive_list(folder_id=None, q=None, max_results=25):
    svc = _drive()
    parts = ["trashed = false"]
    if folder_id:
        parts.append(f"'{folder_id.replace(chr(39), chr(92)+chr(39))}' in parents")
    if q:
        safe_q = q.replace("'", "\\'")
        parts.append(f"(name contains '{safe_q}' or fullText contains '{safe_q}')")
    res = svc.files().list(
        q=" and ".join(parts), pageSize=min(max_results, 50),
        fields="files(id,name,mimeType,modifiedTime,webViewLink,iconLink,size)",
        orderBy="modifiedTime desc",
    ).execute()
    files = res.get("files", [])
    return {"ok": True, "files": files, "count": len(files)}


# ------------------------------------------------------------------ Tasks
def _task_list_id(svc, name):
    res = svc.tasklists().list(maxResults=50).execute()
    for tl in res.get("items", []):
        if tl.get("title", "").strip().lower() == name.strip().lower():
            return tl["id"]
    return None


def tasks_lists():
    svc = _tasks()
    res = svc.tasklists().list(maxResults=50).execute()
    return {"ok": True, "lists": [{"id": t["id"], "title": t["title"]} for t in res.get("items", [])]}


def tasks_list(list_name=D2M_TASK_LIST, show_completed=False):
    svc = _tasks()
    list_id = _task_list_id(svc, list_name)
    if not list_id:
        return {"ok": True, "listName": list_name, "tasks": [], "count": 0, "note": "list not created yet"}
    res = svc.tasks().list(
        tasklist=list_id, maxResults=50,
        showCompleted=show_completed, showHidden=show_completed,
    ).execute()
    today = datetime.now(timezone.utc).date()
    out = []
    for t in res.get("items", []):
        due = (t.get("due") or "")[:10]
        overdue = False
        if due and t.get("status") != "completed":
            try:
                overdue = datetime.strptime(due, "%Y-%m-%d").date() < today
            except ValueError:
                pass
        out.append({
            "id": t.get("id"), "title": t.get("title", ""), "notes": t.get("notes", ""),
            "status": t.get("status", ""), "due": due, "overdue": overdue,
        })
    return {"ok": True, "listName": list_name, "tasks": out, "count": len(out)}


def tasks_create(title, list_name=D2M_TASK_LIST, due_date=None, notes=None):
    svc = _tasks()
    list_id = _task_list_id(svc, list_name)
    if not list_id:
        list_id = svc.tasklists().insert(body={"title": list_name}).execute()["id"]
    body = {"title": title, "status": "needsAction"}
    if due_date:
        body["due"] = f"{due_date}T00:00:00.000Z"
    if notes:
        body["notes"] = notes
    task = svc.tasks().insert(tasklist=list_id, body=body).execute()
    return {"ok": True, "task": {"id": task.get("id"), "title": task.get("title")}}


def tasks_delete(task_id, list_name=D2M_TASK_LIST):
    svc = _tasks()
    list_id = _task_list_id(svc, list_name)
    if not list_id:
        return {"ok": False, "error": "list not found"}
    svc.tasks().delete(tasklist=list_id, task=task_id).execute()
    return {"ok": True, "deleted": task_id}


# ------------------------------------------------------------- Sheets link-out
def sheets_decision_log():
    return {
        "ok": True, "id": DECISION_LOG_SHEET_ID,
        "title": "Commander_Decision_Log_2026",
        "url": f"https://docs.google.com/spreadsheets/d/{DECISION_LOG_SHEET_ID}/edit",
    }


# ------------------------------------------------------------------- Keep
def keep_list(q=None, pinned_only=False, max_results=15):
    import thunderbird_keep as keepmod
    if q:
        return keepmod.search_notes(q, max_results)
    return keepmod.list_notes(max_results, pinned_only)


def keep_create(title, body="", pinned=False):
    import thunderbird_keep as keepmod
    return keepmod.create_note(title, body, None, pinned, "WHITE")


# -------------------------------------------------------------- HTTP dispatch
def _err(handler, code, msg):
    handler._json(code, {"ok": False, "error": msg})


def handle_get(handler, path):
    q = _query(handler.path)
    try:
        if path == "/api/google/calendar":
            days = int((q.get("days") or ["7"])[0])
            return handler._json(200, calendar_events(days))
        if path == "/api/google/drive/list":
            return handler._json(200, drive_list(
                folder_id=(q.get("folder") or [None])[0],
                q=(q.get("q") or [None])[0]))
        if path == "/api/google/tasks/lists":
            return handler._json(200, tasks_lists())
        if path == "/api/google/tasks":
            return handler._json(200, tasks_list(
                list_name=(q.get("list") or [D2M_TASK_LIST])[0],
                show_completed=(q.get("completed") or ["0"])[0] == "1"))
        if path == "/api/google/sheets/decisionlog":
            return handler._json(200, sheets_decision_log())
        if path == "/api/google/keep":
            return handler._json(200, keep_list(
                q=(q.get("q") or [None])[0],
                pinned_only=(q.get("pinned") or ["0"])[0] == "1"))
        return handler._json(404, {"ok": False, "error": "unknown google route"})
    except Exception as e:
        return _err(handler, 500, str(e))


def handle_post(handler, path):
    try:
        body = handler._body_json()
        if path == "/api/google/tasks":
            title = (body.get("title") or "").strip()
            if not title:
                return _err(handler, 400, "title required")
            return handler._json(200, tasks_create(
                title, body.get("listName") or D2M_TASK_LIST,
                body.get("dueDate"), body.get("notes")))
        if path == "/api/google/keep":
            title = (body.get("title") or "").strip()
            if not title:
                return _err(handler, 400, "title required")
            return handler._json(200, keep_create(
                title, body.get("body", ""), bool(body.get("pinned"))))
        return handler._json(404, {"ok": False, "error": "unknown google route"})
    except Exception as e:
        return _err(handler, 500, str(e))


def handle_delete(handler, path):
    try:
        if path.startswith("/api/google/tasks/"):
            task_id = path.rsplit("/", 1)[-1]
            q = _query(handler.path)
            return handler._json(200, tasks_delete(
                task_id, (q.get("list") or [D2M_TASK_LIST])[0]))
        return handler._json(404, {"ok": False, "error": "unknown google route"})
    except Exception as e:
        return _err(handler, 500, str(e))


if __name__ == "__main__":
    import json
    print(json.dumps(calendar_events(7), indent=2, default=str)[:2000])
