"""
Client Sentiment Analyzer
==========================
Scans client email threads and scores sentiment (-1..+1) plus emotion tags
(enthusiasm, concern, confusion, satisfaction) per message. Aggregates into
a per-client 30-day rolling satisfaction trend.

Two scoring paths:
- Lexicon (default, zero dependencies, always available) — core/intel/emotion_lexicon.py
- Claude API (--use-claude) — higher-quality, falls back to lexicon on any error

Input contract: EmailRecord (client, date, subject, body). Gmail data is
fetched upstream via the existing gmail_search_messages / gmail_read_thread
MCP tools (core/email/thunderbird_gmail.py) — records_from_gmail_messages()
adapts their raw message dicts into EmailRecord.

Output:
    sentiment_timeline_by_client.json — {client: [{date, message_snippet, sentiment_score, emotion_tags}, ...]}
    client_satisfaction_trend.json    — {client: {current_30d_avg, sample_count, trend_points: [{date, rolling_avg}]}}
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from core.intel.emotion_lexicon import (
    EMOTION_LEXICON,
    POSITIVE_WORDS,
    NEGATIVE_WORDS,
    NEGATIONS,
    INTENSIFIERS,
)

OUTPUT_DIR = Path(__file__).parent / "output"
TIMELINE_FILE = OUTPUT_DIR / "sentiment_timeline_by_client.json"
TREND_FILE = OUTPUT_DIR / "client_satisfaction_trend.json"

SNIPPET_LEN = 160
TREND_WINDOW_DAYS = 30

_WORD_RE = re.compile(r"[a-z']+")


@dataclass
class EmailRecord:
    client: str
    date: str  # ISO 8601
    subject: str
    body: str
    message_id: Optional[str] = None


@dataclass
class SentimentResult:
    sentiment_score: float
    emotion_tags: List[str]
    method: str  # "lexicon" | "claude"


def records_from_gmail_messages(messages: List[dict], client: str) -> List[EmailRecord]:
    """Adapt raw dicts from gmail_search_messages/gmail_read_thread into EmailRecord."""
    records = []
    for m in messages:
        records.append(
            EmailRecord(
                client=client,
                date=m.get("date") or m.get("internalDate") or "",
                subject=m.get("subject", ""),
                body=m.get("body") or m.get("snippet", ""),
                message_id=m.get("id"),
            )
        )
    return records


def lexicon_sentiment_score(text: str) -> float:
    """Weighted-word score in -1..+1, with negation flip and intensifier boost."""
    words = _WORD_RE.findall(text.lower())
    if not words:
        return 0.0

    total = 0.0
    hits = 0
    for i, word in enumerate(words):
        weight = POSITIVE_WORDS.get(word) or NEGATIVE_WORDS.get(word)
        if weight is None:
            continue

        window = words[max(0, i - 3):i]
        if any(n in window for n in NEGATIONS):
            weight = -weight
        for intensifier, factor in INTENSIFIERS.items():
            if intensifier in window:
                weight *= factor
                break

        total += weight
        hits += 1

    if hits == 0:
        return 0.0
    score = total / hits
    return max(-1.0, min(1.0, score))


def detect_emotions(text: str) -> List[str]:
    lowered = text.lower()
    tags = []
    for emotion, phrases in EMOTION_LEXICON.items():
        if any(phrase in lowered for phrase in phrases):
            tags.append(emotion)
    return tags


def analyze_with_claude(text: str, model: str = "claude-haiku-4-5-20251001") -> Optional[SentimentResult]:
    """Higher-quality sentiment + emotion extraction via Claude. Returns None on any failure."""
    try:
        import anthropic
    except ImportError:
        return None

    prompt = (
        "Analyze the sentiment of this client email. Reply with ONLY compact JSON: "
        '{"sentiment_score": <float -1 to 1>, "emotion_tags": [<subset of '
        '"enthusiasm","concern","confusion","satisfaction">]}\n\n'
        f"EMAIL:\n{text[:4000]}"
    )
    try:
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=model,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        raw = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        parsed = json.loads(raw)
        score = max(-1.0, min(1.0, float(parsed.get("sentiment_score", 0.0))))
        tags = [t for t in parsed.get("emotion_tags", []) if t in EMOTION_LEXICON]
        return SentimentResult(sentiment_score=score, emotion_tags=tags, method="claude")
    except Exception:
        return None


def analyze_email(record: EmailRecord, use_claude: bool = False) -> SentimentResult:
    text = f"{record.subject}\n{record.body}"

    if use_claude:
        result = analyze_with_claude(text)
        if result is not None:
            return result

    return SentimentResult(
        sentiment_score=lexicon_sentiment_score(text),
        emotion_tags=detect_emotions(text),
        method="lexicon",
    )


def _snippet(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    return collapsed[:SNIPPET_LEN] + ("..." if len(collapsed) > SNIPPET_LEN else "")


def build_timeline(records: List[EmailRecord], use_claude: bool = False) -> Dict[str, List[dict]]:
    """Group scored records by client, sorted oldest -> newest."""
    timeline: Dict[str, List[dict]] = {}
    for record in records:
        result = analyze_email(record, use_claude=use_claude)
        entry = {
            "date": record.date,
            "message_snippet": _snippet(record.body or record.subject),
            "sentiment_score": round(result.sentiment_score, 3),
            "emotion_tags": result.emotion_tags,
        }
        timeline.setdefault(record.client, []).append(entry)

    for client_entries in timeline.values():
        client_entries.sort(key=lambda e: e["date"])
    return timeline


def _parse_date(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def rolling_trend(entries: List[dict], window_days: int = TREND_WINDOW_DAYS) -> List[dict]:
    """For each entry, average sentiment_score over the preceding window_days."""
    dated = [(e, _parse_date(e["date"])) for e in entries]
    dated = [(e, d) for e, d in dated if d is not None]
    dated.sort(key=lambda pair: pair[1])

    points = []
    for i, (entry, date) in enumerate(dated):
        window_start = date - timedelta(days=window_days)
        window_scores = [
            e["sentiment_score"] for e, d in dated[: i + 1] if d >= window_start
        ]
        avg = sum(window_scores) / len(window_scores)
        points.append({"date": entry["date"], "rolling_avg": round(avg, 3)})
    return points


def aggregate_satisfaction_trend(timeline: Dict[str, List[dict]]) -> Dict[str, dict]:
    trend = {}
    for client, entries in timeline.items():
        points = rolling_trend(entries)
        trend[client] = {
            "current_30d_avg": points[-1]["rolling_avg"] if points else 0.0,
            "sample_count": len(entries),
            "trend_points": points,
        }
    return trend


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def run(
    records: List[EmailRecord],
    use_claude: bool = False,
    timeline_path: Path = TIMELINE_FILE,
    trend_path: Path = TREND_FILE,
) -> Dict[str, dict]:
    timeline = build_timeline(records, use_claude=use_claude)
    trend = aggregate_satisfaction_trend(timeline)
    save_json(timeline_path, timeline)
    save_json(trend_path, trend)
    return {"timeline": timeline, "trend": trend}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Client sentiment analyzer")
    parser.add_argument("--input", required=True, help="JSON file: list of {client, date, subject, body}")
    parser.add_argument("--use-claude", action="store_true")
    args = parser.parse_args()

    raw = json.loads(Path(args.input).read_text())
    input_records = [EmailRecord(**r) for r in raw]
    output = run(input_records, use_claude=args.use_claude)
    print(f"Wrote {TIMELINE_FILE} and {TREND_FILE}")
    print(f"Clients processed: {list(output['trend'].keys())}")
