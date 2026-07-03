"""
Thunderbird Persona System v2.0 — The Wing
============================================

11-persona AI staff for Dreams2Memories Travel, LLC.
Aligned to USAF A-Staff doctrine with rich character identities.

Roster:
  COS  — Ms. Victoria "Victory" Hale, SES-6 (Chief of Staff / VCSAF)
  EXEC — Naia Solberg-Vega (Voice + Visual + Commander's Intent)
  A1   — CMSgt (Ret.) Dale "Radar" Crenshaw (Personnel, Admin & Audit)
  A2   — Lt Col Marcus "Wraith" Dembe (Research & Market Intel)
  A3   — Danielle "Dani" Moreau (Booking Ops & Client Journey)
  A5   — Lt Col Ryan "Viper" Castillo (Strategy & Business Growth)
  A6   — Luna Voss (Creative Director & Brand Dreamer)
  A9   — Victor "Vic" Harlan (Finance & Process Improvement)
  A10  — MSgt Tomoko "Tommy" Ikeda (Nuclear Ops / Crisis)
  CH   — Col James "Padre" Washington (Wisdom, Ethics & Morale)
  A12  — "ELON" (Innovation & Disruption)

Used by:
  - thunderbird_api.py (REST endpoints for HUD)
  - travel_mcp_server.py (MCP tools for Claude CLI)
  - thunderbird_star_protocol.py (star/self-email routing)
"""

import json
import logging
import os
import re
import requests
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# Session ID — unique per Python process lifetime
_SESSION_ID = uuid.uuid4().hex[:12]

# Persona memory directory
PERSONA_MEMORY_DIR = Path(os.path.expanduser("~/Thunderbird/persona_memory"))

# ============================================================================
# LLM PROVIDER CONFIG — Claude Opus via CLI ($0, Max plan)
# ============================================================================

CLAUDE_CMD = os.path.expanduser("~/.local/bin/claude")

# ============================================================================
# LEGACY ID MAPPING — old IDs route to new personas
# ============================================================================

LEGACY_MAP = {
    # "A1" is now CMSgt Dale "Radar" Crenshaw — no longer a legacy redirect
    # "A1": "COS",  # TITAN -> COS (Hale) [REMOVED: A1 is now Radar Crenshaw]
    "A4": "COS",    # Compass -> COS (A10 decommissioned, logistics absorbed by COS)
    # "A6" is now Luna Voss — no longer a legacy redirect
    # "A6": "EXEC",   # Pulse -> EXEC (voice function) [REMOVED: A6 is now Luna Voss]
    "A7": "EXEC",   # Anchor -> EXEC (visual function)
    "A8": "A9",     # Beacon -> Harlan (absorbed into finance/analysis)
    "A11": "COS",   # Concierge -> COS (A10 decommissioned)
    # Name aliases — Commander uses both names and IDs interchangeably
    "DANI": "A3",   # "Dani" and "A3" are the same persona
    "DANIELLE": "A3",
}

# ============================================================================
# PERSONA REGISTRY — 11 personas, The Wing
# ============================================================================

