#!/usr/bin/env python3
"""
a7_model_audit_gate.py — A7 Sterling OpenCode Model Discipline Gate
====================================================================
Detects "impostor" or banned AI models in OpenCode session history (last 24h).
Intended use: run as a pre-commit hook step, in CI, or on-demand audit.

Usage:
    python3 OpsCenter/a7_model_audit_gate.py              # Gate mode: exits 1 on RED
    python3 OpsCenter/a7_model_audit_gate.py --report-only # Info mode: always exits 0

Install as pre-commit hook step (chain with existing a7_pre_commit_gate.py):
    # In .git/hooks/pre-commit, add after existing gate:
    python3 /home/john/Thunderbird/OpsCenter/a7_model_audit_gate.py
    # (chmod +x is already set by the install note below)

Approved model stack (SO 2026-05-04 / .opencode.json):
    - opencode/big-pickle                                   ($0 native)
    - opencode/deepseek-v4-flash-free                       ($0 native, variant=default ONLY)
    - google/gemini-2.5-flash                               (flat-fee, approved)
    - openrouter/nvidia/nemotron-3-super-120b-a12b:free     ($0 OR free tier)

THREE INDEPENDENT RED TRIGGERS:
    1. providerID=="openrouter" AND aggregate 24h cost > $0.10
       Catches paid OR models drifting in without explicit approval.
       Cost is AGGREGATE across all sessions for each (providerID, model_id) pair.

    2. variant=="high" on any free/native base model
       Reasoning surcharge fires even on $0-base models.
       Example: deepseek-v4-flash-free[high] = $3.74 per session (confirmed).

    3. Explicit banned model list (any session cost > $0)
       Hard names from prior cost audits. Any cost = RED regardless of amount.
       Canonical list lives in harlan_cost_monitor.py BANNED_PAID — keep in sync.

YELLOW: advisory only, commit not blocked.
GREEN: all models compliant.

DB-missing: YELLOW + exit 0 (fail-open — don't block commits when audit
tool itself is unavailable).

CANONICAL BANNED LIST: OpsCenter/harlan_cost_monitor.py (BANNED_PAID set).
Owner: A7 Sterling / A9 Harlan. Both lists MUST stay in sync.
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
DB_PATH = Path.home() / ".local" / "share" / "opencode" / "opencode.db"
WINDOW_HOURS = 24

# ── Thresholds ─────────────────────────────────────────────────────────────────
# Trigger 1: OpenRouter aggregate cost exceeding this in 24h = RED
OR_COST_THRESHOLD_24H = 0.10  # $0.10 USD

# Weekly budget baseline: approved stack is $0 native + flat-fee Gemini.
# Tolerance for incidental probes: $0.50/week. Used by dashboard; documented here.
WEEKLY_BUDGET_TOLERANCE = 0.50

# ── Approved model IDs (bare, no provider prefix) ─────────────────────────────
# If a model isn't in this list AND isn't banned, it gets a YELLOW advisory.
APPROVED_BARE_IDS = {
    "big-pickle",
    "deepseek-v4-flash-free",
    "gemini-2.5-flash",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nemotron-3-super-120b-a12b:free",
}

# ── KNOWN MODEL CATALOG — existence gate (added 2026-06-15, MISSION-267) ──────
# WHY: Four fabricated model IDs shipped historically because the gate only checked
# COST APPROVAL, never EXISTENCE — a configured model ID was trusted to be real:
#   qwen3.6-plus-04-02 · gemini-3.1-flash-lite-preview-20260303 · gemini-flash-2.5-lite
# (plus the OpenRouter-routed variants). Cost approval alone is theater if the ID
# doesn't resolve to a real, live model. This catalog is the source of truth: any
# model ID configured in the router / safeguards MUST resolve here (exact or via a
# documented retired marker) or the gate fails RED in --check-config mode.
#
# Maintenance: when a real model is adopted, add its canonical ID here. Retired
# providers leave a "RETIRED-*" marker which is explicitly allowed (decommissioned,
# not fabricated). Owner: A7 Sterling. Sync new live IDs with gemini_client/.env.
KNOWN_MODEL_CATALOG = {
    # Anthropic (native, via MAX OAuth / Claude CLI)
    "claude-opus-4-7", "claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5-20251001",
    # Google direct (gemini_client — GEMINI_API_KEY). These are the LIVE Gemini IDs.
    "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite",
    # OpenCode native ($0)
    "big-pickle", "deepseek-v4-flash-free",
    # xAI canonical (reference only — no live transport post-OpenRouter retirement)
    "x-ai/grok-4.3",
}

# Allowed non-resolving markers: deliberately retired IDs are NOT fabrications.
# A configured ID matching one of these prefixes passes the existence gate.
RETIRED_MARKER_PREFIXES = ("RETIRED-",)

# Known-fabricated IDs that must NEVER resolve — kept as an explicit denylist so a
# regression that re-introduces one fails RED with a clear message (not a silent pass).
FABRICATED_MODEL_IDS = {
    "qwen3.6-plus-04-02",
    "qwen/qwen3.6-plus-04-02:free",
    "gemini-3.1-flash-lite-preview-20260303",
    "google/gemini-3.1-flash-lite-preview-20260303",
    "gemini-3.1-flash-lite-preview",
    "gemini-flash-2.5-lite",
    "google/gemini-flash-2.5-lite:free",
}


# ── Banned model list — MIRROR of harlan_cost_monitor.py BANNED_PAID ──────────
# Keep synchronized. Add to BOTH files when a new model is banned.
# Owner: A7 Sterling / A9 Harlan.
BANNED_MODELS = {
    # Confirmed cost surprises from prior audits:
    "x-ai/grok-4.1-fast",
    "openai/gpt-4o-mini",
    "openai/gpt-4.1-mini",
    "google/gemini-3.1-flash-lite-preview",
    "gemini-3.1-flash-lite-preview",       # short form in DB
    "deepseek/deepseek-chat-v3.1",
    # Additional paid models never approved for OpenCode:
    "anthropic/claude-3-haiku",
    "anthropic/claude-3.5-haiku",
    "openai/gpt-4o",
    "openai/gpt-5",
    "gpt-5",
}


# ── ANSI color helpers (suppressed when not a tty) ────────────────────────────
def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if sys.stdout.isatty() else text


def RED(t: str) -> str:
    return _c("31;1", t)


def YEL(t: str) -> str:
    return _c("33;1", t)


def GRN(t: str) -> str:
    return _c("32;1", t)


# ── Model parsing ──────────────────────────────────────────────────────────────
def _parse_model(raw: str) -> dict:
    """
    Parse the JSON 'model' column from opencode.db.

    Returns normalized fields:
      model_id   — raw id from JSON (e.g. "deepseek-v4-flash-free")
      bare_id    — model_id with provider prefix stripped if redundant
      provider_id — providerID field (e.g. "opencode", "openrouter")
      variant    — variant field (e.g. "default", "high")
      display    — human-readable label for reports
    """
    try:
        m = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        raw_s = str(raw)
        return {
            "model_id": raw_s,
            "bare_id": raw_s,
            "provider_id": "unknown",
            "variant": "default",
            "display": raw_s,
        }

    model_id = m.get("id", "unknown")
    provider_id = m.get("providerID", "unknown")
    variant = m.get("variant") or "default"

    # Normalize: strip leading provider prefix from model_id when it duplicates
    # the providerID (e.g. opencode.id="opencode/big-pickle" -> bare_id="big-pickle")
    bare_id = model_id
    if "/" in model_id:
        head, tail = model_id.split("/", 1)
        if head == provider_id:
            bare_id = tail

    display = model_id
    if variant and variant not in ("default", ""):
        display += f" [{variant}]"

    return {
        "model_id": model_id,
        "bare_id": bare_id,
        "provider_id": provider_id,
        "variant": variant,
        "display": display,
    }


def _is_banned(m: dict) -> bool:
    """Check all name forms against the banned set."""
    return (
        m["model_id"] in BANNED_MODELS
        or m["bare_id"] in BANNED_MODELS
    )


def _is_free_base(m: dict) -> bool:
    """
    True if the model's BASE rate is $0 before variant surcharges.
      - opencode native provider: always $0 base
      - Any model id ending in :free: $0 base (OpenRouter free tier)
    Note: google/gemini-2.5-flash is flat-fee approved, NOT free-base.
    """
    if m["provider_id"] == "opencode":
        return True
    if m["model_id"].endswith(":free") or m["bare_id"].endswith(":free"):
        return True
    return False


def _is_approved(m: dict) -> bool:
    """True if model is in the explicit approved list."""
    return m["bare_id"] in APPROVED_BARE_IDS or m["model_id"] in APPROVED_BARE_IDS


# ── DB query ───────────────────────────────────────────────────────────────────
def query_24h_sessions() -> list[dict]:
    """
    Return per-(providerID, model_id) aggregate stats for the last 24 hours.

    Aggregation: SUM(cost), COUNT(*), SUM(tokens_input), SUM(tokens_output)
    grouped by the raw 'model' JSON string. This matches Harlan's methodology
    in harlan_cost_monitor.py and produces provider-level cost accountability.
    """
    if not DB_PATH.exists():
        return []

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    cutoff_ms = int(
        (datetime.now(timezone.utc) - timedelta(hours=WINDOW_HOURS)).timestamp() * 1000
    )

    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            rows = conn.execute(
                """
                SELECT model,
                       COALESCE(SUM(cost), 0.0)          AS total_cost,
                       COUNT(*)                           AS session_count,
                       COALESCE(SUM(tokens_input), 0)    AS total_tok_in,
                       COALESCE(SUM(tokens_output), 0)   AS total_tok_out
                FROM session
                WHERE time_created >= ? AND time_created < ?
                  AND model IS NOT NULL
                GROUP BY model
                ORDER BY total_cost DESC
                """,
                (cutoff_ms, now_ms),
            ).fetchall()
    except sqlite3.Error as e:
        print(f"[A7-GATE] DB error: {e}", file=sys.stderr)
        return []

    results = []
    for raw_model, total_cost, session_count, tok_in, tok_out in rows:
        m = _parse_model(raw_model)
        results.append({
            **m,
            "total_cost": round(float(total_cost), 6),
            "session_count": int(session_count),
            "tok_in": int(tok_in),
            "tok_out": int(tok_out),
        })
    return results


# ── Three-trigger evaluation ───────────────────────────────────────────────────
def evaluate(sessions: list[dict]) -> dict:
    """
    Apply the three RED triggers and collect YELLOW advisories.

    Returns:
        reds:    list of {trigger, model, detail} — each is a RED finding
        yellows: list of str advisory messages
        clean:   list of session dicts with no flags
    """
    reds = []
    yellows = []
    clean = []

    for s in sessions:
        session_reds = []

        # ── TRIGGER 1: OpenRouter + aggregate 24h cost > threshold ────────────
        if s["provider_id"] == "openrouter" and s["total_cost"] > OR_COST_THRESHOLD_24H:
            session_reds.append({
                "trigger": "OPENROUTER_COST",
                "model": s,
                "detail": (
                    f"OpenRouter '{s['display']}' billed ${s['total_cost']:.4f} "
                    f"in 24h across {s['session_count']} session(s). "
                    f"Threshold: ${OR_COST_THRESHOLD_24H:.2f}. "
                    f"Replace with native or approved free-tier model."
                ),
            })

        # ── TRIGGER 2: variant=high on free-base model (reasoning surcharge) ──
        if s["variant"] == "high" and _is_free_base(s):
            if s["total_cost"] > 0.001:
                session_reds.append({
                    "trigger": "HIGH_VARIANT_SURCHARGE",
                    "model": s,
                    "detail": (
                        f"Free-base model '{s['display']}' (variant=high) "
                        f"incurred reasoning surcharge: ${s['total_cost']:.4f} "
                        f"({s['tok_in']:,} input tokens, "
                        f"{s['session_count']} session(s)). "
                        f"Switch to variant=default for routine ops tasks."
                    ),
                })
            else:
                yellows.append(
                    f"ADVISORY: '{s['display']}' using variant=high — reasoning "
                    f"surcharge risk. No material cost yet this window."
                )

        # ── TRIGGER 3: Explicit banned model, any cost > $0 ───────────────────
        if _is_banned(s) and s["total_cost"] > 0:
            session_reds.append({
                "trigger": "BANNED_MODEL",
                "model": s,
                "detail": (
                    f"BANNED model '{s['display']}' billed ${s['total_cost']:.4f} "
                    f"({s['session_count']} session(s), {s['tok_in']:,} input tokens). "
                    f"Banned per A7/A9 cost audit. "
                    f"Canonical list: harlan_cost_monitor.py BANNED_PAID."
                ),
            })

        # ── YELLOW: unapproved model with no cost (soft advisory) ─────────────
        if not session_reds and not _is_approved(s) and not _is_banned(s):
            if s["total_cost"] == 0:
                yellows.append(
                    f"UNAPPROVED MODEL (no cost): '{s['display']}' not in approved "
                    f"stack. Monitor — variant drift may incur cost."
                )
            else:
                yellows.append(
                    f"UNAPPROVED MODEL: '{s['display']}' billed ${s['total_cost']:.4f}. "
                    f"Not in approved model stack. Review and add to approved list "
                    f"or ban list."
                )

        # ── YELLOW: context bloat on free models ───────────────────────────────
        if not session_reds and s["total_cost"] == 0 and s["tok_in"] > 2_000_000:
            avg_in = s["tok_in"] // max(s["session_count"], 1)
            yellows.append(
                f"CONTEXT BLOAT: '{s['display']}' avg {avg_in:,} input tokens/session "
                f"({s['session_count']} sessions). No cost now — watch for "
                f"variant drift or provider migration."
            )

        if session_reds:
            reds.extend(session_reds)
        else:
            clean.append(s)

    return {"reds": reds, "yellows": yellows, "clean": clean}


# ── Report printer ─────────────────────────────────────────────────────────────
def print_report(sessions: list[dict], ev: dict, report_only: bool) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    reds = ev["reds"]
    yellows = ev["yellows"]

    if reds:
        overall = "RED"
    elif yellows:
        overall = "YELLOW"
    else:
        overall = "GREEN"

    mode_note = " [--report-only]" if report_only else ""
    divider = "=" * 64

    print(f"\n{divider}")
    print(f"A7 STERLING — OPENCODE MODEL DISCIPLINE GATE | {ts}{mode_note}")
    print(f"Window: Last {WINDOW_HOURS}h  |  DB: {DB_PATH}")
    print(divider)

    if not sessions:
        print(GRN("  No OpenCode sessions recorded in last 24h."))
        print(GRN(f"  GATE: GREEN — nothing to audit."))
        print(f"{divider}\n")
        return

    # Session summary table
    col_model = 48
    print(f"\n  {'MODEL':<{col_model}} {'PROV':<12} {'VAR':<9} {'COST':>9} {'SESS':>5}")
    print(f"  {'-'*col_model} {'-'*12} {'-'*9} {'-'*9} {'-'*5}")
    for s in sessions:
        cost_str = f"${s['total_cost']:.4f}"
        row = (
            f"  {s['display']:<{col_model}} "
            f"{s['provider_id']:<12} "
            f"{s['variant']:<9} "
            f"{cost_str:>9} "
            f"{s['session_count']:>5}"
        )
        # Color-code flagged rows
        if _is_banned(s) and s["total_cost"] > 0:
            print(RED(row))
        elif s["variant"] == "high" and _is_free_base(s) and s["total_cost"] > 0.001:
            print(RED(row))
        elif s["provider_id"] == "openrouter" and s["total_cost"] > OR_COST_THRESHOLD_24H:
            print(RED(row))
        else:
            print(row)

    total_cost_24h = sum(s["total_cost"] for s in sessions)
    total_sessions = sum(s["session_count"] for s in sessions)
    print(f"\n  24h total: ${total_cost_24h:.4f} across {total_sessions} session(s)")

    # RED findings — detailed
    if reds:
        print(f"\n  {RED(f'RED FLAGS ({len(reds)}):')} ")
        for i, r in enumerate(reds, 1):
            print(f"\n  [{i}] {RED(r['trigger'])}")
            # Word-wrap detail at 72 chars with indent
            words = r["detail"].split()
            line = "      "
            for word in words:
                if len(line) + len(word) + 1 > 74:
                    print(RED(line.rstrip()))
                    line = "      " + word + " "
                else:
                    line += word + " "
            if line.strip():
                print(RED(line.rstrip()))

    # YELLOW advisories
    if yellows:
        print(f"\n  {YEL(f'YELLOW ADVISORIES ({len(yellows)}):')} ")
        for y in yellows:
            print(YEL(f"  - {y}"))

    # Clean sessions
    if ev["clean"]:
        print(f"\n  {GRN('COMPLIANT MODELS:')} ")
        for s in ev["clean"]:
            print(GRN(f"  + {s['display']} ({s['provider_id']}) — ${s['total_cost']:.6f}"))

    # Gate verdict
    print()
    if overall == "RED":
        if report_only:
            verdict = RED(f"GATE: RED — {len(reds)} violation(s) [report-only: not blocking]")
        else:
            verdict = RED(f"GATE: RED — {len(reds)} violation(s). Commit BLOCKED.")
    elif overall == "YELLOW":
        verdict = YEL(f"GATE: YELLOW — {len(yellows)} advisory/advisories. Commit permitted.")
    else:
        verdict = GRN("GATE: GREEN — All models compliant.")

    print(f"  {verdict}")
    print(f"{divider}\n")


# ── Existence gate — configured model IDs must resolve to a known catalog ──────
# (added 2026-06-15, MISSION-267)
THUNDERBIRD_ROOT = Path(__file__).resolve().parent.parent

# Files whose configured model IDs are validated against KNOWN_MODEL_CATALOG.
# Add new config sources here as they appear.
MODEL_CONFIG_SOURCES = [
    THUNDERBIRD_ROOT / "core" / "ai_infra" / "thunderbird_model_router.py",
    THUNDERBIRD_ROOT / "core" / "learning" / "model_safeguards.py",
]

# Regex to harvest plausible model-ID string literals from "model_id"/"model"/
# *_MODEL assignments. Conservative: only flags string literals tied to a model
# field/constant, so prose and unrelated strings are not swept in.
import re as _re
_MODEL_LITERAL_RE = _re.compile(
    r"""(?:model_id|["']model["']|[A-Z_]*MODEL)\s*[:=]\s*["']([^"']+)["']"""
)


def _resolves(model_id: str) -> bool:
    """True if a configured model ID is acceptable: in the live catalog, a
    documented retired marker, or a flat tier-routing keyword (not a real ID)."""
    mid = model_id.strip()
    if not mid:
        return True
    if mid in KNOWN_MODEL_CATALOG:
        return True
    if any(mid.startswith(p) for p in RETIRED_MARKER_PREFIXES):
        return True
    # Tier/routing keywords that are intentionally NOT model IDs (resolved downstream)
    if mid in {"openrouter_free", "flux", "perplexity", "perplexity_reasoning",
               "sonnet", "haiku", "opus", "vision", "fast", "grok", "research",
               "default"}:
        return True
    return False


def check_configured_model_ids() -> dict:
    """Scan MODEL_CONFIG_SOURCES for configured model IDs and validate existence.

    Returns {"unresolved": [...], "fabricated": [...], "checked": int}.
      - fabricated: ID is on the explicit FABRICATED_MODEL_IDS denylist (hard RED).
      - unresolved: ID does not resolve against the live catalog / retired markers /
        routing keywords (RED — likely a typo or a new fabrication).
    """
    unresolved: list[dict] = []
    fabricated: list[dict] = []
    checked = 0

    for path in MODEL_CONFIG_SOURCES:
        if not path.exists():
            continue
        for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue  # skip comment lines (retirement notes mention old IDs)
            for mid in _MODEL_LITERAL_RE.findall(line):
                checked += 1
                if mid in FABRICATED_MODEL_IDS:
                    fabricated.append({"file": str(path), "line": lineno, "id": mid})
                elif not _resolves(mid):
                    unresolved.append({"file": str(path), "line": lineno, "id": mid})

    return {"unresolved": unresolved, "fabricated": fabricated, "checked": checked}


def print_config_check(result: dict, report_only: bool) -> str:
    """Severity model (deliberate, to keep the gate honest without false-positive blocks):
      - FABRICATED (explicit denylist of known-invented IDs) → RED, hard block.
        Zero false positives: these IDs were confirmed to not exist.
      - UNRESOLVED (not in KNOWN_MODEL_CATALOG, not a retired marker/routing keyword)
        → YELLOW advisory only. Real but un-catalogued provider IDs (Perplexity, FLUX,
        etc.) land here; the cure is to add them to the catalog, not to block a commit.
    Returns overall: 'RED' | 'YELLOW' | 'GREEN'."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    divider = "=" * 64
    unresolved = result["unresolved"]
    fabricated = result["fabricated"]
    print(f"\n{divider}")
    print(f"A7 STERLING — MODEL-ID EXISTENCE GATE | {ts}")
    print(f"Sources: {len(MODEL_CONFIG_SOURCES)} config file(s)  |  Catalog: {len(KNOWN_MODEL_CATALOG)} live IDs")
    print(divider)
    print(f"\n  Checked {result['checked']} configured model-ID literal(s).")

    if fabricated:
        print(f"\n  {RED(f'FABRICATED IDs — HARD FAIL ({len(fabricated)}):')}")
        for f in fabricated:
            print(RED(f"    {f['id']}  ({Path(f['file']).name}:{f['line']}) — known non-existent, banned"))
    if unresolved:
        print(f"\n  {YEL(f'UNRESOLVED IDs — advisory ({len(unresolved)}):')}")
        for u in unresolved:
            print(YEL(f"    {u['id']}  ({Path(u['file']).name}:{u['line']}) — not in live catalog; "
                      f"add to KNOWN_MODEL_CATALOG if real"))

    if fabricated:
        overall = "RED"
    elif unresolved:
        overall = "YELLOW"
    else:
        overall = "GREEN"

    print()
    if overall == "RED":
        if report_only:
            print(RED(f"  GATE: RED — {len(fabricated)} fabricated model ID(s) [report-only: not blocking]"))
        else:
            print(RED(f"  GATE: RED — {len(fabricated)} fabricated model ID(s). A configured ID must "
                      f"exist (not be invented). Commit BLOCKED."))
    elif overall == "YELLOW":
        print(YEL(f"  GATE: YELLOW — {len(unresolved)} un-catalogued ID(s). Commit permitted; "
                  f"add real IDs to KNOWN_MODEL_CATALOG."))
    else:
        print(GRN("  GATE: GREEN — all configured model IDs resolve to the live catalog."))
    print(f"{divider}\n")
    return overall


# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(
        description="A7 Sterling — OpenCode model discipline gate (24h window)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="See script docstring for trigger definitions and install instructions.",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Print report without gate enforcement (always exits 0).",
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Existence gate: validate every configured model ID resolves against "
             "the live KNOWN_MODEL_CATALOG (catches fabricated IDs). Exits 1 on RED "
             "unless --report-only. Runs independently of the OpenCode DB.",
    )
    args = parser.parse_args()

    # ── Existence gate (MISSION-267): configured model IDs must resolve ──────────
    if args.check_config:
        cfg = check_configured_model_ids()
        overall = print_config_check(cfg, report_only=args.report_only)
        if args.report_only:
            return 0
        # Only fabricated (denylisted) IDs block; YELLOW/GREEN pass.
        return 1 if overall == "RED" else 0

    # DB-missing: YELLOW + fail open (don't block commits)
    if not DB_PATH.exists():
        print(
            YEL(
                f"[A7-GATE] YELLOW: OpenCode DB not found at {DB_PATH}\n"
                f"[A7-GATE] Audit tool unavailable — failing open. Commit permitted."
            )
        )
        return 0

    sessions = query_24h_sessions()
    ev = evaluate(sessions)

    print_report(sessions, ev, report_only=args.report_only)

    if args.report_only:
        return 0

    # Gate enforcement: RED -> exit 1, YELLOW/GREEN -> exit 0
    return 1 if ev["reds"] else 0


if __name__ == "__main__":
    sys.exit(main())
