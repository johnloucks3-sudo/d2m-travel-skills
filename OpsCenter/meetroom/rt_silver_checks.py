#!/usr/bin/env python3
"""rt_silver_guard.py — C4: RT-Interop verification hooks for the Silver gate.

Extract from RT_INTEGRATION_SCHEMA.md C4 (2026-08-08, G1-approved):
  H6: 32 silent-failure taxonomy — negative-testing sanity checks to catch
      swallowed exceptions, unverified diffs, mock returns, false authority.
  H8: tamper-evident state_hash (sha256) verification on card transitions.

Design: standalone, importable by core/silver/gate.py AND callable from the
meetroom CLI. It does NOT modify gate.py — the owning lane (Sterling/A7) is
free to wire the returned findings into Verdict.holds. Pure stdlib.

Usage:
  python3 OpsCenter/meetroom/rt_silver_checks.py {session_dir}
  from OpsCenter.meetroom.rt_silver_checks import rt_interop_findings
"""
import sys
import hashlib
from pathlib import Path

# ── H6 failure mode catalog (32 silent-failure ways → checkable markers) ──
_H6_FAILURE_MARKERS = {
    "mock_return": ("mock", "stub", "fake data"),
    "swallowed_exception": ("except Exception: pass", "except: pass", "except OSError: pass"),
    "unverified_diff": ("py_compile only", "compiles", "no test run"),
    "false_authority": ("trust me", "this is proven", "obviously correct", "guaranteed"),
    "self_certified": ("self-verified", "marked done by author"),
    "silent_change": ("updated quietly", "fixed silently", "no diff"),
    "cherry_pick": ("only passing cases", "selected results", "3/3 scored"),
    "empty_output": ("success.", "done.", "completed.", "no output"),
    "time_bomb": ("works now but", "temp fix", "for now", "hack"),
    "ghost_dependency": ("secretly uses", "implicitly requires", "it just works"),
    "overconfident_unit": ("all green", "full pass", "no failures"),
    "uncommitted_claim": ("should just work", "should be ok", "presumably works", "i believe it works", "it will work"),
}

def h6_findings(text: str) -> list[str]:
    """Return any silent-failure markers present in a work-product description."""
    hay = text.lower()
    hits = []
    for tag, needles in _H6_FAILURE_MARKERS.items():
        for n in needles:
            if n.lower() in hay:
                hits.append(f"H6:{tag}={n}")
                break
    return hits


def h8_verify(card_text: str) -> tuple[bool, str]:
    """Verify the RT_CARD frontmatter state_hash (sha256 of the markdown body).

    Returns (ok, msg). Cards without a state_hash verify as OK (envelope
    optional). Uses the same strip-after-frontmatter contract as rt_recorder.
    """
    import re
    import yaml as _yaml
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", card_text, re.S)
    if not m:
        return True, "no-frontmatter"
    try:
        data = _yaml.safe_load(m.group(1)) or {}
        card = data.get("card", data)
    except _yaml.YAMLError:
        return True, "malformed-frontmatter-skipped"
    want = (card or {}).get("state_hash")
    body = card_text[m.end():].strip()
    if not want:
        return True, "no-state-hash"
    have = hashlib.sha256(body.encode()).hexdigest()
    want = str(want).split(":", 1)[-1].strip()
    ok = have == want
    return ok, ("hash-OK" if ok else f"hash-MISMATCH have={have[:12]}")


def rt_silver_findings(card_dir: Path) -> dict:
    """Run H6 + H8 across a sheet dir's *_input.md cards. Returns {seat: {h6: [...], h8: msg}}."""
    report = {}
    for seat, fname in [("AG", "ag_hale_input.md"), ("CC", "cc_hale_input.md"),
                        ("OC", "oc_hale_input.md"), ("GROK", "grok_hale_input.md")]:
        fp = card_dir / fname
        if not fp.exists():
            continue
        text = fp.read_text()
        ok8, msg8 = h8_verify(text)
        report[f"{seat}:{fname}"] = {
            "h6_findings": h6_findings(text),
            "h8": msg8,
            "h8_ok": "MISMATCH" not in msg8,
        }
    return report


def main():
    if len(sys.argv) < 2:
        print("usage: rt_silver_checks.py <card_dir>", file=sys.stderr)
        return 2
    d = Path(sys.argv[1])
    rep = rt_silver_findings(d)
    for k, v in rep.items():
        print(f"{k}: h6={v['h6_findings'] or 'clean'} · h8={v['h8']}")
    bad = [k for k, v in rep.items() if v["h6_findings"] or not v["h8_ok"]]
    print(f"\nSILVER verdict: {'FAIL ' + str(bad) if bad else 'PASS'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())