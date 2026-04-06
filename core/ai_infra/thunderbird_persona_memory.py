"""
Thunderbird Persona Persistent Memory — Subagent Memory Directories
====================================================================
Each Wing persona gets a persistent memory directory under
~/Thunderbird/Personas/memory/<SLOT>/ that survives across sessions.

Architecture:
  - persona_context.md   — Identity, role, style, active tasks (seed file)
  - session_notes.md     — Appended insights from each session
  - client_context.md    — Client-specific memories
  - decisions.md         — Key decisions made or recommended
  - *.md                 — Any additional memory files

API:
  read_persona_memory(persona_id)           — Read a specific file from a persona's memory dir
  write_persona_memory(persona_id, key, value) — Write/overwrite a named memory file
  append_persona_memory(persona_id, entry)  — Append a timestamped entry to session_notes.md
  get_persona_context_for_injection(persona_id) — Read ALL files, format for prompt injection
  list_persona_memory_files(persona_id)     — List all files in a persona's memory dir

Used by:
  - thunderbird_personas.py (inject_memory_context enrichment)
  - travel_mcp_server.py (store_persona_memory / recall_persona_memory MCP tools)
  - Claude Code Agent Teams (subagent persistent context)
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("thunderbird_persona_memory")

# ============================================================================
# CONFIGURATION
# ============================================================================

PERSONA_MEMORY_ROOT = Path(os.path.expanduser("~/Thunderbird/Personas/memory"))

# Valid persona slots — the 8 active Wing personas with memory directories
VALID_PERSONA_IDS = {"COS", "EXEC", "A2", "A3", "A5", "A9", "CH", "A12"}

# Legacy ID mapping (same as thunderbird_personas.py)
_LEGACY_MAP = {
    "A4": "COS",
    "A7": "EXEC",
    "A8": "A9",
    "A11": "COS",
    "DANI": "A3",
    "DANIELLE": "A3",
    "HALE": "COS",
    "DEMBE": "A2",
    "MOREAU": "A3",
    "CASTILLO": "A5",
    "HARLAN": "A9",
    "WASHINGTON": "CH",
    "ELON": "A12",
}

# Max total characters to inject into a prompt (prevent context overflow)
MAX_INJECTION_CHARS = 8000

# ============================================================================
# HELPERS
# ============================================================================


def _resolve_persona_id(persona_id: str) -> str:
    """Resolve a persona ID, mapping legacy/name aliases to canonical slot IDs."""
    pid = persona_id.upper().strip()
    return _LEGACY_MAP.get(pid, pid)


def _get_persona_dir(persona_id: str) -> Path:
    """Get the memory directory for a persona. Creates it if needed."""
    pid = _resolve_persona_id(persona_id)
    persona_dir = PERSONA_MEMORY_ROOT / pid
    persona_dir.mkdir(parents=True, exist_ok=True)
    return persona_dir


# ============================================================================
# CORE API
# ============================================================================


def read_persona_memory(persona_id: str, filename: str = "persona_context.md") -> str:
    """Read a specific memory file from a persona's directory.

    Args:
        persona_id: Staff slot ID (e.g. 'A3', 'COS', 'Dani').
        filename: The .md file to read (default: persona_context.md).

    Returns:
        File contents as string, or empty string if not found.
    """
    pid = _resolve_persona_id(persona_id)
    persona_dir = _get_persona_dir(pid)
    filepath = persona_dir / filename

    if not filepath.exists():
        logger.debug(f"Memory file not found: {filepath}")
        return ""

    try:
        return filepath.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to read {filepath}: {e}")
        return ""


def write_persona_memory(persona_id: str, key: str, value: str) -> None:
    """Write (create or overwrite) a named memory file for a persona.

    Args:
        persona_id: Staff slot ID (e.g. 'A3', 'COS').
        key: The memory key — becomes the filename (e.g. 'client_context' -> client_context.md).
        value: The content to write.
    """
    pid = _resolve_persona_id(persona_id)
    persona_dir = _get_persona_dir(pid)

    # Sanitize key to filename
    safe_key = key.strip().replace(" ", "_").replace("/", "_")
    if not safe_key.endswith(".md"):
        safe_key += ".md"

    filepath = persona_dir / safe_key

    try:
        filepath.write_text(value, encoding="utf-8")
        logger.info(f"Wrote persona memory: {pid}/{safe_key} ({len(value)} chars)")
    except Exception as e:
        logger.error(f"Failed to write {filepath}: {e}")
        raise


def append_persona_memory(persona_id: str, entry: str) -> None:
    """Append a timestamped entry to a persona's session_notes.md.

    Args:
        persona_id: Staff slot ID (e.g. 'A3', 'COS').
        entry: The text to append.
    """
    pid = _resolve_persona_id(persona_id)
    persona_dir = _get_persona_dir(pid)
    filepath = persona_dir / "session_notes.md"

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    formatted_entry = f"\n### {timestamp}\n{entry.strip()}\n"

    try:
        # Create with header if new
        if not filepath.exists():
            header = f"# {pid} Session Notes\nRunning log of session insights, observations, and context.\n"
            filepath.write_text(header, encoding="utf-8")

        with open(filepath, "a", encoding="utf-8") as f:
            f.write(formatted_entry)

        logger.info(f"Appended to {pid}/session_notes.md ({len(entry)} chars)")
    except Exception as e:
        logger.error(f"Failed to append to {filepath}: {e}")
        raise


def get_persona_context_for_injection(persona_id: str) -> str:
    """Read ALL .md files in a persona's memory directory and format for prompt injection.

    This is the primary integration point — called before every LLM call to give
    the persona persistent context across sessions.

    Args:
        persona_id: Staff slot ID (e.g. 'A3', 'COS').

    Returns:
        Formatted string suitable for appending to a system prompt.
        Returns empty string if no files found or persona dir doesn't exist.
    """
    pid = _resolve_persona_id(persona_id)
    persona_dir = PERSONA_MEMORY_ROOT / pid

    if not persona_dir.exists():
        return ""

    # Collect all .md files, sorted: persona_context.md first, then alphabetical
    md_files = sorted(persona_dir.glob("*.md"))
    if not md_files:
        return ""

    # Prioritize: persona_context.md first, then session_notes.md, then rest
    priority_order = ["persona_context.md", "session_notes.md"]
    ordered_files = []
    remaining = []
    for f in md_files:
        if f.name in priority_order:
            ordered_files.append((priority_order.index(f.name), f))
        else:
            remaining.append(f)
    ordered_files.sort(key=lambda x: x[0])
    final_files = [f for _, f in ordered_files] + remaining

    # Build the injection block
    sections = []
    total_chars = 0

    for filepath in final_files:
        try:
            content = filepath.read_text(encoding="utf-8").strip()
            if not content:
                continue

            # Respect character budget
            if total_chars + len(content) > MAX_INJECTION_CHARS:
                remaining_budget = MAX_INJECTION_CHARS - total_chars
                if remaining_budget > 200:
                    content = content[:remaining_budget] + "\n[... truncated for context window ...]"
                else:
                    break

            sections.append(f"--- {filepath.name} ---\n{content}")
            total_chars += len(content)
        except Exception as e:
            logger.warning(f"Failed to read {filepath}: {e}")
            continue

    if not sections:
        return ""

    header = f"## Persistent Memory ({pid})\nThe following is your persistent memory from previous sessions:\n"
    return header + "\n\n".join(sections)


def list_persona_memory_files(persona_id: str) -> List[Dict[str, any]]:
    """List all memory files for a persona.

    Args:
        persona_id: Staff slot ID.

    Returns:
        List of dicts with filename, size_bytes, modified timestamp.
    """
    pid = _resolve_persona_id(persona_id)
    persona_dir = PERSONA_MEMORY_ROOT / pid

    if not persona_dir.exists():
        return []

    files = []
    for filepath in sorted(persona_dir.glob("*.md")):
        stat = filepath.stat()
        files.append({
            "filename": filepath.name,
            "size_bytes": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        })

    return files


def get_all_persona_memory_stats() -> Dict[str, any]:
    """Get memory statistics across all personas.

    Returns:
        Dict with per-persona file counts, total sizes, and overall stats.
    """
    stats = {
        "root": str(PERSONA_MEMORY_ROOT),
        "personas": {},
        "total_files": 0,
        "total_bytes": 0,
    }

    for pid in VALID_PERSONA_IDS:
        persona_dir = PERSONA_MEMORY_ROOT / pid
        if not persona_dir.exists():
            stats["personas"][pid] = {"files": 0, "bytes": 0}
            continue

        files = list(persona_dir.glob("*.md"))
        total_size = sum(f.stat().st_size for f in files)
        stats["personas"][pid] = {
            "files": len(files),
            "bytes": total_size,
            "filenames": [f.name for f in files],
        }
        stats["total_files"] += len(files)
        stats["total_bytes"] += total_size

    return stats


# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================


def register_persistent_memory_tools(mcp):
    """Register persistent persona memory tools with the MCP server.

    These complement the existing store_persona_memory/recall_persona_memory
    tools (which use JSONL) by adding file-based persistent memory that
    Claude Code Agent Teams subagents can read/write.
    """

    @mcp.tool(
        name="store_persona_memory",
        annotations={"title": "Store Persistent Persona Memory"},
    )
    async def store_persistent_memory_tool(
        persona_id: str,
        key: str,
        value: str,
    ) -> str:
        """Store a persistent memory file for a D2M staff persona.

        This creates/overwrites a named .md file in the persona's memory directory.
        Files persist across all sessions and are auto-injected into persona prompts.

        Args:
            persona_id: Staff slot (COS, EXEC, A2, A3, A5, A9, CH, A12)
            key: Memory key — becomes filename (e.g. 'client_context' -> client_context.md)
            value: Content to store

        Examples:
            store_persona_memory('A3', 'furlow_notes', 'Furlow party prefers ocean-view suites...')
            store_persona_memory('A2', 'mediterranean_intel', 'September weather risk analysis...')
        """
        write_persona_memory(persona_id, key, value)
        pid = _resolve_persona_id(persona_id)
        files = list_persona_memory_files(pid)
        import json
        return json.dumps({
            "status": "stored",
            "persona": pid,
            "key": key,
            "chars_written": len(value),
            "total_files": len(files),
        }, indent=2)

    @mcp.tool(
        name="recall_persona_memory",
        annotations={"title": "Recall Persistent Persona Memory", "readOnlyHint": True},
    )
    async def recall_persistent_memory_tool(
        persona_id: str,
        filename: str = "",
    ) -> str:
        """Recall persistent memory for a D2M staff persona.

        Without filename: returns all memory files (full context injection).
        With filename: returns that specific file.

        Args:
            persona_id: Staff slot (COS, EXEC, A2, A3, A5, A9, CH, A12)
            filename: Optional specific file to read (e.g. 'session_notes.md')

        Examples:
            recall_persona_memory('A3')  — full persistent context for Moreau
            recall_persona_memory('COS', 'session_notes.md')  — Hale's session notes
        """
        import json
        pid = _resolve_persona_id(persona_id)

        if filename:
            content = read_persona_memory(pid, filename)
            return json.dumps({
                "persona": pid,
                "filename": filename,
                "content": content,
            }, indent=2)
        else:
            context = get_persona_context_for_injection(pid)
            files = list_persona_memory_files(pid)
            return json.dumps({
                "persona": pid,
                "files": files,
                "context": context,
            }, indent=2)


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import json
    import sys

    logging.basicConfig(level=logging.INFO, format="%(name)s — %(message)s")

    if "--stats" in sys.argv:
        print(json.dumps(get_all_persona_memory_stats(), indent=2, default=str))

    elif "--list" in sys.argv:
        pid = sys.argv[sys.argv.index("--list") + 1] if len(sys.argv) > sys.argv.index("--list") + 1 else "COS"
        files = list_persona_memory_files(pid)
        print(json.dumps(files, indent=2, default=str))

    elif "--read" in sys.argv:
        idx = sys.argv.index("--read")
        pid = sys.argv[idx + 1] if len(sys.argv) > idx + 1 else "COS"
        fname = sys.argv[idx + 2] if len(sys.argv) > idx + 2 else "persona_context.md"
        content = read_persona_memory(pid, fname)
        print(content)

    elif "--inject" in sys.argv:
        pid = sys.argv[sys.argv.index("--inject") + 1] if len(sys.argv) > sys.argv.index("--inject") + 1 else "COS"
        context = get_persona_context_for_injection(pid)
        print(context)
        print(f"\n--- {len(context)} characters ---")

    elif "--test" in sys.argv:
        print("Testing persona persistent memory...\n")

        # Test write
        write_persona_memory("A3", "test_memory", "This is a test memory entry for Dani Moreau.")
        print("Wrote A3/test_memory.md")

        # Test append
        append_persona_memory("A3", "Dani noted that Furlow party wants early boarding.")
        print("Appended to A3/session_notes.md")

        # Test read
        content = read_persona_memory("A3", "test_memory.md")
        print(f"Read A3/test_memory.md: {content[:80]}...")

        # Test injection
        context = get_persona_context_for_injection("A3")
        print(f"\nInjection context for A3: {len(context)} chars")
        print(context[:500] + "..." if len(context) > 500 else context)

        # Test stats
        stats = get_all_persona_memory_stats()
        print(f"\nStats: {json.dumps(stats, indent=2, default=str)}")

        # Cleanup test file
        test_file = PERSONA_MEMORY_ROOT / "A3" / "test_memory.md"
        if test_file.exists():
            test_file.unlink()
            print("\nCleaned up test file.")

    else:
        print("Usage:")
        print("  python thunderbird_persona_memory.py --stats")
        print("  python thunderbird_persona_memory.py --list <PERSONA_ID>")
        print("  python thunderbird_persona_memory.py --read <PERSONA_ID> [filename]")
        print("  python thunderbird_persona_memory.py --inject <PERSONA_ID>")
        print("  python thunderbird_persona_memory.py --test")
