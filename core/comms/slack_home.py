import json
from collections import OrderedDict
from datetime import datetime, date as date_type
from pathlib import Path


MAX_VIEW_BLOCKS = 100

SHEET_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "tcd_sheet_config.json"

# Band 2 well-known URLs. Only these -- never invent a link (see _front_door_blocks).
GMAIL_URL = "https://mail.google.com/mail/u/0/#inbox"
DRIVE_URL = "https://drive.google.com/drive/my-drive"
CALENDAR_URL = "https://calendar.google.com/"
KEEP_URL = "https://keep.google.com/"
EVERNOTE_URL = "https://www.evernote.com/client/web"
# Obsidian deep-link. The vault name is inferred from this repo's own basename
# -- a ".obsidian" config dir lives at the repo root, confirming it IS the
# vault -- so this only resolves on a machine that already has that vault
# open locally; on any other machine the tap is a no-op, not an error.
OBSIDIAN_URL = "obsidian://open?vault=Thunderbird"

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


def _alert_items(items: list[dict]) -> list[dict]:
    """Band 1 selection: only what urgency itself puts on screen.

    Mirrors the P0/overdue short-circuit in _assign_items exactly -- priority
    P0 or a past suspense date, the two conditions nothing about workflow
    status can hide. Deliberately narrower than the old "Awaiting You"
    grouping (which also pulled in pending_review/deferred and any Strategic-
    inbox item): this tab is a front door, not a board, so only genuine
    alerts render here. Everything else lives in the Sheet, one tap away via
    Band 2.
    """
    alerts = [
        it for it in items
        if (it.get("priority", "") or "").strip().lower() == "p0" or _is_overdue(it)
    ]
    alerts.sort(key=_sort_key)
    return alerts


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
    #
    # NOTE (2026-07-30 three-band rework): this "Awaiting You" grouping is retained
    # here ONLY because home_item_count() must keep counting every section of the
    # board for the top summary line's total. build_home_view() no longer renders
    # this grouping as Band 1 -- see _alert_items() for what Band 1 actually shows.
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


def _sheet_config() -> dict:
    """Parsed config/tcd_sheet_config.json, or {} if absent/unreadable.

    Single read shared by the Sheet row's URL and its live row count (see
    _front_door_blocks) so that "cheap to compute" stays true -- one file
    read, no network call, never re-parsed twice for the same row.
    """
    try:
        return json.loads(SHEET_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _tool_row(emoji: str, name: str, url: str, count: str = "") -> dict:
    """One Band 2 front-door row: emoji + name + optional cheap count + link.

    Always exactly one block (a section, no accessory) -- the "one block, not
    two" constraint the Commander asked for is then trivially true rather
    than something to keep re-verifying. A missing url degrades to plain
    text, never a broken link -- never invent what isn't configured.
    """
    suffix = f"  ·  {count}" if count else ""
    if url:
        text = f"{emoji} *{name}*{suffix} — <{url}|Open>"
    else:
        text = f"{emoji} *{name}*{suffix} — (no link configured)"
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def _front_door_blocks() -> list[dict]:
    """Band 2: THE FRONT DOOR. One row per tool -- this tab links out, it does
    not replace any of these. The Sheet leads because it IS the board (PDTAC
    lives there and works); its row is the only one that gets a live count,
    because that count (last_row_count) is already sitting in the same config
    read as its URL -- genuinely free, unlike every other tool here, which
    would need a network call this function deliberately never makes.
    """
    cfg = _sheet_config()
    sheet_url = cfg.get("spreadsheet_url") or ""
    if not isinstance(sheet_url, str):
        sheet_url = ""
    row_count = cfg.get("last_row_count")
    sheet_count = f"{row_count} rows synced" if isinstance(row_count, int) else ""

    rows = [
        _tool_row(":bar_chart:", "Sheet — the board", sheet_url, sheet_count),
        _tool_row(":email:", "Gmail", GMAIL_URL),
        _tool_row(":file_folder:", "Drive", DRIVE_URL),
        _tool_row(":calendar:", "Calendar", CALENDAR_URL),
        _tool_row(":notepad_spiral:", "Keep", KEEP_URL),
        # No number is configured for a general "Texts" inbox (distinct from
        # the Commander's own cell) anywhere in this repo -- skip rather than
        # invent one. Flip this to sms:<number> the day a real source exists.
        _tool_row(":speech_balloon:", "Texts", ""),
        _tool_row(":elephant:", "Evernote", EVERNOTE_URL),
        _tool_row(":large_blue_diamond:", "Obsidian", OBSIDIAN_URL),
    ]
    return [_header_block("Front Door")] + rows


def _task_band_blocks() -> list[dict]:
    """Band 3: TASK. A single button; another agent wires the modal behind
    action_id="open_task_modal" -- this function only emits the entry point.
    """
    return [
        _header_block("Task"),
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "+ New Task", "emoji": True},
                    "action_id": "open_task_modal",
                    "value": "new",
                }
            ],
        },
    ]


