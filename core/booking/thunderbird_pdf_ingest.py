"""
D2M PDF Ingest — Booking Confirmation Parser
Watches ~/Thunderbird/inbox/ for dropped PDFs.
Extracts booking details, sends structured Telegram alert to Commander.
Moves processed files to inbox/processed/.

Triggered by systemd path unit (d2m-pdf-watch.path).
Supports: Regent Seven Seas, Viking, Silversea, generic cruise confirmations.
"""
import re
import os
import sys
import json
import urllib.request
from pathlib import Path
from datetime import datetime

# Docling — preferred extractor (structured markdown output, better table/layout parsing)
try:
    from docling.document_converter import DocumentConverter as _DoclingConverter
    _DOCLING_CONVERTER = _DoclingConverter()
    DOCLING_OK = True
except Exception:
    DOCLING_OK = False
    _DOCLING_CONVERTER = None

# pdfminer — fallback if Docling unavailable
try:
    from pdfminer.high_level import extract_text as _pdfminer_extract
    PDFMINER_OK = True
except ImportError:
    PDFMINER_OK = False


def extract_text(pdf_path) -> str:
    """Extract text from a PDF. Tries Docling first, falls back to pdfminer."""
    path_str = str(pdf_path)
    if DOCLING_OK:
        try:
            result = _DOCLING_CONVERTER.convert(path_str)
            return result.document.export_to_markdown()
        except Exception as e:
            pass  # fall through to pdfminer
    if PDFMINER_OK:
        return _pdfminer_extract(path_str) or ""
    raise RuntimeError(
        "No PDF extractor available. Install docling or pdfminer.six:\n"
        "  pip install docling\n  pip install pdfminer.six"
    )

INBOX = Path(__file__).parent / "inbox"
PROCESSED = INBOX / "processed"
BOT_TOKEN = os.environ.get("TELEGRAM_C2_BOT_TOKEN", "***REMOVED-SECRET***")  # D2MC2C_bot — Commander C2 channel
COMMANDER_ID = os.environ.get("TELEGRAM_COMMANDER_ID", "7554895206")


# ── Extraction helpers ────────────────────────────────────────────────────────

def _find(pattern: str, text: str, flags=re.IGNORECASE) -> str:
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else ""


def detect_cruise_line(text: str) -> str:
    checks = [
        ("Regent", r"regent seven seas|rssc"),
        ("Viking", r"viking (cruises|ocean|river)"),
        ("Silversea", r"silversea"),
        ("Oceania", r"oceania cruises"),
        ("Seabourn", r"seabourn"),
        ("Cunard", r"cunard"),
        ("AmaWaterways", r"amawaterways"),
        ("Ponant", r"ponant"),
    ]
    tl = text.lower()
    for name, pat in checks:
        if re.search(pat, tl):
            return name
    return "Unknown"


def parse_regent(text: str) -> dict:
    return {
        "booking": _find(r"booking\s+(?:number|#|no\.?)[:\s]+([A-Z0-9]+)", text)
                   or _find(r"confirmation[:\s]+([0-9]{6,})", text),
        "guests": _find(r"guest(?:s)?[:\s]+(.+?)(?:\n|cabin)", text),
        "ship": _find(r"ship[:\s]+(.+?)(?:\n|voyage)", text)
               or _find(r"M\.?V\.?\s+(.+?)(?:\n|voyage)", text),
        "sail_date": _find(r"(?:sail|embark|departure)\s+date[:\s]+([A-Za-z0-9 ,/\-]+)", text),
        "return_date": _find(r"(?:disembark|return|arrival)\s+date[:\s]+([A-Za-z0-9 ,/\-]+)", text),
        "suite": _find(r"(?:suite|stateroom|cabin)[:\s]+([A-Z0-9\- ]+)", text),
        "total": _find(r"(?:total|grand total|invoice total)[:\s]+\$?([\d,]+\.?\d*)", text),
        "deposit": _find(r"deposit[:\s]+\$?([\d,]+\.?\d*)", text),
        "balance": _find(r"(?:balance due|amount due)[:\s]+\$?([\d,]+\.?\d*)", text),
        "fpd": _find(r"(?:final payment|balance due) (?:date|by|on)[:\s]+([A-Za-z0-9 ,/\-]+)", text),
        "voyage": _find(r"voyage[:\s]+(.+?)(?:\n|ship)", text),
    }


def parse_viking(text: str) -> dict:
    return {
        "booking": _find(r"(?:booking|reservation)\s+(?:number|#|no\.?)[:\s]+([A-Z0-9]+)", text),
        "guests": _find(r"passenger(?:s)?[:\s]+(.+?)(?:\n|stateroom)", text),
        "ship": _find(r"(?:ship|vessel)[:\s]+(.+?)(?:\n|voyage)", text)
               or _find(r"Viking\s+([A-Za-z]+)\b", text),
        "sail_date": _find(r"(?:sail|depart(?:ure)?)\s+date[:\s]+([A-Za-z0-9 ,/\-]+)", text),
        "return_date": _find(r"(?:return|arrival)\s+date[:\s]+([A-Za-z0-9 ,/\-]+)", text),
        "suite": _find(r"(?:stateroom|cabin|suite)[:\s]+([A-Z0-9\- ]+)", text),
        "total": _find(r"(?:total fare|grand total)[:\s]+\$?([\d,]+\.?\d*)", text),
        "deposit": _find(r"deposit[:\s]+\$?([\d,]+\.?\d*)", text),
        "balance": _find(r"(?:balance|amount due)[:\s]+\$?([\d,]+\.?\d*)", text),
        "fpd": _find(r"(?:final payment|balance due) (?:date|due|by)[:\s]+([A-Za-z0-9 ,/\-]+)", text),
        "voyage": _find(r"voyage[:\s]+(.+?)(?:\n|ship)", text),
    }


