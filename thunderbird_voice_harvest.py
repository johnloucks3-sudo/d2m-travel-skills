#!/usr/bin/env python3
"""
thunderbird_voice_harvest.py
============================
Dreams2Memories Travel — Commander Voice Example Harvester

Scans sent mail from up to 3 Gmail accounts (johnloucks3, yodainva, d2mconcierge),
extracts genuine John-written emails, tags by recipient tier, scores for voice richness,
and saves as config/voice_examples.json for few-shot injection into drafting prompts.

Usage:
    # One-time OAuth per personal account (opens browser):
    python3 thunderbird_voice_harvest.py --authorize johnloucks3@gmail.com
    python3 thunderbird_voice_harvest.py --authorize yodainva@gmail.com

    # Run the harvest:
    python3 thunderbird_voice_harvest.py --harvest

    # Show stats on what was collected:
    python3 thunderbird_voice_harvest.py --stats

    # Inject 5 examples into a test prompt (smoke test):
    python3 thunderbird_voice_harvest.py --test "draft email to client about final payment"
"""

import argparse
import base64
import html
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ── Config ────────────────────────────────────────────────────────────────────

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
CONFIG_DIR = THUNDERBIRD_DIR / "config"
VOICE_TOKENS_DIR = CONFIG_DIR / "voice_tokens"
OAUTH_CREDENTIALS_FILE = THUNDERBIRD_DIR / "gmail_oauth_credentials.json"
OUTPUT_FILE = CONFIG_DIR / "voice_examples.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# d2mconcierge uses the existing main token
D2M_TOKEN_FILE = THUNDERBIRD_DIR / "gmail_token.json"

# Target: collect up to this many examples per tier
MAX_PER_TIER = 30
# Minimum body length to qualify as a real email
MIN_BODY_CHARS = 60
# Maximum — skip novels (newsletters, long forwards)
MAX_BODY_CHARS = 3000
# How far back to search
DAYS_BACK = 400

ACCOUNTS = [
    {"address": "johnloucks3@gmail.com",          "token": VOICE_TOKENS_DIR / "johnloucks3_token.json"},
    {"address": "yodainva@gmail.com",             "token": VOICE_TOKENS_DIR / "yodainva_token.json"},
    {"address": "jl3lovegrouptravel@gmail.com",   "token": VOICE_TOKENS_DIR / "jl3lovegrouptravel_token.json"},
    {"address": "d2mconcierge@gmail.com",         "token": D2M_TOKEN_FILE},
]

# ── Tier detection ─────────────────────────────────────────────────────────────

# Client last names from active dossiers + known clients
CLIENT_LAST_NAMES = {
    "lyons", "westbrook", "furlow", "britan", "loucks", "kuklinski",
    "mcleod", "ryan", "justin",
}

VENDOR_DOMAINS = {
    "silversea.com", "rssc.com", "regent-seven-seas.com", "cunard.com",
    "oceania.com", "seabourn.com", "vikingcruises.com", "amawaterways.com",
    "ponant.com", "viator.com", "getyourguide.com", "blacklane.com",
    "mozio.com", "taap.com", "bedsonline.com", "asta.org", "clia.org",
    "concierge@d2mluxury.quest", "d2mluxury.quest",
}

FAMILY_PATTERNS = re.compile(
    r"\b(ryan|justin|brittany|mom|dad|sis|bro)\b", re.IGNORECASE
)

# Known Commander addresses — emails here are staff/internal
COMMANDER_ADDRS = {
    "johnloucks3@gmail.com", "yodainva@gmail.com",
    "jl3lovegrouptravel@gmail.com",
    "d2mconcierge@gmail.com", "concierge@d2mluxury.quest",
    "john@d2mluxury.quest",
}

# Markers that indicate automated / template content — skip these
AUTO_MARKERS = [
    "unsubscribe", "this email was sent to", "you're receiving this",
    "click here to", "privacy policy", "terms of service",
    "do not reply", "noreply", "no-reply",
    "automated message", "system notification",
]

