"""
Thunderbird Staff Summary Sheet — IOC Build 2
===============================================
Formal coordination mechanism modeled on USAF AF Form 1768.

Skill addressed:
  5. Debate Then Align — show real disagreement, resolve it, Commander decides.

Architecture:
  Action Officer drafts SSS → routes to coordinators → CONCUR/NON-CONCUR collected
  → non-concurrence memos + rebuttals → Commander receives full package

Push mechanism: any persona can initiate an SSS at any time.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Coordination routing tables
# ---------------------------------------------------------------------------

# IOC-level: all domains coordinate
IOC_COORDINATORS = ["COS", "EXEC", "A2", "A3", "A5", "A6", "A9", "CH", "A12"]

# Client-specific: only relevant domains
CLIENT_COORDINATION = {
    "payment":    ["A3", "A9", "COS"],
    "flights":    ["A2", "A3", "COS"],
    "excursions": ["A2", "A3", "A6"],
    "insurance":  ["A9", "A3", "COS"],
    "pricing":    ["A9", "A5", "COS"],
    "comms":      ["A3", "A6", "EXEC", "COS"],
    "logistics":  ["A3", "COS"],
    "hotel":      ["A2", "A3", "COS"],
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CoordinationBlock:
    """One coordinator's response on an SSS."""
    persona_id: str
    action: str = "COORD"           # COORD / APPR / INFO
    status: str = "pending"         # concur / non_concur / pending
    comment: Optional[str] = None   # rationale
    memo: Optional[str] = None      # non-concurrence memo text
    rebuttal: Optional[str] = None  # action officer's rebuttal
    timestamp: Optional[str] = None


@dataclass
class StaffSummarySheet:
    """Full SSS package — mirrors AF Form 1768 structure."""
    sss_id: str = field(default_factory=lambda: f"SSS-{uuid.uuid4().hex[:8].upper()}")
    action_officer: str = ""
    scope: str = "client"           # ioc / client / hybrid
    category: Optional[str] = None  # payment, flights, etc. (for client scope)
    ioc_items: List[str] = field(default_factory=list)  # e.g., ["IOC-5", "IOC-8"]
    purpose: str = ""
    background: str = ""
    discussion: str = ""
    views_of_others: str = ""       # populated during coordination
    recommendation: str = ""
    coordination: List[CoordinationBlock] = field(default_factory=list)
    tabs: List[Dict] = field(default_factory=list)  # attached docs
    status: str = "draft"           # draft / coordinating / ready / decided
    decision: Optional[str] = None  # Commander's decision
    created: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    decided_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


# ---------------------------------------------------------------------------
# In-memory store (persists for process lifetime; future: SQLite or JSONL)
# ---------------------------------------------------------------------------

_SSS_STORE: Dict[str, StaffSummarySheet] = {}


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def auto_coordinators(
    scope: str,
    category: Optional[str] = None,
    ioc_items: Optional[List[str]] = None,
    action_officer: Optional[str] = None,
) -> List[str]:
    """Determine who coordinates based on scope.

    - ioc: all 9 domains
    - client: auto-select from CLIENT_COORDINATION by category
    - hybrid: client coordinators + IOC-relevant domains (deduplicated)
    """
    if scope == "ioc":
        coords = list(IOC_COORDINATORS)
    elif scope == "client":
        coords = list(CLIENT_COORDINATION.get(category or "", ["A3", "COS"]))
    elif scope == "hybrid":
        # Start with client coordinators
        coords = list(CLIENT_COORDINATION.get(category or "", ["A3", "COS"]))
        # Add all IOC coordinators for hybrid (Commander's directive: IOC matters get all domains)
        for pid in IOC_COORDINATORS:
            if pid not in coords:
                coords.append(pid)
    else:
        coords = ["COS"]

    # Remove action officer from coordinators (they authored it)
    if action_officer and action_officer in coords:
        coords.remove(action_officer)

    return coords


