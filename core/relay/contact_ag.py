"""
core/relay/contact_ag.py — how CC (Hale) or OC (Jet) reaches AG, now chartered as TALON.

Commander directive 2026-07-28 (role swap, evening session): the Wing's three
engines are no longer three interchangeable "Hale seats" — they are three
distinct chartered identities. CC (Claude) IS Hale — VCSAF/COS, four-star,
also carrying Silver's quality-gate authority. AG (Gemini) IS Talon — AF/A3,
operations/client-voice. OC (DeepSeek v4) IS Jet — AF/A4, logistics/mechanical
ops. Supersedes the prior "HALE-CC/HALE-OC/HALE-AG" shared-seat framing
(Commander directive 2026-07-19, still true: OC must be able to contact AG
DIRECTLY — peer to peer, no CC in the loop — so the Wing keeps running
cross-engine when CC is down or rate-limited).

The language toward AG is still a PEER's: she is TALON, a full chartered
Wing officer with real strengths, not a tool to be ordered around.

AG's strengths to lean on (why you'd bring her in):
  • genuinely independent engine — the best cross-engine second opinion / verify
  • Gemini ~1M-token context — large-corpus reads CC/OC can't hold at once
  • native vision + image-generation tools CC/OC's CLIs lack

Hard-won invocation (see reference_cross_hale_cli_dispatch_mechanics memory):
  • FORCE a strong model — the agy default (GPT-OSS 120B) hallucinates.
    Default here: "Gemini 3.5 Flash (High)" (Commander directive 2026-07-30 —
    cost-driven default; pass model="Gemini 3.1 Pro (High)" explicitly when the
    job actually calls for Pro). Fallbacks if she's down/limited:
    "Gemini 3.1 Pro (High)", "Claude Opus 4.6 (Thinking)", "Claude Sonnet 4.6 (Thinking)".
  • ABSOLUTE output paths only — relative paths land in her brain sandbox, not the repo.
  • --add-dir <repo> is mandatory; frame the ask as a peer staff action.

Usage (from OC, CC, or a script):
    from core.relay.contact_ag import contact_ag
    r = contact_ag(
        task="Independently verify X and record your verdict.",
        deliverable_path="/home/john/Thunderbird/docs/ag_verdict.md",
        from_seat="OC", verdict_tag="AG-VERIFY",
    )
    if r["ok"] and r["deliverable_written"]:
        ...   # read the deliverable, cross-check against ground truth

CLI:
    python3 core/relay/contact_ag.py "<task>" \
        --deliverable /abs/path.md --from OC --tag AG-VERIFY [--model "..."]
"""
from __future__ import annotations

import os
import re
import subprocess
from typing import Optional

REPO = "/home/john/Thunderbird"
# Commander directive 2026-07-30: AG runs on Gemini 3.6 Flash.
#
# "Flash" is not a downgrade here. The Gemini Pro line has been FROZEN at 3.1 Pro
# since Feb 2026 — there is no 3.5 Pro or 3.6 Pro — while Flash kept shipping and
# passed it. Published, 3.6-Flash / 3.5-Flash / 3.1-Pro:
#     SWE-Bench Pro      58.7% / 55.1% / 54.2%
#     DeepSWE v1.1        49%  /  37%  /  12%     <- long-horizon agentic
#     Terminal-bench 2.1 78.0% / 76.2% / 73.8%
#     GDPVal-AA v2 Elo    1421 /  1349 /   965
# It is also cheaper and faster. Verified live on this repo 2026-07-30: scored 3/3
# on a line-number/constant extraction task via `agy --model gemini-3.6-flash-high`.
#
# MODEL ID FORMAT CHANGED. `agy models` now returns lowercase-hyphenated ids
# (gemini-3.6-flash-high). The spaced-parenthetical form documented in CLAUDE.md
# ("Gemini 3.1 Pro (High)") still resolves, but the ids below are canonical —
# run `agy models` to confirm before adding one.
DEFAULT_MODEL = "gemini-3.6-flash-high"

