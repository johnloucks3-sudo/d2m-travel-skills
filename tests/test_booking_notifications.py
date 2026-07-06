import json
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from core.notifications import booking_notifications as bn
from core.notifications.booking_notifications import (
    Channel,
    NotificationContext,
    NotificationEvent,
    NotificationPrefs,
    already_fired,
    build_context,
    fire_event,
    get_prefs,
    mark_fired,
    notify_booking_confirmed,
    render,
    run_daily_scan,
    scan_client,
)


LIVE_ENV = {"TWILIO_ACCOUNT_SID": "AC_test", "TWILIO_AUTH_TOKEN": "tok_test",
            "TWILIO_SMS_NUMBER": "+15551234567", "D2M_NOTIFICATIONS_LIVE": "1"}
DRY_ENV: dict = {}


def make_client(client_id="test_client", sms_opt_in=False, push_opt_in=False,
                 phone="+17195559999", email="client@example.com",
                 embark=None, disembark=None, fpd=None, status="active"):
    return {
        "client_id": client_id,
        "client_names": "Test Client",
        "status": status,
        "contacts": [{"role": "primary", "phone": phone, "email": email}],
        "notification_preferences": {
            "sms_opt_in": sms_opt_in,
            "push_opt_in": push_opt_in,
            "push_token": "fcm-token-123" if push_opt_in else None,
        },
        "bookings": [{
            "booking_type": "cruise",
            "ship": "Test Ship",
            "voyage_name": "Test Voyage",
            "cabin_number": "1234",
            "embarkation_date": str(embark) if embark else "2099-01-01",
            "disembarkation_date": str(disembark) if disembark else "2099-01-10",
            "final_payment_date": str(fpd) if fpd else "2099-01-01",
            "balance_due": "$1,000.00",
        }],
    }


# ── Opt-in gating ──────────────────────────────────────────────────────────────

def test_get_prefs_defaults_to_not_opted_in():
    client = {"client_names": "X", "contacts": []}
    prefs = get_prefs(client)
    assert prefs.sms_opt_in is False
    assert prefs.push_opt_in is False


def test_get_prefs_reads_explicit_opt_in():
    client = make_client(sms_opt_in=True, push_opt_in=True)
    prefs = get_prefs(client)
    assert prefs.sms_opt_in is True
    assert prefs.push_opt_in is True
    assert prefs.phone == "+17195559999"
    assert prefs.push_token == "fcm-token-123"


def test_get_prefs_treats_tbd_phone_as_missing():
    client = make_client(phone="TBD")
    prefs = get_prefs(client)
    assert prefs.phone is None


# ── Template rendering ─────────────────────────────────────────────────────────

def test_render_fills_placeholders():
    ctx = NotificationContext(client_id="x", first_name="Erik", ship="Silver Muse", cabin_number="850")
    out = render("Welcome {first_name}, cabin {cabin_number} aboard {ship}.", ctx)
    assert out == "Welcome Erik, cabin 850 aboard Silver Muse."


def test_build_context_extracts_first_name_from_couple():
    client = make_client()
    client["client_names"] = "Erik McLeod & Melissa McGlasson"
    ctx = build_context(client)
    assert ctx.first_name == "Erik"
    assert ctx.ship == "Test Ship"


def test_all_events_have_complete_templates():
    for event in NotificationEvent:
        tmpl = bn.TEMPLATES[event]
        assert "sms" in tmpl and tmpl["sms"]
        assert "push" in tmpl and tmpl["push"]["title"] and tmpl["push"]["body"]
        assert "email_subject" in tmpl and "email_body" in tmpl


# ── SMS channel: dry-run vs live, opt-out, missing recipient ──────────────────

def test_sms_opted_out_never_calls_twilio():
    prefs = NotificationPrefs(sms_opt_in=False, phone="+17195559999")
    ctx = NotificationContext(client_id="x")
    with patch("twilio.rest.Client") as mock_client:
        result = bn.send_sms("x", NotificationEvent.BOOKING_CONFIRMED, ctx, prefs, DRY_ENV)
    assert result["delivery_status"] == "opted_out"
    mock_client.assert_not_called()


def test_sms_missing_phone_reports_no_recipient():
    prefs = NotificationPrefs(sms_opt_in=True, phone=None)
    ctx = NotificationContext(client_id="x")
    result = bn.send_sms("x", NotificationEvent.BOOKING_CONFIRMED, ctx, prefs, DRY_ENV)
    assert result["delivery_status"] == "no_recipient"