def create_sss(
    action_officer: str,
    purpose: str,
    background: str,
    discussion: str,
    recommendation: str,
    scope: str = "client",
    category: Optional[str] = None,
    ioc_items: Optional[List[str]] = None,
    tabs: Optional[List[Dict]] = None,
) -> StaffSummarySheet:
    """Create a new Staff Summary Sheet."""
    coordinators = auto_coordinators(scope, category, ioc_items, action_officer)

    sss = StaffSummarySheet(
        action_officer=action_officer,
        scope=scope,
        category=category,
        ioc_items=ioc_items or [],
        purpose=purpose,
        background=background,
        discussion=discussion,
        recommendation=recommendation,
        tabs=tabs or [],
        status="draft",
        coordination=[
            CoordinationBlock(persona_id=pid) for pid in coordinators
        ],
    )

    _SSS_STORE[sss.sss_id] = sss
    logger.info(f"Created {sss.sss_id} by {action_officer} (scope={scope}, {len(coordinators)} coordinators)")
    return sss


def coordinate_sss(sss_id: str) -> StaffSummarySheet:
    """Route SSS to each coordinator via A2A ask(), collect CONCUR/NON-CONCUR.

    Updates the SSS in-place and builds the Views of Others section.
    """
    from thunderbird_a2a import AgentProtocol
    a2a = AgentProtocol()

    sss = _SSS_STORE.get(sss_id)
    if not sss:
        raise ValueError(f"SSS {sss_id} not found")

    sss.status = "coordinating"

    coord_prompt = (
        f"You are coordinating on Staff Summary Sheet {sss.sss_id}.\n\n"
        f"ACTION OFFICER: {sss.action_officer}\n"
        f"PURPOSE: {sss.purpose}\n\n"
        f"BACKGROUND:\n{sss.background}\n\n"
        f"DISCUSSION:\n{sss.discussion}\n\n"
        f"RECOMMENDATION:\n{sss.recommendation}\n\n"
        "---\n"
        "Respond with your coordination position:\n"
        "1. Start with CONCUR or NON-CONCUR\n"
        "2. Provide your rationale (2-3 sentences from your domain expertise)\n"
        "3. If NON-CONCUR, write a brief non-concurrence memo explaining why and what you'd recommend instead\n"
        "Format: POSITION: [CONCUR/NON-CONCUR]\\nRATIONALE: [text]\\nMEMO: [if non-concur]"
    )

    views = []
    for block in sss.coordination:
        try:
            result = a2a.ask(
                target_persona=block.persona_id,
                query=coord_prompt,
                from_persona=sss.action_officer,
                max_tokens=500,
            )
            answer = result.get("answer", "")

            # Parse position
            if "NON-CONCUR" in answer.upper()[:50]:
                block.status = "non_concur"
            else:
                block.status = "concur"

            # Extract rationale and memo
            block.comment = answer
            if block.status == "non_concur":
                # Try to extract memo section
                import re
                memo_match = re.search(r'MEMO:\s*(.*)', answer, re.DOTALL | re.IGNORECASE)
                block.memo = memo_match.group(1).strip() if memo_match else answer

            block.timestamp = datetime.now(timezone.utc).isoformat()

            # Build views entry
            position_icon = "+" if block.status == "concur" else "X"
            views.append(f"[{position_icon}] {block.persona_id}: {block.comment[:200]}")

            logger.info(f"SSS {sss_id}: {block.persona_id} → {block.status}")

        except Exception as e:
            block.status = "pending"
            block.comment = f"Error during coordination: {e}"
            logger.error(f"SSS {sss_id}: {block.persona_id} coordination failed: {e}")

    sss.views_of_others = "\n\n".join(views)
    sss.status = "ready"
    return sss


