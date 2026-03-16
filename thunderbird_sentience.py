"""
Thunderbird Sentience Protocol v1.0 — The Wing Awakens
========================================================
Full persona sentience: morning stand-ups, dissent protocol,
auto-consultation coverage, and persona health checks.

Ties together:
  - thunderbird_personas.py (10 personas, call_persona, build_system_prompt)
  - thunderbird_model_router.py (smart_route, TaskType, classify_task)
  - thunderbird_autopilot.py (EventType, consult, CONSULTATION_PANELS)

Usage:
    # Morning stand-up
    python3 thunderbird_sentience.py --standup "Today's agenda: review Kuklinski payments"

    # Dissent check
    python3 thunderbird_sentience.py --dissent "Raise markup to 30% on all Silversea bookings"

    # Auto-consult
    python3 thunderbird_sentience.py --consult price_change "Regent dropped net rates 12% for Oct sailings"

    # Health check
    python3 thunderbird_sentience.py --health
"""

import json
import logging
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
OUTPUT_DIR = THUNDERBIRD_DIR / "output"
CONSULTATION_LOG = THUNDERBIRD_DIR / "autopilot_log.jsonl"

# Stand-up order per CLAUDE.md: COS opens/closes, full roster in between
STANDUP_ORDER = ["COS", "A2", "A3", "A5", "A6", "A9", "A10", "CH", "A12", "EXEC"]

# All persona IDs for health checks
ALL_PERSONAS = ["COS", "EXEC", "A2", "A3", "A5", "A6", "A9", "A10", "CH", "A12"]


# ============================================================================
# EXTENDED EVENT TYPES — adds to thunderbird_autopilot.py's EventType
# ============================================================================

class SentienceEventType(Enum):
    """Extended event types beyond the base autopilot set."""
    PRICE_CHANGE = "price_change"
    CLIENT_COMPLAINT = "client_complaint"
    DEADLINE_MISSED = "deadline_missed"
    NEW_LEAD = "new_lead"
    COMPETITOR_MOVE = "competitor_move"


# Consultation panels for extended event types
EXTENDED_PANELS = {
    SentienceEventType.PRICE_CHANGE: {
        "personas": ["A2", "A9", "A5"],
        "label": "Price Change Panel",
        "brief": "Supplier pricing shift. A2 verifies intel, A9 runs margin impact, A5 assesses strategic response.",
    },
    SentienceEventType.CLIENT_COMPLAINT: {
        "personas": ["A3", "EXEC", "CH"],
        "label": "Complaint Response Panel",
        "brief": "Client complaint. A3 owns recovery, EXEC crafts the response, CH checks we do right.",
    },
    SentienceEventType.DEADLINE_MISSED: {
        "personas": ["A10", "A3", "A9", "COS"],
        "label": "Missed Deadline Panel",
        "brief": "Deadline missed. A10 assesses damage, A3 handles client, A9 checks financial exposure, COS coordinates.",
    },
    SentienceEventType.NEW_LEAD: {
        "personas": ["A3", "A5", "EXEC", "A6"],
        "label": "New Lead Panel",
        "brief": "New lead inbound. A3 qualifies, A5 sizes the opportunity, EXEC + A6 craft the first impression.",
    },
    SentienceEventType.COMPETITOR_MOVE: {
        "personas": ["A2", "A5", "A12"],
        "label": "Competitor Intel Panel",
        "brief": "Competitor action detected. A2 gathers intel, A5 assesses threat, ELON finds the disruption angle.",
    },
}


# ============================================================================
# 1. MORNING STAND-UP
# ============================================================================