logger = logging.getLogger("voice_harvest")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


# ── Auth ──────────────────────────────────────────────────────────────────────

def authorize_account(email: str) -> None:
    """Run one-time OAuth flow for a personal Gmail account."""
    if not OAUTH_CREDENTIALS_FILE.exists():
        print(f"ERROR: {OAUTH_CREDENTIALS_FILE} not found.")
        print("Download OAuth client JSON from console.cloud.google.com → d2m-python-pipeline.")
        sys.exit(1)

    VOICE_TOKENS_DIR.mkdir(parents=True, exist_ok=True)

    # Find matching account config
    acct = next((a for a in ACCOUNTS if a["address"] == email), None)
    if not acct:
        print(f"ERROR: {email} is not in the configured accounts list.")
        sys.exit(1)

    token_file = acct["token"]
    flow = InstalledAppFlow.from_client_secrets_file(str(OAUTH_CREDENTIALS_FILE), SCOPES)
    creds = flow.run_local_server(port=0, login_hint=email)
    token_file.write_text(creds.to_json())
    print(f"OK — token saved: {token_file}")


def _get_service(token_file: Path):
    """Build an authenticated Gmail service from a token file."""
    if not token_file.exists():
        return None

    creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            token_file.write_text(creds.to_json())
        except Exception as e:
            logger.warning("Token refresh failed for %s: %s", token_file, e)
            return None

    if not creds.valid:
        return None

    return build("gmail", "v1", credentials=creds)


# ── Text extraction ───────────────────────────────────────────────────────────

def _decode_part(part: dict) -> str:
    """Decode a MIME message part's body."""
    data = part.get("body", {}).get("data", "")
    if not data:
        return ""
    try:
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    except Exception:
        return ""


def _extract_body(payload: dict) -> str:
    """Extract clean plain-text body from a Gmail message payload."""
    mime_type = payload.get("mimeType", "")
    parts = payload.get("parts", [])

    if mime_type == "text/plain":
        return _decode_part(payload)

    if mime_type == "text/html":
        raw = _decode_part(payload)
        return _strip_html(raw)

    # Multipart — prefer text/plain, fall back to text/html
    plain = ""
    html_fallback = ""
    for part in parts:
        ptype = part.get("mimeType", "")
        if ptype == "text/plain":
            plain = _decode_part(part)
        elif ptype == "text/html":
            html_fallback = _strip_html(_decode_part(part))
        elif ptype.startswith("multipart/"):
            nested = _extract_body(part)
            if nested:
                plain = nested

    return plain or html_fallback


