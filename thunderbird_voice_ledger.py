"""
Thunderbird Voice Ledger — IOC-8
=================================
Living document of Commander voice rules, organized by client tier and
relationship context. Fed by the learning compiler (thunderbird_learning.py)
and Commander edits. Consumed by EXEC, A6, and Dani for client-facing output.

Unlike the static voice profile (thunderbird_my_voice.py which snapshots
Gmail patterns via Groq), the Voice Ledger is a continuously updated,
structured rule set that grows with every correction.

Hierarchy:
  GLOBAL rules → TIER rules → CLIENT-SPECIFIC rules
  (most specific wins when rules conflict)

Tiers:
  paying     — active paying clients (Furlow, Ely, Kuklinski, etc.)
  friend     — friends/family (Lyons, Loucks family, Britan, Westbrook)
  prospect   — potential clients not yet booked
  vendor     — suppliers, tour operators, cruise lines
  staff      — internal staff directives (how John talks to COS, etc.)

Storage: JSON ledger file (not SQLite — human-readable, git-trackable).
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
LEDGER_PATH = THUNDERBIRD_DIR / "voice_ledger.json"

VALID_TIERS = {"paying", "friend", "prospect", "vendor", "staff", "global"}
VALID_DOMAINS = {"greeting", "signoff", "tone", "length", "structure", "phrasing",
                 "urgency", "bad_news", "good_news", "humor", "anti_pattern"}


# ---------------------------------------------------------------------------
# Ledger structure
# ---------------------------------------------------------------------------

def _load_ledger() -> Dict[str, Any]:
    """Load the voice ledger from disk."""
    if LEDGER_PATH.exists():
        try:
            return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Failed to load voice ledger: {e}")
    return {
        "meta": {
            "created": datetime.now(timezone.utc).isoformat(),
            "last_updated": None,
            "version": 1,
        },
        "global_rules": [],
        "tier_rules": {},
        "client_rules": {},
    }


def _save_ledger(ledger: Dict[str, Any]):
    """Save the voice ledger to disk."""
    ledger["meta"]["last_updated"] = datetime.now(timezone.utc).isoformat()
    LEDGER_PATH.write_text(
        json.dumps(ledger, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info(f"Voice ledger saved ({_count_rules(ledger)} rules)")


def _count_rules(ledger: Dict) -> int:
    """Count total rules in the ledger."""
    total = len(ledger.get("global_rules", []))
    for rules in ledger.get("tier_rules", {}).values():
        total += len(rules)
    for rules in ledger.get("client_rules", {}).values():
        total += len(rules)
    return total


# ---------------------------------------------------------------------------
# Rule management
# ---------------------------------------------------------------------------

def _make_rule(
    domain: str,
    text: str,
    source: str = "commander_edit",
    example: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a rule entry."""
    return {
        "domain": domain if domain in VALID_DOMAINS else "phrasing",
        "text": text,
        "source": source,
        "example": example,
        "created": datetime.now(timezone.utc).isoformat(),
        "applied_count": 0,
    }


