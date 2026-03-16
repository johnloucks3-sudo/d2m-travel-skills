"""
Thunderbird Commission Reconciliation Automation
==================================================
Dreams2Memories Travel, LLC — Item #6

Matches expected commissions from Booking Master against supplier payment
emails in Gmail. Uses Groq (fast) for extracting payment amounts from
unstructured email text.

Pipeline: Sheets read → Gmail search → Groq parse → reconcile → report → email

Usage:
    from thunderbird_commission_recon import run_reconciliation, get_expected_commissions

    # Full pipeline
    results = run_reconciliation(days_back=90)

    # Just read expected commissions
    expected = get_expected_commissions()

CLI:
    python3 thunderbird_commission_recon.py                  # Full recon, 90 days
    python3 thunderbird_commission_recon.py --days 60        # Custom lookback
    python3 thunderbird_commission_recon.py --dry-run        # No email, just print report
    python3 thunderbird_commission_recon.py --expected-only  # Just dump expected commissions

Dependencies: gspread, google-api-python-client, google-auth, requests
"""

import json
import logging
import re
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

import gspread
from google.oauth2 import service_account as sa_credentials
from mcp.server.fastmcp import FastMCP
from pydantic import Field

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
CREDENTIALS_FILE = THUNDERBIRD_DIR / "credentials.json"
LOG_DIR = THUNDERBIRD_DIR / "logs"
LOG_FILE = LOG_DIR / "commission_recon.log"

SPREADSHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
BOOKING_MASTER_TAB = "Booking Master"

SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# Gmail search terms for commission/payment emails
PAYMENT_SEARCH_QUERIES = [
    "commission payment",
    "remittance advice",
    "agent payment",
    "commission statement",
    "agent commission",
    "payment confirmation commission",
]

# Fuzzy match tolerance: payments within this % of expected are considered "matched"
MATCH_TOLERANCE_PCT = 5.0  # 5%

# Groq extraction prompt
EXTRACTION_SYSTEM_PROMPT = """\
You are a financial data extraction specialist for a luxury travel agency.
Extract payment details from supplier commission emails.

Return ONLY a valid JSON object with these fields:
{
  "supplier_name": "string — the supplier or cruise line name",
  "amount_paid": float — the payment amount (numeric, no currency symbols),
  "currency": "USD" or "EUR" or other ISO code,
  "booking_reference": "string — booking/confirmation number if mentioned, else null",
  "payment_date": "YYYY-MM-DD if found, else null",
  "notes": "any relevant context about the payment"
}

If you cannot extract a field, set it to null. Always return valid JSON.
Do NOT wrap in markdown code blocks. Return the raw JSON object only."""

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# GOOGLE SHEETS — Read Expected Commissions
# ---------------------------------------------------------------------------

def _get_sheets_client():
    """Return an authorized gspread client using the service account."""
    creds = sa_credentials.Credentials.from_service_account_file(
        str(CREDENTIALS_FILE),
        scopes=SHEETS_SCOPES,
    )
    return gspread.authorize(creds)


