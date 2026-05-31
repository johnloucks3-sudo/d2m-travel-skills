#!/usr/bin/env python3
"""
Schema-Validated Price Intelligence Agent — MISSION-091
D2M Thunderbird Wing | core/ai_infra/schema_price_intel.py

Uses `claude --print --output-format json --json-schema <schema>` for structured
price lookups from multiple luxury travel sources. Returns validated JSON dicts —
no text parsing needed.

$0 marginal cost via MAX OAuth (same spawn path as thunderbird_headless_spawn).
Parallel fan-out via ThreadPoolExecutor.

Integration hook: price_result_to_finding() maps results into Finding objects
compatible with core/intel/thunderbird_agentic_intel.py.

Completion gate: run `python3 core/ai_infra/schema_price_intel.py` for offline
commission math smoke tests (no live Claude call required).
"""
from __future__ import annotations

import json
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import jsonschema

from core.ai_infra.thunderbird_headless_spawn import load_oauth_token, verify_prerequisites, spawn_headless_claude

logger = logging.getLogger("schema_price_intel")

# ============================================================================
# Constants
# ============================================================================

CLAUDE_BIN = "/home/john/.local/bin/claude"
MCP_CONFIG = "/home/john/.claude/mcp.json"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"  # Haiku: extraction/classification per SO-TOKEN-DISCIPLINE

EUR_TO_USD = 1.09       # CLAUDE.md default; verify live for quotes > $5,000
STANDARD_MARKUP = 0.25  # Standard hotels/cruises
PREMIUM_MARKUP = 0.22   # Premium / SLH properties
PONANT_COMMISSION = 0.18  # Midpoint 16-20% agent commission range

# D2M targeted luxury lines (CLAUDE.md §7)
D2M_CRUISE_LINES: list[str] = [
    "silversea", "regent", "cunard", "oceania",
    "seabourn", "viking", "amawaterways", "ponant",
]

# Source-specific context injected into each prompt
_SOURCE_CONTEXT: dict[str, str] = {
    "silversea": "Silversea Cruises — ultra-luxury all-inclusive. Check silversea.com for voyage fares, suite categories, and availability.",
    "regent":    "Regent Seven Seas Cruises — ultra-luxury all-inclusive. Check rssc.com for voyage fares, suite categories, and availability.",
    "oceania":   "Oceania Cruises — upper-premium cuisine-focused. Check oceaniacruises.com for voyage fares and cabin categories.",
    "viking":    "Viking Ocean Cruises — destination-focused premium. Check vikingcruises.com for voyage fares and stateroom categories.",
    "ponant":    "Ponant — French ultra-luxury expedition. Check us.ponant.com for voyage fares and cabin categories.",
    "seabourn":  "Seabourn — ultra-luxury all-inclusive. Check seabourn.com for voyage fares and suite categories.",
    "cunard":    "Cunard — classic luxury transatlantic. Check cunard.com for voyage fares and cabin grades.",
    "amawaterways": "AmaWaterways — luxury river cruises. Check amawaterways.com for voyage fares and cabin categories.",
}


# ============================================================================
# JSON Schemas — exported for consumers and validation
# ============================================================================

PRICE_INTEL_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "source_name":          {"type": "string", "description": "Cruise line or supplier name"},
        "source_type":          {"type": "string", "enum": ["cruise", "hotel", "tour", "flight", "transfer"]},
        "query_date":           {"type": "string", "description": "ISO date of this lookup (YYYY-MM-DD)"},
        "cruise_line":          {"type": ["string", "null"]},
        "ship_name":            {"type": ["string", "null"]},
        "voyage_id":            {"type": ["string", "null"]},
        "departure_date":       {"type": ["string", "null"], "description": "ISO date YYYY-MM-DD"},
        "departure_port":       {"type": ["string", "null"]},
        "destination":          {"type": ["string", "null"]},
        "nights":               {"type": ["integer", "null"]},
        "cabin_category":       {"type": ["string", "null"], "description": "e.g. Veranda Suite, Vista Suite"},
        "cabin_type":           {"type": ["string", "null"], "description": "Cabin code e.g. V2, OC"},
        "list_price_per_person": {"type": ["number", "null"], "description": "Published per-person price in USD"},
        "list_price_total":      {"type": ["number", "null"], "description": "Published total (2 pax) in USD"},
        "net_price_per_person":  {"type": ["number", "null"], "description": "Net/wholesale per-person if available"},
        "net_price_total":       {"type": ["number", "null"], "description": "Net/wholesale total if available"},
        "currency":              {"type": "string", "description": "Currency code, e.g. USD, EUR"},
        "availability":          {"type": "string", "enum": ["AVAILABLE", "WAITLIST", "SOLD_OUT", "UNKNOWN"]},
        "promo_codes":           {"type": "array", "items": {"type": "string"}},
        "inclusions":            {"type": "array", "items": {"type": "string"}},
        "early_booking_bonus":   {"type": ["string", "null"]},
        "notes":                 {"type": "string"},
        "confidence":            {
            "type": "string",
            "enum": ["HIGH", "MEDIUM", "LOW"],
            "description": "HIGH=verified, MEDIUM=inferred, LOW=estimated/stale",
        },
        "source_url":            {"type": ["string", "null"]},
        "raw_excerpt":           {"type": ["string", "null"]},
    },
    "required": ["source_name", "source_type", "query_date", "availability", "confidence"],
}