def parse_generic(text: str) -> dict:
    return {
        "booking": _find(r"(?:booking|confirmation|reservation)\s*(?:number|#|no\.?)[:\s]+([A-Z0-9]+)", text),
        "guests": _find(r"(?:guest|passenger|traveler)(?:s)?[:\s]+(.+?)(?:\n)", text),
        "ship": _find(r"(?:ship|vessel|m\.?v\.?)[:\s]+(.+?)(?:\n)", text),
        "sail_date": _find(r"(?:sail|embark|depart(?:ure)?)\s*date[:\s]+([A-Za-z0-9 ,/\-]+)", text),
        "return_date": _find(r"(?:return|disembark|arrival)\s*date[:\s]+([A-Za-z0-9 ,/\-]+)", text),
        "suite": _find(r"(?:suite|stateroom|cabin|room)[:\s]+([A-Z0-9\- ]+)", text),
        "total": _find(r"(?:total|grand total)[:\s]+\$?([\d,]+\.?\d*)", text),
        "deposit": _find(r"deposit[:\s]+\$?([\d,]+\.?\d*)", text),
        "balance": _find(r"(?:balance|amount due)[:\s]+\$?([\d,]+\.?\d*)", text),
        "fpd": _find(r"(?:final payment|balance due)[\s\w]*date[:\s]+([A-Za-z0-9 ,/\-]+)", text),
        "voyage": _find(r"(?:voyage|itinerary|cruise)[:\s]+(.+?)(?:\n)", text),
    }


def extract_fields(text: str) -> tuple[str, dict]:
    line = detect_cruise_line(text)
    if line == "Regent":
        fields = parse_regent(text)
    elif line == "Viking":
        fields = parse_viking(text)
    else:
        fields = parse_generic(text)
    return line, fields


# ── Telegram ─────────────────────────────────────────────────────────────────

_MUTE_FLAG = Path("/home/john/Thunderbird/config/d2mc2c_client_mute")

def send_telegram(msg: str):
    if _MUTE_FLAG.exists():
        return  # client/supplier push muted — SO 2026-05-05
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = json.dumps({
        "chat_id": COMMANDER_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }).encode()
    req = urllib.request.Request(url, data=data,
                                  headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=15)


def build_message(filename: str, line: str, fields: dict) -> str:
    def row(label, val):
        return f"  *{label}:* {val}" if val else ""

    rows = [
        row("Cruise Line", line),
        row("Booking #", fields.get("booking")),
        row("Guests", fields.get("guests")),
        row("Ship", fields.get("ship")),
        row("Voyage", fields.get("voyage")),
        row("Sail Date", fields.get("sail_date")),
        row("Return", fields.get("return_date")),
        row("Suite/Cabin", fields.get("suite")),
        row("Total", f"${fields.get('total')}" if fields.get("total") else ""),
        row("Deposit", f"${fields.get('deposit')}" if fields.get("deposit") else ""),
        row("Balance Due", f"${fields.get('balance')}" if fields.get("balance") else ""),
        row("FPD", fields.get("fpd")),
    ]
    body = "\n".join(r for r in rows if r)
    blanks = sum(1 for v in fields.values() if not v)
    confidence = "🟢 HIGH" if blanks <= 3 else ("🟡 MEDIUM" if blanks <= 6 else "🔴 LOW")

    return (
        f"*📄 PDF BOOKING CONFIRMATION*\n"
        f"_File: {filename}_\n\n"
        f"{body}\n\n"
        f"Confidence: {confidence} ({12 - blanks}/12 fields)\n"
        f"_Review and run /dossier to create dossier_"
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def process_pdf(pdf_path: Path):
    if not PDFMINER_OK:
        send_telegram(f"⚠️ PDF dropped but pdfminer not installed: `{pdf_path.name}`\n"
                      f"Run: `pip3 install pdfminer.six`")
        return

    try:
        text = extract_text(str(pdf_path))
    except Exception as e:
        send_telegram(f"⚠️ PDF parse error: `{pdf_path.name}`\n`{e}`")
        return

    if not text or len(text.strip()) < 100:
        send_telegram(f"⚠️ PDF appears empty or image-only: `{pdf_path.name}`\n"
                      f"_Manual entry required_")
        move_processed(pdf_path)
        return

    line, fields = extract_fields(text)
    msg = build_message(pdf_path.name, line, fields)
    send_telegram(msg)
    print(f"[pdf-ingest] Processed {pdf_path.name} → {line}, "
          f"booking={fields.get('booking', '?')}")
    move_processed(pdf_path)


def move_processed(pdf_path: Path):
    PROCESSED.mkdir(exist_ok=True)
    dest = PROCESSED / pdf_path.name
    if dest.exists():
        ts = datetime.now().strftime("%H%M%S")
        dest = PROCESSED / f"{pdf_path.stem}_{ts}{pdf_path.suffix}"
    pdf_path.rename(dest)
    print(f"[pdf-ingest] Moved → {dest}")


def main():
    INBOX.mkdir(exist_ok=True)
    pdfs = list(INBOX.glob("*.pdf")) + list(INBOX.glob("*.PDF"))
    if not pdfs:
        print("[pdf-ingest] No PDFs in inbox.")
        return
    for pdf in pdfs:
        process_pdf(pdf)


if __name__ == "__main__":
    main()