def get_expected_commissions() -> list[dict]:
    """Read Booking Master sheet and extract expected commission data.

    For each booking row, extracts:
        booking_id, client_name, supplier, expected_commission,
        booking_date, status, client_price, net_cost

    Skips rows without a client name or supplier.
    """
    gc = _get_sheets_client()
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    ws = spreadsheet.worksheet(BOOKING_MASTER_TAB)

    records = ws.get_all_records()
    logger.info(f"Read {len(records)} rows from '{BOOKING_MASTER_TAB}'")

    commissions = []
    for row in records:
        client = str(row.get("Client_Name", "")).strip()
        supplier = str(row.get("Supplier", "")).strip()
        if not client or not supplier:
            continue

        # Extract financial fields — handle various column name possibilities
        booking_id = str(
            row.get("Confirmation_Number", "")
            or row.get("Booking_ID", "")
            or row.get("Booking_Id", "")
        ).strip()

        # Commission can be in several columns depending on how the sheet evolved
        expected_commission = _parse_currency(
            row.get("Commission", "")
            or row.get("Expected_Commission", "")
            or row.get("Agent_Commission", "")
        )

        client_price = _parse_currency(
            row.get("Client_Price", "")
            or row.get("Total_Price", "")
            or row.get("Total_Cost", "")
        )

        net_cost = _parse_currency(
            row.get("Net_Cost", "")
            or row.get("Supplier_Cost", "")
            or row.get("Net_Rate", "")
        )

        # If commission isn't explicit but we have client_price and net_cost, compute it
        if expected_commission == 0.0 and client_price > 0 and net_cost > 0:
            expected_commission = round(client_price - net_cost, 2)

        booking_date = str(
            row.get("Booking_Date", "")
            or row.get("Start_Date", "")
        ).strip()

        status = str(
            row.get("Status", "")
            or row.get("Booking_Status", "")
            or "active"
        ).strip()

        commissions.append({
            "booking_id": booking_id,
            "client_name": client,
            "supplier": supplier,
            "expected_commission": expected_commission,
            "client_price": client_price,
            "net_cost": net_cost,
            "booking_date": booking_date,
            "status": status,
        })

    logger.info(f"Extracted {len(commissions)} bookings with commission data")
    return commissions


def _parse_currency(value) -> float:
    """Parse a currency value from various spreadsheet formats.

    Handles: $1,234.56, 1234.56, "1,234", €800, empty strings, etc.
    """
    if value is None:
        return 0.0
    s = str(value).strip()
    if not s or s in ("", "N/A", "TBD", "Pending", "#NUM!", "-"):
        return 0.0
    # Strip currency symbols and commas
    s = re.sub(r'[€$£,]', '', s)
    try:
        return round(float(s), 2)
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# GMAIL — Search for Payment Emails
# ---------------------------------------------------------------------------

def search_payment_emails(days_back: int = 90) -> list[dict]:
    """Search Gmail for commission/payment emails from suppliers.

    Uses the OAuth-based Gmail service from thunderbird_gmail.py.
    Searches multiple payment-related terms within the lookback window.

    Returns list of dicts with: message_id, sender, date, subject, snippet, body.
    """
    from thunderbird_gmail import _get_gmail_service, _decode_body, _extract_headers

    service = _get_gmail_service()
    cutoff = (datetime.now() - timedelta(days=days_back)).strftime("%Y/%m/%d")

    seen_ids = set()
    results = []

    for query_term in PAYMENT_SEARCH_QUERIES:
        full_query = f"({query_term}) after:{cutoff}"
        try:
            response = (
                service.users()
                .messages()
                .list(userId="me", q=full_query, maxResults=25)
                .execute()
            )

            for msg_ref in response.get("messages", []):
                msg_id = msg_ref["id"]
                if msg_id in seen_ids:
                    continue
                seen_ids.add(msg_id)

                # Fetch full message for body extraction
                msg = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg_id, format="full")
                    .execute()
                )
                payload = msg.get("payload", {})
                headers = _extract_headers(
                    payload.get("headers", []),
                    keys={"From", "To", "Subject", "Date"}
                )
                body = _decode_body(payload)

                # Truncate very long bodies for LLM processing
                if len(body) > 15000:
                    body = body[:15000] + "\n... [TRUNCATED]"

                results.append({
                    "message_id": msg_id,
                    "sender": headers.get("From", ""),
                    "date": headers.get("Date", ""),
                    "subject": headers.get("Subject", ""),
                    "snippet": msg.get("snippet", ""),
                    "body": body,
                })

        except Exception as e:
            logger.warning(f"Gmail search failed for '{query_term}': {e}")
            continue

    logger.info(
        f"Found {len(results)} payment-related emails "
        f"(searched {len(PAYMENT_SEARCH_QUERIES)} queries, {days_back} days back)"
    )
    return results


