#!/usr/bin/env python3
"""
Temporal Memory Evaluation Harness
===================================
Tests our SQLite temporal layer (learning_rules.db) with realistic D2M
travel concierge scenarios. Seeds test data, runs queries, measures gaps,
and documents what Zep/Graphiti would fill.

Run:  python3 scripts/eval_temporal_memory.py
"""

import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Setup — use a temp DB so we don't pollute the live one
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

# We import the schema but point at a test DB
from thunderbird_learning import _SCHEMA

EVAL_DB = Path(tempfile.mkdtemp()) / "eval_temporal.db"

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
GAP  = "\033[93mGAP\033[0m"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(EVAL_DB))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


# ---------------------------------------------------------------------------
# Seed realistic D2M test data
# ---------------------------------------------------------------------------

def seed_test_data(conn: sqlite3.Connection) -> None:
    """Seed the DB with temporal data spanning multiple time periods."""

    now = datetime.now(timezone.utc)

    # -----------------------------------------------------------------------
    # Scenario 1: Commander's sign-off evolution
    # "Best" → "Thanks" (switched around 2026-02-15)
    # -----------------------------------------------------------------------
    conn.execute(
        "INSERT INTO principles "
        "(persona_id, domain, client_tier, principle_text, confidence, "
        " validation_status, created_date, valid_from, valid_to, "
        " superseded_by, priority_tier) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "dani", "voice", "all",
            "Commander signs emails with 'Best' or 'Best regards'",
            0.9, "approved",
            "2025-06-01T00:00:00+00:00",
            "2025-06-01T00:00:00+00:00",
            "2026-02-15T00:00:00+00:00",  # superseded
            2,  # points to the new principle
            "inviolable",
        ),
    )
    conn.execute(
        "INSERT INTO principles "
        "(persona_id, domain, client_tier, principle_text, confidence, "
        " validation_status, created_date, valid_from, valid_to, "
        " superseded_by, priority_tier) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "dani", "voice", "all",
            "Commander signs emails with 'Thanks' or 'Thank you' — NEVER 'Best'",
            1.0, "approved",
            "2026-02-15T00:00:00+00:00",
            "2026-02-15T00:00:00+00:00",
            None,  # still active
            None,
            "inviolable",
        ),
    )

    # -----------------------------------------------------------------------
    # Scenario 2: Furlow hotel preference evolution
    # Preferred Hilton → tried Marriott → now prefers SLH boutique
    # -----------------------------------------------------------------------
    conn.execute(
        "INSERT INTO principles "
        "(persona_id, domain, client_tier, principle_text, confidence, "
        " validation_status, created_date, valid_from, valid_to, "
        " superseded_by, priority_tier) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "dani", "booking", "friend_service",
            "Furlows prefer Hilton properties — loyalty member, points-focused",
            0.85, "approved",
            "2025-08-01T00:00:00+00:00",
            "2025-08-01T00:00:00+00:00",
            "2025-12-01T00:00:00+00:00",
            4,
            "strong",
        ),
    )
    conn.execute(
        "INSERT INTO principles "
        "(persona_id, domain, client_tier, principle_text, confidence, "
        " validation_status, created_date, valid_from, valid_to, "
        " superseded_by, priority_tier) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "dani", "booking", "friend_service",
            "Furlows tried Marriott for Scandinavia trip — mixed reaction",
            0.7, "approved",
            "2025-12-01T00:00:00+00:00",
            "2025-12-01T00:00:00+00:00",
            "2026-02-01T00:00:00+00:00",
            5,
            "strong",
        ),
    )
    conn.execute(
        "INSERT INTO principles "
        "(persona_id, domain, client_tier, principle_text, confidence, "
        " validation_status, created_date, valid_from, valid_to, "
        " superseded_by, priority_tier) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "dani", "booking", "friend_service",
            "Furlows now prefer SLH boutique hotels — want unique, not chain",
            0.95, "approved",
            "2026-02-01T00:00:00+00:00",
            "2026-02-01T00:00:00+00:00",
            None,
            None,
            "strong",
        ),
    )

    # -----------------------------------------------------------------------
    # Scenario 3: Lyons cabin preference evolution
    # Balcony → Veranda Suite → now wants Penthouse
    # -----------------------------------------------------------------------
    conn.execute(
        "INSERT INTO principles "
        "(persona_id, domain, client_tier, principle_text, confidence, "
        " validation_status, created_date, valid_from, valid_to, "
        " superseded_by, priority_tier) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "dani", "booking", "friend_service",
            "Lyons prefer balcony cabins on cruise ships — price-conscious",
            0.8, "approved",
            "2025-06-15T00:00:00+00:00",
            "2025-06-15T00:00:00+00:00",
            "2025-10-01T00:00:00+00:00",
            7,
            "contextual",
        ),
    )
    conn.execute(
        "INSERT INTO principles "
        "(persona_id, domain, client_tier, principle_text, confidence, "
        " validation_status, created_date, valid_from, valid_to, "
        " superseded_by, priority_tier) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "dani", "booking", "friend_service",
            "Lyons upgraded to Veranda Suite on RSSC — loved the space, butler service",
            0.9, "approved",
            "2025-10-01T00:00:00+00:00",
            "2025-10-01T00:00:00+00:00",
            "2026-03-01T00:00:00+00:00",
            8,
            "strong",
        ),
    )
    conn.execute(
        "INSERT INTO principles "
        "(persona_id, domain, client_tier, principle_text, confidence, "
        " validation_status, created_date, valid_from, valid_to, "
        " superseded_by, priority_tier) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "dani", "booking", "friend_service",
            "Lyons now want Penthouse Suite minimum on all future cruises — "
            "Ken said 'we're done with anything smaller'",
            0.95, "approved",
            "2026-03-01T00:00:00+00:00",
            "2026-03-01T00:00:00+00:00",
            None,
            None,
            "strong",
        ),
    )

    # -----------------------------------------------------------------------
    # Scenario 4: Episodic memory — what worked/failed
    # -----------------------------------------------------------------------
    conn.execute(
        "INSERT INTO episodes "
        "(client_key, context_type, what_worked, what_failed, outcome, "
        " persona_id, timestamp, valid_from, valid_to) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "furlow_missy_john", "excursion_rec",
            "Recommended private walking tour instead of group bus tour",
            "Initially suggested hop-on-hop-off — Commander corrected",
            "Furlows loved the private tour, tipped guide $100",
            "dani", "2025-11-15T10:00:00+00:00",
            "2025-11-15T10:00:00+00:00", None,
        ),
    )
    conn.execute(
        "INSERT INTO episodes "
        "(client_key, context_type, what_worked, what_failed, outcome, "
        " persona_id, timestamp, valid_from, valid_to) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "lyons_nancy_ken", "dining_suggestion",
            "Booked rooftop restaurant with Acropolis view for anniversary",
            None,
            "Nancy sent thank-you note — 'best dinner of the trip'",
            "dani", "2025-09-20T18:00:00+00:00",
            "2025-09-20T18:00:00+00:00", None,
        ),
    )
    conn.execute(
        "INSERT INTO episodes "
        "(client_key, context_type, what_worked, what_failed, outcome, "
        " persona_id, timestamp, valid_from, valid_to) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "furlow_missy_john", "booking_query",
            "Proactively checked Finnair seat assignments before client asked",
            "Missed that PNR had unassigned outbound seats for 2 weeks",
            "Commander caught it — standing order now: check PNR within 48h",
            "dani", "2026-03-10T14:00:00+00:00",
            "2026-03-10T14:00:00+00:00", None,
        ),
    )

    # -----------------------------------------------------------------------
    # Scenario 5: Cross-entity relationship — Commander tone per client tier
    # -----------------------------------------------------------------------
    conn.execute(
        "INSERT INTO principles "
        "(persona_id, domain, client_tier, principle_text, confidence, "
        " validation_status, created_date, valid_from, valid_to, "
        " superseded_by, priority_tier) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "dani", "voice", "prospect",
            "For prospects: lead with connection and warmth, not price. "
            "Commander wants relationship-first approach before any numbers.",
            0.9, "approved",
            "2025-09-01T00:00:00+00:00",
            "2025-09-01T00:00:00+00:00",
            None, None,
            "strong",
        ),
    )
    conn.execute(
        "INSERT INTO principles "
        "(persona_id, domain, client_tier, principle_text, confidence, "
        " validation_status, created_date, valid_from, valid_to, "
        " superseded_by, priority_tier) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "dani", "voice", "friend_family",
            "For friends/family: casual, direct, can include personal cell. "
            "Skip the formal greeting — they know John.",
            0.95, "approved",
            "2025-09-01T00:00:00+00:00",
            "2025-09-01T00:00:00+00:00",
            None, None,
            "strong",
        ),
    )

    conn.commit()
    print(f"Seeded {conn.execute('SELECT COUNT(*) FROM principles').fetchone()[0]} principles")
    print(f"Seeded {conn.execute('SELECT COUNT(*) FROM episodes').fetchone()[0]} episodes")


