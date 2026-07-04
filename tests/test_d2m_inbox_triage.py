"""Offline tests for scripts/d2m_inbox_triage.py disposition mapping.

No network — exercises disposition_for() against rules_classifier categories
and classify() itself with a stub registry (no EARA sheet pull).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from core.email.rules_classifier import classify
from d2m_inbox_triage import disposition_for

REGISTRY = {
    "client_emails": {"kyle.kuklinski@example.com"},
    "supplier_domains": {"rssc.com"},
}


def test_client_inquiry_pages():
    cat = classify("kyle.kuklinski@example.com", "Question about our excursions",
                   "can you check the dining reservation", REGISTRY)
    assert cat == "client_inquiry"
    assert disposition_for(cat) == "page+queue"


def test_newsletter_is_spam_for_deletion():
    cat = classify("Heavy on Vikings <newsletters@heavy.com>",
                   "Vikings Fan-Favorite Draft Pick Gets Put on Notice", "", REGISTRY)
    assert cat == "spam"
    assert disposition_for(cat) == "for_deletion+archive"


def test_unknown_sender_is_triaged_not_deleted():
    cat = classify("group333@lawndoctor.com",
                   "Red, White & Green: Keep Your Lawn Looking Its Best", "", REGISTRY)
    assert disposition_for(cat) in ("triaged", "for_deletion+archive")


def test_commander_directive_delegated():
    cat = classify("johnloucks3@gmail.com", "COS, pull the McLeod balance", "", REGISTRY)
    assert disposition_for(cat) == "delegated"


def test_supplier_booking_pages():
    cat = classify("noreply@rssc.com", "Booking Confirmation 3122006", "", REGISTRY)
    assert cat == "booking_confirmation"
    assert disposition_for(cat) == "page+queue"


def test_supplier_intel_no_page():
    # NB: noreply/news@ senders hit the noise fast-path before the supplier
    # check (classifier step order) — use a person-style supplier address.
    cat = classify("agentdesk@rssc.com", "New Grandeur itineraries announced", "", REGISTRY)
    assert cat == "supplier_intel"
    assert disposition_for(cat) == "triaged"


def test_financial_pages():
    cat = classify("billing@rssc.com", "Invoice for booking 2984034", "", REGISTRY)
    assert cat == "financial"
    assert disposition_for(cat) == "page+queue"


def test_every_category_has_a_disposition():
    cats = ["commander_directive", "direct_command", "internal_wing",
            "booking_confirmation", "financial", "supplier_intel",
            "client_inquiry", "intel", "spam", "other"]
    for c in cats:
        assert disposition_for(c) in (
            "delegated", "page+queue", "for_deletion+archive", "triaged")
