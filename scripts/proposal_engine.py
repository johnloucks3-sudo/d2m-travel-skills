#!/usr/bin/env python3
"""
Proposal Engine — parameterized voyage proposal email builder.
Replaces bespoke draft scripts with a single parameterized pipeline.

Usage:
  python3 scripts/proposal_engine.py \
    --client "Kyle Kuklinski" \
    --cruise-line "Viking" \
    --ship "Viking Mars" \
    --departure "2026-12-17" \
    --destination "Panama Canal" \
    --nights 14 \
    --cabin-category "Deluxe Veranda" \
    --price-pp 4999 \
    --currency USD \
    --subject "Your Viking Panama Canal Voyage Proposal" \
    [--output drafts/proposal_kuklinski.html] \
    [--dry-run] \
    [--self-test]

WF-17 gate holds — staged to johnloucks3 only, never sent to clients.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

THUNDERBIRD = Path(__file__).parent.parent
DRAFTS_DIR = THUNDERBIRD / "drafts"
STATE_FILE = THUNDERBIRD / "OpsCenter" / "state" / "proposal_engine_state.json"

SELF_TEST_ARGS = {
    "client": "Test Client",
    "cruise_line": "Silversea",
    "ship": "Silver Nova",
    "departure": "2027-05-05",
    "destination": "World Cruise",
    "nights": 32,
    "cabin_category": "Vista Suite",
    "price_pp": 19900,
    "currency": "USD",
    "subject": "CI Self-Test Proposal",
    "output": Path("/tmp/proposal_engine_selftest.html"),
}


def build_proposal_body(
    client_name: str,
    cruise_line: str,
    ship: str,
    departure: str,
    destination: str,
    nights: int,
    cabin_category: str,
    price_pp: float,
    currency: str,
) -> str:
    return f"""
<h2 style="color:#4a90d9;font-family:Georgia,serif;font-size:22px;margin-bottom:8px;">Your {destination} Voyage Proposal</h2>
<p style="color:#a8c4f0;font-family:Georgia,serif;font-size:13px;margin-top:0;">{cruise_line} · {ship} · Departing {departure}</p>
<hr style="border:1px solid #1a3a6b;margin:20px 0;">

<table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
  <tr>
    <td style="color:#a8c4f0;font-family:Georgia,serif;font-size:13px;padding:8px 0;width:40%;">Cruise Line</td>
    <td style="color:#e8f1ff;font-family:Georgia,serif;font-size:14px;padding:8px 0;">{cruise_line}</td>
  </tr>
  <tr>
    <td style="color:#a8c4f0;font-family:Georgia,serif;font-size:13px;padding:8px 0;">Ship</td>
    <td style="color:#e8f1ff;font-family:Georgia,serif;font-size:14px;padding:8px 0;">{ship}</td>
  </tr>
  <tr>
    <td style="color:#a8c4f0;font-family:Georgia,serif;font-size:13px;padding:8px 0;">Departure</td>
    <td style="color:#e8f1ff;font-family:Georgia,serif;font-size:14px;padding:8px 0;">{departure}</td>
  </tr>
  <tr>
    <td style="color:#a8c4f0;font-family:Georgia,serif;font-size:13px;padding:8px 0;">Duration</td>
    <td style="color:#e8f1ff;font-family:Georgia,serif;font-size:14px;padding:8px 0;">{nights} nights</td>
  </tr>
  <tr>
    <td style="color:#a8c4f0;font-family:Georgia,serif;font-size:13px;padding:8px 0;">Cabin Category</td>
    <td style="color:#e8f1ff;font-family:Georgia,serif;font-size:14px;padding:8px 0;">{cabin_category}</td>
  </tr>
  <tr style="background:#0d1f3c;">
    <td style="color:#4a90d9;font-family:Georgia,serif;font-size:14px;padding:10px 8px;font-weight:bold;">Investment</td>
    <td style="color:#4a90d9;font-family:Georgia,serif;font-size:18px;padding:10px 8px;font-weight:bold;">{currency} {price_pp:,.0f} per person</td>
  </tr>
</table>

