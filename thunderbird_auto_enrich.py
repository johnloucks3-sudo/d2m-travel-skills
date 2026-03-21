"""
Thunderbird Auto-Enrichment Engine — Layer 2 Passive Observation
================================================================
When any persona is asked about a client, AUTOMATICALLY pulls context from
all available sources: Gmail threads, Drive docs, Calendar events, dossiers.

Inspired by Google Personal Intelligence (Section 2H): "Treats your entire
Google Workspace as context for every query."

Usage:
    from thunderbird_auto_enrich import enrich_client_context

    # When Dani/COS/any persona needs to discuss a client:
    context = enrich_client_context("Furlow")
    # Returns structured context block for injection into persona prompt

Integration Points:
    - thunderbird_dani_engine.py: inject before Phase 2 (Artist)
    - thunderbird_dani_email.py: inject before email drafting
    - thunderbird_personas.py: inject into any persona call about a client
"""

import json
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
DOSSIER_DIR = THUNDERBIRD_DIR / "dossiers"
CACHE_DIR = THUNDERBIRD_DIR / "cache" / "client_context"
CACHE_TTL_HOURS = 4  # Refresh cache every 4 hours


# ---------------------------------------------------------------------------
# A. Client Name Detection
# ---------------------------------------------------------------------------

def detect_client_names(text: str) -> List[str]:
    """Detect client names mentioned in a query or message.

    Returns list of potential client identifiers (last names, first names,
    or full names) found in the text.
    """
    # Load known client names from dossiers
    known_clients = _get_known_clients()

    found = []
    text_lower = text.lower()

    for client_key, client_data in known_clients.items():
        # Check all name variants
        for name in client_data.get("name_variants", []):
            if name.lower() in text_lower:
                found.append(client_key)
                break

    return list(set(found))


@lru_cache(maxsize=1)
def _get_known_clients() -> Dict[str, Dict]:
    """Build a lookup table of known clients from dossier filenames and content.

    Cached for the session — clear with _get_known_clients.cache_clear().
    """
    clients = {}

    if not DOSSIER_DIR.exists():
        return clients

    for dossier_file in DOSSIER_DIR.glob("*.md"):
        name = dossier_file.stem
        # Parse dossier filenames like "Furlow_Missy_John" or "Lyons_Nancy_Ken"
        parts = name.replace("_", " ").split()
        if not parts:
            continue

        client_key = parts[0]  # Last name as primary key
        name_variants = [client_key] + parts  # All parts are searchable

        # Also read first few lines for additional names
        try:
            content = dossier_file.read_text(encoding="utf-8", errors="replace")[:500]
            # Look for names in the header
            for line in content.split("\n")[:5]:
                if "name" in line.lower() or "#" in line:
                    # Extract capitalized words as potential names
                    words = re.findall(r"\b[A-Z][a-z]+\b", line)
                    name_variants.extend(words)
        except Exception:
            pass

        clients[client_key] = {
            "dossier_file": str(dossier_file),
            "name_variants": list(set(name_variants)),
        }

    return clients


# ---------------------------------------------------------------------------
# B. Context Gatherers (each pulls from one source)
# ---------------------------------------------------------------------------

def _gather_dossier_context(client_key: str) -> str:
    """Pull the client's dossier content."""
    clients = _get_known_clients()
    if client_key not in clients:
        return ""

    dossier_path = clients[client_key]["dossier_file"]
    try:
        content = Path(dossier_path).read_text(encoding="utf-8", errors="replace")
        # Truncate very long dossiers
        if len(content) > 4000:
            content = content[:4000] + "\n[...dossier truncated...]"
        return f"## CLIENT DOSSIER\n{content}"
    except Exception as e:
        logger.warning(f"Failed to read dossier for {client_key}: {e}")
        return ""


def _gather_gmail_context(client_key: str, max_threads: int = 5) -> str:
    """Pull recent Gmail threads mentioning this client.

    Uses the D2M operational Gmail (d2mconcierge@gmail.com).
    """
    try:
        from thunderbird_gmail import _get_gmail_service, _decode_body, _extract_headers

        service = _get_gmail_service()

        # Search for emails mentioning the client name
        query = f"{client_key} newer_than:90d"
        results = service.users().messages().list(
            userId="me", q=query, maxResults=max_threads * 2
        ).execute()

        messages = results.get("messages", [])
        if not messages:
            return ""

        email_summaries = []
        for msg_ref in messages[:max_threads]:
            try:
                msg = service.users().messages().get(
                    userId="me", id=msg_ref["id"], format="full"
                ).execute()
                payload = msg.get("payload", {})
                headers = _extract_headers(
                    payload.get("headers", []),
                    keys={"From", "To", "Subject", "Date"},
                )
                body = _decode_body(payload)

                # Truncate long emails
                if body and len(body) > 1000:
                    body = body[:1000] + "\n[...truncated...]"

                email_summaries.append(
                    f"**From:** {headers.get('From', '?')} | "
                    f"**To:** {headers.get('To', '?')} | "
                    f"**Date:** {headers.get('Date', '?')}\n"
                    f"**Subject:** {headers.get('Subject', '(no subject)')}\n"
                    f"{body or '(no body)'}\n"
                )
            except Exception as e:
                logger.debug(f"Failed to read message: {e}")
                continue

        if not email_summaries:
            return ""

        return (
            f"## RECENT EMAIL THREADS ({len(email_summaries)} messages, last 90 days)\n"
            + "\n---\n".join(email_summaries)
        )

    except Exception as e:
        logger.warning(f"Gmail context failed for {client_key}: {e}")
        return ""