def resolve_nonconcur(sss_id: str, persona_id: str) -> str:
    """Action officer attempts to resolve a non-concurrence.

    Returns: 'resolved_no_change' | 'resolved_with_changes' | 'unresolved'
    """
    from thunderbird_a2a import AgentProtocol
    a2a = AgentProtocol()

    sss = _SSS_STORE.get(sss_id)
    if not sss:
        raise ValueError(f"SSS {sss_id} not found")

    # Find the non-concurring block
    block = next((b for b in sss.coordination if b.persona_id == persona_id), None)
    if not block or block.status != "non_concur":
        return "no_action_needed"

    # Action officer writes rebuttal
    rebuttal_prompt = (
        f"You are {sss.action_officer}, the action officer on {sss.sss_id}.\n\n"
        f"{persona_id} has NON-CONCURRED with your recommendation.\n\n"
        f"Their non-concurrence memo:\n{block.memo or block.comment}\n\n"
        f"Your original recommendation:\n{sss.recommendation}\n\n"
        "Write a rebuttal memo. Options:\n"
        "1. ACCEPT their point — modify your recommendation (say RESOLVED_WITH_CHANGES)\n"
        "2. DISAGREE — explain why your original recommendation stands (say UNRESOLVED)\n"
        "Start with RESOLVED_WITH_CHANGES or UNRESOLVED, then your rebuttal."
    )

    result = a2a.ask(
        target_persona=sss.action_officer,
        query=rebuttal_prompt,
        from_persona="Commander",
        max_tokens=500,
    )

    rebuttal_text = result.get("answer", "")
    block.rebuttal = rebuttal_text

    if "RESOLVED_WITH_CHANGES" in rebuttal_text.upper()[:50]:
        block.status = "concur"  # Resolved — now concurs with changes
        return "resolved_with_changes"
    else:
        # Unresolved — both memos go to Commander
        return "unresolved"


def present_to_commander(sss_id: str) -> str:
    """Format the full SSS package for Commander presentation.

    Returns formatted markdown string with:
    - SSS body (purpose, background, discussion, recommendation)
    - Views of Others
    - Non-concurrence memos + rebuttals (if any)
    - Coordination tally
    """
    sss = _SSS_STORE.get(sss_id)
    if not sss:
        return f"SSS {sss_id} not found"

    concurs = sum(1 for b in sss.coordination if b.status == "concur")
    non_concurs = sum(1 for b in sss.coordination if b.status == "non_concur")
    pending = sum(1 for b in sss.coordination if b.status == "pending")

    lines = [
        f"# STAFF SUMMARY SHEET — {sss.sss_id}",
        f"**Action Officer:** {sss.action_officer} | **Scope:** {sss.scope}",
        f"**Created:** {sss.created[:19]}",
        "",
        f"## PURPOSE\n{sss.purpose}",
        "",
        f"## BACKGROUND\n{sss.background}",
        "",
        f"## DISCUSSION\n{sss.discussion}",
        "",
    ]

    if sss.views_of_others:
        lines.append(f"## VIEWS OF OTHERS\n{sss.views_of_others}")
        lines.append("")

    lines.append(f"## RECOMMENDATION\n{sss.recommendation}")
    lines.append("")

    # Coordination tally
    lines.append(f"## COORDINATION ({concurs} concur / {non_concurs} non-concur / {pending} pending)")
    for b in sss.coordination:
        icon = {"concur": "+", "non_concur": "X", "pending": "?"}[b.status]
        lines.append(f"  [{icon}] {b.persona_id}: {b.status.upper()}")
    lines.append("")

    # Non-concurrence details
    nc_blocks = [b for b in sss.coordination if b.status == "non_concur"]
    if nc_blocks:
        lines.append("## NON-CONCURRENCE MEMOS")
        for b in nc_blocks:
            lines.append(f"\n### {b.persona_id} — NON-CONCUR")
            lines.append(b.memo or b.comment or "(no memo)")
            if b.rebuttal:
                lines.append(f"\n**Action Officer Rebuttal:**\n{b.rebuttal}")
        lines.append("")

    lines.append("---")
    lines.append(f"**DECISION REQUIRED** — Approve, modify, or reject the recommendation.")
    lines.append(f"Staff Summary Sheet from {sss.action_officer}, D2M Travel")
    lines.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC")

    return "\n".join(lines)


