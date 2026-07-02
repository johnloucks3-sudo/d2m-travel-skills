"""Offline tests for core.web.smart_fetch — no live network. Tier runners are mocked."""
import pytest

from core.web import smart_fetch as sf


# --- _is_walled unit tests ---------------------------------------------------

def test_is_walled_403_status():
    assert sf._is_walled(403, "anything") is True


def test_is_walled_cloudflare_body():
    body = "<html><title>Attention Required! | Cloudflare</title>...</html>"
    assert sf._is_walled(200, body) is True


def test_is_walled_incapsula_body():
    body = "Pardon Our Interruption... Request unsuccessful. Incapsula incident ID 123"
    assert sf._is_walled(200, body) is True


def test_is_walled_akamai_reference():
    body = "Access Denied\nYou don't have permission... Reference #18.abc123"
    assert sf._is_walled(403, body) is True


def test_is_walled_normal_article_not_walled():
    body = "The World's Most Luxurious Cruise Line. Sail aboard our perfectly sized ships."
    assert sf._is_walled(200, body) is False


def test_is_walled_none_status_clean_body():
    assert sf._is_walled(None, "a normal page with real content here") is False


# --- escalation behavior -----------------------------------------------------

def test_clean_tier1_no_escalation(monkeypatch):
    """(a) Clean tier-1 (200, real body) -> tier_used=1, does NOT escalate."""
    calls = {"anansi": 0, "cloak": 0}

    def fake_anansi(url, output, timeout, browser=False):
        calls["anansi"] += 1
        return 200, "The World's Most Luxurious Cruise Line", None

    def fake_cloak(url, output, timeout):
        calls["cloak"] += 1
        return None, "SHOULD NOT BE CALLED", None

    monkeypatch.setattr(sf, "_run_anansi", fake_anansi)
    monkeypatch.setattr(sf, "_run_cloak", fake_cloak)

    r = sf.fetch("https://example.com/", output="text")
    assert r["tier_used"] == 1
    assert r["walled"] is False
    assert r["status"] == 200
    assert "Luxurious" in r["content"]
    assert calls["cloak"] == 0  # never escalated


def test_akamai_403_escalates_to_tier3(monkeypatch):
    """(b) tier-1 Akamai 403 + Reference# body -> escalate -> tier_used=3 with cloak content."""
    def fake_anansi(url, output, timeout, browser=False):
        return 403, "Access Denied\nReference #18.deadbeef", None

    def fake_cloak(url, output, timeout):
        return None, "The World's Most Luxurious Cruise Line | Regent Seven Seas", None

    monkeypatch.setattr(sf, "_run_anansi", fake_anansi)
    monkeypatch.setattr(sf, "_run_cloak", fake_cloak)

    r = sf.fetch("https://www.rssc.com/", output="text")
    assert r["tier_used"] == 3
    assert r["walled"] is False
    assert "Regent Seven Seas" in r["content"]


def test_tier1_error_escalates_to_tier3(monkeypatch):
    """tier-1 hard error (timeout/spawn) -> escalate -> tier_used=3."""
    def fake_anansi(url, output, timeout, browser=False):
        return None, "", "anansi timeout"

    def fake_cloak(url, output, timeout):
        return None, "rescued content", None

    monkeypatch.setattr(sf, "_run_anansi", fake_anansi)
    monkeypatch.setattr(sf, "_run_cloak", fake_cloak)

    r = sf.fetch("https://walled.example/", output="text")
    assert r["tier_used"] == 3
    assert r["content"] == "rescued content"


def test_all_tiers_fail(monkeypatch):
    """Both anansi and cloak fail -> tier_used=None, walled=True, error set."""
    monkeypatch.setattr(sf, "_run_anansi", lambda *a, **k: (403, "Access Denied", None))
    monkeypatch.setattr(sf, "_run_cloak", lambda *a, **k: (None, "", "cloak nonzero exit / empty"))

    r = sf.fetch("https://hardwall.example/", output="text")
    assert r["tier_used"] is None
    assert r["walled"] is True
    assert r["content"] == ""
    assert r["error"]


def test_tier2_browser_serves_when_enabled(monkeypatch):
    """allow_browser_tier=True: tier-1 walled, tier-2 browser clean -> tier_used=2, no cloak."""
    state = {"n": 0}

    def fake_anansi(url, output, timeout, browser=False):
        state["n"] += 1
        if browser:
            return 200, "clean browser-rendered page", None
        return 403, "Access Denied Reference #1", None

    monkeypatch.setattr(sf, "_run_anansi", fake_anansi)
    monkeypatch.setattr(sf, "_run_cloak", lambda *a, **k: (None, "SHOULD NOT REACH", None))

    r = sf.fetch("https://spa.example/", output="text", allow_browser_tier=True)
    assert r["tier_used"] == 2
    assert "browser-rendered" in r["content"]


# --- anansi header parsing helpers ------------------------------------------

def test_parse_anansi_status():
    assert sf._parse_anansi_status("HTTP 200 https://x [0.5s]\nbody") == 200
    assert sf._parse_anansi_status("HTTP 403 https://x\nAccess Denied") == 403
    assert sf._parse_anansi_status("no header here") is None


def test_strip_anansi_header():
    out = "HTTP 200 https://x [0.5s]\nreal content line 1\nline 2"
    assert sf._strip_anansi_header(out) == "real content line 1\nline 2"
    assert sf._strip_anansi_header("no header\nbody") == "no header\nbody"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