<p style="color:#e8f1ff;font-family:Georgia,serif;font-size:14px;">This proposal is prepared exclusively for {client_name} and is subject to availability. Pricing may vary — contact us to confirm and hold your cabin.</p>
<p style="color:#a8c4f0;font-family:Georgia,serif;font-size:13px;font-style:italic;">Prepared by Dreams2Memories Travel, LLC · John A. Loucks III · 719-291-0742</p>
"""


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"last_run": None, "total_proposals": 0, "proposals": {}}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def run_proposal(
    client: str,
    cruise_line: str,
    ship: str,
    departure: str,
    destination: str,
    nights: int,
    cabin_category: str,
    price_pp: float,
    currency: str,
    subject: str,
    output: Path,
    dry_run: bool = False,
) -> bool:
    # Import here so the module is usable standalone
    sys.path.insert(0, str(THUNDERBIRD / "scripts"))
    from d2m_email_builder import build_email_html, stage_draft

    body_html = build_proposal_body(
        client_name=client,
        cruise_line=cruise_line,
        ship=ship,
        departure=departure,
        destination=destination,
        nights=nights,
        cabin_category=cabin_category,
        price_pp=price_pp,
        currency=currency,
    )

    full_html = build_email_html(body_html)

    if dry_run:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(full_html, encoding="utf-8")
        print(f"[DRY RUN] Proposal HTML written ({len(full_html)} chars) → {output}")
        print("[DRY RUN] No draft staged to johnloucks3.")
        _update_state(client, departure, ship, subject, output, staged=False)
        return True

    output.parent.mkdir(parents=True, exist_ok=True)
    success = stage_draft(full_html, "johnloucks3@gmail.com", subject, output)
    _update_state(client, departure, ship, subject, output, staged=success)
    return success


def _update_state(client, departure, ship, subject, output, staged):
    state = load_state()
    key = f"{client}|{departure}|{ship}"
    state["proposals"][key] = {
        "staged_at": datetime.now(timezone.utc).isoformat(),
        "subject": subject,
        "output_path": str(output),
        "staged_to_johnloucks3": staged,
    }
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    state["total_proposals"] = len(state["proposals"])
    save_state(state)


def main():
    parser = argparse.ArgumentParser(description="D2M Proposal Engine")
    parser.add_argument("--client", help="Client full name")
    parser.add_argument("--cruise-line", dest="cruise_line", help="Cruise line name")
    parser.add_argument("--ship", help="Ship name")
    parser.add_argument("--departure", help="Departure date (YYYY-MM-DD)")
    parser.add_argument("--destination", help="Destination / voyage name")
    parser.add_argument("--nights", type=int, help="Voyage duration in nights")
    parser.add_argument("--cabin-category", dest="cabin_category", help="Cabin category")
    parser.add_argument("--price-pp", dest="price_pp", type=float, help="Price per person")
    parser.add_argument("--currency", default="USD", help="Currency code (default: USD)")
    parser.add_argument("--subject", help="Email subject line")
    parser.add_argument("--output", help="Output HTML file path")
    parser.add_argument("--dry-run", action="store_true", help="Build HTML only, do not stage draft")
    parser.add_argument("--self-test", action="store_true", help="CI self-test with hardcoded values")
    args = parser.parse_args()

    if args.self_test:
        st = SELF_TEST_ARGS
        success = run_proposal(
            client=st["client"],
            cruise_line=st["cruise_line"],
            ship=st["ship"],
            departure=st["departure"],
            destination=st["destination"],
            nights=st["nights"],
            cabin_category=st["cabin_category"],
            price_pp=st["price_pp"],
            currency=st["currency"],
            subject=st["subject"],
            output=st["output"],
            dry_run=True,
        )
        if success:
            print("Self-test PASSED")
            sys.exit(0)
        else:
            print("Self-test FAILED")
            sys.exit(1)

    # Normal mode — validate required args
    required = ["client", "cruise_line", "ship", "departure", "destination",
                "nights", "cabin_category", "price_pp", "subject"]
    missing = [f for f in required if not getattr(args, f, None)]
    if missing:
        print(f"ERROR: Missing required arguments: {', '.join(missing)}")
        parser.print_help()
        sys.exit(1)

    if args.output:
        output = Path(args.output)
    else:
        ts = int(time.time())
        safe_client = args.client.replace(" ", "_").lower()
        output = DRAFTS_DIR / f"proposal_{safe_client}_{ts}.html"

    success = run_proposal(
        client=args.client,
        cruise_line=args.cruise_line,
        ship=args.ship,
        departure=args.departure,
        destination=args.destination,
        nights=args.nights,
        cabin_category=args.cabin_category,
        price_pp=args.price_pp,
        currency=args.currency,
        subject=args.subject,
        output=output,
        dry_run=args.dry_run,
    )

    if success:
        print(f"\nProposal staged to johnloucks3. Review in Gmail drafts before sending.")
        print(f"Output: {output}")
        sys.exit(0)
    else:
        print("ERROR: Draft staging failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
