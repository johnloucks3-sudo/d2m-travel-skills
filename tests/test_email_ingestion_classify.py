#!/usr/bin/env python3
"""
test_email_ingestion_classify.py
================================
Offline, deterministic tests for scripts/email_ingestion_pipeline.py::_classify_email.

Guards the MISSION-431 defect: the classifier used to DEFAULT to "client_inquiry",
so every unclassified bulk email (newsletters, promos, political blasts, self-sends,
security alerts) became a P1 mission-board ticket + an auto-drafted junk reply.

Design contract enforced here:
  * Default fallthrough is "other" (non-actionable) — NEVER client_inquiry.
  * client_inquiry is returned ONLY on a positive signal:
        (a) known client (via _determine_email_tier == "CLIENT"), OR
        (b) client_inquiry body/subject signals present AND sender is NOT bulk noise.
  * Bulk/newsletter/promo/noreply senders → "spam" (noise fast-path).
  * booking_confirmation / supplier_intel / invoice / internal_wing preserved.

These tests MUST run offline: the Gemini classifier (_classify_message) is
monkeypatched to raise, forcing the deterministic keyword/positive-signal path.
No live Gmail, no live LLM.

Author: Sterling (A7) — MISSION-431 defect fix
"""

import importlib
import sys
from pathlib import Path

import pytest

THUNDERBIRD_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(THUNDERBIRD_DIR))

import scripts.email_ingestion_pipeline as pipe  # noqa: E402
from core.email import hale_inbox_tools  # noqa: E402


@pytest.fixture(autouse=True)
def force_keyword_path(monkeypatch):
    """
    Force the deterministic (non-LLM) path by making the Gemini classifier raise.
    The pipeline wraps _classify_message in try/except, so a raise routes every
    call through the keyword + positive-signal logic — the code we are testing.
    """
    def _boom(*args, **kwargs):
        raise RuntimeError("gemini disabled in test")

    # Patch at the source module — the pipeline imports it lazily inside the fn.
    monkeypatch.setattr(hale_inbox_tools, "_classify_message", _boom, raising=False)
    yield


def classify(from_addr, subject="", snippet=""):
    return pipe._classify_email(from_addr, subject, snippet)


# ── Criterion 1 & 3: bulk/noise senders never become client_inquiry ──────────

def test_substack_newsletter_is_spam_not_client_inquiry():
    # substack matches _NOISE_PATTERNS -> spam
    result = classify("junonews@substack.com", "Juno Jump Start | Trudeau and the tariff war")
    assert result != "client_inquiry"
    assert result == "spam"


def test_condenast_travel_promo_is_spam():
    # condenast matches _NOISE_PATTERNS (@eml.) -> spam
    result = classify("condenasttraveler@eml.condenast.com", "The 50 Best Hotels in the World")
    assert result != "client_inquiry"
    assert result == "spam"


@pytest.mark.parametrize(
    "from_addr,subject",
    [
        ("newsmax@latest.newsmax.com", "BREAKING: Latest headlines"),
        ("dunkinrewards@emailinfo.dunkinrewards.com", "Your rewards are waiting"),
        ("arbys@emails.arbys.com", "New menu item just dropped"),
    ],
)
def test_promo_blasts_never_client_inquiry(from_addr, subject):
    # These senders do NOT match the noise regex, but they carry no client
    # signal and must fall through to the non-actionable default, NOT client_inquiry.
    result = classify(from_addr, subject)
    assert result != "client_inquiry"


def test_noreply_security_alert_not_client_inquiry():
    result = classify("no-reply@security.google.com", "Security alert for your account")
    assert result != "client_inquiry"
    assert result == "spam"


# ── Criterion 4: internal / booking / invoice preserved ──────────────────────

def test_self_send_is_internal_wing():
    result = classify("johnloucks3@gmail.com", "Notes to self")
    assert result == "internal_wing"


def test_booking_confirmation_survives_noreply_sender():
    # A booking confirmation from a noreply sender must NOT be killed as spam.
    # Booking keyword detection runs before the noise short-circuit.
    result = classify(
        "noreply@rssc.com",
        "Your booking confirmation and itinerary details",
    )
    assert result == "booking_confirmation"


def test_invoice_keyword_routes_to_invoice():
    result = classify(
        "billing@somevendor.com",
        "Invoice payment receipt for your reservation",
    )
    assert result == "invoice"


# ── Criterion 2: client_inquiry only on positive signal ──────────────────────

def test_genuine_inquiry_from_personal_gmail_is_client_inquiry():
    result = classify(
        "prospect.traveler@gmail.com",
        "Cruise question",
        "Hi John, we'd like to book a cruise — can you help with a quote?",
    )
    assert result == "client_inquiry"


def test_known_client_is_client_inquiry(monkeypatch):
    # Criterion 2(a): a sender matching a known client -> client_inquiry,
    # even without strong body signals.
    monkeypatch.setattr(pipe, "_determine_email_tier", lambda s: "CLIENT")
    result = classify(
        "existing.client@somewhere.com",
        "Following up",
        "Just checking in on things.",
    )
    assert result == "client_inquiry"


def test_ambiguous_nonbulk_email_is_other_not_client_inquiry():
    # The core regression guard: an unknown, non-bulk email with NO client
    # signals must be "other" — the non-actionable default — never client_inquiry.
    result = classify(
        "randomperson@example.com",
        "Hello",
        "Saw your name somewhere and thought I would reach out.",
    )
    assert result == "other"
    assert result != "client_inquiry"


def test_gemini_client_inquiry_verdict_cannot_force_client_inquiry(monkeypatch):
    # Compounding-rule guard for the MISSION-431 defect vector: even if the
    # upstream Gemini classifier RETURNS "client_inquiry", the pipeline must NOT
    # honor it — client_inquiry is dropped from the category_map, so the
    # positive-signal gate is the sole authority. A neutral, non-bulk sender with
    # no inquiry phrases must land in "other". If a future edit re-adds the map
    # key, this test fails loudly.
    monkeypatch.setattr(hale_inbox_tools, "_classify_message",
                        lambda *a, **k: "client_inquiry", raising=False)
    result = classify(
        "someone.neutral@example.com",
        "Touching base",
        "Just wanted to say hello.",
    )
    assert result == "other"
    assert result != "client_inquiry"


def test_client_signal_from_bulk_sender_does_not_become_client_inquiry():
    # Positive-signal path requires a NON-bulk sender. A newsletter address that
    # happens to contain a trigger phrase must still not be a client_inquiry.
    result = classify(
        "newsletter@substack.com",
        "We'd like to book a cruise",
        "we are interested in a quote — please send me options",
    )
    assert result != "client_inquiry"