def _strip_html(text: str) -> str:
    """Strip HTML tags and decode entities."""
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _strip_quoted(text: str) -> str:
    """Remove quoted reply blocks and forwarded message headers."""
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Quote markers
        if stripped.startswith(">"):
            continue
        # "On Mon, Mar ... wrote:" pattern
        if re.match(r"On .{10,80} wrote:", stripped):
            break
        # Forwarded message header
        if re.match(r"[-_]{3,}.*forwarded", stripped, re.IGNORECASE):
            break
        # Gmail's "From:" header in a quoted block
        if re.match(r"From:\s+\S+.+\d{4}", stripped):
            break
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def _clean_body(raw: str) -> str:
    """Full clean pipeline: strip HTML → strip quoted → normalize whitespace."""
    text = _strip_quoted(raw)
    # Collapse 3+ blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove lines that are just dashes/equals (dividers)
    text = re.sub(r"^\s*[-=_]{4,}\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


# ── Quality and tier ──────────────────────────────────────────────────────────

def _is_automated(body: str, subject: str) -> bool:
    """Return True if this looks like a templated or automated message."""
    combined = (body + subject).lower()
    return any(marker in combined for marker in AUTO_MARKERS)


def _is_forward(subject: str) -> bool:
    return subject.strip().lower().startswith(("fwd:", "fw:"))


def _detect_tier(to_addr: str, subject: str, body: str) -> str:
    """Tag this email's recipient tier."""
    to_lower = to_addr.lower()
    combined_lower = (subject + " " + body[:200]).lower()

    if to_lower in COMMANDER_ADDRS:
        # Self-submitted voice example (e.g. d2mconcierge → johnloucks3).
        # Check body content to find the real tier rather than defaulting to internal.
        if re.match(r"^Hi \w", body.strip(), re.IGNORECASE):
            # Looks like a client email — detect from content
            domain = ""  # no external recipient to check
            if any(name in combined_lower for name in CLIENT_LAST_NAMES):
                return "client"
            # Travel keywords signal a client email
            travel_keywords = {"cruise", "voyage", "hotel", "flight", "booking",
                               "itinerary", "departure", "arrival", "cabin", "resort"}
            if any(kw in combined_lower for kw in travel_keywords):
                return "client"
            if any(vd in combined_lower for vd in VENDOR_DOMAINS):
                return "vendor"
            # Generic "Hi Name," with no travel context — still likely client
            return "client"
        return "internal"

    domain = to_lower.split("@")[-1] if "@" in to_lower else ""
    if any(vd in domain for vd in VENDOR_DOMAINS):
        return "vendor"

    if any(name in combined_lower for name in CLIENT_LAST_NAMES):
        return "client"

    if FAMILY_PATTERNS.search(body[:300]):
        return "family"

    return "personal"


def _voice_score(body: str) -> int:
    """Score 0-10 for how voice-rich this email is.

    Higher = more personal, specific, confident — better as a voice example.
    """
    score = 0
    # Length sweet spot: 100-600 chars after clean
    length = len(body)
    if 80 <= length <= 600:
        score += 3
    elif 600 < length <= 1200:
        score += 2
    elif length > 1200:
        score += 1

    # Has a greeting with first name
    if re.search(r"^Hi \w+", body, re.MULTILINE):
        score += 2

    # Closes with "Thanks" or "Thank you"
    if re.search(r"\b(Thanks|Thank you),?\s*John\b", body, re.IGNORECASE):
        score += 2

    # Contains specific details: dates, names, dollar amounts, flight numbers
    if re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}", body):
        score += 1
    if re.search(r"\$[\d,]+", body):
        score += 1
    if re.search(r"\b[A-Z]{2}\d{3,4}\b", body):  # flight number pattern
        score += 1

    return min(score, 10)


# ── Harvest ───────────────────────────────────────────────────────────────────

def _harvest_account(address: str, token_file: Path, since_date: str) -> list[dict]:
    """Fetch and process sent mail from one account."""
    service = _get_service(token_file)
    if not service:
        logger.warning("No valid token for %s — skipping (run --authorize %s)", address, address)
        return []

    logger.info("Scanning %s sent mail since %s ...", address, since_date)
    query = f"in:sent after:{since_date}"

    examples = []
    page_token = None
    fetched = 0

    while True:
        try:
            kwargs = {"userId": "me", "q": query, "maxResults": 100}
            if page_token:
                kwargs["pageToken"] = page_token

            resp = service.users().messages().list(**kwargs).execute()
            messages = resp.get("messages", [])
            if not messages:
                break

            for msg_ref in messages:
                msg_id = msg_ref["id"]
                try:
                    msg = (
                        service.users()
                        .messages()
                        .get(userId="me", id=msg_id, format="full")
                        .execute()
                    )
                except HttpError as e:
                    logger.debug("Skipping message %s: %s", msg_id, e)
                    continue

                headers = {
                    h["name"].lower(): h["value"]
                    for h in msg.get("payload", {}).get("headers", [])
                }
                subject = headers.get("subject", "")
                to_addr = headers.get("to", "")
                date_str = headers.get("date", "")

                # Skip forwards
                if _is_forward(subject):
                    continue

                raw_body = _extract_body(msg.get("payload", {}))
                body = _clean_body(raw_body)

                # Quality gates
                if len(body) < MIN_BODY_CHARS or len(body) > MAX_BODY_CHARS:
                    continue
                if _is_automated(body, subject):
                    continue

                tier = _detect_tier(to_addr, subject, body)
                score = _voice_score(body)

                if score < 2:
                    continue  # Too sparse to be useful

                examples.append({
                    "account": address,
                    "tier": tier,
                    "subject": subject,
                    "to": to_addr,
                    "date": date_str,
                    "body": body,
                    "score": score,
                })
                fetched += 1

            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        except HttpError as e:
            logger.error("Gmail API error for %s: %s", address, e)
            break

    logger.info("  %s: found %d qualifying examples", address, fetched)
    return examples


