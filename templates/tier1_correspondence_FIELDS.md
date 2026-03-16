# Tier 1 — Correspondence Template
## Field Reference · `tier1_correspondence.html.j2`

**Use for:** Routine client correspondence · Client replies · Trip Validation emails
**Theme:** White/cream background · Light blue ink · Gold accents · Printer-friendly

---

### REQUIRED FIELDS

| Variable | Description | Example |
|---|---|---|
| `greeting` | Opening salutation | `Dear Nancy and Ken,` |
| `body_html` | Full HTML body content | `<p>Thank you for...</p>` |

---

### OPTIONAL FIELDS

| Variable | Default | Description |
|---|---|---|
| `subject` | `Dreams2Memories Travel` | Browser/PDF title tag |
| `subject_display` | *(none)* | Displayed subject line under meta row — use for Trip Validation, Proposals |
| `date` | *(none)* | Human-readable date — `March 16, 2026` |
| `reference` | *(none)* | Booking/reference number — appears top-right |
| `closing` | `Thank you` | Sign-off word — NEVER "Best" |
| `agent_name` | `John Loucks` | Sender name (body + footer) |
| `agent_title` | `Luxury Travel Advisor · Dreams2Memories Travel` | Title line |
| `agent_phone` | `+17192910742` | Phone href value |
| `agent_phone_display` | `+1 (719) 291-0742` | Phone display text |
| `agent_email` | `concierge@d2mluxury.quest` | Email address |
| `show_telegram` | `true` | Show Telegram link in footer |
| `logo_b64` | *(none)* | Base64-encoded logo PNG |
| `logo_url` | *(none)* | Logo URL (fallback to logo_b64) |
| `agent_photo_b64` | *(none)* | Base64 agent headshot |
| `agent_photo_url` | *(none)* | Agent headshot URL |
| `show_ai_disclosure` | `false` | Show Dani AI disclosure block (true when Dani sends) |

---

### OPTIONAL HTML COMPONENTS
Copy/uncomment from the template as needed:

**Highlight Box** — booking summary, key details, important dates
```html
<div class="highlight-box">
    <div class="box-label">Booking Summary</div>
    <p><strong>Booking Reference:</strong> XXXXXX</p>
    <p><strong>Travel Dates:</strong> Month DD – DD, YYYY</p>
    <p><strong>Destination:</strong> City, Country</p>
</div>
```

**Action Box** — next steps, items needed from client
```html
<div class="action-box">
    <div class="box-label">A Few Items to Note</div>
    <div class="action-item">Passport copies due by [DATE]</div>
    <div class="action-item">Final payment due [DATE] — $X,XXX</div>
</div>
```

---

### AGENT VARIANTS

| Sender | `agent_name` | `agent_email` | `show_ai_disclosure` |
|---|---|---|---|
| John (direct) | `John Loucks` | `concierge@d2mluxury.quest` | `false` |
| Dani (AI) | `Dani Moreau` | `concierge@d2mluxury.quest` | `true` |

---

### CLOSING STANDARDS

| Context | Closing |
|---|---|
| Routine correspondence | `Thank you` |
| Warm/personal | `Thanks` |
| NEVER use | `Best` / `Regards` / `Sincerely` |

---

### PRINT BEHAVIOR
- White background enforced on print
- Box shadows stripped
- Font size drops to 12pt
- Links render as ink-blue, no underline
- All license numbers retained in footer
