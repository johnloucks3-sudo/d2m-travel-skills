"""
Thunderbird Client Survey Module (Item #7)
==========================================

Client satisfaction surveys for Dreams2Memories Travel, LLC.

Features:
- Generate personalized survey emails in EXEC (Naia) voice
- Batch draft creation for Commander review
- Parse freeform survey responses via Groq
- Compile NPS scores and preference tallies

Integrates with: travel_mcp_server.py, thunderbird_gmail.py, thunderbird_personas.py
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

from pydantic import Field
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

THUNDERBIRD_DIR = Path(__file__).parent
SURVEY_LOG = THUNDERBIRD_DIR / "logs" / "survey.log"
SPREADSHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"

SURVEY_QUESTIONS = [
    "What do you value most about working with Dreams2Memories Travel?",
    "On a scale of 1-10, how likely are you to recommend D2M to a friend?",
    "What would you want in a client portal? (Trip timeline / Document uploads / Direct messaging / Payment tracking / Other)",
    "How do you prefer to receive trip information? (Email / PDF / Online portal / Text-WhatsApp)",
    "What's one thing we could do better?",
]


# ============================================================================
# EMAIL GENERATION — EXEC (Naia) Voice
# ============================================================================

def generate_survey_email(client_name: str, client_email: str) -> str:
    """Generate a personalized survey email in EXEC (Naia Solberg-Vega) voice.

    Warm, personal, grateful — never corporate or generic.
    Returns the email body as plain text.
    """
    first_name = client_name.split()[0] if client_name else "there"

    body = f"""Dear {first_name},

I hope this finds you well — and hopefully still savoring a few memories from your travels.

I'm reaching out personally because your experience matters deeply to us at Dreams2Memories Travel. We're a small team that believes every journey should feel like it was made just for you — and your honest feedback is the compass that keeps us pointed in the right direction.

Would you take a few minutes to share your thoughts? Simply reply to this email with your answers — even a few words helps.

1. {SURVEY_QUESTIONS[0]}

2. {SURVEY_QUESTIONS[1]}

3. {SURVEY_QUESTIONS[2]}

4. {SURVEY_QUESTIONS[3]}

5. {SURVEY_QUESTIONS[4]}

There are no wrong answers, and nothing is too small to mention. If something made your trip magical — or if something fell short — we want to hear it.

Thank you for trusting us with your travels, {first_name}. It's a privilege we never take for granted.

With warmth and gratitude,

Naia Solberg-Vega
Dreams2Memories Travel, LLC
concierge@d2mluxury.quest"""

    return body


# ============================================================================
# BATCH DRAFT CREATION
# ============================================================================

def send_survey_batch(clients: List[Dict[str, str]]) -> Dict[str, Any]:
    """Create Gmail drafts for a batch of clients (Commander reviews before sending).

    Args:
        clients: List of {"name": str, "email": str} dicts.

    Returns:
        dict with drafts_created count and client list.
    """
    from thunderbird_gmail import gmail_send_with_approval

    results = []
    drafts_created = 0
    errors = []

    for client in clients:
        name = client.get("name", "")
        email = client.get("email", "")
        if not name or not email:
            errors.append(f"Skipped — missing name or email: {client}")
            continue

        body = generate_survey_email(name, email)
        subject = f"A quick question from Dreams2Memories Travel, {name.split()[0]}"

        try:
            result = gmail_send_with_approval(
                to=email,
                subject=subject,
                body=body,
                persona_id="EXEC",
                auto_send=False,  # Draft only — Commander reviews
            )
            drafts_created += 1
            results.append({
                "name": name,
                "email": email,
                "draft_id": result.get("id", "unknown"),
                "status": "draft_created",
            })
        except Exception as e:
            logger.error(f"Survey draft failed for {name} ({email}): {e}")
            errors.append(f"{name} ({email}): {e}")

    # Log the batch
    _log_survey_action("batch_draft", f"Created {drafts_created} drafts for {len(clients)} clients")

    return {
        "status": "success",
        "drafts_created": drafts_created,
        "total_clients": len(clients),
        "clients": results,
        "errors": errors if errors else None,
    }


# ============================================================================
# RESPONSE PARSING — Groq LLM extraction
# ============================================================================

def parse_survey_response(email_text: str) -> Dict[str, Any]:
    """Parse a freeform survey reply into structured answers using Groq.

    Returns:
        dict with q1_value, q2_nps (int), q3_portal_prefs (list),
        q4_delivery_pref, q5_improvement
    """
    from thunderbird_model_router import _call_groq

    system_prompt = """You are a data extraction assistant for Dreams2Memories Travel.
