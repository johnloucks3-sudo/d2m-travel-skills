"""
Thunderbird Recipient Voice Profiles
=====================================
Per-recipient communication profiles that capture how Commander
writes to each specific person. Goes beyond tier-level rules.

Profiles track:
- Greeting pattern used with this person
- Sign-off pattern used
- Tone level (formal/semi-formal/casual)
- Topics frequently discussed
- Personal references Commander includes
- Communication frequency
- Relationship notes

Hierarchy:
  Voice Ledger (global → tier → client rules) → Recipient Profiles (per-person)
  Recipient profiles are the most specific layer. When a recipient profile
  exists, its patterns override generic tier-level rules.

Storage: JSON file (human-readable, git-trackable).
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
PROFILES_PATH = THUNDERBIRD_DIR / "recipient_profiles.json"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class RecipientProfile:
    """Voice profile for a single recipient."""
    name: str
    email: str = ""
    relationship_tier: str = "prospect"  # paying, friend, prospect, vendor
    greeting_patterns: List[str] = field(default_factory=list)
    signoff_patterns: List[str] = field(default_factory=list)
    tone: str = "semi-formal"  # formal, semi-formal, casual
    personal_references: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    communication_notes: List[str] = field(default_factory=list)
    sample_count: int = 0
    last_updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecipientProfile":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _load_profiles() -> Dict[str, Dict]:
    """Load all recipient profiles from disk."""
    if PROFILES_PATH.exists():
        try:
            return json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Failed to load recipient profiles: {e}")
    return {"meta": {"created": datetime.now(timezone.utc).isoformat(), "version": 1}, "profiles": {}}


def _save_profiles(data: Dict[str, Dict]):
    """Save all recipient profiles to disk."""
    data["meta"]["last_updated"] = datetime.now(timezone.utc).isoformat()
    data["meta"]["profile_count"] = len(data.get("profiles", {}))
    PROFILES_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info(f"Recipient profiles saved ({len(data.get('profiles', {}))} profiles)")


def _normalize_key(name_or_email: str) -> str:
    """Normalize a name or email into a consistent lookup key."""
    return name_or_email.strip().lower()


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------

def get_profile(name_or_email: str) -> Optional[RecipientProfile]:
    """Look up a recipient profile by name or email (fuzzy match)."""
    data = _load_profiles()
    profiles = data.get("profiles", {})
    needle = _normalize_key(name_or_email)

    # Exact key match
    if needle in profiles:
        return RecipientProfile.from_dict(profiles[needle])

    # Fuzzy match: check if needle appears in any key or email field
    for key, pdata in profiles.items():
        if needle in key or needle in pdata.get("email", "").lower():
            return RecipientProfile.from_dict(pdata)
        # Also check if any part of the name matches
        if any(part in key for part in needle.split()):
            return RecipientProfile.from_dict(pdata)

    return None


def update_profile(name_or_email: str, **kwargs) -> RecipientProfile:
    """Update (or create) a recipient profile. Merges list fields."""
    data = _load_profiles()
    profiles = data.get("profiles", {})
    key = _normalize_key(name_or_email)

    # Find existing or create new
    existing = None
    existing_key = key
    for k, pdata in profiles.items():
        if key in k or key in pdata.get("email", "").lower():
            existing = RecipientProfile.from_dict(pdata)
            existing_key = k
            break

    if existing is None:
        existing = RecipientProfile(name=name_or_email.strip())
        existing_key = key

    # Merge fields
    for field_name, value in kwargs.items():
        if not hasattr(existing, field_name):
            continue
        current = getattr(existing, field_name)
        if isinstance(current, list) and isinstance(value, list):
            # Deduplicate while merging
            merged = list(current)
            for item in value:
                if item not in merged:
                    merged.append(item)
            setattr(existing, field_name, merged)
        elif isinstance(current, list) and isinstance(value, str):
            if value not in current:
                current.append(value)
        else:
            setattr(existing, field_name, value)

    existing.last_updated = datetime.now(timezone.utc).isoformat()
    profiles[existing_key] = existing.to_dict()
    data["profiles"] = profiles
    _save_profiles(data)
    return existing


def list_profiles() -> List[RecipientProfile]:
    """Return all stored recipient profiles."""
    data = _load_profiles()
    return [RecipientProfile.from_dict(p) for p in data.get("profiles", {}).values()]


def delete_profile(name_or_email: str) -> bool:
    """Remove a recipient profile."""
    data = _load_profiles()
    profiles = data.get("profiles", {})
    key = _normalize_key(name_or_email)

    # Find the actual key
    target_key = None
    if key in profiles:
        target_key = key
    else:
        for k, pdata in profiles.items():
            if key in k or key in pdata.get("email", "").lower():
                target_key = k
                break

    if target_key:
        del profiles[target_key]
        data["profiles"] = profiles
        _save_profiles(data)
        return True
    return False


# ---------------------------------------------------------------------------
# Learning engine — learn_from_email
# ---------------------------------------------------------------------------

# Greeting patterns
_GREETING_RE = re.compile(
    r"^(Hi|Hey|Hello|Dear|Good\s+(?:morning|afternoon|evening))[\s,]+([A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+)?)",
    re.IGNORECASE,
)

# Sign-off patterns — match the last few lines before a signature block
_SIGNOFF_PATTERNS = [
    re.compile(r"^(Thanks,?)\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^(Thank you,?)\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^(Best,?)\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^(Warm regards,?)\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^(Regards,?)\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^(Cheers,?)\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^(All the best,?)\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^(Take care,?)\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^(Thanks,?\s*\n\s*John)\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^(Thank you,?\s*\n\s*John)\s*$", re.IGNORECASE | re.MULTILINE),
]

# Personal reference markers
_PERSONAL_REF_PATTERNS = [
    re.compile(r"\byour\s+(wife|husband|spouse|daughter|son|kids|children|family|dog|cat|pet)\b", re.IGNORECASE),
    re.compile(r"\b(?:the|your)\s+(kids|girls|boys|little ones|pup|puppy)\b", re.IGNORECASE),
    re.compile(r"\b(Missy|Melissa|Ken|Nancy|Ron|Rondo|Lindy|Kyle|Rosalie|Al|Amy|Larry|Heidi|Erik|Leslie|Rachelle|Susan|Susie)\b"),
    re.compile(r"\b(Elle|Goldendoodle)\b", re.IGNORECASE),
    re.compile(r"\b(Costa Rica|jungle|monkeys)\b", re.IGNORECASE),
    re.compile(r"\b(birthday|anniversary|retirement|celebration)\b", re.IGNORECASE),
]

# Travel topic markers
_TRAVEL_TOPIC_PATTERNS = [
    (re.compile(r"\b(cruise|ship|embark|disembark|cabin|suite|stateroom|voyage)\b", re.IGNORECASE), "cruise"),
    (re.compile(r"\b(flight|airline|airport|seat|PNR|boarding)\b", re.IGNORECASE), "flights"),
    (re.compile(r"\b(hotel|resort|check-in|check-out|room|reservation)\b", re.IGNORECASE), "hotels"),
    (re.compile(r"\b(excursion|tour|activity|sightseeing)\b", re.IGNORECASE), "excursions"),
    (re.compile(r"\b(transfer|transport|pickup|drop-off|car service)\b", re.IGNORECASE), "transfers"),
    (re.compile(r"\b(insurance|coverage|CFAR|Allianz|policy)\b", re.IGNORECASE), "insurance"),
    (re.compile(r"\b(payment|balance|deposit|final payment|CC|credit card)\b", re.IGNORECASE), "payments"),
    (re.compile(r"\b(passport|visa|entry|travel document)\b", re.IGNORECASE), "documents"),
    (re.compile(r"\b(dining|restaurant|dinner|lunch|food|cuisine)\b", re.IGNORECASE), "dining"),
    (re.compile(r"\b(itinerary|schedule|agenda|plan)\b", re.IGNORECASE), "itinerary"),
]


def _detect_tone(body: str) -> str:
    """Analyze an email body for tone markers."""
    exclamation_count = body.count("!")
    lines = body.strip().split("\n")
    total_lines = max(len(lines), 1)

    # Check for formal markers
    formal_markers = ["Dear ", "Sincerely", "Respectfully", "Per our conversation"]
    has_formal = any(m.lower() in body.lower() for m in formal_markers)

    # Check for casual markers
    casual_markers = ["lol", "haha", "btw", "gonna", "wanna", "ya'll", "y'all"]
    has_casual = any(m.lower() in body.lower() for m in casual_markers)

    # Exclamation point density
    excl_density = exclamation_count / total_lines

    if has_formal and not has_casual:
        return "formal"
    elif has_casual or excl_density > 0.5:
        return "casual"
    else:
        return "semi-formal"


def learn_from_email(to: str, subject: str, body: str) -> RecipientProfile:
    """Analyze a sent email and update the recipient's voice profile.

    This learns from Commander's SENT emails — how he writes to each person.

    Args:
        to:      Recipient email address or "Name <email>" format.
        subject: Email subject line.
        body:    Full email body text.

    Returns:
        Updated RecipientProfile for this recipient.
    """
    # Parse recipient
    email_match = re.search(r'<([^>]+)>', to)
    email_addr = email_match.group(1).strip() if email_match else to.strip()
    name_match = re.match(r'^"?([^"<]+)"?\s*<', to)
    name = name_match.group(1).strip() if name_match else to.split("@")[0].strip()

    # Get or create profile
    profile = get_profile(email_addr) or get_profile(name)
    key = _normalize_key(email_addr or name)

    updates: Dict[str, Any] = {}
    if email_addr:
        updates["email"] = email_addr

    # --- Greeting pattern ---
    first_line = body.strip().split("\n")[0] if body.strip() else ""
    greeting_match = _GREETING_RE.match(first_line)
    if greeting_match:
        greeting = greeting_match.group(0).strip().rstrip(",")
        updates["greeting_patterns"] = [greeting]

    # --- Sign-off pattern ---
    for pattern in _SIGNOFF_PATTERNS:
        signoff_match = pattern.search(body)
        if signoff_match:
            updates["signoff_patterns"] = [signoff_match.group(0).strip()]
            break

    # --- Tone ---
    updates["tone"] = _detect_tone(body)

    # --- Personal references ---
    refs_found = []
    for pattern in _PERSONAL_REF_PATTERNS:
        matches = pattern.findall(body)
        for m in matches:
            ref = m if isinstance(m, str) else m[0] if isinstance(m, tuple) else str(m)
            if ref and ref not in refs_found:
                refs_found.append(ref)
    if refs_found:
        updates["personal_references"] = refs_found

    # --- Topics ---
    topics_found = []
    for pattern, topic in _TRAVEL_TOPIC_PATTERNS:
        if pattern.search(body) or pattern.search(subject):
            if topic not in topics_found:
                topics_found.append(topic)
    if topics_found:
        updates["topics"] = topics_found

    # --- Increment sample count ---
    current_count = profile.sample_count if profile else 0
    updates["sample_count"] = current_count + 1

    # Apply updates
    result = update_profile(email_addr or name, **updates)
    logger.info(f"Learned from email to {name} ({email_addr}) — sample #{result.sample_count}")
    return result


# ---------------------------------------------------------------------------
# Injection block for Dani pipeline
# ---------------------------------------------------------------------------

def get_injection_block(name_or_email: str) -> str:
    """Format a recipient profile as a prompt injection block.

    This is injected into Dani's context before she drafts a response,
    giving her specific instructions for how to write to this person.

    Returns empty string if no profile exists.
    """
    profile = get_profile(name_or_email)
    if not profile:
        return ""

    lines = [f"\nRECIPIENT VOICE PROFILE -- {profile.name}:"]

    if profile.greeting_patterns:
        greetings = " / ".join(profile.greeting_patterns[:3])
        lines.append(f"- Greeting: Use \"{greetings}\"")

    if profile.signoff_patterns:
        signoffs = " / ".join(profile.signoff_patterns[:3])
        lines.append(f"- Sign-off: Use \"{signoffs}\"")

    lines.append(f"- Tone: {profile.tone}")
    lines.append(f"- Relationship: {profile.relationship_tier}")

    if profile.personal_references:
        refs = ", ".join(profile.personal_references[:6])
        lines.append(f"- Personal touches: reference {refs}")

    if profile.topics:
        topics = ", ".join(profile.topics[:8])
        lines.append(f"- Topics they care about: {topics}")

    if profile.communication_notes:
        for note in profile.communication_notes[:3]:
            lines.append(f"- Note: {note}")

    if profile.sample_count > 0:
        lines.append(f"- Based on {profile.sample_count} analyzed emails")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Seed profiles from dossiers
# ---------------------------------------------------------------------------

def seed_from_dossiers() -> int:
    """Pre-populate recipient profiles from dossier files.

    Reads ~/Thunderbird/dossiers/*.md and extracts:
    - Client names and emails
    - Relationship tiers
    - Known personal details (family members, pets, etc.)

    Safe to call multiple times — existing profiles are merged, not overwritten.

    Returns count of profiles created or updated.
    """
    dossier_dir = THUNDERBIRD_DIR / "dossiers"
    if not dossier_dir.exists():
        logger.warning("Dossier directory not found")
        return 0

    # Client data extracted from dossiers
    clients = [
        # --- Paying clients ---
        {
            "name": "John Furlow",
            "email": "",
            "tier": "paying",
            "personal_refs": ["Missy", "Costa Rica", "monkeys"],
            "topics": ["cruise", "flights", "payments", "insurance"],
            "notes": ["Travels with Missy (wife)", "Part of Scandinavia group (3 couples)",
                       "Books through AA for AmEx points", "Goes by John"],
        },
        {
            "name": "Missy Furlow",
            "email": "",
            "tier": "paying",
            "personal_refs": ["John Furlow"],
            "topics": ["cruise", "flights"],
            "notes": ["Married to John Furlow", "Books AA flights for 5x AmEx points"],
        },
        {
            "name": "Al Ely",
            "email": "",
            "tier": "paying",
            "personal_refs": ["Amy"],
            "topics": ["cruise", "payments", "insurance", "transfers"],
            "notes": ["Travels with Amy Darrow", "Part of Scandinavia group",
                       "Proactive on payment scheduling", "Uploaded CC to portal"],
        },
        {
            "name": "Amy Darrow",
            "email": "",
            "tier": "paying",
            "personal_refs": ["Al"],
            "topics": ["cruise", "excursions"],
            "notes": ["Travels with Al Ely"],
        },
        {
            "name": "Larry Nichols",
            "email": "",
            "tier": "paying",
            "personal_refs": ["Heidi", "birthday"],
            "topics": ["cruise", "insurance", "payments"],
            "notes": ["Travels with Heidi (wife)", "Part of Scandinavia group",
                       "Reads emails late at night", "Wants CFAR insurance",
                       "Embarkation day is Heidi's birthday"],
        },
        {
            "name": "Heidi Nichols",
            "email": "",
            "tier": "paying",
            "personal_refs": ["Larry"],
            "topics": ["cruise", "transfers", "flights"],
            "notes": ["Married to Larry Nichols", "Birthday on embarkation day (Aug 29)",
                       "Handles flight booking for the couple"],
        },
        {
            "name": "Kyle Kuklinski",
            "email": "kyle.kuklinski@gmail.com",
            "tier": "paying",
            "personal_refs": ["Rosalie", "Roger", "Nicholas", "Josh", "Erica"],
            "topics": ["cruise", "payments", "documents"],
            "notes": ["Group organizer for Kuklinski Viking Panama Canal",
                       "Uploaded CC to portal", "Requested payment delay to Mar 25",
                       "Point of contact for all 3 Kuklinski bookings"],
        },
        {
            "name": "Erik McLeod",
            "email": "emcleod@gmail.com",
            "tier": "paying",
            "personal_refs": ["Melissa"],
            "topics": ["cruise", "excursions", "dining", "hotels", "transfers", "flights"],
            "notes": ["Travels with Melissa McGlasson", "Very hands-on with research",
                       "Multiple bookings (Silver Muse, Regent Lesser Antilles, Prestige, Princess)",
                       "Gold standard for client materials presentation",
                       "Include Melissa (memcglas@gmail.com) on all emails"],
        },
        {
            "name": "Melissa McGlasson",
            "email": "memcglas@gmail.com",
            "tier": "paying",
            "personal_refs": ["Erik"],
            "topics": ["cruise", "dining", "excursions"],
            "notes": ["Travels with Erik McLeod", "Does independent restaurant research",
                       "CC on all future correspondence"],
        },
        # --- Friends & Family ---
        {
            "name": "Nancy Lyons",
            "email": "nancylyons73@outlook.com",
            "tier": "friend",
            "personal_refs": ["Ken"],
            "topics": ["cruise", "dining", "transfers"],
            "notes": ["Friend of Commander", "Non-revenue friend service",
                       "Regent Splendor Athens-Lisbon-NY", "Already has Sintra day trip planned",
                       "Needs dinner reservation at Grande Bretagne Athens"],
        },
        {
            "name": "Ken Lyons",
            "email": "klyons3@bellsouth.net",
            "tier": "friend",
            "personal_refs": ["Nancy"],
            "topics": ["cruise"],
            "notes": ["Married to Nancy Lyons", "Friend of Commander"],
        },
        {
            "name": "Ron Westbrook",
            "email": "rwestbrook3@gmail.com",
            "tier": "friend",
            "personal_refs": ["Lindy", "Ava", "Allie"],
            "topics": ["cruise", "transfers", "excursions", "flights"],
            "notes": ["Goes by Rondo", "Travels with Lindy (wife)",
                       "Silver Nova Pacific with Loucks",
                       "Approved Dani as concierge contact",
                       "Itinerary guinea pig for new features"],
        },
        {
            "name": "Lindy Westbrook",
            "email": "lindywestbrook77@gmail.com",
            "tier": "friend",
            "personal_refs": ["Ron", "Rondo"],
            "topics": ["cruise"],
            "notes": ["Married to Ron Westbrook"],
        },
        {
            "name": "Joe Britan",
            "email": "jbitran@enterprizer.com",
            "tier": "friend",
            "personal_refs": [],
            "topics": ["dining", "flights"],
            "notes": ["Friend of Commander", "Lives in New Jersey",
                       "May want dining recommendations or flight quotes"],
        },
        {
            "name": "Ryan Loucks",
            "email": "loucksrj@gmail.com",
            "tier": "friend",
            "personal_refs": ["Rachelle", "Ava", "Charlotte", "Canaan", "Elle"],
            "topics": ["hotels"],
            "notes": ["Commander's son/relative", "Family relocation Benton LA to Omaha NE",
                       "Two cars, Goldendoodle named Elle",
                       "Warm family tone, frame move as exciting"],
        },
        {
            "name": "Justin Loucks",
            "email": "cnuraptor@gmail.com",
            "tier": "friend",
            "personal_refs": ["Leslie", "Kayleigh", "Aldon"],
            "topics": ["flights"],
            "notes": ["Commander's son/relative", "Family of 4 from Centerville VA",
                       "Round-trip airfare to Colorado Springs Jul 18-25",
                       "Wife Leslie handles flight search"],
        },
        {
            "name": "Leslie Loucks",
            "email": "leslieanichols@gmail.com",
            "tier": "friend",
            "personal_refs": ["Justin", "Kayleigh", "Aldon"],
            "topics": ["flights"],
            "notes": ["Married to Justin Loucks", "Active flight searcher",
                       "SW cancelled IAD flights — searching United from IAD and SW from DCA"],
        },
        {
            "name": "David McLeran",
            "email": "davidmcleran@yahoo.com",
            "tier": "prospect",
            "personal_refs": [],
            "topics": ["excursions"],
            "notes": ["Prospect — Alaska self-drive interest",
                       "Friend introduced via email Mar 2026"],
        },
        # --- Vendors (common) ---
        {
            "name": "Roger Kuklinski",
            "email": "Roger.kuklinski@gmail.com",
            "tier": "paying",
            "personal_refs": ["Nicholas", "Kyle"],
            "topics": ["cruise", "payments"],
            "notes": ["Part of Kuklinski Viking Panama Canal group",
                       "Father of Kyle and Nicholas", "Uploaded CC to portal"],
        },
        {
            "name": "Joshua Morton",
            "email": "Josh@jerichopix.com",
            "tier": "paying",
            "personal_refs": ["Erica"],
            "topics": ["cruise", "payments"],
            "notes": ["Part of Kuklinski Viking Panama Canal group",
                       "Travels with Erica Dodge", "CC still needed for payment"],
        },
    ]

    count = 0
    for client in clients:
        try:
            key = client["email"] or client["name"]
            update_profile(
                key,
                name=client["name"],
                email=client.get("email", ""),
                relationship_tier=client["tier"],
                personal_references=client.get("personal_refs", []),
                topics=client.get("topics", []),
                communication_notes=client.get("notes", []),
            )
            count += 1
        except Exception as e:
            logger.error(f"Failed to seed profile for {client['name']}: {e}")

    logger.info(f"Seeded {count} recipient profiles from dossiers")
    return count


# ---------------------------------------------------------------------------
# MCP Tool Registration
# ---------------------------------------------------------------------------

def register_recipient_profile_tools(mcp_server):
    """Register recipient voice profile tools with the MCP server."""

    @mcp_server.tool(
        name="recipient_profile_get",
        annotations={"title": "Get Recipient Voice Profile", "readOnlyHint": True},
    )
    async def recipient_profile_get_tool(name_or_email: str) -> str:
        """Get voice profile for a specific recipient. Returns greeting patterns,
        tone, personal references, and topics for email drafting."""
        try:
            profile = get_profile(name_or_email)
            if profile:
                injection = get_injection_block(name_or_email)
                return json.dumps({
                    "status": "found",
                    "profile": profile.to_dict(),
                    "injection_block": injection,
                }, indent=2)
            return json.dumps({
                "status": "not_found",
                "message": f"No profile found for '{name_or_email}'",
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp_server.tool(
        name="recipient_profile_list",
        annotations={"title": "List All Recipient Profiles", "readOnlyHint": True},
    )
    async def recipient_profile_list_tool() -> str:
        """List all stored recipient voice profiles with summary stats."""
        try:
            profiles = list_profiles()
            summaries = []
            for p in profiles:
                summaries.append({
                    "name": p.name,
                    "email": p.email,
                    "tier": p.relationship_tier,
                    "tone": p.tone,
                    "samples": p.sample_count,
                    "greeting_count": len(p.greeting_patterns),
                    "topics": p.topics[:5],
                })
            return json.dumps({
                "status": "ok",
                "count": len(summaries),
                "profiles": summaries,
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp_server.tool(
        name="recipient_profile_learn",
        annotations={"title": "Learn Voice Profile from Email"},
    )
    async def recipient_profile_learn_tool(
        to: str,
        subject: str,
        body: str,
    ) -> str:
        """Analyze a sent email to learn how Commander writes to this recipient.
        Extracts greeting, sign-off, tone, personal references, and topics."""
        try:
            profile = learn_from_email(to, subject, body)
            return json.dumps({
                "status": "learned",
                "profile": profile.to_dict(),
                "injection_block": get_injection_block(profile.email or profile.name),
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    logger.info("Recipient Profile tools registered (3 tools)")