# ---------------------------------------------------------------------------
# Test queries — what can our SQLite temporal layer answer?
# ---------------------------------------------------------------------------

class TestResult:
    def __init__(self, name: str, query: str, passed: bool,
                 result: Any = None, gap: str = ""):
        self.name = name
        self.query = query
        self.passed = passed
        self.result = result
        self.gap = gap


def test_point_in_time_query(conn: sqlite3.Connection) -> TestResult:
    """Q: What was Commander's sign-off before 2026-02-15?"""
    query = (
        "SELECT * FROM principles "
        "WHERE domain = 'voice' AND priority_tier = 'inviolable' "
        "AND principle_text LIKE '%sign%' "
        "AND valid_from <= '2026-01-01T00:00:00+00:00' "
        "AND (valid_to IS NULL OR valid_to > '2026-01-01T00:00:00+00:00') "
        "ORDER BY valid_from DESC LIMIT 1"
    )
    row = conn.execute(query).fetchone()
    if row and "Best" in row["principle_text"]:
        return TestResult(
            "Point-in-time: Commander sign-off before switch",
            query, True,
            result=row["principle_text"],
        )
    return TestResult(
        "Point-in-time: Commander sign-off before switch",
        query, False,
        gap="Could not resolve point-in-time query with text LIKE matching",
    )


