"""
Thunderbird Competitive Surveillance Module (Item #8)
=====================================================

AI travel advisor competitive intelligence for Dreams2Memories Travel, LLC.

Features:
- Search for AI travel competitors via Claude Opus CLI (Max plan, $0)
- Deep-dive competitor profiling with A2 (Dembe) persona
- Landscape report with threat matrix and strategic recommendations
- Store intel to Google Sheets Intel_Log tab and A2 persona memory

Integrates with: travel_mcp_server.py, thunderbird_personas.py
"""

import json
import logging
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

from pydantic import Field
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

CLAUDE_CLI = os.path.expanduser("~/.local/bin/claude")


def _call_claude_cli(system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
    """Call Claude Opus via CLI subprocess (Max plan, $0)."""
    combined = f"System: {system_prompt}\n\nUser: {user_prompt}"
    try:
        result = subprocess.run(
            [CLAUDE_CLI, "-p", combined, "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "TERM": "dumb"},
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        else:
            logger.error(f"Claude CLI error: {result.stderr[:200]}")
            return ""
    except Exception as e:
        logger.error(f"Claude CLI error: {e}")
        return ""

# ============================================================================
# CONFIGURATION
# ============================================================================

THUNDERBIRD_DIR = Path(__file__).parent
SURVEILLANCE_LOG = THUNDERBIRD_DIR / "logs" / "competitive_surveillance.log"
SPREADSHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"

SEARCH_QUERIES = [
    "AI travel advisor startup 2025 2026",
    "AI-powered luxury travel planning company",
    "automated travel agent booking AI",
    "MCP model context protocol travel integration",
    "AI concierge cruise booking platform",
    "travel AI advisor competitor landscape",
    "luxury travel technology disruption AI agents",
    "agentic AI booking system travel",
]


# ============================================================================
# COMPETITOR SEARCH
# ============================================================================

def search_competitors() -> List[Dict[str, Any]]:
    """Search for AI travel advisor competitors using Claude Opus CLI.

    Returns list of competitor dicts: name, url, description, funding_if_known.
    """

    all_results = []

    system_prompt = """You are a competitive intelligence analyst for a luxury AI-powered travel agency.
Search for and identify AI travel advisor companies, startups, and platforms.

For each competitor found, return a JSON array of objects:
[
    {
        "name": "Company Name",
        "url": "https://example.com",
        "description": "Brief description of what they do",
        "funding_if_known": "$10M Series A" or "Unknown"
    }
]

Focus on:
- AI-first travel planning companies
- Agentic booking systems
- Companies using MCP or similar AI tool protocols for travel
- Luxury travel tech platforms
- AI concierge services

Return ONLY the JSON array. No explanation text."""

    for query in SEARCH_QUERIES:
        try:
            raw = _call_claude_cli(system_prompt, query, max_tokens=800)

            # Extract JSON array from response
            json_match = re.search(r'\[.*\]', raw, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                if isinstance(parsed, list):
                    all_results.extend(parsed)
        except Exception as e:
            logger.warning(f"Search query failed '{query[:40]}...': {e}")
            continue

    # Deduplicate by company name (case-insensitive)
    seen = set()
    deduped = []
    for r in all_results:
        name_key = r.get("name", "").strip().lower()
        if name_key and name_key not in seen:
            seen.add(name_key)
            deduped.append(r)

    _log_surveillance("search", f"Found {len(deduped)} unique competitors from {len(SEARCH_QUERIES)} queries")
    return deduped


# ============================================================================
# COMPETITOR PROFILING — A2 (Dembe) Analysis
# ============================================================================

def profile_competitor(name: str, url: str) -> Dict[str, Any]:
    """Deep-dive profile of a single competitor using A2 (Dembe) persona.

    Returns: capabilities, pricing_model, target_market, ai_technology,
    mcp_support, threat_level (1-5).
    """
    from thunderbird_personas import build_system_prompt

    a2_prompt = build_system_prompt("A2")

    query = f"""Conduct a competitive intelligence assessment of this AI travel company:

Company: {name}
URL: {url}

Analyze and return ONLY a JSON object with these fields:
{{
    "name": "{name}",
    "url": "{url}",
    "capabilities": "What they offer — list key features",
    "pricing_model": "How they charge (subscription, commission, freemium, etc.) or 'Unknown'",
    "target_market": "Who they serve (luxury, budget, corporate, etc.)",
    "ai_technology": "What AI/LLM tech they use if known, or 'Unknown'",
    "mcp_support": true/false or "Unknown",
    "threat_level": 1-5 (1=minimal overlap, 5=direct competitor to D2M luxury AI travel),
    "assessment": "2-3 sentence threat assessment from A2 perspective"
}}

Return ONLY the JSON object."""

    try:
        raw = _call_claude_cli(a2_prompt, query, max_tokens=600)

        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            profile = json.loads(json_match.group())
            profile["profiled_at"] = datetime.now(timezone.utc).isoformat()
            return profile
        else:
            return {
                "name": name, "url": url,
                "error": "Could not parse profile response",
                "raw_response": raw[:500],
            }

    except Exception as e:
        logger.error(f"Profile failed for {name}: {e}")
        return {"name": name, "url": url, "error": str(e)}


# ============================================================================
# LANDSCAPE REPORT
# ============================================================================

def compile_landscape_report(competitors: List[Dict[str, Any]]) -> str:
    """Generate a formatted competitive landscape report.

    Args:
        competitors: List of profiled competitor dicts.

    Returns:
        Formatted report string with threat matrix, categories, and recommendations.
    """
    from thunderbird_personas import build_system_prompt

    a5_prompt = build_system_prompt("A5")

    # Build threat matrix
    threat_lines = []
    direct = []
    adjacent = []
    platform = []

    for c in competitors:
        name = c.get("name", "Unknown")
        threat = c.get("threat_level", 0)
        caps = c.get("capabilities", "Unknown")

        threat_bar = "*" * int(threat) if isinstance(threat, (int, float)) else "?"
        threat_lines.append(f"  {name:<30} [{threat_bar:<5}] {str(caps)[:60]}")

        # Categorize
        try:
            t = int(threat) if threat else 0
        except (ValueError, TypeError):
            t = 0

        if t >= 4:
            direct.append(name)
        elif t >= 2:
            adjacent.append(name)
        else:
            platform.append(name)

    # Use A5 (Castillo) for strategic analysis
    competitor_summary = json.dumps(competitors, indent=2, default=str)[:3000]

    strategy_query = f"""Based on this competitive intelligence, provide:
1. D2M's key advantages over these competitors
2. D2M's vulnerabilities they could exploit
3. Top 3 recommended actions

Competitor data:
{competitor_summary}

Be concise — bullet points, not paragraphs."""

    try:
        strategic_analysis = _call_claude_cli(a5_prompt, strategy_query, max_tokens=600)
    except Exception as e:
        strategic_analysis = f"(Strategic analysis unavailable: {e})"

    # Assemble report
    report = f"""
================================================================================
COMPETITIVE LANDSCAPE REPORT — Dreams2Memories Travel
Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
Competitors Analyzed: {len(competitors)}
================================================================================

THREAT MATRIX
{'-' * 70}
  Company                        Level  Capabilities
{chr(10).join(threat_lines) if threat_lines else '  (No competitors profiled)'}

CATEGORY BREAKDOWN
{'-' * 70}
  Direct Competitors (Threat 4-5): {', '.join(direct) if direct else 'None identified'}
  Adjacent Players (Threat 2-3):   {', '.join(adjacent) if adjacent else 'None identified'}
  Platform Threats (Threat 0-1):   {', '.join(platform) if platform else 'None identified'}

STRATEGIC ANALYSIS (A5-CASTILLO)
{'-' * 70}
{strategic_analysis}

================================================================================
Report compiled by Thunderbird OS Competitive Surveillance Module
Classification: INTERNAL USE ONLY
================================================================================
"""

    _log_surveillance("report", f"Landscape report compiled — {len(competitors)} competitors")
    return report


# ============================================================================
# INTEL STORAGE — Google Sheets + Persona Memory
# ============================================================================

def store_intel(data: List[Dict[str, Any]]):
    """Write competitor intel to Intel_Log tab in Google Sheets and A2 persona memory.

    Args:
        data: List of competitor profile dicts.
    """
    from thunderbird_personas import store_persona_memory

    # Store in A2 persona memory
    for competitor in data:
        name = competitor.get("name", "Unknown")
        threat = competitor.get("threat_level", "?")
        caps = str(competitor.get("capabilities", ""))[:200]
        memory_content = f"Competitor: {name} | Threat: {threat}/5 | {caps}"
        try:
            store_persona_memory("A2", "research", memory_content)
        except Exception as e:
            logger.warning(f"Failed to store A2 memory for {name}: {e}")

    # Write to Google Sheets Intel_Log
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        creds_file = THUNDERBIRD_DIR / "credentials.json"
        if not creds_file.exists():
            logger.warning("credentials.json not found — skipping Sheets write")
            return

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(str(creds_file), scopes=scopes)
        gc = gspread.authorize(creds)
        ws = gc.open_by_key(SPREADSHEET_ID).worksheet("Intel_Log")

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        rows = []
        for c in data:
            rows.append([
                ts,
                "Competitive Surveillance",
                c.get("name", "Unknown"),
                str(c.get("threat_level", "")),
                str(c.get("capabilities", ""))[:200],
                c.get("url", ""),
                c.get("assessment", "")[:200] if c.get("assessment") else "",
            ])

        if rows:
            ws.append_rows(rows, value_input_option="RAW")
            logger.info(f"Wrote {len(rows)} competitor entries to Intel_Log")

    except Exception as e:
        logger.error(f"Sheets write failed: {e}")


# ============================================================================
# FULL SURVEILLANCE SPRINT
# ============================================================================

def run_surveillance_sprint() -> Dict[str, Any]:
    """Full competitive surveillance pipeline.

    1. Search for competitors
    2. Profile top 10
    3. Compile landscape report
    4. Store intel
    5. Create email draft with report

    Returns summary dict.
    """
    _log_surveillance("sprint_start", "Beginning competitive surveillance sprint")

    # Step 1: Search
    competitors = search_competitors()
    if not competitors:
        _log_surveillance("sprint_end", "No competitors found — sprint aborted")
        return {"status": "no_results", "competitors_found": 0}

    # Step 2: Profile top 10
    to_profile = competitors[:10]
    profiled = []
    for comp in to_profile:
        name = comp.get("name", "")
        url = comp.get("url", "")
        if name:
            profile = profile_competitor(name, url)
            # Merge search data with profile
            merged = {**comp, **profile}
            profiled.append(merged)

    # Step 3: Compile report
    report = compile_landscape_report(profiled)

    # Step 4: Store intel
    store_intel(profiled)

    # Step 5: Full send to Commander inbox (SO 27 MAR 2026 — internal reports are full sends)
    try:
        from core.email.thunderbird_gmail import gmail_send_from_wing
        gmail_send_from_wing(
            to="johnloucks3@gmail.com",
            subject=f"Competitive Surveillance: Travel AI — {datetime.now().strftime('%B %-d, %Y')}",
            body=report,
            persona_id="COS",
        )
        email_status = "sent"
    except Exception as e:
        logger.warning(f"Email send failed: {e}")
        email_status = f"failed: {e}"

    # Save report to file
    try:
        report_dir = THUNDERBIRD_DIR / "output" / "competitive_intel"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / f"surveillance_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        report_file.write_text(report, encoding="utf-8")
    except Exception as e:
        logger.warning(f"Report file save failed: {e}")

    _log_surveillance("sprint_end", f"Sprint complete — {len(profiled)} competitors profiled")

    return {
        "status": "success",
        "competitors_found": len(competitors),
        "competitors_profiled": len(profiled),
        "email_status": email_status,
        "report_preview": report[:500],
    }


# ============================================================================
# LOGGING
# ============================================================================

def _log_surveillance(action: str, detail: str):
    """Append to surveillance log."""
    try:
        SURVEILLANCE_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        line = f"[{ts}] {action} | {detail}\n"
        with open(SURVEILLANCE_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        logger.warning(f"Surveillance log write failed: {e}")


# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================

def register_surveillance_tools(mcp: FastMCP):
    """Register competitive surveillance tools with the MCP server."""

    @mcp.tool(
        name="run_competitive_surveillance",
        annotations={"title": "Run Competitive Surveillance Sprint", "readOnlyHint": False},
    )
    async def run_competitive_surveillance() -> str:
        """Run a full competitive surveillance sprint: search, profile, report, store.

        Searches for AI travel advisor competitors, profiles the top 10,
        compiles a threat matrix and landscape report, stores intel to
        Google Sheets and A2 persona memory, and creates an email draft
        with the report for Commander review.
        """
        result = run_surveillance_sprint()
        return json.dumps(result, indent=2, default=str)

    logger.info("Competitive surveillance tools registered (run_competitive_surveillance)")