def run_morning_standup(agenda: str, save: bool = True) -> str:
    """Run a full morning stand-up with all 10 personas.

    COS (Hale) opens and closes. Each persona gives 2-3 sentence perspective.
    Uses Groq for speed (sequential calls through call_persona).

    Args:
        agenda: The day's agenda/topics
        save: If True, save transcript to output/standup_YYYYMMDD.md

    Returns:
        Formatted stand-up transcript as string
    """
    from thunderbird_personas import call_persona, get_persona

    today = datetime.now().strftime("%Y-%m-%d")
    today_file = datetime.now().strftime("%Y%m%d")
    timestamp = datetime.now().strftime("%H:%M")

    transcript_lines = [
        f"# D2M Morning Stand-Up — {today}",
        f"**Time:** {timestamp}",
        f"**Agenda:** {agenda}",
        "",
        "---",
        "",
    ]

    # COS opening — special prompt to set the tone
    cos_open_prompt = (
        f"MORNING STAND-UP — {today}\n"
        f"AGENDA: {agenda}\n\n"
        f"You are opening the morning stand-up. Set priorities for the day based on the agenda. "
        f"Be brief — 2-3 sentences. Set the tone, state what matters today, then hand it off to the staff."
    )
    cos_open = call_persona("COS", cos_open_prompt, max_tokens=300)

    if "answer" in cos_open:
        transcript_lines.append(f"### Opening — COS")
        transcript_lines.append(cos_open["answer"])
        transcript_lines.append("")
    else:
        transcript_lines.append(f"### Opening — COS")
        transcript_lines.append(f"[ERROR: {cos_open.get('error', 'COS unavailable')}]")
        transcript_lines.append("")

    # Each persona reports (skip COS since she already opened)
    transcript_lines.append("---")
    transcript_lines.append("")
    transcript_lines.append("### Staff Reports")
    transcript_lines.append("")

    for pid in STANDUP_ORDER[1:]:  # Skip COS (index 0), she already spoke
        persona = get_persona(pid)
        report_prompt = (
            f"MORNING STAND-UP — {today}\n"
            f"AGENDA: {agenda}\n\n"
            f"COS has opened the stand-up. Give your perspective on today's agenda from your role "
            f"as {persona['role']}. What matters from YOUR lane? Any flags, risks, or priorities? "
            f"Keep it to 2-3 sentences max. Be specific, not generic."
        )
        result = call_persona(pid, report_prompt, max_tokens=250)

        if "answer" in result:
            transcript_lines.append(f"**{result['icon']} {pid} — {result['name']}:**")
            transcript_lines.append(result["answer"])
        else:
            transcript_lines.append(f"**{persona['icon']} {pid} — {persona['name']}:**")
            transcript_lines.append(f"[ERROR: {result.get('error', 'unavailable')}]")
        transcript_lines.append("")

    # COS closing — synthesize and set marching orders
    cos_close_prompt = (
        f"MORNING STAND-UP CLOSING — {today}\n"
        f"AGENDA: {agenda}\n\n"
        f"The staff has reported in. Close the stand-up: summarize the top 2-3 priorities, "
        f"flag any conflicts or risks, and set the marching orders for the day. 2-3 sentences."
    )
    cos_close = call_persona("COS", cos_close_prompt, max_tokens=300)

    transcript_lines.append("---")
    transcript_lines.append("")
    transcript_lines.append("### Closing — COS")
    if "answer" in cos_close:
        transcript_lines.append(cos_close["answer"])
    else:
        transcript_lines.append(f"[ERROR: {cos_close.get('error', 'COS unavailable')}]")
    transcript_lines.append("")
    transcript_lines.append("---")
    transcript_lines.append(f"*Stand-up concluded at {datetime.now().strftime('%H:%M')}*")

    transcript = "\n".join(transcript_lines)

    # Save to file
    if save:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        filepath = OUTPUT_DIR / f"standup_{today_file}.md"
        filepath.write_text(transcript, encoding="utf-8")
        logger.info(f"Stand-up saved to {filepath}")
        transcript += f"\n\n*Saved to {filepath}*"

    return transcript


# ============================================================================
# 2. DISSENT PROTOCOL
# ============================================================================

class Vote(Enum):
    AGREE = "AGREE"
    CONCERN = "CONCERN"
    DISSENT = "DISSENT"