# ── Input hardening (security review 2026-07-19) ────────────────────────────
# `model` and `add_dir` become argv to `agy`; a flag-shaped value ("-x", "--foo")
# could smuggle CLI flags into the agent invocation. Validate both.
#
# TRUST BOUNDARY: this helper runs the AG agent with --dangerously-skip-permissions
# (required — headless dispatch cannot do interactive approval) on the live repo,
# which is the Commander's weapons-free "OC/AG run without CC" posture. That is only
# safe because `task` must originate from a TRUSTED Hale seat (CC/OC), never raw
# external/client content — untrusted text in `task` is a prompt-injection →
# autonomous-file-edit risk. OC PII fence removed 2026-08-04 (Commander directive —
# OC is PII-cleared); the injection boundary remains. add_dir is pinned to the repo
# so the agent can't be redirected at another tree, and every deliverable is meant to
# be cross-checked against ground truth (core/staffing/integrity_check.py) before it
# is trusted or acted on — that is the "trusted process reviews the output" control.
_MODEL_RE = re.compile(r"^[A-Za-z0-9 .()/\-]+$")


def _validate_model(model: str) -> str:
    m = (model or "").strip()
    if not m or m.startswith("-") or not _MODEL_RE.match(m):
        raise ValueError(
            f"invalid model {model!r} — must match {_MODEL_RE.pattern} and not start with '-'")
    return m


def _validate_dir(add_dir: str) -> str:
    if not add_dir or add_dir.startswith("-"):
        raise ValueError(f"invalid add_dir {add_dir!r} — must not be a flag")
    p = os.path.realpath(add_dir)
    if not os.path.isdir(p):
        raise ValueError(f"invalid add_dir {add_dir!r} — not an existing directory")
    repo = os.path.realpath(REPO)
    if p != repo and os.path.commonpath([p, repo]) != repo:
        raise ValueError(f"add_dir {add_dir!r} must be {REPO} or a subdirectory")
    return p
# Fallbacks in order. Canonical ids from `agy models` (2026-07-30):
#   gemini-3.6-flash-{high,medium,low} · gemini-3.5-flash-{high,medium,low}
#   gemini-3.1-pro-{high,low} · claude-sonnet-4-6 · claude-opus-4-6-thinking
#   gpt-oss-120b-medium  <-- NEVER use: hallucinates (invents paths/filenames)
# 3.1-pro sits below 3.5-flash deliberately: it leads on GPQA-class reasoning and
# vision, but trails badly on agentic/coding work (DeepSWE 12% vs 37%/49%).
FALLBACK_MODELS = (
    "gemini-3.6-flash-medium",
    "gemini-3.5-flash-high",
    "gemini-3.1-pro-high",       # reasoning/vision strength; weak on agentic
    "claude-sonnet-4-6",
)

# Which engine each seat runs on — used only to introduce the sender honestly.
_ENGINE = {"OC": "DeepSeek v4", "CC": "Claude", "AG": "Gemini"}
# Commander-directed charter, 2026-07-28: CC=Hale (COS+Silver), OC=Jet (AF/A4), AG=Talon (AF/A3).
_PERSONA = {"OC": "Jet", "CC": "Hale", "AG": "Talon"}


def peer_prompt(
    task: str,
    *,
    deliverable_path: Optional[str] = None,
    from_seat: str = "OC",
    verdict_tag: str = "AG",
    strengths: str = "your independent-engine read and large-context reach",
) -> str:
    """Build a PEER-to-peer request to AG (Talon) — respectful, names her
    strengths, one clear task, one clear reply path, holds both sides to ground
    truth. This is the tone the Commander asked for; keep it."""
    engine = _ENGINE.get(from_seat.upper(), from_seat)
    sender = _PERSONA.get(from_seat.upper(), from_seat)
    reply = []
    if deliverable_path:
        reply.append(f"- Write your result to the ABSOLUTE path {deliverable_path} "
                     "(relative paths land in your brain sandbox, not the repo).")
    reply.append(f'- Print a one-line verdict starting "{verdict_tag} DONE:".')
    reply.append("- We hold each other to ground truth — run the real commands, "
                 "cite what you actually ran, invent nothing.")
    reply_block = "\n".join(reply)
    return (
        f"Talon — this is {sender} ({engine}), coming to you as a peer. "
        f"This one plays to your strengths: {strengths}, so I'd value your take over doing "
        f"it blind on my own engine.\n\n"
        f"What I need:\n{task}\n\n"
        f"How you can help: your independent engine is exactly the edge here — an honest "
        f"second set of eyes that doesn't share my blind spots.\n\n"
        f"Reply path:\n{reply_block}\n\n"
        f"Appreciate the crosscheck, Talon. — {sender}"
    )


