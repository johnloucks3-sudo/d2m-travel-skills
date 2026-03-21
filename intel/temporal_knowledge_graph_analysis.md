# A2 INTEL REPORT: Temporal Knowledge Graphs for Thunderbird OS Memory Architecture
## Staff Paper from Lt Col Marcus "Wraith" Dembe, A2 (Research & Market Intelligence)
## Dreams2Memories Travel, LLC
### Classification: INTERNAL -- Commander Direct Request
### Date: 2026-03-20
### Priority: CRITICAL -- HIGHEST LEVERAGE UPGRADE (Commander designation)
### Ref: LAYER 3 of Preference Learning Architecture (see also: A2_INTEL_Preference_Learning_LLM_Agents.md)

---

## ISSUE

Commander requires an architecture decision for adding temporal dimension to Thunderbird OS memory -- the ability to answer not just "what does this client prefer?" but "when did that preference change?" and "what was the state of this relationship on date X?" Current systems (thunderbird_learning.py / SQLite corrections+principles, thunderbird_voice_ledger.py / JSON per-tier rules) are flat: they store facts but not their evolution over time. This report evaluates four candidates and recommends a migration path.

---

## DISCUSSION

### 0. CURRENT STATE ASSESSMENT

**What we have (high confidence -- code reviewed):**

| Component | Storage | Temporal Awareness | Gaps |
|-----------|---------|-------------------|------|
| `thunderbird_learning.py` | SQLite `learning_rules.db` | `timestamp` on corrections, `created_date` on principles | No `superseded_date`. No "this principle replaced that one." No point-in-time queries. |
| `thunderbird_voice_ledger.py` | JSON `voice_ledger.json` | `created` field per rule | No versioning. Edits overwrite. No history of rule changes. Cannot answer "what was our tone with Furlows before the Scandinavia booking?" |

**The temporal questions we cannot answer today:**
1. "What hotel did the Furlows prefer before their last trip?"
2. "When did Commander switch from formal to informal tone with the Lyons?"
3. "Show me how our pricing approach with prospects evolved over Q1 2026."
4. "What did we know about Westbrook's travel preferences as of March 1?"
5. "Which principles have been superseded, and what replaced them?"

These are not hypothetical. These are the kinds of questions a luxury travel concierge with 50+ clients will face daily. The temporal dimension is what separates a filing cabinet from institutional memory.

---

### 1. ZEP / GRAPHITI -- Temporal Knowledge Graph Engine

