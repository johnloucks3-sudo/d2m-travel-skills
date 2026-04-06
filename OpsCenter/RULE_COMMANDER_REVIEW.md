# OPERATIONAL RULE: All OpsCenter Output → Commander_Review
## Rule established: 2026-04-04 by COS Hale

**Directive:** Every .md, .txt, and report generated in or under `~/Thunderbird/OpsCenter/`
shall be copied to `~/Thunderbird/Commander_Review/` within 5 minutes of creation.

**Purpose:** Commander has full visibility into all staff output, assessments, and designs.
Nothing is written that the Commander cannot review.

**Includes:**
- All .md assessment reports
- All .txt briefs
- All design specs
- All task manifests
- All activity boards

**Exclusions:**
- .py files (code, not assessments)
- .json config files unless specifically for Commander review
- Temporary/cache files
- __pycache__ directories

**Implementation:** Copyscript runs on every OpsCenter file write via the watcher.
Also: manual sync done on demand.

**Current Status:** First batch synced — 69 files in Commander_Review.