def _summary_block(total: int, alerts: int) -> dict:
    """Top-of-tab context block: what the board holds and what's on fire.

    `total` covers every item passed in, across all sections -- so scoping
    Band 1 down to alerts-only never costs the Commander his sense of how
    much is on the board; that count is still on screen even though this
    view doesn't itemize it (the full board is one tap away in Band 2).
    """
    plural = "" if alerts == 1 else "s"
    text = f"{total} open on the board · {alerts} alert{plural} right now"
    return {"type": "context", "elements": [{"type": "mrkdwn", "text": text}]}


def build_home_view(items: list[dict]) -> dict:
    """Render the Commander's Slack App Home as a three-band FRONT DOOR.

    This is NOT the board -- the Google Sheet is the board (PDTAC is embedded
    there and works). Slack's job here is narrower and stays that way:

      Band 1 ALERTS       -- only what urgency itself surfaces: P0 or past
                              suspense (see _alert_items). Empty most days;
                              emptiness is the signal the Commander is
                              actually clear, not that nothing was checked.
      Band 2 FRONT DOOR    -- one row per tool, deep link + cheap count where
                              one exists, Sheet first because it's the board.
      Band 3 TASK          -- one button that opens the task-intake modal.

    THE INVARIANT (unchanged since the single-band version, 2026-07-29 AG
    parity audit, OpsCenter/state/ag_tcd_slack_parity.md): items rendered +
    items declared hidden == alerts in, always. The item budget is reserved
    against the fixed chrome FIRST -- top summary, Band 1 header, one
    overflow slot, all of Band 2, all of Band 3 -- never consumed
    first-come-first-served, so a real P0 can never disappear silently behind
    the 100-block cap. Slack's hard cap (MAX_VIEW_BLOCKS) is enforced by
    construction: fixed chrome + item_budget can never exceed it.
    """
    counts = home_item_count(items)
    total = sum(counts.values())
    alerts = _alert_items(items)
    alerts_total = len(alerts)

    band2 = _front_door_blocks()
    band3 = _task_band_blocks()

    # Reserve every non-negotiable block first: top summary (1), Band 1
    # header (1), one overflow slot in case Band 1 truncates (1), then all of
    # Band 2 and Band 3 in full -- they never get cut. Whatever's left is the
    # item budget for Band 1.
    reserved = 3 + len(band2) + len(band3)
    item_budget = max(0, MAX_VIEW_BLOCKS - reserved)
    show = min(alerts_total, item_budget)
    withheld = alerts_total - show

    band1_title = "Alerts" if alerts_total else "All clear — no P0s, nothing overdue"

    blocks: list[dict] = [_summary_block(total, alerts_total), _header_block(band1_title)]
    for it in alerts[:show]:
        blocks.append(_item_block(it))
    if withheld:
        blocks.append(_overflow_block("Alerts", withheld))
    blocks.extend(band2)
    blocks.extend(band3)

    return {"type": "home", "blocks": blocks}
