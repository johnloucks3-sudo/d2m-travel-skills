# D2M CLIENT LIFECYCLE — HOW-TO REFERENCE
### Companion to `docs/CLIENT_LIFECYCLE_ARCHITECTURE.md` v1.0
### Implements: `config/lifecycle_touchpoints.json` · `scripts/lifecycle_phase_assignment.py` · `core/email/lifecycle_orchestrator.py`

---

## 1. THE THREE ZONES, OPERATIONALIZED

`scripts/lifecycle_phase_assignment.py` computes the current zone from three
dates — `booking_date`, `fpd_date`, `embark_date` (optional `disembark_date`,
defaults to `embark_date + 10 days` if not supplied):

| Zone | Window | Boundary logic |
|---|---|---|
| COMMITMENT | booking → E-180 | `today < embark_date - 180d` |
| PREPARATION | E-180 → E-30 | `embark_date - 180d <= today < embark_date - 30d` |
| EXECUTION | E-30 → D+30 | `embark_date - 30d <= today <= disembark_date + 30d` |
| COMPLETED | after D+30 | `today > disembark_date + 30d` |

`assign_phase()` returns `current_phase`, `days_remaining_in_phase`, and
`next_touchpoints` (the next 5 touchpoints — any zone — resolved to actual
calendar dates and sorted chronologically). This mirrors the origin scheme
already used by `core/scheduling/thunderbird_anchor_dates.py` (B/E/FPD/D) so
both engines can share booking data without translation.

**Test it:**
```bash
python3 scripts/lifecycle_phase_assignment.py --test
```
Runs the 3 canonical test clients (Kuklinski, McLeod, Furlow) against the
2026-07-06 scan date.

---

## 2. THE 2-WEEK DRAFT RULE

`core/email/lifecycle_orchestrator.py` enforces: **draft complete 14 days
before send**, for every touchpoint, except **TP 0.3 (insurance
recommendation)** which uses the **7-day rule** — the pre-existing-condition
waiver window closes D+14 to D+21, so insurance can't wait the standard 14
days without risking the waiver.

```python
_draft_rule_days("TP 0.3")   # -> 7
_draft_rule_days("TP 1.4")   # -> 14 (standard)
```

Each touchpoint occurrence becomes a **task card**:
```json
{
  "touchpoint_id": "TP 3.3",
  "send_date": "2026-08-08",
  "draft_due": "2026-07-25",
  "draft_rule_exception": false,
  "chain": [
    {"owner": "A2", "sequence": 1, "of": 4, "action": "Draft TP 3.3 (proposal)"},
    {"owner": "A6", "sequence": 2, "of": 4, "action": "Draft TP 3.3 (proposal)"},
    {"owner": "A9", "sequence": 3, "of": 4, "action": "Draft TP 3.3 (proposal)"},
    {"owner": "A3", "sequence": 4, "of": 4, "action": "Finalize TP 3.3 (proposal)"}
  ],
  "gate": "WF-17"
}
```
Cards are appended (deduped by client + touchpoint_id + send_date) to
`OpsCenter/state/lifecycle_task_queue.json`.

**Test it:**
```bash
python3 core/email/lifecycle_orchestrator.py --test
```

---

## 3. STAFF WORKFLOW DIAGRAM

```
A2 Research Input   →   A6 Narrative Draft   →   A9 Financial Check
        ↓                                                 ↓
                    A3 Aggregates + Voices  ←────────────┘
                            ↓
                    COS WF-17 Gate
                            ↓
                    Commander Send Approval
```

Chain order is enforced in `_owners_in_chain_order()`: named owners appear in
`A2 → A6 → A9 → A3` sequence regardless of how they're listed in the
touchpoint's `owner_primary` / `owner_secondary` fields. Roles outside the
creative chain (`COS`, `Commander`) are appended after — they route or gate,
they don't draft.

**Current org-naming note:** `config/lifecycle_touchpoints.json` preserves the
original v1.0 labels (A2/A6/A9/A3) from `CLIENT_LIFECYCLE_ARCHITECTURE.md`.
Current Thunderbird Wing persona names covering the same lanes:

