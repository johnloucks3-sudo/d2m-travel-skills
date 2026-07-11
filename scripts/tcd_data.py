#!/usr/bin/env python3
"""
tcd_data.py — live data adapter for Thunderbird Commander Desktop (TCD) v4.

Reads real Wing state (hale_state.json, standing_orders/, dossiers/, hale_decisions.md)
and produces the {folders, files, outbox} shape the TCD v4 frontend
(drafts/tcd_v4_file_interface.html) already expects, so the existing UI can
render real data instead of its hardcoded mockup array.

Overlay state (comments added via the UI, folder moves, outbox pushes) lives
separately in OpsCenter/tcd_state.json (see tcd_server.py) and is merged on
top of what this module produces — this module only reads source-of-truth
Wing files, it never writes.
"""
import base64
import json
import re
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HALE_STATE = ROOT / "hale_state.json"
HALE_DECISIONS = ROOT / "hale_decisions.md"
STANDING_ORDERS = ROOT / "standing_orders"
DOSSIERS = ROOT / "dossiers"

sys.path.insert(0, str(ROOT / "api"))

GMAIL_ACCOUNTS = [
    ("johnloucks3", "get_commander_gmail"),
    ("d2mconcierge", "get_persona_gmail"),
]

FOLDERS = {
    "strategic": [
        {"id": "s-inbox", "name": "Inbox", "builtin": True},
        {"id": "s-clientstrat", "name": "Client Strategy", "builtin": True},
        {"id": "s-elon", "name": "ELON Tech Vanguard", "builtin": True},
        {"id": "s-financial", "name": "Financial Commitments", "builtin": True},
    ],
    "operational": [
        {"id": "o-inbox", "name": "Inbox", "builtin": True},
        {"id": "o-dailyops", "name": "Daily Ops", "builtin": True},
        {"id": "o-bookings", "name": "Bookings & Payments", "builtin": True},
        {"id": "o-vendor", "name": "Vendor / Portal Issues", "builtin": True},
    ],
    "reference": [
        {"id": "r-inbox", "name": "Inbox", "builtin": True},
        {"id": "r-so", "name": "Standing Orders", "builtin": True},
        {"id": "r-dossier", "name": "Client Dossiers", "builtin": True},
        {"id": "r-research", "name": "Research Archive", "builtin": True},
    ],
}

_PRIORITY_MAP = {"P0": "p0", "P1": "p1", "P2": "p2", "P3": "routine"}


def _load_json(path, default=None):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else {}


def _pri(raw):
    return _PRIORITY_MAP.get((raw or "").upper(), "routine")


def _snip(text, n=220):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:n] + ("…" if len(text) > n else "")


def _financial_folder(msg):
    return "s-financial" if "$" in (msg or "") or "FPD" in (msg or "").upper() else "s-clientstrat"


def build_strategic(state):
    files = []
    for a in state.get("deferred_alerts", []):
        if a.get("priority") not in ("P0", "P1"):
            continue
        if not (a.get("amount") or "financial" in (a.get("condition_type") or "")):
            continue
        body = a.get("message", "")
        files.append({
            "id": f"alert-{a['id']}", "inbox": "strategic",
            "folder": _financial_folder(a.get("message")),
            "type": "decision", "priority": _pri(a.get("priority")), "unread": True,
            "title": a.get("message", "")[:90], "from": "Deferred Alert Monitor",
            "date": a.get("trigger_date", ""),
            "snippet": _snip(body), "body": body,
            "tags": ["deferred-alert", a.get("client", "")], "comments": [],
        })
    elon = state.get("elon_proposals", {})
    if elon:
        claim = elon.get("2026-07-06_batch_claim", "")
        verified = elon.get("2026-07-06_batch_verified", {})
        body = (f"ELON verification pass — {elon.get('verification_method', '')}\n\n"
                f"Claimed: {claim}\n"
                f"Committed to git: {verified.get('committed_to_git', '?')}\n"
                f"Passing both bars (committed + wired): {verified.get('passing_both_bars_committed_and_wired', '?')}\n"
                f"No file evidence found: {verified.get('no_file_evidence_found', '?')}")
        files.append({
            "id": "elon-verify-latest", "inbox": "strategic", "folder": "s-elon",
            "type": "paper", "priority": "p1", "unread": True,
            "title": "ELON proposal verification — claimed vs. git-verified counts diverge",
            "from": "A14 Whetstone", "date": elon.get("last_verified", "")[:10],
            "snippet": _snip(body), "body": body,
            "tags": ["ELON", "verification"], "comments": [],
        })
    return files