def test_sms_dry_run_suppressed_by_default():
    prefs = NotificationPrefs(sms_opt_in=True, phone="+17195559999")
    ctx = NotificationContext(client_id="x")
    with patch("twilio.rest.Client") as mock_client:
        result = bn.send_sms("x", NotificationEvent.BOOKING_CONFIRMED, ctx, prefs, DRY_ENV)
    assert result["delivery_status"] == "dry_run_suppressed"
    mock_client.assert_not_called()


def test_sms_live_send_calls_twilio_and_logs_provider_id():
    prefs = NotificationPrefs(sms_opt_in=True, phone="+17195559999")
    ctx = NotificationContext(client_id="x", first_name="Erik", voyage_name="Test Voyage",
                               ship="Test Ship", cabin_number="123")
    fake_message = MagicMock(status="queued", sid="SM123")
    with patch("twilio.rest.Client") as mock_client_cls:
        mock_client_cls.return_value.messages.create.return_value = fake_message
        result = bn.send_sms("x", NotificationEvent.BOOKING_CONFIRMED, ctx, prefs, LIVE_ENV)
    assert result["delivery_status"] == "queued"
    assert result["provider_id"] == "SM123"
    mock_client_cls.return_value.messages.create.assert_called_once()


def test_sms_live_send_handles_twilio_failure():
    prefs = NotificationPrefs(sms_opt_in=True, phone="+17195559999")
    ctx = NotificationContext(client_id="x")
    with patch("twilio.rest.Client") as mock_client_cls:
        mock_client_cls.return_value.messages.create.side_effect = Exception("carrier rejected")
        result = bn.send_sms("x", NotificationEvent.BOOKING_CONFIRMED, ctx, prefs, LIVE_ENV)
    assert result["delivery_status"] == "failed"
    assert "carrier rejected" in result["error"]


# ── Push channel: not-configured gap is honest, not silently faked ───────────

def test_push_opted_out():
    prefs = NotificationPrefs(push_opt_in=False, push_token="tok")
    ctx = NotificationContext(client_id="x")
    result = bn.send_push("x", NotificationEvent.EMBARK_DAY, ctx, prefs, DRY_ENV)
    assert result["delivery_status"] == "opted_out"


def test_push_dry_run_suppressed():
    prefs = NotificationPrefs(push_opt_in=True, push_token="tok")
    ctx = NotificationContext(client_id="x")
    result = bn.send_push("x", NotificationEvent.EMBARK_DAY, ctx, prefs, DRY_ENV)
    assert result["delivery_status"] == "dry_run_suppressed"


def test_push_live_without_firebase_admin_reports_not_configured():
    prefs = NotificationPrefs(push_opt_in=True, push_token="tok")
    ctx = NotificationContext(client_id="x")
    # firebase_admin is not installed in this environment — verifies the
    # module degrades honestly instead of claiming a fake success.
    result = bn.send_push("x", NotificationEvent.EMBARK_DAY, ctx, prefs, LIVE_ENV)
    assert result["delivery_status"] == "not_configured"


# ── Email digest: always drafts, never direct-sends ───────────────────────────

def test_email_digest_missing_recipient():
    prefs = NotificationPrefs(email=None)
    ctx = NotificationContext(client_id="x")
    result = bn.send_email_digest("x", NotificationEvent.FPD_DUE_7DAYS, ctx, prefs, DRY_ENV)
    assert result["delivery_status"] == "no_recipient"


def test_email_digest_creates_draft_never_calls_send():
    prefs = NotificationPrefs(email="client@example.com")
    ctx = NotificationContext(client_id="x", voyage_name="Test Voyage")
    fake_module = MagicMock()
    fake_module.gmail_create_draft_sync.return_value = {"status": "success", "draft_id": "draft-1"}
    with patch.dict("sys.modules", {"thunderbird_gmail": fake_module}):
        result = bn.send_email_digest("x", NotificationEvent.FPD_DUE_7DAYS, ctx, prefs, DRY_ENV)
    assert result["delivery_status"] == "drafted"
    assert result["provider_id"] == "draft-1"
    fake_module.gmail_create_draft_sync.assert_called_once()
    assert not hasattr(fake_module, "gmail_send_email") or not fake_module.gmail_send_email.called


# ── Idempotency ledger ─────────────────────────────────────────────────────────

def test_already_fired_and_mark_fired(tmp_path, monkeypatch):
    ledger_path = tmp_path / "ledger.json"
    monkeypatch.setattr(bn, "SENT_LEDGER_PATH", ledger_path)
    ledger: dict = {}
    d = date(2026, 7, 6)
    assert already_fired(ledger, "client_a", NotificationEvent.EMBARK_DAY, d) is False
    mark_fired(ledger, "client_a", NotificationEvent.EMBARK_DAY, d)
    assert already_fired(ledger, "client_a", NotificationEvent.EMBARK_DAY, d) is True
    assert json.loads(ledger_path.read_text())["client_a"]["embark_day"] == "2026-07-06"


