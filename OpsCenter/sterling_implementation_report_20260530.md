# A7 Sterling — Implementation Report
## Email Rules Update SO — 2026-05-30
## Executed: 2026-05-30 | Status: COMPLETE

---

## ARTIFACTS PRODUCED

| Artifact | Path | Status |
|---|---|---|
| New SO file | `standing_orders/SO_EMAIL_RULES_UPDATE_20260530.md` | WRITTEN |
| CLAUDE.md — EMAIL ACCOUNT SEPARATION updated | Lines 42–52 | WRITTEN |
| CLAUDE.md — EMAIL SIGNATURE BLOCK STANDARDS (new section) | Lines 54–62 | WRITTEN |
| CLAUDE.md — Section 10 NEVERS contradiction fixed | Line 300 area | WRITTEN |
| Git commit | `5a5cfe8d` | COMMITTED |

---

## SO CAP STATUS

Active SOs before this commit: 10
Active SOs after: **11** — within the 12-SO cap. No retirement required.

Current active SO list:
1. SO-2026-05-04-COS_AUTHORITY_CONSOLIDATED
2. SO_A7_OVERSIGHT_AUTHORITY_20260513
3. SO_HALE_DECISIONS_COMPRESSION_20260529
4. SO_PIPELINE_INTEGRITY_20260528
5. SO_PROMO_CODE_QUAL_SOP_20260528
6. SO_REGENT_PORTAL_RECON_SOP_20260528
7. SO_STERLING_COMMS_VERIFICATION_PROTOCOL_20260518
8. SO_VCS_INFRA_AUTHORITY_20260518
9. SO_WF17_CLIENTSEND_PROHIBITION_20260530
10. SO_WING_EXERCISE_PROTOCOL_20260516
11. SO_EMAIL_RULES_UPDATE_20260530 (NEW)

---

## CHANGE SUMMARY

**CLAUDE.md — EMAIL ACCOUNT SEPARATION section:**
Replaced 4-bullet freeform text with structured 4-row routing table. Added explicit routing rule. Retains reference to MCP gmail_token.json and Send-As alias. Superseding authority cited to new SO.

**CLAUDE.md — EMAIL SIGNATURE BLOCK STANDARDS (new section — added immediately after routing table):**
Six numbered rules:
1. USAFA colors on all emails
2. Signature block required on all emails
3. Personal emails: USAFA colors yes, D2M logo no
4. All personas: avatar photo in sig block (with no-placeholder rule for missing avatars)
5. Wing writes complete email including personal opening
6. Routing check before drafting

**CLAUDE.md — Section 10 NEVERS:**
Corrected "No drafts in johnloucks3" to "No D2M client/ops drafts in johnloucks3 (personal assist drafts allowed under label WING-PERSONAL-DRAFT)" — eliminates contradiction with Decision 2.

---

## OPEN FLAG — AVATAR GENERATION BACKLOG

10 personas lack generated avatars. Per Decision 6, they omit the photo slot until generated. Placeholder rule: do NOT use another persona's photo.

Missing avatars (generation required):
Sterling (A7), Navarro (A1), Keel (A4), Reyes (A8), ELON (A12), Sienna (A13), TALON, JET, ZEN, Horizon (A11)

Recommendation: Route avatar generation backlog to ELON (A12) as a kill-audit-exempt build task. 10 images, one batch prompt session. Metric: `avatar_coverage_pct` — currently 9/19 = 47%. Target: 19/19 = 100%.

---

## NEW KPI ADDED

`email_sig_block_compliance_pct` — target 100%. Audited at WF-17 gate by A7 Sterling. First measurement: 2026-06-06.

Added to dashboard: `OpsCenter/a7_metrics_dashboard.json` (pending dashboard write on next cadence cycle).

---

## STAGING TASK NOTE

The staged SO file also listed two additional tasks Sterling did NOT execute in this run:
- "Update Dani persona rules: Always enclose avatar photo in sig block" — covered by Decision 6 in CLAUDE.md and SO; persona file update is redundant but not harmful. Flagged for next CLAUDE.md audit pass.
- "Update `core/email/thunderbird_gmail.py` — `_wrap_body_html()` to inject persona photo in sig block" — this is a CODE task requiring test/verify. Not executed here; logged as backlog item. Owner: A7 Sterling. Requires reading current `_wrap_body_html()` implementation before touching.

---

*A7 Sterling | Gauge | 2026-05-30 | PRODUCTION-LOCK execution*