COMMISSION_RECONCILIATION_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "price_record_id":   {"type": "string"},
        "net_usd":           {"type": "number", "description": "Net/wholesale amount in USD"},
        "markup_pct":        {"type": "number", "description": "Markup percentage (e.g. 25.0)"},
        "client_price_usd":  {"type": "number"},
        "commission_usd":    {"type": "number", "description": "D2M commission in USD"},
        "d2m_share_usd":     {"type": "number", "description": "D2M net share in USD"},
        "commission_type":   {"type": "string", "enum": ["standard", "premium", "ponant"]},
        "portal_verified":   {"type": "boolean"},
        "harlan_sign_off":   {"type": ["string", "null"]},
        "notes":             {"type": "string"},
    },
    "required": ["net_usd", "markup_pct", "client_price_usd", "commission_usd", "d2m_share_usd"],
}

FAN_OUT_RESULT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "query":             {"type": "string"},
        "query_date":        {"type": "string"},
        "sources_queried":   {"type": "integer"},
        "sources_succeeded": {"type": "integer"},
        "results": {"type": "array", "items": PRICE_INTEL_SCHEMA},
        "errors":  {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "error":  {"type": "string"},
                },
            },
        },
    },
    "required": ["query", "query_date", "sources_queried", "sources_succeeded", "results"],
}


# ============================================================================
# Utility helpers (mirrors fmt_usd from core/travel modules)
# ============================================================================

def fmt_usd(amount: float) -> str:
    try:
        return f"${float(amount):,.2f}"
    except (ValueError, TypeError):
        return str(amount)


def _build_price_prompt(source: str, query: str) -> str:
    context = _SOURCE_CONTEXT.get(source.lower(), f"{source} — travel supplier")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return (
        f"You are a travel price intelligence agent for Dreams2Memories Travel, LLC.\n"
        f"Today's date: {today}\n\n"
        f"Source context: {context}\n\n"
        f"Price lookup query: {query}\n\n"
        f"Return all price data you can determine from your knowledge about this source "
        f"and query. Rules:\n"
        f"- Use availability=UNKNOWN and confidence=LOW when uncertain.\n"
        f"- Use confidence=HIGH only for data you are certain about.\n"
        f"- Set null for any numeric field you cannot confirm — never fabricate prices.\n"
        f"- Set source_name='{source}', source_type='cruise', query_date='{today}'.\n"
        f"- currency should be 'USD' unless the line prices natively in EUR.\n"
        f"- inclusions: list what is all-inclusive (beverages, tips, flights, excursions, etc.).\n"
        f"- notes: note any caveats about data freshness or uncertainty."
    )


# ============================================================================
# Core: claude --json-schema invocation via MAX OAuth
# ============================================================================

