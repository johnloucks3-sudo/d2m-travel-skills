#!/usr/bin/env python3
"""
Offline safety tests for the Gemini MCP bridge (2026-07-12) and its cost
gate. No network, no live MCP server import (that has real side effects —
Telegram/Google auth wiring — and takes ~5s; these tests stay fast/offline).

Run: python -m pytest tests/test_gemini_bridge_safety.py -v
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.ai_infra.router_cost_gates import CostGateTracker, HardLimitExceeded  # noqa: E402
from core.gemini_bridge import mcp_function_bridge as bridge  # noqa: E402


class TestCostGateHardStop:
    def test_blocks_before_hard_limit_crossed(self):
        db = tempfile.mktemp(suffix=".db")
        t = CostGateTracker(db)
        t.configure_pool("p", soft_limit=7.5, hard_limit=10.0)
        t.check_and_consume("p", 9.0)
        try:
            t.check_and_consume("p", 2.0)
            assert False, "should have raised"
        except HardLimitExceeded:
            pass
        assert t.get_all()["p"]["consumed"] == 9.0  # blocked call not counted

    def test_on_hard_limit_callback_fires_exactly_once_per_trip(self):
        db = tempfile.mktemp(suffix=".db")
        t = CostGateTracker(db)
        t.configure_pool("p", soft_limit=1.0, hard_limit=1.0)
        fired = []
        try:
            t.check_and_consume("p", 1.5, on_hard_limit=lambda: fired.append(1))
        except HardLimitExceeded:
            pass
        assert fired == [1]

    def test_callback_exception_does_not_suppress_the_raise(self):
        db = tempfile.mktemp(suffix=".db")
        t = CostGateTracker(db)
        t.configure_pool("p", soft_limit=1.0, hard_limit=1.0)

        def boom():
            raise RuntimeError("gcloud not authorized")

        try:
            t.check_and_consume("p", 1.5, on_hard_limit=boom)
            assert False, "should still raise HardLimitExceeded"
        except HardLimitExceeded:
            pass

    def test_under_limit_calls_pass_through_unblocked(self):
        db = tempfile.mktemp(suffix=".db")
        t = CostGateTracker(db)
        t.configure_pool("p", soft_limit=7.5, hard_limit=10.0)
        t.check_and_consume("p", 1.0)
        t.check_and_consume("p", 1.0)
        assert t.get_all()["p"]["consumed"] == 2.0


class TestGeminiBridgeAllowlist:
    def test_dispatch_refuses_non_allowlisted_tool(self):
        # send_client_email must NEVER be reachable via the Gemini bridge —
        # client send is a Three-Gates Commander-only action.
        result = bridge.dispatch_tool_call("send_client_email", {"to": "x@y.com"})
        assert "error" in result
        assert "not on the Gemini bridge safe allowlist" in result["error"]

    def test_dispatch_refuses_destructive_tool(self):
        result = bridge.dispatch_tool_call("drive_delete_file", {"file_id": "x"})
        assert "error" in result

    def test_dispatch_refuses_booking_write_tool(self):
        result = bridge.dispatch_tool_call("tess_create_booking", {})
        assert "error" in result

    def test_function_declarations_only_cover_allowlisted_names(self):
        decls = bridge.build_function_declarations({"search_flights", "send_client_email"})
        names = {d["name"] for d in decls}
        assert "search_flights" in names
        assert "send_client_email" not in names  # not on SAFE_ALLOWLIST, filtered even if requested

    def test_safe_allowlist_contains_no_dangerous_verbs(self):
        dangerous = ("send", "delete", "trash", "create_booking", "update_booking",
                     "purge", "authorize", "revoke", "drop_")
        for name in bridge.SAFE_ALLOWLIST:
            for verb in dangerous:
                assert verb not in name, f"{name!r} looks unsafe for the Gemini bridge allowlist"
