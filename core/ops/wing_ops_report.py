"""
core/ops/wing_ops_report.py — daily Wing Ops digest for the consolidated briefs.

Commander directive 2026-07-29 (Wing Oversight, Delegation & Transparency):
transparency on successes AND failures, not just when CC happens to mention
one. Real-time failures already page via core.staffing.delegation_outcomes.
page_commander(); this is the routine, daily rollup — wired into the two
existing consolidated brief engines (SO-REPORTING-2026) rather than a new
daemon, same pattern as their build_tcd_suspense_section/
build_fare_watch_section.
"""
from __future__ import annotations

import logging

log = logging.getLogger("wing_ops_report")


def build_wing_ops_digest(since_hours: float = 24) -> dict:
    """Pull the compliance rollup, quality scorecard, and per-seat budget
    status. No new usage-fetcher — no public usage API exists for CC/OC/AG
    (core.ai_infra.seat_budget's own docstring), so staleness is shown
    honestly via its existing ⚠STALE convention rather than invented."""
    since_days = max(since_hours / 24.0, 1 / 24.0)

    try:
        from core.staffing.delegation_outcomes import rollup_stats
        stats = rollup_stats(since_days=since_days)
    except Exception as e:
        log.warning("rollup_stats unavailable: %s", e)
        stats = {}

    try:
        from core.silver.scorecard import summary as scorecard_summary
        scorecard = scorecard_summary()
    except Exception as e:
        log.warning("scorecard summary unavailable: %s", e)
        scorecard = {}

    budgets = {}
    try:
        from core.ai_infra.seat_budget import seat_status
        for seat in ("CC", "OC", "AG"):
            budgets[seat] = seat_status(seat)
    except Exception as e:
        log.warning("seat_budget unavailable: %s", e)

    return {"since_hours": since_hours, "stats": stats, "scorecard": scorecard, "budgets": budgets}


