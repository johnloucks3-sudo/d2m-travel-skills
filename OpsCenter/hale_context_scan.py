"""
Hale Context Scan — Qwen Deep Read
====================================
Feeds all key Thunderbird documents to Qwen's massive context window.
Produces a structured digest written to hale_session_context.md.
Runs before brief generation so Hale briefs from full institutional knowledge.

Qwen 3.6 Plus context: ~32K tokens. We batch the most important docs first.

Priority tiers:
  TIER 1 (always) — state, memory, master plan, CLAUDE.md, session checkpoint
  TIER 2 (always) — all dossiers, wing comms, activity board, knowledge base
  TIER 3 (if space) — roadmaps, blueprints, plans, intel digests

Author: Col Victoria "Iron Vic" Hale — 2026-04-03
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
_OPSCENTER = Path(__file__).resolve().parent
_OUTPUT = _ROOT / "hale_session_context.md"

load_dotenv(str(_ROOT / ".env"))
load_dotenv(str(_ROOT / ".env.telegram"))

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
QWEN_MODEL = "qwen/qwen3.6-plus:free"
MT = timezone(timedelta(hours=-6))

# ── Token budget ──
# Qwen 3.6 Plus: ~32K context. Reserve 3K for output.
# Each char ~0.25 tokens (rough). Budget: ~29K tokens = ~116K chars.
MAX_INPUT_CHARS = 100_000  # conservative


# ── Document priority list ──

TIER1 = [
    _ROOT / "hale_state.json",
    _ROOT / "hale_memory.md",
    _ROOT / "hale_decisions.md",
    _ROOT / "THUNDERBIRD_MASTER_PLAN.md",
    _ROOT / "CLAUDE.md",
    _ROOT / "session_autosave_latest.md",
    _ROOT / "OpsCenter_KnowledgeBase.md",
]

TIER2_GLOBS = [
    (_ROOT / "dossiers", "*.md"),
    (_ROOT / "dossiers", "*.json"),
    (_ROOT / "OpsCenter" / "collaboration", "*.md"),
    (_OPSCENTER, "activity_board.md"),
]

TIER2_FILES = [
    _ROOT / "THUNDERBIRD_USER_MANUAL.md",
    _ROOT / "docs" / "HALE_SUPER_PERSONA_BLUEPRINT_v1.md",
    _ROOT / "docs" / "THUNDERBIRD_A2A_INTEGRATION_PLAN_v1.md",
    _ROOT / "intel" / "daily_innovation_digest.md",
]

TIER3_GLOBS = [
    (_ROOT / "docs", "*.md"),
    (_ROOT / "Plans", "*.md"),
]

# Files to always skip
SKIP_PATTERNS = {
    ".venv", "__pycache__", "node_modules", ".git",
    "hale_session_context.md",  # don't read our own output
    "hale_brief.md",            # generated, not source
}


def _should_skip(path: Path) -> bool:
    return any(p in str(path) for p in SKIP_PATTERNS)


def _read_file(path: Path, max_chars: int = 20_000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n... [truncated — {len(text)} chars total]"
        return text
    except Exception as e:
        return f"[READ ERROR: {e}]"


def _collect_documents() -> list[dict]:
    """Collect documents in priority order. Returns list of {name, content}."""
    docs = []
    total_chars = 0

    def add(path: Path, label: str = None, max_chars: int = 15_000):
        nonlocal total_chars
        if total_chars >= MAX_INPUT_CHARS:
            return False
        if not path.exists() or _should_skip(path):
            return True
        content = _read_file(path, max_chars=max_chars)
        remaining = MAX_INPUT_CHARS - total_chars
        if len(content) > remaining:
            content = content[:remaining] + "\n... [budget exhausted]"
        docs.append({"name": label or path.name, "content": content})
        total_chars += len(content)
        return total_chars < MAX_INPUT_CHARS

    # Tier 1
    for f in TIER1:
        if not add(f, max_chars=20_000):
            break

    # Tier 2 globs
    for (directory, pattern) in TIER2_GLOBS:
        if total_chars >= MAX_INPUT_CHARS:
            break
        if not directory.exists():
            continue
        for f in sorted(directory.glob(pattern)):
            if not add(f, max_chars=8_000):
                break

    # Tier 2 files
    for f in TIER2_FILES:
        if not add(f, max_chars=12_000):
            break

    # Tier 3 globs
    for (directory, pattern) in TIER3_GLOBS:
        if total_chars >= MAX_INPUT_CHARS:
            break
        if not directory.exists():
            continue
        for f in sorted(directory.glob(pattern)):
            if not add(f, max_chars=6_000):
                break

    return docs, total_chars


def _build_corpus(docs: list[dict]) -> str:
    """Assemble all documents into a single corpus string."""
    parts = []
    for doc in docs:
        parts.append(f"\n\n{'='*60}\n## FILE: {doc['name']}\n{'='*60}\n{doc['content']}")
    return "\n".join(parts)


def _call_qwen(corpus: str) -> str:
    """Send corpus to Qwen and get back structured digest."""
    system = """You are Hale's institutional memory engine.