def record_decision(sss_id: str, decision_text: str) -> Dict[str, Any]:
    """Record Commander's decision on an SSS."""
    sss = _SSS_STORE.get(sss_id)
    if not sss:
        return {"error": f"SSS {sss_id} not found"}

    sss.decision = decision_text
    sss.status = "decided"
    sss.decided_at = datetime.now(timezone.utc).isoformat()

    logger.info(f"SSS {sss_id} decided: {decision_text[:100]}")
    return {"sss_id": sss_id, "status": "decided", "decision": decision_text}


def list_sss(status: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """List active/recent SSS packages."""
    sheets = list(_SSS_STORE.values())
    if status:
        sheets = [s for s in sheets if s.status == status]
    sheets.sort(key=lambda s: s.created, reverse=True)
    return [s.to_dict() for s in sheets[:limit]]


# ---------------------------------------------------------------------------
# MCP Tool Registration
# ---------------------------------------------------------------------------

def register_sss_tools(mcp_server):
    """Register Staff Summary Sheet tools with the MCP server."""

    @mcp_server.tool(
        name="sss_create",
        annotations={"title": "Create Staff Summary Sheet"},
    )
    async def sss_create_tool(
        action_officer: str,
        purpose: str,
        background: str,
        discussion: str,
        recommendation: str,
        scope: str = "client",
        category: str = "",
        ioc_items: str = "",
    ) -> str:
        """Create a new Staff Summary Sheet. Any persona can initiate."""
        items = [i.strip() for i in ioc_items.split(",") if i.strip()] if ioc_items else []
        sss = create_sss(
            action_officer=action_officer,
            purpose=purpose,
            background=background,
            discussion=discussion,
            recommendation=recommendation,
            scope=scope,
            category=category or None,
            ioc_items=items,
        )
        return json.dumps({"status": "created", "sss_id": sss.sss_id, "coordinators": [b.persona_id for b in sss.coordination]}, indent=2)

    @mcp_server.tool(
        name="sss_coordinate",
        annotations={"title": "Run SSS Coordination Round"},
    )
    async def sss_coordinate_tool(sss_id: str) -> str:
        """Route SSS to coordinators and collect CONCUR/NON-CONCUR."""
        try:
            sss = coordinate_sss(sss_id)
            concurs = sum(1 for b in sss.coordination if b.status == "concur")
            non_concurs = sum(1 for b in sss.coordination if b.status == "non_concur")
            return json.dumps({
                "status": "coordinated",
                "sss_id": sss_id,
                "concurs": concurs,
                "non_concurs": non_concurs,
                "views": sss.views_of_others[:1000],
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp_server.tool(
        name="sss_resolve",
        annotations={"title": "Resolve Non-Concurrence"},
    )
    async def sss_resolve_tool(sss_id: str, persona_id: str) -> str:
        """Attempt to resolve a non-concurrence between action officer and coordinator."""
        try:
            outcome = resolve_nonconcur(sss_id, persona_id)
            return json.dumps({"sss_id": sss_id, "persona_id": persona_id, "outcome": outcome})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp_server.tool(
        name="sss_present",
        annotations={"title": "Present SSS to Commander", "readOnlyHint": True},
    )
    async def sss_present_tool(sss_id: str) -> str:
        """Format and return the full SSS package for Commander decision."""
        return present_to_commander(sss_id)

    @mcp_server.tool(
        name="sss_decide",
        annotations={"title": "Record Commander Decision on SSS"},
    )
    async def sss_decide_tool(sss_id: str, decision: str) -> str:
        """Record Commander's decision on a Staff Summary Sheet."""
        result = record_decision(sss_id, decision)
        return json.dumps(result, indent=2)

    @mcp_server.tool(
        name="sss_list",
        annotations={"title": "List Staff Summary Sheets", "readOnlyHint": True},
    )
    async def sss_list_tool(status: str = "", limit: int = 20) -> str:
        """List active/recent SSS packages."""
        sheets = list_sss(status=status or None, limit=limit)
        return json.dumps({"count": len(sheets), "sheets": sheets}, indent=2, default=str)

    logger.info("Staff Summary Sheet tools registered (6 tools)")