Extract answers to a 5-question client survey from the email text below.

Return ONLY valid JSON with these exact keys:
{
    "q1_value": "what they value most (string or null)",
    "q2_nps": NPS_SCORE_AS_INTEGER_1_TO_10_OR_NULL,
    "q3_portal_prefs": ["list", "of", "selected", "options"] or [],
    "q4_delivery_pref": "their preferred delivery method (string or null)",
    "q5_improvement": "what they'd improve (string or null)"
}

The 5 questions were:
1. What do you value most about working with Dreams2Memories Travel?
2. On a scale of 1-10, how likely are you to recommend D2M to a friend?
3. What would you want in a client portal? (Trip timeline / Document uploads / Direct messaging / Payment tracking / Other)
4. How do you prefer to receive trip information? (Email / PDF / Online portal / Text-WhatsApp)
5. What's one thing we could do better?

If an answer is missing or unclear, use null for strings or [] for lists.
Return ONLY the JSON object, no explanation."""

    try:
        raw = _call_groq(system_prompt, email_text, model="fast",
                         max_tokens=400, temperature=0.1)

        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
        else:
            parsed = json.loads(raw)

        # Validate and normalize
        result = {
            "q1_value": parsed.get("q1_value"),
            "q2_nps": None,
            "q3_portal_prefs": parsed.get("q3_portal_prefs", []),
            "q4_delivery_pref": parsed.get("q4_delivery_pref"),
            "q5_improvement": parsed.get("q5_improvement"),
            "raw_parsed": parsed,
        }

        # Ensure NPS is an int 1-10
        nps = parsed.get("q2_nps")
        if nps is not None:
            try:
                nps_int = int(nps)
                if 1 <= nps_int <= 10:
                    result["q2_nps"] = nps_int
            except (ValueError, TypeError):
                pass

        # Ensure portal prefs is a list
        if not isinstance(result["q3_portal_prefs"], list):
            result["q3_portal_prefs"] = [str(result["q3_portal_prefs"])]

        return result

    except Exception as e:
        logger.error(f"Survey parse failed: {e}")
        return {
            "q1_value": None,
            "q2_nps": None,
            "q3_portal_prefs": [],
            "q4_delivery_pref": None,
            "q5_improvement": None,
            "error": str(e),
        }


# ============================================================================
# RESULTS COMPILATION — NPS + Tallies + Themes
# ============================================================================

def compile_survey_results(responses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compile survey responses into NPS scores, preference tallies, and themes.

    Args:
        responses: List of parsed survey response dicts (from parse_survey_response).

    Returns:
        dict with nps_score, portal_prefs, delivery_prefs, themes, response_count.
    """
    if not responses:
        return {"error": "No responses to compile", "response_count": 0}

    # NPS calculation
    nps_scores = [r["q2_nps"] for r in responses if r.get("q2_nps") is not None]
    nps_result = _calculate_nps(nps_scores)

    # Portal preference tallies
    portal_tally = {}
    for r in responses:
        for pref in r.get("q3_portal_prefs", []):
            pref_clean = pref.strip().lower()
            portal_tally[pref_clean] = portal_tally.get(pref_clean, 0) + 1

    # Delivery preference tallies
    delivery_tally = {}
    for r in responses:
        pref = r.get("q4_delivery_pref")
        if pref:
            pref_clean = pref.strip().lower()
            delivery_tally[pref_clean] = delivery_tally.get(pref_clean, 0) + 1

    # Theme extraction from q1 and q5
    themes = _extract_themes(responses)

    return {
        "response_count": len(responses),
        "nps": nps_result,
        "portal_preferences": dict(sorted(portal_tally.items(), key=lambda x: -x[1])),
        "delivery_preferences": dict(sorted(delivery_tally.items(), key=lambda x: -x[1])),
        "themes": themes,
        "compiled_at": datetime.now(timezone.utc).isoformat(),
    }


