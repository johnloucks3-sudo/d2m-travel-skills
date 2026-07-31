import re, json
from core.comms.slack_home import build_home_view, home_item_count, MAX_VIEW_BLOCKS


def _item(seq: int, **kw) -> dict:
    base = dict(
        id=f"TCD-{seq:04d}",
        inbox="operational",
        type="decision",
        priority="p2",
        stage="D",
        title=f"Item {seq}",
        source="Dani",
        date="2026-07-20",
        snippet="",
        body="",
        link="",
        sourcePath="",
        comments="",
        status="Open",
        owner="Hale",
    )
    base.update(kw)
    return base


def test_section_assignment():
    """Bucketing (_assign_items, reached via home_item_count) is UNCHANGED by
    the 2026-07-30 three-band rework -- only what build_home_view() renders
    changed. This test now checks both halves: the bucket counts still match
    the original assignment rules, and the RENDERED view only itemizes the
    P0 item (TCD-0002) in the Alerts band -- Strategic/Operational/Reference/
    Watch are counted (see test_home_item_count) but no longer itemized as
    section blocks with headers of their own."""
    items = [
        _item(1, inbox="strategic", status="Open", priority="p2",
              date="2026-07-15"),
        _item(2, inbox="strategic", status="Open", priority="p0",
              date="2026-07-16"),
        _item(3, inbox="strategic", status="Reference", priority="p2",
              date="2026-07-17"),
        _item(4, inbox="operational", status="Open", priority="p1",
              date="2026-07-18"),
        _item(5, inbox="reference", status="Closed", priority="p2",
              date="2026-07-19"),
        _item(6, inbox="", status="Open", priority="p3",
              date="2026-07-20"),
    ]

    counts = home_item_count(items)
    assert counts == {"Awaiting You": 2, "Strategic": 1, "Operational": 1,
                       "Reference": 1, "Watch": 1}

    view = build_home_view(items)
    text = json.dumps(view["blocks"])

    # Item 2 is p0 -> the only item rendered in Band 1 (Alerts). Item 1 is
    # strategic+Open (old "Awaiting You" route) but NOT p0/overdue, so under
    # the new contract it's counted, never itemized in the view.
    assert "TCD-0002" in text, "P0 item must render in the Alerts band"
    for missing in ("TCD-0001", "TCD-0003", "TCD-0004", "TCD-0005", "TCD-0006"):
        assert missing not in text, (
            f"{missing} is not p0/overdue -- must not be itemized in the view"
        )

    # Only two headers now: Band 1 title + "Front Door" + "Task" = 3 total,
    # not one per section.
    headers = [b["text"]["text"] for b in view["blocks"] if b.get("type") == "header"]
    assert headers == ["Alerts", "Front Door", "Task"], headers


def test_oldest_first_within_priority():
    # P0 always outranks an overdue P1 in Band 1 (Alerts); within a tier,
    # oldest date first. Only p0/overdue items ever render as items, so the
    # p1 items here are made overdue via suspense_date to stay eligible.
    items = [
        _item(1, priority="p1", date="2026-07-25", suspense_date="2020-01-01"),
        _item(2, priority="p1", date="2026-07-20", suspense_date="2020-01-01"),
        _item(3, priority="p0", date="2026-07-22"),
        _item(4, priority="p0", date="2026-07-18"),
    ]
    view = build_home_view(items)
    blocks = view["blocks"]
    # Filter to actual item rows (accessory Close button) -- Band 2's tool
    # rows are also "section" blocks but carry no accessory.
    item_blocks = [b for b in blocks
                   if b.get("type") == "section"
                   and b.get("accessory", {}).get("action_id") == "close"]

    seen_ids = [b["accessory"]["value"] for b in item_blocks]

    assert seen_ids == ["TCD-0004", "TCD-0003", "TCD-0002", "TCD-0001"], (
        f"Expected p0 oldest-first then overdue-p1 oldest-first: {seen_ids}"
    )


def test_100_block_cap():
    items = [
        _item(i, priority="p2", date="2026-07-01", inbox="operational")
        for i in range(1, 151)
    ]
    view = build_home_view(items)
    assert view["type"] == "home"
    assert len(view["blocks"]) <= MAX_VIEW_BLOCKS, (
        f"Blocks ({len(view['blocks'])}) exceeds {MAX_VIEW_BLOCKS}"
    )


