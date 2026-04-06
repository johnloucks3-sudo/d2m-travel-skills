"""
Thunderbird Grant Evidence Compiler
====================================
Scans the Thunderbird OS codebase and generates structured evidence
for SBIR/STTR, NSF, SBA, and veteran grant applications.

Produces:
  - Quantitative metrics (LOC, tools, personas, modules)
  - Novel contribution inventory (things no existing system does)
  - Academic framing (PRELUDE/CIPHER/ICAI alignment)
  - Structured evidence package (Markdown output)

MCP tools registered:
  grant_compile_evidence  — scan codebase, generate metrics + evidence
  grant_generate_narrative — produce submission-ready narrative section

Usage:
  python3 thunderbird_grant_compiler.py               # CLI: full evidence scan
  python3 thunderbird_grant_compiler.py --narrative    # CLI: narrative output

Owner: Dreams2Memories Travel, LLC — John Loucks
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path(os.path.expanduser("~/Thunderbird"))

# ---------------------------------------------------------------------------
# Novel Contributions — things no existing system does
# ---------------------------------------------------------------------------

NOVEL_CONTRIBUTIONS = [
    {
        "id": "NC-1",
        "title": "Multi-Persona Preference Routing",
        "description": (
            "11 specialized AI personas with distinct voice profiles, domain expertise, "
            "and behavioral constraints. Learned preferences are routed to the correct "
            "persona context based on domain, client tier, and relationship type. "
            "No existing system — academic or production — routes preference learning "
            "through a multi-persona architecture."
        ),
        "files": [
            "thunderbird_personas.py:PERSONA_REGISTRY",
            "thunderbird_learning.py:get_applicable_rules",
            "thunderbird_voice_ledger.py:voice_ledger_get",
        ],
        "literature_gap": "Zero papers, zero production systems doing multi-persona preference routing.",
        "academic_ref": "Extends PRELUDE (NeurIPS 2024) single-agent personalization to multi-agent.",
    },
    {
        "id": "NC-2",
        "title": "3-Layer Preference Learning Architecture",
        "description": (
            "Layer 1 (Explicit): Edit diff capture, principle extraction, CIPHER retrieval. "
            "Layer 2 (Passive): Sent email voice analysis, auto-enrichment from Gmail/Drive/Calendar. "
            "Layer 3 (Temporal): Knowledge graph with valid_from/valid_to, preference shift detection. "
            "No system integrates all three layers into a unified preference pipeline."
        ),
        "files": [
            "thunderbird_learning.py (Layer 1 — CIPHER)",
            "thunderbird_auto_enrich.py (Layer 2 — passive observation)",
            "thunderbird_my_voice.py (Layer 2 — voice analysis)",
            "thunderbird_temporal_memory.py (Layer 3 — temporal KG)",
        ],
        "literature_gap": (
            "PRELUDE does Layer 1 only. Windsurf Cascade does Layer 2 only. "
            "Zep does Layer 3 only. No system combines all three."
        ),
        "academic_ref": "Novel integration of CIPHER (NeurIPS 2024) + ICAI (ICLR 2025) + Zep temporal.",
    },
    {
        "id": "NC-3",
        "title": "USAF Formal Coordination (SSS) in AI Agent Systems",
        "description": (
            "Staff Summary Sheet system modeled on AF Form 1768. AI personas issue "
            "CONCUR/NON-CONCUR positions with rationale. Non-concurrence memos and "
            "rebuttals surface genuine disagreement before the human decision-maker. "
            "No AI multi-agent system uses formal military coordination doctrine."
        ),
        "files": [
            "thunderbird_sss.py:create_sss",
            "thunderbird_sss.py:coordinate_sss",
            "thunderbird_sss.py:resolve_nonconcur",
            "thunderbird_sss.py:present_to_commander",
        ],
        "literature_gap": "No multi-agent AI system implements formal coordination with non-concurrence resolution.",
        "academic_ref": "Addresses consensus theater problem identified in AI agent collaboration research.",
    },
    {
        "id": "NC-4",
        "title": "Temporal Knowledge Graphs for Travel Preferences",
        "description": (
            "Every client preference has a validity window (valid_from/valid_to). "
            "Supersession chains track how preferences evolve. Point-in-time queries "
            "answer 'what did this client prefer last December?' Preference shift "
            "detection surfaces trends proactively."
        ),
        "files": [
            "thunderbird_temporal_memory.py:SQLiteTemporalBackend",
            "thunderbird_temporal_memory.py:detect_preference_shifts",
            "thunderbird_learning.py:principles (valid_from/valid_to/superseded_by)",
        ],
        "literature_gap": "Zep offers temporal edges but not domain-specific travel preference modeling.",
        "academic_ref": "Extends Graphiti bi-temporal edges to luxury travel domain.",
    },
    {
        "id": "NC-5",
        "title": "Auto-Enrichment from Heterogeneous Sources",
        "description": (
            "When any persona discusses a client, the system auto-pulls context from "
            "Gmail threads, Google Drive documents, Calendar events, dossiers, and "
            "learned preferences. Equivalent to Google Personal Intelligence but for "
            "a multi-persona travel concierge architecture."
        ),
        "files": [
            "thunderbird_auto_enrich.py:enrich_client_context",
            "thunderbird_auto_enrich.py:_gather_gmail_context",
            "thunderbird_auto_enrich.py:_gather_drive_context",
            "thunderbird_auto_enrich.py:_gather_calendar_context",
        ],
        "literature_gap": "Google PI is single-user, single-agent. No multi-persona auto-enrichment exists.",
        "academic_ref": "Implements retrieval-augmented generation across heterogeneous enterprise sources.",
    },
    {
        "id": "NC-6",
        "title": "Voice Profile Learning from Sent Email Analysis",
        "description": (
            "Analyzes the owner's sent emails to extract voice patterns — tone, formality, "
            "sign-off conventions, sentence structure, relationship tier markers. Feeds "
            "learned voice into the Dani (client-facing) persona for authentic output. "
            "Inspired by Spark Mail but integrated into multi-persona learning pipeline."
        ),
        "files": [
            "thunderbird_my_voice.py (sent email analysis)",
            "thunderbird_voice_ledger.py (per-client/per-tier voice rules)",
            "thunderbird_dani_engine.py (voice injection into output)",
        ],
        "literature_gap": "Spark Mail does single-user voice. No system does multi-persona voice routing.",
        "academic_ref": "Novel application of stylometric analysis to AI agent voice personalization.",
    },
    {
        "id": "NC-7",
        "title": "Information Delta Tracking (Semantic Edit Classification)",
        "description": (
            "For every draft edit, classifies WHAT TYPE of information was added or removed: "
            "pricing, personal touch, logistics, internal jargon, formality adjustments. "
            "Creates domain-specific learning beyond simple text diff. Inspired by "
            "Windsurf Cascade action tracking but applied to email/document editing."
        ),
        "files": [
            "thunderbird_info_delta.py (semantic classification)",
            "thunderbird_learning.py:capture_diff (raw capture)",
            "thunderbird_learning.py:extract_principle (rule extraction)",
        ],
        "literature_gap": "Windsurf tracks code actions. No system classifies email edit semantics for learning.",
        "academic_ref": "Extends edit distance metrics with semantic type classification for preference extraction.",
    },
]

# ---------------------------------------------------------------------------
# Codebase Scanner
# ---------------------------------------------------------------------------


def scan_codebase() -> Dict[str, Any]:
    """Scan the Thunderbird codebase and produce quantitative evidence."""
    metrics: Dict[str, Any] = {}

    # 1. Count thunderbird_*.py files and lines
    tb_files = sorted(THUNDERBIRD_DIR.glob("thunderbird_*.py"))
    total_lines = 0
    file_details = []
    for f in tb_files:
        try:
            lines = len(f.read_text(encoding="utf-8", errors="replace").splitlines())
            total_lines += lines
            file_details.append({"file": f.name, "lines": lines})
        except Exception:
            pass

    metrics["thunderbird_modules"] = len(tb_files)
    metrics["thunderbird_lines"] = total_lines
    metrics["top_modules"] = sorted(file_details, key=lambda x: x["lines"], reverse=True)[:15]

    # 2. Count all Python files
    all_py = list(THUNDERBIRD_DIR.glob("*.py")) + list(THUNDERBIRD_DIR.glob("scripts/*.py"))
    all_lines = 0
    for f in all_py:
        try:
            all_lines += len(f.read_text(encoding="utf-8", errors="replace").splitlines())
        except Exception:
            pass
    metrics["total_python_files"] = len(all_py)
    metrics["total_python_lines"] = all_lines

    # 3. Count MCP tools registered
    mcp_pattern = re.compile(r"@mcp_server\.tool|@mcp\.tool")
    mcp_tools = 0
    mcp_by_file = []
    scan_files = list(THUNDERBIRD_DIR.glob("thunderbird_*.py"))
    mcp_server_file = THUNDERBIRD_DIR / "travel_mcp_server.py"
    if mcp_server_file.exists():
        scan_files.append(mcp_server_file)
    for f in scan_files:
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            count = len(mcp_pattern.findall(content))
            if count > 0:
                mcp_tools += count
                mcp_by_file.append({"file": f.name, "tools": count})
        except Exception:
            pass
    metrics["mcp_tools_total"] = mcp_tools
    metrics["mcp_tools_by_file"] = sorted(mcp_by_file, key=lambda x: x["tools"], reverse=True)

    # 4. Count personas
    personas_file = THUNDERBIRD_DIR / "thunderbird_personas.py"
    persona_count = 0
    persona_ids = []
    if personas_file.exists():
        try:
            content = personas_file.read_text(encoding="utf-8", errors="replace")
            matches = re.findall(r'^\s+"([A-Z][A-Z0-9]+)":\s*\{', content, re.MULTILINE)
            persona_count = len(matches)
            persona_ids = matches
        except Exception:
            pass
    metrics["persona_count"] = persona_count
    metrics["persona_ids"] = persona_ids

    # 5. Count dossiers, templates, n8n workflows
    dossier_dir = THUNDERBIRD_DIR / "dossiers"
    metrics["client_dossiers"] = len(list(dossier_dir.glob("*.md"))) if dossier_dir.exists() else 0

    template_dir = THUNDERBIRD_DIR / "templates"
    metrics["templates"] = (
        len(list(template_dir.glob("*.html")) + list(template_dir.glob("*.j2")))
        if template_dir.exists()
        else 0
    )

    n8n_dir = THUNDERBIRD_DIR / "deploy" / "n8n"
    metrics["n8n_workflows"] = len(list(n8n_dir.glob("*.json"))) if n8n_dir.exists() else 0

    # 6. Count key function signatures (novel contributions)
    novel_functions = [
        ("thunderbird_learning.py", r"def (capture_diff|extract_principle|_tfidf_vectorize|get_applicable_rules|_cipher_search)\b"),
        ("thunderbird_temporal_memory.py", r"def (add_temporal_fact|query_fact_at_time|detect_preference_shifts)\b"),
        ("thunderbird_auto_enrich.py", r"def (enrich_client_context|detect_client_names|_gather_gmail_context)\b"),
        ("thunderbird_sss.py", r"def (create_sss|coordinate_sss|resolve_nonconcur|present_to_commander)\b"),
        ("thunderbird_personas.py", r"def (call_persona|get_persona_system_prompt)\b"),
        ("thunderbird_voice_ledger.py", r"def (voice_ledger_get|voice_ledger_add)\b"),
        ("thunderbird_info_delta.py", r"def (classify_edit|track_delta|compute_info_delta)\b"),
        ("thunderbird_my_voice.py", r"def (analyze_sent_emails|extract_voice_profile|refresh_voice_profile)\b"),
        ("thunderbird_dani_engine.py", r"def (aggregate_phase|artist_phase|advocate_phase|generate_dani_response)\b"),
    ]
    novel_fn_count = 0
    for fname, pattern in novel_functions:
        fpath = THUNDERBIRD_DIR / fname
        if fpath.exists():
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
                novel_fn_count += len(re.findall(pattern, content))
            except Exception:
                pass
    metrics["novel_functions"] = novel_fn_count

    # 7. Timestamp
    metrics["scan_timestamp"] = datetime.now(timezone.utc).isoformat()
    metrics["scan_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return metrics


# ---------------------------------------------------------------------------
# Evidence Package Generator
# ---------------------------------------------------------------------------


def generate_evidence_package(metrics: Optional[Dict] = None) -> str:
    """Generate a structured Markdown evidence package for grant applications."""
    if metrics is None:
        metrics = scan_codebase()

    lines = [
        "# THUNDERBIRD OS — GRANT EVIDENCE PACKAGE",
        f"## Dreams2Memories Travel, LLC | Compiled {metrics.get('scan_date', 'N/A')}",
        "",
        "---",
        "",
        "## EXECUTIVE SUMMARY",
        "",
        "Thunderbird OS is a production AI concierge platform for luxury travel that implements",
        "**novel preference learning architecture** with no equivalent in academic literature or",
        "commercial products. The system operates 7 novel technical contributions across",
        f"{metrics.get('thunderbird_modules', 0)} Python modules ({metrics.get('thunderbird_lines', 0):,} lines),",
        f"{metrics.get('mcp_tools_total', 0)} registered MCP tools, and {metrics.get('persona_count', 0)} specialized AI personas.",
        "",
        "**Key claim:** Multi-persona preference routing — where learned preferences are injected",
        "into the correct AI persona based on domain, client tier, and relationship type — has",
        "zero papers in the literature and zero production implementations.",
        "",
        "---",
        "",
        "## NOVEL CONTRIBUTIONS",
        "",
    ]

    # Literature comparison table
    lines.extend([
        "### What Exists in Literature",
        "",
        "| System | What It Does | What It Lacks |",
        "|--------|-------------|---------------|",
        "| PRELUDE/CIPHER (NeurIPS 2024) | Context-sensitive preference retrieval via embeddings | Single-agent only, no multi-persona routing |",
        "| ICAI (ICLR 2025) | Hierarchical preference constitution with tiers | No temporal dimension, no multi-persona |",
        "| LangMem (LangChain) | Semantic + episodic + procedural memory | No formal coordination, no voice learning |",
        "| Zep/Graphiti | Temporal knowledge graph with bi-temporal edges | Generic — no travel domain modeling |",
        "| Windsurf Cascade | Action tracking across IDE interactions | Code-only — no email/document edit semantics |",
        "| Spark Mail | Sent email voice analysis | Single-user, no preference routing |",
        "| Google Personal Intelligence | Multi-source auto-enrichment | Single-agent, consumer — not enterprise multi-persona |",
        "",
        "### What Thunderbird OS Does That NO ONE Else Does",
        "",
    ])

    for nc in NOVEL_CONTRIBUTIONS:
        lines.extend([
            f"#### {nc['id']}: {nc['title']}",
            "",
            nc["description"],
            "",
            f"**Literature gap:** {nc['literature_gap']}",
            f"**Academic reference:** {nc['academic_ref']}",
            f"**Code references:** {', '.join(nc['files'])}",
            "",
        ])

    # Technical architecture
    lines.extend([
        "---",
        "",
        "## TECHNICAL ARCHITECTURE",
        "",
        "### The 3-Layer Preference Learning Pipeline",
        "",
        "```",
        "                    ┌─────────────────────────┐",
        "                    │   CLIENT OUTPUT          │",
        "                    │   (Email/Telegram/       │",
        "                    │    Portal/Voice)         │",
        "                    └───────────┬─────────────┘",
        "                                │ injects",
        "                    ┌───────────▼─────────────┐",
        "                    │   CONTEXT COMPILER       │",
        "                    │                          │",
        "                    │  ┌── Layer 1 Rules       │",
        "                    │  ├── Layer 2 Context     │",
        "                    │  └── Layer 3 Temporal    │",
        "                    └───────────┬─────────────┘",
        "                                │ queries",
        "          ┌─────────────────────┼─────────────────────┐",
        "          │                     │                     │",
        "┌─────────▼────────┐  ┌────────▼──────────┐  ┌──────▼────────────┐",
        "│  LAYER 1         │  │  LAYER 2          │  │  LAYER 3          │",
        "│  Explicit         │  │  Passive           │  │  Temporal KG      │",
        "│  Corrections     │  │  Observations      │  │                   │",
        "│                  │  │                    │  │  valid_from/to    │",
        "│  Edit diffs      │  │  Sent analysis     │  │  Entity graph     │",
        "│  CIPHER search   │  │  Auto-enrich       │  │  Shift detection  │",
        "│  Principle DB    │  │  Action tracking   │  │  Supersession     │",
        "└──────────────────┘  └────────────────────┘  └───────────────────┘",
        "          ▲                     ▲                     ▲",
        "          │                     │                     │",
        "   Owner edits          Owner actions          Time passes,",
        "   AI drafts             (write, forward,      preferences",
        "                         approve, reject)       evolve",
        "```",
        "",
        "### Multi-Persona Architecture (The Wing)",
        "",
        f"**{metrics.get('persona_count', 0)} specialized AI personas** organized in USAF A-Staff doctrine:",
        "",
        "| Persona | Role | Domain |",
        "|---------|------|--------|",
        "| COS (Hale) | Chief of Staff — orchestration | All domains |",
        "| EXEC (Solberg-Vega) | Voice + Visual + Intent | Brand, tone |",
        "| A1 (Crenshaw) | Personnel & Admin | Audit, records |",
        "| A2 (Dembe) | Research & Market Intel | Destinations, competitors |",
        "| A3 (Moreau/Dani) | Client-facing concierge | Bookings, client comms |",
        "| A5 (Castillo) | Strategy & Growth | Pricing, business dev |",
        "| A6 (Voss) | Creative Director | Brand, design |",
        "| A9 (Harlan) | Finance & Process | Commissions, ROI |",
        "| CH (Washington) | Ethics & Morale | Wisdom, guardrails |",
        "| A12 (ELON) | Innovation & Disruption | First principles |",
        "",
    ])

    # Codebase metrics
    lines.extend([
        "---",
        "",
        "## CODEBASE METRICS",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Thunderbird modules (thunderbird_*.py) | {metrics.get('thunderbird_modules', 0)} |",
        f"| Thunderbird lines of code | {metrics.get('thunderbird_lines', 0):,} |",
        f"| Total Python files | {metrics.get('total_python_files', 0)} |",
        f"| Total Python lines | {metrics.get('total_python_lines', 0):,} |",
        f"| MCP tools registered | {metrics.get('mcp_tools_total', 0)} |",
        f"| AI personas | {metrics.get('persona_count', 0)} |",
        f"| Client dossiers | {metrics.get('client_dossiers', 0)} |",
        f"| Jinja2/HTML templates | {metrics.get('templates', 0)} |",
        f"| n8n automation workflows | {metrics.get('n8n_workflows', 0)} |",
        f"| Novel contribution functions | {metrics.get('novel_functions', 0)} |",
        "",
        "### Top Modules by Size",
        "",
        "| Module | Lines |",
        "|--------|-------|",
    ])
    for m in metrics.get("top_modules", []):
        lines.append(f"| {m['file']} | {m['lines']:,} |")

    lines.extend([
        "",
        "### MCP Tools by Module",
        "",
        "| Module | Tools |",
        "|--------|-------|",
    ])
    for m in metrics.get("mcp_tools_by_file", []):
        lines.append(f"| {m['file']} | {m['tools']} |")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Narrative Generator — for grant proposal text
# ---------------------------------------------------------------------------


def generate_narrative() -> str:
    """Generate a submission-ready narrative section for grant proposals."""
    metrics = scan_codebase()

    narrative = f"""# THUNDERBIRD OS — GRANT NARRATIVE