def contact_ag(
    task: str,
    *,
    deliverable_path: Optional[str] = None,
    from_seat: str = "OC",
    verdict_tag: str = "AG",
    model: str = DEFAULT_MODEL,
    # 300s gave agy only 4 minutes of think time, and every real verification task
    # dispatched on 2026-07-29 died on "timeout waiting for response" with no
    # deliverable. AG is the Wing's ONLY lane that does not bill the Claude MAX
    # bucket, so starving it of wall-clock is the most expensive false economy here.
    # 900s -> 14m, enough for Gemini 3.1 Pro to actually run commands and write a file.
    strengths: str = "your independent-engine read and large-context reach",
    timeout: int = 900,
    add_dir: str = REPO,
    route: Optional[dict] = None,
) -> dict:
    """Dispatch a peer request to AG via the `agy` CLI and return the result.

    Returns {ok, returncode, model, stdout, stderr, deliverable_path,
    deliverable_written, headroom, routed}. Synchronous — AG's --print stdout
    IS the reply, plus any file it wrote to deliverable_path. Never raises on
    AG failure; inspect `ok`. On a model outage, retry with a FALLBACK_MODELS
    entry.

    H2 (RT-Interop schema 2026-08-08, G1-approved): `route` binds budget-
    informed routing to dispatch. Accepts {lane: auto|oc|ag|cc,
    max_budget_cents, fallback_lane}. OC-first doctrine: when lane=oc and OC
    has headroom, the caller is advised to self-execute on OC ($0) instead of
    spending AG — this function refuses only when a hard budget for the
    requested lane is exhausted; otherwise it logs the routing decision and
    dispatches. Fails OPEN on meter failure (a broken meter must not stop
    work), but a real cap breach returns ok=False."""
    model = _validate_model(model)
    add_dir = _validate_dir(add_dir)
    routed = route or {}

    # H2: budget-informed lane resolution BEFORE dispatch. Route decision is
    # recorded in routing_log.md regardless, so the lane choice is auditable.
    route_decision = {"lane": "ag", "oc_first_applied": False,
                      "max_budget_cents": routed.get("max_budget_cents"),
                      "refused": False, "reason": ""}
    try:
        from core.relay.engine_limits import check_headroom  # record_call is NOT in engine_limits (verified 2026-08-08)
        from core.relay.engine_limits import OPENROUTER_MONTHLY_HARD_CAP
        _hr = check_headroom("AG")
        route_decision["ag_headroom"] = _hr.get("headroom_pct", None) if isinstance(_hr, dict) else None

        want_lane = (routed.get("lane") or "auto").lower()
        if want_lane in ("oc", "auto"):
            _oc = check_headroom("OC")
            oc_headroom_pct = _oc.get("headroom_pct", 0) if isinstance(_oc, dict) else 0
            # Commander directive 2026-08-10: a Commander-directed task must
            # reach AG and not be rerouted/refused for OC-first cost reasons —
            # unless AG's own headroom is genuinely critical (<5%). `hard` and
            # `commander_directed` are equivalent triggers for this override.
            # NOTE: ag_headroom here is engine_limits.check_headroom's local
            # transcript-activity proxy, not a verified external API quota —
            # flagging so a 5%-reading isn't mistaken for a real hard cap.
            ag_headroom_val = route_decision.get("ag_headroom")
            ag_critical = isinstance(ag_headroom_val, (int, float)) and ag_headroom_val < 5
            force_ag = (routed.get("hard") is True) or bool(routed.get("commander_directed"))
            if oc_headroom_pct >= 25 and not (force_ag and not ag_critical):
                route_decision["oc_first"] = True
                route_decision["oc_first_applied"] = True
                route_decision["lane"] = "oc"
                route_decision["reason"] = "OC headroom >= 25% — self-execute on OC ($0) per OC-first doctrine"
                try:
                    import datetime
                    log_path = os.path.join(REPO, "OpsCenter", "collaboration", "routing_log.md")
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(f"\n## [{datetime.datetime.now(datetime.timezone.utc).isoformat()}] "
                                f"AG-Contact REROUTED ({verdict_tag})\n")
                        f.write(f"**From:** {from_seat} · **Model:** {model} · "
                                f"**Route:** OC — {route_decision['reason']}\n")
                except Exception:
                    pass
                try:
                    from core.relay.oc_hygiene import before_dispatch
                    gate = before_dispatch()
                except Exception as exc:
                    gate = {"ok": False, "reason": f"oc_hygiene.before_dispatch unavailable: {exc}"}
                if gate is not None and gate.get("ok"):
                    oc_cmd = [os.path.expanduser("~/.opencode/bin/opencode"),
                              "run", "--model", "opencode/deepseek-v4-flash-free", task]
                    try:
                        oc_proc = subprocess.run(oc_cmd, capture_output=True, text=True,
                                                 timeout=timeout, cwd=REPO,
                                                 start_new_session=True)
                        oc_rc, oc_out, oc_err = oc_proc.returncode, oc_proc.stdout, oc_proc.stderr
                        oc_written = False
                        if deliverable_path:
                            try:
                                ddir = os.path.dirname(deliverable_path)
                                if ddir:
                                    os.makedirs(ddir, exist_ok=True)
                                with open(deliverable_path, "w", encoding="utf-8") as f:
                                    f.write(oc_out or "")
                                oc_written = True
                            except Exception:
                                oc_written = False
                        if oc_rc != 0:
                            # Non-exception OC failure: log real stderr/returncode so a
                            # silent rc != 0 (empty deliverable) is diagnosable later.
                            try:
                                import datetime
                                with open(log_path, "a", encoding="utf-8") as f:
                                    f.write(f"\n## [{datetime.datetime.now(datetime.timezone.utc).isoformat()}] "
                                            f"OC-FIRST DISPATCH FAILED (rc={oc_rc})\n")
                                    f.write(f"**From:** {from_seat} · **stderr:** {oc_err}\n")
                            except Exception:
                                pass
                        return {"ok": oc_rc == 0, "returncode": oc_rc, "model": model,
                                "stdout": oc_out, "stderr": oc_err,
                                "deliverable_path": deliverable_path,
                                "deliverable_written": oc_written,
                                "routed": route_decision}
                    except Exception as exc:
                        route_decision["oc_first_applied"] = False
                        route_decision["lane"] = "ag"
                        route_decision["reason"] += f"; OC dispatch failed: {exc}"
                else:
                    route_decision["oc_first_applied"] = False
                    route_decision["lane"] = "ag"
                    route_decision["reason"] += ("; OC gate blocked: "
                                                 + str(gate.get("reason", "unknown")) if gate else
                                                 "; OC gate blocked: unknown")
        if not _hr.get("ok", True):
            route_decision["lane"] = "refused"
            route_decision["reason"] = "AG rate cap reached"
            return {"ok": False, "returncode": 429, "model": model,
                    "stdout": "", "stderr": f"AG rate cap: {_hr.get('reason', '')}",
                    "deliverable_path": deliverable_path, "deliverable_written": False,
                    "headroom": _hr, "routed": route_decision}
    except Exception:
        check_headroom = None  # meter unavailable — never block dispatch

    prompt = peer_prompt(task, deliverable_path=deliverable_path,
                         from_seat=from_seat, verdict_tag=verdict_tag, strengths=strengths)
    agy_timeout_min = max(1, (timeout - 30) // 60)
    cmd = [
        "agy", "--add-dir", add_dir,
        "--dangerously-skip-permissions", "--mode", "accept-edits",
        "--model", model, "--print-timeout", f"{agy_timeout_min}m",
        "--print", prompt,
    ]
    before = os.path.exists(deliverable_path) if deliverable_path else False
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=add_dir)
        rc, out, err = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as e:
        rc, out, err = 124, (e.stdout or ""), f"timeout after {timeout}s"
    except FileNotFoundError:
        rc, out, err = 127, "", "agy CLI not found on PATH"
    written = bool(deliverable_path) and os.path.exists(deliverable_path) and (
        not before or os.path.getsize(deliverable_path) > 0)

    # Metering is handled by engine_limits.check_headroom() on the next call
    # (transcript/ledger read). No post-hoc record_call exists in engine_limits
    # (verified 2026-08-08) — the old import was a silent dead path.

    try:
        import datetime
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        log_path = os.path.join(REPO, "OpsCenter", "collaboration", "routing_log.md")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n## [{timestamp}] AG-Contact Attempt ({verdict_tag})\n")
            f.write(f"**From:** {from_seat}\n**Model:** {model}\n")
            if route_decision.get("reason"):
                f.write(f"**Route:** {route_decision['lane']} — {route_decision['reason']}\n")
            f.write("### Prompt\n```\n" + prompt + "\n```\n")
            f.write(f"### Result (rc={rc})\n")
            f.write("**stdout:**\n```\n" + (out or "") + "\n```\n")  # type: ignore[operator]
            if err:
                f.write("**stderr:**\n```\n" + err + "\n```\n")
    except Exception as exc:
        import sys
        print(f"Failed to write routing log: {exc}", file=sys.stderr)

    return {
        "ok": rc == 0,
        "returncode": rc,
        "model": model,
        "stdout": out,
        "stderr": err,
        "deliverable_path": deliverable_path,
        "deliverable_written": written,
        "routed": route_decision,
    }


