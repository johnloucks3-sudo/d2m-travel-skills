"""Claude Usage Collector — reads Claude Code session JSONL files into SQLite.
Supports two formats:
  1. ~/.claude/projects/*/<uuid>.jsonl — Claude session logs with message.usage fields
  2. ~/.claude/projects/*/usage_*.jsonl  — Claude Code --output-usage format (future)
"""
import json, sqlite3, glob, os, time, re
from pathlib import Path

DB = Path.home() / "Thunderbird" / "storage" / "ai_costs.db"
STATE = Path.home() / "Thunderbird" / "storage" / ".collector_state.json"
CLAUDE_HOME = Path.home() / ".claude"
UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.jsonl$')

# Effective token weights per model (from Opus plan)
WEIGHTS = {
    "claude-opus-4-7":       {"in": 5.0, "out": 5.0, "cr": 0.5, "cc": 6.25},
    "claude-sonnet-4-6":     {"in": 1.0, "out": 1.0, "cr": 0.1, "cc": 1.25},
    "claude-haiku-4-5":      {"in": 0.25, "out": 0.25, "cr": 0.025, "cc": 0.31},
}


def _load_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"file_offsets": {}, "files_seen": []}


def _save_state(s):
    STATE.write_text(json.dumps(s, indent=2))


def _compute_effective(model, inp, out, cr, cc):
    w = WEIGHTS.get(model, {"in": 1.0, "out": 1.0, "cr": 0.1, "cc": 1.25})
    return int(inp * w["in"] + out * w["out"] + cr * w["cr"] + cc * w["cc"])


def _extract_usage_from_event(rec):
    """Extract usage from a single line of a session JSONL file.
    Returns dict with keys or None."""
    if rec.get("type") != "assistant":
        return None
    msg = rec.get("message") or {}
    usage = msg.get("usage") if isinstance(msg, dict) else None
    if not usage or not isinstance(usage, dict):
        return None
    inp = usage.get("input_tokens", 0) or 0
    out = usage.get("output_tokens", 0) or 0
    cr = usage.get("cache_read_input_tokens", 0) or 0
    cc = usage.get("cache_creation_input_tokens", 0) or 0
    if inp == 0 and out == 0 and cr == 0 and cc == 0:
        return None
    model = rec.get("advisorModel", "unknown")
    session_id = rec.get("sessionId", "")
    ts = rec.get("timestamp", "")
    return {
        "session_id": session_id,
        "ts": ts,
        "model": model,
        "input_tokens": inp,
        "output_tokens": out,
        "cache_read_tokens": cr,
        "cache_create_tokens": cc,
    }


def collect():
    state = _load_state()
    conn = sqlite3.connect(str(DB), timeout=10)
    conn.execute("PRAGMA busy_timeout=10000")
    new_rows = 0

    # Find session files: headless sessions in -home-john project (fast),
    # plus any usage_*.jsonl across all projects (future --output-usage flag).
    # Skip files > 5MB to avoid processing giant sessions.
    MAX_BYTES = 5 * 1024 * 1024
    # Primary source: headless dispatch sessions
    session_files = glob.glob(str(CLAUDE_HOME / "projects" / "-home-john" / "*.jsonl"))
    # Secondary source: dediated usage files (--output-usage flag output)
    session_files += glob.glob(str(CLAUDE_HOME / "projects" / "*" / "usage_*.jsonl"))
    session_files = [
        f for f in session_files
        if "/subagents/" not in f
        and os.path.getsize(f) <= MAX_BYTES
    ]

    for fpath in sorted(set(session_files)):
        fpath_s = str(fpath)
        basename = os.path.basename(fpath_s)

        offset = state["file_offsets"].get(fpath_s, 0)
        try:
            with open(fpath) as f:
                f.seek(offset)
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    extracted = _extract_usage_from_event(rec)
                    if extracted is None:
                        continue
                    eff = _compute_effective(
                        extracted["model"],
                        extracted["input_tokens"],
                        extracted["output_tokens"],
                        extracted["cache_read_tokens"],
                        extracted["cache_create_tokens"],
                    )
                    try:
                        conn.execute("""
                            INSERT OR IGNORE INTO claude_events
                            (session_id, ts_start, ts_end, model, input_tokens, output_tokens,
                             cache_read_tokens, cache_create_tokens, effective_tokens, source_file)
                            VALUES (?,?,?,?,?,?,?,?,?,?)
                        """, (
                            extracted["session_id"],
                            extracted["ts"],
                            extracted["ts"],
                            extracted["model"],
                            extracted["input_tokens"],
                            extracted["output_tokens"],
                            extracted["cache_read_tokens"],
                            extracted["cache_create_tokens"],
                            eff,
                            fpath_s,
                        ))
                        conn.commit()
                        new_rows += 1
                    except Exception:
                        conn.rollback()
                offset = f.tell()
        except (FileNotFoundError, PermissionError):
            continue
        state["file_offsets"][fpath_s] = offset

    _save_state(state)
    conn.close()
    return new_rows


if __name__ == "__main__":
    n = collect()
    print(json.dumps({
        "collected": n,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "note": "collects from ~/.claude/projects/*/<uuid>.jsonl. For future sessions, pass --output-usage to claude for dedicated usage files." if n == 0 else None,
    }))