def _invoke_claude_json_schema(
    prompt: str,
    schema: dict,
    model: str = DEFAULT_MODEL,
    timeout: int = 60,
) -> dict:
    """
    Synchronous `claude --print --output-format json --json-schema <schema>` call.
    Returns a validated dict conforming to `schema`. No text parsing needed.

    Uses foolproof wrapper (spawn_headless_claude) with extra_args for --json-schema.
    $0 marginal cost via MAX OAuth.

    Raises:
        RuntimeError  — spawn prerequisites failed or Claude returned an error
        TimeoutError  — Claude did not respond within `timeout` seconds
        ValueError    — Claude returned non-JSON or schema validation failed
    """
    schema_json = json.dumps(schema)

    # Use foolproof wrapper per SO 24 APR 2026 with extra_args for --json-schema
    output_file = "/tmp/schema_result.json"
    result = spawn_headless_claude(
        prompt=prompt,
        output_file=output_file,
        model=model,
        task_name="json_schema_validation",
        background=False,
        timeout=timeout,
        extra_args=["--output-format", "json", "--json-schema", schema_json],
    )

    if result.get("status") == "TIMEOUT":
        raise TimeoutError(f"Claude invocation timed out after {timeout}s")
    elif result.get("status") not in ["COMPLETED"]:
        raise RuntimeError(
            f"Claude spawn failed: {result.get('error', 'unknown error')}"
        )

    # Read the output file
    try:
        stdout = Path(output_file).read_text()
    except FileNotFoundError:
        raise RuntimeError("Claude did not write output file")

    # Parse the --output-format json envelope:
    # {"type":"result","subtype":"success","is_error":false,"result":"<json_str>", ...}
    try:
        envelope = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Claude returned non-JSON envelope: {stdout[:300]} — {exc}"
        ) from exc

    if envelope.get("is_error") or envelope.get("type") == "error":
        raise RuntimeError(f"Claude error response: {envelope}")

    raw = envelope.get("result", envelope)

    if isinstance(raw, dict):
        result = raw
    elif isinstance(raw, str):
        try:
            result = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Schema result field is not valid JSON: {raw[:300]} — {exc}"
            ) from exc
    else:
        raise ValueError(f"Unexpected result type {type(raw)}: {raw!r}")

    # Defense-in-depth: validate against schema (logs warning, does not hard-fail)
    try:
        jsonschema.validate(result, schema)
    except jsonschema.ValidationError as exc:
        logger.warning("Schema soft-validation warning for %s: %s", schema.get("title", "schema"), exc.message)

    return result


# ============================================================================
# Commission reconciliation — pure math, no live call
# Mirrors _apply_markup() from core/travel/thunderbird_flight_search.py et al.
# ============================================================================

def reconcile_commission(
    price_record: dict,
    commission_type: str = "standard",
) -> dict:
    """
    Apply D2M commission math to a PRICE_INTEL_SCHEMA result.

    standard → 25% markup on net: client_price = net * 1.25
    premium  → 22% markup on net (SLH / upper-premium properties)
    ponant   → 18% agent commission on list price (Ponant pays D2M; client pays list)

    Ponant distinction: D2M does not mark up the net for Ponant. The client pays
    the published list price; Ponant remits a 16-20% agent commission to D2M.
    All other lines: D2M marks up the net/wholesale price.

    Returns dict conforming to COMMISSION_RECONCILIATION_SCHEMA.
    Harlan sign-off (Rule 5, SO-PIPELINE-INTEGRITY-20260528) remains None until
    portal-verified by A9.
    """
    markup_map = {
        "standard": STANDARD_MARKUP,
        "premium":  PREMIUM_MARKUP,
        "ponant":   PONANT_COMMISSION,
    }
    markup = markup_map.get(commission_type, STANDARD_MARKUP)

    # Prefer net total → net pp → list total (fallback for lines with no net pricing)
    net_raw = float(
        price_record.get("net_price_total")
        or price_record.get("net_price_per_person")
        or price_record.get("list_price_total")
        or 0.0
    )

    # Medium finding fix (MISSION-091 — CC Review): explicit fail on empty price record.
    # Converts silent commission-math failure ($0 propagation) to explicit exception.
    # Logged: SO-PIPELINE-INTEGRITY-20260528 guard rail on financial data quality.
    if net_raw == 0.0:
        raise ValueError(
            f"No usable price data in record from {price_record.get('source_name', 'unknown')} "
            f"— net_price_total, net_price_per_person, and list_price_total are all null/zero."
        )

    currency = price_record.get("currency", "USD")
    if currency.upper() == "EUR":
        net_raw = net_raw * EUR_TO_USD

    if commission_type == "ponant":
        # Ponant: client pays list; D2M earns markup% of list from Ponant as agent comm
        list_raw = float(
            price_record.get("list_price_total")
            or price_record.get("list_price_per_person")
            or net_raw
        )
        if currency.upper() == "EUR":
            list_raw = list_raw * EUR_TO_USD
        commission_usd = list_raw * markup
        client_price = list_raw
        d2m_share = commission_usd
    else:
        client_price = net_raw * (1 + markup)
        commission_usd = client_price - net_raw
        d2m_share = commission_usd  # 1-person shop — 100% to D2M

    record_id = str(
        price_record.get("voyage_id")
        or price_record.get("source_name")
        or ""
    )

    return {
        "price_record_id":  record_id,
        "net_usd":          round(net_raw, 2),
        "markup_pct":       markup * 100,
        "client_price_usd": round(client_price, 2),
        "commission_usd":   round(commission_usd, 2),
        "d2m_share_usd":    round(d2m_share, 2),
        "commission_type":  commission_type,
        "portal_verified":  False,
        "harlan_sign_off":  None,
        "notes": (
            f"{commission_type.capitalize()} commission applied. "
            f"Portal verification pending — Harlan (A9) sign-off required "
            f"per SO-PIPELINE-INTEGRITY-20260528 Rule 5 before any client email."
        ),
    }


