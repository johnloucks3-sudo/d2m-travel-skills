# Commission Reconciliation — 2026-07-02
**Auditor:** Brig Gen (Ret.) Thomas "Gauge" Sterling, A7 (with Harlan A9 as primary source)
**Source data:** `hale_state.json` financial_pulse + Harlan MISSION-426 note (2026-06-24) + `scripts/spawn_commission_audit.py` PDF-confirmed figures

---

## The Gap

| Source | Figure | Basis |
|---|---|---|
| Sheet (commission_expected) | $21,849.16 | Flat 15%/80% assumption — wrong |
| Harlan verified (harlan_verified_total field) | $18,830.83 | `hale_state.json` field |
| Harlan note breakdown sum | $18,830.93 | See below |
| **Delta (field vs sheet):** | **$3,018.33** | |
| **Delta (note sum vs sheet):** | **$3,018.23** | |

**Arithmetic discrepancy flag (A7):** The Harlan note lists components that sum to $18,830.93, but the `harlan_verified_total` JSON field reads $18,830.83 — a $0.10 difference. This is an internal inconsistency in Harlan's own record. Route to Harlan to confirm which figure is authoritative before updating the canonical total.

---

## Harlan Breakdown (MISSION-426, 2026-06-24)

| Component | Amount |
|---|---|
| Confirmed | $6,493.72 |
| Estimated | $12,060.10 |
| Ancillary | $277.11 |
| **Sum** | **$18,830.93** |

Note: the JSON field `harlan_verified_total` = **$18,830.83** does not match this sum. Difference: $0.10.

---

## Root Cause of $3K Gap

**Two identified causes:**

### Cause 1 — Flat 15%/80% assumption (primary driver)
The sheet applies a uniform 15% commission rate and 80% D2M split to all bookings. Actual host agency tiers differ by booking:
- Nexion (Regent bookings): 15% commission, **70%** D2M split (not 80%)
- C&TU / Cruises and Tours Unlimited (Regent): 17% commission, **80%** D2M split
- Viking direct: 17% commission, **80%** D2M split
- Silversea: 16%+1% NCF, **70%** D2M split

Four bookings (Ely/Darrow, Furlow, Nichols, McLeod June 2026) were calculated at 80% when the correct D2M split is 70%. That overcounts D2M share by approximately 10 percentage points on those bookings.

### Cause 2 — Interline booking counted as D2M (secondary driver)
Booking 566910-25 (Loucks Silver Nova Tokyo-Seattle, BN 566910-25): The agent of record is "Interline Travel & Tour," NOT D2M. Commission is zero for D2M. This booking was counted in the sheet commission total. Removal required.

### Cause 3 — Commission column contains deposit amounts (data quality)
Per `spawn_commission_audit.py` notes: "The 'Commission' column contains DEPOSIT AMOUNTS not actual TA commission." The sheet's commission_expected figure is therefore not a commission total — it is a mixed field with deposit and commission values. This inflates the reported figure independently of the split-rate error.

---

## PDF-Confirmed D2M Commission (Harlan MISSION-426 + spawn_commission_audit.py)

| Booking | Guest | Gross | Commission | D2M Split | D2M Share |
|---|---|---|---|---|---|
| 298475-25 | McLeod June (Silver Muse) | $25,896 | $2,594.54 (Silversea 16%+1% NCF) | 70% | $1,816.18 |
| 3096289 | Ely/Darrow (Grandeur Aug) | $20,640 | $2,685.90 (RSSC 15% Nexion) | 70% | $1,880.13 |
| 3071222 | Furlow (Grandeur Aug) | $18,120 | $2,287.90 (RSSC 15% Nexion) | 70% | $1,601.53 |
| 3078056 | Nichols (Grandeur Aug) | $18,896 | $2,287.90 (RSSC 15% Nexion) | 70% | $1,601.53 |
| 3122006 | Loucks Dec 2026 (Grandeur Panama) | $25,798 | $3,775.02 (RSSC 17% C&TU) | 80% | $3,020.02 |
| 9593880 | Kuklinski Kyle+Rosalie (Viking Mars) | $7,598 | $1,291.66 (Viking 17%) | 80% | $1,033.33 |
| 9593873 | Kuklinski Roger+Nicholas (Viking Mars) | $7,598 | $1,291.66 (Viking 17%) | 80% | $1,033.33 |
| 9595029 | Morton/Dodge (Viking Mars) | $6,198 | $1,053.66 (Viking 17%) | 80% | $842.93 |
| 3114500 | McLeod Dec 2027 (SS Prestige) | $15,098 | $2,179.96 (RSSC 17% C&TU) | 80% | $1,743.97 |
| 8X6PGQ | McLeod/McGlasson Princess Mar 2027 | $6,462 | UNKNOWN (passenger copy only) | 70% est | UNKNOWN |
| 2984034 | McLeod Dec 2026 (Grandeur Lesser Antilles) | TBD | PDF MISSING — no TA invoice | TBD | UNKNOWN |
| 566910-25 | Loucks Silver Nova | $10,800 | $0 (Interline agent — NOT D2M) | N/A | $0.00 |

---

## Action Items

- [ ] **Harlan confirms:** which figure is canonical — $18,830.83 (JSON field) or $18,830.93 (note sum). $0.10 discrepancy must be resolved before the sheet is updated.
- [ ] **Fix sheet formula:** Replace flat 15%/80% assumption with actual per-booking host tier (Nexion 15%/70%, C&TU 17%/80%, Viking 17%/80%, Silversea 16%+1%/70%).
- [ ] **Remove Loucks 566910-25:** Interline booking. Zero D2M commission. Remove from D2M commission total.
- [ ] **Fix commission column:** Separate deposit amounts from TA commission figures into distinct columns.
- [ ] **Resolve McLeod 2984034:** Obtain TA invoice from Nexion. Missing PDF = commission unknown. Current split per Harlan: 70% or 80% TBD.
- [ ] **Resolve McLeod 8X6PGQ (Princess):** Passenger copy only — no TA commission shown. Request TA copy.

**All above pending Commander approval to update sheet formula.**

---

## Canonical Figure Until Sheet Is Fixed

**Use Harlan's verified figure: $18,830.93** (component sum, pending $0.10 reconciliation with Harlan).
Do NOT use the sheet figure ($21,849.16) for any financial reporting or client communications until the formula is corrected.

**Missing bookings (2984034, 8X6PGQ):** Commission unknown. Total D2M share when these are resolved will be higher than $18,830.93.

---

## Status
**MISSION-822:** PENDING_REVIEW — Commander approval required to update sheet formula. Harlan reconciliation ($0.10) required before canonical total is finalized.

---

*— Brig Gen (Ret.) Thomas "Gauge" Sterling, A7 | 2026-07-02*
*Harlan A9 is the primary financial authority on this reconciliation. Sterling role: documentation and system analysis only.*
