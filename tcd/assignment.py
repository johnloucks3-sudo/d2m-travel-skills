"""
assignment — deterministic staff-seat routing for D -> T auto-tasking.

The Commander's own model: "I change the P to a D and ... approve (moves to
HALE for tasking) ... Then HALE takes over." The instant an item is Approved,
Hale should hand it to the right staff seat rather than let it sit at D.
Routing is deterministic keyword matching against the item's own fields —
same spirit as OpsCenter/keyword_router.py's model-tier routing, but for a
STAFF_ROOM seat (CLAUDE.md's Hale/Dani/Sterling/Dembe/Harlan), not an LLM.
"""

import re

DEFAULT_OWNER = "Hale"

# Order matters: first matching rule wins. Checked as WHOLE WORDS (not raw
# substrings) against a lowercased blob of the item's own fields — a plain
# `in` check would let "mission" false-match inside "commission" and
# misroute a finance item to Sterling (caught by a real test failure).
_RULES = (
    ("Sterling", ("tech", "ci", "code", "mission", "infra", "metric",
                  "regression", "watchdog", "timer", "deploy")),
    ("Harlan", ("finance", "commission", "budget", "roi", "invoice",
                "payment", "fpd", "cost")),
    ("Dembe", ("research", "intel", "cruise", "destination", "market",
               "itinerary", "excursion", "port")),
    ("Dani", ("client", "gmail", "booking", "email", "guest")),
)


def assign_owner(item: dict) -> str:
    """Best-fit staff seat for a just-Approved item.

    Falls back to Hale (default COS ownership) when nothing matches — an
    item is never left unassigned once it's tasked.
    """
    haystack = " ".join(str(item.get(k, "")) for k in
                        ("title", "type", "inbox", "sourcePath", "snippet", "body")).lower()
    if "$" in haystack:
        return "Harlan"
    for owner, keywords in _RULES:
        if any(re.search(rf"\b{re.escape(kw)}\b", haystack) for kw in keywords):
            return owner
    return DEFAULT_OWNER