def build_operational(state):
    files = []
    for t in state.get("open_tasks", []):
        body = t.get("note") or t.get("blocker") or t.get("title", "")
        files.append({
            "id": f"task-{t['id']}", "inbox": "operational", "folder": "o-dailyops",
            "type": "brief", "priority": _pri(t.get("priority")), "unread": t.get("status") == "active",
            "title": t.get("title", ""), "from": "Mission Board", "date": "",
            "snippet": _snip(body or t.get("title", "")),
            "body": body or t.get("title", ""),
            "tags": [t.get("id", ""), t.get("status", "")], "comments": [],
        })
    for p in state.get("project_tracking", {}).get("active_projects", []):
        body = p.get("notes", "")
        files.append({
            "id": f"proj-{p['id']}", "inbox": "operational", "folder": "o-bookings",
            "type": "email", "priority": "p2", "unread": False,
            "title": f"{p.get('name', '')} — {p.get('status', '')}",
            "from": f"{p.get('owner', 'Wing')} · Project Tracker", "date": p.get("deadline", ""),
            "snippet": _snip(body), "body": body,
            "tags": [p.get("mission", ""), p.get("status", "")], "comments": [],
        })
    for a in state.get("deferred_alerts", []):
        if a.get("priority") not in ("P1", "P2"):
            continue
        if a.get("amount"):
            continue
        body = a.get("message", "")
        files.append({
            "id": f"alert-{a['id']}", "inbox": "operational", "folder": "o-vendor",
            "type": "email", "priority": _pri(a.get("priority")), "unread": True,
            "title": a.get("message", "")[:90], "from": "Deferred Alert Monitor",
            "date": a.get("trigger_date", ""), "snippet": _snip(body), "body": body,
            "tags": ["deferred-alert", a.get("client", "")], "comments": [],
        })
    return files


def _gmail_header(headers, name):
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _gmail_body(payload):
    def _decode(data):
        try:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        except Exception:
            return ""
    body_data = payload.get("body", {}).get("data", "")
    if body_data:
        return _decode(body_data)
    for part in payload.get("parts", []) or []:
        if part.get("mimeType") == "text/plain":
            return _decode(part.get("body", {}).get("data", ""))
    for part in payload.get("parts", []) or []:
        d = part.get("body", {}).get("data", "")
        if d:
            return _decode(d)
    return ""


_gmail_cache = {"ts": 0, "files": []}
_GMAIL_TTL_SECONDS = 300


def build_gmail(max_per_account=12):
    """Recent inbox messages from both Gmail accounts, feeding Operational.
    Cached for _GMAIL_TTL_SECONDS since each refresh does full-message fetches
    against the live Gmail API and the frontend polls every 60s."""
    import time
    now = time.time()
    if now - _gmail_cache["ts"] < _GMAIL_TTL_SECONDS:
        return _gmail_cache["files"]
    files = []
    try:
        import thunderbird_google_auth as gauth
    except Exception as e:
        print(f"tcd_data: gmail auth module unavailable: {e}", file=sys.stderr)
        return files
    for account, getter_name in GMAIL_ACCOUNTS:
        try:
            svc = getattr(gauth, getter_name)()
            listing = svc.users().messages().list(
                userId="me", labelIds=["INBOX"], maxResults=max_per_account,
                q="newer_than:14d",
            ).execute()
            for meta in listing.get("messages", []):
                msg = svc.users().messages().get(
                    userId="me", id=meta["id"], format="full").execute()
                headers = msg.get("payload", {}).get("headers", [])
                subject = _gmail_header(headers, "Subject") or "(no subject)"
                sender = _gmail_header(headers, "From")
                date_hdr = _gmail_header(headers, "Date")
                try:
                    date_iso = parsedate_to_datetime(date_hdr).date().isoformat()
                except Exception:
                    date_iso = ""
                body = _gmail_body(msg.get("payload", {})) or msg.get("snippet", "")
                unread = "UNREAD" in (msg.get("labelIds") or [])
                files.append({
                    "id": f"gmail-{account}-{meta['id']}", "inbox": "operational",
                    "folder": "o-inbox", "type": "email",
                    "priority": "p2" if unread else "routine", "unread": unread,
                    "title": subject, "from": f"{sender} → {account}",
                    "date": date_iso,
                    "snippet": _snip(msg.get("snippet", "") or body),
                    "body": body[:4000],
                    "tags": ["gmail", account], "comments": [],
                })
        except Exception as e:
            print(f"tcd_data: gmail fetch failed for {account}: {e}", file=sys.stderr)
    _gmail_cache["ts"] = now
    _gmail_cache["files"] = files
    return files


