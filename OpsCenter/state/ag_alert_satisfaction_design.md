# AG-DESIGN: Alert Satisfaction

## 1. Is the existing closure ledger sufficient?
**No, it only masks the symptom.**
Tracing the call paths for `deferred_alerts` in `hale_state.json`:
- `commander_queue.build_queue()` correctly filters out items that are present in `commander_closures.jsonl`.
- However, three other generators consume `hale_state.json` directly and iterate over `deferred_alerts` **without calling `commander_queue.is_closed(aid)`**:
  1. `agents/thunderbird_daily_brief.py` (lines 319+)
  2. `agents/thunderbird_eod_brief.py` (lines 239+)
  3. `core/ops/morning_consolidated_brief_engine.py` (line 323)
  4. `core/hale/brief_dashboard_render.py` (line 65)

Because these files don't respect the closure ledger, closing an alert via `commander_queue.close()` removes it from the Commander's desk but allows it to continue firing indefinitely in morning/evening briefs and the dashboard.

## 2. Minimal Schema Change
The most minimal addition to the `deferred_alerts` schema in `hale_state.json` is a single timestamp field:
**Field:** `"satisfied_at": "YYYY-MM-DDThh:mm:ssZ"` (String, ISO-8601, optional)
**Predicate:** `if alert.get("satisfied_at"): continue`

*Example:*
```json
{
  "id": "MCLEOD-2984034-FPD-TRIGGER",
  "condition": "date>=2026-07-07 AND client_returned",
  "satisfied_at": "2026-07-20T14:00:00Z"
}
```

## 3. Ground Truth: Payment Status in TESS/Repo
**Yes, there are existing fields in the repo.**
- In TESS: The TESS API provides a `BalanceDue` field and a `BookingStatus` field (handled in `core/ops/fpd_auto_update.py`, which pulls TESS bookings and checks `booking.get("BalanceDue") <= 0` or if the status contains "paid").
- In the local repository: `fpd_auto_update.py` propagates the TESS payment status into the dossier markdown frontmatter as `fpd_status: PAID` and `fpd_paid_confirmed: <date>`. Additionally, `scripts/fdp_reconcile.py` checks `final_payment_paid` or `fpd_paid` in the local `dossiers/*.json` files.
*(Note: Calling `tess_get_booking` via MCP for 2984034 currently returns `PaymentCount: 0` and no BalanceDue, indicating the payment hasn't yet synced or was made directly to the supplier without updating TESS yet.)*

## 4. Argument Against My Own Design
**The Split Brain Problem:**
Adding a `satisfied_at` field to `deferred_alerts` duplicates state. It divorces the alert's status from the actual ground truth (the dossier or TESS). 

**What slips through:**
If a payment is made, `core/ops/fpd_auto_update.py` will update the dossier to `fpd_status: PAID`. But because the alert in `hale_state.json` operates on a dumb date condition (`date>=2026-07-07`) and relies on `satisfied_at`, the alert will **still fire** unless a human or script remembers to explicitly cross-update `hale_state.json`. 

A more robust design would evaluate the alert's condition against the system of record dynamically (e.g., condition: `date>=2026-07-07 AND NOT dossier_is_paid("2984034")`).