# ---------------------------------------------------------------------------
# GROQ — Parse Payment Amounts from Email Text
# ---------------------------------------------------------------------------

def parse_payment_amount(email_text: str) -> dict:
    """Use Groq (fast model) to extract structured payment data from email text.

    Returns dict with: supplier_name, amount_paid, currency, booking_reference,
                       payment_date, notes
    On failure, returns dict with error field.
    """
    from thunderbird_model_router import _call_groq

    # Combine subject + body for context
    prompt = (
        "Extract the commission payment details from this email:\n\n"
        f"{email_text[:6000]}"
    )

    try:
        raw = _call_groq(
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            query=prompt,
            model="fast",
            max_tokens=400,
            temperature=0.1,
        )

        # Clean up response — strip markdown fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)

        parsed = json.loads(cleaned)

        # Normalize amount_paid to float
        if parsed.get("amount_paid") is not None:
            parsed["amount_paid"] = _parse_currency(parsed["amount_paid"])

        return parsed

    except json.JSONDecodeError as e:
        logger.warning(f"Groq returned invalid JSON: {e}\nRaw: {raw[:200]}")
        return {"error": f"JSON parse failed: {e}", "raw_response": raw[:500]}
    except Exception as e:
        logger.error(f"Groq extraction failed: {e}")
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# RECONCILIATION ENGINE
# ---------------------------------------------------------------------------

def reconcile(expected: list[dict], received: list[dict]) -> dict:
    """Match received payments against expected commissions.

    Matching strategy:
      1. Exact match by booking_id / booking_reference
      2. Fuzzy match by supplier_name + approximate amount (within tolerance)

    Categories:
      - matched: payment matches an expected commission
      - underpaid: payment received but less than expected (with delta)
      - overpaid: payment received but more than expected
      - missing: expected commission with no matching payment
      - unmatched: payment received but can't match to any booking

    Returns dict with categorized results and totals.
    """
    matched = []
    underpaid = []
    overpaid = []
    missing = []
    unmatched = []

    # Index expected by booking_id for fast lookup
    expected_by_id = {}
    for exp in expected:
        bid = exp.get("booking_id", "").strip()
        if bid:
            expected_by_id[bid] = exp

    # Track which expected entries have been matched
    matched_expected_ids = set()
    matched_received_indices = set()

    # Pass 1: Match by booking_id / booking_reference
    for i, recv in enumerate(received):
        ref = str(recv.get("booking_reference", "") or "").strip()
        if ref and ref in expected_by_id:
            exp = expected_by_id[ref]
            _categorize_match(exp, recv, matched, underpaid, overpaid)
            matched_expected_ids.add(ref)
            matched_received_indices.add(i)

    # Pass 2: Fuzzy match by supplier + amount for unmatched payments
    for i, recv in enumerate(received):
        if i in matched_received_indices:
            continue

        recv_supplier = str(recv.get("supplier_name", "") or "").lower()
        recv_amount = recv.get("amount_paid", 0.0) or 0.0

        if not recv_supplier or recv_amount <= 0:
            unmatched.append(recv)
            matched_received_indices.add(i)
            continue

        best_match = None
        best_delta = float("inf")

        for exp in expected:
            bid = exp.get("booking_id", "").strip()
            if bid in matched_expected_ids:
                continue

            exp_supplier = exp.get("supplier", "").lower()
            exp_commission = exp.get("expected_commission", 0.0)

            # Check supplier name similarity (substring match)
            if not (recv_supplier in exp_supplier or exp_supplier in recv_supplier):
                continue

            if exp_commission <= 0:
                continue

            delta = abs(recv_amount - exp_commission)
            tolerance = exp_commission * (MATCH_TOLERANCE_PCT / 100.0)

            if delta < best_delta:
                best_delta = delta
                best_match = exp

        if best_match is not None and best_delta <= best_match["expected_commission"] * 0.50:
            # Within 50% — categorize as match/underpaid/overpaid
            bid = best_match.get("booking_id", "")
            _categorize_match(best_match, recv, matched, underpaid, overpaid)
            matched_expected_ids.add(bid)
            matched_received_indices.add(i)
        else:
            unmatched.append(recv)
            matched_received_indices.add(i)

    # Pass 3: Expected commissions with no payment at all
    for exp in expected:
        bid = exp.get("booking_id", "").strip()
        if bid not in matched_expected_ids and exp.get("expected_commission", 0) > 0:
            status = exp.get("status", "").lower()
            # Only flag active/confirmed bookings as missing
            if status not in ("cancelled", "canceled", "refunded"):
                missing.append(exp)

    # Calculate totals
    total_expected = sum(e.get("expected_commission", 0) for e in expected if e.get("expected_commission", 0) > 0)
    total_received = sum(
        r.get("amount_paid", 0) or 0
        for r in received
        if r.get("amount_paid")
    )
    total_matched = sum(m.get("amount_paid", 0) for m in matched)
    total_missing = sum(m.get("expected_commission", 0) for m in missing)
    total_underpaid_gap = sum(u.get("delta", 0) for u in underpaid)

    return {
        "matched": matched,
        "underpaid": underpaid,
        "overpaid": overpaid,
        "missing": missing,
        "unmatched": unmatched,
        "totals": {
            "total_expected": round(total_expected, 2),
            "total_received": round(total_received, 2),
            "total_matched": round(total_matched, 2),
            "total_missing": round(total_missing, 2),
            "total_underpaid_gap": round(total_underpaid_gap, 2),
            "total_gap": round(total_expected - total_received, 2),
            "match_rate_pct": round(
                (len(matched) / max(len(expected), 1)) * 100, 1
            ),
        },
        "counts": {
            "expected": len(expected),
            "received": len(received),
            "matched": len(matched),
            "underpaid": len(underpaid),
            "overpaid": len(overpaid),
            "missing": len(missing),
            "unmatched": len(unmatched),
        },
    }


