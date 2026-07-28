"""
AG Write-Back — persist AG (Antigravity/Gemini) session learnings
to the shared CC/OC memory directory.

AG (agy) calls the CLI at session end to write a memory file + update MEMORY.md
and immediately index into Qdrant for cross-session retrieval.

Usage (CLI):
    python3 core/memory/ag_memory_write.py \\
        --type feedback \\
        --slug ag_verify_flight_routing \\
        --name "AG Flight Routing Verify" \\
        --description "AG verified flight routing methodology" \\
        --body /tmp/ag_body.md
    python3 core/memory/ag_memory_write.py --body-file /tmp/body.md  # minimal
"""

from __future__ import annotations

import argparse
import fcntl
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

MEMORY_DIR = Path(
    os.environ.get(
        "AG_MEMORY_DIR",
        os.path.expanduser(
            "~/.claude/projects/-home-john-Thunderbird/memory"
        ),
    )
)
_INDEX_FILE = MEMORY_DIR / "MEMORY.md"
_TYPE_VALID = {"user", "feedback", "project", "reference"}
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,64}$")
_ERROR_LOG = Path(
    os.environ.get(
        "AG_MEMORY_ERROR_LOG",
        os.path.expanduser("~/Thunderbird/logs/ag_memory_write_errors.log"),
    )
)

_SECTIONS_BY_TYPE = {
    "user": "Standing Orders & Preferences",
    "feedback": "Recent Ops",
    "project": "Current Projects",
    "reference": "Reference",
}

_SESSION_ID = uuid.uuid4().hex[:12]


def _slugify(text: str) -> str:
    s = text.lower().strip().replace(" ", "-").replace("_", "-")
    s = re.sub(r"[^a-z0-9-]", "", s)
    return s[:64]


def _yaml_safe(val: str) -> str:
    if any(c in val for c in (":", "#", "{", "}", "[", "]", ",", "&", "*", "?", "|", "-", "<", ">", "=", "!", "%", "@", "`")):
        escaped = val.replace('"', '\\"')
        return f'"{escaped}"'
    if val != val.strip():
        escaped = val.replace('"', '\\"')
        return f'"{escaped}"'
    return val


def _ensure_dir():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    _ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)


def _write_error(msg: str):
    _ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with open(_ERROR_LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")


def _find_section_line(lines: list[str], section_header: str) -> int:
    for i, line in enumerate(lines):
        if line.strip().startswith("## ") and section_header in line:
            return i + 1
    return len(lines)


def _update_index(slug: str, name: str, description: str, mem_type: str):
    if not _INDEX_FILE.exists():
        _ensure_dir()
        _INDEX_FILE.write_text("# Thunderbird Project Memory\n*Index only*\n\n")
    try:
        with open(_INDEX_FILE, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            content = f.read()
            lines = content.split("\n") if content else []
            pointer = f"- 🤖 [{name}]({mem_type}_{slug}.md): {description}"
            if pointer in lines:
                fcntl.flock(f, fcntl.LOCK_UN)
                return
            section = _SECTIONS_BY_TYPE.get(mem_type, "Recent Ops")
            insert_at = _find_section_line(lines, section)
            if insert_at >= len(lines):
                lines.append(f"\n## {section}\n")
                lines.append(pointer)
            else:
                lines.insert(insert_at, pointer)
            f.seek(0)
            f.write("\n".join(lines))
            f.truncate()
            fcntl.flock(f, fcntl.LOCK_UN)
    except Exception as e:
        _write_error(f"_update_index failed: {e}")


def ag_write_memory(
    mem_type: str = "feedback",
    slug: str = "",
    name: str = "",
    description: str = "",
    body: str = "",
    session_id: str | None = None,
) -> dict:
    _ensure_dir()
    mem_type = mem_type.lower()
    if mem_type not in _TYPE_VALID:
        return {"ok": False, "error": f"invalid type {mem_type!r}; must be one of {_TYPE_VALID}"}

    slug = (slug or _slugify(name or "untitled")).strip()
    if not _SLUG_RE.match(slug):
        slug = _slugify(slug)
    if not _SLUG_RE.match(slug):
        return {"ok": False, "error": f"could not produce valid slug from {slug!r}"}

    name = (name or slug).strip()
    description = (description or name).strip()

    sid = session_id or _SESSION_ID
    body_text = body.strip() or f"# {name}\n\n{description}\n\n_AG write-back, session {sid}_"
    filename = f"{mem_type}_{slug}.md"
    filepath = MEMORY_DIR / filename

    frontmatter = (
        f"---\n"
        f"name: {_yaml_safe(slug)}\n"
        f"description: {_yaml_safe(description)}\n"
        f"metadata:\n"
        f"  node_type: memory\n"
        f"  type: {_yaml_safe(mem_type)}\n"
        f"  origin: ag\n"
        f"  engine: gemini\n"
        f"  originSessionId: {sid}\n"
        f"---\n\n"
    )
    full_content = frontmatter + body_text + "\n"

    try:
        old = filepath.read_text() if filepath.exists() else ""
        filepath.write_text(full_content)
    except Exception as e:
        _write_error(f"write failed for {filepath}: {e}")
        return {"ok": False, "error": str(e)}

    _update_index(slug, name, description, mem_type)

    try:
        from core.memory.qdrant_memory import QdrantMemorySystem
        qdrant = QdrantMemorySystem()
        idx = qdrant.embed_new_memory(str(filepath))
    except Exception as e:
        _write_error(f"Qdrant indexing failed for {filepath}: {e}")
        idx = {"error": str(e)}

    return {
        "ok": True,
        "path": str(filepath),
        "filename": filename,
        "slug": slug,
        "type": mem_type,
        "qdrant_index": idx,
        "was_overwrite": bool(old),
    }


def main():
    ap = argparse.ArgumentParser(
        description="Write a memory file from AG to the shared CC/OC memory directory."
    )
    ap.add_argument("--type", default="feedback", choices=sorted(_TYPE_VALID),
                    help="Memory type (user/feedback/project/reference)")
    ap.add_argument("--slug", default="",
                    help="kebab-case slug for the filename (auto-derived from --name if omitted)")
    ap.add_argument("--name", default="",
                    help="Human-readable short name")
    ap.add_argument("--description", default="",
                    help="One-line description for MEMORY.md index")
    ap.add_argument("--body", default="",
                    help="Markdown body content (inline)")
    ap.add_argument("--body-file", default="",
                    help="Path to file containing markdown body content")
    ap.add_argument("--session-id", default="",
                    help="Optional session UUID (auto-generated if omitted)")
    a = ap.parse_args()

    body = a.body
    if a.body_file:
        try:
            body = Path(a.body_file).read_text(errors="replace")
        except Exception as e:
            print(f"Error reading body file {a.body_file}: {e}", file=sys.stderr)
            sys.exit(1)

    result = ag_write_memory(
        mem_type=a.type,
        slug=a.slug,
        name=a.name,
        description=a.description,
        body=body,
        session_id=a.session_id or None,
    )

    import json
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