def build_reference():
    files = []
    for f in sorted(STANDING_ORDERS.glob("SO_*.md"))[:20]:
        text = f.read_text(errors="ignore")
        title = text.splitlines()[0].lstrip("# ").strip() if text else f.stem
        files.append({
            "id": f"so-{f.stem}", "inbox": "reference", "folder": "r-so",
            "type": "paper", "priority": "routine", "unread": False,
            "title": title, "from": "Standing Orders", "date": f.stem[-8:] if f.stem[-8:].isdigit() else "",
            "snippet": _snip(text[:400]), "body": text[:4000],
            "tags": ["standing-order"], "comments": [],
        })
    for f in sorted(DOSSIERS.glob("DOSSIER_*.md"))[:20]:
        text = f.read_text(errors="ignore")
        title = text.splitlines()[0].lstrip("# ").strip() if text else f.stem
        files.append({
            "id": f"dossier-{f.stem}", "inbox": "reference", "folder": "r-dossier",
            "type": "paper", "priority": "routine", "unread": False,
            "title": title, "from": "Dossier System", "date": "",
            "snippet": _snip(text[:400]), "body": text[:4000],
            "tags": ["dossier"], "comments": [],
        })
    return files


def build_outbox():
    text = HALE_DECISIONS.read_text(errors="ignore") if HALE_DECISIONS.exists() else ""
    entries = re.findall(
        r"<!-- PLAN:CLOSE plan_id=(\S+) verdict=(\S+) .*?closed_at=(\S+?) -->\n"
        r"\*\*Plan Closed:\*\* \S+\n\*\*Verdict:\*\* \S+\n\*\*Quality tier:\*\* .*?\n"
        r"\*\*Criteria met:\*\* (.*?)\n.*?\*\*Notes:\*\* (.*?)\n",
        text, re.S,
    )
    outbox = []
    for plan_id, verdict, closed_at, criteria_met, notes in entries[-40:]:
        outbox.append({
            "id": f"ob-{plan_id}", "fileId": None,
            "title": (criteria_met if criteria_met and criteria_met != "none" else notes)[:110],
            "executed": verdict == "PASS", "execDate": closed_at[:16].replace("T", " "),
            "from": "hale_decisions.md audit trail",
            "stage": "C" if verdict == "PASS" else "A",
        })
    return outbox


def build_briefing(state):
    alerts = sorted(
        [a for a in state.get("deferred_alerts", []) if a.get("priority") in ("P0", "P1")],
        key=lambda a: (a.get("priority"), a.get("trigger_date", "")),
    )
    fp = state.get("financial_pulse", {})
    wh = state.get("wing_health", {})
    open_tasks = state.get("open_tasks", [])
    return {
        "alerts": [{
            "id": a["id"], "priority": a.get("priority"), "message": a.get("message", ""),
            "client": a.get("client", ""), "trigger_date": a.get("trigger_date", ""),
            "amount": a.get("amount"),
        } for a in alerts],
        "financial_pulse": {
            "pipeline_total": fp.get("total_d2m_pipeline"),
            "sheet_bookings": fp.get("sheet_bookings"),
            "last_checked": fp.get("last_checked", ""),
            "note": fp.get("harlan_note", "") or fp.get("pipeline_note", ""),
        },
        "wing_health": {
            "mcp_server": wh.get("mcp_server", ""),
            "opencode_status": wh.get("opencode_status", ""),
            "telegram_bot": wh.get("telegram_bot", ""),
            "last_health_check": wh.get("last_health_check", ""),
        },
        "stats": {
            "open_tasks_p0": len([t for t in open_tasks if t.get("priority") == "P0"]),
            "open_tasks_total": len(open_tasks),
            "p0_alerts": len([a for a in alerts if a.get("priority") == "P0"]),
            "p1_alerts": len([a for a in alerts if a.get("priority") == "P1"]),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def build_data(include_gmail=True):
    state = _load_json(HALE_STATE, {})
    files = build_strategic(state) + build_operational(state) + build_reference()
    if include_gmail:
        files = build_gmail() + files
    return {"folders": FOLDERS, "files": files, "outbox": build_outbox(),
            "generated_at": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    print(json.dumps(build_data(), indent=2)[:3000])
