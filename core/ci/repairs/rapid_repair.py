#!/usr/bin/env python3
"""
CI Rapid-Repair — LIVE DISPATCH (the cutover front door)
Dreams2Memories Travel, LLC · Thunderbird Wing · Sterling (A7) · 2026-07-02

This is the SAFE replacement for the raw unattended engine. It determines the
RED CI skills and runs each through the safety-contract runner
(schema.run_capability) with a CONSERVATIVE armed-tier policy.

CONSERVATIVE CUTOVER — ARM SAFE ONLY
------------------------------------
    ARMED_TIERS = {"SAFE"}   (see config/ci_rapid_repair_policy.json)

    SAFE (effective)         -> apply=True  -> auto-applied + verify-after
    CAUTION (effective)      -> STAGED (armed_tiers gate in run_capability)
    DESTRUCTIVE (effective)  -> STAGED (tier gate in run_capability, unconditional)

Widening ARMED_TIERS to include "CAUTION" is a Commander/Hale call, made AFTER
validation. It is a one-line change to the policy file; no code edit.

WHY THIS FILE EXISTS (the hazard it removes)
--------------------------------------------
The old path (ci_auto_repair_integration.py -> ci_auto_repair_engine.main())
fired ALL raw repair_ functions unattended on every RED heartbeat, INCLUDING
destructive ones (source-file rewrites, settings.json edits, registry recreation)
with NO tier gate. This file replaces that with explore->assess->tier-gate->
dry-run-by-default->verify-after, and a durable cross-spawn anti-flap gate.

RED SOURCE (advisor #3)
-----------------------
We read the CI registry as RAW JSON (tolerating BOTH schemas: the 47 entries
that use id/health_probe AND the stray entry that uses skill/probe_script) and
run each probe via ci_health.run_probe(). We DO NOT call load_registry() — it
raises today on a malformed entry (litellm-gateway), which would take the whole
sweep down. Defensive-read keeps rapid-repair working even when the registry
schema is temporarily inconsistent.

NON-BLOCKING (advisor #2)
-------------------------
48 probes at up to 60s each + verify-settle sleeps can run for minutes. The
infra_bot heartbeat MUST NOT block on that. integration.py spawns THIS file
DETACHED (subprocess.Popen, start_new_session=True). run_all_red() is safe to
call inline too (tests do), but the live heartbeat path spawns it.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
if str(THUNDERBIRD_ROOT) not in sys.path:
    sys.path.insert(0, str(THUNDERBIRD_ROOT))

CI_REGISTRY = THUNDERBIRD_ROOT / "config" / "ci_registry.json"
POLICY_FILE = THUNDERBIRD_ROOT / "config" / "ci_rapid_repair_policy.json"
DISPATCH_LOG = THUNDERBIRD_ROOT / "logs" / "ci_rapid_repair.log"
NOTIFY_DEDUP = THUNDERBIRD_ROOT / "OpsCenter" / ".ci_rapid_repair_notify_dedup.json"

# --- Registry import so all 48 capabilities self-register in schema.REGISTRY ---
# (Clusters register on import via the @repair_capability decorator.)
import core.ci.repairs.cluster_a   # noqa: F401,E402
import core.ci.repairs.cluster_b   # noqa: F401,E402
import core.ci.repairs.cluster_c   # noqa: F401,E402
import core.ci.repairs.cluster_d   # noqa: F401,E402
import core.ci.repairs.cluster_e   # noqa: F401,E402
import core.ci.repairs.cluster_f   # noqa: F401,E402
import core.ci.repairs.cluster_g   # noqa: F401,E402
import core.ci.repairs.cluster_h   # noqa: F401,E402
import core.ci.repairs._worked_examples  # noqa: F401,E402

from core.ci.repairs.schema import (  # noqa: E402
    REGISTRY, run_capability, Decision, WAREHOUSE_AUDIT,
)

# ============================================================================
# POLICY — armed tiers (documented, operator-editable without touching code)
# ============================================================================

# CONSERVATIVE CUTOVER: arm SAFE ONLY. Widen to {"SAFE","CAUTION"} after
# validation — Commander/Hale call. DESTRUCTIVE is NEVER armable (tier gate is
# unconditional in run_capability; adding it here does nothing).
ARMED_TIERS = {"SAFE"}

# Commander 2026-08-07: KILL all airfare session keep-alives (Centrav etc.)
# EXCEPT Skybird. fare-watch-centrav must NEVER auto-relogin — session keepalive
# is Skybird-only now. Report RED, take NO auto-repair action on these.
SUPPRESSED_AUTO_SKILLS = {"fare-watch-centrav"}


def _load_policy() -> set:
    """Read ARMED_TIERS from the policy file; fall back to the SAFE-only default.
    The file is where Hale/Commander see and change the auto-arm policy."""
    if POLICY_FILE.exists():
        try:
            data = json.loads(POLICY_FILE.read_text())
            tiers = data.get("armed_tiers")
            if isinstance(tiers, list) and tiers:
                # DESTRUCTIVE can never be armed regardless of file contents.
                return {t for t in tiers if t in ("SAFE", "CAUTION")}
        except Exception as e:
            _log(f"policy read failed ({e}) — falling back to SAFE-only default")
    return set(ARMED_TIERS)


# ============================================================================
# LOG
# ============================================================================


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(msg: str) -> None:
    try:
        DISPATCH_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(DISPATCH_LOG, "a") as f:
            f.write(f"{_now()} [RAPID-REPAIR] {msg}\n")
    except Exception:
        pass


# ============================================================================
# RED SOURCE — defensive raw-JSON read, both schemas, ci_health.run_probe
# ============================================================================


def _registry_entries() -> list[dict]:
    """Return [{'skill_id','probe','client_affecting'}] read defensively from the
    raw registry JSON, tolerating BOTH the id/health_probe schema and the stray
    skill/probe_script schema. NEVER calls load_registry() (which raises today)."""
    out: list[dict] = []
    try:
        data = json.loads(CI_REGISTRY.read_text())
    except Exception as e:
        _log(f"registry read failed: {e}")
        return out
    for s in data.get("skills", []):
        sid = s.get("id") or s.get("skill")
        probe = s.get("health_probe") or s.get("probe_script")
        if not sid or not probe:
            continue
        out.append({
            "skill_id": sid,
            "probe": probe,
            "client_affecting": bool(s.get("client_affecting", False)),
        })
    return out


def determine_red_skills() -> list[dict]:
    """Run each registry probe and return the entries that are RED (probe rc!=0)."""
    try:
        from core.ci.ci_health import run_probe
    except Exception as e:
        _log(f"ci_health.run_probe import failed: {e} — cannot determine RED skills")
        return []
    red = []
    for e in _registry_entries():
        try:
            ok, _detail, _ms, _to = run_probe(e["probe"])
        except Exception as ex:
            _log(f"probe raised for {e['skill_id']}: {ex} — treating as RED")
            ok = False
        if not ok:
            red.append(e)
    return red


# ============================================================================
# NOTIFY — one line on NEW AUTO_APPLIED / STAGED, deduped so we don't spam
# ============================================================================


def _load_dedup() -> dict:
    if NOTIFY_DEDUP.exists():
        try:
            return json.loads(NOTIFY_DEDUP.read_text())
        except Exception:
            pass
    return {}


def _save_dedup(d: dict) -> None:
    try:
        NOTIFY_DEDUP.parent.mkdir(parents=True, exist_ok=True)
        NOTIFY_DEDUP.write_text(json.dumps(d, indent=2))
    except Exception as e:
        _log(f"dedup save failed: {e}")


def _notify_once(key: str, msg: str, client_affecting: bool, dedup: dict,
                 window_seconds: int = 3600, recovered: bool = False,
                 staged: bool = False) -> None:
    """Page Telegram (via hale_notify) at most once per key per window. Only
    called for NEW AUTO_APPLIED and NEW STAGED — never for BLOCKED_* / reused
    tokens, so a persistently-RED skill does not page every heartbeat.

    recovered=True only when a repair APPLIED **and verify-after was GREEN** — so
    we never send the "auto-repaired, no action needed" flavor for a SAFE repair
    that ran but failed verification (that must escalate, not reassure)."""
    last = dedup.get(key)
    now = datetime.now(timezone.utc).timestamp()
    if last is not None and (now - last) < window_seconds:
        return
    try:
        from core.notify.hale_notify import notify_hale
        notify_hale("ci-rapid-repair", key, msg,
                    repaired=recovered,
                    client_affecting=client_affecting,
                    staged=staged)
    except Exception as e:
        _log(f"notify failed for {key}: {e}")
    dedup[key] = now


# ============================================================================
# THE DISPATCH
# ============================================================================


def run_all_red(armed_tiers: Optional[set] = None, notify: bool = True) -> dict:
    """
    Determine RED CI skills and run each through the safety-contract runner.

    For each RED skill with a registered RepairSpec:
        run_capability(skill_id, apply=(policy allows auto-apply), armed_tiers=...)
    The armed_tiers whitelist is threaded into the runner so ONLY effective-tier
    SAFE skills auto-apply; CAUTION + DESTRUCTIVE are STAGED (apply gated).

    Returns a summary dict. Every decision is already audited by run_capability
    to OpsCenter/ci_repair_warehouse_audit.jsonl; this function adds a rollup line
    to logs/ci_rapid_repair.log and (optionally) one-line Telegram pages on NEW
    APPLIED/STAGED outcomes (deduped).

    Wrapped so ANY error is logged and returns gracefully — this is called
    (detached) from the infra_bot heartbeat path and must NEVER crash it.
    """
    armed = set(armed_tiers) if armed_tiers is not None else _load_policy()
    summary = {
        "ts": _now(),
        "armed_tiers": sorted(armed),
        "red_count": 0,
        "decisions": {},          # decision -> count
        "per_skill": [],          # [{skill_id, decision, effective_tier, token, note}]
        "no_capability": [],      # RED skills with no RepairSpec
        "error": None,
    }
    try:
        red = determine_red_skills()
        summary["red_count"] = len(red)
        _log(f"determine_red_skills -> {len(red)} RED "
             f"({[e['skill_id'] for e in red]}); armed={sorted(armed)}")

        dedup = _load_dedup() if notify else {}

        for e in red:
            sid = e["skill_id"]
            client_affecting = e["client_affecting"]
            if sid not in REGISTRY:
                summary["no_capability"].append(sid)
                _log(f"{sid}: RED but NO RepairSpec registered — skipping (no-op)")
                continue

            if sid in SUPPRESSED_AUTO_SKILLS:
                _log(f"{sid}: SUPPRESSED — Commander 2026-08-07 killed airfare keep-alives "
                     f"except Skybird; Centrav on-demand only. No auto-repair.")
                summary["per_skill"].append({
                    "skill_id": sid, "decision": "SUPPRESSED", "note":
                    "Centrav on-demand only; no auto-relogin (Commander 2026-08-07)"})
                continue

            # SAFE-only cutover: request apply=True; the runner + armed_tiers gate
            # decide whether it actually auto-applies or gets staged.
            try:
                r = run_capability(sid, apply=True, armed_tiers=armed)
            except Exception as ex:
                _log(f"{sid}: run_capability raised (contained): {ex}")
                summary["decisions"]["ERROR"] = summary["decisions"].get("ERROR", 0) + 1
                summary["per_skill"].append({
                    "skill_id": sid, "decision": "ERROR",
                    "effective_tier": None, "token": None, "note": str(ex)[:200],
                })
                continue

            dec = r.decision.value
            summary["decisions"][dec] = summary["decisions"].get(dec, 0) + 1
            summary["per_skill"].append({
                "skill_id": sid,
                "decision": dec,
                "effective_tier": r.risk_tier.value,
                "token": r.staged_token,
                "note": r.note,
            })
            _log(f"{sid}: {dec} tier={r.risk_tier.value} "
                 f"before={r.verify_before.value} after={r.verify_after.value} "
                 f"token={r.staged_token} — {r.note}")

            if notify:
                if r.decision == Decision.AUTO_APPLIED:
                    recovered = (r.verify_after.value == "GREEN")
                    verb = "AUTO-REPAIRED" if recovered else "APPLIED but verify still RED — escalating"
                    _notify_once(
                        f"AUTO_APPLIED:{sid}",
                        f"CI rapid-repair '{sid}' {verb} (verify={r.verify_after.value})",
                        # a failed SAFE repair on a client-affecting skill must reach Commander
                        client_affecting=(client_affecting and not recovered),
                        dedup=dedup,
                        recovered=recovered,
                    )
                elif r.decision == Decision.STAGED:
                    # Dedup key is the SKILL, deliberately NOT the token. Each staging
                    # run mints a fresh token, so keying on it made every key new and the
                    # suppression window never once engaged: 323 pages across 3 skills in
                    # the 7 days to 2026-07-29 (146 fare-watch-centrav, 140 home-dir-health,
                    # 37 lifecycle-travel-surveys), one per token, 46/day and climbing.
                    # The token still travels in the message body so the Commander can
                    # confirm the current one.
                    _notify_once(
                        f"STAGED:{sid}",
                        f"CI rapid-repair STAGED '{sid}' "
                        f"({r.risk_tier.value}) token={r.staged_token} — one-touch confirm to apply",
                        client_affecting, dedup,
                        window_seconds=86400,   # one ask per skill per day, not per run
                        staged=True,            # success awaiting approval, NOT a failure
                    )
                # BLOCKED_*, DRY_RUN, SKIPPED_HEALTHY, reused tokens -> no page.

        if notify:
            _save_dedup(dedup)

        _log(f"ROLLUP: red={summary['red_count']} decisions={summary['decisions']} "
             f"no_capability={summary['no_capability']}")
    except Exception as ex:
        summary["error"] = str(ex)
        _log(f"run_all_red top-level error (contained): {ex}")
    return summary


# ============================================================================
# CLI — integration.py spawns this DETACHED; also runnable by hand
# ============================================================================


def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="CI rapid-repair live dispatch (safe path)")
    p.add_argument("--no-notify", action="store_true",
                   help="do not page Telegram (dry-run / test mode)")
    p.add_argument("--dry-run-all", action="store_true",
                   help="run EVERY registered capability with apply=False (no mutation, no RED filter)")
    p.add_argument("--arm", default=None,
                   help="override armed tiers, comma-separated (e.g. SAFE or SAFE,CAUTION)")
    args = p.parse_args(argv)

    if args.dry_run_all:
        # Full dry-run sweep of the whole warehouse (used by tests). Zero mutation.
        rows = []
        for sid in sorted(REGISTRY.keys()):
            try:
                r = run_capability(sid, apply=False)
                rows.append((sid, r.decision.value, r.risk_tier.value))
            except Exception as ex:
                rows.append((sid, f"ERROR:{ex}", "?"))
        for sid, dec, tier in rows:
            print(f"{sid:32s} {dec:18s} tier={tier}")
        return 0

    armed = None
    if args.arm:
        armed = {t.strip().upper() for t in args.arm.split(",") if t.strip()}
    summary = run_all_red(armed_tiers=armed, notify=not args.no_notify)
    print(json.dumps(summary, indent=2))
    return 0 if summary.get("error") is None else 1


if __name__ == "__main__":
    sys.exit(main())
