#!/usr/bin/env python3
"""
Thunderbird Gemini File Reader — PDF/Document → Structured Extraction
======================================================================
A7 Sterling — 2026-06-05

CAPABILITY: Upload any PDF/document directly to Google AI File API.
Gemini processes the full document natively (up to 1M tokens) — no chunking,
no preprocessing, no text extraction. Entire cruise brochure in one shot.

PRIMARY USE CASE (Dembe / A2):
  - Read full Silversea/Regent/Viking voyage brochures
  - Extract: dining venues, excursion options, port schedules, cabin categories
  - Spencer Grand Tour: extract hotel options, tour timing, rail schedules
  - Any document >100 pages that would overflow standard context

USAGE:
    from core.ai_infra.gemini_file_reader import extract_from_pdf, ask_about_pdf

    # Extract structured data (dining, excursions, ports)
    data = extract_from_pdf("/path/to/silversea_mediterranean.pdf",
                            extract_type="cruise_brochure",
                            voyage_name="Silver Muse Mediterranean")

    # Free-form query against a document
    answer = ask_about_pdf("/path/to/brochure.pdf",
                           "What specialty dining venues are available and do they require reservations?")

SUPPORTED EXTRACT TYPES:
    "cruise_brochure"    → dining venues, excursions, ports, cabin categories, inclusions
    "hotel_listing"      → room types, amenities, dining, location, pricing tiers
    "tour_guide"         → activity options, timing, group sizes, booking requirements
    "rail_schedule"      → routes, departure times, classes, reservation requirements
    "generic"            → raw summary + key facts

FILE API NOTES:
  - Files persist 48h on Google servers (auto-deleted)
  - Max file size: 2 GB
  - Supported: PDF, plain text, images, audio, video
  - No additional cost beyond standard Gemini API (free-tier allowlist)
  - Files are isolated per API key — not shared
"""

import os
import time
import json
import logging
import requests
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger("thunderbird.gemini_file_reader")

_UPLOAD_BASE = "https://generativelanguage.googleapis.com/upload/v1beta/files"
_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
_DEFAULT_MODEL = "gemini-2.5-pro"  # 1M context, best for long documents
_USAGE_LOG = Path(__file__).parent / "data" / "gemini_file_usage.jsonl"

# Structured extraction prompts per document type
_EXTRACT_PROMPTS: dict[str, str] = {
    "cruise_brochure": """
You are a travel research assistant for a luxury travel agency.
Extract the following from this cruise brochure and return as valid JSON:
{
  "ship_name": "",
  "cruise_line": "",
  "itinerary_name": "",
  "duration_nights": 0,
  "embarkation_port": "",
  "disembarkation_port": "",
  "ports": [{"port": "", "country": "", "arrival": "", "departure": ""}],
  "included_dining": [""],
  "specialty_restaurants": [{"name": "", "cuisine": "", "reservation_required": true, "surcharge": ""}],
  "included_beverages": true,
  "included_excursions": [""],
  "optional_excursions": [{"name": "", "port": "", "duration": "", "price_approx": ""}],
  "cabin_categories": [{"category": "", "name": "", "size_sqft": "", "features": [""]}],
  "inclusions": [""],
  "exclusions": [""],
  "gratuities_included": true,
  "business_class_air_included": false,
  "key_selling_points": [""]
}
Omit any field if not found in the document. Be precise — only include confirmed data.
""",
    "hotel_listing": """
Extract hotel information and return as valid JSON:
{
  "hotel_name": "",
  "chain": "",
  "star_rating": 0,
  "location_address": "",
  "location_description": "",
  "room_types": [{"type": "", "size_sqft": "", "max_occupancy": 0, "features": [""]}],
  "dining_outlets": [{"name": "", "cuisine": "", "meal_periods": [""]}],
  "amenities": [""],
  "check_in_time": "",
  "check_out_time": "",
  "family_friendly_features": [""],
  "concierge_services": [""]
}
""",
    "tour_guide": """
Extract tour/excursion information and return as valid JSON:
{
  "operator_name": "",
  "location": "",
  "tours": [{
    "name": "",
    "duration": "",
    "group_size_max": 0,
    "private_available": false,
    "price_per_person": "",
    "price_private": "",
    "booking_required": true,
    "min_age": "",
    "physical_level": "",
    "includes": [""],
    "highlights": [""]
  }]
}
""",
    "rail_schedule": """
Extract rail schedule information and return as valid JSON:
{
  "operator": "",
  "routes": [{
    "from": "",
    "to": "",
    "duration": "",
    "frequency": "",
    "classes": [{"class": "", "amenities": [""], "reservation_required": false}],
    "passes_accepted": [""],
    "group_booking_available": false,
    "advance_booking_recommended": ""
  }]
}
""",
    "generic": """
Provide a structured summary of this document:
{
  "document_type": "",
  "subject": "",
  "key_facts": [""],
  "dates_mentioned": [""],
  "prices_mentioned": [""],
  "action_items": [""],
  "summary": ""
}
""",
}


