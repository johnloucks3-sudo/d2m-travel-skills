---
mission: MISSION-087
title: Grandeur Group — Haymarket→At Six Pivot — Fire-on-Go Execution Runbook
group: Furlow / Ely-Darrow / Nichols
ship: Regent SS Grandeur · Storied Scandinavia · Stockholm→Oslo
embark: 2026-08-29
prepared_by: Ikeda (A10) — Crisis/Logistics
prepared: 2026-06-11
status: PREP ONLY — NOTHING EXECUTED. All four blocks are financial-gated.
authorization_required: Commander (financial gate). Until "go": no booking, no cancel, no send.
source_of_truth: GROUP_Grandeur_Scandinavia_Aug2026_TRACKER.md (2026-06-09, Harlan-verified)
---

# MISSION-087 — FIRE-ON-GO RUNBOOK
## Haymarket → At Six pivot · 3 couples · Regent SS Grandeur · Aug 29 2026

> **What this is:** the moment the Commander authorizes, the Wing runs this top to bottom. No figuring-it-out-then. Every step has the portal, the buttons, and the proof to capture.
>
> **What this is NOT:** authority to execute. Every block below moves money (or cancels a paid booking). All blocked at the financial gate until Commander says go.

---

## BLUF — THE PLAN ON ONE SCREEN

1. **SEAT FIRST (gate-light).** Furlow HEL→ARN seats — assigning business seats commits no money. Cheapest first move. Fire this the instant he says go, even if the rest waits.
2. **BOOK NEW BEFORE CANCEL OLD.** Confirm At Six Night 1 (Furlow + Nichols) and the 3× ARN→At Six transfers *before* cancelling Haymarket. If a new booking fails, the clients are never left with no Night-1 bed.
3. **THEN CANCEL.** Haymarket hotel + 3 ARN→Haymarket transfers — in Bedsonline — only after At Six is confirmed.
4. **VERIFY-THEN-FIRE on every cancel.** Step 0 of each cancellation is reading the on-screen booking and matching it to the locator. We do NOT cancel a locator blind. (See the data conflicts in §A — they are why.)

**Timeline reality:** Today is 2026-06-11 — **~10 weeks out.** Cliffs are Aug 23 (transfers) and Aug 24 (hotel). There is no 24-hour cost of inaction. This is genuine prep. The gate is the Commander's authorization, not the calendar — do not manufacture urgency.

**Two portals/operators in play (say it plainly so nobody hunts):**
- **Bedsonline** (Hotelbeds B2B) = the portal where the Haymarket hotel and all 3 ARN→Haymarket transfers were booked and where they cancel.
- **Royal Transfer** = the ground *operator* on those transfers. It is NOT a separate portal. All cancellations happen in Bedsonline.
- **Kiwitaxi** = where we get the NEW ARN→At Six transfer (separate vendor, separate booking).

---

## §A — DATA CONFLICTS TO RESOLVE ON-SCREEN (read before you cancel anything)

These are unresolved across sources. They cannot be settled from a file — only by reading the live booking in Bedsonline. That is exactly why every cancellation step opens with an on-screen verification. **Surfacing these is the job; cancelling the wrong locator at a 100%-charge cliff is the failure this runbook exists to prevent.**

| # | Conflict | Source A | Source B | Resolve how |
|---|---|---|---|---|
| A1 | **Is `131-2656351` the group booking, or Furlow's individual locator?** | Group tracker (auth, Jun 9): ONE Haymarket cancellation for all 3. Scandi brief: "one reservation, 3× Grande King rooms." | Furlow timeline: `131-2656351` tied to Furlow's *individual* hotel `1095075 / JF693870`, ~$418 / $801.74 net. | **In Bedsonline, open `131-2656351`. Read how many rooms / which guests.** If it is the group reservation, one cancel covers all. **If `1095075` is a SEPARATE Furlow hotel booking, it must be cancelled too** — or it stays live and hits 100% on Aug 25. This is the live-money risk. Do not close the block until `1095075` is accounted for. |
| A2 | **Furlow ARN→Haymarket transfer amount** | Group tracker: ~$176 | Furlow timeline: $117.56 net / $418 client (transfer 1095074 / DVF6U6) | Flag both. Read actual paid amount on-screen. Harlan reconciles the receivable. |
| A3 | **Transfer payment status (drives refund path)** | Group tracker + Scandi brief: transfers "PAID" | Furlow timeline: transfer "PAYMENT DUE" | Read on-screen. If PAID → expect refund, capture confirmation. If UNPAID → nothing to refund, just cancel. **Do not promise a refund where nothing was paid.** |
| A4 | **Nichols transfer (1095089 / LN693883)** | Group tracker: "Book-Now-Pay-Later — likely no charge" | — | Verify in Bedsonline. If unpaid → cancel, no refund expected. Capture the cancel confirmation regardless. |

