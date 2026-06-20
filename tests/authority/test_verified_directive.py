import sys
sys.path.insert(0, "/home/john/Thunderbird")
from core.authority.verified_directive import match_directive, COMMANDER_TG_ID

NOW = 1_000_000.0


def _rec(text, from_id=COMMANDER_TG_ID, ago_hours=0.0, message_id=1):
    return {"channel": "telegram", "message_id": message_id, "from_id": from_id,
            "chat_id": COMMANDER_TG_ID, "date": NOW - ago_hours * 3600, "text": text}


def test_exact_match_from_commander_verifies():
    recs = [_rec("five chapters, Leviathan keel, fly it")]
    m = match_directive(recs, "five chapters, Leviathan keel, fly it", now_ts=NOW)
    assert m is not None and m["message_id"] == 1


def test_substring_match_verifies():
    recs = [_rec("ok do it: five chapters, Leviathan keel, fly it — go")]
    m = match_directive(recs, "five chapters, Leviathan keel, fly it", now_ts=NOW)
    assert m is not None


def test_no_record_is_unverified():
    assert match_directive([], "fly it", now_ts=NOW) is None


def test_wrong_sender_does_not_verify():
    # someone else's id saying it — NOT the Commander
    recs = [_rec("fly it", from_id=999999)]
    assert match_directive(recs, "fly it", now_ts=NOW) is None


def test_stale_record_does_not_verify():
    recs = [_rec("fly it", ago_hours=48)]  # older than 24h window
    assert match_directive(recs, "fly it", now_ts=NOW, recency_hours=24) is None


def test_fresh_within_window_verifies():
    recs = [_rec("fly it", ago_hours=2)]
    assert match_directive(recs, "fly it", now_ts=NOW, recency_hours=24) is not None


def test_confabulated_text_not_in_source_is_unverified():
    # the coordinator claims a directive the Commander never sent → no source record matches
    recs = [_rec("send the morning brief")]
    assert match_directive(recs, "delete the production database", now_ts=NOW) is None


def test_empty_directive_never_verifies():
    recs = [_rec("anything")]
    assert match_directive(recs, "", now_ts=NOW) is None


def test_prefers_most_recent_match():
    recs = [_rec("fly it", ago_hours=5, message_id=10), _rec("fly it", ago_hours=1, message_id=20)]
    m = match_directive(recs, "fly it", now_ts=NOW)
    assert m["message_id"] == 20