def test_overflow_footer_exact_count():
    # p2/operational items are never alerts (not p0, not overdue) -- they
    # never truncate under the new contract. Use p0 items so Band 1 (Alerts)
    # actually exceeds its budget and produces a real overflow footer.
    items = [
        _item(i, priority="p0", date="2026-07-01", inbox="operational")
        for i in range(1, 151)
    ]
    view = build_home_view(items)
    assert len(view["blocks"]) <= MAX_VIEW_BLOCKS
    text = json.dumps(view["blocks"])

    matches = re.findall(r"\+(\d+) more in (\w[\w ]*)", text)
    assert len(matches) == 1, "Should have exactly one overflow footer (Band 1 only)"

    n_str, section = matches[0]
    assert section.strip() == "Alerts"
    hidden = int(n_str)
    assert hidden > 0, "Overflow count must be positive"

    rendered = sum(
        1 for b in view["blocks"]
        if b.get("type") == "section" and b.get("accessory", {}).get("action_id") == "close"
    )
    assert rendered + hidden == 150, (
        "no silent truncation: rendered + declared-hidden must equal total alerts"
    )


def test_home_item_count():
    items = [
        _item(1, inbox="strategic", status="Open", priority="p2",
              date="2026-07-15"),
        _item(2, inbox="strategic", status="Open", priority="p0",
              date="2026-07-16"),
        _item(3, inbox="operational", status="Open", priority="p1",
              date="2026-07-17"),
        _item(4, inbox="reference", status="Closed", priority="p2",
              date="2026-07-18"),
        _item(5, inbox="", status="Open", priority="p3",
              date="2026-07-19"),
    ]
    counts = home_item_count(items)
    assert isinstance(counts, dict)
    assert counts.get("Awaiting You", 0) >= 2
    assert counts.get("Watch", 0) >= 1
    assert counts.get("Reference", 0) >= 1
    assert sum(counts.values()) == len(items)


def test_empty_items():
    # Empty items must still show the Front Door + all-clear header -- a
    # blank tab reads as "nothing was checked", not "nothing to see".
    view = build_home_view([])
    assert view["type"] == "home"
    assert view["blocks"] != [], "empty items must not render a blank tab"

    headers = [b["text"]["text"] for b in view["blocks"] if b.get("type") == "header"]
    assert "All clear — no P0s, nothing overdue" in headers
    assert "Front Door" in headers
    assert "Task" in headers


def test_no_double_count_across_sections():
    items = [
        _item(1, inbox="strategic", status="Open", priority="p0",
              date="2026-07-15"),
        _item(2, inbox="operational", status="Open", priority="p2",
              date="2026-07-16"),
    ]
    view = build_home_view(items)
    text = json.dumps(view["blocks"])
    assert text.count("TCD-0001") == 1, "P0 alert should appear exactly once"
    # Item 2 isn't p0/overdue -- it's counted for the summary, never itemized,
    # so it must not leak into the rendered blocks at all (no double-render
    # across the Alerts band and the fixed Front Door/Task chrome either).
    assert text.count("TCD-0002") == 0, "non-alert item must not be itemized"

    counts = home_item_count(items)
    assert sum(counts.values()) == 2, "still counted toward the summary total"


def test_many_sections_all_overflow():
    # 100 p0 alerts (over Band 1's ~86-item budget, forcing real truncation)
    # plus 150 more items spread across every non-alert bucket -- confirms
    # home_item_count() still buckets all 250 correctly, the rendered view
    # stays under the block cap, and Band 1's overflow footer is exact even
    # with plenty of uncounted-in-Band-1 items sitting in other buckets.
    items = (
        [_item(i, priority="p0", date="2026-07-01", inbox="operational")
         for i in range(1, 101)]
        + [_item(i, inbox="strategic", priority="p1", date="2026-07-01",
                 status="Reference")
           for i in range(101, 141)]
        + [_item(i, inbox="operational", priority="p2", date="2026-07-01",
                 status="Open")
           for i in range(141, 181)]
        + [_item(i, inbox="reference", priority="p3", date="2026-07-01",
                 status="Closed")
           for i in range(181, 221)]
        + [_item(i, inbox="unknown", priority="routine", date="2026-07-01",
                 status="Open")
           for i in range(221, 251)]
    )
    assert len(items) == 250

    counts = home_item_count(items)
    assert counts == {"Awaiting You": 100, "Strategic": 40, "Operational": 40,
                       "Reference": 40, "Watch": 30}
    assert sum(counts.values()) == 250

    view = build_home_view(items)
    assert len(view["blocks"]) <= MAX_VIEW_BLOCKS

    text = json.dumps(view["blocks"])
    overflow_matches = re.findall(r"\+(\d+) more in Alerts", text)
    assert len(overflow_matches) == 1, "Band 1 (Alerts) should overflow with 100 alerts"

    hidden = int(overflow_matches[0])
    rendered = sum(
        1 for b in view["blocks"]
        if b.get("type") == "section" and b.get("accessory", {}).get("action_id") == "close"
    )
    assert rendered + hidden == 100, "no silent truncation in Band 1"
