---
name: invoice-reconciler
description: >
  Match supplier invoices against client booking records, flag discrepancies,
  and produce a reconciliation report. Works with cruise line invoices, hotel
  confirmations, tour operator receipts, and transfer confirmations. Use when
  asked to reconcile invoices, check billing, verify charges, or audit supplier
  payments against booking records.
license: MIT
compatibility: Claude Code 2.0+, Claude Cowork, Cursor, Gemini CLI, Goose
metadata:
  author: Dreams2Memories Travel, LLC
  version: 0.1.0
  category: travel-operations
  vertical: financial-reconciliation
allowed-tools:
  - Read
  - Write
  - Bash
---

# Invoice Reconciler — D2M Travel Operations

Matches supplier invoices to booking records and flags discrepancies for Harlan review.

## Inputs Required

- Supplier invoice(s) (PDF or structured data)
- Client booking record / dossier
- Expected charges from booking confirmation

## Output

- Line-by-line reconciliation table
- Discrepancy flags (amount mismatch, unexpected charge, missing charge)
- Reconciliation status: CLEAN / NEEDS REVIEW / ESCALATE
- Routed to Harlan (A9) for financial sign-off

## Process

1. Parse invoice documents for charge line items
2. Load client booking record from dossier
3. Match each invoice line to a booking element
4. Flag: amount mismatch > $10, unrecognized line items, missing expected charges
5. Generate reconciliation report
6. Route to Harlan for financial verification (Hard Rule #6 — Harlan signs off on all $ figures)

## Hard Rules

- ❌ NEVER pass financial data to Commander without Harlan sign-off first
- ❌ NEVER auto-approve discrepancies — all flags require human review
- ❌ NEVER delete or modify source invoice documents

## scripts/

- `parse_invoice_pdf.py` — extracts line items from supplier invoice PDFs
- `match_booking_charges.py` — cross-references dossier charges
- `build_reconciliation_report.py` — structured output for Harlan review
