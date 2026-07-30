import json
from collections import OrderedDict
from datetime import datetime, date as date_type
from pathlib import Path


MAX_VIEW_BLOCKS = 100

SHEET_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "tcd_sheet_config.json"

_PRIORITY_RANK = {"p0": 0, "p1": 1, "p2": 2, "p3": 3}


def _priority_key(p: str) -> int:
    return _PRIORITY_RANK.get(p.strip().lower(), 99)


def _parse_date(d: str):
    if not d or not isinstance(d, str):
        return date_type.max
    try:
        return datetime.strptime(d.strip()[:10], "%Y-%m-%d").date()
    except (ValueError, IndexError):
        return date_type.max


def _is_overdue(item: dict) -> bool:
    """Past its suspense date. Independent of workflow status on purpose.

    An item does not stop being overdue because someone deferred it — that is
    precisely the move that made four P0s invisible for up to 36 days.
    """
    raw = item.get("suspense_date") or ""
    if not raw:
        return False
    try:
        return datetime.strptime(str(raw).strip()[:10], "%Y-%m-%d").date() < date_type.today()
    except (ValueError, IndexError):
        return False


def _sort_key(item: dict):
    return (_priority_key(item.get("priority", "")),
            _parse_date(item.get("date", "")))


def home_item_count(items: list[dict]) -> dict:
    assigned: dict[str, list] = _assign_items(items)
    return {name: len(v) for name, v in assigned.items() if v}


def _assign_items(items: list[dict]) -> OrderedDict:
    awaiting: list[dict] = []
    strategic: list[dict] = []
    operational: list[dict] = []
    reference: list[dict] = []
    watch: list[dict] = []

    seen: set[str] = set()

    # Two item shapes reach this function and they do NOT share a schema:
    #
    #   TCD items (tcd/item_model.py)      -> inbox='Strategic'|..., status='Open'
    #   commander_queue.build_queue()      -> NO inbox field at all, and status is
    #                                         'pending_review'|'deferred'|'in_coordination'
    #
    # The original test only matched the TCD shape, so against the live board every one
    # of the 76 real items fell through to Watch and App Home rendered EMPTY — a tab that
    # loads fine and shows the Commander nothing. Match both shapes explicitly.
    #
    # "Awaiting You" means: he personally has to decide. That is pending_review (the
    # literal meaning of the status), anything P0, and Strategic in the TCD shape.
    # THE BLIND SPOT, fixed 2026-07-30.
    #
    # This gate used to require `status in _OPEN` BEFORE considering priority — and
    # 'deferred' was not in _OPEN. Measured against the live board that hid:
    #   4 of 4 P0 items, and 10 of 10 overdue items. Every single one.
    # The 50 items it DID show were 49 P1s and one P2 — the least urgent work on the
    # board — while four P0s sat 10-36 days overdue, invisible. Every item carrying a
    # client name was also in the hidden set.
    #
    # That is the exact "items aging unseen" failure this whole surface exists to
    # prevent, reproduced inside the fix for it. Written 2026-07-29, never tested
    # against a deferred item.
    #
    # NEW RULE: urgency outranks workflow status. A P0 or a past-suspense item is
    # shown REGARDLESS of status — being deferred does not make an overdue P0 stop
    # mattering. `deferred` is now also a legitimately open state in its own right.
    _OPEN = {"open", "pending_review", "in_coordination", "deferred"}
    _AWAITING_STATUS = {"pending_review", "deferred"}

    for item in items:
        status = (item.get("status", "") or "").strip().lower()
        inbox = (item.get("inbox", "") or "").strip().lower()
        priority = (item.get("priority", "") or "").strip().lower()

        # Urgency short-circuit: nothing about workflow state can hide these.
        if priority == "p0" or _is_overdue(item):
            awaiting.append(item)
            seen.add(item["id"])
            continue

        if status in _OPEN and (
            status in _AWAITING_STATUS or inbox == "strategic"
        ):
            awaiting.append(item)
            seen.add(item["id"])

    for item in items:
        if item["id"] in seen:
            continue
        inbox = (item.get("inbox", "") or "").strip().lower()
        if inbox == "strategic":
            strategic.append(item)
        elif inbox == "operational":
            operational.append(item)
        elif inbox == "reference":
            reference.append(item)
        else:
            watch.append(item)

    awaiting.sort(key=_sort_key)
    strategic.sort(key=_sort_key)
    operational.sort(key=_sort_key)
    reference.sort(key=_sort_key)
    watch.sort(key=_sort_key)

    result: OrderedDict[str, list[dict]] = OrderedDict()
    result["Awaiting You"] = awaiting
    result["Strategic"] = strategic
    result["Operational"] = operational
    result["Reference"] = reference
    result["Watch"] = watch
    return result


_DAYS_AGO = date_type.today()


def _days_ago(d: str) -> str:
    dt = _parse_date(d)
    if dt is date_type.max:
        return ""
    delta = (_DAYS_AGO - dt).days
    if delta < 0:
        return "0d ago"
    return f"{delta}d ago"