# ── Date-driven scan logic ────────────────────────────────────────────────────

def test_scan_client_fires_embark_day_exactly_on_date(monkeypatch):
    today = date(2026, 8, 29)
    client = make_client(sms_opt_in=True, embark=today, disembark=today + timedelta(days=7),
                          fpd=today - timedelta(days=60))
    monkeypatch.setattr(bn, "_live_send_enabled", lambda env: False)
    fired = scan_client(client, today, ledger={}, dry_run=False, env={})
    events_fired = {r["event"] for r in fired if "event" in r}
    assert NotificationEvent.EMBARK_DAY.value in events_fired


def test_scan_client_fires_fpd_reminder_7_days_before(monkeypatch):
    fpd = date(2026, 9, 1)
    check_date = fpd - timedelta(days=7)
    client = make_client(sms_opt_in=True, fpd=fpd, embark=date(2099, 1, 1))
    monkeypatch.setattr(bn, "_live_send_enabled", lambda env: False)
    fired = scan_client(client, check_date, ledger={}, dry_run=False, env={})
    events_fired = {r["event"] for r in fired if "event" in r}
    assert NotificationEvent.FPD_DUE_7DAYS.value in events_fired


def test_scan_client_does_not_refire_same_day(monkeypatch):
    today = date(2026, 8, 29)
    client = make_client(sms_opt_in=True, embark=today)
    monkeypatch.setattr(bn, "_live_send_enabled", lambda env: False)
    ledger: dict = {}
    scan_client(client, today, ledger=ledger, dry_run=False, env={})
    second_pass = scan_client(client, today, ledger=ledger, dry_run=False, env={})
    assert second_pass == []


def test_scan_client_ignores_far_future_dates():
    client = make_client(sms_opt_in=True, embark=date(2099, 1, 1))
    fired = scan_client(client, date(2026, 7, 6), ledger={}, dry_run=False, env={})
    assert fired == []


# ── Full-loop integration against Blackboard-shaped YAML fixtures ────────────

def test_run_daily_scan_over_five_fixture_bookings(tmp_path, monkeypatch):
    """Exercises the full scan across 5 clients — one per lifecycle event,
    the acceptance scenario from the task spec ('5 real bookings')."""
    blackboard = tmp_path / "clients"
    blackboard.mkdir()
    monkeypatch.setattr(bn, "BLACKBOARD_DIR", blackboard)
    monkeypatch.setattr(bn, "SENT_LEDGER_PATH", tmp_path / "ledger.json")
    monkeypatch.setattr(bn, "_live_send_enabled", lambda env: False)

    check_date = date(2026, 7, 6)
    fixtures = {
        "client_fpd": make_client("client_fpd", sms_opt_in=True,
                                   fpd=check_date + timedelta(days=7),
                                   embark=date(2099, 1, 1)),
        "client_embark3": make_client("client_embark3", sms_opt_in=True,
                                       embark=check_date + timedelta(days=3)),
        "client_embarkday": make_client("client_embarkday", sms_opt_in=True,
                                         embark=check_date),
        "client_postvoyage": make_client("client_postvoyage", sms_opt_in=True,
                                          disembark=check_date - timedelta(days=1),
                                          embark=date(2020, 1, 1)),
        "client_noop": make_client("client_noop", sms_opt_in=True,
                                    embark=date(2099, 1, 1)),
    }
    for client_id, data in fixtures.items():
        (blackboard / f"{client_id}.yaml").write_text(yaml.dump(data))

    summary = run_daily_scan(check_date=check_date)
    assert summary["processed"] == 5
    assert summary["errors"] == []
    # 4 of 5 clients should have fired exactly one event each (2 channels apiece
    # for fpd/postvoyage since those events default to [SMS, EMAIL_DIGEST]).
    assert summary["fired"] >= 4


def test_notify_booking_confirmed_missing_client_reports_client_not_found():
    results = notify_booking_confirmed("does_not_exist_client_xyz")
    assert results[0]["delivery_status"] == "client_not_found"


def test_fire_event_respects_channel_override(tmp_path, monkeypatch):
    blackboard = tmp_path / "clients"
    blackboard.mkdir()
    monkeypatch.setattr(bn, "BLACKBOARD_DIR", blackboard)
    client = make_client("client_override", sms_opt_in=True, push_opt_in=True)
    (blackboard / "client_override.yaml").write_text(yaml.dump(client))

    results = fire_event("client_override", NotificationEvent.BOOKING_CONFIRMED,
                          channels=[Channel.SMS], env={})
    assert len(results) == 1
    assert results[0]["channel"] == Channel.SMS.value