> **Operating rule for §A:** if any on-screen reading does not match this runbook, STOP and surface to Commander/Harlan before cancelling. We never cancel through a mismatch.

---

## BLOCK 1 — FURLOW HEL→ARN SEATS (FIRE FIRST — gate-light)

**Why first:** assigning two business-class seats on an existing ticket commits no new money. This is the cheapest, lowest-risk move. It also closes the group's only unseated leg on the single shared connection (AY 811 — the group's single point of failure).

**The booking facts:**
- Couple: **John & Missy Furlow**, booking 3071222.
- Leg: **AY 811, HEL→ARN, Aug 27 2026, dep 13:15.** Finnair-operated.
- Status: **2 seats UNASSIGNED** (only open gap in the entire group's flight matrix).
- Locators to give the agent — **both**: **AA PNR `CKZHXA`** (Missy booked AA-direct, the issuing carrier) **and Finnair/oneworld PNR `BB4X94`**. Ticketed Jan 8 2026, Business class.
- POC: **Missy Furlow**, 469-767-8009, missy.furlow@gmail.com (POC for all reservations).

**Option B — AA call-in (Commander-directed path):**
1. Call **American Airlines reservations** (AA issued the ticket, so AA owns the record even though Finnair flies the leg).
2. Give the agent **AA PNR `CKZHXA`** first; if they need the operating-carrier record, give **`BB4X94`** (Finnair).
3. Request: **assign 2 Business-class seats on AY 811 (HEL→ARN, Aug 27, dep 13:15)** for John & Missy Furlow. Ask them to seat the couple together; match the rest of the group's cabin if a block is held.
4. If AA says the seat map is controlled by Finnair (common on codeshare-operated legs): get the **Finnair record locator from AA**, then call **Finnair** directly and assign on `BB4X94`.
5. **Capture:** new seat numbers → write to Furlow dossier flight matrix (replaces "⚠ UNASSIGNED") and the group tracker Action #4.

**Done when:** John & Missy have confirmed seat numbers on AY 811, documented in the dossier. No money moved — this can complete independent of the financial gate the moment Commander says go.

> Side note (Ely-Darrow): Ely HEL→ARN is assigned but seat #s are still "TBD" on PNR `UXVXZP`. Same call can pull those numbers for the record while we have an agent on the line. Nichols is fully seated (2D/2F, BERJYH). Furlow is the only true gap.

---

## BLOCK 2 — BOOK AT SIX NIGHT 1 (Aug 27–28) — Furlow + Nichols only

**Who needs it:** Furlow and Nichols. **Ely-Darrow self-covered** — Al & Amy hold their own At Six Night 1 reservation (deferred payment), per their dossier. Do NOT book a Night-1 for Ely.

**Context to avoid double-booking:**
- **Night 2 (Aug 28–29) is already confirmed** — At Six, Regent-included, **Conf #9092637820900**, all 3 couples. We are ONLY booking Night 1.
- Both nights are At Six → no room change mid-stay. Match the Night-2 room type/occupancy so the couples stay in one room across both nights.

**Booking path — try in this order:**
1. **First check Bedsonline** (Hotelbeds B2B) for At Six Stockholm, Aug 27–28, 2 rooms (1 Furlow, 1 Nichols), 2 adults each. B2B net rate + D2M commission is the preferred path (same portal we already use for this group).
   - If available: book 2 rooms, note the free-cancel window, label per couple.
2. **If At Six is not bookable in Bedsonline** for that date: book direct at **athesixstockholm.com** (or via the same channel Ely used for their own At Six Night-1 reservation — match that path so all 3 couples are in the same property record).
3. **Pull a rate first** — use the `hotel-price` skill (Hotelbeds/Bedsonline B2B) for the At Six Aug 27 net rate before committing, so the Commander sees the number at the gate.

**Capture per couple:** confirmation #, rate, cancellation terms. Write to each dossier. Flag the two new charges to Harlan.

**Done when:** Furlow + Nichols each hold a confirmed At Six Aug 27–28 reservation matching their Night-2 room. (This must be CONFIRMED before Block 4 cancels Haymarket.)

---

## BLOCK 3 — ARN → AT SIX TRANSFERS ×3 (book new)

**Who:** all 3 couples (Furlow, Ely-Darrow, Nichols) — one private car each, ARN airport → At Six Stockholm, **Aug 27** (arrival off AY 811, ~14:00+ local after the 13:15 HEL departure).

**Vendor: Kiwitaxi.** Reality check before the Wing tries a one-click book:
- The `transfer-price` skill is a **price-lookup scraper, not a booking engine.**
- **ARN/Stockholm is NOT in the pre-mapped routes** — it needs custom `--from "ARN Airport" --to "At Six Stockholm"` form-fill to even get a quote.
- **Booking is a manual action on kiwitaxi.com.** Whether D2M holds a Kiwitaxi B2B/agent account is **UNKNOWN** (skill flags: "if registered these may be net agent rates; if not, check the Business section at kiwitaxi.com/business"). Do not assume net agent pricing.

**Steps:**
1. **Quote:** run `transfer-price --from "ARN Airport" --to "At Six Stockholm" --date 2026-08-27 --pax 2` (custom form-fill mode). Expect ~$95–100/couple per the planning estimate; confirm live. Vehicle class: Comfort/Standard private car, 2 adults + luggage.
2. **B2B check:** confirm whether D2M has a Kiwitaxi Business account. If yes → book through it for net + tracking. If no → either book retail on kiwitaxi.com (flag the margin to Harlan) or register Business first (Commander call — that's a new account commitment).
3. **Book 3 cars** for Aug 27, ARN→At Six, timed off AY 811 arrival (build in buffer — international connection + bags; do not cut it tight to the 13:15 HEL departure).
4. **Capture:** 3 confirmation #s, price each, cancellation terms. Write to each dossier transfer field (replaces the cancelled Haymarket transfers). Flag charges to Harlan.

**Done when:** 3 ARN→At Six transfers confirmed. (Confirm BEFORE Block 4 cancels the old transfers.)

---

## BLOCK 4 — CANCEL HAYMARKET + 3 OLD TRANSFERS (cancel LAST, in Bedsonline)

> **GATE:** do not start Block 4 until Blocks 2 and 3 are CONFIRMED. We cancel old lodging/transport only after the replacements are locked. Book-new-before-cancel-old is the safety rule — if At Six or the new transfers had failed, the clients still have their Haymarket fallback.

### 4a — Cancel the 3 ARN→Haymarket transfers (cliff: **Aug 23**, Furlow shows 13:15 local)

All three are Bedsonline bookings (Royal Transfer is the operator, not a separate portal).

| Couple | Transfer locator | Bedsonline ref | Paid? (verify) | Refund expectation |
|---|---|---|---|---|
| Furlow | **1095074** | DVF6U6 | Conflict A2/A3 — read on-screen (~$176 OR $117.56 net; PAID vs DUE) | If paid → refund; if due → nothing to refund |
| Ely-Darrow | **1095091** | AE693884 | ~$176 (verify paid) | If paid → refund |
| Nichols | **1095089** | LN693883 | Book-Now-Pay-Later — likely $0 | Likely no charge, no refund |

**Steps (repeat per transfer):**
1. Log into **Bedsonline** (Hotelbeds B2B portal). Credentials/cookies: Hotelbeds — verify session live before starting (per credential status, refresh if expired).
2. **Bookings → search the locator** (1095074 / 1095091 / 1095089).
3. **VERIFY ON-SCREEN (step 0):** confirm guest names, route (ARN→Haymarket), date Aug 27, and **paid amount**. Match to the table above. If it does not match → STOP, surface to Harlan/Commander. Do not cancel a mismatch.
4. Confirm the **free-cancel deadline shows on or after Aug 23** before cancelling (it should — we're cancelling months early).
5. Click **Cancel booking** → confirm. **Capture the cancellation confirmation # and screenshot.**
6. Record refund status: if the booking was paid, note the expected refund → hand to Harlan as a receivable. If unpaid/pay-later, note "no charge."

### 4b — Cancel the Haymarket hotel (cliff: **Aug 24**; 100% charge from Aug 25)

1. In **Bedsonline**, open **`131-2656351`**.
2. **VERIFY ON-SCREEN (step 0) — this is the §A1 decision point:**
   - Read **how many rooms and which guests** are on `131-2656351`.
   - If it is the **group reservation** (3 rooms, all couples) → one cancel covers Furlow + Nichols + Ely's Night-1 group share. Proceed.
   - If `131-2656351` is **Furlow-individual**, then **find and also cancel Furlow hotel `1095075 / JF693870`** AND locate the Nichols/Ely Haymarket room reservations separately. **Do not close this block until every Haymarket room for the group is cancelled** — a stray live booking hits 100% Aug 25.
3. Confirm **free-cancel deadline shows on or after Aug 24** before cancelling.
4. Click **Cancel** → confirm. **Capture confirmation # + screenshot per room/booking cancelled.**
5. Refund: note any prepaid hotel amounts → Harlan tracks the receivable. (Furlow timeline shows ~$418 client / $801.74 net for the Furlow room — verify against on-screen actual.)

**Done when:** every Haymarket room and all 3 ARN→Haymarket transfers show CANCELLED in Bedsonline, with confirmation #s captured, and Harlan holds the refund-receivable list.

---

## SEQUENCE & DEPENDENCY MAP

```
ON "GO" (financial gate cleared by Commander)
│
├─ BLOCK 1  Furlow HEL→ARN seats ........ FIRE IMMEDIATELY (no money — independent)
│
├─ BLOCK 2  At Six Night 1 (Furlow+Nichols) ─┐
│                                            ├─ both CONFIRMED ──► BLOCK 4 (cancel)
├─ BLOCK 3  ARN→At Six transfers ×3 ─────────┘
│                                                   │
│                                                   ├─ 4a cancel 3 transfers (≤Aug 23)
│                                                   └─ 4b cancel Haymarket   (≤Aug 24)
│                                                        └─ §A1: verify 131-2656351
│                                                           scope; catch 1095075
│
└─ HARLAN: track all new charges + all refund receivables; verify refunds post.
```

**Hard rule:** Block 4 NEVER runs before Blocks 2 & 3 confirm. Book new, then cancel old.

---

## CLIFF DATES (cancel-BY)

| Date | Cliff | Block |
|---|---|---|
| **Aug 23, 2026** (13:15 local for Furlow) | ARN→Haymarket transfers free-cancel ends | 4a |
| **Aug 24, 2026** | Haymarket hotel free-cancel ends — 100% charge from Aug 25 | 4b |
| Aug 26 | Depart DFW (AA 9018 / Finnair) | — |
| Aug 27 | HEL→ARN (AY 811, 13:15) → At Six Stockholm | Blocks 1–3 must be done |
| Aug 29 | Embark Stockholm (🎂 Heidi Nichols' birthday = embark day) | — |

We are 10+ weeks ahead of every cliff. Execute on authorization, not against the clock.

---

## CAPTURE CHECKLIST (what proof to bring back)

- [ ] Block 1: Furlow AY 811 seat #s (+ Ely seat #s if pulled) → dossier
- [ ] Block 2: At Six Aug 27–28 conf # — Furlow, Nichols (rate + cancel terms each)
- [ ] Block 3: 3× ARN→At Six transfer conf #s (price + cancel terms each)
- [ ] Block 4a: 3× cancel confirmation #s + screenshots (1095074 / 1095091 / 1095089)
- [ ] Block 4b: Haymarket cancel confirmation(s) + screenshot(s); §A1 resolved (1095075 accounted for)
- [ ] Harlan: refund-receivable list (paid items only) + new-charge list, reconciled

---

## GATES & PROHIBITIONS (standing)
- **Financial gate:** Blocks 2, 3, 4 all move money or cancel paid bookings → Commander authorization required before execution.
- **Block 1** is gate-light (no money) — clears the moment Commander says go.
- **No client send** in this runbook. If any of this requires telling the clients, that's a separate WF-17 client product (the At Six pivot is client-directed, but any email still routes through the creative chain + Commander send).
- **Verify-then-fire** on every cancellation. Never cancel through an on-screen mismatch.

---

*Prepared 2026-06-11 by MSgt (Ret.) Tomoko "Tommy" Ikeda (A10) — Crisis Response & Independent Assessment, Dreams2Memories Travel, LLC.*
*PREP ONLY. Nothing executed. No bookings, no cancellations, no sends, no commits. Awaiting Commander financial-gate authorization.*

<!-- PHASE4_LIFECYCLE_STAGED_V1 | Autonomously enriched by Phase 4 AI Engine -->
