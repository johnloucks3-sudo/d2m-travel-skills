#!/usr/bin/env python3
"""
MCP Tool Catalog Generator — Dreams2Memories Travel, LLC

Statically scans the Thunderbird MCP tool surface (every `@mcp.tool()` /
`@mcp_server.tool()` / `@server.tool()` decorated function reachable from the
live server's PYTHONPATH) via the `ast` module — no imports, no runtime deps,
safe to run even if optional packages (googleapiclient, playwright, ...) are
missing. Writes:

  docs/mcp_tool_catalog.json     — full structured catalog (source of truth)
  docs/MCP_TOOL_CATALOG.md       — human-readable reference, grouped by module
  docs/MCP_QUICK_START_GUIDE.md  — top-5 most-referenced tools w/ copy-paste JSON

Usage:
    python3 core/mcp/mcp_catalog_generator.py
"""

import ast
import json
import re
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parents[2]

# Mirrors PYTHONPATH in mcp_launcher_core.sh — these are the directories the
# live MCP server (travel_mcp_server.py) resolves bare `from thunderbird_x import y`
# against. Only files directly inside these dirs are actually reachable tools.
SOURCE_DIRS = [
    REPO_ROOT,
    REPO_ROOT / "core/intel",
    REPO_ROOT / "core/email",
    REPO_ROOT / "core/booking",
    REPO_ROOT / "core/travel",
    REPO_ROOT / "core/communication",
    REPO_ROOT / "core/ai_infra",
    REPO_ROOT / "core/client",
    REPO_ROOT / "core/ops",
    REPO_ROOT / "core/scheduling",
    REPO_ROOT / "core/watchtower",
    REPO_ROOT / "core/learning",
    REPO_ROOT / "core/mcp",
    REPO_ROOT / "core/memory",
    REPO_ROOT / "api",
    REPO_ROOT / "agents",
    REPO_ROOT / "ops",
    REPO_ROOT / "business",
    REPO_ROOT / "comms",
    REPO_ROOT / "itinerary",
    REPO_ROOT / "intel",
]

EXCLUDE_NAME_PREFIXES = ("test_", "_")
OUT_JSON = REPO_ROOT / "docs/mcp_tool_catalog.json"
OUT_CATALOG_MD = REPO_ROOT / "docs/MCP_TOOL_CATALOG.md"
OUT_QUICKSTART_MD = REPO_ROOT / "docs/MCP_QUICK_START_GUIDE.md"

EXAMPLE_RE = re.compile(r"""e\.g\.,?\s*['"]([^'"]+)['"]""")


def discover_py_files():
    """Only files directly inside a PYTHONPATH dir (no recursion — matches import resolution)."""
    seen = set()
    files = []
    for d in SOURCE_DIRS:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.py")):
            if f.name.startswith(EXCLUDE_NAME_PREFIXES):
                continue
            rp = f.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            files.append(f)
    return files


def _is_tool_decorator(dec) -> bool:
    """Matches @mcp.tool, @mcp.tool(...), @mcp_server.tool, @server.tool, etc."""
    node = dec.func if isinstance(dec, ast.Call) else dec
    return isinstance(node, ast.Attribute) and node.attr == "tool"


def _literal(node):
    """Best-effort literal eval; falls back to unparsed source text."""
    if node is None:
        return None
    try:
        return ast.literal_eval(node)
    except Exception:
        try:
            return ast.unparse(node)
        except Exception:
            return None


def _parse_field_default(call: ast.Call):
    """Parse a pydantic Field(...) default expression -> (required, default, description)."""
    description = None
    for kw in call.keywords:
        if kw.arg == "description":
            description = _literal(kw.value)

    positional = call.args[0] if call.args else None
    default_kw = next((kw.value for kw in call.keywords if kw.arg == "default"), None)
    default_node = positional if positional is not None else default_kw

    if default_node is None:
        required = not any(kw.arg == "default" for kw in call.keywords)
    elif isinstance(default_node, ast.Constant) and default_node.value is Ellipsis:
        required = True
        default_node = None
    else:
        required = False

    default_value = _literal(default_node) if not required else None
    return required, default_value, description


