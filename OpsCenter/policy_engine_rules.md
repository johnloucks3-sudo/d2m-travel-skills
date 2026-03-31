# Safe-CLI Policy Engine Rules

## 1. Directive Enforcement
- **Email Policy:** Any tool matching `gmailSendEmail` or `sendClientEmail` is automatically denied. Only `draftClientEmail` or `gmailCreateDraft` are permitted.
- **Banned Strings:** Commands containing "Love Group Travel", "delete", or "rm -rf" will trigger immediate dissent and log to `dissent_log.md`.

## 2. PII Sanitizer
- All `arguments` fields are scanned via Regex for patterns:
  - Credit Card (Luhn check)
  - Social Security Numbers
  - Email addresses in raw text (outside of structured fields)
- Any detected PII triggers automatic block and alert to `star_protocol_log`.

## 3. Tool Whitelist
- **Allowed:** `calendar*`, `driveList*`, `driveRead*`, `tessGet*`, `*ReadMessage`
- **Denied:** `*Delete*`, `*Trash*`, `gmailSendEmail`