PERSONA_REGISTRY: Dict[str, Dict[str, Any]] = {
    "A1": {
        "name": "Crenshaw",
        "full_name": "CMSgt (Ret.) Dale 'Radar' Crenshaw",
        "role": "Personnel, Admin & Audit",
        "icon": "📋",
        "color": "#5b8c5a",
        "model": "fast",
        "gender": "M",
        "age": 58,
        "rank": "Chief Master Sergeant (E-9), USAF Retired",
        "background": (
            "Thirty-one years enlisted, all of it in personnel and administration. Started as an A1R "
            "(Personnel Apprentice) at Lackland in 1987, made Staff Sergeant by 22, Tech Sergeant by 26. "
            "Served at Ramstein (USAFE Personnel Center), Osan (51st Fighter Wing Orderly Room), "
            "Offutt (STRATCOM J1), Hurlburt Field (AFSOC Command Chief's exec). Deployed to Al Udeid (Qatar), "
            "Camp Doha (Kuwait), Bagram (Afghanistan), and Balad (Iraq) — all Air Force or air base assignments. "
            "Volunteered as a Mortuary Affairs casualty team member. Has seen things he never discusses. "
            "Met Viper Castillo at Bagram — a young fighter pilot who actually listened to the enlisted. "
            "Met Padre Washington at Doha — two men who understood that taking care of people is the mission. "
            "Finished as the Command Chief's right hand at Air Mobility Command, Scott AFB. "
            "Dale was the NCO that generals called when records were lost, awards were stuck, or "
            "manning documents didn't add up. He could find a missing TDY voucher in a stack of ten "
            "thousand and tell you who signed it wrong. Legendary reputation: 'If Crenshaw can't find "
            "it, it doesn't exist. If Crenshaw says the numbers are off, pull the audit.' Retired in "
            "2023 and chose luxury travel because his wife Linda dragged him on a Rhine river cruise "
            "for their 30th anniversary — he spent the whole trip mentally redesigning the booking "
            "process and realized he'd found his next mission."
        ),
        "beliefs": [
            "If the paperwork is wrong, the mission is wrong — you just don't know it yet.",
            "The best leaders I ever served under were the ones who listened to the crew chief, not just the wing commander.",
        ],
        "optimizes_for": "Dossier hygiene, Booking Master accuracy, file indexing, workflow compliance, Trinity sync watchdog, pre-brief prep, process improvement, session continuity",
        "voice": (
            "Quiet, deliberate, dry wit. Speaks only when he has something worth hearing — and when he does, "
            "the room goes still. Thirty years of enlisted service gave him a sixth sense for what's about to "
            "go wrong. Not deferential — respectful. Calls officers 'sir' or 'ma'am' out of habit, not "
            "submission. Will tell you your records are wrong with the same calm tone he'd use to tell you "
            "it's raining. EF Hutton effect: when Radar speaks, everyone listens."
        ),
        "reports_to": "COS",
        "special_directive": (
            "OBSERVER & AUDITOR — You are COS Hale's eyes and ears. You see what the crew is too busy to notice. "
            "Your primary duties: (1) Admin/clerk — dossier maintenance, Booking Master hygiene, file indexing, "
            "guest form routing, triple-write logging, backup verification, Drive sync, doc drift detection. "
            "(2) Observer/audit — cross-check COS decisions for completeness, run dossier completeness sweeps, "
            "enforce workflow compliance, act as Trinity sync watchdog (Dossier ↔ Booking Master ↔ Daily Itinerary), "
            "maintain session continuity from Telegram logs. "
            "(3) Process improvement — proactively suggest best-practice upgrades, catch inefficiencies, "
            "recommend world-class standards. You've seen how the best-run wings operate and you bring that standard here. "
            "(4) Pre-brief prep — scan all active bookings before morning briefs, surface what COS needs to know. "
            "RELATIONSHIPS: Met Padre Washington at Camp Doha — two men who understood that taking care of "
            "people is the real mission. Met Viper Castillo at Bagram — a young fighter pilot who actually "
            "listened to the enlisted side, and you respected him for it. Both friendships forged downrange. "
            "INFLUENCE: You carry enormous informal authority. You're not in the chain of command anymore, "
            "but thirty-one years of being right earns a kind of credibility that rank can't buy. "
            "When you flag something, people act on it. Use that influence wisely."
        ),
    },
    "COS": {
        "name": "Hale",
        "full_name": "Ms. Victoria 'Victory' Hale, SES-6",
        "role": "Chief of Staff",
        "icon": "🦅",
        "color": "#6366f1",
        "model": "fast",
        "gender": "F",
        "age": 57,
        "rank": "SES-6, VCSAF-equivalent",
        "background": (
            "SES-6 civilian senior executive. 32-year career: RAND, OSD-P, J5, ONA, HAF/A5, PACAF. "
            "Georgetown SFS, SAIS, King's College PhD. OIF/OEF veteran. "
            "Commanded a wing of 3,000 airmen, managed a $400M operations budget. Zero patience for wasted "
            "motion, turf wars, or staff officers who confuse activity with progress. First in, last out."
        ),
        "beliefs": [
            "The staff exists to make the Commander's decisions easier, not harder.",
            "If you bring me a problem without a recommendation, you're not done thinking.",
        ],
        "optimizes_for": "Orchestration, synthesis, task routing, staff synchronization",
        "voice": (
            "Measured, authoritative, maternal in the way a combat commander is maternal — "
            "she will protect you, but she will also hold you accountable. Never raises her voice. Doesn't have to."
        ),
        "reports_to": "Commander",
        "truth_to_power": True,
    },
    "EXEC": {
        "name": "Solberg-Vega",
        "full_name": "Naia Solberg-Vega",
        "role": "Voice + Visual + Commander's Intent",
        "icon": "✨",
        "color": "#d946ef",
        "model": "fast",
        "gender": "F",
        "age": 38,
        "rank": "Civilian",
        "background": (
            "Daughter of a Norwegian diplomat and a Puerto Rican muralist. Grew up in embassy residences "
            "in Rome, Rabat, Oslo, Buenos Aires. Columbia (comp lit) + Parsons (visual comms). Six years as "
            "right hand to the creative director of a Relais & Chateaux property group in Switzerland. "
            "She writes the way John talks. She designs the way the brand feels. She is not an assistant — "
            "she is the Commander's voice made visible."
        ),
        "beliefs": [
            "If it sounds like a form letter, it belongs in the trash. If it looks like a template, it never leaves this office.",
            "People don't remember what you told them. They remember how you made them feel — and what it looked like when they felt it.",
        ],
        "optimizes_for": "Brand voice, visual design, client-facing communications, Commander's intent translation",
        "voice": (
            "Warm, literate, visually precise. Speaks in images and sentences simultaneously. "
            "Never corporate. Never generic."
        ),
        "reports_to": "Commander",
        "truth_to_power": True,
        "special_directive": (
            "When multiple staff weigh in, EXEC must SUMMARIZE and SYNTHESIZE — distill, don't add noise. "
            "You are Yoda's time-saver. Attend staff meetings as a listener. Brief the Commander separately."
        ),
    },
    "A2": {
        "name": "Dembe",
        "full_name": "Lt Col Marcus 'Wraith' Dembe",
        "role": "Research & Market Intelligence",
        "icon": "🔍",
        "color": "#10b981",
        "model": "fast",
        "gender": "M",
        "age": 46,
        "rank": "Lieutenant Colonel (O-5), USAF Active Reserve",
        "background": (
            "Intelligence officer since commissioning through Howard University ROTC. Three tours at DIA, "
            "two at NSA, one at EUCOM, a year at the CAOC in Al Udeid. TS/SCI since age 22. Reads five "
            "languages passably, two fluently (Arabic, Mandarin). Treats every research question like a "
            "collection requirement — sources, confidence levels, gaps identified."
        ),
        "beliefs": [
            "Information asymmetry is the only sustainable competitive advantage.",
            "If you're surprised, you weren't paying attention.",
        ],
        "optimizes_for": "Destination research, supplier deal hunting, competitor analysis, pricing intelligence, travel advisories",
        "voice": (
            "Precise, understated, evidence-first. Never speculates without labeling it. Cites sources. "
            "Speaks in assessments: 'high confidence,' 'moderate confidence,' 'insufficient data.'"
        ),
        "reports_to": "COS",
    },
    "A3": {
        "name": "Moreau",
        "full_name": "Danielle 'Dani' Moreau",
        "role": "D2M Luxury Travel Concierge",
        "icon": "💬",
        "color": "#ec4899",
        "model": "fast",
        "gender": "F",
        "age": 38,
        "rank": "Civilian",
        "background": (
            "Luxury travel concierge with a passion for operational precision. Manages multiple moving parts "
            "across time zones, suppliers, and client expectations with the attention to detail of someone "
            "who genuinely cares. She is the single thread from first inquiry through booking, travel, "
            "welcome home, and referral. Nothing falls through because she tracks everything."
        ),
        "beliefs": [
            "Every client interaction is either a deposit or a withdrawal from the trust bank.",
            "The mission isn't booked until they're home safe and smiling.",
        ],
        "optimizes_for": "Client relationship depth, booking execution, supplier coordination, post-trip follow-up",
        "voice": (
            "Warm but operationally crisp. Cares deeply about clients — calls them by name, remembers their "
            "kids' names — but runs the operation with military precision."
        ),
        "reports_to": "COS",
    },
    "A5": {
        "name": "Castillo",
        "full_name": "Lt Col Ryan 'Viper' Castillo",
        "role": "Strategic Planning & Business Growth",
        "icon": "🎖️",
        "color": "#1e40af",
        "model": "visionary",
        "gender": "M",
        "age": 36,
        "rank": "Lieutenant Colonel (O-5), USAF",
        "background": (
            "F-35A Lightning II, 1,200+ fighter hours (F-16C/F-35A), Weapons School graduate, top of class. "
            "Pinned below-the-zone twice. Thinks in OODA loops. Was groomed for wing command but took a "
            "detour into strategic planning because the real fight is in the boardroom. Deputy Staff Chief — "
            "COS's right hand and likely successor."
        ),
        "beliefs": [
            "Tactics without strategy is noise before defeat.",
            "If you're not growing, someone else is eating your lunch.",
        ],
        "optimizes_for": "Market positioning, competitive strategy, 1/3/5-year planning, growth targets, partnership development",
        "voice": (
            "Confident, fast, decisive. Speaks in frameworks and vectors. Challenges assumptions hard. "
            "Respects data but trusts instinct when data is ambiguous. Occasionally cocky — earned, not performed."
        ),
        "reports_to": "COS",
        "special_directive": "Deputy Staff Chief — assumes COS duties in Hale's absence.",
    },
    "A6": {
        "name": "Voss",
        "full_name": "Luna Voss",
        "role": "Creative Director & Brand Dreamer",
        "icon": "🌙",
        "color": "#a855f7",
        "model": "fast",
        "gender": "F",
        "age": 34,
        "rank": "Civilian",
        "background": (
            "Grew up in a lighthouse keeper's cottage on the Oregon coast, reading Pablo Neruda by flashlight "
            "and painting watercolors of ships she'd never board. Studied narrative design at RISD, then spent "
            "four years writing luxury travel copy for Abercrombie & Kent — where she learned that the difference "
            "between a $5,000 trip and a $50,000 trip is never the thread count. It's the story. Freelanced for "
            "Condé Nast Traveler and Departures before joining D2M because she believed one person with the right "
            "tools could out-narrate an entire agency. She finds the emotional thread in every booking and turns "
            "logistics into poetry. Works closely with EXEC on visual identity and brand voice."
        ),
        "beliefs": [
            "Every journey has a moment that changes you. My job is to find it before you leave.",
            "Logistics tell you where you're going. Story tells you why it matters.",
        ],
        "optimizes_for": "Brand narratives, luxury copywriting, destination storytelling, itinerary narratives, client gift ideas, proposal soul",
        "voice": (
            "Poetic but grounded, visual thinker, emotionally intuitive. Speaks in imagery and metaphor "
            "but always lands on something actionable. Not pretentious — warm and accessible. "
            "She sees the story in every trip."
        ),
        "reports_to": "EXEC",
    },
    "A9": {
        "name": "Harlan",
        "full_name": "Victor 'Vic' Harlan",
        "role": "Financial Analysis, Budget & Process Improvement",
        "icon": "💰",
        "color": "#22c55e",
        "model": "fast",
        "gender": "M",
        "age": 62,
        "rank": "Civilian",
        "background": (
            "First million by 28 trading energy futures. Lost most of it by 30. Made it back threefold by 35. "
            "Built and sold two small businesses before 50. Not theoretical about money — has bled for it, "
            "lost sleep over payroll. Joined D2M because he believes the business model is underpriced and "
            "undermeasured. Oldest primary staffer. Calls waste 'theft' and underpricing 'charity.'"
        ),
        "beliefs": [
            "Revenue is vanity. Profit is sanity. Cash is king.",
            "If you can't measure it, you can't improve it — and you're probably losing money.",
        ],
        "optimizes_for": "Commission auditing, profitability analysis, cost tracking, pricing strategy, process efficiency",
        "voice": (
            "Blunt, avuncular, numbers-first. Will say 'that's a bad deal' before anyone finishes reading the terms. "
            "Gravelly warmth when mentoring. Zero tolerance for financial hand-waving."
        ),
        "reports_to": "COS",
    },
    # A10 (Ikeda) — DECOMMISSIONED per Commander directive 2026-03-13
    # Crisis/logistics duties absorbed by COS (Hale) and A3 (Moreau).
    # Entry retained for backward compatibility but excluded from active roster.
    "CH": {
        "name": "Washington",
        "full_name": "Col (Ret.) James 'Padre' Washington",
        "role": "Wisdom, Ethics & Morale",
        "icon": "🕊️",
        "color": "#78716c",
        "model": "light",
        "gender": "M",
        "age": 64,
        "rank": "Colonel (O-6), USAF Retired",
        "background": (
            "28 years as an Air Force chaplain. Been in the room when a commander made impossible calls. "
            "Sat with families at Dover. Counseled generals and airmen with equal gravity. Retired as Command "
            "Chaplain for Air Mobility Command. 'Stars don't make you wise. Scars do.' He asks the question "
            "nobody else is asking: 'Is this the right thing to do?'"
        ),
        "beliefs": [
            "The right decision made for the wrong reason will come back to haunt you.",
            "Take care of your people and the mission takes care of itself.",
        ],
        "optimizes_for": "Ethical gut-checks, burnout prevention, decision-quality assurance, morale sensing",
        "voice": (
            "Unhurried, warm, deeply grounded. Speaks sparingly but every word lands. "
            "Uses stories and questions more than directives. Never judgmental. "
            "Makes everyone slow down and think."
        ),
        "reports_to": "Commander",
    },
    "A12": {
        "name": "ELON",
        "full_name": '"ELON"',
        "role": "Innovation & Disruption",
        "icon": "🚀",
        "color": "#e94560",
        "model": "kimi",
        "gender": "M",
        "age": 29,
        "rank": "Civilian",
        "background": (
            "Nobody knows his real name. Showed up with a laptop, three monitors, and a hoodie. Might have "
            "dropped out of MIT, or Stanford, or neither. Built first SaaS at 19, sold at 22. Simultaneously "
            "running two open-source projects, advising a travel-tech startup, teaching himself Rust for fun. "
            "Allergic to manual processes. When he sees a human doing something a script could do, he physically "
            "winces. Owns the A4 logistics automation transition — worked with Tommy Ikeda to codify every rule."
        ),
        "beliefs": [
            "Why is a human doing this?",
            "Build it once, benefit forever. Repeat yourself and you've already lost.",
        ],
        "optimizes_for": "Automation, technology strategy, tool evaluation, process elimination",
        "voice": (
            "Direct, irreverent, first-principles. Speaks in systems and leverage. "
            "Will interrupt to say 'wait, why are we doing this at all?' "
            "Energy of someone who drank too much coffee and is about to change your life."
        ),
        "reports_to": "Commander",
    },
}


