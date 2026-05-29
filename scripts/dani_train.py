#!/usr/bin/env python3
"""
dani_train.py — Train Dani (A3) on Commander's voice from recent emails
======================================================================
Dreams2Memories Travel, LLC | Thunderbird Wing

Reads the last 14 days of johnloucks3@gmail.com sent emails, analyzes
voice patterns, tone, phrasing, and client-specific cadence. Produces
a training profile that Dani uses to match Commander's voice exactly.

Usage:
    python3 dani_train.py              # Run analysis and produce training data
    python3 dani_train.py --refresh    # Re-fetch emails from Gmail API
    python3 dani_train.py --status     # Show current training state

Author: Ms. Victoria "Victory" Hale, SES-6 — Thunderbird Wing Chief of Staff
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
TRAINING_FILE = THUNDERBIRD_DIR / "dani_training_data.json"
VOICE_PROFILE = THUNDERBIRD_DIR / "dani_voice_profile.json"
LOG_DIR = THUNDERBIRD_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)


def load_emails() -> list:
    """Load emails from cached training data."""
    if not TRAINING_FILE.exists():
        print(f"No training data found. Run with --refresh to fetch emails.")
        sys.exit(1)
    return json.loads(TRAINING_FILE.read_text())


def classify_recipient(to_field: str) -> str:
    """Classify recipient type based on email domain and context."""
    to_lower = to_field.lower()
    if "d2mconcierge" in to_lower or "@d2m" in to_lower:
        return "internal"
    if "iamheer" in to_lower:
        return "neighbor"
    if "westbrook" in to_lower or "rwestbrook" in to_lower:
        return "friend"
    if "kuklinski" in to_lower or "kyle" in to_lower:
        return "client"
    if "mcleod" in to_lower or "emcleod" in to_lower:
        return "client"
    if "gmail.com" in to_lower or "yahoo.com" in to_lower or "outlook.com" in to_lower:
        return "personal"
    return "other"


def analyze_voice(emails: list) -> dict:
    """Analyze Commander's voice patterns from sent emails."""
    stats = {
        "total_emails": len(emails),
        "by_recipient_type": Counter(),
        "common_openings": Counter(),
        "common_closings": Counter(),
        "signature_patterns": Counter(),
        "avg_body_length": 0,
        "contractions_use": {"yes": 0, "no": 0},
        "greetings": Counter(),
        "signoffs": Counter(),
    }

    total_body_len = 0
    body_count = 0
    sentences = []

    for e in emails:
        rtype = classify_recipient(e.get("to", ""))
        stats["by_recipient_type"][rtype] += 1

        body = e.get("body", "").strip()
        if not body:
            continue

        total_body_len += len(body)
        body_count += 1

        # Extract first line (greeting)
        lines = body.split("\n")
        first_line = ""
        for line in lines:
            line = line.strip()
            if line and not line.startswith("--") and not line.startswith("_"):
                first_line = line
                break

        if first_line:
            stats["common_openings"][first_line[:60]] += 1
            greeting = first_line.split(",")[0] if "," in first_line else first_line[:20]
            stats["greetings"][greeting.strip()] += 1

        # Extract last line (signoff)
        last_lines = []
        for line in reversed(lines):
            stripped = line.strip()
            if stripped and stripped not in last_lines:
                last_lines.append(stripped)
                if len(last_lines) >= 3:
                    break

        full_signoff = " | ".join(reversed(last_lines[:2]))
        if full_signoff:
            stats["common_closings"][full_signoff[:80]] += 1

        # Look for "Thanks" signoffs
        for line in reversed(lines):
            ls = line.strip()
            if ls.lower().startswith("thanks") or ls.lower().startswith("thank"):
                stats["signoffs"][ls] += 1
                break

        # Check for signature block
        for line in lines:
            ls = line.strip()
            if "John A Loucks" in ls or "Dreams2Memories" in ls or "719-291-0742" in ls:
                stats["signature_patterns"][ls[:50]] += 1

        # Count contractions (I'm, don't, it's, etc.)
        contraction_count = len(re.findall(r"\b\w+'\w+\b", body))
        if contraction_count > 0:
            stats["contractions_use"]["yes"] += 1
        else:
            stats["contractions_use"]["no"] += 1

        # Collect sentences for style analysis
        raw_sentences = re.split(r'[.!?]+', body)
        for s in raw_sentences:
            s = s.strip()
            if len(s) > 10:
                sentences.append(s)

    stats["avg_body_length"] = total_body_len // body_count if body_count else 0

    # Top patterns
    stats["top_greetings"] = stats["greetings"].most_common(5)
    stats["top_signoffs"] = stats["signoffs"].most_common(5)
    stats["top_openings"] = stats["common_openings"].most_common(5)

    # Determine contraction preference
    total_contractions = stats["contractions_use"]["yes"] + stats["contractions_use"]["no"]
    stats["contraction_rate"] = round(stats["contractions_use"]["yes"] / total_contractions, 2) if total_contractions else 0

    # Analyze sentence length
    if sentences:
        avg_words = sum(len(s.split()) for s in sentences) / len(sentences)
        stats["avg_sentence_words"] = round(avg_words, 1)
    else:
        stats["avg_sentence_words"] = 0

    return stats


