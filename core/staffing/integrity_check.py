"""
core/staffing/integrity_check.py — CC's cross-engine integrity double-check.

Commander directive 2026-07-19: before CC (Claude) declares substantive/gated work
done or reports completion, a DIFFERENT engine independently verifies CC's key
claims against ground truth. Reason: on 2026-07-18 CC self-reported a cross-Hale
delegation as complete when it had failed — self-report over ground truth, the
exact defect the Wing's anti-theater system exists to prevent. CC's own "it's
done" is not ground truth; a peer engine that does not share CC's blind spots
must check it.

This is the reciprocal of the cross-Hale certification the Staff Summary Sheet
already requires for seat-executed sheets — here it guards CC's *own* claims and
final reports, not just delegated tickets.

Usage:
    from core.staffing.integrity_check import cc_integrity_double_check
    r = cc_integrity_double_check(
        claims=[
            "There are exactly 3 SSS sheets and all 3 are CLOSED.",
            "the retired web-app module has 0 references left in *.py.",
        ],
        ground_truth_cmds=[
            "python3 OpsCenter/mission_board_sync.py list",
            "grep -rn 'retired_module_name' --include='*.py' . | wc -l",
        ],
        deliverable_path="/home/john/Thunderbird/logs/sss_dispatch/cc_integrity.md",
        engine="AG",           # or "OC"
    )
    # r["stdout"] carries the verifier's per-claim VERIFIED/DISCREPANCY findings.

CLI:
    python3 core/staffing/integrity_check.py --engine AG \
        --claim "..." --claim "..." --cmd "..." --cmd "..." \
        --deliverable /abs/path.md
"""
from __future__ import annotations

import subprocess
from typing import Optional

REPO = "/home/john/Thunderbird"
_CACHE_PATH = f"{REPO}/logs/integrity_check_cache.json"


def _cache_key(claims: list[str], ground_truth_cmds: Optional[list[str]], engine: str) -> str:
    import hashlib
    blob = "|".join(sorted(claims)) + "||" + "|".join(sorted(ground_truth_cmds or [])) + "||" + engine.upper()
    return hashlib.sha256(blob.encode()).hexdigest()[:24]


