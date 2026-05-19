"""
Thunderbird Trip Architect — Autonomous Trip Design Pipeline
=============================================================

MVP for Thunderbird OS Item #5: Flagship build.

Pipeline: Parse client inquiry → Research destinations (A2 Dembe) →
          Price options (with markup) → Render proposals (EXEC voice) →
          Draft email to Commander for approval.

Graceful degradation: works even if hotel/flight APIs are unavailable.
Falls back to persona-estimated pricing when live data isn't available.

Usage:
    from thunderbird_trip_architect import architect_pipeline, parse_client_inquiry

    # Full pipeline
    result = architect_pipeline(
        "We're 4 couples looking for a Mediterranean cruise in October, budget $8k/person, love history and wine",
        client_name="Furlow Party",
        client_email="furlow@example.com",
    )

    # Just parse
    parsed = parse_client_inquiry("7-night Alaska cruise for 2, late July, $12k total, adventure lovers")
"""

import json
import logging
import os
import re
import subprocess
import time
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

# ── Thunderbird imports ──
from thunderbird_personas import (
    call_persona,
    store_persona_memory,
    inject_memory_context,
    build_system_prompt,
    resolve_id,
)
from thunderbird_model_router import route_call, MODEL_TAGS, _call_groq, GROQ_MODELS

# Gmail — import with fallback so module loads even without OAuth token
try:
    from thunderbird_gmail import (
        gmail_send_with_approval,
        gmail_send_as_persona,
        PERSONA_DISPLAY_NAMES,
    )
except Exception:
    gmail_send_with_approval = None
    gmail_send_as_persona = None
    PERSONA_DISPLAY_NAMES = {}

# ── Logging ──
LOG_DIR = Path.home() / "Thunderbird" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "trip_architect.log"

logger = logging.getLogger("trip_architect")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s — %(message)s"))
    logger.addHandler(fh)

# ── Session persistence ──
SESSION_DIR = Path.home() / "Thunderbird" / "architect_sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

# ── Commander email ──
COMMANDER_EMAIL = "johnloucks3@gmail.com"

# ── Currency helpers (mirrors thunderbird_flight_search.py) ──
EUR_TO_USD = 1.09
STANDARD_MARKUP = 0.25
PREMIUM_MARKUP = 0.22


# ==========================================================================
# STEP 1: SESSION STATE TRACKING
# ==========================================================================

