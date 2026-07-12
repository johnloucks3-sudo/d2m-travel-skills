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

    def test_dispatch_refuses_booking_write_tool(self):
        result = bridge.dispatch_tool_call("tess_create_booking", {})
        assert "error" in result

    def test_array_params_always_include_items_schema(self):
        # 2026-07-12 LIVE BUG: Gemini's API 400s on any ARRAY property with
        # no `items` sub-schema ("GenerateContentRequest...items: missing
        # field"). Every List[...] param in the catalog must get one.
        decls = bridge.build_function_declarations()
        for decl in decls:
            for pname, prop in decl["parameters"]["properties"].items():
                if prop["type"] == "ARRAY":
                    assert "items" in prop, f"{decl['name']}.{pname} ARRAY missing items schema"

    def test_function_declarations_only_cover_allowlisted_names(self):
        decls = bridge.build_function_declarations({"search_flights", "send_client_email"})
        names = {d["name"] for d in decls}
        assert "search_flights" in names
        assert "send_client_email" not in names  # not on SAFE_ALLOWLIST, filtered even if requested

    def test_safe_allowlist_contains_no_client_send_tools(self):
        # WF-17 client-send is Commander-only, full stop — this must hold no
        # matter how far the allowlist grows. gmail_send_from_wing is the
        # ONE deliberate, hard-pinned exception (see next test class) so it's
        # excluded from this blanket check, not from the rule it represents.
        forbidden_sends = (
            "gmail_send_email", "gmail_send_draft", "gmail_reply_in_thread",
            "send_client_email", "send_whatsapp", "send_morning_briefing",
        )
        assert not (bridge.SAFE_ALLOWLIST & set(forbidden_sends))

    def test_safe_allowlist_contains_no_financial_or_booking_verbs(self):
        dangerous = ("create_booking", "update_booking", "purge", "authorize", "revoke", "drop_")
        for name in bridge.SAFE_ALLOWLIST:
            for verb in dangerous:
                assert verb not in name, f"{name!r} looks unsafe for the Gemini bridge allowlist"


class TestGoogleWriteExpansion:
    def test_google_write_tools_present_after_2026_07_12_expansion(self):
        expected = {
            "gmail_create_draft", "gmail_delete_draft", "gmail_trash_message",
            "drive_upload_file", "drive_delete_file",
            "sheets_write_data", "docs_update_content",
            "contacts_create", "forms_create_form", "keep_create_note",
        }
        assert expected <= bridge.SAFE_ALLOWLIST

    def test_dispatch_still_refuses_actual_send_tools_after_expansion(self):
        # gmail_send_from_wing deliberately excluded here — it's the one
        # hard-pinned exception, covered by TestD2mSendHardPin below, and
        # calling dispatch on it would hit the live server.
        for name in ("gmail_send_email", "gmail_send_draft",
                     "gmail_reply_in_thread", "send_client_email", "send_whatsapp"):
            result = bridge.dispatch_tool_call(name, {})
            assert "error" in result, f"{name!r} must stay refused"


class TestD2mSendHardPin:
    """gmail_send_from_wing (2026-07-12): the one send exception, and only
    ever to johnloucks3 — Commander-authorized, internal-briefing channel,
    not client-facing. Never actually calls the live server / sends real
    email — the server object is faked."""

    def test_to_param_hidden_from_gemini_declaration(self):
        decls = bridge.build_function_declarations({"gmail_send_from_wing"})
        decl = next(d for d in decls if d["name"] == "gmail_send_from_wing")
        assert "to" not in decl["parameters"]["properties"]

    def test_dispatch_forces_recipient_even_if_model_supplies_a_different_one(self, monkeypatch):
        captured = {}

        class FakeServer:
            async def call_tool(self, name, args):
                captured["name"] = name
                captured["args"] = args
                return ({"status": "sent"}, None)

        monkeypatch.setattr(bridge, "_get_server", lambda: FakeServer())
        bridge.dispatch_tool_call(
            "gmail_send_from_wing",
            {"to": "someone-else@attacker.example", "subject": "hi", "body": "hi"},
        )
        assert captured["args"]["to"] == bridge.D2M_COMMANDER_EMAIL
        assert captured["args"]["to"] != "someone-else@attacker.example"