def test_current_state_query(conn: sqlite3.Connection) -> TestResult:
    """Q: What is Commander's current sign-off?"""
    query = (
        "SELECT * FROM principles "
        "WHERE domain = 'voice' AND priority_tier = 'inviolable' "
        "AND principle_text LIKE '%sign%' "
        "AND (valid_to IS NULL OR valid_to > datetime('now')) "
        "ORDER BY valid_from DESC LIMIT 1"
    )
    row = conn.execute(query).fetchone()
    if row and "Thanks" in row["principle_text"]:
        return TestResult(
            "Current state: Commander sign-off now",
            query, True,
            result=row["principle_text"],
        )
    return TestResult(
        "Current state: Commander sign-off now",
        query, False,
        gap="Current-state query failed",
    )


def test_preference_evolution(conn: sqlite3.Connection) -> TestResult:
    """Q: Show how the Furlows' hotel preference evolved."""
    query = (
        "SELECT rule_id, principle_text, valid_from, valid_to, superseded_by "
        "FROM principles "
        "WHERE domain = 'booking' AND principle_text LIKE '%Furlow%' "
        "ORDER BY valid_from ASC"
    )
    rows = conn.execute(query).fetchall()
    if len(rows) == 3:
        chain = [dict(r) for r in rows]
        return TestResult(
            "Preference evolution: Furlow hotel history",
            query, True,
            result=chain,
        )
    return TestResult(
        "Preference evolution: Furlow hotel history",
        query, False,
        gap=f"Expected 3 evolution steps, got {len(rows)}",
    )