def _parse_params(fn: ast.AsyncFunctionDef | ast.FunctionDef):
    args = fn.args
    positional = [a for a in args.args if a.arg not in ("self", "cls")]
    defaults = list(args.defaults)
    pad = len(positional) - len(defaults)
    aligned = [None] * pad + defaults

    params = []
    for arg, default_node in zip(positional, aligned):
        type_str = ast.unparse(arg.annotation) if arg.annotation else "Any"
        description = None
        default_value = None

        if default_node is None:
            required = True
        elif isinstance(default_node, ast.Call) and (
            (isinstance(default_node.func, ast.Name) and default_node.func.id == "Field")
            or (isinstance(default_node.func, ast.Attribute) and default_node.func.attr == "Field")
        ):
            required, default_value, description = _parse_field_default(default_node)
        else:
            required = False
            default_value = _literal(default_node)

        params.append({
            "name": arg.arg,
            "type": type_str,
            "required": required,
            "default": default_value,
            "description": description,
        })

    # keyword-only args (rare, but handle for completeness)
    for arg, default_node in zip(args.kwonlyargs, args.kw_defaults):
        type_str = ast.unparse(arg.annotation) if arg.annotation else "Any"
        if default_node is None:
            params.append({"name": arg.arg, "type": type_str, "required": True,
                            "default": None, "description": None})
        elif isinstance(default_node, ast.Call) and (
            (isinstance(default_node.func, ast.Name) and default_node.func.id == "Field")
            or (isinstance(default_node.func, ast.Attribute) and default_node.func.attr == "Field")
        ):
            required, default_value, description = _parse_field_default(default_node)
            params.append({"name": arg.arg, "type": type_str, "required": required,
                            "default": default_value, "description": description})
        else:
            params.append({"name": arg.arg, "type": type_str, "required": False,
                            "default": _literal(default_node), "description": None})

    return params


def _decorator_name_and_annotations(dec):
    name = None
    annotations = {}
    if isinstance(dec, ast.Call):
        for kw in dec.keywords:
            if kw.arg == "name":
                name = _literal(kw.value)
            elif kw.arg == "annotations" and isinstance(kw.value, ast.Dict):
                for k, v in zip(kw.value.keys, kw.value.values):
                    key = _literal(k)
                    if key is not None:
                        annotations[key] = _literal(v)
    return name, annotations


def parse_tool_defs(py_file: Path):
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    except (SyntaxError, UnicodeDecodeError):
        return []

    rel = py_file.relative_to(REPO_ROOT)
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        tool_decs = [d for d in node.decorator_list if _is_tool_decorator(d)]
        if not tool_decs:
            continue
        dec = tool_decs[0]
        explicit_name, annotations = _decorator_name_and_annotations(dec)
        tool_name = explicit_name or node.name
        docstring = ast.get_docstring(node) or ""
        found.append({
            "name": tool_name,
            "module": str(rel),
            "function": node.name,
            "description": docstring.strip().split("\n")[0] if docstring else "",
            "full_description": docstring.strip(),
            "annotations": annotations,
            "parameters": _parse_params(node),
        })
    return found


def build_catalog():
    """Returns (catalog: {tool_name: record}, conflicts: [(name, file1, file2)])"""
    catalog = {}
    conflicts = []
    for f in discover_py_files():
        for rec in parse_tool_defs(f):
            name = rec["name"]
            if name in catalog and catalog[name]["module"] != rec["module"]:
                conflicts.append((name, catalog[name]["module"], rec["module"]))
                continue  # first-seen wins (SOURCE_DIRS order == PYTHONPATH precedence)
            catalog.setdefault(name, rec)
    return catalog, conflicts


# ---------------------------------------------------------------------------
# Example JSON generation
# ---------------------------------------------------------------------------

def _placeholder_for(param):
    t = param["type"]
    desc = param.get("description") or ""
    m = EXAMPLE_RE.search(desc)
    if m:
        return m.group(1)
    if param["default"] is not None and not param["required"]:
        return param["default"]
    tl = t.lower()
    if "bool" in tl:
        return True
    if "int" in tl:
        return 1
    if "float" in tl:
        return 1.0
    if "list" in tl:
        return []
    if "dict" in tl:
        return {}
    return f"<{param['name']}>"


def generate_example(tool: dict) -> dict:
    """Ready-to-copy JSON args for a tool — required params always present."""
    example = {}
    for p in tool["parameters"]:
        if p["required"] or p["default"] not in (None, ""):
            example[p["name"]] = _placeholder_for(p)
    return example


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

def _params_table(params):
    if not params:
        return "_No parameters._\n"
    lines = ["| Parameter | Type | Required | Default | Description |",
             "|---|---|---|---|---|"]
    for p in params:
        default = "" if p["default"] is None else str(p["default"])
        desc = (p["description"] or "").replace("|", "\\|")
        lines.append(f"| `{p['name']}` | `{p['type']}` | "
                      f"{'✅' if p['required'] else ''} | {default} | {desc} |")
    return "\n".join(lines) + "\n"