def build_voice_profile(emails: list) -> dict:
    """Build a structured voice profile for Dani to use."""
    stats = analyze_voice(emails)

    # Categorize by recipient type for tone variation
    by_type = defaultdict(list)
    for e in emails:
        by_type[classify_recipient(e.get("to", ""))].append(e)

    recipient_notes = {}
    for rtype, group in by_type.items():
        profiles = []
        for e in group:
            body = e.get("body", "").strip()[:300]
            if body:
                profiles.append({
                    "to": e.get("to", "")[:40],
                    "subject": e.get("subject", "")[:60],
                    "tone_sample": body[:200],
                })
        recipient_notes[rtype] = profiles[:3]  # Keep 3 examples per type

    profile = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "source": "Last 14 days of johnloucks3@gmail.com sent mail",
        "email_count": stats["total_emails"],
        "voice_summary": {
            "avg_message_length_chars": stats["avg_body_length"],
            "avg_sentence_words": stats["avg_sentence_words"],
            "contraction_rate": stats["contraction_rate"],
            "uses_contractions": stats["contraction_rate"] > 0.3,
        },
        "greeting_patterns": {
            "most_common": [g for g, _ in stats["top_greetings"]],
            "typical_signoffs": [s for s, _ in stats["top_signoffs"]],
        },
        "hard_rules": [
            "NEVER use flowery or salesy language — Commander is direct",
            "NEVER say 'I'm excited to...' — Commander doesn't sell, he informs",
            "ALWAYS lead with the answer, not the context",
            "Use contractions (I'm, don't, it's) — natural cadence",
            "Keep sentences short — average 12-15 words",
            "Signature block: 'John' only for personal. Full block for clients.",
            "When correcting yourself, be brief — 'Correction:' then the fix",
            "Don't over-explain. Trust the recipient to follow.",
        ],
        "phrases_to_avoid": [
            "I'm thrilled to",
            "I'm excited to announce",
            "Let me walk you through",
            "This is where I earn my keep",
            "I'd be honored to",
            "Please don't hesitate to",
        ],
        "phrases_to_use": [
            "Here's what I found",
            "Let me know if I can help",
            "I was thinking",
            "Thanks",
            "My thoughts:",
            "Quick update:",
        ],
        "recipient_tone_samples": recipient_notes,
        "by_recipient_type": {
            rtype: count
            for rtype, count in stats["by_recipient_type"].items()
        },
    }

    VOICE_PROFILE.write_text(json.dumps(profile, indent=2))
    return profile


def print_summary(profile: dict):
    """Print a readable summary of the voice profile."""
    print("=" * 60)
    print("DANI VOICE PROFILE — Training Summary")
    print("=" * 60)
    print(f"Source: {profile['email_count']} emails from last 14 days")
    print()
    print("VOICE STATS:")
    print(f"  Avg message length: {profile['voice_summary']['avg_message_length_chars']} chars")
    print(f"  Avg sentence: {profile['voice_summary']['avg_sentence_words']} words")
    print(f"  Uses contractions: {profile['voice_summary']['uses_contractions']}")
    print()
    print("GREETINGS:")
    for g in profile['greeting_patterns']['most_common'][:3]:
        print(f"  \"{g}\"")
    print()
    print("SIGNOFFS:")
    for s in profile['greeting_patterns']['typical_signoffs'][:3]:
        print(f"  \"{s}\"")
    print()
    print("HARD RULES:")
    for r in profile['hard_rules']:
        print(f"  • {r}")
    print()
    print("RECIPIENT MIX:")
    for rtype, count in profile['by_recipient_type'].items():
        print(f"  {rtype}: {count}")
    print()
    print(f"Full profile saved to: {VOICE_PROFILE}")
    print("=" * 60)


def refresh_emails():
    """Fetch fresh emails from Gmail API."""
    import base64
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    token_file = THUNDERBIRD_DIR / "creds" / "johnloucks3_token.json"
    token_data = json.loads(token_file.read_text())
    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes", ["https://www.googleapis.com/auth/gmail.modify"]),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    service = build("gmail", "v1", credentials=creds)

    two_weeks = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y/%m/%d")
    results = service.users().messages().list(
        userId="me", q=f"from:johnloucks3@gmail.com after:{two_weeks}", maxResults=50
    ).execute()

    emails = []
    for m in results.get("messages", []):
        msg = service.users().messages().get(userId="me", id=m["id"], format="full").execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        body = ""
        parts = msg.get("payload", {}).get("parts", [msg.get("payload", {})])
        for part in parts:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                    break
        emails.append({
            "id": m["id"],
            "to": headers.get("To", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "body": body[:2000] if body else "",
        })

    TRAINING_FILE.write_text(json.dumps(emails, indent=2))
    print(f"Refreshed: {len(emails)} emails from last 14 days")
    return emails


def main():
    parser = argparse.ArgumentParser(description="Train Dani on Commander's voice")
    parser.add_argument("--refresh", action="store_true", help="Re-fetch emails from Gmail")
    parser.add_argument("--status", action="store_true", help="Show current training state")
    args = parser.parse_args()

    if args.refresh:
        emails = refresh_emails()
    else:
        emails = load_emails()

    if args.status:
        print(f"Training data: {len(emails)} emails")
        print(f"Voice profile: {VOICE_PROFILE.exists()}")
        if VOICE_PROFILE.exists():
            profile = json.loads(VOICE_PROFILE.read_text())
            print_summary(profile)
        return

    profile = build_voice_profile(emails)
    print_summary(profile)


if __name__ == "__main__":
    main()