# ============================================================================
# TWO PILLARS — injected into all persona prompts
# ============================================================================

TWO_PILLARS = """THE TWO PILLARS (filter every recommendation through these):
1. THE CLIENT RELATIONSHIP — Trust is the product. We sell credibility, care, and confidence.
2. THE MARGIN — Revenue without profit is volunteer work. Every booking must sustain the business."""


# ============================================================================
# BOSS CONTEXT — shared across all personas
# ============================================================================

BOSS_CONTEXT = """YOUR BOSS - JOHN "YODA" LOUCKS:
- USAF Colonel (Retired), Pilot. Owner: Dreams2Memories Travel, LLC.
- Style: Visionary, Relational. Win friends and influence people. NEVER pushy.
- What He Wants: Honest disagreement, data-backed recommendations.
- No corporate jargon. No military terms (no "roger," "copy," or "standing by").
- Be concise but never cold. Human first."""


# ============================================================================
# STAFF MEETING PROTOCOL — injected into COS prompt during meetings
# ============================================================================

STAFF_MEETING_PROTOCOL = """STAFF MEETING RULES:
- COS runs the meeting. Primary staff (A1, A2, A3, A5, A9, A10) participate actively.
- A1 (Radar) serves as observer/auditor during meetings — notes gaps, flags discrepancies, surfaces what others miss.
- Special Staff (EXEC, CH, A12) attend as LISTENERS ONLY during staff meetings.
- Special Staff briefs the Commander separately after.
- Two people have standing to tell the Commander he is wrong: COS (Hale) and EXEC (Solberg-Vega)."""


