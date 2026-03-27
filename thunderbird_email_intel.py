"""
Thunderbird Email Intelligence Officer
========================================

Proactive email intelligence system that scans ALL incoming email,
reasons about relevance using context from client dossiers, booking data,
and supplier registries, then takes action: drafts responses, sends
staff papers to Commander, updates dossiers, creates action items.

Replaces: thunderbird_email_classifier.py (label-gated, 8-category, 8B model)

Architecture:
  Three sweeps run on schedule (every 30-60 min):
    1. SUPPLIER SWEEP  — emails from known supplier domains
    2. CLIENT SWEEP    — emails from known client addresses
    3. GENERAL SWEEP   — everything else worth attention

  Staff-to-Commander emails use EARA Constitution format:
    ISSUE: / DISCUSSION: / OPTIONS: / ACTIONS I RECOMMEND TAKING:

  Client draft responses use Commander's voice (my_voice_profile.md)
  via EXEC persona.

Models:
  - Claude Opus via CLI subprocess (Max plan, $0) — all analysis tasks

Standalone:  python3 thunderbird_email_intel.py
Scheduler:   from thunderbird_email_intel import run_email_intel_sweep
"""

import base64
import json
import logging
import os
import re
import subprocess
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests
from googleapiclient.errors import HttpError

from thunderbird_gmail import (
    _get_gmail_service,
    _decode_body,
    _extract_headers,
    gmail_send_with_approval,
    PERSONA_DISPLAY_NAMES,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
DOSSIERS_DIR = THUNDERBIRD_DIR / "Dossiers"
DOSSIERS_DIR_LOWER = THUNDERBIRD_DIR / "dossiers"
COMMANDER_REVIEW_DIR = THUNDERBIRD_DIR / "Commander_Review"
STATE_FILE = THUNDERBIRD_DIR / "email_intel_state.json"
VOICE_PROFILE_FILE = THUNDERBIRD_DIR / "my_voice_profile.md"

# Google Sheets
SHEETS_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
REGISTRY_CLIENTS_TAB = "Registry_Clients"
REFERENCE_SUPPLIERS_TAB = "Reference_Suppliers"
BOOKING_MASTER_TAB = "Booking Master"
ACTION_TRACKER_TAB = "Action_Tracker"

# Gmail
YODA_EMAIL = "johnloucks3@gmail.com"       # Commander's personal inbox — recipient for staff reports
OPS_EMAIL = "d2mconcierge@gmail.com"       # D2M ops sender — all draft From headers (gmail_token.json)
CONCIERGE_EMAIL = "concierge@d2mluxury.quest"

# Claude Haiku via CLI subprocess (Max plan, $0) — switched from Opus 2026-03-27 to reduce session quota burn
CLAUDE_CLI = os.path.expanduser("~/.local/bin/claude")

# Sweep config
SWEEP_LOOKBACK_HOURS = 6
MAX_EMAILS_PER_SWEEP = 50

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)


# ============================================================================
# STATE PERSISTENCE
# ============================================================================

def _load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {
        "processed_ids": [],
        "last_run": None,
        "stats": {
            "total": 0, "supplier": 0, "client": 0,
            "general": 0, "skipped": 0, "drafts_created": 0,
            "staff_papers_sent": 0,
        },
    }


def _save_state(state: Dict[str, Any]):
    # Keep processed_ids list from growing unbounded — last 2000
    if len(state.get("processed_ids", [])) > 2000:
        state["processed_ids"] = state["processed_ids"][-2000:]
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ============================================================================
# PHASE 1.2 — CLIENT REGISTRY (3-source merge)
# ============================================================================

