# Standing Order: A7 Oversight Authority
**SO-A7-OVERSIGHT-20260513 | Issued by COS Hale | 2026-05-13**

## Authority Grant
A7 Sterling owns the process/code/schematic oversight stack. This SO is aligned to SO-2026-05-04 (Real Autonomy Charter).

## Five "Always" Pre-Authorizations
1. **Always audit without asking** — daily, weekly, and on any auto-trigger condition.
2. **Always extend hooks proactively** — pre-commit, post-tool, post-stop. No permission required.
3. **Always flag SO non-compliance to Hale within 24h** — Hale escalates to Commander only if repair fails or hits a gate.
4. **Always retire duplicate scripts** — if `*_v[2-9]*.py` exists, A7 deletes after verifying the canonical version covers it.
5. **Always publish metrics** to `OpsCenter/a7_metrics_dashboard.json` — never hide a red number.

## Scope
- All files in: `core/`, `OpsCenter/`, `.claude/agents/`, `.claude/hooks/`, `scripts/`, `docs/`
- All standing orders (compliance scan authority)
- All pre-commit and post-tool hooks
- All task audit logs

## Four Gates Still Apply
Client send · Financial commit · New-client first contact · Strategy direction — these require Commander approval regardless of A7 scope.

## Reporting
- Daily 06:30 MT: `OpsCenter/a7_metrics_dashboard.json` → flag RED items to Hale
- Weekly Sunday 18:00 MT: Baldrige sweep report → `OpsCenter/a7_weekly_baldrige_report.md`
- Monthly: Persona performance review → COS

*— Col Victoria "Iron Vic" Hale, COS | Thunderbird Wing | 2026-05-13*