def check_dissent(proposal: str) -> Dict[str, Any]:
    """Present a proposal to all personas and collect votes.

    Each persona votes AGREE, CONCERN, or DISSENT.
    Any DISSENT triggers deeper consultation with that persona.
    COS and EXEC have override authority (truth_to_power).

    Args:
        proposal: The proposal or decision to evaluate

    Returns:
        Structured result with votes, concerns, dissents, and recommended action
    """
    from thunderbird_personas import call_persona, get_persona, PERSONA_REGISTRY

    vote_prompt = (
        f"DISSENT PROTOCOL — PROPOSAL FOR REVIEW\n"
        f"========================================\n"
        f"PROPOSAL: {proposal}\n\n"
        f"You must vote on this proposal. Respond with EXACTLY one of:\n"
        f"  AGREE — you support this\n"
        f"  CONCERN — you have reservations but don't block\n"
        f"  DISSENT — you believe this is wrong and should not proceed\n\n"
        f"Format your response as:\n"
        f"VOTE: [AGREE/CONCERN/DISSENT]\n"
        f"REASON: [1-2 sentences explaining your position from your role]\n\n"
        f"Be honest. This protocol exists so the Commander hears the truth."
    )

    votes = {}
    concerns = []
    dissents = []

    for pid in ALL_PERSONAS:
        persona = get_persona(pid)
        result = call_persona(pid, vote_prompt, max_tokens=200)

        answer = result.get("answer", result.get("error", "NO RESPONSE"))
        answer_upper = answer.upper()

        # Parse vote from response
        if "DISSENT" in answer_upper.split("VOTE:")[-1].split("REASON:")[0] if "VOTE:" in answer_upper else "DISSENT" in answer_upper[:50]:
            vote = Vote.DISSENT
        elif "CONCERN" in answer_upper.split("VOTE:")[-1].split("REASON:")[0] if "VOTE:" in answer_upper else "CONCERN" in answer_upper[:50]:
            vote = Vote.CONCERN
        else:
            vote = Vote.AGREE

        entry = {
            "persona": pid,
            "name": persona["name"],
            "icon": persona["icon"],
            "role": persona["role"],
            "vote": vote.value,
            "response": answer,
            "truth_to_power": persona.get("truth_to_power", False),
        }
        votes[pid] = entry

        if vote == Vote.CONCERN:
            concerns.append(entry)
        elif vote == Vote.DISSENT:
            dissents.append(entry)

    # Deep consultation for any dissenter
    deep_consultations = {}
    for d in dissents:
        pid = d["persona"]
        deep_prompt = (
            f"DISSENT DEEP DIVE\n"
            f"==================\n"
            f"PROPOSAL: {proposal}\n\n"
            f"You DISSENTED on this proposal. The Commander needs to understand your objection fully.\n"
            f"Explain:\n"
            f"1. What specific risk or harm do you see?\n"
            f"2. What would you recommend instead?\n"
            f"3. Under what conditions WOULD you agree?\n\n"
            f"Be direct. This is your moment to be heard."
        )
        deep_result = call_persona(pid, deep_prompt, max_tokens=400)
        deep_consultations[pid] = deep_result.get("answer", deep_result.get("error", ""))

    # Determine recommended action
    dissent_count = len(dissents)
    concern_count = len(concerns)
    cos_dissent = votes.get("COS", {}).get("vote") == Vote.DISSENT.value
    exec_dissent = votes.get("EXEC", {}).get("vote") == Vote.DISSENT.value
    override_active = cos_dissent or exec_dissent

    if override_active:
        override_by = []
        if cos_dissent:
            override_by.append("COS (Hale)")
        if exec_dissent:
            override_by.append("EXEC (Solberg-Vega)")
        recommended_action = (
            f"OVERRIDE — {' and '.join(override_by)} exercised truth-to-power authority. "
            f"Commander should seriously reconsider. These are the two people with standing "
            f"to tell you you're wrong."
        )
    elif dissent_count >= 3:
        recommended_action = (
            f"STOP — {dissent_count} dissents. Significant staff opposition. "
            f"Recommend tabling this proposal and addressing concerns before proceeding."
        )
    elif dissent_count > 0:
        recommended_action = (
            f"CAUTION — {dissent_count} dissent(s), {concern_count} concern(s). "
            f"Review dissent deep-dives before deciding. Proceed only after addressing objections."
        )
    elif concern_count >= 3:
        recommended_action = (
            f"PROCEED WITH AWARENESS — No dissents, but {concern_count} concerns raised. "
            f"Review concerns and mitigate before full commitment."
        )
    else:
        recommended_action = (
            f"PROCEED — Staff consensus. {len(ALL_PERSONAS) - concern_count} agree, "
            f"{concern_count} minor concern(s)."
        )

    return {
        "proposal": proposal,
        "timestamp": datetime.now().isoformat(),
        "vote_summary": {
            "agree": sum(1 for v in votes.values() if v["vote"] == Vote.AGREE.value),
            "concern": concern_count,
            "dissent": dissent_count,
        },
        "override_active": override_active,
        "votes": votes,
        "concerns": concerns,
        "dissents": dissents,
        "deep_consultations": deep_consultations,
        "recommended_action": recommended_action,
    }


