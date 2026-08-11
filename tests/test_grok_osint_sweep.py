"""Tests for grok_osint_sweep() — mocked only, no real API call in the suite.

Live end-to-end call verified manually 2026-08-11 (real PONG response,
confirmed against the actual xAI Responses API before this test was written).
"""
from unittest.mock import MagicMock, patch

from core.intel.thunderbird_x_osint import grok_osint_sweep


def _fake_response(text="Real Silversea fare update.", citations=None):
    resp = MagicMock()
    resp.output_text = text
    ann = MagicMock()
    ann.type = "url_citation"
    ann.url = "https://example.com/article"
    ann.title = "Example Article"
    block = MagicMock()
    block.annotations = [ann] if citations is None else citations
    message = MagicMock()
    message.type = "message"
    message.content = [block]
    resp.output = [message]
    return resp


@patch("core.intel.thunderbird_x_osint.OpenAI")
@patch("core.intel.thunderbird_x_osint.load_dotenv")
def test_grok_osint_sweep_returns_expected_shape(mock_load_dotenv, mock_openai_cls, monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    mock_client.responses.create.return_value = _fake_response()
    mock_openai_cls.return_value = mock_client

    result = grok_osint_sweep("latest luxury cruise industry news", max_results=5)

    assert result["query"] == "latest luxury cruise industry news"
    assert result["output_text"] == "Real Silversea fare update."
    assert result["citations"] == [{"url": "https://example.com/article", "title": "Example Article"}]
    assert "timestamp" in result
    mock_client.responses.create.assert_called_once()


@patch("core.intel.thunderbird_x_osint.OpenAI")
@patch("core.intel.thunderbird_x_osint.load_dotenv")
def test_grok_osint_sweep_no_citations(mock_load_dotenv, mock_openai_cls, monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "fake-key-for-test")
    mock_client = MagicMock()
    mock_client.responses.create.return_value = _fake_response(citations=[])
    mock_openai_cls.return_value = mock_client

    result = grok_osint_sweep("no results query")

    assert result["citations"] == []