def harvest_all() -> dict:
    """Run harvest across all three accounts and save output."""
    VOICE_TOKENS_DIR.mkdir(parents=True, exist_ok=True)

    since_date = (datetime.now() - timedelta(days=DAYS_BACK)).strftime("%Y/%m/%d")
    all_examples = []

    for acct in ACCOUNTS:
        examples = _harvest_account(acct["address"], acct["token"], since_date)
        all_examples.extend(examples)

    # Sort by score descending, then deduplicate near-identical bodies
    all_examples.sort(key=lambda x: -x["score"])
    deduped = _deduplicate(all_examples)

    # Cap per tier
    by_tier: dict[str, list] = {}
    for ex in deduped:
        tier = ex["tier"]
        bucket = by_tier.setdefault(tier, [])
        if len(bucket) < MAX_PER_TIER:
            bucket.append(ex)

    # Flatten back, preserve tier ordering
    final: list[dict] = []
    for tier in ("client", "vendor", "internal", "family", "personal"):
        final.extend(by_tier.get(tier, []))

    output = {
        "meta": {
            "generated": datetime.now().isoformat(),
            "accounts_scanned": [a["address"] for a in ACCOUNTS],
            "days_back": DAYS_BACK,
            "total_examples": len(final),
            "by_tier": {tier: len(items) for tier, items in by_tier.items()},
        },
        "examples": final,
    }

    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    logger.info("Saved %d examples to %s", len(final), OUTPUT_FILE)

    # Print summary
    print("\n── Voice Harvest Complete ─────────────────────────────")
    print(f"Total examples: {len(final)}")
    for tier, items in by_tier.items():
        print(f"  {tier:12s}: {len(items)}")
    print(f"\nOutput: {OUTPUT_FILE}")
    return output


def _deduplicate(examples: list[dict]) -> list[dict]:
    """Remove near-duplicate emails (same first 80 chars of body)."""
    seen: set[str] = set()
    out = []
    for ex in examples:
        key = ex["body"][:80].strip().lower()
        if key not in seen:
            seen.add(key)
            out.append(ex)
    return out


# ── Few-shot retrieval (used by tools_sdk) ────────────────────────────────────

