# PARA Adapted for Thunderbird Wing

**BLUF:** Thunderbird's 112 top-level dirs reorganized into Tiago Forte's PARA (Projects · Areas · Resources · Archive). No files moved — this is the **map**, not the migration. Physical moves are optional, gated, and must not break imports/systemd hooks.

| PARA Bucket | Definition | Thunderbird Target |
|---|---|---|
| **P**rojects | Short-term efforts with a finish line | Mission board + `Plans/` + active deliverables |
| **A**reas | Ongoing responsibilities you maintain | Personas, `ops/`, `OpsCenter/`, `routines/` |
| **R**esources | Reference material you may need | `docs/`, `dossiers/`, `intel/`, `references/`, `standing_orders/` |
| **A**rchive | Inactive stuff from the other three | `archive/`, `FOR_DELETION/`, `backups/`, `Outputs/` |

---

## 🟦 PROJECTS — things with a deadline / finish line

> *Current → `mission_board_sync.py list` · `Plans/` · `output/`*

| Dir | Role | Status Gate |
|---|---|---|
| `Plans/` | Approved + drafted implementation plans | Commander-approved before commit |
| `output/` | Active deliverable output (dashboards, PDFs) | Current |
| `drafts/` | Email + product drafts in flight | WF-17 gate |
| `architect_sessions/` | Trip Architect active sessions | Commander approval per session |
| `Commander_Review/` | Items staged for Commander read | Must drain before close |
| `mission board` (via `OpsCenter/`) | Live P0-P3 tasking | `mission_board_sync.py` only |
| `validations/` | In-flight trip validations | 6-step sign-off |
| `lead/`, `incoming/`, `routing_tickets/` | New work inbound queue | Triage → project or archive |

## 🟩 AREAS — ongoing responsibilities (maintain, not finish)

> *These are the standing seats, SOPs, and always-on systems.*

| Dir | Area Owned |
|---|---|
| `core/` | All Wing code — the living brain |
| `ops/` + `OpsCenter/` | Hale's operations center: logs, queues, state |
| `Personas/` + `persona_memory/` | Wing staff identities + memory |
| `routines/` | Standing daily/weekly rituals |
| `standing_orders/` | Doctrine — Sterling owns edits |
| `scripts/` | Operational tooling |
| `business/` + `D2M/` + `Commercial/` | Company ops (brand, commissions, tiers) |
| `templates/` | Reusable email/PDF/stationery |
| `workflows/`, `routines/`, `recipes/` | Repeatable procedures |
| `state/`, `hale_state*`, `voice_ledger.json` | Live Wing state |
| `systemd/`, `timers/` | Scheduled automation |

## 🟨 RESOURCES — reference you pull when needed

| Dir | Content |
|---|---|
| `docs/` | Design docs, audits, position papers |
| `dossiers/` (canonical) | Client trip dossiers — **primary** |
| `Dossiers/` + `dossiers_json/` | ⚠️ duplicates of above — archive candidates |
| `intel/` + `intel_web/` + `scraping_intel/` | Research + OSINT products |
| `references/` | Quick-reference (palettes, formats) |
| `templates/` | (shared with Areas) |
| `research/` | Deep-dive outputs |
| `media/` + `images/` + `restaurant_images/` | Visual assets |
| `manuals/` + `specs/` + `examples/` | Learning material |
| `recipes/` | Tested procedures |

## ⬛ ARCHIVE — inactive, kept for reference

| Dir | Note |
|---|---|
| `archive/` | Primary archive |
| `backups/` + `backup_staging/` | Backup copies |
| `FOR_DELETION/` | Staged for deletion — purge after review |
| `Outputs/` | ⚠️ duplicate of `output/` — merge into archive |
| `tmp/` + `scratch/` | Ephemeral |
| `vendor/` | Third-party pinned code |

---

## ⚠️ FINDINGS (duplicates / cleanup candidates)

| Finding | Confidence | Severity |
|---|---|---|
| `output/` vs `Outputs/` — duplicate dirs | High | Med |
| `dossiers/` vs `Dossiers/` vs `dossiers_json/` — 3 copies | High | Med |
| `bryana/` vs `Bryana/` — case duplicate | High | Low |
| `agents/` vs `Agents_NEW/` vs `agent_docs/` — overlap | Med | Med |
| `FOR_DELETION/` has content in `core/`, `OpsCenter/` — verify before purge | High | High |

---

## RECOMMENDATION
1. Keep this as the **map** — do not move dirs yet (imports + systemd hooks break).
2. Fix the 5 duplicate findings first (archive the stale copy each time).
3. Route all NEW work: Project → `Plans/` + mission board · Area → `core/`/`ops/` · Resource → `docs/`/`references/` · Done → `archive/`.