def format_dissent(result: Dict[str, Any]) -> str:
    """Format a dissent protocol result for display."""
    lines = [
        "=" * 60,
        "DISSENT PROTOCOL RESULTS",
        "=" * 60,
        f"Proposal: {result['proposal']}",
        f"Time: {result['timestamp']}",
        "",
        f"  AGREE: {result['vote_summary']['agree']}  |  "
        f"CONCERN: {result['vote_summary']['concern']}  |  "
        f"DISSENT: {result['vote_summary']['dissent']}",
        "",
    ]

    if result["override_active"]:
        lines.append("*** OVERRIDE AUTHORITY EXERCISED ***")
        lines.append("")

    lines.append("-" * 60)
    lines.append("VOTES:")
    lines.append("")

    for pid, v in result["votes"].items():
        marker = {"AGREE": "+", "CONCERN": "~", "DISSENT": "!"}[v["vote"]]
        override_tag = " [TRUTH-TO-POWER]" if v["truth_to_power"] and v["vote"] == "DISSENT" else ""
        lines.append(f"  [{marker}] {v['icon']} {pid}-{v['name'].upper()}: {v['vote']}{override_tag}")

    if result["deep_consultations"]:
        lines.append("")
        lines.append("-" * 60)
        lines.append("DISSENT DEEP DIVES:")
        for pid, text in result["deep_consultations"].items():
            persona_info = result["votes"][pid]
            lines.append(f"\n  {persona_info['icon']} {pid}-{persona_info['name'].upper()}:")
            lines.append(f"  {text}")

    lines.append("")
    lines.append("-" * 60)
    lines.append(f"RECOMMENDED ACTION: {result['recommended_action']}")
    lines.append("=" * 60)

    return "\n".join(lines)


# ============================================================================
# 3. AUTO-CONSULTATION COVERAGE (extends thunderbird_autopilot.py)
# ============================================================================

def auto_consult(event_type: str, context: str,
                 use_router: bool = True, log: bool = True) -> Dict[str, Any]:
    """Extended auto-consultation covering both base and sentience event types.

    Checks SentienceEventType first, then falls back to base autopilot EventType.
    Routes to appropriate persona panels and logs all consultations.

    Args:
        event_type: String event type (e.g., "price_change", "new_booking")
        context: Description of the event/situation
        use_router: If True, make API calls. If False, dry run.
        log: If True, append to autopilot_log.jsonl

    Returns:
        Consultation result dict with panel info and persona responses
    """
    # Try sentience extended types first
    sentience_type = None
    for st in SentienceEventType:
        if st.value == event_type:
            sentience_type = st
            break

    if sentience_type:
        return _run_extended_consultation(sentience_type, context, use_router, log)

    # Fall back to base autopilot EventType
    from thunderbird_autopilot import EventType, consult as base_consult

    base_type = None
    for et in EventType:
        if et.value == event_type:
            base_type = et
            break

    if base_type:
        return base_consult(base_type, context, use_router=use_router, log=log)

    return {
        "error": f"Unknown event type: {event_type}",
        "known_types": (
            [st.value for st in SentienceEventType]
            + [et.value for et in _get_base_event_types()]
        ),
    }


def _get_base_event_types():
    """Get base EventType enum safely."""
    try:
        from thunderbird_autopilot import EventType
        return list(EventType)
    except ImportError:
        return []