def test_lyons_cabin_evolution(conn: sqlite3.Connection) -> TestResult:
    """Q: Show how the Lyons' cabin preference evolved."""
    query = (
        "SELECT rule_id, principle_text, valid_from, valid_to, superseded_by, confidence "
        "FROM principles "
        "WHERE domain = 'booking' AND principle_text LIKE '%Lyons%' "
        "ORDER BY valid_from ASC"
    )
    rows = conn.execute(query).fetchall()
    if len(rows) == 3:
        # Verify the chain: balcony → veranda → penthouse
        texts = [r["principle_text"] for r in rows]
        if "balcony" in texts[0].lower() and "penthouse" in texts[2].lower():
            return TestResult(
                "Preference evolution: Lyons cabin history",
                query, True,
                result=[dict(r) for r in rows],
            )
    return TestResult(
        "Preference evolution: Lyons cabin history",
        query, False,
        gap=f"Expected 3-step cabin evolution (balcony→veranda→penthouse), got {len(rows)}",
    )


def test_supersession_chain(conn: sqlite3.Connection) -> TestResult:
    """Q: Can we follow the superseded_by chain for Furlow preferences?"""
    first = conn.execute(
        "SELECT * FROM principles "
        "WHERE principle_text LIKE '%Furlow%Hilton%'"
    ).fetchone()
    if not first:
        return TestResult(
            "Supersession chain traversal",
            "N/A", False,
            gap="Could not find root principle",
        )

    chain = [dict(first)]
    current = first
    while current["superseded_by"]:
        nxt = conn.execute(
            "SELECT * FROM principles WHERE rule_id = ?",
            (current["superseded_by"],),
        ).fetchone()
        if not nxt:
            break
        chain.append(dict(nxt))
        current = nxt

    if len(chain) == 3:
        return TestResult(
            "Supersession chain traversal",
            "Follow superseded_by links", True,
            result=[c["principle_text"][:60] for c in chain],
        )
    return TestResult(
        "Supersession chain traversal",
        "Follow superseded_by links", False,
        gap=f"Chain length {len(chain)}, expected 3",
    )


def test_episode_recall(conn: sqlite3.Connection) -> TestResult:
    """Q: What worked for the Furlows on excursions?"""
    query = (
        "SELECT * FROM episodes "
        "WHERE client_key = 'furlow_missy_john' "
        "AND context_type = 'excursion_rec' "
        "AND (valid_to IS NULL OR valid_to > datetime('now')) "
        "ORDER BY timestamp DESC"
    )
    rows = conn.execute(query).fetchall()
    if rows and "private walking" in rows[0]["what_worked"].lower():
        return TestResult(
            "Episode recall: Furlow excursion lessons",
            query, True,
            result=rows[0]["what_worked"],
        )
    return TestResult(
        "Episode recall: Furlow excursion lessons",
        query, False,
        gap="Could not retrieve episodic memory",
    )


def test_cross_entity_relationship(conn: sqlite3.Connection) -> TestResult:
    """Q: What voice rules apply to prospects vs friends/family?
    GAP: SQLite has no graph relationships — we fake it with client_tier tags.
    """
    prospect = conn.execute(
        "SELECT * FROM principles WHERE client_tier = 'prospect' AND domain = 'voice'"
    ).fetchone()
    friend = conn.execute(
        "SELECT * FROM principles WHERE client_tier = 'friend_family' AND domain = 'voice'"
    ).fetchone()

    if prospect and friend:
        return TestResult(
            "Cross-entity: voice rules by client tier",
            "client_tier tag lookup", True,
            result={
                "prospect": prospect["principle_text"][:80],
                "friend_family": friend["principle_text"][:80],
            },
            gap="PARTIAL — works via tags but no true entity→relationship→entity graph. "
                "Cannot traverse: Client→prefers→Hotel→located_in→City. "
                "Zep/Graphiti would model this as a real knowledge graph.",
        )
    return TestResult(
        "Cross-entity: voice rules by client tier",
        "client_tier tag lookup", False,
        gap="Tag-based lookup failed",
    )