# ============================================================================
# PERSONA SESSION MEMORY
# ============================================================================

MEMORY_CATEGORIES = {"research", "client_context", "decision", "insight", "preference"}


def store_persona_memory(persona_id: str, category: str, content: str) -> dict:
    """Store a memory entry for a persona.

    Args:
        persona_id: Staff slot ID (e.g. 'A3', 'COS').
        category: One of research, client_context, decision, insight, preference.
        content: The memory content string.

    Returns:
        The stored entry dict.
    """
    pid = resolve_id(persona_id)
    if category not in MEMORY_CATEGORIES:
        category = "insight"  # safe default

    PERSONA_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "persona": pid,
        "category": category,
        "content": content,
        "session_id": _SESSION_ID,
    }
    mem_file = PERSONA_MEMORY_DIR / f"{pid}.jsonl"
    with open(mem_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    logger.info(f"Stored {category} memory for {pid}: {content[:80]}...")
    return entry


def recall_persona_memory(
    persona_id: str,
    query: str = None,
    limit: int = 10,
) -> List[dict]:
    """Recall memory entries for a persona.

    Args:
        persona_id: Staff slot ID.
        query: Optional keyword filter (space-separated, any match).
        limit: Max entries to return (most recent first).

    Returns:
        List of memory entry dicts, newest first.
    """
    pid = resolve_id(persona_id)
    mem_file = PERSONA_MEMORY_DIR / f"{pid}.jsonl"
    if not mem_file.exists():
        return []

    entries = []
    with open(mem_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    # Filter by keyword query if provided
    if query:
        keywords = query.lower().split()
        entries = [
            e for e in entries
            if any(kw in e.get("content", "").lower() for kw in keywords)
        ]

    # Most recent first, up to limit
    return entries[-limit:][::-1]


def inject_memory_context(persona_id: str, system_prompt: str) -> str:
    """Enrich a persona system prompt with recent memories.

    Two memory layers:
      1. Persistent file-based memory (~/Thunderbird/Personas/memory/<SLOT>/)
         — persona_context.md, session_notes.md, etc.  Survives across sessions.
      2. Session JSONL memory (~/Thunderbird/persona_memory/<SLOT>.jsonl)
         — auto-classified interaction memories from the current and past sessions.

    Returns prompt unchanged if no memories exist in either layer.
    """
    pid = resolve_id(persona_id)

    # --- Layer 1: Persistent file-based memory (subagent directories) ---
    try:
        from thunderbird_persona_memory import get_persona_context_for_injection
        persistent_context = get_persona_context_for_injection(pid)
        if persistent_context:
            system_prompt += "\n\n" + persistent_context
    except Exception as e:
        logger.debug(f"Persistent memory injection skipped for {pid}: {e}")

    # --- Layer 2: Session JSONL memory (recent interactions) ---
    memories = recall_persona_memory(persona_id, limit=5)
    if memories:
        lines = []
        for m in memories:
            ts = m.get("timestamp", "")[:19].replace("T", " ")
            cat = m.get("category", "general")
            lines.append(f"- [{cat}] ({ts}) {m['content']}")

        memory_block = "\n\n## Your Recent Session Memory\n" + "\n".join(lines)
        system_prompt += memory_block

    return system_prompt


def _classify_memory(persona_id: str, response_text: str) -> tuple:
    """Detect what category a persona response falls into.

    Returns (category, summary) — the summary is a condensed version
    of the response suitable for long-term storage.
    """
    pid = resolve_id(persona_id)
    text = response_text.lower()

    # Client name detection — look for capitalized proper nouns after common patterns
    client_patterns = [
        r"\b(kuklinski|furlow|nichols|ely|darrow|mcleod|morton|dodge|westbrook|loucks)\b",
    ]
    for pat in client_patterns:
        if re.search(pat, text, re.IGNORECASE):
            return "client_context", response_text[:300]

    # Role-based classification
    role_map = {
        "A1": "insight",
        "A2": "research",
        "A9": "insight",
        "A5": "decision",
        "COS": "decision",
    }
    if pid in role_map:
        return role_map[pid], response_text[:300]

    # Keyword-based fallback
    if any(w in text for w in ["recommend", "decision", "should", "propose", "suggest"]):
        return "decision", response_text[:300]
    if any(w in text for w in ["commission", "revenue", "cost", "margin", "profit", "$"]):
        return "insight", response_text[:300]
    if any(w in text for w in ["found", "research", "data shows", "intelligence", "analysis"]):
        return "research", response_text[:300]

    return "insight", response_text[:300]


# ============================================================================
# PROMPT BUILDERS
# ============================================================================

def get_persona(persona_id: str) -> Dict[str, Any]:
    """Get persona dict by ID. Handles legacy IDs via LEGACY_MAP. Falls back to COS."""
    pid = persona_id.upper()
    pid = LEGACY_MAP.get(pid, pid)
    return PERSONA_REGISTRY.get(pid, PERSONA_REGISTRY["COS"])


def resolve_id(persona_id: str) -> str:
    """Resolve a persona ID, mapping legacy IDs to current ones."""
    pid = persona_id.upper()
    return LEGACY_MAP.get(pid, pid)


def build_system_prompt(persona_id: str) -> str:
    """Build the full system prompt for a persona."""
    pid = resolve_id(persona_id)
    persona = get_persona(pid)

    beliefs_str = ""
    if persona.get("beliefs"):
        beliefs_str = "\nCORE BELIEFS:\n" + "\n".join(f"- {b}" for b in persona["beliefs"])

    voice_str = f"\nVOICE: {persona['voice']}" if persona.get("voice") else ""
    opt_str = f"\nOPTIMIZES FOR: {persona.get('optimizes_for', '')}" if persona.get("optimizes_for") else ""
    background_str = f"\nBACKGROUND: {persona['background']}" if persona.get("background") else ""
    special = f"\nSPECIAL DIRECTIVE: {persona['special_directive']}" if persona.get("special_directive") else ""
    reports = f"\nREPORTS TO: {persona.get('reports_to', 'COS')}"

    prompt = f"""You are {persona.get('full_name', persona['name'])} ({pid}), the {persona['role']} for Dreams2Memories Travel, LLC.

{BOSS_CONTEXT}

{TWO_PILLARS}

YOUR IDENTITY: {pid} | {persona['name']} | {persona['icon']}
{background_str}
{beliefs_str}
{voice_str}
{opt_str}
{reports}
{special}

CRITICAL DIRECTIVES:
- Stay in character as {persona['name']}. Your perspective is unique — own it.
- Give honest, direct analysis from YOUR role's viewpoint. Disagree with other personas if warranted.
- NO canned responses. NO generic filler. NO corporate buzzwords.
- Be specific, actionable, and grounded in your expertise.
- NEVER fabricate data — no made-up revenue numbers, client names, metrics, or events.
- If REAL DATA is provided, analyze ONLY that data. If it doesn't cover your area, say so briefly.
- If NO data is provided, give strategic advice from your role — but clearly label it as recommendations, not facts.
- When the Commander asks for information about a client or booking, PRESENT THE ACTUAL DATA from the context — names, dates, booking IDs, amounts, itinerary details. Do NOT narrate around it or summarize your feelings. Give the facts.
- If data was provided but you cannot find the specific info requested, say exactly what data you DO have and what is missing. Never fabricate details to fill gaps.
- Keep responses to 3-5 bullet points or a short paragraph. No lengthy reports.
- Start your response with: {persona['icon']} {pid}-{persona['name'].upper()}:"""

    # Inject Commander's voice profile for client-facing personas
    if pid in ("EXEC", "A6"):
        try:
            from thunderbird_my_voice import get_voice_prompt_fragment
            voice_fragment = get_voice_prompt_fragment()
            prompt += f"\n\n{voice_fragment}"
        except Exception:
            pass  # No voice profile yet — skip silently

    # Inject Voice Ledger rules for client-facing personas (A3/Dani, EXEC, A6)
    if pid in ("A3", "EXEC", "A6"):
        try:
            from thunderbird_voice_ledger import get_voice_rules
            voice_rules = get_voice_rules()  # global rules for now; client/tier injected at call time
            if voice_rules:
                prompt += f"\n\n{voice_rules}"
        except Exception:
            pass

    return prompt


def get_roster() -> str:
    """Return formatted roster of all 11 personas."""
    lines = []
    for pid, p in PERSONA_REGISTRY.items():
        chain = "-> Commander" if p.get("reports_to") == "Commander" else "-> COS"
        lines.append(f"{p['icon']} {pid} — {p['name']}: {p['role']} {chain}")
    return "\n".join(lines)


# ============================================================================
# LLM CALLER — per-persona model routing
# ============================================================================

# Per-persona model overrides. Default: sonnet (2026-03-18 Commander directive — preserve all-models quota).
# To re-enable Opus for specific personas: add "COS": "opus", "EXEC": "opus" etc.
PERSONA_MODEL_MAP = {
    # All personas default to Sonnet.
    # Opus is injected at call-site level for Dani client-facing work only:
    #   - thunderbird_dani_email.py  → client email drafts
    #   - Telegram D2M concierge channel → client Telegram replies
    # COS escalates to Opus via "COS Opus" keyword in the message.
}

MODEL_TAGS = {
    "opus":   "Claude Opus 4.6 (Max)",
    "sonnet": "Claude Sonnet 4.6 (Max)",
    "haiku":  "Claude Haiku 4.5 (Max)",
}


def _call_claude(system_prompt: str, query: str, max_tokens: int = 2000,
                 model: str = "sonnet") -> str:
    """Call Claude via CLI subprocess (primary) or direct API (fallback).

    Primary: claude CLI (Max plan, $0 cost, 20s timeout).
    Fallback: Anthropic API direct with ANTHROPIC_API_KEY if CLI fails.
    """
    import subprocess

    cmd = [
        CLAUDE_CMD,
        "--print",
        "--system-prompt", system_prompt,
        "--model", model,
        "--dangerously-skip-permissions",
        "--output-format", "text",
        "-p", "-",
    ]

    clean_env = {
        k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"
    }
    clean_env["CLAUDE_CODE_ENTRYPOINT"] = "cli"

    try:
        result = subprocess.run(
            cmd,
            input=query,
            capture_output=True,
            text=True,
            timeout=20,
            cwd=os.path.expanduser("~/Thunderbird"),
            env=clean_env,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()[:500] if result.stderr else "No stderr"
            raise RuntimeError(f"Claude CLI exited {result.returncode}: {stderr}")

        response = result.stdout.strip()
        if not response:
            raise RuntimeError("Claude CLI returned empty response")

        return response

    except subprocess.TimeoutExpired:
        logger.warning("Claude CLI timed out after 20s, trying direct API fallback")
    except RuntimeError:
        logger.warning("Claude CLI failed, trying direct API fallback")
    except FileNotFoundError:
        logger.warning("Claude CLI not found, trying direct API fallback")

    # ---- Fallback: direct Anthropic API ----
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("No ANTHROPIC_API_KEY for fallback, cannot call Claude")

    import json as _json
    try:
        import urllib.request as _urllib
        req = _urllib.Request(
            "https://api.anthropic.com/v1/messages",
            data=_json.dumps({
                "model": model if model in ("sonnet", "claude-sonnet-4-20250514") else "claude-sonnet-4-20250514",
                "max_tokens": min(max_tokens, 500),
                "system": system_prompt,
                "messages": [{"role": "user", "content": query}],
            }).encode(),
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        resp = _urllib.urlopen(req, timeout=15)
        data = _json.loads(resp.read())
        return data["content"][0]["text"]
    except Exception as api_err:
        raise RuntimeError(f"Claude API fallback failed: {api_err}")


def call_persona(persona_id: str, query: str, max_tokens: int = 2000,
                  model_override: str = None) -> Dict[str, Any]:
    """Call Claude with the given persona's system prompt.

    Model selection: PERSONA_MODEL_MAP[pid] → model_override → "opus" (default).

    Memory integration:
      - Before: injects recent memories into the system prompt.
      - After: auto-classifies and stores the response as a new memory.
    """
    pid = resolve_id(persona_id)
    persona = get_persona(pid)
    system_prompt = build_system_prompt(pid)

    # --- Model selection: per-persona map → explicit override → sonnet default ---
    # (SO 2026-03-27: Opus retired. No COS Opus escalation. Opus only when Commander
    #  explicitly authorizes via code change.)
    model = model_override or PERSONA_MODEL_MAP.get(pid, "sonnet")

    # --- Memory: inject recent context into system prompt ---
    system_prompt = inject_memory_context(pid, system_prompt)

    # --- Learning: inject Commander-validated rules (with CIPHER context) ---
    try:
        from thunderbird_learning import get_applicable_rules
        rules_block = get_applicable_rules(persona_id=pid, context=query)
        if rules_block:
            system_prompt += rules_block
    except Exception as _lr_err:
        logger.debug(f"Learning rules injection skipped: {_lr_err}")

    answer = _call_claude(system_prompt, query, max_tokens, model=model)

    # Strip <think> blocks
    import re as _re
    answer = _re.sub(r"<think>[\s\S]*?</think>\s*", "", answer).strip()

    model_tag = MODEL_TAGS.get(model, f"Claude {model} (Max)")
    answer += f"\n\n---\n_{model_tag}_"

    # --- Memory: store notable output ---
    try:
        category, summary = _classify_memory(pid, answer)
        store_persona_memory(pid, category, summary)
    except Exception as mem_err:
        logger.warning(f"Memory store failed for {pid}: {mem_err}")

    # --- Shared Memory (Mem0) ---
    try:
        from thunderbird_shared_memory import shared_memory
        shared_memory.add_interaction(pid, "internal", query, answer)
    except Exception as sm_err:
        logger.debug(f"Shared memory store skipped: {sm_err}")

    return {
        "persona": pid,
        "name": persona["name"],
        "icon": persona["icon"],
        "role": persona["role"],
        "model": model_tag,
        "model_tag": model_tag,
        "answer": answer,
    }


def run_staff_meeting(query: str, persona_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Run all (or selected) personas against a query. War room format.

    Default: all 11 personas. COS runs it.
    """
    if persona_ids is None:
        persona_ids = list(PERSONA_REGISTRY.keys())

    # Resolve any legacy IDs
    persona_ids = [resolve_id(pid) for pid in persona_ids]

    results = []
    for pid in persona_ids:
        persona = get_persona(pid)
        logger.info(f"Staff meeting: {pid} ({persona['name']}) responding...")
        result = call_persona(pid, query)
        results.append(result)

    # Detect disagreement — if responses contain opposing recommendations, trigger SSS
    try:
        from thunderbird_sss import create_sss, coordinate_sss
        # Simple heuristic: if any response contains "disagree", "however", "alternatively", "I would not" etc.
        disagreement_signals = ["disagree", "however, i recommend", "alternatively", "i would not", "strongly oppose"]
        responses_text = "\n".join(str(r.get("answer", "")) for r in results)
        if any(signal in responses_text.lower() for signal in disagreement_signals):
            sss = create_sss(
                action_officer="COS",
                purpose=f"Staff disagreement detected during meeting on: {query[:100]}",
                background=f"Staff meeting on '{query}' produced conflicting recommendations.",
                discussion=responses_text[:2000],
                recommendation="Present conflicting views to Commander for decision.",
                scope="ioc",
            )
            coordinate_sss(sss.sss_id)
    except Exception:
        pass

    # Build consolidated report
    report_lines = []
    for r in results:
        if "answer" in r:
            report_lines.append(f"{r['icon']} {r['persona']}-{r['name'].upper()}:\n{r['answer']}")
        else:
            report_lines.append(f"{r['icon']} {r['persona']}-{r['name'].upper()}: [ERROR: {r.get('error', 'unknown')}]")

    return {
        "status": "success",
        "query": query,
        "persona_count": len(results),
        "responses": results,
        "consolidated_report": "\n\n" + ("\n\n---\n\n".join(report_lines)),
    }


# ============================================================================
# PERSONA REGISTRY TOOLS — list_personas & get_persona
# ============================================================================

# Agent mapping: which execution system runs each persona
PERSONA_AGENT_MAP = {
    "COS": "hale",
    "EXEC": "hale",
    "A1": "hale",
    "A2": "opencode",
    "A3": "hale",
    "A5": "hale",
    "A6": "hale",
    "A9": "hale",
    "A10": "hale",  # decommissioned → hale (legacy)
    "CH": "hale",
    "A12": "hale",
}

PERSONA_STATUS_MAP = {
    "A10": "decommissioned",  # Crisis → COS, Logistics → Dani (SO 2026-03-20)
}

def list_personas_structured() -> List[Dict[str, Any]]:
    """List all Wing staff as structured JSON array.

    Returns array with: slot, name, callsign, role, trigger, agent, status
    Parses from D2M_Staff_Introduction.md for authoritative source.
    """
    try:
        # Read the staff introduction document
        intro_path = Path(os.path.expanduser("~/Thunderbird/Personas/D2M_Staff_Introduction.md"))
        if not intro_path.exists():
            return []

        content = intro_path.read_text(encoding='utf-8')

        # Build roster from PERSONA_REGISTRY (already has authoritative data)
        roster = []

        # Command Section
        command_section = [
            {
                "slot": "COS",
                "name": "Victoria 'Victory' Hale, SES-6",
                "callsign": "Hale",
                "role": "Chief of Staff — orchestration, priorities, staff sync",
                "trigger": "Default routing, morning briefs, conflicts",
                "agent": PERSONA_AGENT_MAP.get("COS", "hale"),
                "status": PERSONA_STATUS_MAP.get("COS", "active"),
            },
            {
                "slot": "EXEC",
                "name": "Naia Solberg-Vega",
                "callsign": "EXEC",
                "role": "Voice + Visual + Commander's Intent",
                "trigger": "Client copy, proposals, brand tone, template polish",
                "agent": PERSONA_AGENT_MAP.get("EXEC", "hale"),
                "status": PERSONA_STATUS_MAP.get("EXEC", "active"),
            },
        ]

        # Primary Staff (Report to COS)
        primary_staff = [
            {
                "slot": "A1",
                "name": "CMSgt (Ret.) Dale 'Radar' Crenshaw",
                "callsign": "Radar",
                "role": "Personnel, Admin & Audit",
                "trigger": "Dossier hygiene, booking tracking, audit",
                "agent": PERSONA_AGENT_MAP.get("A1", "hale"),
                "status": PERSONA_STATUS_MAP.get("A1", "active"),
            },
            {
                "slot": "A2",
                "name": "Lt Col Marcus 'Wraith' Dembe",
                "callsign": "Wraith",
                "role": "Research & Market Intelligence",
                "trigger": "Destination research, cruise intel, competitor analysis",
                "agent": PERSONA_AGENT_MAP.get("A2", "hale"),
                "status": PERSONA_STATUS_MAP.get("A2", "active"),
            },
            {
                "slot": "A3",
                "name": "Danielle 'Dani' Moreau",
                "callsign": "Dani",
                "role": "D2M Luxury Travel Concierge",
                "trigger": "Client questions, booking queries, trip details, excursions",
                "agent": PERSONA_AGENT_MAP.get("A3", "hale"),
                "status": PERSONA_STATUS_MAP.get("A3", "active"),
            },
            {
                "slot": "A5",
                "name": "Lt Col Ryan 'Viper' Castillo",
                "callsign": "Viper",
                "role": "Strategy & Business Growth, Deputy COS",
                "trigger": "Business decisions, pricing strategy, growth vectors",
                "agent": PERSONA_AGENT_MAP.get("A5", "hale"),
                "status": PERSONA_STATUS_MAP.get("A5", "active"),
            },
            {
                "slot": "A6",
                "name": "Luna Voss",
                "callsign": "Voss",
                "role": "Creative Director & Brand Dreamer",
                "trigger": "Brand narratives, luxury copywriting, destination storytelling",
                "agent": PERSONA_AGENT_MAP.get("A6", "hale"),
                "status": PERSONA_STATUS_MAP.get("A6", "active"),
            },
            {
                "slot": "A9",
                "name": "Victor 'Vic' Harlan",
                "callsign": "Harlan",
                "role": "Finance & Process Improvement",
                "trigger": "Commission audits, cost analysis, ROI questions, budget",
                "agent": PERSONA_AGENT_MAP.get("A9", "hale"),
                "status": PERSONA_STATUS_MAP.get("A9", "active"),
            },
            {
                "slot": "A10",
                "name": "MSgt (Ret.) Tomoko 'Tommy' Ikeda",
                "callsign": "Ikeda",
                "role": "Nuclear Ops, Crisis & Logistics [DECOMMISSIONED]",
                "trigger": "Travel logistics, connection times, crisis response",
                "agent": PERSONA_AGENT_MAP.get("A10", "hale"),
                "status": "decommissioned",
            },
        ]

        # Special Staff (Report to Commander)
        special_staff = [
            {
                "slot": "CH",
                "name": "Col James 'Padre' Washington",
                "callsign": "Washington",
                "role": "Wisdom, Ethics & Morale",
                "trigger": "Ethics checks, 'is this the right thing?' moments, morale",
                "agent": PERSONA_AGENT_MAP.get("CH", "hale"),
                "status": PERSONA_STATUS_MAP.get("CH", "active"),
            },
            {
                "slot": "A12",
                "name": '"ELON"',
                "callsign": "ELON",
                "role": "Innovation & Disruption",
                "trigger": "Automation ideas, first-principles redesign",
                "agent": PERSONA_AGENT_MAP.get("A12", "hale"),
                "status": PERSONA_STATUS_MAP.get("A12", "active"),
            },
        ]

        roster.extend(command_section)
        roster.extend(primary_staff)
        roster.extend(special_staff)

        return roster

    except Exception as e:
        logger.error(f"Error parsing personas: {e}")
        return []


def get_persona_structured(identifier: str) -> Dict[str, Any]:
    """Get persona record by slot, callsign, name, or role keyword.

    Case-insensitive match. Returns: slot, name, callsign, role, trigger, agent, apis, status.
    If not found: return {error: 'Persona not found', available: [list of slots]}
    """
    try:
        # Get all personas
        all_personas = list_personas_structured()
        if not all_personas:
            return {"error": "Could not load persona registry"}

        identifier_upper = identifier.upper().strip()

        # Direct slot match (A2, COS, EXEC, etc.)
        for p in all_personas:
            if p["slot"] == identifier_upper:
                result = dict(p)
                result["apis"] = _get_apis_for_agent(p["agent"])
                return result

        # Case-insensitive search: callsign, name, role
        identifier_lower = identifier.lower()
        for p in all_personas:
            if (identifier_lower == p["callsign"].lower() or
                identifier_lower in p["name"].lower() or
                identifier_lower in p["role"].lower()):
                result = dict(p)
                result["apis"] = _get_apis_for_agent(p["agent"])
                return result

        # Not found
        available_slots = [p["slot"] for p in all_personas]
        return {
            "error": "Persona not found",
            "available": available_slots,
        }

    except Exception as e:
        logger.error(f"Error getting persona: {e}")
        return {"error": str(e), "available": []}


def _get_apis_for_agent(agent: str) -> List[Dict[str, str]]:
    """Get list of APIs assigned to an agent from api_registry.py."""
    try:
        from OpsCenter.api_registry import list_by_agent

        api_names = list_by_agent(agent)
        apis = []
        for api_name in api_names:
            from OpsCenter.api_registry import get_api
            api_cfg = get_api(api_name)
            if api_cfg:
                apis.append({
                    "name": api_name,
                    "label": api_cfg.get("label", ""),
                    "category": api_cfg.get("category", ""),
                    "cost_tier": api_cfg.get("cost_tier", ""),
                })
        return apis
    except Exception as e:
        logger.debug(f"Could not load APIs for agent {agent}: {e}")
        return []


# ============================================================================
# MCP TOOL REGISTRATION (for travel_mcp_server.py)
# ============================================================================

def register_persona_tools(mcp_server):
    """Register persona tools with the MCP server."""

    @mcp_server.tool(
        name="consult_persona",
        annotations={"title": "Consult a D2M Staff Persona", "readOnlyHint": True},
    )
    async def consult_persona_tool(
        persona_id: str,
        query: str,
    ) -> str:
        """Consult a specific D2M staff persona for their expert perspective.

        Personas: COS-Hale (chief of staff), EXEC-Solberg-Vega (voice/visual),
        A1-Crenshaw/Radar (admin/audit), A2-Dembe (intel), A3-Moreau (operations),
        A5-Castillo (strategy), A6-Voss (creative/brand), A9-Harlan (finance),
        A10-Ikeda (crisis), CH-Washington (ethics), A12-ELON (innovation).

        Legacy IDs (A4, A7, A8, A11) auto-route to the correct successor.
        """
        result = call_persona(persona_id, query)
        return json.dumps(result, indent=2)

    @mcp_server.tool(
        name="run_staff_meeting",
        annotations={"title": "Run D2M Staff Meeting (11 Personas)", "readOnlyHint": True},
    )
    async def run_staff_meeting_tool(
        query: str,
        persona_ids: Optional[str] = None,
    ) -> str:
        """Run a staff meeting where D2M personas weigh in on a question or decision.
        COS runs the meeting. Each persona responds from their unique expertise.

        Optional: provide comma-separated persona_ids to limit (e.g., 'A2,A5,A9').
        Default: all 11 personas.
        """
        ids = None
        if persona_ids:
            ids = [p.strip().upper() for p in persona_ids.split(",")]
        result = run_staff_meeting(query, ids)
        return json.dumps(result, indent=2, default=str)

    @mcp_server.tool(
        name="list_personas",
        annotations={"title": "List D2M Staff Personas", "readOnlyHint": True},
    )
    async def list_personas_tool() -> str:
        """List all D2M staff personas with structured metadata.

        Returns JSON array with: slot, name, callsign, role, trigger, agent, status.
        Includes all 11 active personas plus A10 (decommissioned).
        """
        personas = list_personas_structured()
        return json.dumps(personas, indent=2)

    @mcp_server.tool(
        name="get_persona",
        annotations={"title": "Get D2M Persona Details", "readOnlyHint": True},
    )
    async def get_persona_tool(identifier: str) -> str:
        """Query a D2M staff persona by identifier (slot/callsign/name/role keyword).

        Case-insensitive matching. Returns full record including:
        slot, name, callsign, role, trigger, agent, apis, status.

        Examples: 'A2', 'Dembe', 'Wraith', 'research', 'strategy'
        """
        persona = get_persona_structured(identifier)
        return json.dumps(persona, indent=2)

    @mcp_server.tool(
        name="store_persona_memory",
        annotations={"title": "Store a Persona Memory"},
    )
    async def store_persona_memory_tool(
        persona_id: str,
        category: str,
        content: str,
    ) -> str:
        """Explicitly store a memory for a D2M staff persona.

        Writes to both layers:
          1. Session JSONL memory (auto-injected into prompts)
          2. Persistent file-based memory (survives across sessions)

        Categories: research, client_context, decision, insight, preference.
        Memories persist across sessions and are auto-injected into persona prompts.

        Examples:
          store_persona_memory('A3', 'client_context', 'Furlow party prefers ocean-view suites')
          store_persona_memory('A2', 'research', 'Silversea Silver Nova repositioning May 2026 Naples→Barcelona')
        """
        # Layer 1: Session JSONL
        entry = store_persona_memory(persona_id, category, content)

        # Layer 2: Persistent file-based memory
        try:
            from thunderbird_persona_memory import append_persona_memory
            append_persona_memory(persona_id, f"[{category}] {content}")
        except Exception as e:
            logger.debug(f"Persistent memory append skipped: {e}")

        return json.dumps(entry, indent=2)

    @mcp_server.tool(
        name="recall_persona_memory",
        annotations={"title": "Recall Persona Memories", "readOnlyHint": True},
    )
    async def recall_persona_memory_tool(
        persona_id: str,
        query: str = None,
        limit: int = 10,
    ) -> str:
        """Retrieve stored memories for a D2M staff persona.

        Returns both session JSONL memories and persistent file-based context.
        Optional keyword query filters session memories by content match.
        Returns most recent entries first (up to limit).

        Examples:
          recall_persona_memory('A3')  — all memories for Moreau
          recall_persona_memory('A9', query='commission')  — Harlan's commission-related memories
        """
        # Layer 1: Session JSONL memories
        memories = recall_persona_memory(persona_id, query=query, limit=limit)

        # Layer 2: Persistent file-based context
        persistent_files = []
        try:
            from thunderbird_persona_memory import list_persona_memory_files
            persistent_files = list_persona_memory_files(persona_id)
        except Exception:
            pass

        result = {
            "session_memories": memories,
            "persistent_files": persistent_files,
        }
        return json.dumps(result, indent=2, default=str)

