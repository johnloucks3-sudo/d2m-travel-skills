#!/usr/bin/env python3
"""
tests/test_rules_classifier.py
==============================
OFFLINE, fast pytest suite for core.email.rules_classifier.

Zero-network guarantee: the sheet fetch seam (_fetch_from_sheet) and the AI path
(deep_classify) are monkeypatched to RAISE — proving classify() never touches the
network or a model in the hot path.

Author: Sterling (A7) — 2026-07-01
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.email import rules_classifier as rc  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def registry():
    return {
        "client_emails": {"crnakim@yahoo.com"},
        "supplier_domains": {"rssc.com", "silversea.com"},
    }


@pytest.fixture(autouse=True)
def _block_network(monkeypatch):
    """Hard-block every network/model seam. classify() must still work."""
    def _boom(*a, **k):
        raise AssertionError("NETWORK/MODEL CALL in hot path — forbidden")
    monkeypatch.setattr(rc, "_fetch_from_sheet", _boom)
    monkeypatch.setattr(rc, "deep_classify", _boom)


# ── B. classify() — pure, offline ─────────────────────────────────────────────

@pytest.mark.parametrize("sender,subject,body,expected", [
    # spam / promo
    ("junonews@substack.com", "Weekly digest", "", "spam"),
    ("news@newsmax.com", "Breaking", "", "spam"),
    ("deals@dunkin.com", "Free coffee", "", "spam"),
    ("promo@arbys.com", "New sandwich", "", "spam"),
    # booking confirmation from a noreply@ sender must survive the noise step
    ("noreply@silversea.com", "Booking Confirmation — SS Nova", "", "booking_confirmation"),
    # internal wing
    ("johnloucks3@gmail.com", "notes", "", "internal_wing"),
    # supplier by registry domain (domain match, not substring)
    ("someone@rssc.com", "Question about a sailing", "", "supplier_intel"),
    # registry client → client_inquiry
    ("crnakim@yahoo.com", "Hi", "just checking in", "client_inquiry"),
    # unknown personal gmail sender w/ strong inquiry body → client_inquiry
    ("stranger@gmail.com", "Trip", "Hi John, we are interested in a cruise — can you help with a quote?", "client_inquiry"),
    # unknown ambiguous → other
    ("random@example.org", "Hello there", "just saying hi", "other"),
])
def test_classify_cases(registry, sender, subject, body, expected):
    assert rc.classify(sender, subject, body, registry=registry) == expected


def test_newsmax_dunkin_arbys_not_client_inquiry(registry):
    for s in ("news@newsmax.com", "deals@dunkin.com", "promo@arbys.com"):
        assert rc.classify(s, "hi", "can you help us book a cruise", registry=registry) != "client_inquiry"


def test_command_prefix_beats_self_address(registry):
    assert rc.classify("johnloucks3@gmail.com", "COS, run the audit", "", registry=registry) == "commander_directive"
    assert rc.classify("johnloucks3@gmail.com", "Re: Hale: do this", "", registry=registry) == "direct_command"


def test_gmail_is_not_internal(registry):
    # A gmail prospect must NOT be swallowed as internal_wing.
    assert rc.classify("prospect@gmail.com", "hi", "", registry=registry) != "internal_wing"


def test_supplier_substring_not_matched(registry):
    # silversea.com@evil.com must not match the supplier set.
    assert rc.classify("silversea.com@evil.com", "hello", "", registry=registry) != "supplier_intel"


def test_supplier_invoice_vs_booking(registry):
    assert rc.classify("billing@rssc.com", "Commission statement", "", registry=registry) == "financial"
    assert rc.classify("agent@rssc.com", "Your reservation confirmed", "", registry=registry) == "booking_confirmation"


def test_supplier_domain_branch_via_body(registry):
    # Neutral subject → skips step 2; supplier domain branch (step 4) reads body keywords.
    assert rc.classify("agent@rssc.com", "hello", "invoice attached", registry=registry) == "financial"
    assert rc.classify("agent@rssc.com", "hello", "your booking is confirmed", registry=registry) == "booking_confirmation"
    assert rc.classify("agent@rssc.com", "hello", "just an FYI", registry=registry) == "supplier_intel"


def test_intel_keyword(registry):
    assert rc.classify("editor@somewhere.org", "Travel advisory for Norway", "", registry=registry) == "intel"


def test_is_d2m_relevant():
    assert rc.is_d2m_relevant("client_inquiry")
    assert rc.is_d2m_relevant("financial")
    assert not rc.is_d2m_relevant("spam")
    assert not rc.is_d2m_relevant("other")


# ── A. load_registry cache logic ───────────────────────────────────────────────

def _fake_fetch():
    return {"client_emails": {"a@b.com"}, "supplier_domains": {"rssc.com"}}


def test_cache_fresh_used_no_refetch(tmp_path, monkeypatch):
    cache = tmp_path / "reg.json"
    cache.write_text(json.dumps({
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "client_emails": ["cached@x.com"],
        "supplier_domains": ["cached.com"],
    }))
    # If it refetches, this raises.
    monkeypatch.setattr(rc, "_fetch_from_sheet", lambda: (_ for _ in ()).throw(AssertionError("refetched")))
    reg = rc.load_registry(cache_path=cache)
    assert "cached@x.com" in reg["client_emails"]


def test_cache_stale_triggers_refetch(tmp_path, monkeypatch):
    cache = tmp_path / "reg.json"
    old = datetime.now(timezone.utc) - timedelta(hours=rc.REGISTRY_TTL_HOURS + 1)
    cache.write_text(json.dumps({
        "fetched_at": old.isoformat(),
        "client_emails": ["stale@x.com"],
        "supplier_domains": ["stale.com"],
    }))
    monkeypatch.setattr(rc, "_fetch_from_sheet", _fake_fetch)
    reg = rc.load_registry(cache_path=cache)
    assert "a@b.com" in reg["client_emails"]
    # cache overwritten with fresh data
    written = json.loads(cache.read_text())
    assert "a@b.com" in written["client_emails"]


def test_sheet_fails_no_cache_falls_back(tmp_path, monkeypatch):
    cache = tmp_path / "reg.json"  # does not exist
    monkeypatch.setattr(rc, "_fetch_from_sheet", lambda: (_ for _ in ()).throw(RuntimeError("no net")))
    reg = rc.load_registry(force_refresh=True, cache_path=cache)
    # Suppliers are guaranteed non-empty (hardcoded); assert on the guaranteed side.
    assert len(reg["supplier_domains"]) > 0
    assert isinstance(reg["client_emails"], set)
