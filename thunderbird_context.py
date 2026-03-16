"""
Thunderbird Context Engine
==========================

Gathers real operational data for persona injection.
Two context tiers:
  - Compact tier: compact context (~5500 chars) for models with smaller context limits
  - Claude tier: full context (up to 200K chars) leveraging Claude's 1M context window (GA)

Two modes:
  - Commander mode: bookings + relevant client dossier excerpt
  - Client mode: scoped to one client only
"""

import logging
import os
import time
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger("thunderbird_context")

_context_cache: dict = {}
_cache_ttl = 300  # 5 minutes


def _cache_valid(key: str) -> bool:
    entry = _context_cache.get(key)
    return bool(entry and (time.time() - entry["ts"]) < _cache_ttl)


def _cache_get(key: str) -> str:
    return _context_cache[key]["data"]


def _cache_set(key: str, data: str):
    _context_cache[key] = {"data": data, "ts": time.time()}


# ---------------------------------------------------------------------------
# Client name detection
# ---------------------------------------------------------------------------

CLIENT_NAMES = [
    "mcleod", "mcglasson", "furlow", "ely", "darrow", "nichols",
    "kuklinski", "morton", "dodge", "loucks", "westbrook",
    "beesley", "black", "boyce", "burcham", "gaughan", "looper",
    "piontek", "sciacca", "stoycos",
]


def _detect_clients_in_query(query: str) -> list[str]:
    query_lower = query.lower()
    return [name for name in CLIENT_NAMES if name in query_lower]


# ---------------------------------------------------------------------------
# Data loaders — COMPACT format
# ---------------------------------------------------------------------------

def _load_bookings_compact() -> str:
    """One-line-per-booking summary. Minimal."""
    try:
        from thunderbird_anchor_dates import KNOWN_BOOKINGS
    except ImportError:
        return ""

    today = date.today()
    lines = ["BOOKINGS:"]
    for key, bk in KNOWN_BOOKINGS.items():
        days = (bk["embark_date"] - today).days
        fpd_days = (bk["fpd"] - today).days
        fpd_flag = f" FPD-{fpd_days}d!" if bk.get("fpd_status") == "PENDING" and fpd_days <= 30 else ""
        lines.append(
            f"  {bk['client']} | {bk['supplier']} {bk['ship']} {bk['conf']} | "
            f"{bk['embark_date'].strftime('%b %d')}–{bk['disembark_date'].strftime('%b %d, %Y')} "
            f"T-{days}d | FPD:{bk['fpd'].strftime('%b %d')}({bk.get('fpd_status','?')}){fpd_flag}"
        )
    return "\n".join(lines)


def _load_anchor_compact() -> str:
    """Just overdue + due this week. No full timeline."""
    try:
        from thunderbird_anchor_dates import compute_all_known_anchors, scan_all_bookings_due
        all_anchors = compute_all_known_anchors()
        report = scan_all_bookings_due(all_anchors)
    except Exception:
        return ""

    lines = []
    if report.get("overdue"):
        lines.append("OVERDUE:")
        for a in report["overdue"][:5]:
            lines.append(f"  {a['label']} — {a['booking']}")
    if report.get("due_today"):
        lines.append("DUE TODAY:")
        for a in report["due_today"][:5]:
            lines.append(f"  {a['label']} — {a['booking']}")
    if report.get("due_this_week"):
        lines.append("THIS WEEK:")
        for a in report["due_this_week"][:5]:
            lines.append(f"  {a['date']}: {a['label']} — {a['booking']}")
    return "\n".join(lines)