def _categorize_match(exp: dict, recv: dict, matched: list, underpaid: list, overpaid: list):
    """Compare expected vs received amounts and place into the right category."""
    exp_amount = exp.get("expected_commission", 0.0)
    recv_amount = recv.get("amount_paid", 0.0) or 0.0
    delta = round(recv_amount - exp_amount, 2)
    tolerance = exp_amount * (MATCH_TOLERANCE_PCT / 100.0)

    entry = {
        "booking_id": exp.get("booking_id", ""),
        "client_name": exp.get("client_name", ""),
        "supplier": exp.get("supplier", ""),
        "expected_commission": exp_amount,
        "amount_paid": recv_amount,
        "delta": delta,
        "payment_date": recv.get("payment_date", ""),
        "booking_reference": recv.get("booking_reference", ""),
    }

    if abs(delta) <= tolerance:
        matched.append(entry)
    elif delta < 0:
        underpaid.append(entry)
    else:
        overpaid.append(entry)


# ---------------------------------------------------------------------------
# REPORT GENERATION
# ---------------------------------------------------------------------------

def _fmt_usd(amount: float) -> str:
    """Format amount as USD string."""
    if amount < 0:
        return f"-${abs(amount):,.2f}"
    return f"${amount:,.2f}"


def generate_recon_report(results: dict) -> str:
    """Generate a formatted commission reconciliation report.

    Sections:
      - Summary: total expected vs received, gap amount
      - Matched payments (green)
      - Underpayments with delta (yellow)
      - Missing payments — expected but not received (red)
      - Unmatched payments — received but can't match to booking (blue)
      - Action items
    """
    t = results["totals"]
    c = results["counts"]
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = []
    lines.append("=" * 70)
    lines.append("  COMMISSION RECONCILIATION REPORT")
    lines.append(f"  Dreams2Memories Travel, LLC — {ts}")
    lines.append("=" * 70)
    lines.append("")

    # ── SUMMARY ──
    lines.append("--- SUMMARY ---")
    lines.append(f"  Total Expected Commissions:  {_fmt_usd(t['total_expected'])}")
    lines.append(f"  Total Received Payments:     {_fmt_usd(t['total_received'])}")
    lines.append(f"  Total Gap:                   {_fmt_usd(t['total_gap'])}")
    lines.append(f"  Match Rate:                  {t['match_rate_pct']}%")
    lines.append("")
    lines.append(f"  Bookings with commissions:   {c['expected']}")
    lines.append(f"  Payment emails found:        {c['received']}")
    lines.append(f"  Matched:                     {c['matched']}")
    lines.append(f"  Underpaid:                   {c['underpaid']}")
    lines.append(f"  Overpaid:                    {c['overpaid']}")
    lines.append(f"  Missing (no payment):        {c['missing']}")
    lines.append(f"  Unmatched (no booking):      {c['unmatched']}")
    lines.append("")

    # ── MATCHED ──
    if results["matched"]:
        lines.append("--- MATCHED PAYMENTS [OK] ---")
        for m in results["matched"]:
            lines.append(
                f"  [OK] {m['supplier']} / {m['client_name']} "
                f"(#{m['booking_id']}) — Expected {_fmt_usd(m['expected_commission'])}, "
                f"Received {_fmt_usd(m['amount_paid'])}"
            )
        lines.append("")

    # ── UNDERPAID ──
    if results["underpaid"]:
        lines.append("--- UNDERPAYMENTS [SHORTFALL] ---")
        for u in results["underpaid"]:
            lines.append(
                f"  [!!] {u['supplier']} / {u['client_name']} "
                f"(#{u['booking_id']}) — Expected {_fmt_usd(u['expected_commission'])}, "
                f"Received {_fmt_usd(u['amount_paid'])}, "
                f"Shortfall: {_fmt_usd(abs(u['delta']))}"
            )
        lines.append("")

    # ── OVERPAID ──
    if results["overpaid"]:
        lines.append("--- OVERPAYMENTS [SURPLUS] ---")
        for o in results["overpaid"]:
            lines.append(
                f"  [++] {o['supplier']} / {o['client_name']} "
                f"(#{o['booking_id']}) — Expected {_fmt_usd(o['expected_commission'])}, "
                f"Received {_fmt_usd(o['amount_paid'])}, "
                f"Surplus: {_fmt_usd(o['delta'])}"
            )
        lines.append("")

    # ── MISSING ──
    if results["missing"]:
        lines.append("--- MISSING PAYMENTS [NOT RECEIVED] ---")
        for m in results["missing"]:
            lines.append(
                f"  [XX] {m['supplier']} / {m['client_name']} "
                f"(#{m['booking_id']}) — Expected {_fmt_usd(m['expected_commission'])} "
                f"— Status: {m.get('status', 'unknown')}"
            )
        lines.append("")

    # ── UNMATCHED ──
    if results["unmatched"]:
        lines.append("--- UNMATCHED PAYMENTS [NO BOOKING FOUND] ---")
        for u in results["unmatched"]:
            lines.append(
                f"  [??] {u.get('supplier_name', 'Unknown')} — "
                f"{_fmt_usd(u.get('amount_paid', 0))} "
                f"on {u.get('payment_date', 'unknown date')} "
                f"(ref: {u.get('booking_reference', 'none')})"
            )
        lines.append("")

    # ── ACTION ITEMS ──
    actions = []
    for u in results["underpaid"]:
        actions.append(
            f"Contact {u['supplier']} about {_fmt_usd(abs(u['delta']))} "
            f"shortfall on booking #{u['booking_id']} ({u['client_name']})"
        )
    for m in results["missing"]:
        actions.append(
            f"Follow up with {m['supplier']} — no payment received for "
            f"booking #{m['booking_id']} ({m['client_name']}), "
            f"expected {_fmt_usd(m['expected_commission'])}"
        )
    for u in results["unmatched"]:
        if u.get("amount_paid", 0) > 0:
            actions.append(
                f"Investigate unmatched payment of {_fmt_usd(u.get('amount_paid', 0))} "
                f"from {u.get('supplier_name', 'unknown')} — no matching booking found"
            )

    if actions:
        lines.append("--- ACTION ITEMS ---")
        for i, action in enumerate(actions, 1):
            lines.append(f"  {i}. {action}")
        lines.append("")

    lines.append("=" * 70)
    lines.append("  End of Report — Vic Harlan (A9), Finance & Process Improvement")
    lines.append("=" * 70)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# FULL PIPELINE