def add_global_rule(
    domain: str,
    text: str,
    source: str = "commander_edit",
    example: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a rule that applies to ALL client-facing output."""
    ledger = _load_ledger()
    rule = _make_rule(domain, text, source, example)
    ledger["global_rules"].append(rule)
    _save_ledger(ledger)
    logger.info(f"Added global voice rule [{domain}]: {text[:60]}")
    return rule


def add_tier_rule(
    tier: str,
    domain: str,
    text: str,
    source: str = "commander_edit",
    example: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a rule for a specific relationship tier."""
    if tier not in VALID_TIERS:
        raise ValueError(f"Invalid tier '{tier}'. Valid: {VALID_TIERS}")
    ledger = _load_ledger()
    if tier not in ledger["tier_rules"]:
        ledger["tier_rules"][tier] = []
    rule = _make_rule(domain, text, source, example)
    ledger["tier_rules"][tier].append(rule)
    _save_ledger(ledger)
    logger.info(f"Added {tier}-tier voice rule [{domain}]: {text[:60]}")
    return rule


def add_client_rule(
    client_name: str,
    domain: str,
    text: str,
    source: str = "commander_edit",
    example: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a rule specific to a named client."""
    ledger = _load_ledger()
    key = client_name.strip()
    if key not in ledger["client_rules"]:
        ledger["client_rules"][key] = []
    rule = _make_rule(domain, text, source, example)
    ledger["client_rules"][key].append(rule)
    _save_ledger(ledger)
    logger.info(f"Added client voice rule for {key} [{domain}]: {text[:60]}")
    return rule


def remove_rule(
    scope: str,
    index: int,
    tier_or_client: Optional[str] = None,
) -> bool:
    """Remove a rule by scope (global/tier/client) and index."""
    ledger = _load_ledger()
    try:
        if scope == "global":
            ledger["global_rules"].pop(index)
        elif scope == "tier" and tier_or_client:
            ledger["tier_rules"][tier_or_client].pop(index)
        elif scope == "client" and tier_or_client:
            ledger["client_rules"][tier_or_client].pop(index)
        else:
            return False
        _save_ledger(ledger)
        return True
    except (IndexError, KeyError):
        return False


# ---------------------------------------------------------------------------
# Retrieval — build injection block for persona prompts
# ---------------------------------------------------------------------------

def get_voice_rules(
    client_name: Optional[str] = None,
    tier: Optional[str] = None,
) -> str:
    """Build a voice rules injection block for persona system prompts.

    Cascading specificity: global → tier → client-specific.
    Returns empty string if no rules exist.
    """
    ledger = _load_ledger()
    rules_to_inject: List[Dict] = []

    # 1. Global rules always apply
    rules_to_inject.extend(ledger.get("global_rules", []))

    # 2. Tier rules if tier specified
    if tier and tier in ledger.get("tier_rules", {}):
        rules_to_inject.extend(ledger["tier_rules"][tier])

    # 3. Client-specific rules (highest specificity)
    if client_name:
        # Fuzzy match: check if client_name appears in any key
        for key, client_rules in ledger.get("client_rules", {}).items():
            if client_name.lower() in key.lower() or key.lower() in client_name.lower():
                rules_to_inject.extend(client_rules)

    if not rules_to_inject:
        return ""

    # Increment applied counts
    _increment_applied(ledger, rules_to_inject)

    # Format injection block
    lines = ["\nCOMMANDER'S VOICE RULES (apply these to all client-facing output):"]
    for r in rules_to_inject:
        prefix = f"[{r['domain']}]"
        lines.append(f"- {prefix} {r['text']}")
        if r.get("example"):
            lines.append(f"  Example: {r['example']}")

    return "\n".join(lines)


def _increment_applied(ledger: Dict, rules: List[Dict]):
    """Increment applied_count for matched rules and save."""
    for r in rules:
        r["applied_count"] = r.get("applied_count", 0) + 1
    _save_ledger(ledger)


# ---------------------------------------------------------------------------
# Import from learning compiler
# ---------------------------------------------------------------------------

def import_from_learning_compiler() -> int:
    """Pull voice-domain approved principles from the learning compiler
    and add them as global voice rules (deduplicating).

    Returns count of new rules imported.
    """
    try:
        from thunderbird_learning import list_rules
    except ImportError:
        logger.warning("Learning compiler not available")
        return 0

    voice_principles = list_rules(status="approved", domain="voice")
    if not voice_principles:
        return 0

    ledger = _load_ledger()
    existing_texts = {r["text"] for r in ledger.get("global_rules", [])}
    # Also check tier/client rules
    for rules in ledger.get("tier_rules", {}).values():
        existing_texts.update(r["text"] for r in rules)
    for rules in ledger.get("client_rules", {}).values():
        existing_texts.update(r["text"] for r in rules)

    imported = 0
    for p in voice_principles:
        text = p.get("principle_text", "")
        if text and text not in existing_texts:
            tier = p.get("client_tier")
            if tier and tier in VALID_TIERS:
                add_tier_rule(tier, "phrasing", text, source="learning_compiler")
            else:
                add_global_rule("phrasing", text, source="learning_compiler")
            existing_texts.add(text)
            imported += 1

    logger.info(f"Imported {imported} voice rules from learning compiler")
    return imported


# ---------------------------------------------------------------------------
# Seed ledger with known principles
# ---------------------------------------------------------------------------

def seed_initial_rules():
    """Seed the voice ledger with principles extracted from Mar 19-20 email traffic.

    Safe to call multiple times — checks for existing rules before adding.
    """
    ledger = _load_ledger()
    if _count_rules(ledger) > 0:
        logger.info("Voice ledger already seeded — skipping")
        return

    # Global rules (from feedback_voice_learning_principles.md)
    globals_to_add = [
        ("signoff", 'Sign-off: "Thanks, John" — never "Best," never "Warm regards," never a paragraph.',
         None, "Thanks,\nJohn"),
        ("tone", "Mirror warmth, be shorter and more certain. Client uncertain → John is steady.",
         None, None),
        ("anti_pattern", "Never upsell, add extras, or pad with filler in routine replies.",
         None, None),
    ]

    # Tier: paying clients
    paying_rules = [
        ("length", "Four sentences max for routine replies. Confirm action, confirm ask, close.",
         None, None),
        ("structure", "Length is appropriate when the letter does several things (payment + portal + relationship). Don't shorten multi-purpose letters.",
         None, None),
    ]

    # Tier: vendor
    vendor_rules = [
        ("tone", "Transactional but personal. Correct the record matter-of-factly, don't make it a production.",
         None, '"Thanks for sending."'),
    ]

    # Tier: staff
    staff_rules = [
        ("structure", "Short tasking with confirmation request. Task + how to acknowledge.",
         None, '"Scan this into dossier. Report complete or ask questions."'),
        ("structure", 'Credit + next action, one line each.',
         None, '"Excellent analysis. Develop a deeper paper on this."'),
        ("phrasing", 'Embedded directives in operational replies are standing orders. Staff must catch them.',
         None, '"COS, add flights from IAD NON SOUTHWEST from now on."'),
    ]

    for domain, text, source, example in globals_to_add:
        add_global_rule(domain, text, source=source or "mar20_email_analysis", example=example)

    for domain, text, source, example in paying_rules:
        add_tier_rule("paying", domain, text, source=source or "mar20_email_analysis", example=example)

    for domain, text, source, example in vendor_rules:
        add_tier_rule("vendor", domain, text, source=source or "mar20_email_analysis", example=example)

    for domain, text, source, example in staff_rules:
        add_tier_rule("staff", domain, text, source=source or "mar20_email_analysis", example=example)

    logger.info(f"Voice ledger seeded with {_count_rules(_load_ledger())} initial rules")


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def get_ledger_summary() -> str:
    """Return a formatted summary of the voice ledger for briefings."""
    ledger = _load_ledger()
    total = _count_rules(ledger)

    if total == 0:
        return ""

    lines = [f"**Voice Ledger:** {total} rules"]

    g = len(ledger.get("global_rules", []))
    if g:
        lines.append(f"  - {g} global")

    for tier, rules in ledger.get("tier_rules", {}).items():
        if rules:
            lines.append(f"  - {len(rules)} {tier}-tier")

    for client, rules in ledger.get("client_rules", {}).items():
        if rules:
            lines.append(f"  - {len(rules)} {client}-specific")

    # Top applied rules
    all_rules = list(ledger.get("global_rules", []))
    for rules in ledger.get("tier_rules", {}).values():
        all_rules.extend(rules)
    for rules in ledger.get("client_rules", {}).values():
        all_rules.extend(rules)

    top = sorted(all_rules, key=lambda r: r.get("applied_count", 0), reverse=True)[:3]
    if top and top[0].get("applied_count", 0) > 0:
        lines.append("  Most-applied:")
        for r in top:
            if r.get("applied_count", 0) > 0:
                lines.append(f"    [{r['domain']}] {r['text'][:60]}... ({r['applied_count']}x)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MCP Tool Registration
# ---------------------------------------------------------------------------

def register_voice_ledger_tools(mcp_server):
    """Register voice ledger tools with the MCP server."""

    @mcp_server.tool(
        name="voice_ledger_add",
        annotations={"title": "Add Voice Rule to Ledger"},
    )
    async def voice_ledger_add_tool(
        scope: str,
        domain: str,
        text: str,
        tier_or_client: str = "",
        example: str = "",
        source: str = "commander_edit",
    ) -> str:
        """Add a voice rule. scope: global/tier/client. domain: greeting/signoff/tone/length/etc."""
        try:
            if scope == "global":
                rule = add_global_rule(domain, text, source, example or None)
            elif scope == "tier":
                rule = add_tier_rule(tier_or_client, domain, text, source, example or None)
            elif scope == "client":
                rule = add_client_rule(tier_or_client, domain, text, source, example or None)
            else:
                return json.dumps({"error": f"Invalid scope '{scope}'. Use global/tier/client."})
            return json.dumps({"status": "added", "rule": rule}, indent=2, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp_server.tool(
        name="voice_ledger_get",
        annotations={"title": "Get Voice Rules for Context", "readOnlyHint": True},
    )
    async def voice_ledger_get_tool(
        client_name: str = "",
        tier: str = "",
    ) -> str:
        """Get applicable voice rules for a client/tier context."""
        block = get_voice_rules(
            client_name=client_name or None,
            tier=tier or None,
        )
        if not block:
            return json.dumps({"status": "empty", "message": "No voice rules found for this context"})
        return json.dumps({"status": "ok", "rules_block": block})

    @mcp_server.tool(
        name="voice_ledger_list",
        annotations={"title": "List All Voice Rules", "readOnlyHint": True},
    )
    async def voice_ledger_list_tool() -> str:
        """List all rules in the voice ledger."""
        ledger = _load_ledger()
        return json.dumps({
            "total_rules": _count_rules(ledger),
            "global": ledger.get("global_rules", []),
            "tier_rules": ledger.get("tier_rules", {}),
            "client_rules": ledger.get("client_rules", {}),
        }, indent=2, default=str)

    @mcp_server.tool(
        name="voice_ledger_import",
        annotations={"title": "Import Voice Rules from Learning Compiler"},
    )
    async def voice_ledger_import_tool() -> str:
        """Pull approved voice principles from learning compiler into ledger."""
        count = import_from_learning_compiler()
        return json.dumps({"status": "imported", "new_rules": count})

    @mcp_server.tool(
        name="voice_ledger_seed",
        annotations={"title": "Seed Voice Ledger with Initial Rules"},
    )
    async def voice_ledger_seed_tool() -> str:
        """Seed the voice ledger with known principles from Mar 19-20 email traffic."""
        seed_initial_rules()
        ledger = _load_ledger()
        return json.dumps({"status": "seeded", "total_rules": _count_rules(ledger)})

    @mcp_server.tool(
        name="voice_ledger_remove",
        annotations={"title": "Remove Voice Rule"},
    )
    async def voice_ledger_remove_tool(
        scope: str,
        index: int,
        tier_or_client: str = "",
    ) -> str:
        """Remove a voice rule by scope and index."""
        ok = remove_rule(scope, index, tier_or_client or None)
        return json.dumps({"status": "removed" if ok else "not_found"})

    logger.info("Voice Ledger tools registered (6 tools)")
