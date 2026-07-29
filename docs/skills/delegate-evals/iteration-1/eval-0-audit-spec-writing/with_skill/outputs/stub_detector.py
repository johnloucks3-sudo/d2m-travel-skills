#!/usr/bin/env python3
"""
Mechanical stub / real-implementation classifier for ONE Python file.

Ground-truth tool for the timer-script audit. OC runs this per manifest
entry and cites its output as evidence -- it does not narrate a verdict
from memory. CC re-runs it during verification and diffs the result
against what OC reported.

Usage: python3 stub_detector.py <path>
Always prints one JSON object to stdout, even for a missing/unreadable/
unparsable file -- that is reported as data (verdict MISSING /
UNREADABLE / SYNTAX_ERROR), never as a crash, so a bad path can't kill
the batch run.
"""
import ast
import json
import os
import sys

IO_MARKERS = [
    "open(", "subprocess.", "requests.", "smtplib", "urlopen", "os.system",
    "socket.", "sqlite3.", "psycopg2", ".execute(", "gspread", "google.auth",
    "systemctl", "send_message", "send_email", "gmail", "Popen(", "mcp__",
    "playwright", "httpx.", "aiohttp", "write_text(", "read_text(",
    "json.dump(", "json.load(", ".post(", "write_bytes(", "shutil.",
    "Path(", "os.rename(", "os.remove(", "yaml.safe_load(", "yaml.dump(",
]
TODO_MARKERS = ("TODO", "FIXME", "XXX", "not implemented", "NotImplementedError")


def _is_docstring(stmt):
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(getattr(stmt, "value", None), ast.Constant)
        and isinstance(stmt.value.value, str)
    )


def _body_is_stub(body):
    b = body[1:] if body and _is_docstring(body[0]) else body
    if not b:
        return True
    if len(b) == 1:
        stmt = b[0]
        if isinstance(stmt, ast.Pass):
            return True
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is Ellipsis:
            return True
        if isinstance(stmt, ast.Raise):
            exc = stmt.exc
            name = getattr(exc, "id", None) or getattr(getattr(exc, "func", None), "id", None)
            if name == "NotImplementedError":
                return True
    return False


def classify(path):
    if not os.path.isfile(path):
        return {"script_path": path, "verdict": "MISSING", "reason": "file does not exist"}
    try:
        src = open(path, "r", encoding="utf-8", errors="replace").read()
    except Exception as e:
        return {"script_path": path, "verdict": "UNREADABLE", "reason": str(e)}
    try:
        tree = ast.parse(src, filename=path)
    except SyntaxError as e:
        return {"script_path": path, "verdict": "SYNTAX_ERROR", "reason": str(e), "line": e.lineno}

    lines = src.splitlines()
    total_lines = len(lines)

    funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    stub_funcs = [f.name for f in funcs if _body_is_stub(f.body)]
    real_funcs = [f.name for f in funcs if f.name not in stub_funcs]

    io_hits = [(i + 1, m) for i, line in enumerate(lines) for m in IO_MARKERS if m in line]
    todo_hits = [(i + 1, line.strip()) for i, line in enumerate(lines) if any(t in line for t in TODO_MARKERS)]
    has_main_guard = "__main__" in src

    if funcs and len(stub_funcs) == len(funcs) and not io_hits:
        verdict = "STUB"
    elif not funcs and not io_hits and total_lines < 15:
        verdict = "STUB"
    elif io_hits and stub_funcs and len(stub_funcs) >= len(real_funcs):
        verdict = "PARTIAL_STUB"
    elif io_hits:
        verdict = "REAL_IMPLEMENTATION"
    else:
        verdict = "PARTIAL_STUB"

    return {
        "script_path": path,
        "verdict": verdict,
        "total_lines": total_lines,
        "function_count": len(funcs),
        "stub_function_names": stub_funcs,
        "real_function_names": real_funcs,
        "io_evidence": io_hits[:10],
        "todo_evidence": todo_hits[:10],
        "has_main_guard": has_main_guard,
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: stub_detector.py <path>"}))
        sys.exit(2)
    print(json.dumps(classify(sys.argv[1]), indent=2))