# ============================================================================
# Integration hook: price result → Finding (thunderbird_agentic_intel.py)
# ============================================================================

def price_result_to_finding(price_result: dict, query: str):
    """
    Map a PRICE_INTEL_SCHEMA dict to a Finding object for use in
    thunderbird_agentic_intel.run_sweep() and intel email rendering.

    Import is lazy to avoid circular dependency at module load time.
    """
    from core.intel.thunderbird_agentic_intel import Finding  # noqa: PLC0415

    source = price_result.get("source_name", "unknown")
    ship = price_result.get("ship_name") or ""
    departure = price_result.get("departure_date") or ""
    availability = price_result.get("availability", "UNKNOWN")
    confidence = price_result.get("confidence", "LOW")

    title = f"[PRICE] {source}"
    if ship:
        title += f" — {ship}"
    if departure:
        title += f" ({departure})"

    price_str = ""
    if price_result.get("list_price_per_person"):
        price_str = fmt_usd(price_result["list_price_per_person"]) + "/pp"
    elif price_result.get("list_price_total"):
        price_str = fmt_usd(price_result["list_price_total"]) + " total"

    summary = f"{query} | {availability} | {price_str} | Confidence: {confidence}"

    tier = "HIGH" if availability == "AVAILABLE" and confidence != "LOW" else "WATCH"
    score_map = {"HIGH": 50, "MEDIUM": 25, "LOW": 10}

    return Finding(
        title=title[:200],
        source=f"price_intel/{source.lower().replace(' ', '_')}",
        url=price_result.get("source_url") or "",
        summary=summary[:300],
        keywords_matched=[source.lower(), "price_intel", query[:30]],
        score=score_map.get(confidence, 10),
        tier=tier,
    )


# ============================================================================
# SchemaPriceAgent — primary class
# ============================================================================

class SchemaPriceAgent:
    """
    Schema-validated price intelligence agent for D2M luxury cruise research.

    Uses `claude --json-schema` for structured lookups. All results conform to
    PRICE_INTEL_SCHEMA — no text parsing required by callers.

    Model routing:
    - Haiku (default) — extraction/classification per SO-TOKEN-DISCIPLINE
    - Pass model='claude-sonnet-4-6' for synthesis across conflicting results

    Cost: $0 via MAX OAuth.
    """

    def __init__(self, model: str = DEFAULT_MODEL, timeout: int = 60):
        self.model = model
        self.timeout = timeout

    def lookup_price(self, source: str, query: str) -> dict:
        """
        Single-source structured price lookup.

        Args:
            source: Cruise line key (e.g. 'regent', 'silversea') or free-form name
            query: Natural-language price query (e.g. '7-night Caribbean Dec 2026')

        Returns:
            dict conforming to PRICE_INTEL_SCHEMA
        """
        prompt = _build_price_prompt(source, query)
        return _invoke_claude_json_schema(
            prompt=prompt,
            schema=PRICE_INTEL_SCHEMA,
            model=self.model,
            timeout=self.timeout,
        )

    def fan_out(
        self,
        sources: list[str],
        query: str,
        max_workers: int = 4,
    ) -> dict:
        """
        Parallel multi-source price lookup via ThreadPoolExecutor.

        Args:
            sources: List of source keys to query in parallel
            query:   Price query applied to each source
            max_workers: Max parallel workers (capped at len(sources))

        Returns:
            dict conforming to FAN_OUT_RESULT_SCHEMA
        """
        results: list[dict] = []
        errors: list[dict] = []

        def _one(src: str) -> dict:
            return self.lookup_price(source=src, query=query)

        with ThreadPoolExecutor(max_workers=min(max_workers, len(sources))) as pool:
            futures = {pool.submit(_one, src): src for src in sources}
            for future in as_completed(futures):
                src = futures[future]
                try:
                    results.append(future.result())
                except Exception as exc:
                    logger.warning("fan_out: %s failed — %s", src, exc)
                    errors.append({"source": src, "error": str(exc)})

        return {
            "query":             query,
            "query_date":        datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "sources_queried":   len(sources),
            "sources_succeeded": len(results),
            "results":           results,
            "errors":            errors,
        }

    def reconcile_commissions(self, fan_out_result: dict) -> list[dict]:
        """
        Apply commission math to all results in a fan_out() response.
        Ponant results use ponant commission type; all others use standard.

        Returns list of COMMISSION_RECONCILIATION_SCHEMA dicts, each with
        the source price_record embedded under key 'price_record'.
        """
        reconciled = []
        for r in fan_out_result.get("results", []):
            ctype = "ponant" if "ponant" in r.get("source_name", "").lower() else "standard"
            rec = reconcile_commission(r, commission_type=ctype)
            rec["price_record"] = r
            reconciled.append(rec)
        return reconciled

    def to_findings(self, fan_out_result: dict, query: str) -> list:
        """
        Convert all fan_out results to Finding objects for thunderbird_agentic_intel.
        """
        return [
            price_result_to_finding(r, query)
            for r in fan_out_result.get("results", [])
        ]


