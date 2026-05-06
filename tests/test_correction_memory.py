"""
Tests for CorrectionMemory (Layer 4 of Hale Escalation).
Validates correction detection, topic locking, similarity match, expiry.
"""
import sys
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(THUNDERBIRD_ROOT))

import pytest
from core.ops.correction_memory import (
    CorrectionMemory,
    _extract_topic_keywords,
    _topic_similarity,
)


# ─── Correction-detection patterns ──────────────────────────────────────
class TestIsCorrection:
    def test_no_direct(self):
        assert CorrectionMemory.is_correction("No, that's wrong.")

    def test_again(self):
        assert CorrectionMemory.is_correction("You did it again.")

    def test_i_told_you(self):
        assert CorrectionMemory.is_correction("I told you not to ask.")

    def test_unacceptable(self):
        assert CorrectionMemory.is_correction("This is unacceptable.")

    def test_should_have(self):
        assert CorrectionMemory.is_correction("You should have caught that.")

    def test_clean_message(self):
        assert not CorrectionMemory.is_correction("Thanks, looks good.")

    def test_empty(self):
        assert not CorrectionMemory.is_correction("")


# ─── Topic extraction & similarity ──────────────────────────────────────
class TestTopicExtraction:
    def test_extract_keywords(self):
        kw = _extract_topic_keywords("Validate the McLeod dossier and check FPD")
        assert "mcleod" in kw
        assert "dossier" in kw
        assert "validate" in kw

    def test_stopwords_removed(self):
        kw = _extract_topic_keywords("the and is are these those")
        assert kw == []

    def test_similarity_high(self):
        a = ["mcleod", "dossier", "validate", "fpd"]
        b = ["mcleod", "dossier", "validation", "check"]
        assert _topic_similarity(a, b) > 0

    def test_similarity_zero(self):
        a = ["alpha", "bravo", "charlie"]
        b = ["delta", "echo", "foxtrot"]
        assert _topic_similarity(a, b) == 0.0


# ─── log_correction + auto-lock behavior ────────────────────────────────
class TestLogCorrection:
    def setup_method(self):
        # Each test gets a fresh store
        self.tmp = Path("/tmp/test_correction_memory.json")
        if self.tmp.exists():
            self.tmp.unlink()
        self.mem = CorrectionMemory(store_path=self.tmp, lock_threshold=2)

    def teardown_method(self):
        if self.tmp.exists():
            self.tmp.unlink()

    def test_first_correction_logged_not_locked(self):
        result = self.mem.log_correction(
            commander_message="Wrong, do it differently.",
            prior_request="Validate the McLeod dossier",
            prior_response="Maybe try this?",
        )
        assert result["logged"] is True
        assert result["correction_count"] == 1
        assert result["auto_locked"] is False

    def test_two_corrections_same_topic_locks(self):
        self.mem.log_correction(
            "Wrong.", "Validate McLeod dossier", "options menu"
        )
        result = self.mem.log_correction(
            "I told you again.", "Validate McLeod dossier and FPD", "still wrong"
        )
        assert result["correction_count"] == 2
        assert result["auto_locked"] is True

    def test_distinct_topics_separate(self):
        self.mem.log_correction("Wrong.", "Send Westbrook itinerary", "")
        self.mem.log_correction("Wrong.", "Update Furlow flight booking", "")
        stats = self.mem.stats()
        assert stats["total_topics"] >= 2

    def test_non_correction_not_logged(self):
        result = self.mem.log_correction(
            "Thanks!", "Send the email", ""
        )
        assert result["logged"] is False

    def test_no_keywords_not_logged(self):
        result = self.mem.log_correction(
            "Wrong.", "the a is", ""
        )
        assert result["logged"] is False


# ─── should_autoroute_sonnet ────────────────────────────────────────────
class TestAutoroute:
    def setup_method(self):
        self.tmp = Path("/tmp/test_correction_memory_autoroute.json")
        if self.tmp.exists():
            self.tmp.unlink()
        self.mem = CorrectionMemory(store_path=self.tmp, lock_threshold=2)

    def teardown_method(self):
        if self.tmp.exists():
            self.tmp.unlink()

    def test_autoroute_after_lock(self):
        self.mem.log_correction("Wrong.", "Validate McLeod dossier", "")
        self.mem.log_correction(
            "Again wrong.", "Validate McLeod dossier and FPD", ""
        )
        # Locked. Future similar request should auto-route.
        assert self.mem.should_autoroute_sonnet(
            "Please validate McLeod dossier today"
        ) is True

    def test_no_autoroute_before_lock(self):
        self.mem.log_correction("Wrong.", "Validate McLeod dossier", "")
        # Only 1 correction — not locked yet.
        assert self.mem.should_autoroute_sonnet(
            "Validate McLeod dossier"
        ) is False

    def test_no_autoroute_unrelated_topic(self):
        self.mem.log_correction("Wrong.", "Validate McLeod dossier", "")
        self.mem.log_correction(
            "Wrong.", "Validate McLeod dossier and FPD", ""
        )
        # Different topic should NOT autoroute
        assert self.mem.should_autoroute_sonnet(
            "What time does Westbrook depart Honolulu"
        ) is False

    def test_get_lock_reason_when_locked(self):
        self.mem.log_correction("Wrong.", "Validate McLeod dossier", "")
        self.mem.log_correction("Wrong.", "Validate McLeod dossier FPD", "")
        reason = self.mem.get_lock_reason("Validate McLeod dossier")
        assert reason is not None
        assert "topic_summary" in reason
        assert reason["correction_count"] == 2


# ─── Expiry ─────────────────────────────────────────────────────────────
class TestExpiry:
    def test_expired_topic_pruned(self):
        tmp = Path("/tmp/test_correction_memory_expiry.json")
        if tmp.exists():
            tmp.unlink()
        mem = CorrectionMemory(store_path=tmp, lock_threshold=2, lock_ttl_days=30)
        mem.log_correction("Wrong.", "Validate McLeod dossier", "")
        mem.log_correction("Wrong.", "Validate McLeod dossier FPD", "")

        # Manually backdate the topic to 31 days ago
        old = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        for h in mem._data:
            mem._data[h]["last_seen"] = old
        mem._save()

        # Reload and confirm pruning
        mem2 = CorrectionMemory(store_path=tmp, lock_threshold=2, lock_ttl_days=30)
        stats = mem2.stats()
        assert stats["total_topics"] == 0
        assert mem2.should_autoroute_sonnet("Validate McLeod dossier") is False
        tmp.unlink()


# ─── Persistence ────────────────────────────────────────────────────────
class TestPersistence:
    def test_round_trip(self):
        tmp = Path("/tmp/test_correction_memory_persist.json")
        if tmp.exists():
            tmp.unlink()
        mem = CorrectionMemory(store_path=tmp, lock_threshold=2)
        mem.log_correction("Wrong.", "Validate McLeod dossier", "")
        mem.log_correction("Wrong.", "Validate McLeod dossier FPD", "")
        # Reload from disk
        mem2 = CorrectionMemory(store_path=tmp, lock_threshold=2)
        assert mem2.should_autoroute_sonnet("Validate McLeod dossier") is True
        tmp.unlink()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