# ---------------------------------------------------------------------------

def run_reconciliation(days_back: int = 90, dry_run: bool = False) -> dict:
    """Full commission reconciliation pipeline.

    Steps:
      1. Read expected commissions from Booking Master
      2. Search Gmail for payment emails
      3. Parse each payment email via Groq
      4. Reconcile expected vs received
      5. Generate report
      6. Email report to Commander (unless dry_run)
      7. Log to ~/Thunderbird/logs/commission_recon.log

    Returns dict with: report (str), results (dict), timestamp.
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"Starting commission reconciliation (days_back={days_back})")

    # Step 1: Get expected commissions
    try:
        expected = get_expected_commissions()
        logger.info(f"Step 1: {len(expected)} expected commissions loaded")
    except Exception as e:
        logger.error(f"Failed to read Booking Master: {e}")
        return {"error": f"Sheets read failed: {e}", "timestamp": ts}

    # Step 2: Search Gmail for payment emails
    try:
        payment_emails = search_payment_emails(days_back=days_back)
        logger.info(f"Step 2: {len(payment_emails)} payment emails found")
    except Exception as e:
        logger.error(f"Gmail search failed: {e}")
        return {"error": f"Gmail search failed: {e}", "timestamp": ts}

    # Step 3: Parse payment amounts from each email
    received = []
    for email in payment_emails:
        email_text = f"Subject: {email['subject']}\nFrom: {email['sender']}\n\n{email['body']}"
        parsed = parse_payment_amount(email_text)
        if parsed.get("error"):
            logger.warning(f"Parse failed for email '{email['subject'][:50]}': {parsed['error']}")
            continue
        # Attach the original email metadata
        parsed["_email_id"] = email["message_id"]
        parsed["_email_subject"] = email["subject"]
        parsed["_email_sender"] = email["sender"]
        received.append(parsed)

    logger.info(f"Step 3: {len(received)} payments successfully parsed from {len(payment_emails)} emails")

    # Step 4: Reconcile
    results = reconcile(expected, received)
    logger.info(
        f"Step 4: Reconciled — {results['counts']['matched']} matched, "
        f"{results['counts']['missing']} missing, "
        f"{results['counts']['underpaid']} underpaid"
    )

    # Step 5: Generate report
    report = generate_recon_report(results)

    # Step 6: Log to file
    _log_recon(report, results, ts)

    # Step 7: Email report to Commander (draft, not auto-send)
    if not dry_run and (results["counts"]["missing"] > 0 or results["counts"]["underpaid"] > 0):
        try:
            from thunderbird_gmail import gmail_send_with_approval
            gmail_send_with_approval(
                to="johnloucks3@gmail.com",
                subject=f"Commission Reconciliation Report — {datetime.now().strftime('%b %d, %Y')}",
                body=report,
                persona_id="A9",
                auto_send=False,  # Draft for Commander review
            )
            logger.info("Step 7: Recon report drafted to Commander via Gmail")
        except Exception as e:
            logger.warning(f"Failed to draft recon email: {e}")

    # Step 8: Store summary in A9 persona memory (best effort)
    _store_a9_memory(results)

    return {
        "report": report,
        "results": results,
        "timestamp": ts,
        "emails_searched": len(payment_emails),
        "payments_parsed": len(received),
        "dry_run": dry_run,
    }


def _log_recon(report: str, results: dict, timestamp: str):
    """Write reconciliation report and summary to the log file."""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 70}\n")
            f.write(f"[{timestamp}] Commission Reconciliation Run\n")
            f.write(f"{'=' * 70}\n")
            f.write(report)
            f.write("\n\n--- Raw Totals JSON ---\n")
            f.write(json.dumps(results["totals"], indent=2))
            f.write("\n--- Counts JSON ---\n")
            f.write(json.dumps(results["counts"], indent=2))
            f.write("\n\n")
    except Exception as e:
        logger.warning(f"Failed to write recon log: {e}")


def _store_a9_memory(results: dict):
    """Store a summary in A9 Harlan's persona memory for proactive briefings."""
    try:
        from thunderbird_personas import store_persona_memory
        t = results["totals"]
        c = results["counts"]
        summary = (
            f"Commission Recon ({datetime.now().strftime('%Y-%m-%d')}): "
            f"Expected {_fmt_usd(t['total_expected'])}, "
            f"Received {_fmt_usd(t['total_received'])}, "
            f"Gap {_fmt_usd(t['total_gap'])}. "
            f"{c['matched']} matched, {c['missing']} missing, "
            f"{c['underpaid']} underpaid."
        )
        store_persona_memory("A9", "commission_recon", summary)
        logger.info("Stored recon summary in A9 persona memory")
    except Exception as e:
        # Non-critical — don't fail the pipeline
        logger.debug(f"Could not store A9 memory (non-critical): {e}")