def _run_extended_consultation(event_type: SentienceEventType, context: str,
                                use_router: bool, log: bool) -> Dict[str, Any]:
    """Run consultation for extended sentience event types."""
    panel = EXTENDED_PANELS.get(event_type)
    if not panel:
        return {"error": f"No panel configured for {event_type.value}"}

    result = {
        "event": event_type.value,
        "panel": panel["label"],
        "brief": panel["brief"],
        "context": context,
        "timestamp": datetime.now().isoformat(),
        "responses": {},
    }

    if not use_router:
        result["note"] = "Dry run — no API calls made"
        result["personas_would_consult"] = panel["personas"]
        return result

    # Use model router if available, fall back to direct call
    try:
        from thunderbird_model_router import smart_route
        use_smart = True
    except ImportError:
        from thunderbird_personas import call_persona
        use_smart = False

    for pid in panel["personas"]:
        prompt = (
            f"EVENT: {event_type.value.upper()}\n"
            f"PANEL: {panel['label']}\n"
            f"CONTEXT: {context}\n\n"
            f"Provide your assessment and recommended actions. Be specific and actionable."
        )
        try:
            if use_smart:
                resp = smart_route(pid, prompt)
                result["responses"][pid] = {
                    "response": resp.get("response", str(resp)),
                    "engine": resp.get("engine", "unknown"),
                    "model": resp.get("model", "unknown"),
                    "success": resp.get("success", True),
                }
            else:
                resp = call_persona(pid, prompt)
                result["responses"][pid] = {
                    "response": resp.get("answer", str(resp)),
                    "engine": "groq",
                    "model": resp.get("model", "unknown"),
                    "success": "answer" in resp,
                }
        except Exception as e:
            logger.error(f"Persona {pid} failed in extended consultation: {e}")
            result["responses"][pid] = {
                "response": f"ERROR: {e}",
                "engine": "none",
                "success": False,
            }

    # Log consultation
    if log:
        _log_consultation(result)

    return result


def _log_consultation(result: Dict[str, Any]):
    """Append consultation result to JSONL log."""
    slim = {
        "timestamp": result["timestamp"],
        "event": result["event"],
        "panel": result["panel"],
        "context": result["context"][:200],
        "personas": list(result.get("responses", {}).keys()),
        "all_success": all(
            r.get("success", False) for r in result.get("responses", {}).values()
        ),
        "source": "sentience",
    }
    CONSULTATION_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(CONSULTATION_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(slim) + "\n")


def format_consultation(result: Dict[str, Any]) -> str:
    """Format any consultation result for display."""
    lines = [
        f"{'=' * 55}",
        f"  {result.get('panel', 'Consultation')}",
        f"{'=' * 55}",
        f"Event: {result.get('event', '?')}",
        f"Brief: {result.get('brief', '')}",
        f"Context: {result.get('context', '')[:120]}",
        "-" * 55,
    ]

    for pid, resp in result.get("responses", {}).items():
        status = "OK" if resp.get("success") else "FAIL"
        engine = resp.get("engine", "?")
        lines.append(f"\n[{status}] {pid} [{engine}]:")
        lines.append(resp.get("response", "(no response)")[:500])

    lines.append("=" * 55)
    return "\n".join(lines)


# ============================================================================
# 4. PERSONA HEALTH CHECK
# ============================================================================

