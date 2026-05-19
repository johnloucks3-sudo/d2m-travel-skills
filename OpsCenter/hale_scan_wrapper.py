"""
Hale Scan Wrapper — Universal Synthesis Injector
==================================================
Wraps ANY scan output with Hale's VCSAF synthesis before delivery.
Raw data is preserved below the synthesis block.

Usage:
    # Pipe mode
    python3 hale_scan_wrapper.py --type innovation < raw_output.txt

    # File mode
    python3 hale_scan_wrapper.py --type tech --file /path/to/output.txt

    # Send to Telegram after synthesis
    python3 hale_scan_wrapper.py --type intel --file output.txt --send

    # Called from another script
    from hale_scan_wrapper import wrap_and_send
    wrap_and_send(raw_text, scan_type="innovation", send_telegram=True)

Scan types: intel | innovation | tech | booking | commission | general

Output format (Telegram):
    ── HALE SYNTHESIS ──────────────────────
    [Hale's VCSAF take — what matters, action items]
    ─────────────────────────────────────────
    RAW DATA ↓
    [Full original scan output]

Author: Victoria "Victory" Hale, SES-6 — 2026-04-03 (re-roled 2026-05-17)
"""

import argparse
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(str(_ROOT / ".env"))
load_dotenv(str(_ROOT / ".env.telegram"))

MT = timezone(timedelta(hours=-6))

TELEGRAM_BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID    = os.getenv("TELEGRAM_COMMANDER_ID", os.getenv("TELEGRAM_CHAT_ID", ""))

DIVIDER_TOP = "\u2500" * 38
DIVIDER_MID = "\u2500" * 38


def _send_telegram(text: str):
    """Send message to Commander via Telegram. Splits if over 4096 chars."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[hale_scan_wrapper] Telegram not configured — printing to stdout.")
        print(text)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    chunk_size = 4000

    # Split on paragraph boundaries if possible
    chunks = []
    while text:
        if len(text) <= chunk_size:
            chunks.append(text)
            break
        split_at = text.rfind("\n\n", 0, chunk_size)
        if split_at == -1:
            split_at = text.rfind("\n", 0, chunk_size)
        if split_at == -1:
            split_at = chunk_size
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()

    for i, chunk in enumerate(chunks):
        try:
            resp = requests.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": chunk,
                "parse_mode": "Markdown",
            }, timeout=15)
            if not resp.ok:
                # Retry without Markdown if parse fails
                resp = requests.post(url, json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": chunk,
                }, timeout=15)
        except Exception as e:
            print(f"[hale_scan_wrapper] Telegram send failed: {e}", file=sys.stderr)


def wrap_and_send(raw_output: str, scan_type: str = "general",
                  send_telegram: bool = False, label: str = None) -> str:
    """
    Main entry point. Returns the formatted combined output.
    Optionally sends to Telegram.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from hale_dispatcher import HaleDispatcher

    ts = datetime.now(MT).strftime("%Y-%m-%d %H:%M MT")
    scan_label = label or scan_type.upper()

    print(f"[hale_scan_wrapper] Synthesizing {scan_label} scan at {ts}...")
    hale = HaleDispatcher()
    synthesis = hale.synthesize(raw_output, scan_type=scan_type)

    # Build combined output
    combined = f"""{DIVIDER_TOP}
*HALE* | {scan_label} | {ts}
{DIVIDER_TOP}

{synthesis}

{DIVIDER_MID}
*RAW DATA* \u2193
{DIVIDER_MID}

{raw_output}"""

    if send_telegram:
        _send_telegram(combined)
        print(f"[hale_scan_wrapper] Sent to Telegram ({len(combined):,} chars).")
    else:
        print(combined)

    return combined


def main():
    parser = argparse.ArgumentParser(description="Hale scan synthesis wrapper")
    parser.add_argument("--type",  default="general",
                        choices=["intel","innovation","tech","booking","commission","general"],
                        help="Scan type — determines synthesis focus")
    parser.add_argument("--file",  default=None, help="Input file path (default: stdin)")
    parser.add_argument("--send",  action="store_true", help="Send result to Telegram")
    parser.add_argument("--label", default=None, help="Display label override")
    args = parser.parse_args()

    # Read input
    if args.file:
        raw = Path(args.file).read_text(encoding="utf-8", errors="replace")
    else:
        raw = sys.stdin.read()

    if not raw.strip():
        print("[hale_scan_wrapper] No input. Exiting.")
        sys.exit(0)

    wrap_and_send(raw, scan_type=args.type, send_telegram=args.send, label=args.label)


if __name__ == "__main__":
    main()
