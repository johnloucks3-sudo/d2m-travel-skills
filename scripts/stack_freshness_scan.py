#!/usr/bin/env python3
"""stack_freshness_scan.py — Readiness Ladder & "Fresh and Lethal" staleness phase-out engine.

Implements SO_READINESS_LADDER_FRESHNESS_20260621.md §4 cadence + §1 ladder.

ADVISORY / READ-ONLY (v1). RECOMMENDS demotions down the readiness ladder and writes a
report. It does NOT delete, move, disable, or modify anything. A later, gated version executes.

Readiness ladder (demotion is the default direction):
  ACTIVE DUTY -> (a) NATIONAL GUARD (load-on-demand) -> (b) RESERVE (archived)
              -> (c) RETIRED-ACTIVE-RESERVE (.DISABLED/soak) -> (d) RETIRED COMPLETELY (verified-gone)

Modes (SO §4 cadence table) — same engine, the flag selects emphasis/actionability:
  --daily      init-footprint check (RED if Active-Duty auto-load > 15K tokens) + summary
  --weekly     staleness scan; surface unused >=14d -> National Guard (a) candidates
  --monthly    Reserve sweep; National-Guard items unused another 30d -> Reserve (b)
  --quarterly  Retire sweep; Reserve/cold items unused all quarter -> tier-c/d

Usage:
  python3 scripts/stack_freshness_scan.py --weekly
  python3 scripts/stack_freshness_scan.py --daily
  python3 scripts/stack_freshness_scan.py --json

Output:
  OpsCenter/state/stack_freshness_report.json   (machine)
  OpsCenter/state/STACK_FRESHNESS.md             (human)

Exit 0 always — RED footprint / long candidate lists are FINDINGS, not errors.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
STATE_DIR = ROOT / "OpsCenter" / "state"
SYSTEMD_USER = Path.home() / ".config" / "systemd" / "user"
REPORT_JSON = STATE_DIR / "stack_freshness_report.json"
REPORT_MD = STATE_DIR / "STACK_FRESHNESS.md"

SCAN_DIRS = ["core", "OpsCenter", "scripts", "agents", "api"]
SCAN_EXTS = {".py", ".sh"}

# --- §4 staleness thresholds (default, tunable). Days since last activity. ---
# "Last activity" = max(mtime, git last-commit). "Unused" also requires zero inbound refs.
TH_NATIONAL_GUARD = 14   # unused >=14d            -> (a) National Guard
TH_RESERVE = 44          # >=30d FURTHER (14+30)   -> (b) Reserve
TH_RETIRED_RESERVE = 134 # >=90d FURTHER (44+90)   -> (c) Retired-active-reserve
TH_RETIRED_COMPLETE = 224  # >=1 quarter cold (134+90) -> (d) Retired completely

# Tier labels (ladder order)
TIER_ACTIVE = "ACTIVE DUTY"
TIER_NG = "a) NATIONAL GUARD"
TIER_RESERVE = "b) RESERVE"
TIER_RETIRED_RESERVE = "c) RETIRED-ACTIVE-RESERVE"
TIER_RETIRED_COMPLETE = "d) RETIRED COMPLETELY"

# §1: ACTIVE DUTY is earned. But these NEVER get demoted regardless of signal.
# 6 protected email-scanner/relay files (SO 2026-06-08) + the scanner itself + the
# 4 timer-backed scripts this engine creates.
PROTECTED_FILES = {
    "OpsCenter/run_commander_directive_sweep.py",
    "OpsCenter/dispatch_and_email.py",
    "OpsCenter/email_task_ingest.py",
    "core/email/thunderbird_commander_inbox.py",
    "OpsCenter/relay_send.py",
    "core/relay/wing_relay.py",
}
NEVER_DEMOTE = set(PROTECTED_FILES) | {
    "scripts/stack_freshness_scan.py",
}

# §2 context-bloat: Active-Duty auto-load = CLAUDE.md @-refs + MEMORY.md
AUTO_LOAD_FILES = [
    ROOT / "Personas" / "hale_cos.md",
    ROOT / "hale_brief.md",
    ROOT / "hale_state.json",
    ROOT / "OpsCenter" / "session_context_latest.md",
    Path.home() / ".claude" / "projects" / "-home-john-Thunderbird" / "memory" / "MEMORY.md",
]
FOOTPRINT_TOKEN_TARGET = 15000  # §2: Active-Duty auto-load target <= 15K tokens

NOW = time.time()


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------
def enumerate_scripts():
    """All *.py/*.sh under the scan dirs. Returns list of Path (absolute)."""
    found = []
    for d in SCAN_DIRS:
        base = ROOT / d
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            if p.is_file() and p.suffix in SCAN_EXTS:
                found.append(p)
    return sorted(set(found))


def enumerate_units():
    """systemd user .service/.timer units."""
    if not SYSTEMD_USER.is_dir():
        return []
    units = [p for p in SYSTEMD_USER.iterdir()
             if p.is_file() and p.suffix in (".service", ".timer")]
    return sorted(units)


# ---------------------------------------------------------------------------
# Single-pass reference index (advisor #2): read every scannable text file once,
# build a set of all referenced basenames + python module names. O(repo) once.
# ---------------------------------------------------------------------------
def build_reference_index(scripts, units):
    """Return (referenced_basenames:set, imported_modules:set, execstart_targets:set).

    referenced_basenames: every 'foo.py'/'foo.sh' bare-filename string seen anywhere.
    imported_modules: every module token seen in import / from-import statements.
    execstart_targets: every basename appearing in a systemd ExecStart= line.
    """
    referenced = set()
    imported = set()
    execstart = set()

    fname_re = re.compile(r"\b([A-Za-z0-9_\-.]+\.(?:py|sh))\b")
    import_re = re.compile(r"^\s*(?:from\s+([A-Za-z0-9_.]+)\s+import|import\s+([A-Za-z0-9_.]+))")

    # Corpus = all scan-dir scripts + a few governance/text files + systemd units.
    corpus = list(scripts)
    for extra in ("CLAUDE.md", "Personas", "standing_orders", "docs"):
        ep = ROOT / extra
        if ep.is_file():
            corpus.append(ep)
        elif ep.is_dir():
            corpus.extend(p for p in ep.rglob("*")
                          if p.is_file() and p.suffix in {".md", ".py", ".sh", ".json"})
    corpus.extend(units)

    for p in set(corpus):
        try:
            text = p.read_text(errors="ignore")
        except Exception:
            continue
        for m in fname_re.findall(text):
            referenced.add(m)
        if p.suffix == ".py":
            for line in text.splitlines():
                im = import_re.match(line)
                if im:
                    mod = (im.group(1) or im.group(2) or "").split(".")[0]
                    if mod:
                        imported.add(mod)

    # ExecStart targets from systemd units
    exec_re = re.compile(r"^\s*ExecStart=.*?([A-Za-z0-9_\-./]+\.(?:py|sh))", re.MULTILINE)
    for u in units:
        try:
            text = u.read_text(errors="ignore")
        except Exception:
            continue
        for m in exec_re.findall(text):
            execstart.add(Path(m).name)

    return referenced, imported, execstart


# ---------------------------------------------------------------------------
# Staleness signals
# ---------------------------------------------------------------------------
def git_commit_ts(rel_path):
    """Epoch seconds of last commit touching rel_path, or None."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", rel_path],
            cwd=str(ROOT), capture_output=True, text=True, timeout=10,
        )
        s = out.stdout.strip()
        return int(s) if s else None
    except Exception:
        return None


def last_activity_ts(path, rel):
    """max(mtime, git-commit) — the MORE RECENT signal (advisor #3)."""
    try:
        mtime = path.stat().st_mtime
    except Exception:
        mtime = 0
    gts = git_commit_ts(rel)
    return max(mtime, gts or 0)


def classify_script(path, ref_index):
    referenced, imported, execstart = ref_index
    rel = str(path.relative_to(ROOT))
    name = path.name
    stem = path.stem

    # Inbound reference detection (advisor #1): orphan only if ALL miss.
    has_filename_ref = name in referenced
    has_import_ref = stem in imported
    is_execstart = name in execstart
    # A self-only filename hit (the file naming itself in a comment/docstring) still
    # counts as referenced — we are conservative by design.
    referenced_anywhere = has_filename_ref or has_import_ref or is_execstart

    last_ts = last_activity_ts(path, rel)
    age_days = (NOW - last_ts) / 86400.0 if last_ts else None

    protected = rel in NEVER_DEMOTE

    rec = TIER_ACTIVE
    reason = ""
    if protected:
        reason = "protected / never-demote"
    elif referenced_anywhere:
        why = []
        if has_import_ref:
            why.append("imported")
        if has_filename_ref:
            why.append("name-referenced")
        if is_execstart:
            why.append("systemd ExecStart")
        reason = "referenced (" + ", ".join(why) + ") — stays ACTIVE"
    elif age_days is None:
        reason = "no activity signal — neutral, stays ACTIVE"
    else:
        # Unused = no inbound refs AND last-activity older than threshold.
        if age_days >= TH_RETIRED_COMPLETE:
            rec = TIER_RETIRED_COMPLETE
        elif age_days >= TH_RETIRED_RESERVE:
            rec = TIER_RETIRED_RESERVE
        elif age_days >= TH_RESERVE:
            rec = TIER_RESERVE
        elif age_days >= TH_NATIONAL_GUARD:
            rec = TIER_NG
        else:
            rec = TIER_ACTIVE
            reason = f"orphan but fresh ({age_days:.0f}d) — stays ACTIVE"
        if rec != TIER_ACTIVE:
            reason = f"orphan (0 inbound refs) + cold {age_days:.0f}d"

    return {
        "kind": "script",
        "path": rel,
        "name": name,
        "referenced": referenced_anywhere,
        "imported": has_import_ref,
        "name_referenced": has_filename_ref,
        "execstart": is_execstart,
        "protected": protected,
        "age_days": round(age_days, 1) if age_days is not None else None,
        "recommended_tier": rec,
        "reason": reason,
    }


def systemctl_show(unit_name, prop):
    try:
        out = subprocess.run(
            ["systemctl", "--user", "show", "-p", prop, "--value", unit_name],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def systemctl_is_enabled(unit_name):
    try:
        out = subprocess.run(
            ["systemctl", "--user", "is-enabled", unit_name],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def classify_unit(path):
    rel = f"~/.config/systemd/user/{path.name}"
    name = path.name
    enabled = systemctl_is_enabled(name)

    # ExecStart target existence (service units): orphan = target missing.
    # Prefer the SCRIPT argument (.py/.sh) over the interpreter; expand systemd
    # specifiers (%h=$HOME). A missing interpreter-only path is NOT an orphan.
    execstart_target = None
    target_exists = None
    if path.suffix == ".service":
        try:
            text = path.read_text(errors="ignore")
            exec_line = ""
            workdir = None
            for line in text.splitlines():
                if line.strip().startswith("WorkingDirectory="):
                    workdir = line.split("WorkingDirectory=", 1)[1].strip().replace("%h", str(Path.home()))
                if line.strip().startswith("ExecStart=") and not exec_line:
                    exec_line = line.split("ExecStart=", 1)[1]
            if exec_line:
                home = str(Path.home())
                # Strip exec prefixes like -, @, +, ! that systemd allows.
                exec_line = exec_line.strip().lstrip("-@+!:").strip()
                # Tokenize on whitespace, then expand %h / %H per whole token.
                raw_tokens = exec_line.split()
                toks = [t.replace("%h", home).replace("%H", home) for t in raw_tokens]
                # Prefer a .py/.sh script argument; else the first absolute path that
                # is NOT a bare interpreter (python/bash/node/sh).
                interp = ("python", "python3", "bash", "sh", "node", "npx", "/bin/sh", "/usr/bin/env")
                script_tokens = [t for t in toks if t.endswith((".py", ".sh"))]
                if script_tokens:
                    execstart_target = script_tokens[0]
                else:
                    abs_non_interp = [t for t in toks
                                      if t.startswith("/") and Path(t).name not in interp]
                    execstart_target = abs_non_interp[0] if abs_non_interp else (toks[0] if toks else None)
                if execstart_target and not execstart_target.startswith("/") and workdir:
                    # Resolve relative script arg against WorkingDirectory.
                    execstart_target = str(Path(workdir) / execstart_target)
                if execstart_target and execstart_target.startswith("/"):
                    target_exists = Path(execstart_target).exists()
                else:
                    target_exists = None  # unresolved → neutral, never an orphan
        except Exception:
            pass

    # last-run (neutral if unknown — advisor open question)
    last_run_raw = systemctl_show(name, "ExecMainStartTimestampMonotonic")
    last_run_human = systemctl_show(name, "ExecMainStartTimestamp")

    # A timer-driven oneshot .service is INTENTIONALLY disabled — its paired .timer
    # is the enabled entry point. Such a service is HOT, not a demotion candidate.
    # (Advisor catch: do not over-demote timer payloads.) Same for our own freshness
    # units until Hale enables them.
    paired_timer_hot = False
    if path.suffix == ".service":
        timer = path.with_suffix(".timer")
        if timer.exists():
            tstate = systemctl_is_enabled(timer.name)
            tactive = ""
            try:
                tactive = subprocess.run(
                    ["systemctl", "--user", "is-active", timer.name],
                    capture_output=True, text=True, timeout=10).stdout.strip()
            except Exception:
                pass
            if tstate in ("enabled", "static") or tactive == "active":
                paired_timer_hot = True
    self_infra = name.startswith("d2m-freshness-")  # this engine's own units

    rec = TIER_ACTIVE
    reason = ""
    orphan = (target_exists is False)
    if orphan:
        rec = TIER_RETIRED_RESERVE
        reason = f"ExecStart target missing: {execstart_target} — orphan unit"
    elif paired_timer_hot:
        reason = "timer-driven payload — paired .timer enabled/active, stays ACTIVE"
    elif self_infra:
        reason = "freshness engine's own unit — pinned ACTIVE (pending Hale enable)"
    elif enabled in ("disabled", "masked"):
        rec = TIER_NG
        reason = f"unit {enabled} (installed, not active) — load-on-demand candidate"
    else:
        reason = f"enabled={enabled}" + (
            f", target ok" if target_exists else (", no ExecStart target" if path.suffix == ".timer" else ""))

    return {
        "kind": "unit",
        "path": rel,
        "name": name,
        "enabled": enabled,
        "execstart_target": execstart_target,
        "target_exists": target_exists,
        "last_run": last_run_human or "unknown",
        "protected": False,
        "recommended_tier": rec,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# §2 init-footprint
# ---------------------------------------------------------------------------
def footprint_check():
    files = []
    total_chars = 0
    for f in AUTO_LOAD_FILES:
        try:
            chars = len(f.read_text(errors="ignore"))
        except Exception:
            chars = 0
        files.append({"file": str(f), "chars": chars, "est_tokens": chars // 4})
        total_chars += chars
    est_tokens = total_chars // 4
    status = "RED" if est_tokens > FOOTPRINT_TOKEN_TARGET else "GREEN"
    return {
        "est_tokens": est_tokens,
        "total_chars": total_chars,
        "target_tokens": FOOTPRINT_TOKEN_TARGET,
        "status": status,
        "files": sorted(files, key=lambda x: -x["est_tokens"]),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Readiness Ladder staleness phase-out scanner (advisory)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--daily", action="store_true", help="init-footprint check + summary")
    g.add_argument("--weekly", action="store_true", help="staleness scan -> National Guard candidates")
    g.add_argument("--monthly", action="store_true", help="Reserve sweep")
    g.add_argument("--quarterly", action="store_true", help="Retire sweep (tier c/d)")
    ap.add_argument("--json", action="store_true", help="print full report JSON to stdout")
    args = ap.parse_args()

    mode = ("daily" if args.daily else "weekly" if args.weekly else
            "monthly" if args.monthly else "quarterly" if args.quarterly else "weekly")

    t0 = time.time()
    scripts = enumerate_scripts()
    units = enumerate_units()
    ref_index = build_reference_index(scripts, units)

    # One classification engine; mode selects emphasis (advisor #6).
    script_items = [classify_script(p, ref_index) for p in scripts]
    unit_items = [classify_unit(p) for p in units]
    all_items = script_items + unit_items

    # Tier rollups
    tier_order = [TIER_ACTIVE, TIER_NG, TIER_RESERVE, TIER_RETIRED_RESERVE, TIER_RETIRED_COMPLETE]
    counts = {t: 0 for t in tier_order}
    for it in all_items:
        counts[it["recommended_tier"]] = counts.get(it["recommended_tier"], 0) + 1

    # Actionable band per mode (which transition this cadence surfaces)
    actionable_tiers = {
        "daily": [],  # footprint-focused
        "weekly": [TIER_NG],
        "monthly": [TIER_RESERVE],
        "quarterly": [TIER_RETIRED_RESERVE, TIER_RETIRED_COMPLETE],
    }[mode]
    demotion_candidates = [it for it in all_items if it["recommended_tier"] != TIER_ACTIVE]
    actionable = [it for it in demotion_candidates if it["recommended_tier"] in actionable_tiers]

    # Top demotion candidates overall (coldest first)
    def sort_key(it):
        ti = tier_order.index(it["recommended_tier"])
        age = it.get("age_days") or 0
        return (-ti, -age)
    top_candidates = sorted(demotion_candidates, key=sort_key)[:25]

    footprint = footprint_check() if mode == "daily" or args.json else footprint_check()

    report = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "advisory": True,
        "so": "SO_READINESS_LADDER_FRESHNESS_20260621.md",
        "thresholds_days": {
            "national_guard": TH_NATIONAL_GUARD,
            "reserve": TH_RESERVE,
            "retired_reserve": TH_RETIRED_RESERVE,
            "retired_complete": TH_RETIRED_COMPLETE,
        },
        "inventory": {
            "scripts": len(scripts),
            "units": len(units),
            "total": len(all_items),
        },
        "tier_counts": counts,
        "footprint": footprint,
        "demotion_candidate_count": len(demotion_candidates),
        "actionable_this_cadence": [
            {"path": it["path"], "tier": it["recommended_tier"], "reason": it["reason"],
             "age_days": it.get("age_days")} for it in actionable
        ],
        "top_candidates": [
            {"path": it["path"], "kind": it["kind"], "tier": it["recommended_tier"],
             "reason": it["reason"], "age_days": it.get("age_days")} for it in top_candidates
        ],
        "elapsed_sec": round(time.time() - t0, 2),
    }

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2))
    write_markdown(report)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"⚡ STACK FRESHNESS SCAN — mode={mode} (ADVISORY, read-only)")
        print(f"   Inventory: {len(scripts)} scripts + {len(units)} units = {len(all_items)} items")
        print(f"   Recommended tiers:")
        for t in tier_order:
            print(f"     {t:28s} {counts.get(t,0)}")
        fp = footprint
        print(f"   Init footprint: {fp['est_tokens']:,} tokens (target <= {FOOTPRINT_TOKEN_TARGET:,}) -> {fp['status']}")
        print(f"   Demotion candidates total: {len(demotion_candidates)} | actionable this {mode}: {len(actionable)}")
        if top_candidates:
            print(f"   Top demotion candidates:")
            for it in top_candidates[:10]:
                age = f"{it.get('age_days')}d" if it.get("age_days") is not None else "—"
                print(f"     [{it['recommended_tier']:26s}] {it['path']} ({age}) — {it['reason']}")
        print(f"   Reports: {REPORT_JSON}  +  {REPORT_MD}")
        print(f"   Elapsed: {report['elapsed_sec']}s")

    return 0


def write_markdown(report):
    fp = report["footprint"]
    lines = []
    lines.append(f"# STACK FRESHNESS — Readiness Ladder Report")
    lines.append(f"*Generated {report['generated']} · mode `{report['mode']}` · ADVISORY (read-only)*")
    lines.append("")
    lines.append(f"SO: `{report['so']}` — v1 RECOMMENDS demotions; executes nothing.")
    lines.append("")
    lines.append("## Init-Context Footprint (§2)")
    lines.append("")
    lines.append(f"**{fp['est_tokens']:,} tokens** of Active-Duty auto-load "
                 f"(target ≤ {fp['target_tokens']:,}) → **{fp['status']}**")
    lines.append("")
    lines.append("| Auto-load file | est tokens |")
    lines.append("|---|---|")
    for f in fp["files"]:
        lines.append(f"| `{f['file']}` | {f['est_tokens']:,} |")
    lines.append("")
    lines.append("## Inventory & Recommended Tiers")
    lines.append("")
    inv = report["inventory"]
    lines.append(f"{inv['scripts']} scripts + {inv['units']} systemd units = **{inv['total']} items**")
    lines.append("")
    lines.append("| Recommended tier | count |")
    lines.append("|---|---|")
    for t, c in report["tier_counts"].items():
        lines.append(f"| {t} | {c} |")
    lines.append("")
    lines.append(f"Demotion candidates: **{report['demotion_candidate_count']}** · "
                 f"actionable this `{report['mode']}`: **{len(report['actionable_this_cadence'])}**")
    lines.append("")
    if report["actionable_this_cadence"]:
        lines.append(f"## Actionable This Cadence ({report['mode']})")
        lines.append("")
        lines.append("| Item | → Tier | Age | Reason |")
        lines.append("|---|---|---|---|")
        for it in report["actionable_this_cadence"]:
            age = f"{it['age_days']}d" if it.get("age_days") is not None else "—"
            lines.append(f"| `{it['path']}` | {it['tier']} | {age} | {it['reason']} |")
        lines.append("")
    lines.append("## Top Demotion Candidates (coldest first)")
    lines.append("")
    lines.append("| Item | Kind | → Tier | Age | Reason |")
    lines.append("|---|---|---|---|---|")
    for it in report["top_candidates"]:
        age = f"{it['age_days']}d" if it.get("age_days") is not None else "—"
        lines.append(f"| `{it['path']}` | {it['kind']} | {it['tier']} | {age} | {it['reason']} |")
    lines.append("")
    lines.append(f"*Thresholds (days since last activity): "
                 f"NG≥{report['thresholds_days']['national_guard']} · "
                 f"Reserve≥{report['thresholds_days']['reserve']} · "
                 f"Retired-reserve≥{report['thresholds_days']['retired_reserve']} · "
                 f"Retired-complete≥{report['thresholds_days']['retired_complete']}. "
                 f"Demotion requires 0 inbound refs AND cold. Protected/referenced/fresh stay ACTIVE.*")
    REPORT_MD.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