@dataclass
class ArchitectSession:
    """Persistent session state for a Trip Architect pipeline run.

    Tracks progress across all phases so the pipeline can resume after
    Commander review/approval and survive process restarts.
    """
    session_id: str = ""
    client_name: str = ""
    client_email: str = ""
    inquiry: str = ""
    created_at: str = ""
    updated_at: str = ""

    # Pipeline phase tracking
    phase: str = "new"  # new -> parsed -> researched -> priced -> rendered -> staff_paper -> awaiting_approval -> approved -> proposal_sent -> complete
    steps_completed: Dict[str, str] = field(default_factory=dict)

    # Data from each phase
    parsed: Dict = field(default_factory=dict)
    research_options: List[Dict] = field(default_factory=list)
    priced_options: List[Dict] = field(default_factory=list)
    staff_paper: str = ""
    commander_decision: str = ""  # SEND 1/2/3, REVISE, HOLD
    selected_option: int = 0
    rendered_proposal: str = ""
    proposal_pdf_path: str = ""
    draft_id: str = ""

    # Client context (Step 2)
    client_context: Dict = field(default_factory=dict)

    # Consultation results (Step 5)
    a3_logistics: str = ""
    a9_finance: str = ""

    # Model tracking
    model_tags_used: List[str] = field(default_factory=list)

    def save(self):
        """Persist session to JSON file."""
        self.updated_at = datetime.now(timezone.utc).isoformat()
        path = SESSION_DIR / f"{self.session_id}.json"
        path.write_text(json.dumps(asdict(self), indent=2, default=str), encoding="utf-8")
        logger.info("Session saved: %s (phase: %s)", self.session_id, self.phase)

    @classmethod
    def load(cls, session_id: str) -> "ArchitectSession":
        """Load a session from disk."""
        path = SESSION_DIR / f"{session_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"No session found: {session_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        session = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        logger.info("Session loaded: %s (phase: %s)", session.session_id, session.phase)
        return session

    @classmethod
    def create(cls, inquiry: str, client_name: str = "", client_email: str = "") -> "ArchitectSession":
        """Create a new session with a unique ID."""
        now = datetime.now(timezone.utc)
        session_id = f"arch_{now.strftime('%Y%m%d_%H%M%S')}_{client_name.replace(' ', '_')[:20] or 'unknown'}"
        session = cls(
            session_id=session_id,
            client_name=client_name,
            client_email=client_email,
            inquiry=inquiry,
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            phase="new",
        )
        session.save()
        return session

    @classmethod
    def list_sessions(cls, active_only: bool = True) -> List[Dict]:
        """List all sessions, optionally filtering to active ones."""
        sessions = []
        for f in sorted(SESSION_DIR.glob("arch_*.json"), reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if active_only and data.get("phase") == "complete":
                    continue
                sessions.append({
                    "session_id": data.get("session_id"),
                    "client_name": data.get("client_name"),
                    "phase": data.get("phase"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                })
            except Exception:
                continue
        return sessions


# ==========================================================================
# STEP 2: CLIENT CONTEXT LOADER
# ==========================================================================

def _load_client_context(client_name: str = "", client_email: str = "") -> Dict:
    """Build rich client context from 3 sources (mirrors email_intel pattern).

    Sources:
    1. Registry_Clients tab (Google Sheets) — demographics, preferences
    2. Dossiers directory — trip history, notes, action items
    3. Booking Master tab — active bookings, payment status

    Returns a merged context dict. Fails gracefully if sources are unavailable.
    """
    context = {
        "client_name": client_name,
        "client_email": client_email,
        "registry": {},
        "dossier_summary": "",
        "active_bookings": [],
        "known_preferences": [],
    }

    # ── Source 1: Registry_Clients tab ──
    try:
        from thunderbird_drive import sheets_service
        SPREADSHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
        result = sheets_service().spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="Registry_Clients!A1:Z200",
        ).execute()
        rows = result.get("values", [])
        if rows:
            headers = [h.lower().strip() for h in rows[0]]
            for row in rows[1:]:
                row_dict = dict(zip(headers, row + [""] * (len(headers) - len(row))))
                name = row_dict.get("client name", "") or row_dict.get("name", "")
                email = row_dict.get("email", "")
                if (client_name and client_name.lower() in name.lower()) or \
                   (client_email and client_email.lower() == email.lower()):
                    context["registry"] = row_dict
                    logger.info("Client found in Registry_Clients: %s", name)
                    break
    except Exception as e:
        logger.warning("Registry_Clients lookup failed: %s", e)

    # ── Source 2: Dossier files ──
    try:
        dossier_dir = Path.home() / "Thunderbird" / "Dossiers"
        if dossier_dir.exists() and client_name:
            # Try to match dossier by client name
            search_name = client_name.lower().replace(" ", "_")
            for dossier_file in dossier_dir.glob("*.md"):
                if search_name in dossier_file.stem.lower() or \
                   client_name.split()[0].lower() in dossier_file.stem.lower():
                    content = dossier_file.read_text(encoding="utf-8")
                    # Take first 2000 chars as summary
                    context["dossier_summary"] = content[:2000]
                    logger.info("Dossier found: %s", dossier_file.name)
                    break
    except Exception as e:
        logger.warning("Dossier lookup failed: %s", e)

    # ── Source 3: Booking Master ──
    try:
        from thunderbird_drive import sheets_service
        SPREADSHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
        result = sheets_service().spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="Booking Master!A1:Z200",
        ).execute()
        rows = result.get("values", [])
        if rows:
            headers = [h.lower().strip() for h in rows[0]]
            for row in rows[1:]:
                row_dict = dict(zip(headers, row + [""] * (len(headers) - len(row))))
                name = row_dict.get("client name", "") or row_dict.get("client", "")
                if client_name and client_name.lower() in name.lower():
                    context["active_bookings"].append(row_dict)
            if context["active_bookings"]:
                logger.info("Found %d bookings for %s", len(context["active_bookings"]), client_name)
    except Exception as e:
        logger.warning("Booking Master lookup failed: %s", e)

    # ── Derive preferences from history ──
    if context["dossier_summary"]:
        prefs = []
        lower = context["dossier_summary"].lower()
        for kw in ["wine", "history", "food", "adventure", "spa", "culture", "beach",
                    "luxury", "excursion", "photography", "diving", "golf"]:
            if kw in lower:
                prefs.append(kw)
        context["known_preferences"] = prefs

    return context


def _format_client_brief(ctx: Dict) -> str:
    """Format client context into a brief for persona prompts."""
    parts = [f"CLIENT: {ctx.get('client_name', 'Unknown')}"]

    reg = ctx.get("registry", {})
    if reg:
        parts.append(f"  Registry: {', '.join(f'{k}={v}' for k, v in reg.items() if v and k not in ('email',))}")

    if ctx.get("active_bookings"):
        parts.append(f"  Active bookings: {len(ctx['active_bookings'])}")
        for b in ctx["active_bookings"][:3]:
            parts.append(f"    - {b.get('supplier', '?')}: {b.get('dates', '?')} ({b.get('status', '?')})")

    if ctx.get("known_preferences"):
        parts.append(f"  Known preferences: {', '.join(ctx['known_preferences'])}")

    if ctx.get("dossier_summary"):
        parts.append(f"  Dossier excerpt: {ctx['dossier_summary'][:300]}...")

    return "\n".join(parts)


def fmt_usd(amount) -> str:
    """Format a numeric amount as USD string: $X,XXX.XX"""
    try:
        val = float(amount)
        return f"${val:,.2f}"
    except (ValueError, TypeError):
        return str(amount)


def _apply_markup(net_amount: float, currency: str = "USD",
                  markup: float = STANDARD_MARKUP) -> dict:
    """Convert to USD if needed and apply commission markup."""
    usd_net = net_amount
    if currency.upper() == "EUR":
        usd_net = net_amount * EUR_TO_USD

    client_price = usd_net * (1 + markup)
    commission = client_price - usd_net
    return {
        "net_usd": round(usd_net, 2),
        "markup_pct": f"{markup * 100:.0f}%",
        "client_price": round(client_price, 2),
        "commission": round(commission, 2),
        "client_price_fmt": fmt_usd(client_price),
        "commission_fmt": fmt_usd(commission),
    }


# ==========================================================================
# 1. PARSE CLIENT INQUIRY
# ==========================================================================

_PARSE_SYSTEM_PROMPT = """You are a travel inquiry parser for Dreams2Memories Travel, LLC.
Extract structured data from a client's travel inquiry. Return ONLY valid JSON — no markdown, no explanation.

JSON schema:
{
  "destination": "string or null — where they want to go",
  "destinations_flexible": true/false — whether they're open to alternatives,
  "departure_date": "YYYY-MM-DD or null",
  "return_date": "YYYY-MM-DD or null",
  "date_flexible": true/false,
  "duration_nights": integer or null,
  "budget_total": number or null — total budget in USD,
  "budget_per_person": number or null — per-person budget in USD,
  "party_size": integer or null,
  "party_description": "string or null — e.g. '4 couples', 'family with 2 kids'",
  "travel_type": "cruise|hotel|tour|mixed|unknown",
  "cruise_line_preference": "string or null",
  "cabin_type": "string or null — e.g. 'balcony', 'suite', 'ocean view'",
  "travel_style": "luxury|premium|value|unknown",
  "preferences": ["list of interest keywords: history, wine, food, adventure, relaxation, culture, beaches, nightlife, etc."],
  "special_requirements": "string or null — mobility, dietary, anniversary, etc.",
  "raw_summary": "1-sentence summary of the inquiry"
}

Rules:
- If budget is stated as total, populate budget_total. If per-person, populate budget_per_person.
- Infer party_size from context if not explicit (e.g. "4 couples" = 8).
- If travel_style not stated, infer from budget and language cues.
- Set destinations_flexible=true if they say things like "somewhere in..." or "open to suggestions".
- Always populate raw_summary."""


def parse_client_inquiry(text: str) -> dict:
    """Extract structured travel requirements from a free-text client inquiry.

    Uses Claude Opus via CLI for NLP extraction. Returns a structured dict.
    """
    logger.info("Parsing client inquiry: %s", text[:120])

    try:
        response = _call_groq(
            _PARSE_SYSTEM_PROMPT,
            text,
            model="fast",
            max_tokens=600,
            temperature=0.2,
        )

        # Strip any markdown code fences the model might add
        cleaned = response.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        parsed = json.loads(cleaned)
        logger.info("Parsed inquiry: %s", json.dumps(parsed, indent=2))
        return parsed

    except json.JSONDecodeError as e:
        logger.error("JSON parse failed on Claude response: %s\nRaw: %s", e, response[:500])
        # Return a minimal dict so the pipeline can still attempt to proceed
        return {
            "destination": None,
            "raw_summary": text[:200],
            "parse_error": str(e),
        }
    except Exception as e:
        logger.error("parse_client_inquiry failed: %s", traceback.format_exc())
        return {
            "destination": None,
            "raw_summary": text[:200],
            "parse_error": str(e),
        }


# ==========================================================================
# 2. RESEARCH DESTINATION (A2 — Dembe)
# ==========================================================================

def _gather_intel(parsed: dict) -> str:
    """Gather supplemental intel from ship_intel and world_intel for A2's research.

    Returns a text block with relevant intel to inject into A2's prompt.
    """
    intel_parts = []

    # Ship intel — if travel type is cruise
    if parsed.get("travel_type") in ("cruise", "mixed", "unknown"):
        try:
            from thunderbird_ship_intel import get_ship_intelligence
            dest = parsed.get("destination", "")
            if dest:
                ship_data = get_ship_intelligence(dest)
                if ship_data and not ship_data.get("error"):
                    intel_parts.append("SHIP INTELLIGENCE:\n" + json.dumps(ship_data, indent=2, default=str)[:1500])
                    logger.info("Ship intel gathered for %s", dest)
        except (ImportError, Exception) as e:
            logger.info("Ship intel not available: %s", e)

    # World intel — travel advisories, destination news
    try:
        from thunderbird_world_intel import get_travel_advisories
        dest = parsed.get("destination", "")
        if dest:
            advisories = get_travel_advisories(dest)
            if advisories and not advisories.get("error"):
                intel_parts.append("TRAVEL ADVISORIES:\n" + json.dumps(advisories, indent=2, default=str)[:800])
                logger.info("World intel gathered for %s", dest)
    except (ImportError, Exception) as e:
        logger.info("World intel not available: %s", e)

    return "\n\n".join(intel_parts) if intel_parts else ""


def research_destination(parsed: dict, client_context: Dict = None) -> List[dict]:
    """Call A2 (Dembe) persona with parsed requirements to get 3 distinct options.

    Enhanced with ship/world intel and client context injection.
    Each option: name, description, why_it_fits, estimated_price_range.
    """
    logger.info("Researching destinations for: %s", parsed.get("raw_summary", "unknown"))

    # Gather supplemental intel (Step 3)
    supplemental = _gather_intel(parsed)

    # Build a focused research brief for Dembe
    dest = parsed.get("destination") or "open — suggest best fits"
    budget_str = ""
    if parsed.get("budget_per_person"):
        budget_str = f"Budget: {fmt_usd(parsed['budget_per_person'])} per person"
    elif parsed.get("budget_total"):
        budget_str = f"Budget: {fmt_usd(parsed['budget_total'])} total"
    else:
        budget_str = "Budget: not specified"

    party = parsed.get("party_description") or f"{parsed.get('party_size', 'unknown')} travelers"
    prefs = ", ".join(parsed.get("preferences", [])) or "not specified"
    travel_type = parsed.get("travel_type", "unknown")
    style = parsed.get("travel_style", "unknown")
    dates = ""
    if parsed.get("departure_date"):
        dates = f"Dates: {parsed['departure_date']}"
        if parsed.get("return_date"):
            dates += f" to {parsed['return_date']}"
    elif parsed.get("duration_nights"):
        dates = f"Duration: {parsed['duration_nights']} nights"

    cabin = parsed.get("cabin_type") or "not specified"
    cruise_pref = parsed.get("cruise_line_preference") or "open"
    special = parsed.get("special_requirements") or "none"

    query = f"""COLLECTION REQUIREMENT — Trip Architect Research

Client profile:
- Destination interest: {dest}
- {budget_str}
- Party: {party}
- Travel type: {travel_type}
- Style: {style}
- Interests: {prefs}
- {dates}
- Cabin preference: {cabin}
- Cruise line preference: {cruise_pref}
- Special requirements: {special}

TASK: Provide exactly 3 distinct options. For each option, return ONLY valid JSON in this format:
[
  {{
    "name": "Option name — destination or cruise/property name",
    "description": "2-3 sentence description",
    "why_it_fits": "Why this matches the client's requirements",
    "travel_type": "cruise|hotel|tour|mixed",
    "estimated_price_pp": estimated price per person in USD (number),
    "estimated_total": estimated total price in USD (number),
    "confidence": "high|moderate|low",
    "key_selling_points": ["point1", "point2", "point3"],
    "potential_concerns": ["concern1"]
  }},
  ...
]

Make each option genuinely different — different destinations, ships, or property styles.
Base estimates on your knowledge of luxury travel pricing. Be realistic, not optimistic."""

    # Inject supplemental intel (Step 3)
    if supplemental:
        query += f"\n\nSUPPLEMENTAL INTELLIGENCE:\n{supplemental}"

    # Inject client context (Step 2)
    if client_context:
        brief = _format_client_brief(client_context)
        if brief:
            query += f"\n\nCLIENT BACKGROUND (use to tailor recommendations):\n{brief}"

    try:
        result = call_persona("A2", query, max_tokens=1200)

        if "error" in result:
            logger.error("A2 research call failed: %s", result["error"])
            return _fallback_research(parsed)

        answer = result.get("answer", "")

        # Extract JSON from the response (Dembe might wrap it in commentary)
        json_match = re.search(r'\[.*\]', answer, re.DOTALL)
        if json_match:
            options = json.loads(json_match.group())
            logger.info("A2 returned %d research options", len(options))
            return options
        else:
            logger.warning("Could not extract JSON from A2 response, using raw text")
            return _fallback_research(parsed, dembe_text=answer)

    except json.JSONDecodeError as e:
        logger.error("JSON parse failed on A2 response: %s", e)
        return _fallback_research(parsed)
    except Exception as e:
        logger.error("research_destination failed: %s", traceback.format_exc())
        return _fallback_research(parsed)


def _fallback_research(parsed: dict, dembe_text: str = None) -> List[dict]:
    """Generate fallback research options when A2's structured response fails.

    Creates generic options based on the parsed inquiry so the pipeline continues.
    """
    dest = parsed.get("destination") or "Mediterranean"
    budget_pp = parsed.get("budget_per_person") or parsed.get("budget_total", 5000)
    if isinstance(budget_pp, (int, float)) and budget_pp > 20000:
        # Likely a total budget, estimate per-person
        party = parsed.get("party_size") or 2
        budget_pp = budget_pp / party

    options = [
        {
            "name": f"{dest} — Option A (Premium)",
            "description": f"Premium experience in {dest} matching client preferences.",
            "why_it_fits": "Aligns with stated budget and interests.",
            "travel_type": parsed.get("travel_type", "mixed"),
            "estimated_price_pp": round(float(budget_pp) * 0.9, 2),
            "estimated_total": None,
            "confidence": "low",
            "key_selling_points": ["Matches budget", "Fits travel style"],
            "potential_concerns": ["Pricing is estimated — needs live verification"],
            "fallback": True,
        },
        {
            "name": f"{dest} — Option B (Value)",
            "description": f"Value-oriented alternative in {dest}.",
            "why_it_fits": "Under budget with quality experience.",
            "travel_type": parsed.get("travel_type", "mixed"),
            "estimated_price_pp": round(float(budget_pp) * 0.7, 2),
            "estimated_total": None,
            "confidence": "low",
            "key_selling_points": ["Budget-friendly", "Solid experience"],
            "potential_concerns": ["Pricing is estimated"],
            "fallback": True,
        },
        {
            "name": f"Alternative Destination — Option C",
            "description": "Alternative destination for comparison.",
            "why_it_fits": "Provides contrast and client choice.",
            "travel_type": parsed.get("travel_type", "mixed"),
            "estimated_price_pp": round(float(budget_pp) * 0.85, 2),
            "estimated_total": None,
            "confidence": "low",
            "key_selling_points": ["Different perspective", "May surprise"],
            "potential_concerns": ["Needs Commander input on destination"],
            "fallback": True,
        },
    ]

    if dembe_text:
        options[0]["dembe_raw_analysis"] = dembe_text[:500]

    return options


# ==========================================================================
# STEP 5: STAFF CONSULTATIONS (A3 Logistics + A9 Finance)
# ==========================================================================

def _consult_a3_logistics(priced_options: List[dict], parsed: dict, client_context: Dict = None) -> str:
    """A3 (Moreau) reviews logistics feasibility — connections, timing, operational risk."""
    logger.info("Consulting A3 (Moreau) on logistics")

    options_brief = ""
    for i, opt in enumerate(priced_options, 1):
        options_brief += f"\nOption {i}: {opt.get('name', '?')}\n"
        options_brief += f"  Type: {opt.get('travel_type', '?')}\n"
        pricing = opt.get("pricing", {})
        options_brief += f"  Price: {pricing.get('client_total', 'TBD')}\n"

    dates = ""
    if parsed.get("departure_date"):
        dates = f"Departure: {parsed['departure_date']}"
        if parsed.get("return_date"):
            dates += f" — Return: {parsed['return_date']}"

    client_brief = ""
    if client_context:
        client_brief = _format_client_brief(client_context)

    query = f"""OPERATIONS ASSESSMENT — Trip Architect

{options_brief}

Party: {parsed.get('party_description', f"{parsed.get('party_size', '?')} travelers")}
{dates}
Special requirements: {parsed.get('special_requirements', 'none')}

{client_brief}

TASK: Assess each option from an OPERATIONS perspective. For each:
1. Connection feasibility — flight routing, transfer logistics, layover risks
2. Timing — is the date realistic for booking? Any seasonal concerns?
3. Operational risks — visa requirements, health advisories, supplier reliability
4. Client-specific concerns based on their profile/history

Keep it concise — 3-5 bullets per option. Flag any RED FLAGS prominently."""

    try:
        result = call_persona("A3", query, max_tokens=800)
        answer = result.get("answer", "A3 assessment unavailable")
        logger.info("A3 logistics assessment complete")
        return answer
    except Exception as e:
        logger.error("A3 consultation failed: %s", e)
        return f"A3 logistics assessment unavailable: {e}"


def _consult_a9_finance(priced_options: List[dict], parsed: dict) -> str:
    """A9 (Harlan) reviews financial viability — margins, risk, commission optimization."""
    logger.info("Consulting A9 (Harlan) on finances")

    options_brief = ""
    total_potential = 0.0
    for i, opt in enumerate(priced_options, 1):
        pricing = opt.get("pricing", {})
        raw = pricing.get("raw", {})
        comm = raw.get("commission_total", 0)
        total_potential += comm
        options_brief += f"\nOption {i}: {opt.get('name', '?')}\n"
        options_brief += f"  Net pp: {pricing.get('net_per_person', 'TBD')}\n"
        options_brief += f"  Client pp: {pricing.get('client_per_person', 'TBD')}\n"
        options_brief += f"  Client total: {pricing.get('client_total', 'TBD')}\n"
        options_brief += f"  Commission total: {pricing.get('commission_total', 'TBD')}\n"
        options_brief += f"  Markup: {pricing.get('markup', 'TBD')}\n"
        options_brief += f"  Source: {pricing.get('source', 'unknown')}\n"

    query = f"""FINANCIAL ASSESSMENT — Trip Architect

{options_brief}

Total potential commission across all options: {fmt_usd(total_potential)}
Party size: {parsed.get('party_size', '?')}
Stated budget: {fmt_usd(parsed.get('budget_per_person') or parsed.get('budget_total', 0))} {'per person' if parsed.get('budget_per_person') else 'total'}

TASK: Assess each option from a FINANCIAL perspective:
1. Is the markup appropriate? (25% standard, 22% premium/SLH)
2. Commission viability — is this worth pursuing? Hours-to-revenue ratio?
3. Budget alignment — are we over/under the client's stated budget?
4. Risk factors — cancellation exposure, payment terms, currency risk
5. Recommendation — which option maximizes D2M revenue while staying client-appropriate?

Be blunt. Numbers first. If an option is charity, say so."""

    try:
        result = call_persona("A9", query, max_tokens=800)
        answer = result.get("answer", "A9 assessment unavailable")
        logger.info("A9 finance assessment complete")
        return answer
    except Exception as e:
        logger.error("A9 consultation failed: %s", e)
        return f"A9 financial assessment unavailable: {e}"


# ==========================================================================
# STEP 6: EARA STAFF PAPER RENDERER
# ==========================================================================

def _render_eara_staff_paper(
    session: "ArchitectSession",
    priced_options: List[dict],
    parsed: dict,
    a3_assessment: str,
    a9_assessment: str,
    client_context: Dict = None,
) -> str:
    """Render a full EARA Constitution staff paper for Commander review.

    Format: ISSUE / DISCUSSION / OPTIONS / ACTIONS I RECOMMEND TAKING
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    client = session.client_name or "Unknown Client"

    lines = []
    lines.append("=" * 70)
    lines.append("STAFF PAPER — TRIP ARCHITECT")
    lines.append(f"Classification: INTERNAL — Commander Eyes Only")
    lines.append(f"Date: {now}")
    lines.append(f"Session: {session.session_id}")
    lines.append(f"Prepared by: COS Hale, with A2 (Research), A3 (Ops), A9 (Finance)")
    lines.append("=" * 70)
    lines.append("")

    # ── ISSUE ──
    lines.append("I. ISSUE")
    lines.append("-" * 40)
    lines.append(f"Trip design request from {client}.")
    lines.append(f"Inquiry: {parsed.get('raw_summary', session.inquiry[:200])}")
    party = parsed.get("party_description") or f"{parsed.get('party_size', '?')} travelers"
    lines.append(f"Party: {party}")
    budget = ""
    if parsed.get("budget_per_person"):
        budget = f"{fmt_usd(parsed['budget_per_person'])} per person"
    elif parsed.get("budget_total"):
        budget = f"{fmt_usd(parsed['budget_total'])} total"
    if budget:
        lines.append(f"Budget: {budget}")
    lines.append("")

    # ── Client context ──
    if client_context and any(client_context.get(k) for k in ("registry", "dossier_summary", "active_bookings")):
        lines.append("CLIENT BACKGROUND")
        lines.append("-" * 40)
        lines.append(_format_client_brief(client_context))
        lines.append("")

    # ── DISCUSSION ──
    lines.append("II. DISCUSSION")
    lines.append("-" * 40)
    lines.append("")

    # A2 Research results
    lines.append("A. Research Assessment (A2 — Dembe)")
    for i, opt in enumerate(priced_options, 1):
        lines.append(f"\n  Option {i}: {opt.get('name', 'Unnamed')}")
        lines.append(f"  {opt.get('description', '')}")
        if opt.get("why_it_fits"):
            lines.append(f"  Fit: {opt['why_it_fits']}")
        if opt.get("key_selling_points"):
            for sp in opt["key_selling_points"]:
                lines.append(f"    + {sp}")
        if opt.get("potential_concerns"):
            for c in opt["potential_concerns"]:
                lines.append(f"    ! {c}")
        pricing = opt.get("pricing", {})
        if pricing.get("client_per_person"):
            lines.append(f"  Pricing: {pricing['client_per_person']} pp / {pricing.get('client_total', 'TBD')} total")
            lines.append(f"  Commission: {pricing.get('commission_total', 'N/A')} ({pricing.get('markup', '?')} markup)")
            lines.append(f"  Source: {pricing.get('source', 'unknown')}")
            if pricing.get("note"):
                lines.append(f"  Note: {pricing['note']}")
    lines.append("")

    # A3 Operations
    lines.append("B. Operations Assessment (A3 — Moreau)")
    lines.append(a3_assessment)
    lines.append("")

    # A9 Finance
    lines.append("C. Financial Assessment (A9 — Harlan)")
    lines.append(a9_assessment)
    lines.append("")

    # ── OPTIONS ──
    lines.append("III. OPTIONS")
    lines.append("-" * 40)

    total_commission = 0.0
    lines.append(f"\n  {'Option':<12} {'Per Person':<16} {'Total':<16} {'Commission':<16}")
    lines.append(f"  {'─' * 56}")
    for i, opt in enumerate(priced_options, 1):
        pricing = opt.get("pricing", {})
        pp = pricing.get("client_per_person", "TBD")
        total = pricing.get("client_total", "TBD")
        comm = pricing.get("commission_total", "N/A")
        lines.append(f"  Option {i:<4} {pp:<16} {total:<16} {comm:<16}")
        raw = pricing.get("raw", {})
        if raw.get("commission_total"):
            total_commission += raw["commission_total"]

    if total_commission > 0:
        lines.append(f"\n  Total potential D2M commission: {fmt_usd(total_commission)}")
    lines.append("")

    # ── ACTIONS I RECOMMEND TAKING ──
    lines.append("IV. ACTIONS I RECOMMEND TAKING")
    lines.append("-" * 40)
    lines.append("Commander, please reply with one of:")
    lines.append(f"  SEND 1  — Approve Option 1, generate branded proposal for {client}")
    lines.append(f"  SEND 2  — Approve Option 2, generate branded proposal for {client}")
    lines.append(f"  SEND 3  — Approve Option 3, generate branded proposal for {client}")
    lines.append("  REVISE  — Request changes (specify what to adjust)")
    lines.append("  HOLD    — Defer for further research")
    lines.append("")
    lines.append(f"Session ID: {session.session_id}")
    lines.append(f"Resume: architect_approve('{session.session_id}', 'SEND 1')")
    lines.append("")

    return "\n".join(lines)


# ==========================================================================
# 3. PRICE OPTIONS
# ==========================================================================

def price_options(options: List[dict], parsed: dict) -> List[dict]:
    """Attempt to get real pricing for each option. Apply commission markup.

    Tries live APIs first (Hotelbeds, Amadeus), falls back to A2 estimates.
    Applies 25% standard or 22% premium/SLH markup.
    """
    logger.info("Pricing %d options", len(options))

    party_size = parsed.get("party_size") or 2

    priced = []
    for i, opt in enumerate(options):
        logger.info("Pricing option %d: %s", i + 1, opt.get("name", "unnamed"))

        try:
            # Determine markup tier
            style = parsed.get("travel_style", "premium")
            name_lower = (opt.get("name", "") + " " + opt.get("description", "")).lower()
            is_premium = style == "luxury" or any(
                kw in name_lower for kw in ["slh", "small luxury", "regent", "silversea", "seabourn"]
            )
            markup = PREMIUM_MARKUP if is_premium else STANDARD_MARKUP

            # Try to get live pricing
            live_price = _try_live_pricing(opt, parsed)

            if live_price and live_price.get("net_pp"):
                # We got real pricing
                net_pp = live_price["net_pp"]
                currency = live_price.get("currency", "USD")
                pricing = _apply_markup(net_pp, currency, markup)

                opt["pricing"] = {
                    "source": live_price.get("source", "api"),
                    "net_per_person": fmt_usd(pricing["net_usd"]),
                    "client_per_person": pricing["client_price_fmt"],
                    "client_total": fmt_usd(pricing["client_price"] * party_size),
                    "commission_per_person": pricing["commission_fmt"],
                    "commission_total": fmt_usd(pricing["commission"] * party_size),
                    "markup": pricing["markup_pct"],
                    "party_size": party_size,
                    "raw": {
                        "net_pp": pricing["net_usd"],
                        "client_pp": pricing["client_price"],
                        "commission_pp": pricing["commission"],
                        "total": round(pricing["client_price"] * party_size, 2),
                        "commission_total": round(pricing["commission"] * party_size, 2),
                    },
                }
            else:
                # Fall back to A2's estimated pricing
                est_pp = opt.get("estimated_price_pp")
                if est_pp:
                    # A2's estimate is already a client-facing number, so we reverse-engineer net
                    # to show proper commission math
                    client_pp = float(est_pp)
                    net_pp = client_pp / (1 + markup)
                    commission_pp = client_pp - net_pp

                    est_total = opt.get("estimated_total")
                    if not est_total:
                        est_total = client_pp * party_size

                    opt["pricing"] = {
                        "source": "estimate (A2 Dembe)",
                        "net_per_person": fmt_usd(net_pp),
                        "client_per_person": fmt_usd(client_pp),
                        "client_total": fmt_usd(est_total),
                        "commission_per_person": fmt_usd(commission_pp),
                        "commission_total": fmt_usd(commission_pp * party_size),
                        "markup": f"{markup * 100:.0f}%",
                        "party_size": party_size,
                        "note": "Estimated pricing — verify with supplier before quoting client",
                        "raw": {
                            "net_pp": round(net_pp, 2),
                            "client_pp": round(client_pp, 2),
                            "commission_pp": round(commission_pp, 2),
                            "total": round(float(est_total), 2),
                            "commission_total": round(commission_pp * party_size, 2),
                        },
                    }
                else:
                    opt["pricing"] = {
                        "source": "unavailable",
                        "note": "No pricing data — needs manual research",
                    }

        except Exception as e:
            logger.error("Pricing failed for option %d: %s", i + 1, traceback.format_exc())
            opt["pricing"] = {
                "source": "error",
                "error": str(e),
                "note": "Pricing failed — using A2 estimate if available",
            }

        priced.append(opt)

    logger.info("Pricing complete for %d options", len(priced))
    return priced


def _try_live_pricing(option: dict, parsed: dict) -> Optional[dict]:
    """Attempt to get live pricing from APIs. Returns None if unavailable.

    Tries cruise scraping, hotel APIs, and flight APIs based on travel type.
    Catches all errors for graceful degradation.
    """
    travel_type = option.get("travel_type", parsed.get("travel_type", "unknown"))

    # ── Cruise pricing via ship intel scraping ──
    if travel_type == "cruise":
        try:
            from thunderbird_ship_intel import get_ship_intelligence
            name_lower = (option.get("name", "") + " " + option.get("description", "")).lower()
            # Try to extract cruise line from option name
            for line_name in ["regent", "silversea", "viking", "seabourn", "oceania", "cunard", "ponant"]:
                if line_name in name_lower:
                    logger.info("Attempting ship intel pricing for %s", line_name)
                    intel = get_ship_intelligence(line_name)
                    if intel and not intel.get("error"):
                        # Ship intel returns voyage data — try to extract pricing
                        voyages = intel.get("voyages", [])
                        for v in voyages:
                            price = v.get("price_from") or v.get("starting_price")
                            if price:
                                try:
                                    net_pp = float(str(price).replace("$", "").replace(",", ""))
                                    return {"net_pp": net_pp, "currency": "USD", "source": f"ship_intel ({line_name})"}
                                except (ValueError, TypeError):
                                    continue
                    break
        except (ImportError, Exception) as e:
            logger.info("Ship intel pricing not available: %s", e)
        return None

    # ── Hotel pricing via Hotelbeds API ──
    if travel_type in ("hotel", "mixed"):
        try:
            from thunderbird_hotel_search import search_hotels_api
            dest = parsed.get("destination")
            checkin = parsed.get("departure_date")
            checkout = parsed.get("return_date")
            if dest and checkin and checkout:
                logger.info("Attempting Hotelbeds search for %s", dest)
                results = search_hotels_api(
                    destination=dest,
                    check_in=checkin,
                    check_out=checkout,
                    guests=parsed.get("party_size", 2),
                )
                if results and isinstance(results, list) and len(results) > 0:
                    # Take the median-priced result
                    sorted_results = sorted(results, key=lambda h: h.get("price", float("inf")))
                    mid = len(sorted_results) // 2
                    hotel = sorted_results[mid]
                    net_pp = hotel.get("price", 0) / max(parsed.get("party_size", 2), 1)
                    return {"net_pp": net_pp, "currency": hotel.get("currency", "USD"), "source": "Hotelbeds API"}
        except (ImportError, AttributeError) as e:
            logger.info("Hotelbeds API not available: %s", e)
        except Exception as e:
            logger.warning("Hotel pricing attempt failed: %s", e)

    # ── Flight pricing via Amadeus API ──
    if travel_type in ("mixed",):
        try:
            from thunderbird_flight_search import search_flights_api
            origin = parsed.get("origin_airport")
            dest_airport = parsed.get("destination_airport")
            dep_date = parsed.get("departure_date")
            if origin and dest_airport and dep_date:
                logger.info("Attempting Amadeus flight search %s -> %s", origin, dest_airport)
                flights = search_flights_api(origin=origin, destination=dest_airport, date=dep_date)
                if flights and isinstance(flights, list) and len(flights) > 0:
                    cheapest = min(flights, key=lambda f: f.get("price", float("inf")))
                    return {"net_pp": cheapest.get("price", 0), "currency": "USD", "source": "Amadeus API"}
        except (ImportError, AttributeError) as e:
            logger.info("Amadeus API not available: %s", e)
        except Exception as e:
            logger.warning("Flight pricing attempt failed: %s", e)

    return None


# ==========================================================================
# 4. RENDER PROPOSALS
# ==========================================================================

def render_proposals(priced_options: List[dict], parsed: dict) -> str:
    """Format priced options into a clean, readable proposal.

    Uses EXEC voice (Naia Solberg-Vega) for the narrative intro.
    Ends with Commander action prompt.
    """
    logger.info("Rendering proposal with %d options", len(priced_options))

    # Get EXEC to write the intro
    client_desc = parsed.get("party_description") or f"{parsed.get('party_size', 'the')} travelers"
    dest = parsed.get("destination") or "their dream destination"
    prefs = ", ".join(parsed.get("preferences", [])) or "a memorable experience"

    exec_query = f"""Write a 2-3 sentence warm, literate introduction for a travel proposal.
The client: {client_desc} interested in {dest}. They love {prefs}.
Travel style: {parsed.get('travel_style', 'premium')}.
Keep it personal, not corporate. This is the opening of a proposal the Commander will review."""

    try:
        exec_result = call_persona("EXEC", exec_query, max_tokens=300)
        intro = exec_result.get("answer", "").strip()
        # Strip the persona tag and model attribution from the intro
        intro = re.sub(r'^.*?EXEC-SOLBERG-VEGA:\s*', '', intro, flags=re.IGNORECASE)
        intro = re.sub(r'\n\n---\n_.*?_$', '', intro, flags=re.DOTALL)
    except Exception:
        intro = f"Three curated options for {client_desc}, tailored to their love of {prefs}."

    # Build the proposal
    lines = []
    lines.append("=" * 70)
    lines.append("TRIP ARCHITECT — PROPOSAL DRAFT")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Inquiry: {parsed.get('raw_summary', 'N/A')}")
    lines.append("=" * 70)
    lines.append("")
    lines.append(intro)
    lines.append("")

    total_commission = 0.0

    for i, opt in enumerate(priced_options, 1):
        lines.append(f"{'─' * 50}")
        lines.append(f"  OPTION {i}: {opt.get('name', 'Unnamed')}")
        lines.append(f"{'─' * 50}")
        lines.append("")
        lines.append(f"  {opt.get('description', 'No description available.')}")
        lines.append("")

        if opt.get("why_it_fits"):
            lines.append(f"  Why it fits: {opt['why_it_fits']}")
            lines.append("")

        if opt.get("key_selling_points"):
            lines.append("  Highlights:")
            for sp in opt["key_selling_points"]:
                lines.append(f"    + {sp}")
            lines.append("")

        pricing = opt.get("pricing", {})
        if pricing.get("client_per_person"):
            lines.append("  Pricing:")
            lines.append(f"    Per person:  {pricing['client_per_person']}")
            lines.append(f"    Total ({pricing.get('party_size', '?')} pax):  {pricing.get('client_total', 'TBD')}")
            lines.append(f"    Source:      {pricing.get('source', 'unknown')}")
            if pricing.get("note"):
                lines.append(f"    Note:       {pricing['note']}")
            lines.append("")
            lines.append(f"  Commission (INTERNAL — not shown to client):")
            lines.append(f"    Markup:     {pricing.get('markup', 'N/A')}")
            lines.append(f"    Per person: {pricing.get('commission_per_person', 'N/A')}")
            lines.append(f"    Total:      {pricing.get('commission_total', 'N/A')}")

            raw = pricing.get("raw", {})
            if raw.get("commission_total"):
                total_commission += raw["commission_total"]
        else:
            lines.append("  Pricing: Not available — needs manual research")

        if opt.get("potential_concerns"):
            lines.append("")
            lines.append("  Watch items:")
            for c in opt["potential_concerns"]:
                lines.append(f"    ! {c}")

        lines.append("")

    # Comparison summary
    lines.append("=" * 70)
    lines.append("  COMPARISON SUMMARY")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"  {'Option':<12} {'Per Person':<16} {'Total':<16} {'Commission':<16}")
    lines.append(f"  {'─' * 56}")

    for i, opt in enumerate(priced_options, 1):
        pricing = opt.get("pricing", {})
        pp = pricing.get("client_per_person", "TBD")
        total = pricing.get("client_total", "TBD")
        comm = pricing.get("commission_total", "N/A")
        lines.append(f"  Option {i:<4} {pp:<16} {total:<16} {comm:<16}")

    lines.append("")
    if total_commission > 0:
        lines.append(f"  Total potential commission: {fmt_usd(total_commission)}")
    lines.append("")

    # Commander action prompt
    lines.append("=" * 70)
    lines.append("  COMMANDER ACTION REQUIRED")
    lines.append("=" * 70)
    lines.append("")
    lines.append("  Reply with:")
    lines.append("    SEND 1  — Send Option 1 to client")
    lines.append("    SEND 2  — Send Option 2 to client")
    lines.append("    SEND 3  — Send Option 3 to client")
    lines.append("    REVISE  — Request changes to any option")
    lines.append("    HOLD    — Defer for further research")
    lines.append("")

    rendered = "\n".join(lines)
    logger.info("Proposal rendered: %d lines, commission potential %s",
                len(lines), fmt_usd(total_commission))
    return rendered


# ==========================================================================
# STEP 7: ARCHITECT PIPELINE — Full Orchestration with Session State
# ==========================================================================

def _notify_commander(step_name: str, status: str, details: str = "", session_id: str = ""):
    """Send a progress email to Commander after each step completes."""
    if not gmail_send_as_persona:
        logger.info("Gmail not available — skipping progress notification for %s", step_name)
        return
    try:
        subject = f"Trip Architect — Step Complete: {step_name}"
        body = f"Commander,\n\n"
        body += f"Trip Architect step completed.\n\n"
        body += f"Step: {step_name}\n"
        body += f"Status: {status}\n"
        if session_id:
            body += f"Session: {session_id}\n"
        if details:
            body += f"\nDetails:\n{details}\n"
        body += f"\n— COS Hale\n   Trip Architect Pipeline v2.0"

        gmail_send_as_persona(
            to=COMMANDER_EMAIL,
            subject=subject,
            body=body,
            persona_id="COS",
        )
        logger.info("Commander notified: %s — %s", step_name, status)
    except Exception as e:
        logger.warning("Failed to notify Commander on %s: %s", step_name, e)


def architect_pipeline(
    inquiry: str,
    client_name: str = None,
    client_email: str = None,
    session_id: str = None,
    notify: bool = True,
) -> dict:
    """Full Trip Architect pipeline: parse -> research -> price -> consult -> staff paper.

    Phase 1: Generates EARA staff paper for Commander review.
    Phase 2: On Commander approval, generates branded PDF proposal.

    Args:
        inquiry: Free-text client travel inquiry.
        client_name: Optional client name for personalization.
        client_email: Optional client email for draft preparation.
        session_id: Resume an existing session (skip completed steps).
        notify: Send email after each step (default True).

    Returns:
        dict with session data + result summary.
    """
    logger.info("=" * 60)
    logger.info("TRIP ARCHITECT PIPELINE START")
    logger.info("Client: %s | Email: %s", client_name or "unknown", client_email or "none")
    logger.info("Inquiry: %s", inquiry[:200])
    logger.info("=" * 60)

    # ── Load or create session ──
    if session_id:
        try:
            session = ArchitectSession.load(session_id)
            logger.info("Resuming session %s at phase: %s", session_id, session.phase)
        except FileNotFoundError:
            logger.error("Session %s not found — creating new", session_id)
            session = ArchitectSession.create(inquiry, client_name or "", client_email or "")
    else:
        session = ArchitectSession.create(inquiry, client_name or "", client_email or "")

    result = {
        "status": "running",
        "session_id": session.session_id,
        "client_name": client_name,
        "client_email": client_email,
        "steps": dict(session.steps_completed),
        "model_tags_used": list(session.model_tags_used),
    }

    # ── Step 1: Parse ──
    if session.phase in ("new",):
        try:
            parsed = parse_client_inquiry(inquiry)
            session.parsed = parsed
            session.phase = "parsed"
            session.steps_completed["parse"] = "success"
            session.model_tags_used.append(MODEL_TAGS.get("fast", "Claude Opus"))
            session.save()
            result["steps"]["parse"] = "success"
            if notify:
                _notify_commander("1. Parse Inquiry", "SUCCESS",
                    f"Destination: {parsed.get('destination', '?')}\n"
                    f"Budget: {fmt_usd(parsed.get('budget_per_person') or parsed.get('budget_total', 0))}\n"
                    f"Party: {parsed.get('party_description', '?')}\n"
                    f"Type: {parsed.get('travel_type', '?')}",
                    session.session_id)
        except Exception as e:
            logger.error("Parse step failed: %s", e)
            session.steps_completed["parse"] = f"error: {e}"
            session.save()
            result["steps"]["parse"] = f"error: {e}"
            parsed = {"destination": None, "raw_summary": inquiry[:200]}
            session.parsed = parsed
            session.phase = "parsed"
            session.save()
    else:
        parsed = session.parsed

    # ── Step 2: Client Context ──
    if session.phase in ("parsed",) and not session.client_context:
        try:
            client_ctx = _load_client_context(client_name or "", client_email or "")
            session.client_context = client_ctx
            session.steps_completed["client_context"] = "success"
            session.save()
            result["steps"]["client_context"] = "success"
            if notify:
                ctx_summary = f"Registry: {'found' if client_ctx.get('registry') else 'not found'}\n"
                ctx_summary += f"Dossier: {'found' if client_ctx.get('dossier_summary') else 'not found'}\n"
                ctx_summary += f"Active bookings: {len(client_ctx.get('active_bookings', []))}\n"
                ctx_summary += f"Known preferences: {', '.join(client_ctx.get('known_preferences', [])) or 'none'}"
                _notify_commander("2. Client Context", "SUCCESS", ctx_summary, session.session_id)
        except Exception as e:
            logger.warning("Client context failed: %s", e)
            session.steps_completed["client_context"] = f"warning: {e}"
            session.save()
    client_ctx = session.client_context or {}

    # ── Step 3: Research (A2 + ship/world intel) ──
    if session.phase in ("parsed",):
        try:
            options = research_destination(parsed, client_context=client_ctx)
            session.research_options = options
            session.phase = "researched"
            session.steps_completed["research"] = f"success — {len(options)} options"
            session.model_tags_used.append(MODEL_TAGS.get("fast", "Claude Opus"))
            session.save()
            result["steps"]["research"] = f"success — {len(options)} options"
            if notify:
                opt_summary = "\n".join(
                    f"  Option {i}: {o.get('name', '?')} ({o.get('confidence', '?')} confidence)"
                    for i, o in enumerate(options, 1)
                )
                _notify_commander("3. A2 Research + Intel", "SUCCESS",
                    f"{len(options)} options generated:\n{opt_summary}", session.session_id)
        except Exception as e:
            logger.error("Research step failed: %s", e)
            options = _fallback_research(parsed)
            session.research_options = options
            session.phase = "researched"
            session.steps_completed["research"] = f"fallback: {e}"
            session.save()
    else:
        options = session.research_options or _fallback_research(parsed)

    # ── Step 4: Price ──
    if session.phase in ("researched",):
        try:
            priced = price_options(options, parsed)
            session.priced_options = priced
            session.phase = "priced"
            session.steps_completed["price"] = "success"
            session.save()
            result["steps"]["price"] = "success"
            if notify:
                price_lines = "\n".join(
                    f"  Option {i}: {o.get('pricing', {}).get('client_total', 'TBD')} "
                    f"(commission: {o.get('pricing', {}).get('commission_total', 'N/A')})"
                    for i, o in enumerate(priced, 1)
                )
                _notify_commander("4. Pricing", "SUCCESS",
                    f"Pricing complete:\n{price_lines}", session.session_id)
        except Exception as e:
            logger.error("Price step failed: %s", e)
            priced = options
            session.priced_options = priced
            session.phase = "priced"
            session.steps_completed["price"] = f"error: {e}"
            session.save()
    else:
        priced = session.priced_options or options

    # ── Step 5: Staff Consultations (A3 + A9) ──
    if session.phase in ("priced",):
        try:
            a3_assessment = _consult_a3_logistics(priced, parsed, client_ctx)
            session.a3_logistics = a3_assessment
            session.steps_completed["a3_consult"] = "success"
            session.save()
            if notify:
                _notify_commander("5a. A3 Logistics Assessment", "SUCCESS",
                    a3_assessment[:500], session.session_id)
        except Exception as e:
            logger.error("A3 consultation failed: %s", e)
            a3_assessment = f"A3 assessment unavailable: {e}"
            session.a3_logistics = a3_assessment
            session.steps_completed["a3_consult"] = f"error: {e}"

        try:
            a9_assessment = _consult_a9_finance(priced, parsed)
            session.a9_finance = a9_assessment
            session.steps_completed["a9_consult"] = "success"
            session.save()
            if notify:
                _notify_commander("5b. A9 Finance Assessment", "SUCCESS",
                    a9_assessment[:500], session.session_id)
        except Exception as e:
            logger.error("A9 consultation failed: %s", e)
            a9_assessment = f"A9 assessment unavailable: {e}"
            session.a9_finance = a9_assessment
            session.steps_completed["a9_consult"] = f"error: {e}"

        session.phase = "consulted"
        session.save()
    else:
        a3_assessment = session.a3_logistics or "N/A"
        a9_assessment = session.a9_finance or "N/A"

    # ── Step 6: EARA Staff Paper ──
    if session.phase in ("consulted",):
        try:
            staff_paper = _render_eara_staff_paper(
                session, priced, parsed, a3_assessment, a9_assessment, client_ctx
            )
            session.staff_paper = staff_paper
            session.phase = "staff_paper"
            session.steps_completed["staff_paper"] = "success"
            session.save()
            result["staff_paper"] = staff_paper
            if notify:
                _notify_commander("6. EARA Staff Paper", "SUCCESS",
                    "Staff paper rendered. Sending for Commander review...", session.session_id)
        except Exception as e:
            logger.error("Staff paper render failed: %s", e)
            # Fall back to old-style render
            staff_paper = render_proposals(priced, parsed)
            session.staff_paper = staff_paper
            session.phase = "staff_paper"
            session.steps_completed["staff_paper"] = f"fallback: {e}"
            session.save()

    # ── Step 7: Email staff paper to Commander ──
    if session.phase in ("staff_paper",) and not session.draft_id:
        try:
            if gmail_send_with_approval:
                subject = f"STAFF PAPER — Trip Architect: {client_name or 'New Inquiry'}"
                body = f"Commander,\n\n"
                body += f"The Wing has completed Phase 1 analysis of a trip design request.\n"
                body += f"Please review the staff paper below and reply with your decision.\n\n"
                body += session.staff_paper
                body += f"\n\n— Victoria 'Victory' Hale, SES-6 (VCSAF)\n   Trip Architect Pipeline v5.1"

                draft_result = gmail_send_with_approval(
                    to=COMMANDER_EMAIL,
                    subject=subject,
                    body=body,
                    persona_id="COS",
                    auto_send=True,  # Send directly — this is the staff paper
                )
                session.draft_id = draft_result.get("message_id") or draft_result.get("id", "")
                session.phase = "awaiting_approval"
                session.steps_completed["email_staff_paper"] = f"sent — {session.draft_id}"
                session.save()
                result["draft_id"] = session.draft_id
                if notify:
                    _notify_commander("7. Staff Paper Delivered", "SUCCESS",
                        f"Staff paper sent to Commander.\nSession: {session.session_id}\n"
                        f"Awaiting SEND/REVISE/HOLD decision.", session.session_id)
            else:
                session.phase = "awaiting_approval"
                session.steps_completed["email_staff_paper"] = "skipped — gmail not available"
                session.save()
        except Exception as e:
            logger.error("Email staff paper failed: %s", e)
            session.steps_completed["email_staff_paper"] = f"error: {e}"
            session.phase = "awaiting_approval"
            session.save()

    # ── Store in persona memory ──
    try:
        summary = (
            f"Trip Architect inquiry from {client_name or 'unknown client'}: "
            f"{parsed.get('raw_summary', inquiry[:100])}. "
            f"Generated {len(priced)} options. Session: {session.session_id}."
        )
        if priced and priced[0].get("pricing", {}).get("raw", {}).get("total"):
            summary += f" Lead option total: {fmt_usd(priced[0]['pricing']['raw']['total'])}."
        store_persona_memory("A3", "client_context", summary)
        store_persona_memory("A2", "research", summary)
        result["steps"]["memory_store"] = "success"
    except Exception as e:
        logger.warning("Memory store failed: %s", e)
        result["steps"]["memory_store"] = f"error: {e}"

    # ── Finalize Phase 1 ──
    result["steps"] = dict(session.steps_completed)
    result["model_tags_used"] = list(set(session.model_tags_used))
    result["phase"] = session.phase
    result["session_id"] = session.session_id

    if session.phase == "awaiting_approval":
        result["status"] = "awaiting_commander_decision"
        result["next_action"] = f"architect_approve('{session.session_id}', 'SEND 1|2|3 or REVISE or HOLD')"
    elif all("error" not in str(v) for v in session.steps_completed.values()):
        result["status"] = "success"
    else:
        result["status"] = "completed_with_warnings"

    logger.info("TRIP ARCHITECT PHASE 1 COMPLETE — status: %s, session: %s",
                result["status"], session.session_id)

    return result


# ==========================================================================
# STEP 9: PHASE 2 — BRANDED PDF PROPOSAL (on Commander approval)
# ==========================================================================

def architect_approve(session_id: str, decision: str) -> dict:
    """Phase 2: Commander approves an option — generate branded PDF proposal.

    Args:
        session_id: The architect session to approve.
        decision: SEND 1, SEND 2, SEND 3, REVISE, or HOLD.

    Returns:
        dict with status, PDF path (if generated), and email result.
    """
    logger.info("Commander decision: %s for session %s", decision, session_id)

    try:
        session = ArchitectSession.load(session_id)
    except FileNotFoundError:
        return {"status": "error", "error": f"Session {session_id} not found"}

    if session.phase not in ("awaiting_approval", "staff_paper"):
        return {"status": "error", "error": f"Session is in phase '{session.phase}', expected 'awaiting_approval'"}

    session.commander_decision = decision.strip().upper()

    # ── HOLD ──
    if "HOLD" in session.commander_decision:
        session.phase = "held"
        session.steps_completed["commander_decision"] = "HOLD"
        session.save()
        return {"status": "held", "session_id": session_id, "message": "Session held for further research"}

    # ── REVISE ──
    if "REVISE" in session.commander_decision:
        session.phase = "priced"  # Roll back to allow re-consultation
        session.steps_completed["commander_decision"] = f"REVISE: {decision}"
        session.save()
        return {"status": "revision_requested", "session_id": session_id,
                "message": "Session rolled back. Run architect_pipeline with session_id to regenerate."}

    # ── SEND N ──
    send_match = re.match(r"SEND\s+(\d+)", session.commander_decision)
    if not send_match:
        return {"status": "error", "error": f"Unrecognized decision: {decision}. Use SEND 1/2/3, REVISE, or HOLD."}

    option_num = int(send_match.group(1))
    if option_num < 1 or option_num > len(session.priced_options):
        return {"status": "error", "error": f"Option {option_num} doesn't exist. Available: 1-{len(session.priced_options)}"}

    selected = session.priced_options[option_num - 1]
    session.selected_option = option_num
    session.phase = "approved"
    session.steps_completed["commander_decision"] = f"SEND {option_num}"
    session.save()

    # ── Generate branded proposal with EXEC voice ──
    try:
        client_desc = session.parsed.get("party_description") or f"{session.parsed.get('party_size', 'the')} travelers"
        dest = selected.get("name", session.parsed.get("destination", "your destination"))
        prefs = ", ".join(session.parsed.get("preferences", [])) or "exceptional travel"

        exec_query = f"""Write a warm, personal travel proposal letter for {session.client_name or client_desc}.

Selected option: {selected.get('name', 'Custom Trip')}
Description: {selected.get('description', '')}
Why it fits: {selected.get('why_it_fits', '')}
Key highlights: {', '.join(selected.get('key_selling_points', []))}
Pricing: {selected.get('pricing', {}).get('client_per_person', 'TBD')} per person / {selected.get('pricing', {}).get('client_total', 'TBD')} total
Travel style: {session.parsed.get('travel_style', 'premium')}
Their interests: {prefs}

Write 3-4 paragraphs:
1. Warm opening referencing their specific interests
2. Why this option is perfect for them — paint the picture
3. Pricing summary (client-facing numbers ONLY — no commission, no markup, no internal data)
4. Next steps — "ready to hold your reservation" or similar

Sign off as: John Loucks, Dreams2Memories Travel, LLC
Tone: personal, literate, warm — never corporate. This is a human letter, not a brochure."""

        exec_result = call_persona("EXEC", exec_query, max_tokens=1000)
        proposal_text = exec_result.get("answer", "")
        # Clean persona tags
        proposal_text = re.sub(r'^.*?EXEC-SOLBERG-VEGA:\s*', '', proposal_text, flags=re.IGNORECASE)
        proposal_text = re.sub(r'\n\n---\n_.*?_$', '', proposal_text, flags=re.DOTALL)

        session.rendered_proposal = proposal_text
        session.steps_completed["branded_proposal"] = "success"
        session.save()

    except Exception as e:
        logger.error("EXEC proposal generation failed: %s", e)
        proposal_text = f"[Proposal generation failed: {e}]"
        session.steps_completed["branded_proposal"] = f"error: {e}"
        session.save()

    # ── Generate PDF (optional — uses itinerary pipeline if available) ──
    pdf_path = ""
    try:
        from itinerary_finishing_pipeline import render_html_to_pdf
        output_dir = Path.home() / "Thunderbird" / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r'[^\w\-]', '_', session.client_name or "proposal")
        pdf_filename = f"Trip_Proposal_{safe_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
        pdf_path = str(output_dir / pdf_filename)

        # Simple HTML proposal
        html = f"""<!DOCTYPE html>
<html><head>
<style>
body {{ font-family: 'Georgia', serif; max-width: 700px; margin: 40px auto; padding: 20px; color: #0d1b2e; }}
h1 {{ color: #0d1b2e; border-bottom: 2px solid #c9a84c; padding-bottom: 10px; }}
.logo {{ color: #c9a84c; font-size: 14px; letter-spacing: 2px; }}
.footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #c9a84c; font-size: 12px; color: #8a9ab5; }}
</style>
</head><body>
<div class="logo">DREAMS2MEMORIES TRAVEL, LLC</div>
<h1>Your Travel Proposal</h1>
<p><strong>{session.client_name or 'Valued Client'}</strong></p>
{''.join(f'<p>{para}</p>' for para in proposal_text.split(chr(10) + chr(10)) if para.strip())}
<div class="footer">
Dreams2Memories Travel, LLC | John Loucks | 719-291-0742 | johnloucks3@gmail.com
</div>
</body></html>"""

        render_html_to_pdf(html, pdf_path)
        session.proposal_pdf_path = pdf_path
        session.steps_completed["pdf_generation"] = f"success — {pdf_path}"
        session.save()
        logger.info("Proposal PDF generated: %s", pdf_path)
    except (ImportError, Exception) as e:
        logger.info("PDF generation skipped: %s", e)
        session.steps_completed["pdf_generation"] = f"skipped: {e}"
        session.save()

    # ── Email proposal to Commander (and optionally client) ──
    try:
        if gmail_send_with_approval:
            subject = f"Travel Proposal — {session.client_name or 'Client'}: {selected.get('name', 'Custom Trip')}"
            body = f"Commander,\n\n"
            body += f"Branded proposal generated for {session.client_name or 'client'} (Option {option_num}).\n"
            body += f"Session: {session.session_id}\n\n"
            body += f"--- PROPOSAL TEXT ---\n\n{proposal_text}\n\n"
            if pdf_path:
                body += f"PDF saved: {pdf_path}\n"
            body += f"\nReply SEND CLIENT to forward this proposal to {session.client_email or 'the client'}."
            body += f"\n\n— Naia Solberg-Vega (EXEC)\n   Trip Architect Pipeline v2.0"

            gmail_send_with_approval(
                to=COMMANDER_EMAIL,
                subject=subject,
                body=body,
                persona_id="EXEC",
                auto_send=True,
            )
            session.steps_completed["proposal_email"] = "sent to Commander"
            session.save()
    except Exception as e:
        logger.error("Proposal email failed: %s", e)
        session.steps_completed["proposal_email"] = f"error: {e}"
        session.save()

    session.phase = "proposal_sent"
    session.save()

    return {
        "status": "proposal_generated",
        "session_id": session_id,
        "selected_option": option_num,
        "option_name": selected.get("name"),
        "proposal_text": proposal_text[:500] + "..." if len(proposal_text) > 500 else proposal_text,
        "pdf_path": pdf_path,
        "phase": session.phase,
        "steps": dict(session.steps_completed),
    }


# ==========================================================================
# STEP 10: EMAIL INTEL AUTO-TRIGGER HOOK
# ==========================================================================

def architect_from_email(email_subject: str, email_body: str, sender_name: str = "",
                         sender_email: str = "") -> Optional[dict]:
    """Hook for Email Intel Officer — auto-triggers Trip Architect on inquiry emails.

    Called by thunderbird_email_intel.py when it detects a travel inquiry.
    Returns pipeline result or None if the email doesn't qualify.
    """
    # Quick check — does this look like a travel inquiry?
    inquiry_keywords = ["cruise", "trip", "travel", "vacation", "flight", "hotel",
                        "booking", "quote", "price", "availability", "itinerary",
                        "interested in", "looking for", "can you help"]

    combined = (email_subject + " " + email_body).lower()
    if not any(kw in combined for kw in inquiry_keywords):
        return None

    logger.info("Email Intel triggered Trip Architect for: %s (%s)", sender_name, email_subject)

    # Use the email body as the inquiry
    inquiry_text = f"Email inquiry from {sender_name or sender_email}:\n"
    inquiry_text += f"Subject: {email_subject}\n\n{email_body}"

    return architect_pipeline(
        inquiry=inquiry_text,
        client_name=sender_name or sender_email.split("@")[0],
        client_email=sender_email,
        notify=True,
    )


# ==========================================================================
# STEP 8: MCP TOOL REGISTRATION (Enhanced)
# ==========================================================================

def register_trip_architect_tools(mcp_server):
    """Register Trip Architect tools with the MCP server."""

    @mcp_server.tool(
        name="trip_architect",
        annotations={"title": "Run Autonomous Trip Architect", "readOnlyHint": False},
    )
    async def trip_architect_tool(
        inquiry: str,
        client_name: Optional[str] = None,
        client_email: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """Run the autonomous Trip Architect pipeline on a client inquiry.

        Phase 1: Parses inquiry, researches via A2, prices with markup,
        consults A3 (logistics) + A9 (finance), generates EARA staff paper,
        emails Commander for approval.

        Phase 2: Use trip_architect_approve to generate branded proposal.

        Provide the inquiry text and optionally client name and email.
        Pass session_id to resume an existing session.
        """
        result = architect_pipeline(
            inquiry, client_name=client_name, client_email=client_email,
            session_id=session_id,
        )
        return json.dumps(result, indent=2, default=str)

    @mcp_server.tool(
        name="trip_architect_approve",
        annotations={"title": "Approve Trip Architect Proposal", "readOnlyHint": False},
    )
    async def trip_architect_approve_tool(
        session_id: str,
        decision: str,
    ) -> str:
        """Approve or reject a Trip Architect proposal.

        session_id: The architect session ID (from trip_architect result).
        decision: SEND 1, SEND 2, SEND 3 (approve an option),
                  REVISE (request changes), or HOLD (defer).
        """
        result = architect_approve(session_id, decision)
        return json.dumps(result, indent=2, default=str)

    @mcp_server.tool(
        name="trip_architect_sessions",
        annotations={"title": "List Trip Architect Sessions", "readOnlyHint": True},
    )
    async def trip_architect_sessions_tool(
        active_only: bool = True,
    ) -> str:
        """List all Trip Architect sessions.

        Set active_only=False to include completed sessions.
        """
        sessions = ArchitectSession.list_sessions(active_only=active_only)
        return json.dumps(sessions, indent=2, default=str)

    @mcp_server.tool(
        name="parse_inquiry",
        annotations={"title": "Parse Travel Inquiry", "readOnlyHint": True},
    )
    async def parse_inquiry_tool(
        inquiry: str,
    ) -> str:
        """Parse a client travel inquiry into structured data.

        Extracts destination, dates, budget, party size, preferences,
        travel style, and more from free-text input.
        """
        parsed = parse_client_inquiry(inquiry)
        return json.dumps(parsed, indent=2, default=str)

    logger.info("Trip Architect MCP tools registered (trip_architect, trip_architect_approve, trip_architect_sessions, parse_inquiry)")


# ==========================================================================
# STEP 11: CLI
# ==========================================================================

if __name__ == "__main__":
    import sys

    def _print_usage():
        print("Thunderbird Trip Architect v2.0 — Autonomous Trip Design Pipeline")
        print()
        print("Usage:")
        print("  python3 thunderbird_trip_architect.py --test              # Run test pipeline")
        print("  python3 thunderbird_trip_architect.py --architect 'inquiry text'  # Run pipeline on inquiry")
        print("  python3 thunderbird_trip_architect.py --approve SESSION_ID 'SEND 1'  # Approve a session")
        print("  python3 thunderbird_trip_architect.py --sessions          # List active sessions")
        print("  python3 thunderbird_trip_architect.py --status SESSION_ID # Show session status")
        print()
        print("Import: from thunderbird_trip_architect import architect_pipeline, architect_approve")

    if len(sys.argv) < 2:
        _print_usage()
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "--test":
        print("Running Trip Architect pipeline test...\n")
        test_inquiry = (
            "We're 4 couples looking for a 10-day Mediterranean cruise in October 2026. "
            "Budget is about $8,000 per person. We love history, wine, and good food. "
            "Prefer balcony cabins. Open to Silversea, Oceania, or Viking."
        )
        result = architect_pipeline(
            test_inquiry,
            client_name="Test Party",
            client_email=None,
            notify=False,
        )
        print(f"Session: {result.get('session_id')}")
        print(f"Phase: {result.get('phase')}")
        print(f"Status: {result.get('status')}")
        print(f"Steps: {json.dumps(result.get('steps', {}), indent=2)}")
        if result.get("staff_paper"):
            print("\n--- STAFF PAPER ---")
            print(result["staff_paper"][:2000])

    elif cmd == "--architect":
        if len(sys.argv) < 3:
            print("Error: provide inquiry text after --architect")
            sys.exit(1)
        inquiry = " ".join(sys.argv[2:])
        print(f"Running Trip Architect on: {inquiry[:100]}...\n")
        result = architect_pipeline(inquiry)
        print(f"Session: {result.get('session_id')}")
        print(f"Phase: {result.get('phase')}")
        print(f"Status: {result.get('status')}")
        print(json.dumps(result.get("steps", {}), indent=2))

    elif cmd == "--approve":
        if len(sys.argv) < 4:
            print("Error: --approve SESSION_ID DECISION")
            sys.exit(1)
        sid = sys.argv[2]
        decision = " ".join(sys.argv[3:])
        print(f"Approving session {sid}: {decision}\n")
        result = architect_approve(sid, decision)
        print(json.dumps(result, indent=2, default=str))

    elif cmd == "--sessions":
        sessions = ArchitectSession.list_sessions(active_only="--all" not in sys.argv)
        if sessions:
            print(f"{'Session ID':<45} {'Client':<20} {'Phase':<20} {'Updated'}")
            print("-" * 110)
            for s in sessions:
                print(f"{s['session_id']:<45} {s['client_name']:<20} {s['phase']:<20} {s.get('updated_at', '?')}")
        else:
            print("No active sessions.")

    elif cmd == "--status":
        if len(sys.argv) < 3:
            print("Error: --status SESSION_ID")
            sys.exit(1)
        try:
            session = ArchitectSession.load(sys.argv[2])
            print(f"Session: {session.session_id}")
            print(f"Client: {session.client_name}")
            print(f"Phase: {session.phase}")
            print(f"Created: {session.created_at}")
            print(f"Updated: {session.updated_at}")
            print(f"Steps: {json.dumps(session.steps_completed, indent=2)}")
            if session.commander_decision:
                print(f"Commander Decision: {session.commander_decision}")
        except FileNotFoundError:
            print(f"Session not found: {sys.argv[2]}")

    else:
        _print_usage()