## Innovation in AI-Powered Luxury Travel Concierge Systems
### Dreams2Memories Travel, LLC | {datetime.now().strftime('%B %Y')}

---

## 1. THE PROBLEM

The luxury travel industry faces a fundamental mismatch between AI capability and human
trust. While 30% of travelers now use AI for trip planning, only 2% allow AI to make
actual bookings (Skift, 2026). In March 2026, OpenAI abandoned direct booking capabilities
in ChatGPT, validating that the industry needs a human-AI hybrid model — not full automation.

Existing AI systems fail luxury travelers because they operate as single-agent,
stateless interactions. They cannot remember that a client shifted from Mediterranean
to Scandinavian preferences, that a couple prefers suite upgrades on anniversaries,
or that a particular client requires a warm-but-not-casual communication tone.

## 2. THE INNOVATION

Thunderbird OS introduces **multi-persona preference routing** — a novel AI architecture
where learned preferences flow through specialized AI agents organized in a formal
coordination structure. This system has **zero equivalents** in academic literature or
commercial products.

### 2.1 Technical Novelty

The system implements a 3-layer preference learning pipeline:

**Layer 1 — Explicit Correction Learning:** When the human advisor edits an AI-generated
draft, the system captures the exact delta, extracts a generalizable principle, and stores
it with context embeddings (CIPHER). Future drafts retrieve the most contextually similar
past corrections — not just keyword matches. This extends PRELUDE (NeurIPS 2024) from
single-agent to multi-persona routing.

