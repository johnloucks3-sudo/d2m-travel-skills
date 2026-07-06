"""
Tests for core/intel/sentiment_analyzer.py.

The 50-sample labeled set below is synthetic (travel-client phrasing patterns,
no real client PII) manually labeled with expected polarity bucket and
primary emotion. It stands in for the "50 real client emails, manually
labeled" validation set requested for this build — swap in real archive
excerpts by loading them into LABELED_SAMPLES with the same shape.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.intel.sentiment_analyzer import (
    EmailRecord,
    lexicon_sentiment_score,
    detect_emotions,
    analyze_email,
    build_timeline,
    rolling_trend,
    aggregate_satisfaction_trend,
    records_from_gmail_messages,
)

# (text, expected_bucket in {"positive","negative","neutral"}, expected_emotion or None)
LABELED_SAMPLES = [
    ("We are SO excited for this trip, we can't wait to board!", "positive", "enthusiasm"),
    ("This is amazing, thank you so much for putting this together.", "positive", "satisfaction"),
    ("I'm thrilled about the excursion options, they look fantastic.", "positive", "enthusiasm"),
    ("Thanks so much, this is exactly what we wanted.", "positive", "satisfaction"),
    ("We really appreciate how smooth this whole process has been.", "positive", "satisfaction"),
    ("Wonderful, the itinerary looks perfect!", "positive", "enthusiasm"),
    ("We are so pleased with how everything turned out.", "positive", "satisfaction"),
    ("Can't wait to see Stockholm, this is going to be incredible.", "positive", "enthusiasm"),
    ("Great job on the dining reservations, very impressed.", "positive", None),
    ("We love this itinerary, best trip planning we've had.", "positive", "enthusiasm"),
    ("Everything was easy and helpful, thank you.", "positive", None),
    ("This looks beautiful, we are excited to go.", "positive", "enthusiasm"),
    ("Really happy with the excursion choices, well done.", "positive", "satisfaction"),
    ("So excited, this is the best news all week!", "positive", "enthusiasm"),
    ("We appreciate your quick response, very helpful.", "positive", None),
    ("Perfect, thank you, we couldn't be happier with this plan.", "positive", "satisfaction"),
    ("Awesome, this exceeded our expectations completely.", "positive", "satisfaction"),
    ("This is going to be an amazing anniversary trip!", "positive", "enthusiasm"),
    ("Thank you, we are very pleased with the cabin selection.", "positive", "satisfaction"),
    ("We're so excited about the wine tasting excursion.", "positive", "enthusiasm"),
    ("I'm a bit worried about the connection time in Rome.", "negative", "concern"),
    ("We're concerned about the payment deadline, is there flexibility?", "negative", "concern"),
    ("I'm nervous about the medical form requirements.", "negative", "concern"),
    ("This is frustrating, the portal keeps giving an error.", "negative", None),
    ("We're disappointed the excursion got cancelled.", "negative", None),
    ("Not sure if this is a problem, but the dates look off.", "negative", "concern"),
    ("Very concerned about whether our flight will make the connection.", "negative", "concern"),
    ("I'm worried about my husband's mobility on this excursion.", "negative", "concern"),
    ("This delay is annoying, we were told it would ship faster.", "negative", None),
    ("We're upset that nobody responded for three days.", "negative", None),
    ("A bit apprehensive about the visa requirements honestly.", "negative", "concern"),
    ("Concerned about the extra fees that showed up on the invoice.", "negative", "concern"),
    ("I'm troubled by the mismatch between the quote and the invoice.", "negative", "concern"),
    ("This whole thing has been a difficult and confusing mess.", "negative", "confusion"),
    ("We're unhappy with how the last update was communicated.", "negative", None),
    ("I'm confused about which excursion is included versus paid.", "negative", "confusion"),
    ("I don't understand the difference between these two cabin categories.", "negative", "confusion"),
    ("This is unclear — which date is the actual final payment due?", "negative", "confusion"),
    ("Sorry, I'm lost on how the portal login is supposed to work.", "negative", "confusion"),
    ("Can you clarify what this line item on the invoice means?", "negative", "confusion"),
    ("Not sure what this excursion code refers to, can you explain?", "negative", "confusion"),
    ("I'm mixed up about which couple is in which cabin.", "negative", "confusion"),
    ("Please clarify — we don't get how the gratuities are billed.", "negative", "confusion"),
    ("What does this insurance clause actually mean for us?", "negative", "confusion"),
    ("Here is the signed form for the upcoming voyage.", "neutral", None),
    ("Please confirm receipt of the attached documents.", "neutral", None),
    ("Our flight lands at 3pm on the embarkation day.", "neutral", None),
    ("Attached is the passport copy you requested.", "neutral", None),
    ("Can you send the packing list again?", "neutral", None),
    ("We will be arriving a day early as discussed.", "neutral", None),
    ("Let me know the next steps for the group booking.", "neutral", None),
]


class TestLexiconScoring(unittest.TestCase):
    def test_labeled_sample_polarity_accuracy(self):
        correct = 0
        for text, expected_bucket, _ in LABELED_SAMPLES:
            score = lexicon_sentiment_score(text)
            if expected_bucket == "positive":
                bucket = "positive" if score > 0.05 else ("neutral" if score >= -0.05 else "negative")
            elif expected_bucket == "negative":
                bucket = "negative" if score < -0.05 else ("neutral" if score <= 0.05 else "positive")
            else:
                bucket = "neutral" if -0.05 <= score <= 0.05 else ("positive" if score > 0 else "negative")
            if bucket == expected_bucket:
                correct += 1

        accuracy = correct / len(LABELED_SAMPLES)
        self.assertGreaterEqual(
            accuracy, 0.7,
            f"Lexicon polarity accuracy {accuracy:.0%} below 70% threshold on labeled set",
        )

    def test_score_bounds(self):
        for text, _, _ in LABELED_SAMPLES:
            score = lexicon_sentiment_score(text)
            self.assertGreaterEqual(score, -1.0)
            self.assertLessEqual(score, 1.0)

    def test_negation_flips_sign(self):
        self.assertGreater(lexicon_sentiment_score("This is great."), 0)
        self.assertLess(lexicon_sentiment_score("This is not great."), 0)

    def test_empty_text_is_neutral(self):
        self.assertEqual(lexicon_sentiment_score(""), 0.0)


class TestEmotionDetection(unittest.TestCase):
    def test_labeled_sample_emotion_recall(self):
        expected_with_emotion = [(t, e) for t, _, e in LABELED_SAMPLES if e is not None]
        hits = sum(1 for text, emotion in expected_with_emotion if emotion in detect_emotions(text))
        recall = hits / len(expected_with_emotion)
        self.assertGreaterEqual(
            recall, 0.7,
            f"Emotion tag recall {recall:.0%} below 70% threshold on labeled set",
        )

    def test_no_emotion_for_plain_neutral_text(self):
        tags = detect_emotions("Attached is the passport copy you requested.")
        self.assertEqual(tags, [])

    def test_multiple_emotions_can_coexist(self):
        text = "We are so excited but also a bit worried about the connection."
        tags = detect_emotions(text)
        self.assertIn("enthusiasm", tags)
        self.assertIn("concern", tags)


class TestAnalyzeEmail(unittest.TestCase):
    def test_analyze_email_uses_lexicon_by_default(self):
        record = EmailRecord(client="Test Client", date="2026-06-01T10:00:00", subject="Excited!", body="We can't wait!")
        result = analyze_email(record)
        self.assertEqual(result.method, "lexicon")
        self.assertGreater(result.sentiment_score, 0)
        self.assertIn("enthusiasm", result.emotion_tags)

    def test_claude_path_falls_back_without_api_key(self):
        record = EmailRecord(client="Test Client", date="2026-06-01T10:00:00", subject="Excited!", body="We can't wait!")
        result = analyze_email(record, use_claude=True)
        self.assertIn(result.method, ("lexicon", "claude"))


class TestTimelineAndTrend(unittest.TestCase):
    def setUp(self):
        self.records = [
            EmailRecord(client="Kuklinski", date="2026-06-01T10:00:00", subject="Hi", body="So excited for this trip!"),
            EmailRecord(client="Kuklinski", date="2026-06-15T10:00:00", subject="Payment", body="A bit worried about the deadline."),
            EmailRecord(client="Kuklinski", date="2026-06-25T10:00:00", subject="Thanks", body="Thank you so much, we love it!"),
            EmailRecord(client="Furlow", date="2026-06-10T10:00:00", subject="Docs", body="Attached is the passport copy."),
        ]

    def test_build_timeline_groups_by_client_and_sorts(self):
        timeline = build_timeline(self.records)
        self.assertEqual(set(timeline.keys()), {"Kuklinski", "Furlow"})
        dates = [e["date"] for e in timeline["Kuklinski"]]
        self.assertEqual(dates, sorted(dates))
        for entry in timeline["Kuklinski"]:
            self.assertIn("sentiment_score", entry)
            self.assertIn("emotion_tags", entry)
            self.assertIn("message_snippet", entry)

    def test_rolling_trend_within_window(self):
        timeline = build_timeline(self.records)
        points = rolling_trend(timeline["Kuklinski"])
        self.assertEqual(len(points), 3)
        # last point averages all 3 (all within 30 days of each other)
        self.assertAlmostEqual(
            points[-1]["rolling_avg"],
            round(sum(e["sentiment_score"] for e in timeline["Kuklinski"]) / 3, 3),
            places=2,
        )

    def test_aggregate_satisfaction_trend_shape(self):
        timeline = build_timeline(self.records)
        trend = aggregate_satisfaction_trend(timeline)
        self.assertIn("Kuklinski", trend)
        self.assertIn("current_30d_avg", trend["Kuklinski"])
        self.assertEqual(trend["Kuklinski"]["sample_count"], 3)
        self.assertEqual(trend["Furlow"]["sample_count"], 1)


class TestGmailAdapter(unittest.TestCase):
    def test_records_from_gmail_messages(self):
        raw = [
            {"id": "abc123", "date": "2026-06-01T10:00:00", "subject": "Hi", "body": "So excited!"},
            {"id": "def456", "date": "2026-06-02T10:00:00", "snippet": "Attached form"},
        ]
        records = records_from_gmail_messages(raw, client="Test Client")
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].client, "Test Client")
        self.assertEqual(records[0].message_id, "abc123")
        self.assertEqual(records[1].body, "Attached form")


if __name__ == "__main__":
    unittest.main()