def _load_client_dossier_excerpt(client_names: list[str], max_chars: int = 3000,
                                  full_context: bool = False) -> str:
    """Load client-specific sections from relevant dossiers.

    Args:
        max_chars: Character limit for compact-tier context (default 3000).
        full_context: If True (Claude tier), load full dossier content up to 50K chars.
    """
    if full_context:
        max_chars = 50_000  # Claude 1M context can handle full dossiers
    if not client_names:
        return ""

    dossier_dir = Path(os.path.expanduser("~/Thunderbird/dossiers"))
    if not dossier_dir.exists():
        return ""

    excerpts = []
    total = 0

    for f in sorted(dossier_dir.glob("DOSSIER_*.md")):
        if f.name == "DOSSIER_Regent_Tips_Guide.md":
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            content_lower = content.lower()

            if not any(name in content_lower for name in client_names):
                continue

            # Extract trip header (first 12 lines)
            all_lines = content.split("\n")
            header = "\n".join(all_lines[:12])

            # Extract client-specific sections
            for name in client_names:
                in_section = False
                section_lines = []
                for line in all_lines:
                    if name in line.lower():
                        in_section = True
                    elif in_section and line.startswith("═" * 5) and len(section_lines) > 3:
                        break
                    if in_section:
                        section_lines.append(line)

                if section_lines:
                    excerpt = header + "\n\n" + "\n".join(section_lines)
                    if total + len(excerpt) > max_chars:
                        excerpt = excerpt[:max_chars - total] + "\n[truncated]"
                    excerpts.append(excerpt)
                    total += len(excerpt)
                    if total >= max_chars:
                        break

        except Exception:
            continue

        if total >= max_chars:
            break

    if excerpts:
        return "DOSSIER DATA:\n" + "\n---\n".join(excerpts)
    return ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _load_client_profile_compact(client_names: list[str], max_chars: int = 1500,
                                  full_context: bool = False) -> str:
    """Pull client profile data from the Clients tab in Google Sheets.

    Uses the Dani engine's _fetch_client_profile for the actual data fetch.
    Compact tier: truncates for compact context.
    Claude tier: returns full profile data (up to 20K chars).
    """
    if full_context:
        max_chars = 20_000  # Claude 1M context — no need to truncate profiles
    if not client_names:
        return ""
    try:
        from thunderbird_dani_engine import _fetch_client_profile
        profiles = []
        total = 0
        for name in client_names:
            profile = _fetch_client_profile(name)
            if profile:
                if total + len(profile) > max_chars:
                    profile = profile[:max_chars - total] + "\n[truncated]"
                profiles.append(profile)
                total += len(profile)
                if total >= max_chars:
                    break
        return "\n".join(profiles)
    except Exception as e:
        logger.debug(f"Client profile load failed: {e}")
        return ""