**Layer 2 — Passive Observation Learning:** The system analyzes the advisor's naturally
sent emails to extract voice patterns, monitors which draft suggestions are accepted vs.
rejected, and auto-enriches every client query with context from Gmail, Google Drive,
and Calendar. This operates like Google Personal Intelligence but across a multi-persona
architecture with {metrics.get('persona_count', 0)} specialized agents.

**Layer 3 — Temporal Knowledge Graphs:** Every client preference has a validity window.
The system tracks when preferences changed and why, detects trends, and proactively
surfaces shifts. "The Furlows preferred Mediterranean until 2025, then shifted to
Scandinavia" is a query the system can answer — and volunteer proactively.

### 2.2 Multi-Persona Architecture

Unlike single-agent assistants, Thunderbird OS operates {metrics.get('persona_count', 0)} AI
personas organized in USAF A-Staff doctrine. Each persona has distinct voice characteristics,
domain expertise, and behavioral constraints. A formal coordination mechanism — the Staff
Summary Sheet, modeled on USAF AF Form 1768 — surfaces genuine disagreement between personas
before the human decision-maker acts. This eliminates the "consensus theater" problem
documented in multi-agent AI research.

### 2.3 Production Scale

The system is not a research prototype. It is a production platform serving paying
luxury travel clients:

