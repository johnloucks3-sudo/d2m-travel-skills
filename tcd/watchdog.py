"""
watchdog — generic long-tail collector for OpsCenter/*.json files that were
never wired into TCD (MISSION-001A Phase 3, D-tier: "~50 more OpsCenter
watchdog/financial/alert-dedup files").

What's genuinely generic here is the SCAFFOLD, not per-file logic: each
file's alert semantics are too heterogeneous (different schemas, different
"this is worth surfacing" conditions) for a single JSON-shape inference, so
every registry entry still carries a short purpose-built ``extract_fn``.
What the scaffold buys: one shared collection loop, try/except isolation
per file (one bad/missing file never blocks the batch — same fail-soft
contract as ``tcd/collectors.py``'s Gmail/Keep/SMS collectors), consistent
``watch-<slug>`` id namespacing, and ONE place to register a new file
instead of a new one-off builder function every time.

To extend: write a small ``extract_fn(data: dict) -> Optional[dict]`` that
returns ``None`` when nothing is alert-worthy, or a legacy tcd_data-shaped
item dict otherwise (id/inbox/folder/type/priority/title/from/date/snippet/
body/tags/comments), and append ``(path, extract_fn)`` to ``REGISTRY``.
"""
import json
import sys
from datetime import date, datetime
from pathlib import Path

from . import _imports

ROOT = _imports.ROOT
OPSCENTER = ROOT / "OpsCenter"


def _load_json(path):
    """Missing/unparseable file -> {} (every extract_fn treats an empty
    dict as "nothing alert-worthy" and returns None, same fail-quiet
    contract as a genuinely healthy file)."""
    try:
        return json.loads(Path(path).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _snip(text, n=220):
    text = " ".join((text or "").split())
    return text[:n] + ("…" if len(text) > n else "")


def _extract_staff_tasking(d: dict):
    """staff_tasking_schedule.json — surface only when a task is flagged
    critical; quiet log otherwise."""
    critical = [t for t in d.get("tasks", []) if t.get("critical")]
    if not critical:
        return None
    body = "\n".join(
        f"- {t.get('task_id', '')}: {t.get('client', '')} — "
        f"{t.get('deliverable', '')} (due {t.get('draft_due', '')[:10]})"
        for t in critical
    )
    return {
        "id": "watch-staff-tasking-critical", "inbox": "operational", "folder": "o-dailyops",
        "type": "decision", "priority": "p1", "unread": True,
        "title": f"Staff tasking — {len(critical)} critical touchpoint(s) flagged",
        "from": "Staff Tasking Schedule", "date": d.get("generated_at", "")[:10],
        "snippet": _snip(body), "body": body,
        "tags": ["staff-tasking", "critical"], "comments": [],
    }


def _extract_hale_incidents(d: dict):
    """hale_incidents_today.json — surface only when today has unresolved
    incidents; quiet log otherwise."""
    unresolved = d.get("summary", {}).get("unresolved", 0)
    if not unresolved:
        return None
    open_incidents = [i for i in d.get("incidents", []) if i.get("status") not in ("GREEN", "resolved")]
    body = "\n".join(
        f"- {i.get('time', '')} {i.get('service', '')}: {i.get('note', i.get('event_type', ''))}"
        for i in open_incidents[:10]
    )
    return {
        "id": f"watch-incidents-{d.get('date', 'today')}", "inbox": "operational",
        "folder": "o-vendor", "type": "decision", "priority": "p1", "unread": True,
        "title": f"{unresolved} unresolved incident(s) today ({d.get('date', '')})",
        "from": "Hale Incidents", "date": d.get("date", ""),
        "snippet": _snip(body), "body": body,
        "tags": ["incidents", "unresolved"], "comments": [],
    }


def _extract_prediction_ledger(d):
    """commander_prediction_ledger.json — surface only stale (>=7d), still-
    open predictions; roll up as ONE item, not one per prediction (this is
    a monitoring log, not individually distinct decisions)."""
    if not isinstance(d, list):
        return None
    today = date.today()
    stale = []
    for p in d:
        if p.get("status") != "open":
            continue
        try:
            predicted = datetime.strptime(p.get("date_predicted", ""), "%Y-%m-%d").date()
        except ValueError:
            continue
        if (today - predicted).days >= 7:
            stale.append(p)
    if not stale:
        return None
    body = "\n".join(f"- {p.get('id', '')} ({p.get('date_predicted', '')}): "
                     f"{p.get('predicted_action', '')[:140]}" for p in stale[:10])
    return {
        "id": "watch-prediction-ledger-stale", "inbox": "operational", "folder": "o-dailyops",
        "type": "decision", "priority": "p2", "unread": True,
        "title": f"Commander prediction ledger — {len(stale)} open prediction(s) >=7d stale",
        "from": "Prediction Ledger", "date": today.isoformat(),
        "snippet": _snip(body), "body": body,
        "tags": ["prediction-ledger", "stale"], "comments": [],
    }


def _extract_incubator_gate(d: dict):
    """eod_incubator_config.json — surface an approved-but-unactioned gate
    candidate (a capability nomination that cleared review but nobody has
    followed through on); quiet otherwise."""
    gc = d.get("gate_candidate", {})
    if gc.get("status") != "approved":
        return None
    body = f"{gc.get('name', '')} — owner {gc.get('owner', '?')}\n\n{gc.get('description', '')}"
    return {
        "id": f"watch-incubator-gate-{gc.get('name', 'candidate')[:40]}", "inbox": "strategic",
        "folder": "s-inbox", "type": "decision", "priority": "p2", "unread": True,
        "title": f"Incubator gate candidate approved, unactioned: {gc.get('name', '')}",
        "from": f"{gc.get('owner', 'Wing')} · EOD Incubator", "date": d.get("last_updated", "")[:10],
        "snippet": _snip(body), "body": body,
        "tags": ["incubator", "gate-candidate"], "comments": [],
    }


# (path, extract_fn) — extend here to register a new file. extract_fn takes
# the parsed JSON (dict or list) and returns None or a legacy item dict.
REGISTRY = (
    (OPSCENTER / "staff_tasking_schedule.json", _extract_staff_tasking),
    (OPSCENTER / "hale_incidents_today.json", _extract_hale_incidents),
    (OPSCENTER / "commander_prediction_ledger.json", _extract_prediction_ledger),
    (OPSCENTER / "eod_incubator_config.json", _extract_incubator_gate),
)


def collect_watchdog(registry=None) -> list:
    """Run every registered (path, extract_fn) pair; one bad file's
    exception is recorded to stderr and skipped, never blocks the batch."""
    registry = registry if registry is not None else REGISTRY
    items = []
    for path, extract_fn in registry:
        try:
            data = _load_json(path)
            item = extract_fn(data)
            if item:
                items.append(item)
        except Exception as e:
            print(f"tcd.watchdog: {path} failed: {e}", file=sys.stderr)
    return items