def get_active_client_travel_profile() -> dict:
    """Return structured travel profiles for all active clients.

    Returns dict per client: {airports, airlines, ports, cruise_lines, destinations, dates}.
    Built from dossiers + KNOWN_BOOKINGS.

    Used by the Intel Crew for client-aware filtering.
    """
    import re as _re
    profiles = {}

    # Load from KNOWN_BOOKINGS
    try:
        from thunderbird_anchor_dates import KNOWN_BOOKINGS
        for key, bk in KNOWN_BOOKINGS.items():
            client = bk.get("client", key)
            if client not in profiles:
                profiles[client] = {
                    "airports": [],
                    "airlines": [],
                    "ports": [],
                    "cruise_lines": [],
                    "destinations": [],
                    "dates": [],
                }
            supplier = bk.get("supplier", "")
            if supplier and supplier not in profiles[client]["cruise_lines"]:
                profiles[client]["cruise_lines"].append(supplier)
            profiles[client]["dates"].append({
                "embark": str(bk.get("embark_date", "")),
                "disembark": str(bk.get("disembark_date", "")),
            })
    except Exception as e:
        logger.debug(f"KNOWN_BOOKINGS load failed: {e}")

    # Enrich from dossiers
    dossier_dir = Path(os.path.expanduser("~/Thunderbird/dossiers"))
    if dossier_dir.exists():
        for f in sorted(dossier_dir.glob("DOSSIER_*.md")):
            if f.name == "DOSSIER_Regent_Tips_Guide.md":
                continue
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                content_lower = content.lower()

                for client in list(profiles.keys()):
                    if client.lower().split()[0] in content_lower:
                        codes = _re.findall(r'\b([A-Z]{3})\b', content)
                        known_airports = {
                            "DCA", "IAD", "DEN", "COS", "SEA", "OMA", "HNL",
                            "ORD", "LAX", "JFK", "SFO", "MIA", "ATL", "DFW",
                        }
                        for code in codes:
                            if code in known_airports and code not in profiles[client]["airports"]:
                                profiles[client]["airports"].append(code)
            except Exception:
                continue

    # Hardcoded enrichment for known clients
    hardcoded = {
        "Justin Loucks": {"airports": ["DCA", "IAD", "COS", "DEN"], "airlines": ["Southwest", "SWA"]},
        "Ryan Loucks": {"airports": ["OMA", "COS", "DEN"]},
        "Westbrook": {"airports": ["HNL", "COS", "DEN", "SEA"], "airlines": ["Southwest", "SWA"]},
        "Lyons": {"ports": ["Athens", "Piraeus"], "cruise_lines": ["Regent", "RSSC"]},
    }
    for client, data in hardcoded.items():
        if client not in profiles:
            profiles[client] = {"airports": [], "airlines": [], "ports": [], "cruise_lines": [], "destinations": [], "dates": []}
        for key, values in data.items():
            for v in values:
                if v not in profiles[client].get(key, []):
                    profiles[client].setdefault(key, []).append(v)

    return profiles


def gather_commander_context(query: str = "", full_context: bool = False) -> str:
    """Operational context for persona calls.

    Args:
        query: User query — client names are auto-detected.
        full_context: If True, use Claude-tier limits (full dossiers, no truncation).
                      If False, use compact-tier limits (~5500 chars total).

    Detects client names in query → loads their dossier excerpt + client profile.
    Always includes compact booking list + anchor alerts.
    """
    mentioned = _detect_clients_in_query(query) if query else []
    tier = "full" if full_context else "compact"
    cache_key = f"cmd_{tier}_{'_'.join(sorted(mentioned)) or 'gen'}"

    if _cache_valid(cache_key):
        return _cache_get(cache_key)

    parts = [
        f"[D2M OPS {datetime.now().strftime('%Y-%m-%d %H:%M')}]",
        _load_bookings_compact(),
        _load_anchor_compact(),
        _load_client_dossier_excerpt(mentioned, full_context=full_context),
        _load_client_profile_compact(mentioned, full_context=full_context),
        "RULES: Use ONLY this data. If info is missing, say so — do NOT fabricate.",
    ]

    context = "\n\n".join(p for p in parts if p)
    _cache_set(cache_key, context)
    return context


def gather_client_context(client_name: str, full_context: bool = False) -> str:
    """Client-scoped context for client-facing Dani.

    Args:
        full_context: If True, use Claude-tier limits (full dossier, full profile).
    """
    tier = "full" if full_context else "compact"
    cache_key = f"client_{tier}_{client_name.lower()}"
    if _cache_valid(cache_key):
        return _cache_get(cache_key)

    dossier_chars = 50_000 if full_context else 4000
    profile_chars = 20_000 if full_context else 1500

    parts = [
        f"[Client: {client_name} | {datetime.now().strftime('%Y-%m-%d')}]",
        _load_client_dossier_excerpt([client_name.lower()], max_chars=dossier_chars,
                                      full_context=full_context),
        _load_client_profile_compact([client_name.lower()], max_chars=profile_chars,
                                      full_context=full_context),
        "RULES: Answer from this data only. No other client info. If missing, say so warmly.",
    ]

    context = "\n\n".join(p for p in parts if p)
    _cache_set(cache_key, context)
    return context


def invalidate_cache():
    _context_cache.clear()