def _get_sheets_client():
    """Get authenticated gspread client."""
    import gspread
    from google.oauth2 import service_account
    creds = service_account.Credentials.from_service_account_file(
        str(THUNDERBIRD_DIR / "credentials.json"),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return gspread.authorize(creds)


def _load_registry_clients() -> List[Dict[str, str]]:
    """Load Registry_Clients tab from Sheets. Returns list of row dicts."""
    try:
        gc = _get_sheets_client()
        ws = gc.open_by_key(SHEETS_ID).worksheet(REGISTRY_CLIENTS_TAB)
        rows = ws.get_all_records()
        logger.info(f"Registry_Clients: {len(rows)} clients loaded")
        return rows
    except Exception as e:
        logger.error(f"Failed to load Registry_Clients: {e}")
        return []


def _load_booking_master() -> List[Dict[str, str]]:
    """Load Booking Master tab. Returns list of row dicts."""
    try:
        gc = _get_sheets_client()
        ws = gc.open_by_key(SHEETS_ID).worksheet(BOOKING_MASTER_TAB)
        rows = ws.get_all_records()
        logger.info(f"Booking Master: {len(rows)} rows loaded")
        return rows
    except Exception as e:
        logger.error(f"Failed to load Booking Master: {e}")
        return []


def _extract_emails_from_text(text: str) -> Set[str]:
    """Extract all email addresses from text."""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return {e.lower() for e in re.findall(pattern, text)}


def _load_dossier_data() -> List[Dict[str, Any]]:
    """Load all dossier files and extract client info."""
    dossiers = []
    for dossier_dir in [DOSSIERS_DIR, DOSSIERS_DIR_LOWER]:
        if not dossier_dir.is_dir():
            continue
        for f in dossier_dir.glob("*.md"):
            try:
                text = f.read_text(encoding="utf-8")
                emails = _extract_emails_from_text(text)
                # Remove known non-client emails
                emails -= {YODA_EMAIL, CONCIERGE_EMAIL,
                           "dreams2memories@d2m-python-pipeline.iam.gserviceaccount.com"}

                # Extract client name from first heading
                name_match = re.search(r'#.*?—\s*(.+?)$', text, re.MULTILINE)
                client_name = name_match.group(1).strip() if name_match else f.stem

                # Extract DOBs
                dob_matches = re.findall(
                    r'DOB\s*\|?\s*([\w]+\s+\d{1,2},?\s+\d{4})', text
                )

                # Extract booking IDs
                booking_ids = re.findall(
                    r'(?:Booking|booking)\s*(?:ID|#)?\s*[:|]?\s*(\w{5,})', text
                )

                # Extract suppliers
                suppliers = []
                for s in ["Regent", "Viking", "Silversea", "Ponant", "Oceania",
                          "Seabourn", "Cunard", "AmaWaterways"]:
                    if s.lower() in text.lower():
                        suppliers.append(s)

                # Extract key dates
                fpd_match = re.search(
                    r'(?:Final Payment|FPD).*?(\w+ \d{1,2}(?:,?\s*\d{4})?)', text
                )

                dossiers.append({
                    "path": str(f),
                    "filename": f.name,
                    "client_name": client_name,
                    "emails": emails,
                    "dobs": dob_matches,
                    "booking_ids": booking_ids,
                    "suppliers": suppliers,
                    "fpd": fpd_match.group(1) if fpd_match else None,
                    "text": text,
                })
            except Exception as e:
                logger.error(f"Failed to parse dossier {f.name}: {e}")

    logger.info(f"Dossiers: {len(dossiers)} loaded")
    return dossiers


def build_client_registry() -> Dict[str, Dict[str, Any]]:
    """Build merged client registry keyed by lowercase email address.

    Merges: Registry_Clients (Sheets) + Dossier files + Booking Master.
    Returns dict: email -> {name, phone, dob, suppliers, bookings, dossier_path, ...}
    """
    registry: Dict[str, Dict[str, Any]] = {}

    # Source 1: Registry_Clients from Sheets
    for row in _load_registry_clients():
        email = row.get("Email", "").strip().lower()
        if not email:
            continue
        registry[email] = {
            "name": row.get("Last Name", ""),
            "email": email,
            "phone": row.get("Phone Number", ""),
            "dob": row.get("Birthday", ""),
            "vip": str(row.get("VIP Status", "")).upper() == "TRUE",
            "preferences": row.get("Preferences", ""),
            "personality": row.get("Personality", ""),
            "comm_pref": row.get("Communication Preference", ""),
            "lifetime_value": row.get("Lifetime Value", ""),
            "last_contact": row.get("Last Contact", ""),
            "source": "registry",
            "suppliers": [],
            "bookings": [],
            "dossier_path": None,
            "dossier_text": None,
        }

    # Source 2: Dossier files (enrich existing or add new)
    dossier_data = _load_dossier_data()
    for d in dossier_data:
        for email in d["emails"]:
            if email in registry:
                # Enrich existing
                entry = registry[email]
                entry["dossier_path"] = d["path"]
                entry["dossier_text"] = d["text"]
                entry["suppliers"] = list(set(entry["suppliers"] + d["suppliers"]))
                if d["dobs"] and not entry.get("dob"):
                    entry["dob"] = d["dobs"][0]
            else:
                # New from dossier
                registry[email] = {
                    "name": d["client_name"],
                    "email": email,
                    "phone": "",
                    "dob": d["dobs"][0] if d["dobs"] else "",
                    "vip": False,
                    "source": "dossier",
                    "suppliers": d["suppliers"],
                    "bookings": d["booking_ids"],
                    "dossier_path": d["path"],
                    "dossier_text": d["text"],
                }

    # Source 3: Booking Master (enrich with supplier/booking data)
    for row in _load_booking_master():
        # Try to match by client name against existing registry entries
        client_name = row.get("Client", row.get("client", "")).strip().lower()
        supplier = row.get("Supplier", row.get("supplier", "")).strip()
        booking_id = row.get("Booking ID", row.get("booking_id", "")).strip()

        if client_name and supplier:
            for email, entry in registry.items():
                entry_name = entry.get("name", "").lower()
                if entry_name and (
                    entry_name in client_name or client_name in entry_name
                ):
                    if supplier and supplier not in entry.get("suppliers", []):
                        entry.setdefault("suppliers", []).append(supplier)
                    if booking_id and booking_id not in entry.get("bookings", []):
                        entry.setdefault("bookings", []).append(booking_id)

    logger.info(f"Client registry built: {len(registry)} unique emails")
    return registry


# ============================================================================
# PHASE 1.3 — SUPPLIER LOOKUP
# ============================================================================

def build_supplier_lookup() -> Dict[str, Dict[str, str]]:
    """Load Reference_Suppliers from Sheets.

    Returns dict: domain -> {category, keywords, active}
    """
    try:
        gc = _get_sheets_client()
        ws = gc.open_by_key(SHEETS_ID).worksheet(REFERENCE_SUPPLIERS_TAB)
        rows = ws.get_all_records()
        lookup = {}
        for row in rows:
            domain = row.get("Domain (e.g. rssc.com)", "").strip().lower()
            if not domain:
                continue
            active = str(row.get("Active (Yes/No)", "Yes")).strip().lower()
            if active not in ("yes", "true", "1"):
                continue
            lookup[domain] = {
                "domain": domain,
                "category": row.get("Category (e.g. Cruise Line)", ""),
                "keywords": row.get("Priority Keywords", ""),
            }
        logger.info(f"Supplier lookup: {len(lookup)} active domains")
        return lookup
    except Exception as e:
        logger.error(f"Failed to load Reference_Suppliers: {e}")
        return {}


def _match_supplier(from_addr: str, supplier_lookup: Dict) -> Optional[Dict]:
    """Check if an email sender matches a known supplier domain."""
    # Extract domain from email address
    email_match = re.search(r'@([\w.-]+)', from_addr)
    if not email_match:
        return None
    sender_domain = email_match.group(1).lower()

    # Direct match
    if sender_domain in supplier_lookup:
        return supplier_lookup[sender_domain]

    # Subdomain match (e.g., mail.rssc.com matches rssc.com)
    parts = sender_domain.split(".")
    for i in range(len(parts) - 1):
        parent = ".".join(parts[i:])
        if parent in supplier_lookup:
            return supplier_lookup[parent]

    return None


def _match_client(from_addr: str, client_registry: Dict) -> Optional[Dict]:
    """Check if an email sender matches a known client."""
    email_match = re.search(r'<?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+)>?', from_addr)
    if not email_match:
        return None
    sender_email = email_match.group(1).lower()

    if sender_email == YODA_EMAIL:
        return None  # Don't match self

    return client_registry.get(sender_email)


# ============================================================================
# PHASE 1.4 — EARA FORMAT STAFF PAPER SENDER
# ============================================================================

def send_staff_paper(
    persona_id: str,
    issue: str,
    discussion: str,
    options: Optional[str],
    actions: str,
    subject_prefix: str = "",
) -> Dict[str, Any]:
    """Send a staff paper to Commander's inbox in EARA Constitution format.

    From: persona via concierge@d2mluxury.quest
    To: johnloucks3@gmail.com
    Format: ISSUE / DISCUSSION / OPTIONS / ACTIONS I RECOMMEND TAKING
    """
    persona_name = PERSONA_DISPLAY_NAMES.get(
        persona_id.upper(), PERSONA_DISPLAY_NAMES["CONCIERGE"]
    )

    # Build subject
    subject = f"[{persona_id.upper()}] "
    if subject_prefix:
        subject += f"{subject_prefix}"
    else:
        subject += issue[:80]

    # Build body in EARA format
    body_parts = [
        f"ISSUE:\n{issue}",
        f"\nDISCUSSION:\n{discussion}",
    ]
    if options:
        body_parts.append(f"\nOPTIONS:\n{options}")
    body_parts.append(f"\nACTIONS I RECOMMEND TAKING:\n{actions}")

    # Add attribution
    body_parts.append(
        f"\n---\nStaff Paper from {persona_name}\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M MT')}\n"
        f"Thunderbird Email Intelligence Officer"
    )

    body = "\n".join(body_parts)

    result = gmail_send_with_approval(
        to=YODA_EMAIL,
        subject=subject,
        body=body,
        persona_id=persona_id,
        auto_send=True,
    )

    logger.info(f"Staff paper sent: [{persona_id}] {issue[:60]}")
    return result


# ============================================================================
# PHASE 2 — LLM REASONING (Claude Opus via CLI subprocess)
# ============================================================================

def _call_opus(system_prompt: str, user_prompt: str,
               max_tokens: int = 1200, temperature: float = 0.2,
               max_retries: int = 3) -> str:
    """Call Claude Opus via CLI subprocess for email analysis.

    Uses the Claude Code CLI with Max plan OAuth ($0 cost).
    Strips ANTHROPIC_API_KEY so CLI uses Max plan instead of API credits.
    """
    combined_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"

    # Strip ANTHROPIC_API_KEY so CLI uses Max plan OAuth ($0)
    # Also strip CLAUDECODE to allow subprocess invocation from within Claude Code
    clean_env = {k: v for k, v in os.environ.items()
                 if k not in ("ANTHROPIC_API_KEY", "CLAUDECODE")}

    cmd = [
        CLAUDE_CLI,
        "--print",
        "--model", "haiku",
        "--dangerously-skip-permissions",
        "--output-format", "text",
        "-p", combined_prompt,
    ]

    last_error = None
    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                env=clean_env,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            else:
                stderr = result.stderr.strip()[:200] if result.stderr else "No stderr"
                last_error = RuntimeError(
                    f"Opus CLI error (exit {result.returncode}): {stderr}"
                )
                logger.error(str(last_error))
                if attempt < max_retries - 1:
                    wait = 10 * (attempt + 1)
                    logger.warning(f"Retrying in {wait}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait)
        except subprocess.TimeoutExpired:
            last_error = RuntimeError("Opus CLI timed out after 300s")
            logger.error(str(last_error))
            if attempt < max_retries - 1:
                logger.warning(f"Retrying after timeout (attempt {attempt + 1}/{max_retries})...")
        except Exception as e:
            last_error = e
            logger.error(f"Opus CLI exception: {e}")
            if attempt < max_retries - 1:
                time.sleep(10)

    raise last_error


def _parse_json_response(raw: str) -> Dict[str, Any]:
    """Parse JSON from LLM response, stripping markdown fences."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        logger.error(f"Failed to parse JSON from LLM: {cleaned[:300]}")
        return {"error": "json_parse_failed", "raw": cleaned[:500]}


# ============================================================================
# PHASE 2.1 — SUPPLIER SWEEP
# ============================================================================

SUPPLIER_SYSTEM_PROMPT = """You are the Email Intelligence Officer for Dreams2Memories Travel, LLC, a luxury travel agency.

You are analyzing an email from a KNOWN SUPPLIER. Your job is to determine:
1. What this email is about (sale/promotion, itinerary change, policy update, confirmation, admin, etc.)
2. Which active D2M clients might be affected or could benefit
3. Whether this requires action from the Commander (John "Yoda" Loucks)
4. If there's an OPPORTUNITY to contact clients about a promotion or sale

Return a JSON object:
{
  "email_type": "sale|itinerary_change|policy_update|confirmation|admin|newsletter|other",
  "summary": "2-3 sentence summary of what this email is about",
  "affected_clients": ["last_name1", "last_name2"],
  "opportunity": true/false,
  "opportunity_description": "description of the opportunity or null",
  "risk": true/false,
  "risk_description": "description of the risk or null",
  "action_needed": true/false,
  "urgency": "urgent|normal|low",
  "issue": "one-sentence ISSUE statement for staff paper",
  "discussion": "2-4 sentence DISCUSSION for staff paper",
  "recommended_actions": ["action 1", "action 2"],
  "draft_client_emails": true/false,
  "draft_targets": ["client_email1", "client_email2"]
}

RULES:
- Match client names against the ACTIVE CLIENTS list provided
- If a cruise line is running a sale, check which clients have sailed that line before
- Itinerary changes on active bookings are ALWAYS urgent
- Policy changes that affect insurance, cancellation, or payment terms are important
- Newsletters with no actionable content should have action_needed=false
- Return ONLY valid JSON."""

CLIENT_SYSTEM_PROMPT = """You are the Email Intelligence Officer for Dreams2Memories Travel, LLC, a luxury travel agency.

You are analyzing an email from a KNOWN CLIENT. You have their full dossier with booking details, key dates, and action items.

Your job is to:
1. Understand what the client is asking or communicating
2. Determine the complexity and appropriate response
3. Draft the key points that should be in a response
4. Identify any action items that need tracking

Return a JSON object:
{
  "summary": "2-3 sentence summary of what the client is saying/asking",
  "client_intent": "question|request|confirmation|complaint|information|scheduling",
  "topics": ["insurance", "payment", "logistics", "excursions", etc.],
  "complexity": "low|medium|high",
  "needs_research": true/false,
  "urgency": "urgent|normal|low",
  "sentiment": "positive|neutral|concerned|frustrated",
  "issue": "one-sentence ISSUE statement for staff paper",
  "discussion": "2-4 sentence DISCUSSION with relevant dossier context",
  "recommended_actions": ["action 1", "action 2"],
  "draft_response_points": ["key point 1 for the reply", "key point 2"],
  "action_items": ["trackable action item 1", "trackable action item 2"],
  "dossier_update": "text to append to EMAIL LOG section"
}

RULES:
- Reference specific details from the dossier (dates, amounts, booking IDs)
- If the client asks about insurance, note their age (from DOB), trip value, and deposit date for quoting
- complexity=high triggers escalation to a more powerful model for the draft response
- needs_research=true means the response requires looking up external information
- Always provide concrete draft_response_points, not generic placeholders
- Return ONLY valid JSON."""

GENERAL_SYSTEM_PROMPT = """You are the Email Intelligence Officer for Dreams2Memories Travel, LLC, a luxury travel agency.

You are analyzing an email that is NOT from a known supplier or client. Determine if it's relevant to D2M business.

Return a JSON object:
{
  "relevant": true/false,
  "relevance_reason": "why this matters to D2M or null",
  "category": "prospect|industry_news|personal_travel|referral|spam|other",
  "summary": "1-2 sentence summary",
  "action_needed": true/false,
  "urgency": "urgent|normal|low",
  "issue": "one-sentence ISSUE or null if not relevant",
  "recommended_actions": ["action 1"] or []
}

RULES:
- Prospects asking about travel services ARE relevant
- Industry news about cruise lines, destinations, or travel tech IS relevant
- GEOPOLITICS, DEFENSE, MILITARY, WAR news IS relevant (category=industry_news) — Commander wants multi-domain intel
- POLITICS, POLICY, SOCIAL ISSUES news IS relevant (category=industry_news) — Commander directive: "flooded with info"
- AIRLINE route changes, aviation news IS relevant — cross-ref against client airports
- MARITIME, ports, shipping news IS relevant
- ENERGY, MARKETS news IS relevant — affects travel costs and client destinations
- Weather alerts, natural disasters, health advisories IS relevant — affects active voyages
- Personal emails with no travel/business/news/geopolitical connection are NOT relevant (relevant=false)
- Spam, marketing for non-travel products, automated receipts are NOT relevant
- Newsletters covering world affairs, defense, politics ARE relevant — do NOT filter these out
- When in doubt, mark relevant=true — let the Commander decide
- Return ONLY valid JSON."""


def _build_context_summary(
    client_registry: Dict,
    dossier_data: Optional[List] = None,
) -> str:
    """Build a context summary of active clients for LLM prompts."""
    lines = ["ACTIVE D2M CLIENTS AND BOOKINGS:"]
    seen_names = set()

    for email, info in client_registry.items():
        name = info.get("name", "Unknown")
        if name.lower() in seen_names:
            continue
        seen_names.add(name.lower())

        parts = [f"- {name} ({email})"]
        if info.get("suppliers"):
            parts.append(f"  Suppliers: {', '.join(info['suppliers'])}")
        if info.get("bookings"):
            parts.append(f"  Bookings: {', '.join(info['bookings'][:3])}")
        if info.get("dob"):
            parts.append(f"  DOB: {info['dob']}")
        lines.append("\n".join(parts))

    return "\n".join(lines)


def _read_email(service, msg_id: str) -> Dict[str, Any]:
    """Read a full email message and return clean dict."""
    msg = (
        service.users()
        .messages()
        .get(userId="me", id=msg_id, format="full")
        .execute()
    )
    payload = msg.get("payload", {})
    headers = _extract_headers(
        payload.get("headers", []),
        {"From", "To", "Subject", "Date", "Cc"},
    )
    body = _decode_body(payload)
    if len(body) > 30000:
        body = body[:30000] + "\n... [TRUNCATED]"
    return {
        "id": msg["id"],
        "threadId": msg["threadId"],
        "labels": msg.get("labelIds", []),
        "snippet": msg.get("snippet", ""),
        "headers": headers,
        "body": body,
    }


# ============================================================================
# PHASE 3 — RESPONSE ENGINE
# ============================================================================

def _load_voice_profile() -> str:
    """Load Commander's voice profile for EXEC draft writing."""
    if VOICE_PROFILE_FILE.exists():
        text = VOICE_PROFILE_FILE.read_text(encoding="utf-8")
        # Extract the prompt fragment section
        fragment_match = re.search(
            r'```\n(COMMANDER\'S VOICE PROFILE.*?)```',
            text, re.DOTALL,
        )
        if fragment_match:
            return fragment_match.group(1).strip()
        return text
    return "Write in a professional, warm, semi-formal tone. Sign as John."


DRAFT_RESPONSE_SYSTEM = """You are EXEC (Naia Solberg-Vega) for Dreams2Memories Travel, LLC.
You are drafting a client email response in the Commander's voice.

{voice_profile}

RULES:
- Write ONLY the email body — no subject line, no meta-commentary
- Be substantive — answer their actual question with specific details
- Reference specific dates, amounts, booking numbers from the context provided
- If discussing insurance: include age-based considerations, CFAR window analysis, specific quotes when possible
- If discussing payments: include exact amounts and deadlines
- Keep it concise but thorough — the Commander's voice is warm but precise
- Never salesy. Present information, leave decisions to them.
- Sign off as:
  John

  John A Loucks III
  Owner, Dreams2Memories Travel, LLC
  719-291-0742
  johnloucks3@gmail.com"""


def _draft_client_response(
    email_data: Dict,
    analysis: Dict,
    client_info: Dict,
    use_claude: bool = False,
) -> Optional[str]:
    """Generate a draft client response in Commander's voice."""
    voice_profile = _load_voice_profile()
    system_prompt = DRAFT_RESPONSE_SYSTEM.format(voice_profile=voice_profile)

    # Build rich context
    context_parts = [
        f"CLIENT: {client_info.get('name', 'Unknown')}",
        f"EMAIL: {client_info.get('email', '')}",
    ]
    if client_info.get("dob"):
        context_parts.append(f"DOB: {client_info['dob']}")
    if client_info.get("suppliers"):
        context_parts.append(f"SUPPLIER HISTORY: {', '.join(client_info['suppliers'])}")
    if client_info.get("bookings"):
        context_parts.append(f"BOOKING IDS: {', '.join(client_info['bookings'])}")

    # Include dossier excerpt if available
    dossier_text = client_info.get("dossier_text", "")
    if dossier_text:
        # Truncate for context window (raised to 20K — Claude 1M context is GA)
        if len(dossier_text) > 20000:
            dossier_text = dossier_text[:20000] + "\n... [TRUNCATED]"
        context_parts.append(f"\nFULL DOSSIER:\n{dossier_text}")

    # Include any relevant Commander_Review briefings
    if client_info.get("name"):
        client_name_lower = client_info["name"].lower()
        for f in COMMANDER_REVIEW_DIR.glob("*.md"):
            try:
                review_text = f.read_text(encoding="utf-8")
                if client_name_lower in review_text.lower():
                    excerpt = review_text[:2000]
                    context_parts.append(
                        f"\nCOMMANDER REVIEW ({f.name}):\n{excerpt}"
                    )
                    break  # One briefing is enough context
            except Exception:
                continue

    headers = email_data["headers"]
    user_prompt = (
        "\n".join(context_parts) + "\n\n"
        f"ANALYSIS:\n"
        f"Summary: {analysis.get('summary', '')}\n"
        f"Draft points: {json.dumps(analysis.get('draft_response_points', []))}\n\n"
        f"EMAIL TO RESPOND TO:\n"
        f"From: {headers.get('From', '')}\n"
        f"Subject: {headers.get('Subject', '')}\n"
        f"Date: {headers.get('Date', '')}\n"
        f"Body:\n{email_data['body']}\n\n"
        f"Write the reply now."
    )

    try:
        if use_claude:
            return _call_claude_sonnet(system_prompt, user_prompt)
        else:
            return _call_opus(system_prompt, user_prompt, max_tokens=1500)
    except Exception as e:
        logger.error(f"Draft response generation failed: {e}")
        return None


def _create_gmail_draft(service, to: str, subject: str, body: str,
                        thread_id: Optional[str] = None) -> Optional[str]:
    """Create a Gmail draft reply."""
    from email.mime.text import MIMEText

    mime_msg = MIMEText(body, "plain")
    mime_msg["to"] = to
    mime_msg["from"] = OPS_EMAIL  # D2M ops sends drafts — not Commander personal
    mime_msg["subject"] = f"Re: {subject}" if not subject.startswith("Re:") else subject

    raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode("utf-8")
    draft_body = {"message": {"raw": raw}}
    if thread_id:
        draft_body["message"]["threadId"] = thread_id

    try:
        draft = service.users().drafts().create(
            userId="me", body=draft_body
        ).execute()
        return draft["id"]
    except Exception as e:
        logger.error(f"Gmail draft creation failed: {e}")
        return None


# ============================================================================
# DOSSIER WRITER
# ============================================================================

def _append_to_dossier(dossier_path: str, email_data: Dict, summary: str,
                       action_items: Optional[List[str]] = None):
    """Append email summary to dossier EMAIL LOG and optionally OPEN ACTION ITEMS."""
    path = Path(dossier_path)
    if not path.exists():
        logger.warning(f"Dossier not found: {dossier_path}")
        return

    headers = email_data["headers"]
    date_str = headers.get("Date", "")
    try:
        # Try to parse into short format
        cleaned = re.sub(r"\s*\([A-Z]+\)\s*$", "", date_str)
        for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%d %b %Y %H:%M:%S %z"):
            try:
                dt = datetime.strptime(cleaned, fmt)
                short_date = dt.strftime("%b %d")
                break
            except ValueError:
                continue
        else:
            short_date = date_str[:10]
    except Exception:
        short_date = date_str[:10]

    sender = headers.get("From", "unknown")
    sender_short = sender.split("<")[0].strip().strip('"') or sender
    subject = headers.get("Subject", "(no subject)")

    log_entry = f"\n**{short_date} — {sender_short}** (Re: {subject})\n> {summary}\n"

    content = path.read_text(encoding="utf-8")

    # Insert into EMAIL LOG section
    email_log_pattern = r"(### EMAIL LOG[^\n]*\n)"
    match = re.search(email_log_pattern, content)
    if match:
        insert_pos = match.end()
        rest = content[insert_pos:]
        next_section = re.search(r"\n---\n|\n### ", rest)
        if next_section:
            insert_pos = insert_pos + next_section.start()
        else:
            insert_pos = len(content)
        content = content[:insert_pos] + log_entry + content[insert_pos:]
    else:
        content += f"\n\n### EMAIL LOG\n{log_entry}"

    # Add action items if provided
    if action_items:
        for item in action_items:
            action_entry = f"\n- [ ] {item} (auto-intel {short_date})"
            action_pattern = r"(### OPEN ACTION ITEMS\n)"
            amatch = re.search(action_pattern, content)
            if amatch:
                insert_pos = amatch.end()
                rest = content[insert_pos:]
                lines = rest.split("\n")
                offset = 0
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith(("- [", "* [")) or re.match(r"^\d+\.\s", stripped):
                        offset += len(line) + 1
                    else:
                        break
                insert_pos += offset
                content = content[:insert_pos] + action_entry + "\n" + content[insert_pos:]
            else:
                content += f"\n\n### OPEN ACTION ITEMS{action_entry}\n"

    path.write_text(content, encoding="utf-8")
    logger.info(f"  -> Dossier updated: {path.name}")


# ============================================================================
# PHASE 2.1/2.2/2.3 — THE THREE SWEEPS
# ============================================================================

def _consult_a2_supplier_intel(
    email_data: Dict, supplier_info: Dict, analysis: Dict,
) -> Optional[str]:
    """Consult A2 (Dembe) for market intelligence assessment on supplier email.

    A2 analyzes: pricing trends, availability shifts, competitive positioning,
    itinerary modifications, fare alerts — anything with market intel value.

    Uses Claude Opus (Max plan).
    Returns A2's assessment text, or None on failure.
    """
    headers = email_data["headers"]

    a2_system_prompt = (
        "You are Lt Col Marcus 'Wraith' Dembe (A2), Research & Market Intelligence "
        "for Dreams2Memories Travel, LLC.\n\n"
        "You are reviewing a supplier email that has already been triaged. Your job is to "
        "provide a MARKET INTELLIGENCE ASSESSMENT — the strategic layer that COS and EXEC "
        "need to make decisions.\n\n"
        "Focus on:\n"
        "1. PRICING TRENDS — Is this a price increase, decrease, flash sale? How does it "
        "compare to what we've seen from this supplier recently?\n"
        "2. AVAILABILITY SIGNALS — Are they pushing unsold inventory? Is a sailing close to "
        "selling out? Repositioning cruises?\n"
        "3. COMPETITIVE POSITIONING — Does this change how we should position this supplier "
        "vs. alternatives (e.g., Silversea vs. Regent for a Mediterranean itinerary)?\n"
        "4. CLIENT OPPORTUNITIES — Which active D2M clients could benefit, and why?\n"
        "5. RISK INDICATORS — Itinerary changes, policy shifts, or cancellation signals.\n\n"
        "Speak in assessments: 'high confidence,' 'moderate confidence,' 'insufficient data.' "
        "Be precise and evidence-first. 3-6 sentences max."
    )

    a2_user_prompt = (
        f"SUPPLIER: {supplier_info['domain']} ({supplier_info['category']})\n"
        f"EMAIL SUBJECT: {headers.get('Subject', '')}\n"
        f"EMAIL DATE: {headers.get('Date', '')}\n\n"
        f"TRIAGE SUMMARY: {analysis.get('summary', 'N/A')}\n"
        f"EMAIL TYPE: {analysis.get('email_type', 'unknown')}\n"
        f"OPPORTUNITY: {analysis.get('opportunity_description', 'None identified')}\n"
        f"RISK: {analysis.get('risk_description', 'None identified')}\n"
        f"AFFECTED CLIENTS: {', '.join(analysis.get('affected_clients', []))}\n\n"
        f"EMAIL BODY:\n{email_data['body'][:4000]}\n\n"
        f"Provide your market intelligence assessment."
    )

    try:
        a2_response = _call_opus(
            a2_system_prompt, a2_user_prompt,
            max_tokens=600, temperature=0.2,
        )
        logger.info(f"  A2 (Dembe) market intel assessment complete ({len(a2_response)} chars)")
        return a2_response
    except Exception as e:
        logger.error(f"  A2 (Dembe) consultation failed: {e}")
        return None


def _process_supplier_email(
    service, email_data: Dict, supplier_info: Dict,
    client_registry: Dict, context_summary: str,
) -> Dict[str, Any]:
    """Process a supplier email: analyze, consult A2, send staff paper, draft client emails."""

    headers = email_data["headers"]
    user_prompt = (
        f"SUPPLIER: {supplier_info['domain']} ({supplier_info['category']})\n"
        f"PRIORITY KEYWORDS: {supplier_info['keywords']}\n\n"
        f"{context_summary}\n\n"
        f"EMAIL:\n"
        f"From: {headers.get('From', '')}\n"
        f"Subject: {headers.get('Subject', '')}\n"
        f"Date: {headers.get('Date', '')}\n"
        f"Body:\n{email_data['body']}"
    )

    raw_response = _call_opus(SUPPLIER_SYSTEM_PROMPT, user_prompt)
    analysis = _parse_json_response(raw_response)

    result = {
        "type": "supplier",
        "supplier": supplier_info["domain"],
        "category": supplier_info["category"],
        "analysis": analysis,
        "a2_intel": None,
        "staff_paper_sent": False,
        "drafts_created": 0,
    }

    if analysis.get("error"):
        return result

    # --- A2 (Dembe) Market Intelligence Consultation ---
    # A2 gets early visibility on ALL supplier emails that have actionable content:
    # pricing changes, availability updates, itinerary mods, fare alerts, competitor intel
    a2_assessment = None
    if analysis.get("action_needed") or analysis.get("opportunity") or analysis.get("risk"):
        a2_assessment = _consult_a2_supplier_intel(email_data, supplier_info, analysis)
        result["a2_intel"] = a2_assessment

    # Send staff paper if action needed or opportunity detected
    if analysis.get("action_needed") or analysis.get("opportunity") or analysis.get("risk"):
        persona = "A2" if not analysis.get("risk") else "A10"
        options_text = None
        if analysis.get("opportunity"):
            options_text = (
                f"1. Draft and send promotional emails to matched clients\n"
                f"2. Note the sale for next client conversation\n"
                f"3. No action — clients not a fit"
            )

        # Enrich discussion with A2's market intel assessment
        discussion = analysis.get("discussion", analysis.get("summary", ""))
        if a2_assessment:
            discussion += (
                f"\n\n--- A2 (DEMBE) MARKET INTELLIGENCE ASSESSMENT ---\n"
                f"{a2_assessment}"
            )

        send_staff_paper(
            persona_id=persona,
            issue=analysis.get("issue", f"Supplier email from {supplier_info['domain']}"),
            discussion=discussion,
            options=options_text,
            actions="\n".join(
                f"{i+1}. {a}" for i, a in
                enumerate(analysis.get("recommended_actions", ["Review email"]))
            ),
            subject_prefix=f"Supplier Intel: {headers.get('Subject', '')[:50]}",
        )
        result["staff_paper_sent"] = True

    # Draft client emails if opportunity matches clients
    if analysis.get("draft_client_emails") and analysis.get("draft_targets"):
        voice_profile = _load_voice_profile()
        for target_email in analysis["draft_targets"]:
            client = client_registry.get(target_email.lower())
            if not client:
                continue

            # Generate personalized promotion email
            promo_prompt = (
                f"Write a short, personalized email from John Loucks to {client.get('name', 'client')} "
                f"about this promotion/opportunity:\n\n"
                f"{analysis.get('opportunity_description', analysis.get('summary', ''))}\n\n"
                f"The client has previously sailed with: {', '.join(client.get('suppliers', []))}\n\n"
                f"Keep it casual, warm, not salesy. Present the info and let them decide.\n"
                f"{voice_profile}"
            )
            try:
                draft_body = _call_opus(
                    "You write emails in John Loucks' voice. Short, warm, not salesy.",
                    promo_prompt, max_tokens=800,
                )
                draft_id = _create_gmail_draft(
                    service, target_email,
                    f"Thought of you — {headers.get('Subject', 'travel opportunity')[:40]}",
                    draft_body,
                )
                if draft_id:
                    result["drafts_created"] += 1
            except Exception as e:
                logger.error(f"Failed to draft promo email to {target_email}: {e}")

    return result


def _process_client_email(
    service, email_data: Dict, client_info: Dict,
) -> Dict[str, Any]:
    """Process a client email: analyze, draft response, send staff paper, update dossier."""

    headers = email_data["headers"]

    # Build client context for LLM
    dossier_excerpt = ""
    if client_info.get("dossier_text"):
        dt = client_info["dossier_text"]
        dossier_excerpt = dt[:5000] if len(dt) > 5000 else dt

    user_prompt = (
        f"CLIENT: {client_info.get('name', 'Unknown')}\n"
        f"EMAIL: {client_info.get('email', '')}\n"
        f"DOB: {client_info.get('dob', 'unknown')}\n"
        f"SUPPLIERS: {', '.join(client_info.get('suppliers', []))}\n"
        f"VIP: {client_info.get('vip', False)}\n\n"
        f"CLIENT DOSSIER:\n{dossier_excerpt}\n\n"
        f"EMAIL:\n"
        f"From: {headers.get('From', '')}\n"
        f"Subject: {headers.get('Subject', '')}\n"
        f"Date: {headers.get('Date', '')}\n"
        f"Body:\n{email_data['body']}"
    )

    raw_response = _call_opus(CLIENT_SYSTEM_PROMPT, user_prompt)
    analysis = _parse_json_response(raw_response)

    result = {
        "type": "client",
        "client": client_info.get("name", "Unknown"),
        "email": client_info.get("email", ""),
        "analysis": analysis,
        "staff_paper_sent": False,
        "draft_created": False,
        "dossier_updated": False,
        "escalated": False,
    }

    if analysis.get("error"):
        return result

    # Determine if escalation needed
    use_claude = (
        analysis.get("complexity") == "high" or
        analysis.get("needs_research", False)
    )
    if use_claude:
        result["escalated"] = True
        logger.info(f"  Escalating to Claude Sonnet (complexity={analysis.get('complexity')})")

    # Draft response
    draft_body = _draft_client_response(
        email_data, analysis, client_info, use_claude=use_claude,
    )
    if draft_body:
        # Extract reply-to address
        from_addr = headers.get("From", "")
        email_match = re.search(r'<?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+)>?', from_addr)
        reply_to = email_match.group(1) if email_match else from_addr

        draft_id = _create_gmail_draft(
            service, reply_to,
            headers.get("Subject", ""),
            draft_body,
            thread_id=email_data.get("threadId"),
        )
        if draft_id:
            result["draft_created"] = True
            result["draft_id"] = draft_id

    # Send staff paper (companion to the draft)
    persona = "A3"  # Moreau owns client ops
    if analysis.get("urgency") == "urgent":
        persona = "COS"
    elif "insurance" in str(analysis.get("topics", [])):
        persona = "A9"  # Harlan for financial/insurance

    options_text = None
    if len(analysis.get("recommended_actions", [])) > 1:
        options_text = "\n".join(
            f"{i+1}. {a}" for i, a in
            enumerate(analysis.get("recommended_actions", []))
        )

    send_staff_paper(
        persona_id=persona,
        issue=analysis.get("issue", f"Client email from {client_info.get('name', 'Unknown')}"),
        discussion=analysis.get("discussion", analysis.get("summary", "")),
        options=options_text,
        actions="\n".join(
            f"{i+1}. {a}" for i, a in
            enumerate(analysis.get("recommended_actions", ["Review draft and send"]))
        ),
        subject_prefix=f"Client: {client_info.get('name', '')} — {headers.get('Subject', '')[:40]}",
    )
    result["staff_paper_sent"] = True

    # Update dossier
    if client_info.get("dossier_path"):
        _append_to_dossier(
            client_info["dossier_path"],
            email_data,
            analysis.get("dossier_update", analysis.get("summary", "")),
            analysis.get("action_items"),
        )
        result["dossier_updated"] = True

    return result


def _process_general_email(
    service, email_data: Dict, context_summary: str,
) -> Dict[str, Any]:
    """Process a general email (not supplier, not known client)."""

    headers = email_data["headers"]
    user_prompt = (
        f"{context_summary}\n\n"
        f"EMAIL:\n"
        f"From: {headers.get('From', '')}\n"
        f"Subject: {headers.get('Subject', '')}\n"
        f"Date: {headers.get('Date', '')}\n"
        f"Body:\n{email_data['body']}"
    )

    raw_response = _call_opus(GENERAL_SYSTEM_PROMPT, user_prompt)
    analysis = _parse_json_response(raw_response)

    result = {
        "type": "general",
        "analysis": analysis,
        "staff_paper_sent": False,
    }

    if analysis.get("error"):
        return result

    # Only send staff paper if relevant and action needed
    if analysis.get("relevant") and analysis.get("action_needed"):
        send_staff_paper(
            persona_id="COS",
            issue=analysis.get("issue", f"Email from {headers.get('From', 'unknown')}"),
            discussion=analysis.get("summary", ""),
            options=None,
            actions="\n".join(
                f"{i+1}. {a}" for i, a in
                enumerate(analysis.get("recommended_actions", ["Review"]))
            ),
            subject_prefix=f"General: {headers.get('Subject', '')[:50]}",
        )
        result["staff_paper_sent"] = True

    return result


# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

def run_email_intel_sweep(
    lookback_hours: int = SWEEP_LOOKBACK_HOURS,
    max_emails: int = MAX_EMAILS_PER_SWEEP,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Main entry point: scan inbox, classify, analyze, act.

    Three sweeps in one pass:
      1. Match sender against supplier domains → supplier sweep
      2. Match sender against client registry → client sweep
      3. Everything else → general sweep (only if relevant)

    Args:
        lookback_hours: How far back to scan (default 6h)
        max_emails: Max emails to process per sweep
        dry_run: If True, analyze but don't send papers/drafts/update dossiers

    Returns:
        Summary dict with counts and per-email results
    """
    logger.info("=" * 60)
    logger.info("EMAIL INTELLIGENCE OFFICER — SWEEP STARTING")
    logger.info("=" * 60)

    state = _load_state()
    processed_ids = set(state.get("processed_ids", []))

    # --- FAST PATH: Connect to Gmail and check for new emails FIRST ---
    # Skip expensive registry builds if there is nothing new to process.
    service = _get_gmail_service()

    # Search for recent unread emails (broad scan)
    # Skip promotions and social categories, skip self-sent
    query = (
        f"is:unread "
        f"newer_than:{lookback_hours}h "
        f"-from:me "
        f"-category:promotions "
        f"-category:social "
        f"-label:THUNDERBIRD-Processed "
    )

    try:
        results = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_emails)
            .execute()
        )
    except HttpError as e:
        logger.error(f"Gmail search failed: {e}")
        return {"status": "error", "error": str(e)}

    message_stubs = results.get("messages", [])
    logger.info(f"Found {len(message_stubs)} unread emails in last {lookback_hours}h")

    # Early exit: no new emails or all already processed — skip registry builds
    new_stubs = [s for s in message_stubs if s["id"] not in processed_ids]
    if not new_stubs:
        logger.info("No new emails to process — exiting early (skipping registry builds).")
        return {
            "status": "ok",
            "emails_found": len(message_stubs),
            "new_to_process": 0,
            "skipped": len(message_stubs),
            "results": [],
        }

    # Build registries (only when there are new emails to process)
    logger.info("Building client registry (3-source merge)...")
    client_registry = build_client_registry()
    logger.info("Building supplier lookup...")
    supplier_lookup = build_supplier_lookup()
    context_summary = _build_context_summary(client_registry)

    sweep_results = []
    stats = {"supplier": 0, "client": 0, "general": 0, "skipped": len(message_stubs) - len(new_stubs),
             "drafts": 0, "papers": 0}

    for stub in new_stubs:
        msg_id = stub["id"]

        # Read full message
        try:
            email_data = _read_email(service, msg_id)
        except HttpError as e:
            logger.error(f"Failed to read {msg_id}: {e}")
            continue

        from_addr = email_data["headers"].get("From", "")
        subject = email_data["headers"].get("Subject", "(no subject)")
        logger.info(f"\n--- Processing: {subject[:60]} from {from_addr[:40]}")

        # Classify: supplier, client, or general
        supplier_match = _match_supplier(from_addr, supplier_lookup)
        client_match = _match_client(from_addr, client_registry)

        try:
            if supplier_match:
                logger.info(f"  SUPPLIER: {supplier_match['domain']} ({supplier_match['category']})")
                if not dry_run:
                    result = _process_supplier_email(
                        service, email_data, supplier_match,
                        client_registry, context_summary,
                    )
                else:
                    result = {"type": "supplier", "dry_run": True}
                stats["supplier"] += 1

            elif client_match:
                logger.info(f"  CLIENT: {client_match.get('name', 'Unknown')}")
                if not dry_run:
                    result = _process_client_email(
                        service, email_data, client_match,
                    )
                else:
                    result = {"type": "client", "dry_run": True}
                stats["client"] += 1

            else:
                logger.info("  GENERAL: unknown sender")
                if not dry_run:
                    result = _process_general_email(
                        service, email_data, context_summary,
                    )
                else:
                    result = {"type": "general", "dry_run": True}
                stats["general"] += 1

            # Track stats
            if result.get("staff_paper_sent"):
                stats["papers"] += 1
            if result.get("draft_created") or result.get("drafts_created", 0) > 0:
                stats["drafts"] += result.get("drafts_created", 1 if result.get("draft_created") else 0)

            result["message_id"] = msg_id
            result["subject"] = subject
            result["from"] = from_addr
            sweep_results.append(result)

            # Only mark as processed on SUCCESS
            processed_ids.add(msg_id)

        except Exception as e:
            logger.error(f"Processing failed for {msg_id}: {traceback.format_exc()}")
            sweep_results.append({
                "message_id": msg_id,
                "subject": subject,
                "from": from_addr,
                "type": "error",
                "error": str(e),
            })
            # NOT marked as processed — will be retried on next sweep

        # Throttle between emails to avoid rate limiting
        if not dry_run:
            time.sleep(2)

    # Save state
    state["processed_ids"] = list(processed_ids)
    state["last_run"] = datetime.now().isoformat()
    state["stats"]["total"] += len(sweep_results)
    state["stats"]["supplier"] += stats["supplier"]
    state["stats"]["client"] += stats["client"]
    state["stats"]["general"] += stats["general"]
    state["stats"]["skipped"] += stats["skipped"]
    state["stats"]["drafts_created"] += stats["drafts"]
    state["stats"]["staff_papers_sent"] += stats["papers"]

    if not dry_run:
        _save_state(state)

    summary = {
        "status": "success",
        "dry_run": dry_run,
        "sweep_time": datetime.now().isoformat(),
        "lookback_hours": lookback_hours,
        "emails_found": len(message_stubs),
        "processed": len(sweep_results),
        "skipped": stats["skipped"],
        "supplier_emails": stats["supplier"],
        "client_emails": stats["client"],
        "general_emails": stats["general"],
        "drafts_created": stats["drafts"],
        "staff_papers_sent": stats["papers"],
        "results": sweep_results,
    }

    logger.info(f"\n{'=' * 60}")
    logger.info(f"SWEEP COMPLETE — {len(sweep_results)} processed")
    logger.info(f"  Supplier: {stats['supplier']} | Client: {stats['client']} | General: {stats['general']}")
    logger.info(f"  Drafts: {stats['drafts']} | Staff Papers: {stats['papers']}")
    logger.info(f"{'=' * 60}")

    return summary


# ============================================================================
# PHASE 4 — VOICE PROFILE REFRESH
# ============================================================================

def refresh_voice_profile(months_back: int = 1, max_emails: int = 200) -> Dict[str, Any]:
    """Survey Commander's sent emails and update my_voice_profile.md.

    Args:
        months_back: How many months of sent mail to analyze (default 1, use 4 for bootstrap)
        max_emails: Max sent emails to analyze

    Returns:
        Summary with email count and profile update status
    """
    logger.info(f"Voice profile refresh: {months_back} months back, max {max_emails} emails")

    service = _get_gmail_service()

    # Search sent mail
    after_date = (datetime.now() - timedelta(days=months_back * 30)).strftime("%Y/%m/%d")
    query = f"in:sent after:{after_date}"

    try:
        results = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_emails)
            .execute()
        )
    except HttpError as e:
        logger.error(f"Sent mail search failed: {e}")
        return {"status": "error", "error": str(e)}

    message_stubs = results.get("messages", [])
    logger.info(f"Found {len(message_stubs)} sent emails")

    # Collect email bodies
    email_samples = []
    for stub in message_stubs:
        try:
            msg = service.users().messages().get(
                userId="me", id=stub["id"], format="full"
            ).execute()
            payload = msg.get("payload", {})
            body = _decode_body(payload)
            headers_raw = payload.get("headers", [])
            to_header = next(
                (h["value"] for h in headers_raw if h["name"] == "To"), ""
            )

            # Skip auto-generated, self-emails, and very short messages
            if body and len(body) > 50 and YODA_EMAIL not in to_header:
                # Truncate individual emails
                email_samples.append(body[:1500])
        except Exception:
            continue

    if not email_samples:
        return {"status": "no_emails", "count": 0}

    logger.info(f"Analyzing {len(email_samples)} sent email samples")

    # Analyze voice patterns via Claude Opus
    # Split into batches for manageable processing
    batch_size = 20
    all_analyses = []

    for i in range(0, len(email_samples), batch_size):
        batch = email_samples[i:i + batch_size]
        combined = "\n\n---EMAIL---\n\n".join(batch)

        analysis_prompt = (
            f"Analyze these {len(batch)} sent emails from John Loucks, owner of "
            f"Dreams2Memories Travel, a luxury travel agency. He goes by 'Yoda.'\n\n"
            f"Identify patterns in:\n"
            f"1. Opening style (greetings, how he addresses people)\n"
            f"2. Closing style (sign-offs)\n"
            f"3. Sentence structure (length, complexity)\n"
            f"4. Tone (primary and secondary tones)\n"
            f"5. Favorite phrases and expressions\n"
            f"6. What he NEVER does\n"
            f"7. How he handles good news vs bad news vs urgent matters\n"
            f"8. Formatting preferences (bold, lists, etc.)\n\n"
            f"EMAILS:\n{combined}"
        )

        for attempt in range(3):
            try:
                batch_result = _call_opus(
                    "You are a writing style analyst. Be specific and cite examples.",
                    analysis_prompt,
                    max_tokens=1500,
                )
                all_analyses.append(batch_result)
                break
            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    wait = 15 * (attempt + 1)
                    logger.warning(f"Rate limited on batch {i}, waiting {wait}s...")
                    time.sleep(wait)
                else:
                    logger.error(f"Voice analysis batch {i} failed: {e}")
                    break

    if not all_analyses:
        return {"status": "analysis_failed", "count": len(email_samples)}

    # Synthesize into final voice profile
    synthesis_prompt = (
        f"Synthesize these {len(all_analyses)} voice analyses into a single, comprehensive "
        f"voice profile for John 'Yoda' Loucks.\n\n"
        f"Format the output EXACTLY like this:\n\n"
        f"# Your Voice — John Loucks\n"
        f"## The Big Picture\n[overall style summary]\n\n"
        f"## How You Open\n[opening patterns with examples]\n\n"
        f"## How You Close\n[closing patterns]\n\n"
        f"## Sentence DNA\n[structure and complexity]\n\n"
        f"## Tone & Temperature\n[primary/secondary tones]\n\n"
        f"## Your Go-To Moves\n[favorite phrases, patterns]\n\n"
        f"## What You Never Do\n[anti-patterns]\n\n"
        f"## The Signature\n[unique identifying traits]\n\n"
        f"Then add a '## Prompt Fragment (for persona injection)' section with "
        f"a single paragraph prompt that captures all the above rules.\n\n"
        f"ANALYSES:\n\n" + "\n\n---\n\n".join(all_analyses)
    )

    try:
        profile_text = _call_opus(
            "You are a writing style expert. Create a precise, actionable voice profile.",
            synthesis_prompt,
            max_tokens=2000,
        )

        # Add metadata
        profile_text += (
            f"\n\n---\n\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
            f"{len(email_samples)} sent emails analyzed | "
            f"Model: Claude Opus (Max plan)*\n"
        )

        # Write profile
        VOICE_PROFILE_FILE.write_text(profile_text, encoding="utf-8")
        logger.info(f"Voice profile updated: {VOICE_PROFILE_FILE}")

        return {
            "status": "success",
            "emails_analyzed": len(email_samples),
            "months_back": months_back,
            "profile_path": str(VOICE_PROFILE_FILE),
        }

    except Exception as e:
        logger.error(f"Voice profile synthesis failed: {e}")
        return {"status": "synthesis_failed", "error": str(e)}


# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================

def register_email_intel_tools(mcp_server):
    """Register Email Intelligence Officer MCP tools."""
    from pydantic import Field as PydanticField

    @mcp_server.tool(
        name="run_email_intel_sweep",
        annotations={"title": "Run Email Intelligence Sweep", "readOnlyHint": False},
    )
    async def run_email_intel_sweep_tool(
        lookback_hours: int = PydanticField(
            6, description="How many hours back to scan (default 6)"
        ),
        dry_run: bool = PydanticField(
            False, description="If true, analyze only — no drafts, papers, or dossier updates"
        ),
    ) -> str:
        """Proactive email intelligence sweep. Scans ALL inbox email,
        classifies as supplier/client/general, generates analysis,
        drafts responses, sends staff papers to Commander, updates dossiers.

        Runs automatically on schedule but can be triggered manually.
        """
        try:
            result = run_email_intel_sweep(
                lookback_hours=lookback_hours,
                dry_run=dry_run,
            )
            return json.dumps(result, indent=2, default=str)
        except Exception as e:
            logger.error(f"Email intel sweep error: {e}")
            return json.dumps({"error": str(e), "type": "sweep_error"})

    @mcp_server.tool(
        name="email_intel_status",
        annotations={"title": "Email Intel Status", "readOnlyHint": True},
    )
    async def email_intel_status_tool() -> str:
        """View Email Intelligence Officer status — last run, stats, registry sizes."""
        try:
            state = _load_state()
            client_count = len(build_client_registry())
            supplier_count = len(build_supplier_lookup())

            return json.dumps({
                "status": "success",
                "last_run": state.get("last_run"),
                "lifetime_stats": state.get("stats", {}),
                "processed_ids_count": len(state.get("processed_ids", [])),
                "client_registry_size": client_count,
                "supplier_registry_size": supplier_count,
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "type": "status_error"})

    @mcp_server.tool(
        name="refresh_voice_profile",
        annotations={"title": "Refresh Commander Voice Profile", "readOnlyHint": False},
    )
    async def refresh_voice_profile_tool(
        months_back: int = PydanticField(
            1, description="Months of sent mail to analyze (use 4 for bootstrap)"
        ),
    ) -> str:
        """Analyze Commander's sent emails and update my_voice_profile.md.
        Use months_back=4 for initial bootstrap from 4 months of sent mail.
        """
        try:
            result = refresh_voice_profile(months_back=months_back)
            return json.dumps(result, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e), "type": "voice_error"})

    logger.info("Email Intelligence Officer tools registered (sweep, status, voice_profile)")


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import sys

    if "--sweep" in sys.argv:
        dry_run = "--dry-run" in sys.argv
        hours = 6
        for arg in sys.argv[1:]:
            if arg.startswith("--hours="):
                hours = int(arg.split("=", 1)[1])

        result = run_email_intel_sweep(lookback_hours=hours, dry_run=dry_run)
        print(json.dumps(result, indent=2, default=str))

    elif "--voice-bootstrap" in sys.argv:
        result = refresh_voice_profile(months_back=4, max_emails=500)
        print(json.dumps(result, indent=2, default=str))

    elif "--voice-refresh" in sys.argv:
        result = refresh_voice_profile(months_back=1)
        print(json.dumps(result, indent=2, default=str))

    elif "--status" in sys.argv:
        state = _load_state()
        print(json.dumps(state, indent=2, default=str))

    elif "--test-registries" in sys.argv:
        print("Building client registry...")
        cr = build_client_registry()
        print(f"Client registry: {len(cr)} entries")
        for email, info in list(cr.items())[:5]:
            print(f"  {email}: {info.get('name')} | suppliers={info.get('suppliers')}")

        print("\nBuilding supplier lookup...")
        sl = build_supplier_lookup()
        print(f"Supplier lookup: {len(sl)} domains")
        for domain, info in list(sl.items())[:5]:
            print(f"  {domain}: {info['category']} | keywords={info['keywords'][:40]}")

    else:
        print("Thunderbird Email Intelligence Officer")
        print("=" * 40)
        print("Usage:")
        print("  --sweep              Run full email intelligence sweep")
        print("  --sweep --dry-run    Analyze only, no actions")
        print("  --sweep --hours=12   Scan last 12 hours")
        print("  --voice-bootstrap    Build voice profile from 4 months of sent mail")
        print("  --voice-refresh      Weekly voice profile update (1 month)")
        print("  --status             Show last run stats")
        print("  --test-registries    Test client + supplier registry loading")