# ---------------------------------------------------------------------------
# MCP TOOL REGISTRATION
# ---------------------------------------------------------------------------

def register_commission_recon_tools(mcp: FastMCP):
    """Register commission reconciliation tools with the MCP server."""

    @mcp.tool(
        name="reconcile_commissions",
        annotations={
            "title": "Run Commission Reconciliation",
            "readOnlyHint": True,
        },
    )
    async def reconcile_commissions(
        days_back: int = Field(
            90,
            description="Number of days to search back for payment emails (default 90)",
        ),
    ) -> str:
        """Run commission reconciliation to match supplier payments against expected commissions.

        Reads expected commissions from Booking Master, searches Gmail for
        payment/remittance emails, extracts amounts via Groq, and generates
        a reconciliation report with matched, underpaid, missing, and unmatched items.
        Drafts the report to Commander for review if discrepancies are found.
        """
        try:
            result = run_reconciliation(days_back=days_back, dry_run=False)
            if "error" in result:
                return json.dumps({"status": "error", "error": result["error"]}, indent=2)

            return json.dumps({
                "status": "success",
                "timestamp": result["timestamp"],
                "totals": result["results"]["totals"],
                "counts": result["results"]["counts"],
                "report": result["report"],
                "emails_searched": result["emails_searched"],
                "payments_parsed": result["payments_parsed"],
            }, indent=2)

        except Exception as e:
            logger.error(f"Commission reconciliation failed: {e}")
            return json.dumps({"status": "error", "error": str(e)}, indent=2)

    logger.info("Commission reconciliation tools registered")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    )

    if "--expected-only" in sys.argv:
        print("Reading expected commissions from Booking Master...")
        commissions = get_expected_commissions()
        for c in commissions:
            print(
                f"  {c['supplier']:25s} | {c['client_name']:20s} | "
                f"#{c['booking_id']:15s} | "
                f"Expected: {_fmt_usd(c['expected_commission']):>12s} | "
                f"Status: {c['status']}"
            )
        print(f"\nTotal: {len(commissions)} bookings")
        sys.exit(0)

    days = 90
    if "--days" in sys.argv:
        idx = sys.argv.index("--days")
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])

    dry_run = "--dry-run" in sys.argv

    print(f"Running commission reconciliation (days_back={days}, dry_run={dry_run})...")
    result = run_reconciliation(days_back=days, dry_run=dry_run)

    if "error" in result:
        print(f"\nERROR: {result['error']}")
        sys.exit(1)

    print(result["report"])
    print(f"\nLog saved to: {LOG_FILE}")
