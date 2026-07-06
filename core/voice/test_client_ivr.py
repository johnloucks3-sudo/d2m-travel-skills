#!/usr/bin/env python3
"""
test_client_ivr.py — Simulated call-flow test suite for core/voice/client_ivr.py

Stands in for the "10 real test calls" in the task spec: this environment has
no provisioned Twilio number or public endpoint to receive a real inbound
call, so these drive the same state machine (process_turn) that a real Twilio
webhook would call, with fabricated (non-client) fixture dossiers written to
a temp directory. Real-call validation against actual Twilio speech-to-text
output is still outstanding — see the module docstring's Known Limitations.

Run: python3 -m unittest core.voice.test_client_ivr -v
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from core.voice import client_ivr as ivr


FIXTURES = {
    "paid_client.md": (
        "---\n"
        "client: Testcase\n"
        "full_name: Wanda Pemberton\n"
        "cruise_line: Regent\n"
        "ship: Grandeur\n"
        'booking: "1234567"\n'
        "departure: 2027-03-10\n"
        "fpd: 2026-12-01\n"
        "fpd_amount: 5000\n"
        "payment_status: paid_in_full\n"
        "status: active\n"
        "---\n\n"
        "# Fixture dossier — Wanda Pemberton\n"
        "DOB 1975-05-02\n"
    ),
    "balance_due_client.md": (
        "---\n"
        "client: Testcase\n"
        "full_name: Harold Quince\n"
        "cruise_line: Viking\n"
        "ship: Mars\n"
        'booking: "7654321"\n'
        "departure: 2027-06-15\n"
        "fpd: 2027-03-15\n"
        "fpd_amount: 8200\n"
        "payment_status: deposit_paid\n"
        "status: active\n"
        "---\n\n"
        "# Fixture dossier — Harold Quince\n"
        "DOB 1968-11-20\n"
    ),
    "no_dob_client.md": (
        "---\n"
        "client: Testcase\n"
        "full_name: Priya Nakamura\n"
        "cruise_line: Silversea\n"
        "ship: Nova\n"
        'booking: "9988776"\n'
        "departure: 2027-09-01\n"
        "fpd: 2027-06-01\n"
        "fpd_amount: 6100\n"
        "payment_status: deposit_paid\n"
        "status: active\n"
        "---\n\n"
        "# Fixture dossier — Priya Nakamura (no DOB on file)\n"
    ),
    "ambiguous_a.md": (
        "---\n"
        "client: Testcase\n"
        "full_name: Sam Whitfield\n"
        "cruise_line: Regent\n"
        "ship: Splendor\n"
        'booking: "1112222"\n'
        "departure: 2027-01-01\n"
        "payment_status: paid_in_full\n"
        "status: active\n"
        "---\n\n# Fixture — Whitfield A\nDOB 1980-01-01\n"
    ),
    "ambiguous_b.md": (
        "---\n"
        "client: Testcase\n"
        "full_name: Pat Whitfield\n"
        "cruise_line: Regent\n"
        "ship: Explorer\n"
        'booking: "3334444"\n'
        "departure: 2027-02-02\n"
        "payment_status: paid_in_full\n"
        "status: active\n"
        "---\n\n# Fixture — Whitfield B\nDOB 1982-02-02\n"
    ),
}


class ClientIVRTestBase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="ivr_test_"))
        for name, content in FIXTURES.items():
            (self.tmpdir / name).write_text(content)
        self._orig_dossiers_dir = ivr.DOSSIERS_DIR
        self._orig_call_log = ivr.CALL_LOG
        ivr.DOSSIERS_DIR = self.tmpdir
        ivr.CALL_LOG = self.tmpdir / "call_log.jsonl"
        ivr.CALL_STATES.clear()

    def tearDown(self):
        ivr.DOSSIERS_DIR = self._orig_dossiers_dir
        ivr.CALL_LOG = self._orig_call_log
        ivr.CALL_STATES.clear()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _log_events(self) -> list[dict]:
        if not ivr.CALL_LOG.exists():
            return []
        return [json.loads(line) for line in ivr.CALL_LOG.read_text().splitlines() if line.strip()]


class TestIntentClassifier(unittest.TestCase):
    def test_final_payment(self):
        self.assertEqual(ivr.classify_intent("what's my final payment balance"), "final_payment")
        self.assertEqual(ivr.classify_intent("how much do I owe"), "final_payment")

    def test_excursions(self):
        self.assertEqual(ivr.classify_intent("tell me about my shore excursions"), "excursions")

    def test_concierge(self):
        self.assertEqual(ivr.classify_intent("who is my concierge"), "concierge")

    def test_booking_status(self):
        self.assertEqual(ivr.classify_intent("is my booking confirmed"), "booking_status")

    def test_escalate(self):
        self.assertEqual(ivr.classify_intent("I want to talk to a human"), "escalate")

    def test_unclear(self):
        self.assertEqual(ivr.classify_intent("what's the weather like"), "unclear")


class TestSpeechParsing(unittest.TestCase):
    def test_iso_date(self):
        self.assertEqual(ivr.parse_spoken_date("my birthday is 1975-05-02"), "1975-05-02")

    def test_slash_date(self):
        self.assertEqual(ivr.parse_spoken_date("5/2/1975"), "1975-05-02")

    def test_month_name_date(self):
        self.assertEqual(ivr.parse_spoken_date("May 2, 1975"), "1975-05-02")

    def test_no_match(self):
        self.assertIsNone(ivr.parse_spoken_date("I don't remember"))


class TestClientMatching(ClientIVRTestBase):
    def test_match_by_surname(self):
        records = ivr.load_client_records()
        matches = ivr.find_client_by_speech(records, "Pemberton")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["full_name"], "Wanda Pemberton")

    def test_match_by_booking_number(self):
        records = ivr.load_client_records()
        matches = ivr.find_client_by_speech(records, "7654321")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["full_name"], "Harold Quince")

    def test_no_match(self):
        records = ivr.load_client_records()
        matches = ivr.find_client_by_speech(records, "Nonexistent Person")
        self.assertEqual(matches, [])

    def test_ambiguous_surname_match(self):
        records = ivr.load_client_records()
        matches = ivr.find_client_by_speech(records, "Whitfield")
        self.assertEqual(len(matches), 2)


# ── Simulated call scenarios (stand-in for the 10 real test calls) ──────────
class TestSimulatedCalls(ClientIVRTestBase):
    def test_01_booking_status_verified_with_dob(self):
        sid = "CA_test_01"
        ivr.process_turn(sid, "+15550001111", "", "")               # greeting
        ivr.process_turn(sid, "+15550001111", "Pemberton", "")       # identify
        twiml = ivr.process_turn(sid, "+15550001111", "what's my booking status", "")  # intent -> verify
        self.assertIn("date of birth", twiml)
        twiml = ivr.process_turn(sid, "+15550001111", "May 2, 1975", "")  # verify -> response
        self.assertIn("Regent", twiml)
        self.assertIn("paid in full", twiml.lower())
        events = self._log_events()
        self.assertTrue(any(e["event"] == "verified" for e in events))
        self.assertTrue(any(e["event"] == "response_given" and e["verified"] for e in events))

    def test_02_final_payment_verified_balance_due(self):
        sid = "CA_test_02"
        ivr.process_turn(sid, "+15550002222", "", "")
        ivr.process_turn(sid, "+15550002222", "Quince", "")
        ivr.process_turn(sid, "+15550002222", "when is my final payment due", "")
        twiml = ivr.process_turn(sid, "+15550002222", "November 20, 1968", "")
        self.assertIn("8,200", twiml)
        self.assertIn("March 15, 2027", twiml)

    def test_03_final_payment_wrong_dob_twice_escalates(self):
        sid = "CA_test_03"
        ivr.process_turn(sid, "+15550003333", "", "")
        ivr.process_turn(sid, "+15550003333", "Quince", "")
        ivr.process_turn(sid, "+15550003333", "final payment please", "")
        ivr.process_turn(sid, "+15550003333", "January 1, 1900", "")   # wrong, attempt 1
        twiml = ivr.process_turn(sid, "+15550003333", "January 1, 1900", "")  # wrong, attempt 2 -> escalate
        self.assertIn("connect you", twiml.lower())
        events = self._log_events()
        self.assertTrue(any(e["event"] == "escalated" and e["reason"] == "verification_failed" for e in events))
        self.assertNotIn(sid, ivr.CALL_STATES)

    def test_04_no_dob_on_file_falls_back_to_booking_digits(self):
        sid = "CA_test_04"
        ivr.process_turn(sid, "+15550004444", "", "")
        ivr.process_turn(sid, "+15550004444", "Nakamura", "")
        ivr.process_turn(sid, "+15550004444", "what's my balance", "")
        twiml = ivr.process_turn(sid, "+15550004444", "", "9988776")  # DTMF booking ref as fallback factor
        self.assertIn("6,100", twiml)

    def test_05_excursions_no_verification_required(self):
        sid = "CA_test_05"
        ivr.process_turn(sid, "+15550005555", "", "")
        ivr.process_turn(sid, "+15550005555", "Pemberton", "")
        twiml = ivr.process_turn(sid, "+15550005555", "what are my shore excursions", "")
        self.assertIn("excursions are confirmed", twiml)
        events = self._log_events()
        self.assertTrue(any(e["event"] == "response_given" and e["intent"] == "excursions" and not e["verified"]
                             for e in events))

    def test_06_concierge_intent(self):
        sid = "CA_test_06"
        ivr.process_turn(sid, "+15550006666", "", "")
        ivr.process_turn(sid, "+15550006666", "Pemberton", "")
        twiml = ivr.process_turn(sid, "+15550006666", "who is my concierge", "")
        self.assertIn(ivr.CONCIERGE_NAME, twiml)

    def test_07_unmatched_caller_escalates_after_retry(self):
        sid = "CA_test_07"
        ivr.process_turn(sid, "+15550007777", "", "")
        ivr.process_turn(sid, "+15550007777", "Nobody Here", "")
        twiml = ivr.process_turn(sid, "+15550007777", "Still Nobody", "")
        self.assertIn("connect you", twiml.lower())
        events = self._log_events()
        self.assertTrue(any(e["event"] == "escalated" and e["reason"] == "no_match" for e in events))

    def test_08_ambiguous_name_resolved_by_booking_ref(self):
        sid = "CA_test_08"
        ivr.process_turn(sid, "+15550008888", "", "")
        twiml = ivr.process_turn(sid, "+15550008888", "Whitfield", "")
        self.assertIn("more than one booking", twiml)
        twiml = ivr.process_turn(sid, "+15550008888", "", "3334444")
        self.assertIn("How can I help", twiml)
        self.assertEqual(ivr.CALL_STATES[sid]["record"]["full_name"], "Pat Whitfield")

    def test_09_explicit_human_request_at_identify_escalates_immediately(self):
        sid = "CA_test_09"
        ivr.process_turn(sid, "+15550009999", "", "")
        twiml = ivr.process_turn(sid, "+15550009999", "I want to speak to a human", "")
        self.assertIn("connect you", twiml.lower())
        events = self._log_events()
        self.assertTrue(any(e["event"] == "escalated" and e["reason"] == "explicit_human_request" for e in events))

    def test_10_followup_no_ends_call_then_new_question_reopens(self):
        sid = "CA_test_10"
        ivr.process_turn(sid, "+15550001010", "", "")
        ivr.process_turn(sid, "+15550001010", "Pemberton", "")
        ivr.process_turn(sid, "+15550001010", "who is my concierge", "")
        twiml = ivr.process_turn(sid, "+15550001010", "no thank you", "")
        self.assertIn("Have a wonderful day", twiml)
        self.assertNotIn(sid, ivr.CALL_STATES)

        # A second call from the same number is a fresh CallSid — no bleed-through state
        sid2 = "CA_test_10b"
        ivr.process_turn(sid2, "+15550001010", "", "")
        twiml2 = ivr.process_turn(sid2, "+15550001010", "Pemberton", "")
        self.assertIn("How can I help", twiml2)


class TestStatusCallback(ClientIVRTestBase):
    def test_call_completed_logs_duration_and_clears_state(self):
        sid = "CA_status_test"
        ivr.CALL_STATES[sid] = ivr._new_state()
        ivr.handle_status_callback(sid, "completed", "142")
        events = self._log_events()
        self.assertTrue(any(e["event"] == "call_completed" and e["duration_seconds"] == 142 for e in events))
        self.assertNotIn(sid, ivr.CALL_STATES)

    def test_non_terminal_status_is_ignored(self):
        sid = "CA_status_test_2"
        ivr.handle_status_callback(sid, "ringing", "")
        self.assertEqual(self._log_events(), [])


class TestSignatureValidation(unittest.TestCase):
    def test_rejects_bad_signature(self):
        self.assertFalse(ivr.validate_twilio_request(
            "https://example.com/voice", {"CallSid": "CA1"}, "bogus", "sometoken"))

    def test_accepts_correct_signature(self):
        import hashlib
        import hmac
        from base64 import b64encode
        token = "sometoken"
        url = "https://example.com/voice"
        params = {"CallSid": "CA1", "From": "+15551234567"}
        s = url
        for key in sorted(params.keys()):
            s += key + params[key]
        sig = b64encode(hmac.new(token.encode(), s.encode(), hashlib.sha1).digest()).decode()
        self.assertTrue(ivr.validate_twilio_request(url, params, sig, token))


if __name__ == "__main__":
    unittest.main()