def get_voice_examples(context: str, tier: str = "client", n: int = 5) -> list[dict]:
    """Return n voice examples most relevant to context and tier.

    Called by _call_via_anthropic_direct at draft time.
    Tuned 2026-03-23: recency boost, min score 3, diversity across tiers,
    body capped at 600 chars to keep few-shot block token-efficient.

    context: the draft prompt (used for keyword matching)
    tier: "client" | "vendor" | "internal" | "family" | "personal"
    n: number of examples to return (default 5)
    """
    if not OUTPUT_FILE.exists():
        return []
    try:
        data = json.loads(OUTPUT_FILE.read_text())
    except Exception:
        return []

    from datetime import datetime, timedelta, timezone
    examples = data.get("examples", [])

    # Quality gate — raise minimum voice score from 2 → 3
    examples = [e for e in examples if e.get("score", 0) >= 3]

    # Keyword match: score by overlap with context
    ctx_words = set(re.findall(r"\b\w{4,}\b", context.lower()))
    now = datetime.now(tz=timezone.utc)

    def relevance(ex: dict) -> float:
        body_words = set(re.findall(r"\b\w{4,}\b", (ex.get("body", "") + ex.get("subject", "")).lower()))
        overlap = len(ctx_words & body_words)
        # Recency boost: emails from last 90 days get +1.5
        try:
            from email.utils import parsedate_to_datetime
            sent = parsedate_to_datetime(ex.get("date", ""))
            sent_utc = sent.astimezone(timezone.utc)
            age_days = (now - sent_utc).days
            recency = 1.5 if age_days <= 90 else (0.75 if age_days <= 365 else 0.0)
        except Exception:
            recency = 0.0
        # Voice score 50%, context overlap 30%, recency 20%
        return ex.get("score", 0) * 0.5 + overlap * 0.3 + recency * 0.2

    # Primary tier
    tier_pool = [e for e in examples if e.get("tier") == tier]
    if len(tier_pool) < n:
        tier_pool = examples  # widen to all tiers

    scored = sorted(tier_pool, key=relevance, reverse=True)

    # Diversity: ensure at most 3 from same tier in final n
    selected, tier_counts = [], {}
    for ex in scored:
        t = ex.get("tier", "other")
        if tier_counts.get(t, 0) >= 3:
            continue
        # Cap body at 600 chars — keeps few-shot block token-efficient
        ex_trimmed = dict(ex)
        if len(ex_trimmed.get("body", "")) > 600:
            ex_trimmed["body"] = ex_trimmed["body"][:597] + "..."
        selected.append(ex_trimmed)
        tier_counts[t] = tier_counts.get(t, 0) + 1
        if len(selected) >= n:
            break

    return selected


def format_few_shot_block(examples: list[dict]) -> str:
    """Format examples as a system-prompt few-shot block."""
    if not examples:
        return ""

    lines = ["# Commander Voice Examples — Write Like These\n"]
    lines.append(
        "The following are real emails written by John Loucks. "
        "Match his rhythm, brevity, warmth, and specificity. "
        "Do not imitate structure mechanically — absorb the voice.\n"
    )

    for i, ex in enumerate(examples, 1):
        tier_label = ex.get("tier", "").upper()
        subj = ex.get("subject", "")
        body = ex.get("body", "")
        lines.append(f"--- Example {i} [{tier_label}] — Subject: {subj} ---")
        lines.append(body)
        lines.append("")

    return "\n".join(lines)


# ── Auto-sync from Gmail sent folder (#3) ─────────────────────────────────────

SYNC_STATE_FILE = CONFIG_DIR / "voice_sync_state.json"


