#!/usr/bin/env python3
"""
tcd_data.py — live data adapter for Thunderbird Commander Desktop (TCD) v4.

Reads real Wing state (hale_state.json, standing_orders/, dossiers/, hale_decisions.md)
and produces the {folders, files, outbox} shape the TCD v4 frontend
(drafts/tcd_v4_file_interface.html) already expects, so the existing UI can
render real data instead of its hardcoded mockup array.

Overlay state (comments added via the UI, folder moves, outbox pushes) lives
separately in OpsCenter/tcd_state.json and is merged on
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
TCD_TRASH = ROOT / "OpsCenter/tcd_trash"
MISSION_BOARD = ROOT / "OpsCenter" / "mission_board.json"
ELON_PROPOSALS_DIR = ROOT / "OpsCenter" / "elon_proposals"
A7_METRICS_PATH = ROOT / "OpsCenter" / "a7_metrics_dashboard.json"
STAFF_CADENCE_PATH = ROOT / "OpsCenter" / "staff_cadence_log.json"

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


def count_untouched_elon_proposals(proposals_dir=None):
    """MISSION-001A correction: hale_state.json's
    ``elon_proposals.proposal_queue.open_proposals_raw_count`` (94) is NOT
    "94 proposals awaiting Commander review" -- it's a raw never-archived
    file count (the CLOSED/ archive protocol was never adopted). Most of
    those files are already-executed work with a matching ``*_EXECUTION.md``
    companion in the same directory.

    Best available proxy for "genuinely untouched": a PROPOSAL-*.md file
    whose exact filename is never referenced inside ANY *_EXECUTION.md's
    text. Not perfectly precise (a proposal could be done via a path that
    never narrates the filename back), but it's a real signal instead of a
    raw file count -- and it's what a Commander-facing rollup should say,
    labeled as a proxy, not asserted as exact.
    """
    d = proposals_dir or ELON_PROPOSALS_DIR
    if not d.is_dir():
        return None
    exec_text = ""
    for f in d.glob("*_EXECUTION.md"):
        try:
            exec_text += f.read_text(errors="replace") + "\n"
        except OSError:
            continue
    referenced = set(re.findall(r"PROPOSAL-[A-Za-z0-9_-]+", exec_text))
    total = 0
    untouched = 0
    for p in d.glob("PROPOSAL-*.md"):
        total += 1
        stem = p.stem
        if not any(stem == r or stem.startswith(r) or r.startswith(stem) for r in referenced):
            untouched += 1
    return {"total": total, "untouched": untouched, "touched": total - untouched}


def build_a7_metrics_alert(path=None):
    """MISSION-001A A-tier gap: a7_metrics_dashboard.json's continuity_recert
    was never wired into TCD -- Sterling's own health dashboard could sit RED
    indefinitely with nobody's review surface showing it. Only emits an item
    when genuinely abnormal (overall != GREEN); silent otherwise -- same
    fail-quiet contract as the rest of TCD's alert-style collectors."""
    d = _load_json(path or A7_METRICS_PATH, {})
    recert = d.get("continuity_recert", {})
    overall = recert.get("overall")
    if not overall or overall == "GREEN":
        return None
    red_items = recert.get("red_items") or d.get("red_items") or []
    body = f"A7 continuity recertification: {overall}\n\n" + "\n".join(f"- {r}" for r in red_items)
    return {
        "id": "a7metrics-continuity", "inbox": "strategic", "folder": "s-inbox",
        "type": "decision", "priority": "p1", "unread": True,
        "title": f"A7 continuity recert {overall} — {len(red_items)} flagged item(s)",
        "from": "A7 Sterling · Metrics Dashboard",
        "date": (recert.get("timestamp") or d.get("generated_at") or "")[:10],
        "snippet": _snip(body), "body": body,
        "tags": ["a7-metrics", "continuity", overall.lower()], "comments": [],
    }


