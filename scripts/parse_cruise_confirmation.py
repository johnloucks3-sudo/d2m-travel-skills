#!/usr/bin/env python3
"""
parse_cruise_confirmation.py — D2M Cruise Planners AI replication.
Parses cruise booking confirmation PDFs or email bodies → structured JSON → TESS.

Usage:
    python3 scripts/parse_cruise_confirmation.py booking.pdf
    python3 scripts/parse_cruise_confirmation.py --email-id <gmail_thread_id>
    python3 scripts/parse_cruise_confirmation.py --dry-run booking.pdf

Output: {booking_ref, cruise_line, ship, sail_date, guests, cabin_type,
         fpd, deposit_paid, total_fare, commission_expected}
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

THUNDERBIRD = Path(__file__).parent.parent
sys.path.insert(0, str(THUNDERBIRD))

EXTRACTION_PROMPT = """
Extract booking confirmation details from this cruise line document.
Return ONLY valid JSON with these fields (null if not found):
{
  "booking_ref": "string — booking/reservation number",
  "cruise_line": "string — e.g. Regent Seven Seas, Silversea, Viking Ocean",
  "ship": "string — vessel name",
  "sail_date": "YYYY-MM-DD — embarkation date",
  "return_date": "YYYY-MM-DD — disembarkation date if present",
  "guests": ["string — full name of each guest"],
  "cabin_type": "string — cabin/suite category",
  "cabin_number": "string or null",
  "itinerary": "string — departure port to arrival port",
  "total_fare": "number — total price in USD (null if not found)",
  "deposit_paid": "number — deposit amount in USD",
  "balance_due": "number — remaining balance",
  "fpd": "YYYY-MM-DD — final payment date (null if not found)",
  "commission_rate": "number — agent commission % (null if not in document)",
  "commission_expected": "number — calculated commission in USD (null if not in document)",
  "special_requests": "string or null",
  "raw_notes": "string — any other important details"
}
Only output the JSON object. No explanation.
"""


def extract_text_from_pdf(pdf_path: str) -> str:
    """Try docling first, fall back to llamaparse, fall back to pypdf."""
    try:
        from core.ai_infra.thunderbird_docling import extract_pdf
        result = extract_pdf(pdf_path)
        if result and len(result) > 100:
            return result
    except Exception:
        pass

    try:
        from core.ai_infra.thunderbird_llamaparse import extract_text
        result = extract_text(pdf_path)
        if result and len(result) > 100:
            return result
    except Exception:
        pass

    try:
        import pypdf
        reader = pypdf.PdfReader(pdf_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        raise RuntimeError(f"All PDF extractors failed for {pdf_path}: {e}")


def parse_with_gemini(text: str) -> dict:
    """Use Gemini via the existing Thunderbird Gemini adapter."""
    try:
        from core.ai_infra.thunderbird_gemini import generate
        response = generate(EXTRACTION_PROMPT + "\n\nDOCUMENT:\n" + text[:50000])
        raw = response.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
        return json.loads(raw)
    except Exception:
        pass
    return {}


def parse_with_claude(text: str) -> dict:
    """Fallback: use Claude Haiku for extraction."""
    import subprocess
    env = dict(os.environ)
    creds_path = Path.home() / ".claude" / ".credentials.json"
    if creds_path.exists():
        import json as _json
        creds = _json.loads(creds_path.read_text())
        env["CLAUDE_CODE_OAUTH_TOKEN"] = creds.get("claudeAiOauth", {}).get("accessToken", "")

    prompt = EXTRACTION_PROMPT + "\n\nDOCUMENT:\n" + text[:30000]
    r = subprocess.run(
        [str(Path.home() / ".local/bin/claude"), "--dangerously-skip-permissions",
         "--model", "claude-haiku-4-5-20251001", "-p", prompt],
        capture_output=True, text=True, timeout=60, env=env,
    )
    raw = (r.stdout or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    try:
        return json.loads(raw)
    except Exception:
        return {"parse_error": raw[:200]}


def write_to_tess(booking: dict) -> bool:
    """Write confirmed booking to TESS if all required fields are present."""
    required = ["booking_ref", "cruise_line", "ship", "sail_date"]
    if not all(booking.get(f) for f in required):
        return False
    try:
        from core.integrations.tess_client import TessClient
        client = TessClient()
        client.update_booking(booking["booking_ref"], booking)
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="Parse cruise booking confirmation")
    parser.add_argument("pdf", nargs="?", help="Path to confirmation PDF")
    parser.add_argument("--email-id", help="Gmail thread ID to fetch confirmation from")
    parser.add_argument("--dry-run", action="store_true", help="Print result, don't write to TESS")
    parser.add_argument("--output", help="Write JSON output to this file")
    args = parser.parse_args()

    text = ""
    source = ""

    if args.pdf:
        pdf_path = Path(args.pdf)
        if not pdf_path.exists():
            print(f"ERROR: File not found: {args.pdf}", file=sys.stderr)
            sys.exit(1)
        print(f"Extracting text from: {pdf_path.name}")
        text = extract_text_from_pdf(str(pdf_path))
        source = str(pdf_path)
    elif args.email_id:
        print(f"Fetching email thread: {args.email_id}")
        try:
            from core.email.thunderbird_gmail import get_thread_body
            text = get_thread_body(args.email_id)
            source = f"email:{args.email_id}"
        except Exception as e:
            print(f"ERROR: Could not fetch email: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Read from stdin
        text = sys.stdin.read()
        source = "stdin"

    if not text or len(text) < 50:
        print("ERROR: Could not extract text from document", file=sys.stderr)
        sys.exit(1)

    print(f"Extracted {len(text)} chars from {source}")
    print("Parsing with AI...")

    # Try Gemini first, fall back to Claude Haiku
    booking = parse_with_gemini(text)
    if not booking or "parse_error" in booking:
        print("Gemini parse failed, trying Claude Haiku...")
        booking = parse_with_claude(text)

    if "parse_error" in booking:
        print(f"WARNING: Parse error: {booking['parse_error']}", file=sys.stderr)

    booking["_source"] = source
    booking["_parsed_at"] = __import__("datetime").datetime.utcnow().isoformat() + "Z"

    result_json = json.dumps(booking, indent=2)
    print("\n--- PARSED BOOKING ---")
    print(result_json)

    if args.output:
        Path(args.output).write_text(result_json)
        print(f"\nSaved to: {args.output}")

    if not args.dry_run and booking.get("booking_ref"):
        print("\nWriting to TESS...")
        ok = write_to_tess(booking)
        print(f"TESS write: {'✅ SUCCESS' if ok else '⚠️  SKIPPED (TESS client unavailable)'}")
    elif args.dry_run:
        print("\n[dry-run] — TESS write skipped")

    return booking


if __name__ == "__main__":
    main()