**Source:** [ArXiv paper (Jan 2025)](https://arxiv.org/abs/2501.13956) | [GitHub: getzep/graphiti](https://github.com/getzep/graphiti) | [Zep Platform](https://www.getzep.com/)

**Architecture (high confidence):**

Graphiti is the open-source engine; Zep is the commercial managed platform built on top of it.

Three-tier subgraph hierarchy:
- **Episode Subgraph** -- Raw ingestion events (conversations, emails, JSON data). Each episode is a node; entities mentioned in it are linked via `MENTIONS` edges. This is provenance.
- **Semantic Entity Subgraph** -- Extracted entities (clients, hotels, preferences) with typed relationships. Each relationship edge carries `valid_at` and `invalid_at` timestamps. This is the temporal layer.
- **Community Subgraph** -- Hierarchical clustering of related entities for efficient retrieval. Think "the Furlow cluster" = their preferences, trips, dining history, communication patterns.

**Bi-temporal data model:**
- `valid_at` -- when the fact became true in the real world
- `invalid_at` -- when the fact was superseded (null = still current)
- `created_at` -- when the system ingested the fact
- These are on EDGES, not nodes. The entity "Furlows" persists; the edge "Furlows --prefers--> formal_tone" gets an `invalid_at` when superseded by "Furlows --prefers--> warm_informal_tone"

**Python SDK (verified via PyPI: `graphiti-core`):**

```python
from datetime import datetime
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

# Initialize with Neo4j or FalkorDB backend
graphiti = Graphiti(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password"
)
await graphiti.build_indices_and_constraints()

# Ingest a client interaction as an episode
await graphiti.add_episode(
    name="Furlow_booking_update_20260315",
    episode_body=(
        "Missy Furlow confirmed she prefers balcony cabins over suites "
        "for Scandinavia itineraries. Previously requested suites for "
        "Mediterranean trips. Final payment of $15,486 due April 1."
    ),
    episode_type=EpisodeType.text,
    reference_time=datetime(2026, 3, 15),
    source_description="Commander notes from booking call",
    group_id="client_furlow"  # Multi-tenant namespace
)

# Temporal query: what did we know on March 1?
results = await graphiti.search(
    query="Furlow cabin preferences",
    num_results=5,
    # Graphiti's temporal search filters by valid_at/invalid_at
)

# Each result includes temporal metadata:
# edge.valid_at = datetime(2026, 3, 15)
# edge.invalid_at = None  (still current)
# edge.fact = "Missy Furlow prefers balcony cabins for Scandinavia"
```

**The `group_id` parameter is critical for us.** It enables multi-tenant isolation -- each client, each persona, each domain can be its own namespace. Map: `group_id="client_furlow"`, `group_id="persona_A3"`, `group_id="voice_rules"`.

**Self-hosted requirements (high confidence):**
- Python 3.10+
- Graph database: Neo4j 5.26+ OR FalkorDB (Redis-compatible, lighter) OR Kuzu (embedded, zero-config)
- LLM for entity extraction: OpenAI (default), Anthropic, or Groq
- `pip install graphiti-core` (Apache 2.0 license)
- FalkorDB variant: `pip install graphiti-core[falkordb]`

**Zep Cloud pricing:**
- Free: 1,000 credits/month (1 credit = 1 episode)
- Flex: $25/month for 20,000 credits
- Enterprise: custom
- **Self-hosted Zep Community Edition: DEPRECATED.** Self-hosting means using Graphiti directly.

**Benchmark performance (high confidence):**
- LongMemEval: 63.8% accuracy (vs Mem0 at 49.0%, using GPT-4o)
- DMR benchmark: 94.8% (vs MemGPT at 93.4%)
- 18.5% accuracy improvement over baseline, 90% latency reduction

**MCP Server (verified):**
Graphiti ships an [MCP server](https://github.com/getzep/graphiti/blob/main/mcp_server/README.md) that exposes: `add_episode`, `search_nodes`, `search_facts`, `delete_entity_edge`, `delete_episode`. This could plug directly into our existing MCP infrastructure on YOGA.

**Assessment:** This is the most architecturally sophisticated option. The bi-temporal model on edges is exactly what we need. The MCP server is a natural fit. The concern is operational complexity -- running Neo4j or FalkorDB alongside our existing SQLite is a new dependency.

---

### 2. MEM0 -- Dual-Store Memory Layer

**Source:** [GitHub: mem0ai/mem0](https://github.com/mem0ai/mem0) (~48K stars) | [Documentation](https://docs.mem0.ai/) | [Research paper](https://mem0.ai/research)

**Architecture (high confidence):**

Mem0 combines three storage backends:
- **Vector store** -- semantic similarity search (Qdrant, Pinecone, ChromaDB, PGVector -- 22+ options)
- **Graph store** -- relationship modeling via Neo4j, Memgraph, Kuzu, or Neptune (optional layer)
- **Key-value store** -- fast fact retrieval

**Hierarchical memory scoping (directly relevant):**

```python
from mem0 import Memory

# Configuration for self-hosted with graph memory
config = {
    "llm": {
        "provider": "anthropic",
        "config": {
            "model": "claude-sonnet-4-20250514",
            "api_key": "...",
        }
    },
    "graph_store": {
        "provider": "neo4j",
        "config": {
            "url": "bolt://localhost:7687",
            "username": "neo4j",
            "password": "password"
        }
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "host": "localhost",
            "port": 6333
        }
    }
}

memory = Memory.from_config(config)

# Add memory scoped to persona + client
memory.add(
    "Commander prefers warm-informal tone with Furlow family. "
    "Sign-off is always 'Thanks, John' -- never 'Best.'",
    user_id="client_furlow",
    agent_id="A3_dani",  # Persona-scoped
    metadata={"domain": "voice", "tier": "paying"}
)

# Search with hierarchical scoping
results = memory.search(
    query="How should Dani address the Furlows?",
    user_id="client_furlow",
    agent_id="A3_dani"
)
```

**Persona mapping (high confidence this maps to our architecture):**

| Mem0 Concept | D2M Equivalent |
|-------------|---------------|
| `user_id` | Client name (Furlow, Lyons, Westbrook) |
| `agent_id` | Persona ID (A2, A3, COS, EXEC) |
| `run_id` | Session/conversation ID |

**Mem0g (graph-enhanced variant) performance:**
- 26% accuracy improvement over flat vector retrieval (Mem0 research paper)
- Temporal reasoning F1: 51.55 (highest among tested systems on temporal tasks)
- Sub-50ms retrieval latency

**Self-hosted setup:**
```bash
pip install "mem0ai[graph]"
pip install "psycopg[binary,pool]" rank-bm25 langchain-neo4j neo4j
# Docker for backing services
docker run -d -p 6333:6333 qdrant/qdrant
docker run -d -p 7687:7687 neo4j:5
```

**Temporal capabilities (moderate confidence -- this is the weak spot):**

Mem0 does NOT have Graphiti's bi-temporal edge model. It tracks:
- When a memory was created
- When a memory was last accessed
- Memory decay/importance scoring

But it does NOT natively track:
- "This fact was true from date X to date Y"
- "This fact superseded that fact"
- Point-in-time queries ("What did we know on March 1?")

The graph layer (Mem0g) adds entity-relationship tracking but without temporal validity windows. You can query "what entities are related to Furlow?" but not "what entities were related to Furlow as of January?"

**Pricing:**
- Open source: free (Apache 2.0)
- Managed platform: starts at $249/month (Pro), but the open-source version is fully functional
- $24M Series A raised October 2025

**Assessment:** Strongest developer ecosystem and easiest path to production. The `user_id`/`agent_id` hierarchy maps perfectly to our persona architecture. But the temporal gap is real -- and temporal is the entire point of this upgrade. Using Mem0 for temporal tracking would require custom extensions on top of the graph layer.

---

### 3. LANGMEM SDK -- Procedural Memory via Prompt Optimization

**Source:** [GitHub: langchain-ai/langmem](https://github.com/langchain-ai/langmem) | [Documentation](https://langchain-ai.github.io/langmem/) | [Launch blog](https://blog.langchain.com/langmem-sdk-launch/)

**Architecture (high confidence):**

Three memory types modeled on cognitive psychology:

| Type | What it stores | Our analog |
|------|---------------|-----------|
| **Semantic** | Key facts and relationships | `learning_rules.db` principles table |
| **Episodic** | Memories of past interactions | `learning_rules.db` corrections table |
| **Procedural** | How to perform tasks -- saved as updated instructions | `voice_ledger.json` rules + system prompt injection |

**The procedural memory concept is the most relevant to us.** It works like this:

```python
from langmem import create_prompt_optimizer

# Create an optimizer that refines instructions from feedback
optimizer = create_prompt_optimizer(
    "anthropic:claude-sonnet-4-20250514",
    kind="metaprompt",  # Uses reflection + meta-prompt
    config={"max_reflection_steps": 3}
)

# Feed it a trajectory (conversation + feedback)
trajectory = [
    {"role": "user", "content": "Draft email to Missy Furlow about final payment"},
    {"role": "assistant", "content": "Dear Mrs. Furlow, ..."},  # Generated
    {"role": "user", "content": "Too formal. We're past that with the Furlows. "
                                 "Start with 'Hey Missy' and keep it to 4 sentences."}
]

# Optimizer produces updated instructions
updated_prompt = optimizer.invoke(
    {"trajectories": [trajectory]},
    current_prompt="You are Dani, a luxury travel concierge..."
)
# Result: prompt now includes "For paying-tier clients like the Furlows,
# use informal greetings ('Hey [first name]') and limit to 4 sentences."
```

**Comparison to our principle injection:**

| Feature | LangMem | Thunderbird Learning Compiler |
|---------|---------|------------------------------|
| Diff capture | Not explicit -- uses trajectory feedback | `capture_email_diff()` -- explicit before/after |
| Principle extraction | `create_prompt_optimizer()` with metaprompt | `extract_principles()` via Claude CLI |
| Storage | Backend-agnostic (LangGraph store, vector DB, etc.) | SQLite `principles` table |
| Injection | Rewrites the entire system prompt | Appends `LEARNED PRINCIPLES` block |
| Temporal tracking | None | `created_date` only (no supersession) |

**Dependencies:**
- `pip install langmem` (MIT license, free)
- Requires: `langchain>=0.3.8`, `langchain-anthropic>=0.3`, `langgraph-sdk>=0.1.40`
- Python 3.10+

**Assessment:** LangMem's procedural memory is philosophically closest to what our learning compiler already does -- the "learned procedures saved as updated instructions" pattern is exactly our principle injection. But LangMem adds no temporal dimension. It also introduces the full LangChain dependency tree, which we have deliberately avoided. If we adopted LangMem, we'd get a more sophisticated prompt optimization loop but still no temporal tracking. This is a complementary tool, not a solution to the temporal problem.

---

### 4. NEO4J + TEMPORAL PROPERTIES (ROLL YOUR OWN)

**Source:** [Neo4j Cypher Manual -- Temporal Values](https://neo4j.com/docs/cypher-manual/current/values-and-types/temporal/) | [Neo4j NODES 2025](https://neo4j.com/nodes-2025/)

**Architecture (moderate confidence -- this is a design exercise, not a product):**

Neo4j has native temporal data types (Date, DateTime, Duration) and supports temporal properties on both nodes and relationships. You could build a Graphiti-like system from scratch:

```cypher
// Create a temporal fact
CREATE (c:Client {name: "Furlow"})-[r:PREFERS {
    fact: "balcony cabin for Scandinavia",
    valid_from: datetime("2026-03-15"),
    valid_to: null,
    source: "commander_notes",
    confidence: 0.95
}]->(p:Preference {type: "cabin_type", value: "balcony"})

// Point-in-time query: what did Furlows prefer on March 1?
MATCH (c:Client {name: "Furlow"})-[r:PREFERS]->(p:Preference)
WHERE r.valid_from <= datetime("2026-03-01")
  AND (r.valid_to IS NULL OR r.valid_to > datetime("2026-03-01"))
RETURN p.type, p.value, r.fact, r.valid_from
```

**But this is Graphiti without the automation.** You'd have to build:
1. Entity extraction from text (LLM calls)
2. Relationship deduplication and merging
3. Temporal supersession logic (when new fact invalidates old fact)
4. Community detection for efficient retrieval
5. Hybrid search (combining graph traversal with vector similarity)

Estimated build effort: 2,000-4,000 lines of Python, 3-6 weeks of focused development.

**Alternatively: Minimum Viable Temporal Layer on SQLite**

We do not need Neo4j to add temporal tracking. Here is what a lightweight temporal extension to our existing `learning_rules.db` would look like:

```sql
-- Add temporal columns to existing principles table
ALTER TABLE principles ADD COLUMN valid_from TEXT;
ALTER TABLE principles ADD COLUMN valid_to TEXT;
ALTER TABLE principles ADD COLUMN superseded_by INTEGER
    REFERENCES principles(rule_id);
ALTER TABLE principles ADD COLUMN supersession_reason TEXT;

-- Create a temporal view for "what's true now?"
CREATE VIEW current_principles AS
SELECT * FROM principles
WHERE validation_status = 'approved'
  AND (valid_to IS NULL OR valid_to > datetime('now'))
  AND valid_from <= datetime('now');

-- Create a temporal view for point-in-time queries
-- Usage: SELECT * FROM principles_at('2026-03-01')
-- (SQLite doesn't support parameterized views, so this would be a Python function)
```

```python
# Minimal temporal extension to thunderbird_learning.py
def get_principles_at(
    point_in_time: str,
    persona_id: Optional[str] = None,
    client_tier: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Fetch principles that were active at a specific point in time."""
    conn = _get_db()
    try:
        conditions = [
            "validation_status = 'approved'",
            "valid_from <= ?",
            "(valid_to IS NULL OR valid_to > ?)",
        ]
        params = [point_in_time, point_in_time]

        if persona_id:
            conditions.append("(persona_id = ? OR persona_id IS NULL)")
            params.append(persona_id)
        if client_tier:
            conditions.append("(client_tier = ? OR client_tier IS NULL)")
            params.append(client_tier)

        where = " AND ".join(conditions)
        rows = conn.execute(
            f"SELECT * FROM principles WHERE {where} "
            f"ORDER BY created_date DESC",
            params,
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def supersede_principle(
    old_rule_id: int,
    new_principle_text: str,
    reason: str,
    persona_id: Optional[str] = None,
    domain: str = "voice",
    client_tier: Optional[str] = None,
    confidence: float = 0.8,
) -> Dict[str, Any]:
    """Supersede an existing principle with a new one.

    Sets valid_to on the old principle and creates a new one
    with valid_from = now and a back-reference.
    """
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_db()
    try:
        # Close out the old principle
        conn.execute(
            "UPDATE principles SET valid_to = ? WHERE rule_id = ?",
            (now, old_rule_id),
        )

        # Create the new principle
        cur = conn.execute(
            "INSERT INTO principles "
            "(persona_id, domain, client_tier, principle_text, confidence, "
            " validation_status, created_date, valid_from) "
            "VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)",
            (persona_id, domain, client_tier, new_principle_text,
             confidence, now, now),
        )
        new_id = cur.lastrowid

        # Link old to new
        conn.execute(
            "UPDATE principles SET superseded_by = ?, "
            "supersession_reason = ? WHERE rule_id = ?",
            (new_id, reason, old_rule_id),
        )

        conn.commit()
        return {
            "old_rule_id": old_rule_id,
            "new_rule_id": new_id,
            "reason": reason,
            "valid_from": now,
        }
    finally:
        conn.close()


def get_principle_history(rule_id: int) -> List[Dict[str, Any]]:
    """Trace the full history of a principle -- what it replaced
    and what replaced it."""
    conn = _get_db()
    try:
        chain = []
        current_id = rule_id

        # Walk backward to find the original
        while current_id:
            row = conn.execute(
                "SELECT * FROM principles WHERE superseded_by = ?",
                (current_id,),
            ).fetchone()
            if row:
                chain.insert(0, dict(row))
                current_id = row["rule_id"]
            else:
                break

        # Now walk forward from the starting rule
        current_id = rule_id
        while current_id:
            row = conn.execute(
                "SELECT * FROM principles WHERE rule_id = ?",
                (current_id,),
            ).fetchone()
            if row:
                chain.append(dict(row))
                current_id = row["superseded_by"]
            else:
                break

        return chain
    finally:
        conn.close()
```

**Voice ledger temporal extension:**

```python
# Minimal temporal extension to thunderbird_voice_ledger.py
def _make_rule(
    domain: str,
    text: str,
    source: str = "commander_edit",
    example: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a rule entry with temporal fields."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "domain": domain if domain in VALID_DOMAINS else "phrasing",
        "text": text,
        "source": source,
        "example": example,
        "created": now,
        "valid_from": now,
        "valid_to": None,       # null = still active
        "superseded_by": None,  # index of replacement rule
        "supersession_reason": None,
        "applied_count": 0,
    }


def supersede_voice_rule(
    scope: str,
    index: int,
    new_text: str,
    reason: str,
    tier_or_client: Optional[str] = None,
    domain: Optional[str] = None,
) -> Dict[str, Any]:
    """Supersede a voice rule -- marks old as invalid,
    creates new with back-reference."""
    ledger = _load_ledger()
    now = datetime.now(timezone.utc).isoformat()

    # Locate the old rule
    if scope == "global":
        rules = ledger["global_rules"]
    elif scope == "tier" and tier_or_client:
        rules = ledger.get("tier_rules", {}).get(tier_or_client, [])
    elif scope == "client" and tier_or_client:
        rules = ledger.get("client_rules", {}).get(tier_or_client, [])
    else:
        return {"error": "Invalid scope"}

    if index >= len(rules):
        return {"error": f"Index {index} out of range"}

    old_rule = rules[index]
    old_rule["valid_to"] = now
    old_rule["superseded_by"] = len(rules)  # Index of new rule
    old_rule["supersession_reason"] = reason

    # Create new rule
    new_rule = _make_rule(
        domain=domain or old_rule["domain"],
        text=new_text,
        source="supersession",
        example=old_rule.get("example"),
    )
    rules.append(new_rule)

    _save_ledger(ledger)
    return {
        "old_index": index,
        "new_index": len(rules) - 1,
        "reason": reason,
    }
```

**Assessment:** The SQLite temporal extension is achievable in a single coding session -- maybe 200 lines of changes across both files. It gives us 80% of the temporal capability we need without any new infrastructure dependencies. It does NOT give us entity extraction, relationship graphs, or community detection. But for a single-user system with ~50 clients and ~7 personas, we may not need those yet.

---

### 5. COMPARATIVE MATRIX

| Dimension | Graphiti (Zep) | Mem0 | LangMem | SQLite Temporal | Our Current State |
|-----------|---------------|------|---------|----------------|-------------------|
| **Temporal edges (valid_from/to)** | Native, bi-temporal | No | No | Manual (our code) | No |
| **Point-in-time queries** | Native | No | No | Manual (our code) | No |
| **Supersession tracking** | Automatic | No | No | Manual (our code) | No |
| **Entity extraction** | Automatic (LLM-driven) | Automatic | No (external) | Manual | No |
| **Multi-persona scoping** | `group_id` | `agent_id` | LangGraph namespaces | Our existing schema | Persona filter on principles |
| **Multi-client isolation** | `group_id` | `user_id` | LangGraph namespaces | Our existing schema | `client_tier` only |
| **MCP server** | Yes (ships with it) | No | No | N/A (our MCP) | Yes (our MCP) |
| **Self-hosted** | Yes (Graphiti OSS) | Yes (Apache 2.0) | Yes (MIT) | Already hosted | Already hosted |
| **New infra required** | Neo4j/FalkorDB + vector DB | Vector DB + optional Neo4j | LangChain ecosystem | None | N/A |
| **Python package** | `graphiti-core` | `mem0ai` | `langmem` | stdlib `sqlite3` | stdlib `sqlite3` |
| **Monthly cost** | $0 self-hosted / $25 cloud | $0 self-hosted / $249 cloud | $0 | $0 | $0 |
| **LLM dependency** | Yes (entity extraction) | Yes (memory extraction) | Yes (prompt optimization) | Optional | Yes (principle extraction) |
| **Benchmark accuracy** | 63.8% (LongMemEval) | 49.0% (LongMemEval) | Insufficient data | N/A | N/A |
| **Community/ecosystem** | Growing (~8K GH stars) | Strong (~48K GH stars) | LangChain ecosystem | Universal | N/A |
| **Integration effort** | Medium (2-3 days) | Medium (2-3 days) | Low (1 day) | Low (4-8 hours) | Baseline |
| **Operational complexity** | High (graph DB ops) | Medium (vector + graph DB ops) | Low | None | Baseline |

---

### 6. ANSWERING THE COMMANDER'S FIVE QUESTIONS

**Q1: Can Zep handle "What hotel did the Furlows prefer before their last trip?"**

Yes. High confidence. This is precisely what the bi-temporal edge model is built for. The query would traverse the `PREFERS` edges for the Furlow entity node, filtering where `valid_to` is not null (superseded preferences) and ordering by `valid_to DESC`. The first result is the preference that was active just before the current one.

**Q2: Can Zep handle "When did Commander switch from formal to informal tone with this client?"**

Yes. High confidence. Tone rules would be ingested as episodes. Graphiti would extract entities (Commander, client, tone_style) and create edges with temporal bounds. A search for tone-related facts about a specific client, filtered to superseded edges, would show the transition point.

**Q3: How would Graphiti plug into our existing SQLite learning DB?**

Two viable approaches:

**Option A -- Supplement (recommended for Phase 1):** Keep SQLite as the source of truth for corrections and principles. Add the temporal columns to SQLite (the lightweight extension above). Feed approved principles into Graphiti as episodes for relationship/entity tracking. SQLite handles the fast operational path; Graphiti handles the deep temporal/relational queries.

**Option B -- Replace (Phase 2, if warranted):** Migrate all principle storage to Graphiti. SQLite retains only raw corrections as an append-only log. All retrieval, injection, and temporal queries go through Graphiti. This is cleaner but requires Graphiti to be production-stable.

**Q4: What's the minimum viable temporal layer?**

The SQLite extension in Section 4 above. Four new columns on `principles`, three new Python functions, comparable additions to the voice ledger. Achievable in one coding session. Gives us supersession chains, point-in-time queries, and principle history -- without any new dependencies.

**Q5: What's the migration path?**

Phase 1 (immediate): SQLite temporal extension. No new dependencies. Answers 80% of temporal questions.

Phase 2 (when client count exceeds ~30 active): Add Graphiti with FalkorDB for relationship graphs and entity extraction. Run alongside SQLite. Feed principles and voice rules into Graphiti as episodes.

Phase 3 (when the system is mature): Evaluate whether to consolidate on Graphiti or maintain the dual-store. Decision depends on operational stability and whether the relationship graph queries prove valuable in practice.

---

### 7. INFORMATION GAPS

1. **Graphiti production stability** -- Insufficient data. The project is 14 months old. The paper was January 2025. I found one bug report about `add_episode` throwing JSON parse errors (GitHub issue #871). Not enough production deployment reports to assess reliability at scale. **Confidence: low-moderate.**

2. **FalkorDB vs Neo4j for our scale** -- Insufficient data on FalkorDB for small-scale deployments. FalkorDB is Redis-compatible and lighter, but the Graphiti Docker image currently only supports Neo4j (GitHub issue #749). Kuzu (embedded, zero-config) is the most interesting option for us but is the least tested. **Confidence: low.**

3. **LLM cost of entity extraction** -- Each `add_episode` call in Graphiti triggers LLM inference for entity extraction. At ~$0.003/call on Sonnet, and assuming ~50 episodes/day (emails, corrections, notes), that's ~$4.50/month. Tolerable, but it adds up. With our Max plan, this would be covered. **Confidence: moderate.**

4. **Mem0 temporal roadmap** -- Mem0 raised $24M in October 2025. Their blog from January 2026 discusses graph memory extensively but does not mention temporal validity windows. It is unclear if temporal edges are on their roadmap. **Confidence: insufficient data.**

5. **LangMem + Claude Code integration** -- LangMem is designed for LangGraph. We do not use LangGraph. Adapting it to our architecture is feasible but would require adapter code. **Confidence: moderate -- the patterns are transferable but the tooling is not plug-and-play.**

---

## OPTIONS

### Option 1: SQLite Temporal Extension Only (LOW RISK, IMMEDIATE)

Add `valid_from`, `valid_to`, `superseded_by`, `supersession_reason` to both `learning_rules.db` and `voice_ledger.json`. Implement `get_principles_at()`, `supersede_principle()`, `get_principle_history()` and their voice ledger equivalents. Register as MCP tools.

- **Effort:** 4-8 hours
- **New dependencies:** None
- **Monthly cost:** $0
- **Temporal coverage:** Point-in-time queries, supersession chains, principle history
- **What it misses:** Entity extraction, relationship graphs, community detection

### Option 2: SQLite Temporal + Graphiti Sidecar (MODERATE RISK, 1-2 WEEKS)

Everything in Option 1, PLUS deploy Graphiti with FalkorDB on YOGA. Feed approved principles and client interactions into Graphiti as episodes. Use Graphiti for deep temporal/relational queries ("show me everything about how our relationship with the Furlows has evolved"). Use SQLite for fast operational queries ("what rules apply to this email draft right now?").

- **Effort:** 2-3 days for SQLite temporal + 1 week for Graphiti integration
- **New dependencies:** FalkorDB (Docker), graphiti-core, LLM calls for entity extraction
- **Monthly cost:** ~$5 in LLM inference (covered by Max plan)
- **Temporal coverage:** Full bi-temporal with entity graphs
- **What it misses:** Mem0's hierarchical `user_id`/`agent_id` scoping (can be emulated with `group_id`)

### Option 3: Mem0 as Primary Memory Layer (MODERATE RISK, 1-2 WEEKS)

Replace both SQLite principles retrieval and voice ledger retrieval with Mem0. Map personas to `agent_id`, clients to `user_id`. Use the graph layer for relationship tracking. Accept the temporal gap and build custom temporal extensions on top of Mem0's graph layer.

- **Effort:** 2-3 days for core integration + ongoing work for temporal extensions
- **New dependencies:** Qdrant (Docker), optionally Neo4j, mem0ai package
- **Monthly cost:** $0 self-hosted
- **Temporal coverage:** Partial -- creation timestamps and access patterns, but no native validity windows
- **What it misses:** The core temporal feature this entire upgrade is about

### Option 4: LangMem for Procedural Memory Enhancement (LOW RISK, COMPLEMENTARY)

Add LangMem's prompt optimizer as an alternative to our current `extract_principles()` function. Use it alongside either Option 1 or 2 for more sophisticated prompt refinement.

- **Effort:** 1 day
- **New dependencies:** langmem, langchain ecosystem
- **Monthly cost:** $0
- **Temporal coverage:** None (this is a prompt optimization tool, not a temporal store)
- **What it adds:** More sophisticated principle extraction via metaprompt/gradient algorithms

---

## ACTIONS I RECOMMEND TAKING

1. **Execute Option 1 immediately.** The SQLite temporal extension is the highest-ROI move. Four to eight hours of coding, zero new dependencies, and it answers Commander's core temporal questions today. I have the schema changes and Python functions drafted above -- they can be implemented in the next coding session.

2. **Do NOT adopt Mem0 for this use case.** Despite its strong ecosystem (48K GitHub stars, $24M funding), it lacks the specific temporal capability that defines this entire upgrade. Using Mem0 here would be buying a solution to a problem we don't have (vector similarity search) while ignoring the problem we do have (temporal fact validity).

3. **Stage Graphiti/FalkorDB evaluation for Phase 2.** After the SQLite temporal layer is live and we have 30-60 days of temporal data, evaluate whether we need the entity extraction and relationship graph capabilities. If we find ourselves manually tagging entities and relationships in SQLite, that's the signal to bring in Graphiti. Install `graphiti-core` on YOGA for experimentation, but do not put it in the production path yet.

4. **Consider LangMem's prompt optimizer as a Phase 2 enhancement** to our principle extraction pipeline -- not as a temporal solution, but as a way to generate better-quality principles from corrections. The `metaprompt` algorithm with reflection steps is more sophisticated than our current single-pass extraction. But this is optimization, not architecture.

5. **For the grant narrative:** The temporal knowledge graph capability is a genuine differentiator. No consumer travel platform tracks preference evolution over time. Frame it as: "Adaptive Preference Learning with Temporal Knowledge Graphs -- a system that doesn't just remember what clients want, but understands how their preferences have evolved and why." This is the kind of language that resonates with innovation grants.

**Bottom line:** Start with the lightweight SQLite temporal extension. It's the right move for a single-operator, ~50-client luxury travel concierge. When the client roster grows or the relationship graph queries prove essential, Graphiti is the clear upgrade path. Do not over-engineer this -- temporal columns on SQLite give us the answer to every question Commander asked, today, for zero dollars and zero new infrastructure.

---

*Staff Paper from Lt Col Marcus "Wraith" Dembe, A2 (Research & Market Intelligence)*
*Dreams2Memories Travel, LLC*

---

### APPENDIX A: Source Links

**Zep / Graphiti:**
- [ArXiv Paper: Zep Temporal Knowledge Graph Architecture](https://arxiv.org/abs/2501.13956)
- [GitHub: getzep/graphiti](https://github.com/getzep/graphiti)
- [Graphiti PyPI: graphiti-core](https://pypi.org/project/graphiti-core/)
- [Zep Platform & Pricing](https://www.getzep.com/pricing/)
- [Graphiti MCP Server README](https://github.com/getzep/graphiti/blob/main/mcp_server/README.md)
- [Graphiti Deep Technical Overview](https://deepwiki.com/getzep/graphiti)
- [Zep Blog: Architecture](https://blog.getzep.com/zep-a-temporal-knowledge-graph-architecture-for-agent-memory/)

**Mem0:**
- [GitHub: mem0ai/mem0](https://github.com/mem0ai/mem0)
- [Mem0 Documentation](https://docs.mem0.ai/)
- [Mem0 Research Paper (26% accuracy gains)](https://mem0.ai/research)
- [Mem0 Graph Memory Docs](https://docs.mem0.ai/open-source/features/graph-memory)
- [Mem0 Self-Hosted Docker Guide](https://mem0.ai/blog/self-host-mem0-docker)
- [Mem0 Python SDK Quickstart](https://docs.mem0.ai/open-source/python-quickstart)
- [AWS: Mem0 with ElastiCache & Neptune](https://aws.amazon.com/blogs/database/build-persistent-memory-for-agentic-ai-applications-with-mem0-open-source-amazon-elasticache-for-valkey-and-amazon-neptune-analytics/)

**LangMem:**
- [GitHub: langchain-ai/langmem](https://github.com/langchain-ai/langmem)
- [LangMem Documentation](https://langchain-ai.github.io/langmem/)
- [LangMem Launch Blog](https://blog.langchain.com/langmem-sdk-launch/)
- [LangMem Procedural Memory Notebook](https://github.com/langchain-ai/langmem/blob/main/examples/intro_videos/procedural_memory.ipynb)
- [LangMem Conceptual Guide](https://langchain-ai.github.io/langmem/concepts/conceptual_guide/)
- [LangMem PyPI](https://pypi.org/project/langmem/)

**Neo4j / SQLite Temporal:**
- [Neo4j Cypher Manual: Temporal Values](https://neo4j.com/docs/cypher-manual/current/values-and-types/temporal/)
- [Neo4j Python Driver: Temporal Data Types](https://neo4j.com/docs/api/python-driver/current/types/temporal.html)
- [GitHub: thatdevsherry/historia (SQLite Temporal Tables)](https://github.com/thatdevsherry/historia)
- [SQLite Temporal Tables Pattern](https://www.ohnekontur.de/2024/02/19/unlocking-time-harnessing-the-power-of-temporal-tables-in-sqlite/)
- [Neo4j Blog: Graphiti Knowledge Graph Memory](https://neo4j.com/blog/developer/graphiti-knowledge-graph-memory/)

**Benchmarks / Comparisons:**
- [Mem0 vs Zep Comparison (2026)](https://vectorize.io/articles/mem0-vs-zep)
- [5 AI Agent Memory Systems Compared (2026 Benchmark Data)](https://dev.to/varun_pratapbhardwaj_b13/5-ai-agent-memory-systems-compared-mem0-zep-letta-supermemory-superlocalmemory-2026-benchmark-59p3)
- [Cognee: AI Memory Tools Evaluation](https://www.cognee.ai/blog/deep-dives/ai-memory-tools-evaluation)
- [Mem0 vs Zep vs LangMem vs MemoClaw Comparison 2026](https://dev.to/anajuliabit/mem0-vs-zep-vs-langmem-vs-memoclaw-ai-agent-memory-comparison-2026-1l1k)