def _calculate_nps(scores: List[int]) -> Dict[str, Any]:
    """Calculate Net Promoter Score from a list of 1-10 ratings.

    NPS = ((promoters - detractors) / total) * 100
    - Promoters: 9-10
    - Passives: 7-8
    - Detractors: 1-6
    """
    if not scores:
        return {"score": None, "total_rated": 0, "note": "No NPS ratings received"}

    promoters = sum(1 for s in scores if s >= 9)
    passives = sum(1 for s in scores if 7 <= s <= 8)
    detractors = sum(1 for s in scores if s <= 6)
    total = len(scores)

    nps = round(((promoters - detractors) / total) * 100)

    return {
        "score": nps,
        "promoters": promoters,
        "passives": passives,
        "detractors": detractors,
        "total_rated": total,
        "average_rating": round(sum(scores) / total, 1),
    }


def _extract_themes(responses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Use Groq to summarize key themes from q1 (value) and q5 (improvement)."""
    values = [r["q1_value"] for r in responses if r.get("q1_value")]
    improvements = [r["q5_improvement"] for r in responses if r.get("q5_improvement")]

    if not values and not improvements:
        return {"value_themes": [], "improvement_themes": [], "note": "No text responses to analyze"}

    from thunderbird_model_router import _call_groq

    system_prompt = """You are analyzing client survey responses for Dreams2Memories Travel.
Identify the top 3-5 themes from the provided answers.

Return ONLY valid JSON:
{
    "value_themes": ["theme 1", "theme 2", ...],
    "improvement_themes": ["theme 1", "theme 2", ...]
}"""

    query = f"""What clients value most:
{chr(10).join(f'- {v}' for v in values) if values else '(no responses)'}

What clients want improved:
{chr(10).join(f'- {i}' for i in improvements) if improvements else '(no responses)'}"""

    try:
        raw = _call_groq(system_prompt, query, model="fast",
                         max_tokens=300, temperature=0.3)
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"Theme extraction failed: {e}")
        return {
            "value_themes": values[:5],
            "improvement_themes": improvements[:5],
            "note": "Raw responses (LLM theme extraction failed)",
        }


# ============================================================================
# LOGGING
# ============================================================================

def _log_survey_action(action: str, detail: str):
    """Append to survey log."""
    try:
        SURVEY_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        line = f"[{ts}] {action} | {detail}\n"
        with open(SURVEY_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        logger.warning(f"Survey log write failed: {e}")


# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================

def register_survey_tools(mcp: FastMCP):
    """Register survey tools with the MCP server."""

    @mcp.tool(
        name="send_client_survey",
        annotations={"title": "Send Client Survey Batch", "readOnlyHint": False},
    )
    async def send_client_survey(
        clients_json: str = Field(
            ...,
            description='JSON array of client objects: [{"name": "Jane Doe", "email": "jane@example.com"}, ...]'
        ),
    ) -> str:
        """Create Gmail drafts for client satisfaction surveys (EXEC voice).

        Drafts are NOT auto-sent — Commander reviews in Gmail before sending.
        Each client gets a personalized email with 5 survey questions.
        """
        try:
            clients = json.loads(clients_json)
            if not isinstance(clients, list):
                return json.dumps({"error": "clients_json must be a JSON array"})
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON: {e}"})

        result = send_survey_batch(clients)
        return json.dumps(result, indent=2)

    @mcp.tool(
        name="compile_survey_results",
        annotations={"title": "Compile Survey Results", "readOnlyHint": True},
    )
    async def compile_survey_results_tool(
        responses_json: str = Field(
            ...,
            description="JSON array of parsed survey responses (from parse_survey_response)"
        ),
    ) -> str:
        """Compile parsed survey responses into NPS score, preference tallies, and themes.

        Input: JSON array of response dicts with keys:
        q1_value, q2_nps, q3_portal_prefs, q4_delivery_pref, q5_improvement.
        """
        try:
            responses = json.loads(responses_json)
            if not isinstance(responses, list):
                return json.dumps({"error": "responses_json must be a JSON array"})
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON: {e}"})

        result = compile_survey_results(responses)
        return json.dumps(result, indent=2)

    logger.info("Survey tools registered (send_client_survey, compile_survey_results)")
