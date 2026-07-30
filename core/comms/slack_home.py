from collections import OrderedDict
from datetime import datetime, date as date_type


MAX_VIEW_BLOCKS = 100

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

    for item in items:
        status = item.get("status", "")
        inbox = (item.get("inbox", "") or "").strip().lower()
        priority = (item.get("priority", "") or "").strip().lower()
        if status == "Open" and (inbox == "strategic" or priority == "p0"):
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


def build_home_view(items: list[dict]) -> dict:
    """Render the Commander's desk, never hiding work without saying so.

    THE INVARIANT THIS FUNCTION EXISTS TO HOLD:
        items rendered + items declared hidden == items in
    for every section, always.

    The first implementation broke it in a way that passed every acceptance criterion:
    when the 100-block budget ran out mid-list it recorded `hidden[section] = N` and
    moved on WITHOUT emitting a block — so the count lived in a dict the Commander never
    saw. With 150 items: 96 rendered, footer claimed 17 hidden, 54 actually were, and the
    Watch section vanished with no header at all. A desk that looks clear while it is not
    is the precise failure this whole migration exists to end, so the budget is now
    reserved up front rather than consumed first-come-first-served.

    Every non-empty section is GUARANTEED a header, and a footer whenever anything in it
    is withheld — even if the section can show zero items.
    """
    sections: OrderedDict[str, list[dict]] = _assign_items(items)
    live = [(name, its) for name, its in sections.items() if its]
    if not live:
        return {"type": "home", "blocks": [_header_block("Nothing on your desk")]}

    # Reserve the non-negotiable chrome first: one header per section, plus one footer
    # slot per section in case it needs one. Whatever survives is the item budget.
    reserved = 2 * len(live)
    item_budget = max(0, MAX_VIEW_BLOCKS - reserved)

    # Fair-share the item budget, then hand unused remainder to sections that want more,
    # so a small section never strands capacity a large one could use.
    share = item_budget // len(live)
    quota = {name: min(len(its), share) for name, its in live}
    leftover = item_budget - sum(quota.values())
    for name, its in live:
        if leftover <= 0:
            break
        want = len(its) - quota[name]
        take = min(want, leftover)
        quota[name] += take
        leftover -= take

    blocks: list[dict] = []
    for name, its in live:
        blocks.append(_header_block(name))
        show = quota[name]
        for si in its[:show]:
            blocks.append(_item_block(si))
        withheld = len(its) - show
        if withheld:
            blocks.append(_overflow_block(name, withheld))

    return {"type": "home", "blocks": blocks}
