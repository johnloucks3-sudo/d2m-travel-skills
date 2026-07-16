"""
Regression test for TESSClient.add_note() (2026-07-16).

Root cause, two layers deep:
1. add_note() POSTed to a generic REST path (/{entity_type}/{entity_id}/notes)
   -- 404. myAgentGenie is an action-based API, not resource/id REST.
2. An earlier add_note() definition (same class, same method name -- Python
   keeps only the later definition, silently shadowing the first) had the
   right action-based call shape but assumed PostBookingNote/PostClientNote
   actions exist for parity with PostTripNote -- HTTP 500. The real action
   catalog (output/tess_map/08_action_catalog.md:422-425) confirms TESS has
   no Booking or Client note action at all, only PostTripNote(tripID,
   noteContent).

Asserts: 'trips' routes to the real PostTripNote action; 'bookings'/
'clients' return a clear validation error pointing the caller at TripID
resolution, instead of a 404/500 surprise.
"""
import sys

sys.path.insert(0, "/home/john/Thunderbird")

from core.booking.thunderbird_tess import TESSClient


def test_add_note_trips_calls_post_trip_note(monkeypatch):
    client = TESSClient.__new__(TESSClient)
    captured = {}

    def fake_call_action(resource, action, body=None, **params):
        captured["resource"] = resource
        captured["action"] = action
        captured["body"] = body
        captured["params"] = params
        return {"ok": True}

    monkeypatch.setattr(client, "call_action", fake_call_action)
    result = client.add_note("trips", 1631588, "Excursions confirmed")

    assert result == {"ok": True}
    assert captured["resource"] == "Trip"
    assert captured["action"] == "PostTripNote"
    assert captured["body"] is None
    assert captured["params"] == {"tripID": 1631588, "noteContent": "Excursions confirmed"}


def test_add_note_bookings_rejected_with_actionable_error():
    client = TESSClient.__new__(TESSClient)
    result = client.add_note("bookings", 2256103, "some note")

    assert result["type"] == "validation_error"
    assert "TripID" in result["error"]
    assert "PostTripNote" in result["error"]


def test_add_note_clients_rejected_with_actionable_error():
    client = TESSClient.__new__(TESSClient)
    result = client.add_note("clients", "999", "some note")

    assert result["type"] == "validation_error"