def _cache_load() -> dict:
    import json, os
    if not os.path.exists(_CACHE_PATH):
        return {}
    try:
        with open(_CACHE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _cache_get(key: str, ttl_seconds: float) -> Optional[dict]:
    """Returns the cached verdict entry if present and within ttl_seconds, else None."""
    import time
    entry = _cache_load().get(key)
    if not entry:
        return None
    if time.time() - entry.get("cached_at", 0) > ttl_seconds:
        return None
    return entry


def _cache_put(key: str, verdict: str, detail: str, engine: str) -> None:
    import json, os, time
    os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
    cache = _cache_load()
    cache[key] = {"verdict": verdict, "detail": detail, "engine": engine, "cached_at": time.time()}
    # bound growth — keep the 200 most recent entries
    if len(cache) > 200:
        for k in sorted(cache, key=lambda k: cache[k].get("cached_at", 0))[:len(cache) - 200]:
            del cache[k]
    try:
        with open(_CACHE_PATH, "w") as f:
            json.dump(cache, f, indent=2)
    except Exception:
        pass


def build_verification_task(claims: list[str], ground_truth_cmds: Optional[list[str]] = None) -> str:
    """The verification brief handed to the other engine — check each claim
    against real command output, report per-claim, and give a single roll-up."""
    lines = [
        "Integrity double-check. For each CLAIM below, INDEPENDENTLY verify it by "
        "running the real command(s) yourself and comparing the actual output. Do "
        "not take the claim on trust — you are the check on it. Report per claim: "
        "'VERIFIED (<observed value>)' or 'DISCREPANCY (<claim> vs <actual>)'. "
        "If a command errors, say so; invent nothing.\n",
    ]
    for i, c in enumerate(claims, 1):
        lines.append(f"{i}. CLAIM: {c}")
    if ground_truth_cmds:
        lines.append("\nGround-truth commands to run (from the repo root):")
        for cmd in ground_truth_cmds:
            lines.append(f"  $ {cmd}")
    lines.append(
        "\nEnd with exactly one roll-up line: "
        "'INTEGRITY: ALL-VERIFIED' if every claim checks out, otherwise "
        "'INTEGRITY: DISCREPANCIES — <list which claims failed>'."
    )
    return "\n".join(lines)


def cc_integrity_double_check(
    claims: list[str],
    *,
    ground_truth_cmds: Optional[list[str]] = None,
    engine: str = "AG",
    deliverable_path: Optional[str] = None,
    model: Optional[str] = None,
    timeout: int = 300,
) -> dict:
    """Hand CC's key claims to a different engine for independent ground-truth
    verification. `engine`: "AG" (Gemini 3.1 Pro via contact_ag) or "OC"
    (DeepSeek v4 via opencode). Returns the same result shape as contact_ag:
    {ok, returncode, model, stdout, stderr, deliverable_path, deliverable_written}.
    Never raises on verifier failure — inspect `ok`; if the peer can't be reached,
    the caller must mark the claim UNVERIFIED, never upgrade it to done."""
    task = build_verification_task(claims, ground_truth_cmds)

    if engine.upper() == "AG":
        from core.relay.contact_ag import contact_ag
        return contact_ag(
            task,
            deliverable_path=deliverable_path,
            from_seat="CC",
            verdict_tag="INTEGRITY",
            model=model or "Gemini 3.1 Pro (High)",
            strengths="your independent engine — you don't share my blind spots, "
                      "which is exactly why you're the right check on my own claims",
            timeout=timeout,
        )

    if engine.upper() == "OC":
        import os, re
        model = model or "opencode/deepseek-v4-flash-free"
        # argv hardening: reject flag-shaped model values (security review 2026-07-19)
        if model.startswith("-") or not re.match(r"^[A-Za-z0-9 .()/\-]+$", model):
            raise ValueError(f"invalid model {model!r}")
        prompt = (
            "HALE-OC — this is HALE-CC asking for an integrity double-check, peer to "
            "peer. I don't want you to trust my summary; I want you to check it.\n\n"
            + task
            + (f"\n\nWrite your findings to the ABSOLUTE path {deliverable_path}."
               if deliverable_path else "")
        )
        before = os.path.exists(deliverable_path) if deliverable_path else False
        cmd = ["opencode", "run", prompt, "--dir", REPO, "--model", model]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=REPO)
            rc, out, err = proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as e:
            rc, out, err = 124, (e.stdout or ""), f"timeout after {timeout}s"
        except FileNotFoundError:
            rc, out, err = 127, "", "opencode CLI not found on PATH"
        written = bool(deliverable_path) and os.path.exists(deliverable_path) and (
            not before or os.path.getsize(deliverable_path) > 0)
        return {"ok": rc == 0, "returncode": rc, "model": model, "stdout": out,
                "stderr": err, "deliverable_path": deliverable_path,
                "deliverable_written": written}

    raise ValueError(f"engine must be 'AG' or 'OC', got {engine!r}")


def _parse_verdict(stdout: str) -> tuple[str, str]:
    """Parse the verifier's mandatory roll-up line. Returns (verdict, detail).
    No roll-up line found at all → UNVERIFIED, not a silent PASS — the
    verifier's own contract wasn't followed, so its answer can't be trusted."""
    import re
    text = stdout or ""
    if re.search(r"INTEGRITY:\s*ALL-VERIFIED", text):
        return "PASS", ""
    m = re.search(r"INTEGRITY:\s*DISCREPANCIES\s*(?:—|-)?\s*(.*)", text)
    if m:
        return "DISCREPANCY", m.group(1).strip()[:300]
    return "UNVERIFIED", "verifier produced no INTEGRITY: roll-up line"