- **{metrics.get('thunderbird_lines', 0):,} lines** of Python across {metrics.get('thunderbird_modules', 0)} core modules
- **{metrics.get('mcp_tools_total', 0)} MCP tools** providing real-time access to booking systems, airline data,
  hotel inventory, and client communications
- **{metrics.get('n8n_workflows', 0)} automation workflows** handling scheduled intel, email processing, and alerts
- **{metrics.get('client_dossiers', 0)} active client dossiers** with structured preference and booking data
- Telegram command-and-control interface for mobile advisor operations
- Client-facing portal with magic-link authentication

## 3. MARKET VALIDATION

- ChatGPT abandoned direct booking (Mar 2026) — validates the concierge model
- 30% of travelers use AI for planning, 2% let AI book — D2M targets the 28% gap
- Luxury travel market: $1.5T globally, growing 7.5% annually
- AI in travel market projected to reach $13.4B by 2030

## 4. FOUNDER QUALIFICATIONS

**John Loucks** — Founder & CEO, Dreams2Memories Travel, LLC

- **60% service-connected disabled veteran** (VA rating)
- **USAFA graduate** — United States Air Force Academy, commissioned officer
- **SDVOSB eligible** — Service-Disabled Veteran-Owned Small Business
- Active, licensed travel advisor with paying clients and host agency relationship
- Colorado Springs, Colorado — USAFA community