def build_wing_ops_section(digest: dict) -> str:
    """HTML section matching the existing dark-navy (#07076b) table style
    used by morning_consolidated_brief_engine.build_tcd_suspense_section /
    build_fare_watch_section."""
    stats = digest.get("stats") or {}
    scorecard = digest.get("scorecard") or {}
    budgets = digest.get("budgets") or {}

    if not stats:
        return '<p style="color:#64748b;font-style:italic;">Wing Ops ledger unavailable this cycle.</p>'

    # SILENCE IS NOT GREEN.
    #
    # Until 2026-07-29 this section rendered "no discrepancies, blocks, or drops
    # this window ✅" whenever `fail_bits` was empty — which, with a ledger
    # holding 4 rows, meant it rendered green in every brief regardless of
    # whether anything had ever been checked. That green line went to the
    # Commander twice a day and reported an absence of evidence as evidence of
    # absence. The `if not stats` guard above never caught it, because
    # rollup_stats() always returns a fully-populated dict of zeros.
    #
    # A zero with no denominator is a lie of omission. Every rollup in this
    # system must distinguish "checked and clean" from "nothing was checked."
    total = stats.get("total", 0) or 0

    fail_bits = []
    if stats.get("discrepancies_caught"):
        fail_bits.append(f'<span style="color:#dc2626;font-weight:bold;">{stats["discrepancies_caught"]} discrepancy(ies) caught</span>')
    if stats.get("blocked_certifications"):
        fail_bits.append(f'<span style="color:#dc2626;font-weight:bold;">{stats["blocked_certifications"]} certification(s) blocked</span>')
    if stats.get("dropped"):
        fail_bits.append(f'<span style="color:#dc2626;font-weight:bold;">{stats["dropped"]} OC ticket(s) dropped</span>')
    if stats.get("follow_up_overdue"):
        fail_bits.append(f'<span style="color:#ea580c;font-weight:bold;">{stats["follow_up_overdue"]} follow-up(s) overdue</span>')
    if stats.get("self_execute_unjustified"):
        fail_bits.append(f'<span style="color:#ca8a04;font-weight:bold;">{stats["self_execute_unjustified"]} unjustified self-execute(s)</span>')
    if fail_bits:
        fail_line = " &nbsp;|&nbsp; ".join(fail_bits)
    elif total == 0:
        # Matches the ⚠STALE convention already used for budgets below.
        fail_line = ('<span style="color:#ea580c;font-weight:bold;">⚠ 0 outcomes logged this '
                     'window — NOTHING WAS CHECKED.</span> '
                     '<span style="color:#64748b;">This is not a clean bill of health. '
                     'Either no delegations ran, or the oversight layer is not recording. '
                     'Verify before treating as green.</span>')
    else:
        fail_line = (f'<span style="color:#16a34a;">no discrepancies, blocks, or drops '
                     f'across {total} checked outcome(s) ✅</span>')

    # The oversight layer's own liveness. A silent sensor is worse than no
    # sensor — "monitor efficacy, not presence." If the reaper has stopped,
    # every clean line above is unsupported and must say so.
    try:
        from core.oversight.reaper import reaper_is_healthy
        healthy, health_msg = reaper_is_healthy()
        if not healthy:
            fail_line = (f'<span style="color:#dc2626;font-weight:bold;">⚠ OVERSIGHT LAYER '
                         f'DEGRADED: {health_msg}</span><br>' + fail_line)
    except Exception:
        pass

    budget_cells = ""
    for seat in ("CC", "OC", "AG"):
        b = budgets.get(seat, {})
        pct = f"{b['weekly_pct']:.0f}%" if b.get("weekly_pct") is not None else "?"
        stale = ' <span style="color:#ea580c;">⚠STALE</span>' if b.get("stale") else ""
        budget_cells += f'<td style="padding:8px 10px;border:1px solid #e2e8f0;">{seat}: {pct}{stale}</td>'

    sc_rows = ""
    for seat, cats in sorted(scorecard.items()):
        totals = {"pass": 0, "fail": 0, "redo": 0, "hit": 0, "miss": 0}
        for cat, cell in cats.items():
            for k in totals:
                totals[k] += cell.get(k, 0)
        sc_rows += (f'<tr><td style="padding:6px 10px;border:1px solid #e2e8f0;font-weight:600;">{seat}</td>'
                    f'<td style="padding:6px 10px;border:1px solid #e2e8f0;color:#16a34a;">{totals["pass"]+totals["hit"]} pass</td>'
                    f'<td style="padding:6px 10px;border:1px solid #e2e8f0;color:#dc2626;">{totals["fail"]+totals["miss"]} fail</td>'
                    f'<td style="padding:6px 10px;border:1px solid #e2e8f0;color:#ca8a04;">{totals["redo"]} redo</td></tr>')
    if not sc_rows:
        sc_rows = '<tr><td colspan="4" style="padding:6px 10px;color:#64748b;font-style:italic;">No scorecard evidence yet.</td></tr>'

    return f"""
<p style="font-size:13px;margin:4px 0 10px;">{fail_line}</p>
<table style="width:100%;border-collapse:collapse;margin:6px 0;font-size:13px;">
    <tr style="background:#07076b;color:#fff;">
        <th colspan="3" style="padding:8px 10px;text-align:left;">Per-seat budget (⚠STALE = data older than 24h, no public usage API)</th>
    </tr>
    <tr>{budget_cells}</tr>
</table>
<table style="width:100%;border-collapse:collapse;margin:10px 0;font-size:13px;">
    <tr style="background:#07076b;color:#fff;">
        <th style="padding:8px 10px;text-align:left;">Seat</th>
        <th style="padding:8px 10px;text-align:left;">Pass</th>
        <th style="padding:8px 10px;text-align:left;">Fail</th>
        <th style="padding:8px 10px;text-align:left;">Redo</th>
    </tr>
    {sc_rows}
</table>
<p style="font-size:12px;color:#64748b;margin-top:4px;">
    {stats.get('total', 0)} logged outcomes / {digest.get('since_hours', 24):.0f}h &nbsp;·&nbsp;
    self-exec:{stats.get('self_execute_count', 0)} &nbsp;·&nbsp; delegated:{stats.get('delegate_count', 0)} &nbsp;·&nbsp;
    verified-PASS:{stats.get('verified_pass', 0)} &nbsp;·&nbsp; certified:{stats.get('certified_pass', 0)}
    &nbsp;·&nbsp; Source: OpsCenter/delegation_outcomes.jsonl
</p>
"""
