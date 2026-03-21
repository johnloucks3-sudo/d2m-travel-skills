"""
Thunderbird API Cost Tracker
==============================
Logs all API calls (Claude, Gemini, Hotelbeds, Amadeus) with token counts
and estimated costs. Writes to Google Sheets API_Cost_Log tab.

Usage:
    from thunderbird_api_costs import log_api_call, get_daily_summary

    log_api_call("anthropic", "claude-sonnet-4-20250514", input_tokens=500, output_tokens=200,
                 caller="A3", task="booking_status")

    summary = get_daily_summary()  # Returns today's costs by provider
"""

import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import gspread
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
CREDENTIALS_FILE = THUNDERBIRD_DIR / "credentials.json"
SPREADSHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
TAB_NAME = "API_Cost_Log"
LOCAL_LOG = THUNDERBIRD_DIR / "api_cost_log.jsonl"

# ── Pricing per 1M tokens (USD) ──
PRICING = {
    # Groq ELIMINATED — pricing retained for historical cost analysis only
    "llama-3.3-70b-versatile":   {"input": 0.59,  "output": 0.79},
    "llama-3.1-8b-instant":      {"input": 0.05,  "output": 0.08},
    # Anthropic Claude (primary engine — $0 on Max plan)
    "claude-sonnet-4-20250514":  {"input": 3.00,  "output": 15.00},
    "claude-opus-4-20250514":    {"input": 15.00, "output": 75.00},
    "claude-haiku-4-5-20251001": {"input": 0.80,  "output": 4.00},
    # Google Gemini
    "gemini-2.0-flash":          {"input": 0.10,  "output": 0.40},
    "gemini-1.5-pro":            {"input": 1.25,  "output": 5.00},
    # API calls (flat rate per call)
    "hotelbeds":     {"per_call": 0.00},  # Free tier
    "amadeus":       {"per_call": 0.00},  # Free tier
    "bedsonline":    {"per_call": 0.00},  # Browser scrape
}

HEADERS = [
    "Timestamp", "Date", "Provider", "Model", "Input_Tokens", "Output_Tokens",
    "Cache_Tokens", "Cost_USD", "Caller", "Task", "Notes"
]


def _get_sheet():
    """Get or create the API_Cost_Log tab."""
    creds = service_account.Credentials.from_service_account_file(
        str(CREDENTIALS_FILE),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gc = gspread.authorize(creds)
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)

    try:
        ws = spreadsheet.worksheet(TAB_NAME)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=TAB_NAME, rows=1000, cols=len(HEADERS))
        ws.update(values=[HEADERS], range_name="A1")
        ws.format("A1:K1", {"textFormat": {"bold": True}})
        logger.info(f"Created {TAB_NAME} tab with headers")

    return ws


def estimate_cost(model: str, input_tokens: int = 0, output_tokens: int = 0,
                  cache_tokens: int = 0) -> float:
    """Estimate cost in USD for an API call."""
    pricing = PRICING.get(model)
    if not pricing:
        return 0.0

    if "per_call" in pricing:
        return pricing["per_call"]

    input_cost = (input_tokens / 1_000_000) * pricing.get("input", 0)
    output_cost = (output_tokens / 1_000_000) * pricing.get("output", 0)
    # Cache reads are typically 90% cheaper
    cache_cost = (cache_tokens / 1_000_000) * pricing.get("input", 0) * 0.1

    return round(input_cost + output_cost + cache_cost, 6)


def log_api_call(provider: str, model: str,
                 input_tokens: int = 0, output_tokens: int = 0,
                 cache_tokens: int = 0,
                 caller: str = "", task: str = "", notes: str = "",
                 write_sheet: bool = True) -> float:
    """Log an API call and return estimated cost.

    Args:
        provider: anthropic, gemini, hotelbeds, amadeus
        model: model ID string
        input_tokens: input token count
        output_tokens: output token count
        cache_tokens: cached token count (if applicable)
        caller: persona ID or module name
        task: what the call was for
        notes: any additional context
        write_sheet: if True, also append to Google Sheet
    """
    cost = estimate_cost(model, input_tokens, output_tokens, cache_tokens)
    now = datetime.now()

    row = {
        "timestamp": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "provider": provider,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_tokens": cache_tokens,
        "cost_usd": cost,
        "caller": caller,
        "task": task,
        "notes": notes,
    }

    # Always write to local JSONL (fast, reliable)
    with open(LOCAL_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")

    # Optionally write to Google Sheet
    if write_sheet:
        try:
            ws = _get_sheet()
            ws.append_row([
                row["timestamp"], row["date"], provider, model,
                input_tokens, output_tokens, cache_tokens,
                f"${cost:.4f}", caller, task, notes
            ])
        except Exception as e:
            logger.warning(f"Failed to write to Sheet: {e}")

    return cost


def get_daily_summary(target_date: Optional[date] = None) -> dict:
    """Summarize API costs for a given day from local log."""
    target = target_date or date.today()
    target_str = target.isoformat()

    totals = {}
    call_count = 0

    if not LOCAL_LOG.exists():
        return {"date": target_str, "total_cost": 0, "calls": 0, "by_provider": {}}

    with open(LOCAL_LOG, "r", encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            if row.get("date") != target_str:
                continue

            provider = row.get("provider", "unknown")
            cost = row.get("cost_usd", 0)
            totals[provider] = totals.get(provider, 0) + cost
            call_count += 1

    total = sum(totals.values())
    return {
        "date": target_str,
        "total_cost": round(total, 4),
        "calls": call_count,
        "by_provider": {k: round(v, 4) for k, v in sorted(totals.items())},
    }


def setup_sheet():
    """Create the API_Cost_Log tab if it doesn't exist."""
    ws = _get_sheet()
    print(f"API_Cost_Log tab ready. Rows: {ws.row_count}")


if __name__ == "__main__":
    setup_sheet()
    # Log a test entry
    cost = log_api_call(
        "anthropic", "claude-sonnet-4-20250514",
        input_tokens=500, output_tokens=200,
        caller="test", task="router_test", notes="Initial test entry"
    )
    print(f"Test entry logged. Estimated cost: ${cost:.6f}")
    summary = get_daily_summary()
    print(f"Today's summary: {summary}")
