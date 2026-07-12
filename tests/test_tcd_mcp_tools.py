#!/usr/bin/env python3
"""
Offline tests for tcd.mcp_tools — the MCP wrapper around the tcd/ package
(2026-07-13, built so Antigravity/any MCP client can operate the TCD board
via the real, tested engine instead of reimplementing schema logic against
raw sheets_read_data/write_data calls).

No credentials, no network: writeback.read_sheet_rows is monkeypatched.
Run: python -m pytest tests/test_tcd_mcp_tools.py -v
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tcd import mcp_tools  # noqa: E402


class _FakeMCP:
    """Captures @mcp_server.tool()-decorated functions by name, mirroring
    FastMCP's registration decorator closely enough to test in isolation."""

    def __init__(self):
        self.tools = {}

    def tool(self, name, **kwargs):
        def decorator(fn):
            self.tools[name] = fn
            return fn
        return decorator


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestTcdGetItems:
    def test_registers_all_three_tools(self):
        server = _FakeMCP()
        mcp_tools.register_tcd_tools(server)
        assert {"tcd_get_items", "tcd_sync_now", "tcd_process_writeback"} <= set(server.tools)

    def test_filters_by_inbox(self, monkeypatch):
        rows = [
            {"id": "1", "inbox": "strategic", "stage": "D", "status": "OPEN"},
            {"id": "2", "inbox": "operational", "stage": "A", "status": "OPEN"},
        ]
        monkeypatch.setattr("tcd.writeback.read_sheet_rows", lambda: rows)
        server = _FakeMCP()
        mcp_tools.register_tcd_tools(server)
        import json
        result = json.loads(_run(server.tools["tcd_get_items"](inbox="strategic")))
        assert result["count"] == 1
        assert result["items"][0]["id"] == "1"

    def test_filters_by_stage_and_status(self, monkeypatch):
        rows = [
            {"id": "1", "inbox": "strategic", "stage": "D", "status": "OPEN"},
            {"id": "2", "inbox": "strategic", "stage": "D", "status": "DISPOSE"},
        ]
        monkeypatch.setattr("tcd.writeback.read_sheet_rows", lambda: rows)
        server = _FakeMCP()
        mcp_tools.register_tcd_tools(server)
        import json
        result = json.loads(_run(server.tools["tcd_get_items"](stage="D", status="DISPOSE")))
        assert result["count"] == 1
        assert result["items"][0]["id"] == "2"

    def test_no_filters_returns_everything(self, monkeypatch):
        rows = [{"id": "1", "inbox": "strategic"}, {"id": "2", "inbox": "operational"}]
        monkeypatch.setattr("tcd.writeback.read_sheet_rows", lambda: rows)
        server = _FakeMCP()
        mcp_tools.register_tcd_tools(server)
        import json
        result = json.loads(_run(server.tools["tcd_get_items"]()))
        assert result["count"] == 2


class TestTcdProcessWriteback:
    def test_delegates_to_writeback_process_once(self, monkeypatch):
        called = {}

        def fake_process_once():
            called["ran"] = True
            return {"disposed": [], "staged": [], "commented": [], "unchanged": 3, "errors": []}

        monkeypatch.setattr("tcd.writeback.process_once", fake_process_once)
        server = _FakeMCP()
        mcp_tools.register_tcd_tools(server)
        import json
        result = json.loads(_run(server.tools["tcd_process_writeback"]()))
        assert called.get("ran") is True
        assert result["unchanged"] == 3
