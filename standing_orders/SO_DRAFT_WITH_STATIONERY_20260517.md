# Standing Order — Draft with Stationery (17 MAY 2026)

**Authority:** Hale COS, by Commander directive  
**Supersedes:** SO_TWO_LANE_EMAIL_PIPELINE_20260507  
**Status:** ACTIVE  

## Rule

**Formatted HTML drafts survive Gmail when preprocessed correctly. Use the direct format pipeline, not the Two-Lane workaround.**

## Process

### Method 1: gmail_create_draft_sync (Recommended)

```python
from core.email.thunderbird_gmail import gmail_create_draft_sync

gmail_create_draft_sync(
    to="client@email.com",
    subject="Your Voyage Update",
    body=html_content  # Full HTML with stationery or just body text
)
```

How it works:
- `_wrap_body_html()` auto-detects full HTML documents (`<!doctype` or `<html>`)
- Uses `premailer.transform()` to inline all CSS into element styles
- Creates `multipart/alternative` draft with plain text + HTML
- Applies `THUNDERBIRD-Commander-Review` label

### Method 2: Preprocess + Direct Draft (Manual)

```bash
# Step 1: Harden HTML for Gmail
python3 scripts/gmail_template_stripper.py input.html output.html

# Step 2: Create draft with raw HTML
python3 scripts/create_gmail_draft_direct.py \
    --html output.html \
    --to client@email.com \
    --subject "Subject Line"
```

### Method 3: Full DIY (Reference)

See `ops/create_kuklinski_draft.py` — reads HTML from file, builds `MIMEText(html, 'html')`, creates draft via Gmail API.

## Why It Works

1. `gmail_template_stripper.py` inlines CSS from `<style>` blocks, removes unsafe tags, converts div→tables
2. `premailer` (in `_wrap_body_html`) further hardens CSS inlining
3. No `<style>` blocks remain — all styles inline, Gmail cannot strip them
4. Cream (#f7f3ea) background and blue (#0000ff) ink survive all Gmail sanitization

## Reference

- `docs/GMAIL_TEMPLATE_SOLUTION_IRONCLAD.md` — full technical deep-dive
- `scripts/gmail_template_stripper.py` — GmailSafePreprocessor (517 lines)
- `core/email/thunderbird_gmail.py` → `gmail_create_draft_sync()` at line 2646