def verify_and_record(
    claims: list[str],
    *,
    ground_truth_cmds: Optional[list[str]] = None,
    engine: str = "AG",
    deliverable_path: Optional[str] = None,
    ticket_id: str = "",
    task_type: str = "",
    model: Optional[str] = None,
    timeout: int = 300,
    page_on_discrepancy: bool = True,
    cache_ttl_seconds: float = 900,
    force_recheck: bool = False,
) -> dict:
    """The recording wrapper CLAUDE.md's HARD RULE now names — use this,
    never cc_integrity_double_check() directly, so the verdict is never
    silently unrecorded (Commander directive, SO-WING-OVERSIGHT-2026).

    Calls cc_integrity_double_check() unchanged, parses its mandatory
    roll-up line, forces UNVERIFIED (never a silent upgrade to PASS) if the
    engine itself was unreachable, records the outcome to
    core.staffing.delegation_outcomes, scores CC's claim in the seat
    scorecard, and pages the Commander in real time on DISCREPANCY/
    UNVERIFIED — the mechanical fix for a discrepancy passing through
    silently (2026-07-28 night 8-Sector Wing Exercise: AG marked a state
    complete when it wasn't; nothing durable recorded the catch).

    cache_ttl_seconds (WAR ROOM 2026-08-07, idea #8): identical (claims,
    ground_truth_cmds, engine) within the TTL skips the real engine dispatch
    — cuts redundant AG/OC calls when CC re-verifies the same claim set
    inside one working session. Cache is keyed on the exact claim/cmd/engine
    tuple, so any change to what's being checked is a fresh check. The
    outcome ledger still gets a row (dispatch_mode='cache_hit') so the audit
    trail stays complete; only the live engine round-trip is skipped. Set
    force_recheck=True to bypass, or cache_ttl_seconds=0 to disable caching
    for a call that must always hit ground truth fresh."""
    from core.staffing.delegation_outcomes import record_outcome, page_commander

    key = _cache_key(claims, ground_truth_cmds, engine)
    cached = None if (force_recheck or cache_ttl_seconds <= 0) else _cache_get(key, cache_ttl_seconds)

    if cached:
        verdict, detail = cached["verdict"], cached["detail"]
        r = {"ok": True, "returncode": 0, "model": model, "stdout": "",
             "stderr": "", "deliverable_path": deliverable_path,
             "deliverable_written": False, "from_cache": True,
             "cached_at": cached["cached_at"]}
        record_outcome(
            seat="CC", action="integrity_check", verdict=verdict,
            ticket_id=ticket_id, task_type=task_type, dispatch_mode="cache_hit",
            discrepancy_detail=detail, verified_by=engine,
        )
        r["verdict"] = verdict
        r["discrepancy_detail"] = detail
        return r

    r = cc_integrity_double_check(
        claims, ground_truth_cmds=ground_truth_cmds, engine=engine,
        deliverable_path=deliverable_path, model=model, timeout=timeout,
    )
    if not r["ok"]:
        verdict, detail = "UNVERIFIED", f"engine {engine} unreachable/failed (rc={r['returncode']})"
    else:
        verdict, detail = _parse_verdict(r["stdout"])

    if cache_ttl_seconds > 0:
        _cache_put(key, verdict, detail, engine)

    record_outcome(
        seat="CC", action="integrity_check", verdict=verdict,
        ticket_id=ticket_id, task_type=task_type, dispatch_mode="sync",
        discrepancy_detail=detail, verified_by=engine,
    )
    try:
        from core.silver.scorecard import record as scorecard_record
        if verdict in ("PASS", "DISCREPANCY"):
            scorecard_record("CC", category=task_type or "integrity",
                             outcome="pass" if verdict == "PASS" else "fail",
                             task_type=task_type, ref=ticket_id)
    except Exception:
        pass

    if page_on_discrepancy and verdict in ("DISCREPANCY", "UNVERIFIED"):
        page_commander(
            problem=f"Integrity check {verdict} — {ticket_id or 'ad hoc claim'}: {', '.join(claims)[:120]}",
            discussion=detail or "Verifier could not confirm CC's claim(s) against ground truth.",
            action=f"Verified by {engine}. See routing_log.md / deliverable for full findings.",
            next_steps="Review before treating the underlying task as done.",
        )
    r["verdict"] = verdict
    r["discrepancy_detail"] = detail
    return r


if __name__ == "__main__":
    import argparse, json, sys
    ap = argparse.ArgumentParser(description="CC cross-engine integrity double-check.")
    ap.add_argument("--claim", action="append", default=[], help="A claim to verify (repeatable)")
    ap.add_argument("--cmd", action="append", default=[], help="Ground-truth command (repeatable)")
    ap.add_argument("--engine", default="AG", choices=["AG", "OC"])
    ap.add_argument("--deliverable", help="ABSOLUTE path for the verifier's findings")
    ap.add_argument("--model")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--print-task-only", action="store_true")
    a = ap.parse_args()
    if not a.claim:
        ap.error("at least one --claim is required")
    if a.print_task_only:
        print(build_verification_task(a.claim, a.cmd or None)); sys.exit(0)
    r = cc_integrity_double_check(a.claim, ground_truth_cmds=a.cmd or None, engine=a.engine,
                                  deliverable_path=a.deliverable, model=a.model, timeout=a.timeout)
    print(json.dumps({k: v for k, v in r.items() if k != "stdout"}, indent=2))
    print("\n--- verifier findings ---\n" + r["stdout"])
    sys.exit(0 if r["ok"] else 1)