def render_catalog_md(catalog: dict, conflicts: list) -> str:
    by_module = defaultdict(list)
    for rec in catalog.values():
        by_module[rec["module"]].append(rec)

    lines = [
        "# MCP Tool Catalog",
        "*Auto-generated by `core/mcp/mcp_catalog_generator.py` — do not hand-edit. "
        "Regenerated weekly via `mcp-catalog-refresh.timer`.*",
        "",
        f"**{len(catalog)} tools** across **{len(by_module)} modules**.",
        "",
        "Machine-readable form: `docs/mcp_tool_catalog.json`. "
        "Quick-start (5 most-referenced tools): `docs/MCP_QUICK_START_GUIDE.md`.",
        "",
    ]
    if conflicts:
        lines.append(f"> ⚠️ {len(conflicts)} duplicate tool name(s) found across modules "
                      "(first module in PYTHONPATH order wins — see JSON `_conflicts`).")
        lines.append("")

    lines.append("## Index")
    for module in sorted(by_module):
        anchor = module.replace("/", "").replace(".", "").replace("_", "-").lower()
        lines.append(f"- [{module}](#{anchor}) ({len(by_module[module])} tools)")
    lines.append("")

    for module in sorted(by_module):
        lines.append(f"## {module}")
        lines.append("")
        for rec in sorted(by_module[module], key=lambda r: r["name"]):
            lines.append(f"### `{rec['name']}`")
            if rec["description"]:
                lines.append(f"{rec['description']}")
            lines.append("")
            lines.append(_params_table(rec["parameters"]))
            example = generate_example(rec)
            lines.append("**Example call:**")
            lines.append("```json")
            lines.append(json.dumps({"tool": rec["name"], "arguments": example}, indent=2))
            lines.append("```")
            lines.append("")
    return "\n".join(lines)


def _usage_counts(catalog: dict) -> dict:
    """Rank tools by how often their name string is referenced elsewhere in the repo
    (skills, scripts, docs) — a mechanical proxy for 'most-used', not fabricated."""
    counts = {}
    skip_dirs = {".venv", "node_modules", "__pycache__", ".git"}
    all_text = []
    for path in REPO_ROOT.rglob("*"):
        if path.is_dir() or path.suffix not in (".py", ".md", ".json"):
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        if path in (OUT_JSON, OUT_CATALOG_MD, OUT_QUICKSTART_MD):
            continue
        try:
            all_text.append(path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
    blob = "\n".join(all_text)
    for name in catalog:
        counts[name] = len(re.findall(r"\b" + re.escape(name) + r"\b", blob))
    return counts


def render_quickstart_md(catalog: dict) -> str:
    counts = _usage_counts(catalog)
    top5 = sorted(catalog, key=lambda n: counts.get(n, 0), reverse=True)[:5]

    lines = [
        "# MCP Quick-Start Guide",
        "*Auto-generated by `core/mcp/mcp_catalog_generator.py`. "
        "5 most-referenced tools in the codebase, ranked by literal name occurrence "
        "count (mechanical proxy for usage frequency) — not a hand-picked list.*",
        "",
        "Full reference: `docs/MCP_TOOL_CATALOG.md` · Machine-readable: `docs/mcp_tool_catalog.json`",
        "",
    ]
    for name in top5:
        rec = catalog[name]
        lines.append(f"## `{name}` ({counts.get(name, 0)} references)")
        if rec["description"]:
            lines.append(rec["description"])
        lines.append("")
        lines.append(f"Module: `{rec['module']}`")
        lines.append("")
        lines.append(_params_table(rec["parameters"]))
        lines.append("**Copy-paste:**")
        lines.append("```json")
        lines.append(json.dumps({"tool": name, "arguments": generate_example(rec)}, indent=2))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def generate():
    catalog, conflicts = build_catalog()

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    json_payload = {
        "_generated_by": "core/mcp/mcp_catalog_generator.py",
        "_tool_count": len(catalog),
        "_conflicts": [{"name": n, "kept": a, "shadowed": b} for n, a, b in conflicts],
        "tools": catalog,
    }
    OUT_JSON.write_text(json.dumps(json_payload, indent=2, default=str))
    OUT_CATALOG_MD.write_text(render_catalog_md(catalog, conflicts))
    OUT_QUICKSTART_MD.write_text(render_quickstart_md(catalog))

    return catalog, conflicts


if __name__ == "__main__":
    catalog, conflicts = generate()
    print(f"Scanned {len(discover_py_files())} files → {len(catalog)} tools "
          f"({len(conflicts)} name conflicts)")
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_CATALOG_MD}")
    print(f"Wrote {OUT_QUICKSTART_MD}")
