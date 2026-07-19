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
        import os
        model = model or "opencode/deepseek-v4-flash-free"
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