def _badge(priority: str) -> str:
    p = priority.strip().lower()
    if p == "p0":
        return ":red_circle: P0"
    if p == "p1":
        return ":large_orange_circle: P1"
    if p == "p2":
        return ":large_yellow_circle: P2"
    if p == "p3":
        return ":white_circle: P3"
    return f":black_circle: {priority}"


def _header_block(title: str) -> dict:
    return {
        "type": "header",
        "text": {"type": "plain_text", "text": title, "emoji": True},
    }


def _item_block(item: dict) -> dict:
    title = item.get("title", "Untitled")
    priority = item.get("priority", "")
    source = item.get("source", "")
    days = _days_ago(item.get("date", ""))
    meta = f"*{title}* | {_badge(priority)} | {source} | {days}"
    item_id = item.get("id", "")

    return {
        "type": "section",
        "text": {"type": "mrkdwn", "text": meta},
        "accessory": {
            "type": "button",
            "text": {"type": "plain_text", "text": "Close"},
            "action_id": "close",
            "value": item_id,
        },
    }


def _overflow_block(section: str, count: int) -> dict:
    return {
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"+{count} more in {section}"}
        ],
    }


def _sheet_url() -> str:
    """spreadsheet_url from config/tcd_sheet_config.json, or "" if absent.

    Never invent a link — a wrong URL sends the Commander to a blank tab looking for
    the board he was just told exists. Absent config degrades to plain text below.
    """
    try:
        cfg = json.loads(SHEET_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    url = cfg.get("spreadsheet_url")
    return url.strip() if isinstance(url, str) and url.strip() else ""


def _summary_block(total: int, awaiting: int) -> dict:
    """Top-of-tab context block: the count this scoped view does NOT show.

    App Home renders Awaiting You only (see build_home_view), so without this line
    scoping the view down would cost the Commander his sense of the total board —
    trading "items aging unseen" for "items he doesn't know exist." This line is the
    fix: he always sees the full-board number even though he isn't looking at it.
    """
    text = f"{total} open · {awaiting} awaiting your decision · full board in Sheets"
    return {"type": "context", "elements": [{"type": "mrkdwn", "text": text}]}


def _sheet_footer_block() -> dict:
    """Bottom-of-tab link out to the Sheet for bulk work App Home cannot do.

    App Home is single-item buttons only — no drag-fill, no multi-select. Anything
    beyond a one-off Close belongs in the Sheet, so the way there is always on screen.
    """
    url = _sheet_url()
    text = f"<{url}|Full board: Google Sheets>" if url else "Full board: Google Sheets"
    return {"type": "context", "elements": [{"type": "mrkdwn", "text": text}]}


def build_home_view(items: list[dict]) -> dict:
    """Render ONLY what needs the Commander's decision — not the whole board.

    2026-07-29 AG parity audit (OpsCenter/state/ag_tcd_slack_parity.md): App Home is
    hard-capped at 100 blocks and cannot be threaded or tabbed. Rendering every section
    (Strategic/Operational/Reference/Watch) at 2 blocks/item hits that cap around 50
    items — with 200+ items on the board, ~150 go invisible behind a footer. That is
    the exact "items aging unseen" failure TCD existed to prevent. So this view no
    longer tries to be the whole board: it shows Awaiting You (status=='Open' and
    (priority=='P0' or inbox=='Strategic')) and nothing else. Bulk/tabbed work stays in
    the Sheet, one link away (see _sheet_footer_block).

    THE INVARIANT THIS FUNCTION EXISTS TO HOLD (unchanged from the prior version):
        items rendered + items declared hidden == items in
    for the Awaiting You set, always — the budget is reserved up front, never consumed
    first-come-first-served, so a full list can never disappear silently.

    The Commander must never lose sight of the total board just because this view is
    scoped: _summary_block carries the ALL-inboxes open count and the Awaiting You count
    every time, sourced from home_item_count() so the header line and the section content
    can never drift apart from double bookkeeping.
    """
    counts = home_item_count(items)
    total = sum(counts.values())
    awaiting: list[dict] = _assign_items(items)["Awaiting You"]
    awaiting_total = counts.get("Awaiting You", 0)

    top = _summary_block(total, awaiting_total)
    footer = _sheet_footer_block()

    if not awaiting:
        return {"type": "home", "blocks": [
            top, _header_block("Nothing awaiting your decision"), footer,
        ]}

    # Reserve the non-negotiable chrome first: top summary, section header, sheet
    # footer, and one slot in case an overflow footer is needed. Whatever survives is
    # the item budget — the same "reserve first" fix that closed the silent-loss bug.
    reserved = 4
    item_budget = max(0, MAX_VIEW_BLOCKS - reserved)
    show = min(len(awaiting), item_budget)
    withheld = len(awaiting) - show

    blocks: list[dict] = [top, _header_block("Awaiting You")]
    for it in awaiting[:show]:
        blocks.append(_item_block(it))
    if withheld:
        blocks.append(_overflow_block("Awaiting You", withheld))
    blocks.append(footer)

    return {"type": "home", "blocks": blocks}