def build_staff_cadence_alert(path=None):
    """MISSION-001A A-tier gap: staff_cadence_log.json's gate_decision was
    never wired -- a THROTTLED cadence gate could sit unreviewed. Only emits
    when the LATEST run (by run_date) is throttled; silent otherwise
    (verified quiet as of 2026-07-13 -- latest run reads OPEN, a prior run
    from 2026-07-07 was THROTTLED but is no longer current)."""
    d = _load_json(path or STAFF_CADENCE_PATH, {})
    runs = d.get("runs", [])
    if not runs:
        return None
    latest = max(runs, key=lambda r: r.get("run_date", ""))
    decision = latest.get("gate_decision", "")
    if not decision.startswith("THROTTLED"):
        return None
    body = (f"Staff cadence gate ({latest.get('run_date', '')}): {decision}\n\n"
            f"{json.dumps(latest.get('detail', {}), indent=2)}")
    return {
        "id": f"cadence-{latest.get('run_date', 'unknown')}", "inbox": "strategic",
        "folder": "s-inbox", "type": "decision", "priority": "p2", "unread": True,
        "title": f"Staff cadence THROTTLED — {latest.get('run_date', '')}",
        "from": "Staff Cadence Gate", "date": latest.get("run_date", ""),
        "snippet": _snip(body), "body": body,
        "tags": ["staff-cadence", "throttled"], "comments": [],
    }


_SILVER_LEDGER = ROOT / "OpsCenter" / "silver_ledger.jsonl"
_DISMISSED_CACHE: dict = {}


def _commander_dismissals(ledger_path=None) -> dict:
    """Map alert-id -> timestamp of the Commander's most recent close/override.

    WHY THIS EXISTS (2026-07-29). `build_strategic`/`build_operational`
    regenerated every alert card from state on EVERY sync, `unread: True`, with
    no check for whether the Commander had already answered. tcd-sync runs
    roughly every ten minutes, so a close was erased on the next tick.

    The ledger for alert-MCLEOD-2984034-FPD-TRIGGER records the cost:

      Jul 29 00:36  "will contact Erik McLeod re: $11,943.15 FPD directly"
      Jul 29 03:50  "FBD accomplished 20 July, 8 days ago"
      Jul 29 03:54  "FBD accomplished 20 July, 8 days ago"   (again)
      Jul 29 04:10  (card re-raised anyway)
      Jul 29 17:35  "AS I have stated many times, the final payment
                     has been submitted"

    Five answers over eighteen hours about a payment completed on 20 July. The
    system had no memory of being answered, so re-detection masqueraded as
    diligence. Detecting a thing repeatedly is not tracking it (MAST FM-1.3).
    """
    key = str(ledger_path or _SILVER_LEDGER)
    if key in _DISMISSED_CACHE:
        return _DISMISSED_CACHE[key]
    out: dict = {}
    try:
        voided = set()
        rows = []
        for line in Path(key).read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
        # VOID annotations retract synthetic/test rows so a probe can never
        # silence a real alert.
        for r in rows:
            if r.get("verdict") == "VOID":
                voided.add(r.get("mission_id"))
        for r in rows:
            mid = r.get("mission_id") or ""
            if mid in voided:
                continue
            wp = r.get("work_product") or ""
            is_override = r.get("verdict") == "OVERRIDE"
            is_cmdr_close = "Commander CLOSE" in wp or "Commander via" in wp
            if not (is_override or is_cmdr_close):
                continue
            ts = r.get("ts") or ""
            if ts > out.get(mid, ""):
                out[mid] = ts
    except FileNotFoundError:
        pass
    except Exception:
        pass
    _DISMISSED_CACHE[key] = out
    return out