You have been given a full dump of Thunderbird Wing's knowledge base.
Your job: produce a structured digest that Hale can use as session context.
Output clean Markdown only. No tool calls. No hallucinations. Only what's in the documents."""

    prompt = f"""Read the following Thunderbird Wing documents and produce a structured digest.

{corpus}

---

Now produce the digest with these sections:

## 1. ACTIVE CLIENTS & BOOKINGS
For each client: name, trip, status, key dates, any urgent flags.

## 2. OPEN TASKS & PENDING ITEMS
Everything in flight across all systems. Who owns what.

## 3. FINANCIAL STATUS
Payments due, overdue, commissions pending. Concrete numbers where visible.

## 4. WING ARCHITECTURE (current)
Model routing, key services, what's running, what's broken.

## 5. STANDING ORDERS (non-negotiable)
List all active SOs with dates.

## 6. STRATEGY & ROADMAP
Active initiatives, next priorities, what Commander has authorized.

## 7. KEY DECISIONS (recent)
What was decided, when, by whom.

## 8. URGENT FLAGS
Anything that needs Commander attention in the next 24 hours.

Be specific. Use numbers where available. If something is unknown, say UNKNOWN, not guess."""

    try:
        payload = json.dumps({
            "model": QWEN_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
            "max_tokens": 3000,
            "temperature": 0.1,
        }, ensure_ascii=False).encode("utf-8")

        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json; charset=utf-8",
                "HTTP-Referer": "https://d2mluxury.quest",
                "X-Title": "Thunderbird Wing - Hale Context Scan",
            },
            data=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[CONTEXT SCAN ERROR] Qwen failed: {e}"


def run():
    now = datetime.now(MT)
    ts = now.strftime("%Y-%m-%d %H:%M MT")

    print(f"[hale_context_scan] Starting at {ts}")

    if not OPENROUTER_API_KEY:
        print("[hale_context_scan] ERROR: OPENROUTER_API_KEY not set.")
        sys.exit(1)

    docs, total_chars = _collect_documents()
    print(f"[hale_context_scan] Collected {len(docs)} documents ({total_chars:,} chars)")

    corpus = _build_corpus(docs)
    print(f"[hale_context_scan] Sending to Qwen ({len(corpus):,} chars corpus)...")

    digest = _call_qwen(corpus)

    header = f"# HALE — Session Context\n*Generated by Qwen deep scan at {ts}*\n*Documents read: {len(docs)} | Chars ingested: {total_chars:,}*\n\n---\n\n"
    output = header + digest

    _OUTPUT.write_text(output, encoding="utf-8")
    print(f"[hale_context_scan] Context written to {_OUTPUT}")
    print(f"[hale_context_scan] Digest length: {len(digest):,} chars")

    return output


if __name__ == "__main__":
    result = run()
    # Print first 500 chars as preview
    print("\n--- DIGEST PREVIEW ---")
    print(result[:800])