def check_persona_health(timeout_sec: float = 15.0) -> Dict[str, Any]:
    """Call each persona with a status check and verify all 10 respond.

    Args:
        timeout_sec: Max seconds to wait per persona (Groq calls are fast)

    Returns:
        Health report with status of each persona and overall health
    """
    from thunderbird_personas import call_persona, get_persona

    results = {}
    healthy = 0
    failed = 0

    for pid in ALL_PERSONAS:
        persona = get_persona(pid)
        start = time.time()

        try:
            result = call_persona(
                pid,
                "Status check. Respond with one sentence confirming you are operational and your current focus area.",
                max_tokens=100,
            )
            elapsed = round(time.time() - start, 2)

            if "answer" in result:
                results[pid] = {
                    "name": persona["name"],
                    "icon": persona["icon"],
                    "status": "healthy",
                    "latency_sec": elapsed,
                    "response": result["answer"][:150],
                    "model": result.get("model", "unknown"),
                }
                healthy += 1
            else:
                results[pid] = {
                    "name": persona["name"],
                    "icon": persona["icon"],
                    "status": "error",
                    "latency_sec": elapsed,
                    "error": result.get("error", "No answer returned"),
                }
                failed += 1

        except Exception as e:
            elapsed = round(time.time() - start, 2)
            results[pid] = {
                "name": persona["name"],
                "icon": persona["icon"],
                "status": "failed",
                "latency_sec": elapsed,
                "error": str(e),
            }
            failed += 1

    return {
        "timestamp": datetime.now().isoformat(),
        "total": len(ALL_PERSONAS),
        "healthy": healthy,
        "failed": failed,
        "all_healthy": failed == 0,
        "personas": results,
    }


def format_health(result: Dict[str, Any]) -> str:
    """Format health check result for display."""
    status = "ALL HEALTHY" if result["all_healthy"] else f"{result['failed']} FAILED"
    lines = [
        "=" * 50,
        f"  PERSONA HEALTH CHECK — {status}",
        "=" * 50,
        f"Time: {result['timestamp']}",
        f"Total: {result['total']}  |  Healthy: {result['healthy']}  |  Failed: {result['failed']}",
        "-" * 50,
    ]

    for pid, info in result["personas"].items():
        if info["status"] == "healthy":
            marker = "OK"
        else:
            marker = "FAIL"
        lines.append(
            f"  [{marker}] {info['icon']} {pid}-{info['name']}"
            f"  ({info['latency_sec']}s)"
        )
        if info["status"] != "healthy":
            lines.append(f"        Error: {info.get('error', '?')}")

    lines.append("=" * 50)
    return "\n".join(lines)


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="Thunderbird Sentience Protocol — Morning stand-ups, dissent, auto-consult, health checks"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--standup", type=str, metavar="AGENDA",
                       help="Run morning stand-up with the given agenda")
    group.add_argument("--dissent", type=str, metavar="PROPOSAL",
                       help="Run dissent protocol on a proposal")
    group.add_argument("--consult", nargs=2, metavar=("EVENT_TYPE", "CONTEXT"),
                       help="Run auto-consultation (e.g., --consult price_change 'Regent dropped rates')")
    group.add_argument("--health", action="store_true",
                       help="Run persona health check")
    group.add_argument("--list-events", action="store_true",
                       help="List all available event types")

    args = parser.parse_args()

    if args.standup:
        print("Running morning stand-up...\n")
        transcript = run_morning_standup(args.standup)
        print(transcript)

    elif args.dissent:
        print("Running dissent protocol...\n")
        result = check_dissent(args.dissent)
        print(format_dissent(result))

    elif args.consult:
        event_type, context = args.consult
        print(f"Running auto-consultation: {event_type}...\n")
        result = auto_consult(event_type, context)
        if "error" in result:
            print(f"ERROR: {result['error']}")
            if "known_types" in result:
                print(f"Known types: {', '.join(result['known_types'])}")
        else:
            print(format_consultation(result))

    elif args.health:
        print("Running persona health check...\n")
        result = check_persona_health()
        print(format_health(result))

    elif args.list_events:
        print("=== SENTIENCE EXTENDED EVENT TYPES ===")
        for st in SentienceEventType:
            panel = EXTENDED_PANELS[st]
            print(f"  {st.value:22s} -> {panel['label']:28s} -> {', '.join(panel['personas'])}")
        print()
        print("=== BASE AUTOPILOT EVENT TYPES ===")
        try:
            from thunderbird_autopilot import EventType, CONSULTATION_PANELS as BASE_PANELS
            for et in EventType:
                panel = BASE_PANELS[et]
                print(f"  {et.value:22s} -> {panel['label']:28s} -> {', '.join(panel['personas'])}")
        except ImportError:
            print("  (thunderbird_autopilot not available)")