def _alert_answered(alert, dismissals) -> bool:
    """Has the Commander already answered THIS alert since it last triggered?

    Deliberately compares against the alert's own trigger_date, so a genuinely
    NEW trigger (a later date — a new deadline, a changed amount) surfaces
    again. Suppressing forever would be the opposite failure: a real recurrence
    silently swallowed.
    """
    mid = f"alert-{alert.get('id')}"
    when = dismissals.get(mid) or dismissals.get(str(alert.get("id")))
    if not when:
        return False
    trig = (alert.get("trigger_date") or "")[:19]
    return not trig or when[:19] >= trig


def build_strategic(state):
    files = []
    dismissals = _commander_dismissals()
    for a in state.get("deferred_alerts", []):
        if _alert_answered(a, dismissals):
            continue
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
        counts = count_untouched_elon_proposals()
        if counts:
            proposal_line = (
                f"Proposal backlog: {counts['untouched']} of {counts['total']} "
                f"OpsCenter/elon_proposals/*.md files have no matching "
                f"*_EXECUTION.md (proxy for 'genuinely untouched' — not exact).\n"
                f"CORRECTION (2026-07-13, MISSION-001A): hale_state.json's "
                f"open_proposals_raw_count ({elon.get('proposal_queue', {}).get('open_proposals_raw_count', '?')}) "
                f"is a raw never-archived file count, NOT an undecided-proposal "
                f"count — the CLOSED/ archive protocol was never adopted, so "
                f"most of those files are already-executed work that was never "
                f"moved out. The figure above replaces it."
            )
        else:
            proposal_line = "Proposal backlog: unable to scan OpsCenter/elon_proposals/."
        body = (f"ELON verification pass — {elon.get('verification_method', '')}\n\n"
                f"Claimed: {claim}\n"
                f"Committed to git: {verified.get('committed_to_git', '?')}\n"
                f"Passing both bars (committed + wired): {verified.get('passing_both_bars_committed_and_wired', '?')}\n"
                f"No file evidence found: {verified.get('no_file_evidence_found', '?')}\n\n"
                f"{proposal_line}")
        files.append({
            "id": "elon-verify-latest", "inbox": "strategic", "folder": "s-elon",
            "type": "paper", "priority": "p1", "unread": True,
            "title": "ELON proposal verification — claimed vs. git-verified counts diverge",
            "from": "A14 Whetstone", "date": elon.get("last_verified", "")[:10],
            "snippet": _snip(body), "body": body,
            "tags": ["ELON", "verification"], "comments": [],
        })
    a7_alert = build_a7_metrics_alert()
    if a7_alert:
        files.append(a7_alert)
    cadence_alert = build_staff_cadence_alert()
    if cadence_alert:
        files.append(cadence_alert)
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
    dismissals = _commander_dismissals()
    for a in state.get("deferred_alerts", []):
        if a.get("priority") not in ("P1", "P2"):
            continue
        if a.get("amount"):
            continue
        if _alert_answered(a, dismissals):
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