def _gather_calendar_context(client_key: str) -> str:
    """Pull upcoming calendar events mentioning this client."""
    try:
        # Use Google Calendar API if available
        from googleapiclient.discovery import build
        from google.oauth2.service_account import Credentials

        creds_path = THUNDERBIRD_DIR / "credentials.json"
        if not creds_path.exists():
            return ""

        creds = Credentials.from_service_account_file(
            str(creds_path),
            scopes=["https://www.googleapis.com/auth/calendar.readonly"],
        )
        service = build("calendar", "v3", credentials=creds)

        now = datetime.utcnow().isoformat() + "Z"
        future = (datetime.utcnow() + timedelta(days=180)).isoformat() + "Z"

        events_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            timeMax=future,
            q=client_key,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = events_result.get("items", [])
        if not events:
            return ""

        event_lines = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            summary = event.get("summary", "(no title)")
            event_lines.append(f"- {start}: {summary}")

        return (
            f"## UPCOMING CALENDAR EVENTS\n"
            + "\n".join(event_lines)
        )

    except Exception as e:
        logger.debug(f"Calendar context failed for {client_key}: {e}")
        return ""


def _gather_drive_context(client_key: str) -> str:
    """Pull Drive documents related to this client."""
    try:
        from googleapiclient.discovery import build
        from google.oauth2.service_account import Credentials

        creds_path = THUNDERBIRD_DIR / "credentials.json"
        if not creds_path.exists():
            return ""

        creds = Credentials.from_service_account_file(
            str(creds_path),
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        service = build("drive", "v3", credentials=creds)

        results = service.files().list(
            q=f"fullText contains '{client_key}' and trashed = false",
            fields="files(id, name, mimeType, modifiedTime)",
            orderBy="modifiedTime desc",
            pageSize=10,
        ).execute()

        files = results.get("files", [])
        if not files:
            return ""

        file_lines = []
        for f in files:
            modified = f.get("modifiedTime", "?")[:10]
            file_lines.append(f"- [{f['name']}] ({f['mimeType']}) — modified {modified}")

        return (
            f"## RELATED DRIVE DOCUMENTS\n"
            + "\n".join(file_lines)
        )

    except Exception as e:
        logger.debug(f"Drive context failed for {client_key}: {e}")
        return ""


def _gather_learning_context(client_key: str) -> str:
    """Pull learned principles related to this client."""
    try:
        from thunderbird_learning import get_applicable_rules
        rules = get_applicable_rules(client_tier=None, domain=None)
        if not rules:
            return ""

        # Filter rules that mention this client
        client_rules = []
        for line in rules.split("\n"):
            if client_key.lower() in line.lower():
                client_rules.append(line)

        if not client_rules:
            return ""

        return (
            f"## LEARNED PREFERENCES (for {client_key})\n"
            + "\n".join(client_rules)
        )
    except Exception as e:
        logger.debug(f"Learning context failed for {client_key}: {e}")
        return ""


# ---------------------------------------------------------------------------
# C. Cache Management
# ---------------------------------------------------------------------------

def _get_cache_path(client_key: str) -> Path:
    """Get the cache file path for a client."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{client_key.lower()}_context.json"


def _is_cache_valid(client_key: str) -> bool:
    """Check if the cache is still fresh."""
    cache_path = _get_cache_path(client_key)
    if not cache_path.exists():
        return False

    try:
        cache_data = json.loads(cache_path.read_text())
        cached_at = datetime.fromisoformat(cache_data.get("cached_at", "2000-01-01"))
        return (datetime.now() - cached_at).total_seconds() < CACHE_TTL_HOURS * 3600
    except Exception:
        return False


def _write_cache(client_key: str, context: Dict[str, str]):
    """Write enriched context to cache."""
    cache_path = _get_cache_path(client_key)
    cache_data = {
        "client_key": client_key,
        "cached_at": datetime.now().isoformat(),
        "context": context,
    }
    cache_path.write_text(json.dumps(cache_data, indent=2))


def _read_cache(client_key: str) -> Optional[Dict[str, str]]:
    """Read cached context if valid."""
    if not _is_cache_valid(client_key):
        return None

    cache_path = _get_cache_path(client_key)
    try:
        cache_data = json.loads(cache_path.read_text())
        return cache_data.get("context", {})
    except Exception:
        return None


# ---------------------------------------------------------------------------
# D. Main Entry Point
# ---------------------------------------------------------------------------

def enrich_client_context(
    query_or_client: str,
    force_refresh: bool = False,
    include_gmail: bool = True,
    include_calendar: bool = True,
    include_drive: bool = True,
) -> str:
    """Auto-enrich a query with all available context about mentioned clients.

    This is the Layer 2 "Google Personal Intelligence" equivalent.
    Call this BEFORE any persona generates a response about a client.

    Args:
        query_or_client: Either a client name or a message mentioning clients
        force_refresh: Bypass cache and pull fresh data
        include_gmail: Pull recent email threads
        include_calendar: Pull upcoming calendar events
        include_drive: Pull related Drive documents

    Returns:
        Formatted context block ready for injection into persona prompt.
        Empty string if no clients detected or no context found.
    """
    # Detect client names in the query
    client_keys = detect_client_names(query_or_client)

    # If no clients detected via dossier matching, treat the whole query as a potential name
    if not client_keys:
        # Try using the first capitalized word as a client name
        words = re.findall(r"\b[A-Z][a-z]+\b", query_or_client)
        if words:
            client_keys = [words[0]]

    if not client_keys:
        return ""

    all_context_blocks = []

    for client_key in client_keys:
        # Check cache first
        if not force_refresh:
            cached = _read_cache(client_key)
            if cached:
                context_block = "\n\n".join(
                    v for v in cached.values() if v
                )
                if context_block:
                    all_context_blocks.append(
                        f"# AUTO-ENRICHED CONTEXT: {client_key} (cached)\n\n{context_block}"
                    )
                    continue

        # Gather from all sources
        context = {}

        # Always include dossier
        context["dossier"] = _gather_dossier_context(client_key)

        # Optional sources
        if include_gmail:
            context["gmail"] = _gather_gmail_context(client_key)

        if include_calendar:
            context["calendar"] = _gather_calendar_context(client_key)

        if include_drive:
            context["drive"] = _gather_drive_context(client_key)

        # Always include learning context
        context["learning"] = _gather_learning_context(client_key)

        # Cache the results
        _write_cache(client_key, context)

        # Build the context block
        context_block = "\n\n".join(v for v in context.values() if v)
        if context_block:
            all_context_blocks.append(
                f"# AUTO-ENRICHED CONTEXT: {client_key}\n\n{context_block}"
            )

    if not all_context_blocks:
        return ""

    result = "\n\n---\n\n".join(all_context_blocks)
    logger.info(
        f"Auto-enriched context for {len(client_keys)} client(s): "
        f"{', '.join(client_keys)} ({len(result)} chars)"
    )
    return result


def clear_client_cache(client_key: Optional[str] = None):
    """Clear the context cache for a specific client or all clients."""
    if client_key:
        cache_path = _get_cache_path(client_key)
        if cache_path.exists():
            cache_path.unlink()
            logger.info(f"Cleared cache for {client_key}")
    else:
        if CACHE_DIR.exists():
            for f in CACHE_DIR.glob("*_context.json"):
                f.unlink()
            logger.info("Cleared all client context caches")


# ---------------------------------------------------------------------------
# E. MCP Tool Registration
# ---------------------------------------------------------------------------

def register_auto_enrich_tools(mcp_server):
    """Register auto-enrichment tools with the MCP server."""

    @mcp_server.tool(
        name="auto_enrich_client",
        annotations={"title": "Auto-Enrich Client Context", "readOnlyHint": True},
    )
    async def auto_enrich_tool(
        query: str,
        force_refresh: bool = False,
    ) -> str:
        """Auto-enrich a query with all available context about mentioned clients.

        Pulls Gmail threads, Drive docs, Calendar events, dossiers, and learned
        preferences. Like Google Personal Intelligence for D2M.
        """
        context = enrich_client_context(query, force_refresh=force_refresh)
        if not context:
            return json.dumps({
                "status": "no_context",
                "message": "No client detected or no context found",
            })
        return json.dumps({
            "status": "enriched",
            "context_length": len(context),
            "context": context,
        })

    @mcp_server.tool(
        name="auto_enrich_clear_cache",
        annotations={"title": "Clear Client Context Cache"},
    )
    async def clear_cache_tool(
        client_key: str = "",
    ) -> str:
        """Clear the auto-enrichment cache for a client or all clients."""
        clear_client_cache(client_key or None)
        return json.dumps({"status": "cleared", "client": client_key or "all"})

    logger.info("Auto-enrichment tools registered (2 tools)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if len(sys.argv) < 2:
        print("Usage: python3 thunderbird_auto_enrich.py <client_name_or_query>")
        print("Example: python3 thunderbird_auto_enrich.py 'Furlow'")
        print("         python3 thunderbird_auto_enrich.py 'What cabin did the Lyons book?'")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    print(f"Auto-enriching context for: {query}\n")

    context = enrich_client_context(query)
    if context:
        print(context)
    else:
        print("No client context found.")