def _get_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set — check /home/john/Thunderbird/.env")
    return key


def _log_usage(operation: str, file_path: str, model: str, success: bool,
               tokens_est: int = 0, error: Optional[str] = None) -> None:
    try:
        _USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "file": str(file_path),
            "model": model,
            "tokens_est": tokens_est,
            "success": success,
            "error": error,
        }
        with open(_USAGE_LOG, "a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as exc:
        logger.warning("gemini_file_reader: usage log failed: %s", exc)


def upload_file(file_path: str, display_name: Optional[str] = None) -> str:
    """
    Upload a file to Google AI File API.
    Returns the file URI (e.g. "files/abc123") for use in subsequent prompts.
    File persists 48h on Google servers.
    """
    api_key = _get_api_key()
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    mime_type = "application/pdf" if path.suffix.lower() == ".pdf" else "text/plain"
    file_size = path.stat().st_size
    name = display_name or path.name

    logger.info("gemini_file_reader: uploading %s (%d bytes)", name, file_size)

    # Resumable upload — required for files > 5MB
    init_resp = requests.post(
        f"{_UPLOAD_BASE}?key={api_key}",
        headers={
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(file_size),
            "X-Goog-Upload-Header-Content-Type": mime_type,
            "Content-Type": "application/json",
        },
        json={"file": {"display_name": name}},
        timeout=30,
    )
    init_resp.raise_for_status()
    upload_url = init_resp.headers.get("X-Goog-Upload-URL")
    if not upload_url:
        raise RuntimeError("No upload URL in response headers")

    # Upload file bytes
    with open(path, "rb") as f:
        data = f.read()

    upload_resp = requests.post(
        upload_url,
        headers={
            "Content-Length": str(file_size),
            "X-Goog-Upload-Offset": "0",
            "X-Goog-Upload-Command": "upload, finalize",
        },
        data=data,
        timeout=120,
    )
    upload_resp.raise_for_status()
    file_info = upload_resp.json()
    file_uri = file_info.get("file", {}).get("uri", "")
    file_name = file_info.get("file", {}).get("name", "")

    if not file_uri:
        raise RuntimeError(f"Upload succeeded but no URI returned: {file_info}")

    # Poll until file is ACTIVE (processing can take 10-30s for large PDFs)
    for _ in range(30):
        state_resp = requests.get(
            f"{_API_BASE}/{file_name}?key={api_key}", timeout=15
        )
        state_resp.raise_for_status()
        state = state_resp.json().get("state", "")
        if state == "ACTIVE":
            logger.info("gemini_file_reader: file ACTIVE → %s", file_uri)
            _log_usage("upload", file_path, _DEFAULT_MODEL, True)
            return file_uri
        elif state == "FAILED":
            raise RuntimeError(f"File processing failed: {state_resp.json()}")
        time.sleep(2)

    raise RuntimeError(f"File never reached ACTIVE state after 60s: {file_uri}")


def ask_about_pdf(file_path: str, question: str,
                  model: str = _DEFAULT_MODEL, max_tokens: int = 4096) -> str:
    """
    Upload a PDF and ask any free-form question about it.
    Gemini reads the full document natively.

    Args:
        file_path: Local path to PDF file
        question:  Natural language question
        model:     Gemini model (default: gemini-2.5-pro for 1M context)
        max_tokens: Max response tokens

    Returns:
        Answer string from Gemini
    """
    api_key = _get_api_key()

    logger.info("gemini_file_reader: ask_about_pdf — %s", question[:60])
    t0 = time.time()

    file_uri = upload_file(file_path)

    payload = {
        "contents": [{
            "role": "user",
            "parts": [
                {"fileData": {"mimeType": "application/pdf", "fileUri": file_uri}},
                {"text": question},
            ],
        }],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.3},
    }

    resp = requests.post(
        f"{_API_BASE}/models/{model}:generateContent?key={api_key}",
        json=payload, timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = parts[0].get("text", "") if parts else ""

    elapsed = int((time.time() - t0) * 1000)
    tokens_est = len(text) // 4
    _log_usage("ask_about_pdf", file_path, model, bool(text), tokens_est)
    logger.info("gemini_file_reader: response in %dms, ~%d tokens", elapsed, tokens_est)

    if not text:
        raise RuntimeError(f"Empty response from {model}")
    return text


def extract_from_pdf(file_path: str, extract_type: str = "generic",
                     voyage_name: str = "", model: str = _DEFAULT_MODEL,
                     max_tokens: int = 8192) -> dict:
    """
    Upload a PDF and extract structured data based on document type.

    Args:
        file_path:    Local path to PDF
        extract_type: One of cruise_brochure | hotel_listing | tour_guide | rail_schedule | generic
        voyage_name:  Optional context hint (e.g. "Silver Muse Mediterranean Jun 2026")
        model:        Gemini model
        max_tokens:   Max response tokens

    Returns:
        Parsed dict of extracted data
    """
    if extract_type not in _EXTRACT_PROMPTS:
        extract_type = "generic"

    system_prompt = _EXTRACT_PROMPTS[extract_type]
    if voyage_name:
        system_prompt += f"\n\nDocument context: {voyage_name}"

    raw = ask_about_pdf(file_path, system_prompt, model=model, max_tokens=max_tokens)

    # Strip markdown code fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("gemini_file_reader: JSON parse failed, returning raw text")
        return {"raw_text": raw, "parse_error": True, "extract_type": extract_type}


def batch_extract(file_paths: list[str], extract_type: str = "generic",
                  delay_seconds: float = 4.0) -> list[dict]:
    """
    Extract from multiple PDFs sequentially.
    Respects Gemini free-tier 5 RPM for Pro model (4s delay between calls).
    """
    results = []
    for i, path in enumerate(file_paths):
        if i > 0:
            time.sleep(delay_seconds)
        try:
            result = extract_from_pdf(path, extract_type)
            result["_source_file"] = path
            result["_success"] = True
            results.append(result)
        except Exception as exc:
            logger.error("gemini_file_reader: failed on %s: %s", path, exc)
            results.append({"_source_file": path, "_success": False, "_error": str(exc)})
    return results


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    try:
        from dotenv import load_dotenv
        load_dotenv("/home/john/Thunderbird/.env")
    except ImportError:
        pass

    if len(sys.argv) < 2:
        print("Usage: python3 gemini_file_reader.py <pdf_path> [question]")
        sys.exit(1)

    pdf = sys.argv[1]
    question = sys.argv[2] if len(sys.argv) > 2 else "Summarize this document in 3 bullet points."

    print(f"[gemini_file_reader] Reading: {pdf}")
    print(f"[gemini_file_reader] Question: {question}\n")

    result = ask_about_pdf(pdf, question)
    print(result)