def build_missions(state, mission_board=None):
    """Wing Tasking missions (OpsCenter/mission_board.json) as Items, folded
    into the SAME PDTAC pipeline as everything else — one review surface,
    no separate untracked taxonomy. Skips any mission whose id already
    appears as a hale_state.json open_task (task-<id>) so nothing double-
    counts if the two ever overlap.
    """
    mission_board = mission_board if mission_board is not None else _load_json(MISSION_BOARD, {})
    open_task_ids = {t.get("id", "") for t in state.get("open_tasks", [])}
    files = []
    for m in mission_board.get("missions", []):
        mid = m.get("id", "")
        if not mid or mid in open_task_ids:
            continue
        body = m.get("description", "") or m.get("title", "")
        files.append({
            "id": f"mission-{mid}", "inbox": "operational", "folder": "o-dailyops",
            "type": "brief", "priority": _pri(m.get("priority")),
            "unread": m.get("status") == "pending_review",
            "title": m.get("title", ""), "from": f"{m.get('assigned_to', 'Wing')} · Wing Tasking",
            "date": (m.get("updated_at", "") or m.get("created_at", ""))[:10],
            "snippet": _snip(body), "body": body,
            "tags": ["mission", m.get("status", "")], "comments": [],
            "status": m.get("status", ""),
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


# Outbox noise filter — hale_decisions.md PLAN:CLOSE entries are written by every
# background watchdog/CI-repair lane on every cooldown/retry cycle, not just real
# Commander decisions. These patterns match routine automated pings (session
# warming, crash-report filing, cooldown backoffs, Lane-1 deferrals) so the
# Outbox only surfaces closures a human would recognize as a decision.
_OUTBOX_NOISE_NOTES = re.compile(
    r"cooldown active|deferred to Lane 1|warmed \+ re-saved \d+ cookies|"
    r"start attempted \(ok=|self-alerting unit|session warmed \+ authenticated|"
    r"recovered.{0,3}verified active|auto-filed by backstop hook|^repaired=|"
    r"skipped \(profile locked|never reached assessment|^error: Connection timed out",
    re.I,
)
_OUTBOX_NOISE_CRITERIA = re.compile(
    r"crash report written to|flagged units recorded to", re.I,
)


def build_outbox():
    text = HALE_DECISIONS.read_text(errors="ignore") if HALE_DECISIONS.exists() else ""
    entries = re.findall(
        r"<!-- PLAN:CLOSE plan_id=(\S+) verdict=(\S+) .*?closed_at=(\S+?) -->\n"
        r"\*\*Plan Closed:\*\* \S+\n\*\*Verdict:\*\* \S+\n\*\*Quality tier:\*\* .*?\n"
        r"\*\*Criteria met:\*\* (.*?)\n.*?\*\*Notes:\*\* (.*?)\n",
        text, re.S,
    )
    outbox = []
    for plan_id, verdict, closed_at, criteria_met, notes in entries:
        if _OUTBOX_NOISE_NOTES.search(notes) or _OUTBOX_NOISE_CRITERIA.search(criteria_met):
            continue
        outbox.append({
            "id": f"ob-{plan_id}", "fileId": None,
            "title": (criteria_met if criteria_met and criteria_met != "none" else notes)[:110],
            "executed": verdict == "PASS", "execDate": closed_at[:16].replace("T", " "),
            "from": "hale_decisions.md audit trail",
            "stage": "C" if verdict == "PASS" else "A",
        })
    return outbox[-40:]


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


# ---------------------------------------------------------------------------
# DELETE — cascading source cleanup
#
# the retired TCD web app owned the HTTP layer and audit-trail append; this module owns
# knowing where each file id's foundation record actually lives and how to
# remove it. Every deletion path is recoverable: JSON-backed records are
# backed up to TCD_TRASH/deleted_json_records.jsonl before removal, and
# file-backed records (standing orders, dossiers) are moved into TCD_TRASH
# rather than unlinked. Gmail messages are trashed via the API (30-day Gmail
# trash), never permanently deleted.
# ---------------------------------------------------------------------------

def _atomic_write_json(path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    tmp.replace(path)


def _backup_record(kind, entry_id, record):
    TCD_TRASH.mkdir(parents=True, exist_ok=True)
    log = TCD_TRASH / "deleted_json_records.jsonl"
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "kind": kind,
              "entry_id": entry_id, "record": record}
    with log.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def _delete_state_list_entry(list_path, entry_id):
    """list_path: tuple of keys locating a list in hale_state.json, e.g.
    ('open_tasks',) or ('project_tracking', 'active_projects')."""
    state = _load_json(HALE_STATE, {})
    container = state
    for key in list_path[:-1]:
        container = container.setdefault(key, {})
    lst = container.setdefault(list_path[-1], [])
    idx = next((i for i, e in enumerate(lst) if e.get("id") == entry_id), None)
    if idx is None:
        return {"ok": False, "reason": f"'{entry_id}' not found in hale_state.json:{'.'.join(list_path)}"}
    removed = lst.pop(idx)
    _backup_record(".".join(list_path), entry_id, removed)
    _atomic_write_json(HALE_STATE, state)
    return {"ok": True, "source": f"hale_state.json:{'.'.join(list_path)}", "removed": removed}


def _delete_mission_board_entry(entry_id):
    board = _load_json(MISSION_BOARD, {})
    lst = board.setdefault("missions", [])
    idx = next((i for i, e in enumerate(lst) if e.get("id") == entry_id), None)
    if idx is None:
        return {"ok": False, "reason": f"'{entry_id}' not found in mission_board.json:missions"}
    removed = lst.pop(idx)
    _backup_record("mission_board.missions", entry_id, removed)
    _atomic_write_json(MISSION_BOARD, board)
    return {"ok": True, "source": "mission_board.json:missions", "removed": removed}


def _delete_source_file(dir_path, filename):
    src = dir_path / filename
    if not src.is_file():
        return {"ok": False, "reason": f"source file not found: {src}"}
    TCD_TRASH.mkdir(parents=True, exist_ok=True)
    dest = TCD_TRASH / f"{datetime.now():%Y%m%d-%H%M%S}_{filename}"
    src.rename(dest)
    return {"ok": True, "source": str(src), "trashed_to": str(dest)}


def _delete_gmail_message(file_id):
    rest = file_id[len("gmail-"):]
    account, msg_id = None, None
    for acct, _getter in GMAIL_ACCOUNTS:
        if rest.startswith(acct + "-"):
            account, msg_id = acct, rest[len(acct) + 1:]
            break
    if not account:
        return {"ok": False, "reason": f"could not parse gmail account from '{file_id}'"}
    try:
        import thunderbird_google_auth as gauth
        getter_name = dict(GMAIL_ACCOUNTS)[account]
        svc = getattr(gauth, getter_name)()
        svc.users().messages().trash(userId="me", id=msg_id).execute()
        _gmail_cache["ts"] = 0  # force refresh so it drops out of Operational immediately
        return {"ok": True, "source": f"gmail:{account}:{msg_id}",
                "action": "trashed via Gmail API (recoverable from Gmail Trash for 30d)"}
    except Exception as e:
        return {"ok": False, "reason": f"gmail trash failed: {e}"}


def delete_item(file_id):
    """Remove the foundation source record backing a TCD file id.
    Never raises — always returns {"ok": bool, ...} so the caller can still
    hide the item from the TCD view even when no foundation record exists."""
    if file_id.startswith("alert-"):
        return _delete_state_list_entry(("deferred_alerts",), file_id[len("alert-"):])
    if file_id.startswith("task-"):
        return _delete_state_list_entry(("open_tasks",), file_id[len("task-"):])
    if file_id.startswith("proj-"):
        return _delete_state_list_entry(("project_tracking", "active_projects"), file_id[len("proj-"):])
    if file_id.startswith("so-"):
        return _delete_source_file(STANDING_ORDERS, file_id[len("so-"):] + ".md")
    if file_id.startswith("dossier-"):
        return _delete_source_file(DOSSIERS, file_id[len("dossier-"):] + ".md")
    if file_id.startswith("gmail-"):
        return _delete_gmail_message(file_id)
    if file_id.startswith("mission-"):
        return _delete_mission_board_entry(file_id[len("mission-"):])
    return {"ok": False, "reason": f"no foundation source mapped for id '{file_id}' — hidden in TCD only"}


def build_data(include_gmail=True):
    state = _load_json(HALE_STATE, {})
    files = build_strategic(state) + build_operational(state) + build_reference()
    if include_gmail:
        files = build_gmail() + files
    return {"folders": FOLDERS, "files": files, "outbox": build_outbox(),
            "generated_at": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    print(json.dumps(build_data(), indent=2)[:3000])
