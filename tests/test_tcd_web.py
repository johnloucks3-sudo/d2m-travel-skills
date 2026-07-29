"""
Regression test for the TCD Decision Board's status/state bubble
(tcd/web.py `.status-pill`).

Incident (2026-07-29): the Commander reported the status bubble "still not
working" after two prior fix attempts. Root cause was NOT a code defect —
tcd/web.py on disk already had the fix (commit 1b967d2ea, `_action_state()` +
colored `.status-pill.<state>` CSS/JS) — but `client-portal-server.service`
(the long-lived process serving tcd.d2mluxury.quest) had been started
*before* that commit landed and never restarted, so it kept serving the old
module cached in `sys.modules` with the dead `<span class="status-pill">`
markup (empty, `display:none`, and only ever set client-side by JS that a
reload wiped).

This test locks down the code contract `_action_state`/`_card` must uphold:
a decided item (Approved/Held/Rejected/Closed/Modified) always renders a
*visible, labeled* pill from server-rendered HTML alone, with no client-side
JS required — so a stale-vs-fresh process is trivially distinguishable by
curling the page. Run against the pre-1b967d2ea tcd/web.py (bare
`<span class="status-pill"></span>` for every row) this fails.
"""
from tcd.web import _action_state, _card


def test_action_state_approved_from_stage():
    row = {"id": "gmail-1", "stage": "D", "status": "Open", "comments": ""}
    decided, label, css_key = _action_state(row)
    assert decided is True
    assert label == "APPROVED"
    assert css_key == "approved"


def test_action_state_held_from_status():
    row = {"id": "gmail-2", "stage": "P", "status": "Reference", "comments": ""}
    assert _action_state(row) == (True, "HELD", "held")


def test_action_state_rejected_from_status():
    row = {"id": "gmail-3", "stage": "P", "status": "Delete", "comments": ""}
    assert _action_state(row) == (True, "REJECTED", "rejected")


def test_action_state_closed_from_status():
    row = {"id": "gmail-4", "stage": "P", "status": "Closed", "comments": ""}
    assert _action_state(row) == (True, "CLOSED", "closed")


def test_action_state_modified_from_comment_marker():
    row = {
        "id": "gmail-5", "stage": "P", "status": "Open",
        "comments": "prior note\n[Commander via tcd.d2mluxury.quest] edited the title",
    }
    assert _action_state(row) == (True, "MODIFIED", "modified")


def test_action_state_undecided_returns_no_pill():
    row = {"id": "gmail-6", "stage": "P", "status": "Open", "comments": ""}
    assert _action_state(row) == (False, "", "")


def test_card_renders_visible_labeled_pill_for_decided_item():
    """The bug: a decided item served a bare, invisible pill span with no
    label and no `show`/state class — indistinguishable from an undecided
    item in the server-rendered HTML. The fix must always stamp a `show`
    class plus the state's css_key, and the human-readable label as text."""
    row = {
        "id": "mission-123", "stage": "D", "status": "Open", "title": "Test item",
        "priority": "p1", "from": "", "date": "", "link": "", "owner": "",
        "comments": "",
    }
    html_out = _card(row)
    assert '<span class="status-pill show approved">APPROVED</span>' in html_out
    assert 'class="card decided"' in html_out
    # The old broken markup this regresses against:
    assert '<span class="status-pill"></span>' not in html_out


def test_card_undecided_item_has_no_visible_pill():
    row = {
        "id": "mission-124", "stage": "P", "status": "Open", "title": "Test item",
        "priority": "p1", "from": "", "date": "", "link": "", "owner": "",
        "comments": "",
    }
    html_out = _card(row)
    assert '<span class="status-pill"></span>' in html_out
    assert "show" not in html_out.split('status-pill')[1].split('>')[0]