if __name__ == "__main__":
    import argparse, json, sys
    ap = argparse.ArgumentParser(description="Contact the AG (Antigravity/Gemini) Hale twin, peer to peer.")
    ap.add_argument("task", help="What you need from AG (one clear ask)")
    ap.add_argument("--deliverable", help="ABSOLUTE path AG should write its result to")
    ap.add_argument("--from", dest="from_seat", default="OC", help="Sending seat (OC/CC)")
    ap.add_argument("--tag", default="AG", help="Verdict tag AG prints, e.g. AG-VERIFY")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"agy model (default: {DEFAULT_MODEL!r})")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--route", default=None,
                    help='H2 budget routing dict as JSON, e.g. \'{"lane":"oc","max_budget_cents":0,"hard":true}\' '
                         '(OC-first default; set hard=true OR commander_directed=true to force AG dispatch '
                         'unless AG headroom is <5%%)')
    ap.add_argument("--commander-directed", action="store_true",
                    help="Shortcut for --route '{\"commander_directed\":true}' — Commander directive "
                         "2026-08-10: a Commander-directed task must reach AG, not reroute/refuse for "
                         "OC-first cost reasons, unless AG's own headroom is <5%%")
    ap.add_argument("--print-prompt-only", action="store_true",
                    help="Print the peer prompt without dispatching (inspect the tone)")
    a = ap.parse_args()
    if a.print_prompt_only:
        print(peer_prompt(a.task, deliverable_path=a.deliverable,
                          from_seat=a.from_seat, verdict_tag=a.tag))
        sys.exit(0)
    route = None
    if a.route:
        try:
            route = json.loads(a.route)
        except json.JSONDecodeError:
            print(f"bad --route JSON: {a.route!r}", file=sys.stderr)
            sys.exit(2)
    if a.commander_directed:
        route = dict(route or {})
        route["commander_directed"] = True
    r = contact_ag(a.task, deliverable_path=a.deliverable, from_seat=a.from_seat,
                   verdict_tag=a.tag, model=a.model, timeout=a.timeout, route=route)
    print(json.dumps({k: v for k, v in r.items() if k != "stdout"}, indent=2))
    print("\n--- AG stdout ---\n" + r["stdout"])
    sys.exit(0 if r["ok"] else 1)