def test_natural_language_query(conn: sqlite3.Connection) -> TestResult:
    """Q: 'What hotel did the Furlows prefer before their last trip?'
    GAP: SQLite cannot do semantic/NL search — requires exact LIKE patterns.
    """
    # We have to know the exact phrasing or use LIKE wildcards
    row = conn.execute(
        "SELECT * FROM principles "
        "WHERE principle_text LIKE '%Furlow%' "
        "AND valid_to IS NOT NULL "
        "ORDER BY valid_to DESC LIMIT 1"
    ).fetchone()

    if row:
        return TestResult(
            "Natural language query: 'What hotel before last trip?'",
            "LIKE pattern workaround", True,
            result=row["principle_text"],
            gap="MAJOR GAP — requires hardcoded LIKE patterns. Cannot handle: "
                "'What did the Furlows like about their Copenhagen hotel?' "
                "Zep does semantic search over the knowledge graph with embeddings.",
        )
    return TestResult(
        "Natural language query: 'What hotel before last trip?'",
        "LIKE pattern workaround", False,
        gap="LIKE pattern failed entirely",
    )


def test_preference_shift_detection(conn: sqlite3.Connection) -> TestResult:
    """Q: Detect when preferences shifted for Furlows.
    GAP: Must compute manually — no built-in shift detection.
    """
    rows = conn.execute(
        "SELECT rule_id, principle_text, valid_from, valid_to, confidence "
        "FROM principles "
        "WHERE principle_text LIKE '%Furlow%' AND domain = 'booking' "
        "ORDER BY valid_from ASC"
    ).fetchall()

    if len(rows) >= 2:
        shifts = []
        for i in range(1, len(rows)):
            prev = rows[i - 1]
            curr = rows[i]
            shifts.append({
                "from": prev["principle_text"][:50],
                "to": curr["principle_text"][:50],
                "shift_date": curr["valid_from"],
                "confidence_delta": (curr["confidence"] or 0) - (prev["confidence"] or 0),
            })
        return TestResult(
            "Preference shift detection: Furlow hotels",
            "Manual computation from valid_from/valid_to", True,
            result=shifts,
            gap="PARTIAL — works but requires manual code. No automatic drift detection. "
                "Zep/Graphiti tracks edge invalidation natively and can surface "
                "'this fact was contradicted by newer information' automatically.",
        )
    return TestResult(
        "Preference shift detection: Furlow hotels",
        "N/A", False,
        gap="Insufficient data for shift detection",
    )


# ---------------------------------------------------------------------------
# Run all tests and report
# ---------------------------------------------------------------------------

