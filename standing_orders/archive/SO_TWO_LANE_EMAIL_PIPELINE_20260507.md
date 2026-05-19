# SUPERSEDED — Two-Lane Email Pipeline (07 MAY 2026)

**Retired:** 17 MAY 2026 by Hale COS  
**Replaced by:** SO_DRAFT_WITH_STATIONERY_20260517.md  
**Reason:** Commander confirmed that properly preprocessed HTML (via `gmail_template_stripper.py` + `premailer`) survives Gmail's rendering engine. The Two-Lane system added unnecessary friction. Direct formatted drafts are the preferred workflow.

## Original Text

> **Drafts MUST be plain text — NEVER apply HTML stationery at draft creation time.**
> - **Lane 1 (Edit Lane):** `gmail_create_draft()` creates plain-text drafts in d2mconcierge. Commander edits content freely in Gmail compose with no style-stripping risk.
> - **Lane 2 (Publish Lane):** Commander runs `/approve [draft_id]` in Telegram → `publish_draft()` fetches the edited body, applies the correct stationery template, sends via `messages().send()`, deletes the source draft.
> - **VIOLATION:** Calling `_wrap_body_html()` or `_wrap_staff_html()` at draft creation time causes Gmail to strip all inline CSS when Commander opens the draft to edit.

## What Changed

- `CLAUDE.md` SO section deleted
- `scripts/gmail_template_stripper.py` + `gmail_create_draft_sync()` + premailer pipeline validated as working
- Direct draft-with-stationery process documented as SO 17 MAY 2026
