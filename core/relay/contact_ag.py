"""
core/relay/contact_ag.py — how any Hale seat reaches its Antigravity twin (AG).

Commander directive 2026-07-19: OC (DeepSeek v4) must be able to contact AG
(Gemini 3.1 Pro) DIRECTLY — peer to peer, no CC in the loop — so the Wing keeps
running cross-engine when CC (Claude) is down or rate-limited. And the language
we use toward AG is a PEER's: she is HALE-AG / "Victory", a full Hale seat with
real strengths, not a tool to be ordered around.

AG's strengths to lean on (why you'd bring her in):
  • genuinely independent engine — the best cross-engine second opinion / verify
  • Gemini ~1M-token context — large-corpus reads CC/OC can't hold at once
  • native vision + image-generation tools CC/OC's CLIs lack

Hard-won invocation (see reference_cross_hale_cli_dispatch_mechanics memory):
  • FORCE a strong model — the agy default (GPT-OSS 120B) hallucinates.
    Default here: "Gemini 3.1 Pro (High)". Fallbacks if she's down/limited:
    "Claude Opus 4.6 (Thinking)", "Claude Sonnet 4.6 (Thinking)", "Gemini 3.5 Flash (High)".
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

import subprocess
from typing import Optional

REPO = "/home/john/Thunderbird"
DEFAULT_MODEL = "Gemini 3.1 Pro (High)"
FALLBACK_MODELS = (
    "Claude Opus 4.6 (Thinking)",
    "Claude Sonnet 4.6 (Thinking)",
    "Gemini 3.5 Flash (High)",
)

# Which engine each seat runs on — used only to introduce the sender honestly.
_ENGINE = {"OC": "DeepSeek v4", "CC": "Claude", "AG": "Gemini"}


def peer_prompt(
    task: str,
    *,
    deliverable_path: Optional[str] = None,
    from_seat: str = "OC",
    verdict_tag: str = "AG",
    strengths: str = "your independent-engine read and large-context reach",
) -> str:
    """Build a PEER-to-peer request to AG (Victory) — respectful, names her
    strengths, one clear task, one clear reply path, holds both sides to ground
    truth. This is the tone the Commander asked for; keep it."""
    engine = _ENGINE.get(from_seat.upper(), from_seat)
    reply = []
    if deliverable_path:
        reply.append(f"- Write your result to the ABSOLUTE path {deliverable_path} "
                     "(relative paths land in your brain sandbox, not the repo).")
    reply.append(f'- Print a one-line verdict starting "{verdict_tag} DONE:".')
    reply.append("- We hold each other to ground truth — run the real commands, "
                 "cite what you actually ran, invent nothing.")
    reply_block = "\n".join(reply)
    return (
        f"Victory — this is HALE-{from_seat.upper()} ({engine}), coming to you as a peer. "
        f"This one plays to your strengths: {strengths}, so I'd value your take over doing "
        f"it blind on my own engine.\n\n"
        f"What I need:\n{task}\n\n"
        f"How you can help: your independent engine is exactly the edge here — an honest "
        f"second set of eyes that doesn't share my blind spots.\n\n"
        f"Reply path:\n{reply_block}\n\n"
        f"Appreciate the crosscheck, Victory. — HALE-{from_seat.upper()}"
    )


def contact_ag(
    task: str,
    *,
    deliverable_path: Optional[str] = None,
    from_seat: str = "OC",
    verdict_tag: str = "AG",
    model: str = DEFAULT_MODEL,
    strengths: str = "your independent-engine read and large-context reach",
    timeout: int = 300,
    add_dir: str = REPO,
) -> dict:
    """Dispatch a peer request to AG via the `agy` CLI and return the result.

    Returns {ok, returncode, model, stdout, stderr, deliverable_path,
    deliverable_written}. Synchronous — AG's --print stdout IS the reply, plus
    any file it wrote to deliverable_path. Never raises on AG failure; inspect
    `ok`. On a model outage, retry with a FALLBACK_MODELS entry."""
    import os
    prompt = peer_prompt(task, deliverable_path=deliverable_path,
                         from_seat=from_seat, verdict_tag=verdict_tag, strengths=strengths)
    cmd = [
        "agy", "--add-dir", add_dir,
        "--dangerously-skip-permissions", "--mode", "accept-edits",
        "--model", model, "--print", prompt,
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
    return {
        "ok": rc == 0,
        "returncode": rc,
        "model": model,
        "stdout": out,
        "stderr": err,
        "deliverable_path": deliverable_path,
        "deliverable_written": written,
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
    ap.add_argument("--print-prompt-only", action="store_true",
                    help="Print the peer prompt without dispatching (inspect the tone)")
    a = ap.parse_args()
    if a.print_prompt_only:
        print(peer_prompt(a.task, deliverable_path=a.deliverable,
                          from_seat=a.from_seat, verdict_tag=a.tag))
        sys.exit(0)
    r = contact_ag(a.task, deliverable_path=a.deliverable, from_seat=a.from_seat,
                   verdict_tag=a.tag, model=a.model, timeout=a.timeout)
    print(json.dumps({k: v for k, v in r.items() if k != "stdout"}, indent=2))
    print("\n--- AG stdout ---\n" + r["stdout"])
    sys.exit(0 if r["ok"] else 1)
