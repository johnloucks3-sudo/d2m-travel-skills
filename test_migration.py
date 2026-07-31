import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, "/home/john/Thunderbird/core/intel")
sys.path.insert(0, "/home/john/Thunderbird/core/ai_infra")
from thunderbird_intel_crew import IntelCrew

def test_migration():
    crew = IntelCrew()
    raw_mock = {"news_feeds": [], "airline_articles": [], "advisories": []}
    
    # Test 1: OC succeeds
    with patch("core.relay.dispatch_oc.dispatch_to_oc") as mock_dispatch:
        mock_dispatch.return_value = {"ok": True, "ticket_id": "TICKET-123", "follow_up_due": "2026-07-30T10:00:00"}
        with patch("core.staffing.delegation_outcomes.record_outcome") as mock_record:
            res = crew.analyze(raw_mock)
            assert mock_dispatch.called
            assert mock_record.called
            assert "TICKET-123" in res["analysis"]
            print("Test 1 (OC Success) passed.")

    # Test 2: OC fails, fallback to Claude
    with patch("core.relay.dispatch_oc.dispatch_to_oc") as mock_dispatch:
        mock_dispatch.side_effect = Exception("OC is down")
        with patch("thunderbird_personas.call_persona") as mock_call_persona:
            mock_call_persona.return_value = {"answer": "Claude Fallback Analysis"}
            with patch("core.staffing.delegation_outcomes.record_outcome") as mock_record:
                res = crew.analyze(raw_mock)
                assert mock_dispatch.called
                assert mock_call_persona.called
                assert mock_record.called
                assert res["analysis"] == "Claude Fallback Analysis"
                print("Test 2 (OC Failure Fallback) passed.")

if __name__ == "__main__":
    test_migration()