## 5. WHAT FUNDING WOULD ACCOMPLISH

A $50K-$150K grant would fund:

| Item | Cost | Timeline |
|------|------|----------|
| Vector embedding infrastructure (CIPHER Phase 2) | $10K-$15K | Months 1-2 |
| Temporal knowledge graph deployment (Zep/Neo4j) | $8K-$12K | Months 2-3 |
| Academic paper submission (NeurIPS/AAAI workshop) | $5K-$8K | Months 3-4 |
| User study with 10 luxury travel advisors | $15K-$25K | Months 3-5 |
| Production hardening and security audit | $10K-$15K | Months 4-5 |
| Client-facing portal expansion | $10K-$15K | Months 5-6 |
| API documentation and developer tools | $5K-$10K | Month 6 |

## 6. BROADER IMPACT

The multi-persona preference routing architecture is domain-general. While developed for
luxury travel, the pattern applies to:

- **Healthcare:** Multi-specialist coordination with patient preference continuity
- **Legal:** Multi-practice team coordination with client communication preferences
- **Financial advisory:** Multi-product teams with evolving client risk preferences
- **Education:** Multi-instructor coordination with individual learning preferences

The USAF formal coordination mechanism (SSS) addresses a documented problem in AI safety:
how to surface genuine disagreement among AI agents before a human acts on their recommendations.