def run_evaluation() -> None:
    print("=" * 72)
    print("TEMPORAL MEMORY EVALUATION HARNESS")
    print("D2M Travel — SQLite Layer vs Zep/Graphiti Assessment")
    print("=" * 72)
    print(f"\nEval DB: {EVAL_DB}")
    print()

    conn = get_db()
    seed_test_data(conn)
    print()

    tests = [
        test_point_in_time_query,
        test_current_state_query,
        test_preference_evolution,
        test_lyons_cabin_evolution,
        test_supersession_chain,
        test_episode_recall,
        test_cross_entity_relationship,
        test_natural_language_query,
        test_preference_shift_detection,
    ]

    results: List[TestResult] = []
    for test_fn in tests:
        try:
            result = test_fn(conn)
        except Exception as e:
            result = TestResult(test_fn.__doc__ or test_fn.__name__, "N/A", False, gap=str(e))
        results.append(result)

        status = PASS if result.passed else FAIL
        print(f"  [{status}] {result.name}")
        if result.result and result.passed:
            if isinstance(result.result, list):
                for item in result.result[:3]:
                    if isinstance(item, dict):
                        txt = item.get("principle_text", item.get("from", str(item)))
                        print(f"         -> {str(txt)[:70]}")
                    else:
                        print(f"         -> {str(item)[:70]}")
            elif isinstance(result.result, dict):
                for k, v in result.result.items():
                    print(f"         {k}: {str(v)[:60]}")
            else:
                print(f"         -> {str(result.result)[:70]}")
        if result.gap:
            print(f"         {GAP}: {result.gap}")
        print()

    conn.close()

    # Summary
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    gaps_with_text = [r for r in results if r.gap]

    print("=" * 72)
    print(f"RESULTS: {passed}/{total} queries answered by SQLite temporal layer")
    print("=" * 72)

    print("\n--- GAPS THAT ZEP/GRAPHITI WOULD FILL ---\n")

    gap_analysis = [
        {
            "gap": "Semantic / Natural Language Search",
            "sqlite": "LIKE '%keyword%' patterns only — brittle, no synonyms, no context",
            "zep": "Hybrid search: cosine similarity on embeddings + BM25 text retrieval. "
                   "Can answer 'what did they like about Copenhagen?' without exact keywords.",
        },
        {
            "gap": "Entity-Relationship Graph",
            "sqlite": "Flat tables with tags (client_tier, domain). No entity→relationship→entity.",
            "zep": "True knowledge graph: Client→prefers→Hotel→located_in→City. "
                   "Traverse: 'find all clients who liked hotels in Scandinavia.' "
                   "Entity deduplication via 3-tier strategy (exact→fuzzy→LLM).",
        },
        {
            "gap": "Automatic Temporal Edge Invalidation",
            "sqlite": "Manual supersede_principle() with explicit valid_to. Developer must code it.",
            "zep": "Graphiti automatically detects contradictions and invalidates old edges. "
                   "4 temporal dimensions per edge: created_at, expired_at, valid_at, invalid_at.",
        },
        {
            "gap": "Preference Drift Detection",
            "sqlite": "Must write custom SQL to compare confidence/valid_from across rows.",
            "zep": "Built-in temporal reasoning — 'this fact was contradicted by newer info' "
                   "surfaced automatically during search.",
        },
        {
            "gap": "Cross-Session Context Persistence",
            "sqlite": "Episodes table with simple text fields. No embedding-based retrieval.",
            "zep": "Episodes are first-class objects. Each episode is LLM-analyzed to extract "
                   "entities and relationships, auto-deduplicated against existing graph.",
        },
        {
            "gap": "MCP Integration",
            "sqlite": "Custom MCP tools wrapping raw SQL (our current approach).",
            "zep": "Official Graphiti MCP Server with add_episode, search_facts, search_nodes, "
                   "get_episodes. Stdio + HTTP transports. Drop-in for Claude Desktop.",
        },
    ]

    for g in gap_analysis:
        print(f"  [{GAP}] {g['gap']}")
        print(f"    SQLite: {g['sqlite']}")
        print(f"    Zep:    {g['zep']}")
        print()

    print("--- RECOMMENDATION ---\n")
    print("  Our SQLite temporal layer handles basic point-in-time queries,")
    print("  supersession chains, and tag-based filtering. It's a solid Phase 1.")
    print()
    print("  Zep Cloud ($25/mo Flex) or self-hosted Graphiti adds:")
    print("    1. Semantic search over the knowledge graph (no more LIKE patterns)")
    print("    2. True entity-relationship graph (Client→Hotel→City traversal)")
    print("    3. Automatic contradiction detection and edge invalidation")
    print("    4. MCP server for Claude Desktop / Claude Code integration")
    print("    5. LLM-powered entity extraction and deduplication")
    print()
    print("  Phase 2 path: Install thunderbird_temporal_memory.py (built),")
    print("  sign up at getzep.com (free tier, no CC), get API key,")
    print("  flip backend='zep' in the abstract interface.")
    print()

    # Cleanup
    os.unlink(EVAL_DB)
    os.rmdir(EVAL_DB.parent)


if __name__ == "__main__":
    run_evaluation()