| v1.0 label | Current persona | Lane |
|---|---|---|
| A2 | Dembe | Research / market intel |
| A6 | Luna | Narrative / brand copy |
| A8 *(not in v1.0)* | Reyes | Experience layer (excursions, dining, accessibility) |
| A9 | Harlan | Financial verification |
| A3 | Dani | Client voice / final send |
| COS | Hale | Routing, WF-17 gate, dossier maintenance |

The current mandatory creative chain (per `CLAUDE.md` — Amended 2026-05-30) is
Reyes → Luna → Naia → Dani → TALON+JET → WF-17, which supersedes the v1.0
A2→A6→A9→A3 sequence for **client-facing product execution**. This orchestrator
schedules and routes against the v1.0 architecture's role labels for lifecycle
*planning* purposes; when a card actually reaches drafting, route it through
the current creative chain, not directly to the legacy A-number.

---

## 4. PER-CRUISE-LINE VARIANCES

### FPD Standard
| Line | FPD | Notes |
|---|---|---|
| Regent Seven Seas | T-120 | Standard |
| Silversea | T-120 | Standard |
| Seabourn | T-120 | Standard |
| Viking | T-120 | Standard |
| Oceania | **T-90** | Verify contract — shorter window |
| Cunard | **T-90** | Verify contract — shorter window |

### Excursion Booking Window Opens
| Line | Window Opens | D2M Prep Deadline |
|---|---|---|
| Regent Seven Seas | T-180 | T-194 |
| Silversea | T-150 to T-180 | T-164 |
| Seabourn | T-180 | T-194 |
| Oceania | T-180 | T-194 |
| **Viking** | **From booking (D+0)** | **D+14 — immediate, no lead time** |
| Cunard | T-180 | T-194 |
| AmaWaterways | T-180 | T-194 |
| Ponant | T-90 to T-120 | T-104 |

### Specialty Dining Opens
| Line | Window Opens | D2M Prep Deadline |
|---|---|---|
| Regent (Chartreuse, Pacific Rim) | T-90 | T-104 |
| Silversea (La Dame) | T-120 to T-150 | T-134 |
| Seabourn (Keller Grill) — suites | T-180 | T-194 |
| Seabourn (Keller Grill) — general | T-90 | T-104 |
| Oceania | T-90 | T-104 |
| Viking | T-90 | T-104 |
| Cunard | T-90 | T-104 |
| Ponant | T-90 | T-104 |

### Pre/Post Hotel Standard
Universal across all lines: **3 nights pre-embarkation, 3 nights post-disembarkation**,
always recommended, client opts out — never opts in.

**Template standard used by `lifecycle_touchpoints.json`:** T-180 (excursions) /
T-90 (dining). The **Viking exception** (excursions open at booking, not
T-180) is not yet encoded as a per-line override in the JSON — the touchpoint
schedule is currently one universal template. If a Viking client's excursion
research (TP 2.5) needs to begin at D+14 instead of T-240 (T-8mo), override it
manually per-client until a per-line variance table is added to the config
(tracked as a follow-up, not built in this pass — see § 5).

---

## 5. KNOWN LIMITATIONS / FOLLOW-UPS

- **No per-cruise-line override table in `lifecycle_touchpoints.json`** — all
  39 touchpoints use the universal T-180/T-90 windows. Viking's D+0 excursion
  window is documented above but not yet enforced in code.
- **`disembark_date` defaults to `embark_date + 10 days`** if not supplied to
  `assign_phase()` — always pass the real disembark date when known; the
  default is only a fallback for incomplete booking data.
- **`next_touchpoints()` returns at most 5 items** — sufficient for the
  30–60 day planning horizon the orchestrator uses; raise `limit` if a wider
  scan is needed (e.g. full-lifecycle audit).
- **`lifecycle_orchestrator.py` writes task cards, it does not execute them.**
  Actually drafting content still goes through the standing creative chain
  (Reyes/Luna/Naia/Dani) and WF-17 gate per `CLAUDE.md`.

---

*Thunderbird Wing | D2M Client Lifecycle Architecture — Reference Implementation | 2026-07-06*