---

*Dreams2Memories Travel, LLC — Colorado Springs, CO*
*John Loucks, Founder & CEO — USAFA, 60% Disabled Veteran*
"""
    return narrative


# ---------------------------------------------------------------------------
# MCP Tool Registration
# ---------------------------------------------------------------------------


def register_grant_tools(mcp_server):
    """Register grant evidence compiler tools with the MCP server."""

    @mcp_server.tool(
        name="grant_compile_evidence",
        annotations={"title": "Compile Grant Evidence Package", "readOnlyHint": True},
    )
    async def grant_compile_evidence_tool(
        output_format: str = "markdown",
    ) -> str:
        """Scan the Thunderbird codebase and compile structured evidence for grant applications.

        Returns quantitative metrics (LOC, tools, personas), novel contribution inventory,
        and academic framing. Output as Markdown or JSON.

        Args:
            output_format: 'markdown' for formatted evidence package, 'json' for raw metrics
        """
        metrics = scan_codebase()

        if output_format == "json":
            return json.dumps(
                {
                    "metrics": metrics,
                    "novel_contributions": NOVEL_CONTRIBUTIONS,
                    "status": "compiled",
                },
                indent=2,
                default=str,
            )

        package = generate_evidence_package(metrics)
        return package

    @mcp_server.tool(
        name="grant_generate_narrative",
        annotations={"title": "Generate Grant Narrative", "readOnlyHint": True},
    )
    async def grant_generate_narrative_tool() -> str:
        """Generate a submission-ready narrative section for SBIR/STTR/NSF grant proposals.

        Produces a complete narrative covering: problem statement, technical innovation,
        market validation, founder qualifications, budget framework, and broader impact.
        Uses real codebase metrics scanned at generation time.
        """
        return generate_narrative()

    logger.info("Grant compiler tools registered (2 tools)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if "--narrative" in sys.argv:
        print(generate_narrative())
    elif "--json" in sys.argv:
        metrics = scan_codebase()
        print(json.dumps(
            {"metrics": metrics, "novel_contributions": NOVEL_CONTRIBUTIONS},
            indent=2, default=str,
        ))
    else:
        metrics = scan_codebase()
        package = generate_evidence_package(metrics)
        print(package)

        # Also write to file
        output_path = THUNDERBIRD_DIR / "intel" / "grant_evidence_package.md"
        output_path.write_text(package, encoding="utf-8")
        print(f"\n--- Written to {output_path} ---")