# ============================================================================
# Convenience wrappers
# ============================================================================

def lookup_cruise_price(source: str, query: str, model: str = DEFAULT_MODEL) -> dict:
    """Single-call convenience wrapper. Returns PRICE_INTEL_SCHEMA dict."""
    return SchemaPriceAgent(model=model).lookup_price(source=source, query=query)


def fan_out_cruise_prices(
    query: str,
    sources: Optional[list[str]] = None,
    max_workers: int = 4,
) -> dict:
    """
    Multi-source fan-out convenience wrapper.
    Defaults to all D2M_CRUISE_LINES if sources is None.
    Returns FAN_OUT_RESULT_SCHEMA dict.
    """
    return SchemaPriceAgent().fan_out(
        sources=sources or D2M_CRUISE_LINES,
        query=query,
        max_workers=max_workers,
    )


# ============================================================================
# __main__ — offline smoke test (commission math + schema validation, no live call)
# ============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    print("=== MISSION-091 Schema Price Intel — Smoke Test ===")
    print("(Commission math + schema validation — no live Claude call)\n")
    passed = 0
    failed = 0

    def _check(label: str, condition: bool, detail: str = "") -> None:
        global passed, failed
        if condition:
            print(f"   ✅  {label}")
            passed += 1
        else:
            print(f"   ❌  {label}" + (f" — {detail}" if detail else ""))
            failed += 1

    # ── Test 1: Standard markup (Regent) ──────────────────────────────────
    print("1. Standard markup — Regent net $12,000")
    r1 = reconcile_commission(
        {"source_name": "regent", "voyage_id": "REG-12345", "net_price_total": 12000.0, "currency": "USD"},
        "standard",
    )
    _check("markup_pct == 25.0",       r1["markup_pct"] == 25.0)
    _check("client_price == $15,000",  r1["client_price_usd"] == 15000.0)
    _check("commission == $3,000",     r1["commission_usd"] == 3000.0)
    _check("d2m_share == $3,000",      r1["d2m_share_usd"] == 3000.0)
    _check("harlan_sign_off is None",  r1["harlan_sign_off"] is None)
    print(f"   net={fmt_usd(r1['net_usd'])} → client={fmt_usd(r1['client_price_usd'])} | commission={fmt_usd(r1['commission_usd'])}\n")

    # ── Test 2: Ponant agent commission ───────────────────────────────────
    print("2. Ponant agent commission — list price $20,000")
    r2 = reconcile_commission(
        {"source_name": "ponant", "voyage_id": "PON-98765", "list_price_total": 20000.0, "currency": "USD"},
        "ponant",
    )
    expected_comm = round(20000.0 * 0.18, 2)
    _check("markup_pct == 18.0",        r2["markup_pct"] == 18.0)
    _check("client_price == list price", r2["client_price_usd"] == 20000.0)
    _check("commission == 18% of list",  r2["commission_usd"] == expected_comm)
    print(f"   list={fmt_usd(r2['client_price_usd'])} → D2M earns={fmt_usd(r2['commission_usd'])} (18% agent comm)\n")

    # ── Test 3: EUR → USD + premium markup ───────────────────────────────
    print("3. EUR conversion + premium markup — Cunard net EUR 10,000")
    r3 = reconcile_commission(
        {"source_name": "cunard", "net_price_total": 10000.0, "currency": "EUR"},
        "premium",
    )
    expected_net    = round(10000.0 * EUR_TO_USD, 2)
    expected_client = round(expected_net * 1.22, 2)
    _check("EUR→USD conversion",       r3["net_usd"] == expected_net,
           f"got {r3['net_usd']}, expected {expected_net}")
    _check("premium markup 22%",        r3["markup_pct"] == 22.0)
    _check("client_price correct",      r3["client_price_usd"] == expected_client,
           f"got {r3['client_price_usd']}, expected {expected_client}")
    print(f"   EUR 10,000 → {fmt_usd(r3['net_usd'])} net → {fmt_usd(r3['client_price_usd'])} client (22% premium)\n")

    # ── Test 4: Schema validation ─────────────────────────────────────────
    print("4. Schema validation — PRICE_INTEL_SCHEMA")
    try:
        jsonschema.validate(
            {
                "source_name": "silversea", "source_type": "cruise",
                "query_date": "2026-05-31", "availability": "AVAILABLE",
                "confidence": "HIGH", "currency": "USD",
                "promo_codes": [], "inclusions": ["beverages", "tips"],
                "notes": "All-inclusive.",
            },
            PRICE_INTEL_SCHEMA,
        )
        _check("PRICE_INTEL_SCHEMA valid sample", True)
    except jsonschema.ValidationError as exc:
        _check("PRICE_INTEL_SCHEMA valid sample", False, exc.message)

    print("\n5. Schema validation — COMMISSION_RECONCILIATION_SCHEMA")
    try:
        jsonschema.validate(
            {
                "price_record_id": "REG-12345",
                "net_usd": 12000.0, "markup_pct": 25.0,
                "client_price_usd": 15000.0, "commission_usd": 3000.0,
                "d2m_share_usd": 3000.0, "commission_type": "standard",
                "portal_verified": False, "harlan_sign_off": None,
                "notes": "Pending portal verification.",
            },
            COMMISSION_RECONCILIATION_SCHEMA,
        )
        _check("COMMISSION_RECONCILIATION_SCHEMA valid sample", True)
    except jsonschema.ValidationError as exc:
        _check("COMMISSION_RECONCILIATION_SCHEMA valid sample", False, exc.message)

    # ── Test 5: fan_out result structure ──────────────────────────────────
    print("\n6. fan_out result structure validation")
    mock_fan_out = {
        "query": "7-night Caribbean Dec 2026",
        "query_date": "2026-05-31",
        "sources_queried": 2,
        "sources_succeeded": 1,
        "results": [
            {"source_name": "regent", "source_type": "cruise", "query_date": "2026-05-31",
             "availability": "AVAILABLE", "confidence": "HIGH", "currency": "USD",
             "list_price_total": 14000.0,  # required: guard rejects zero-price records
             "promo_codes": [], "inclusions": [], "notes": ""}
        ],
        "errors": [{"source": "silversea", "error": "timeout"}],
    }
    try:
        jsonschema.validate(mock_fan_out, FAN_OUT_RESULT_SCHEMA)
        _check("FAN_OUT_RESULT_SCHEMA valid sample", True)
    except jsonschema.ValidationError as exc:
        _check("FAN_OUT_RESULT_SCHEMA valid sample", False, exc.message)

    # ── reconcile_commissions on mock fan_out ─────────────────────────────
    agent = SchemaPriceAgent()
    recs = agent.reconcile_commissions(mock_fan_out)
    _check("reconcile_commissions returns 1 record", len(recs) == 1)
    _check("record embeds price_record", "price_record" in recs[0])

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    if failed:
        print("FAIL — see errors above")
        sys.exit(1)
    else:
        print("All smoke tests PASS. Module importable.")
        print(f"\nUsage:")
        print(f"  from core.ai_infra.schema_price_intel import SchemaPriceAgent")
        print(f"  agent = SchemaPriceAgent()")
        print(f"  result = agent.lookup_price('regent', '7-night Caribbean Dec 2026')")
        print(f"  fan = agent.fan_out(['regent', 'silversea'], '7-night Caribbean Dec 2026')")
        print(f"  commissions = agent.reconcile_commissions(fan)")