def _load_sync_state() -> dict:
    if SYNC_STATE_FILE.exists():
        try:
            return json.loads(SYNC_STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_sync_state(state: dict) -> None:
    SYNC_STATE_FILE.write_text(json.dumps(state, indent=2))


def sync_from_sent() -> None:
    """Append new sent emails from d2mconcierge to voice_examples.json.

    Tracks last sync timestamp in config/voice_sync_state.json so each run
    only pulls emails sent since the previous sync. Run nightly via systemd.
    """
    if not OUTPUT_FILE.exists():
        print("No voice_examples.json found — run --harvest first.")
        return

    state = _load_sync_state()
    last_sync = state.get("last_sync_date")

    if last_sync:
        since_date = last_sync
        print(f"Syncing d2mconcierge sent mail since {since_date} ...")
    else:
        # First sync: only look back 30 days (full history already in harvest)
        since_date = (datetime.now() - timedelta(days=30)).strftime("%Y/%m/%d")
        print(f"First sync — looking back 30 days ({since_date}) ...")

    # Load existing examples and build dedup fingerprint set
    data = json.loads(OUTPUT_FILE.read_text())
    existing = data.get("examples", [])
    seen_keys: set[str] = {ex["body"][:80].strip().lower() for ex in existing}

    # Harvest new examples from d2mconcierge + johnloucks3 (drafts approved to either)
    sync_addresses = {"d2mconcierge@gmail.com", "johnloucks3@gmail.com"}
    new_examples = []
    for acct in ACCOUNTS:
        if acct["address"] in sync_addresses:
            new_examples.extend(_harvest_account(acct["address"], acct["token"], since_date))

    # Filter out duplicates
    fresh = [ex for ex in new_examples
             if ex["body"][:80].strip().lower() not in seen_keys]

    if not fresh:
        print("No new examples found.")
        _save_sync_state({"last_sync_date": datetime.now().strftime("%Y/%m/%d")})
        return

    # Append and re-sort by score; don't hard-cap on sync (let library grow)
    combined = existing + fresh
    combined.sort(key=lambda x: -x.get("score", 0))

    data["examples"] = combined
    data["meta"]["total_examples"] = len(combined)
    data["meta"]["last_sync"] = datetime.now().isoformat()

    # Update tier counts
    by_tier: dict[str, int] = {}
    for ex in combined:
        by_tier[ex.get("tier", "unknown")] = by_tier.get(ex.get("tier", "unknown"), 0) + 1
    data["meta"]["by_tier"] = by_tier

    OUTPUT_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    # Invalidate the _load_voice_card cache so tools_sdk picks up fresh examples
    # (voice harvest module may be imported — clear cached examples too)
    if hasattr(get_voice_examples, "_cache"):
        del get_voice_examples._cache  # type: ignore[attr-defined]

    _save_sync_state({"last_sync_date": datetime.now().strftime("%Y/%m/%d")})

    print(f"\n── Voice Sync Complete ────────────────────────────────")
    print(f"New examples added: {len(fresh)}")
    print(f"Library total:      {len(combined)}")
    for tier, count in by_tier.items():
        print(f"  {tier:12s}: {count}")


# ── Stats ─────────────────────────────────────────────────────────────────────

def show_stats() -> None:
    if not OUTPUT_FILE.exists():
        print(f"No harvest file found at {OUTPUT_FILE}")
        print("Run: python3 thunderbird_voice_harvest.py --harvest")
        return

    data = json.loads(OUTPUT_FILE.read_text())
    meta = data.get("meta", {})
    examples = data.get("examples", [])

    print("\n── Voice Examples Library ─────────────────────────────")
    print(f"Generated: {meta.get('generated', '?')}")
    print(f"Days back: {meta.get('days_back', '?')}")
    print(f"Accounts:  {', '.join(meta.get('accounts_scanned', []))}")
    print(f"Total:     {meta.get('total_examples', len(examples))} examples")
    print()
    for tier, count in meta.get("by_tier", {}).items():
        print(f"  {tier:12s}: {count}")

    # Show top 3 by score
    top = sorted(examples, key=lambda x: -x.get("score", 0))[:3]
    print("\nTop 3 by voice score:")
    for ex in top:
        print(f"  [{ex['score']}/10] {ex['subject'][:60]}  ({ex['tier']})")


# ── Test injection ────────────────────────────────────────────────────────────

def test_injection(context: str) -> None:
    examples = get_voice_examples(context, tier="client", n=5)
    if not examples:
        print("No examples found. Run --harvest first.")
        return
    block = format_few_shot_block(examples)
    print(block)
    print(f"\n── {len(examples)} examples injected ({len(block)} chars) ──")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="D2M Commander Voice Harvester")
    parser.add_argument("--authorize", metavar="EMAIL",
                        help="One-time OAuth flow for a Gmail account")
    parser.add_argument("--harvest", action="store_true",
                        help="Run the full harvest across all accounts")
    parser.add_argument("--stats", action="store_true",
                        help="Show stats on the current examples library")
    parser.add_argument("--sync", action="store_true",
                        help="Append new d2mconcierge sent mail to examples library (run nightly)")
    parser.add_argument("--test", metavar="CONTEXT",
                        help="Show 5 examples that would be injected for this context")

    args = parser.parse_args()

    if args.authorize:
        authorize_account(args.authorize)
    elif args.harvest:
        harvest_all()
    elif args.sync:
        sync_from_sent()
    elif args.stats:
        show_stats()
    elif args.test:
        test_injection(args.test)
    else:
        parser.print_help()
