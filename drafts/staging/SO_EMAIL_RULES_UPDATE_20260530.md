# STAGED SO — Email Rules Update
# Commander directive 2026-05-30 | Staged for Sterling (A7) CLAUDE.md implementation
# PRODUCTION-LOCK: Sterling executes CLAUDE.md edits. Hale stages.

## SOURCE: Commander directive 2026-05-30

Six decisions made. Map to CLAUDE.md "EMAIL ACCOUNT SEPARATION" section + new sig block SO.

---

## DECISION 1 — Wing writes personal opening for all emails Commander sends

**New rule:** For any email the Wing drafts for Commander to send — whether D2M client, personal assist, or report — the Wing writes the COMPLETE email including the personal/relationship framing paragraph at the top. Commander should not need to add the opening himself.

**What this requires:** When routing a draft, the Wing persona must know:
- Who the recipient is (classmate, client, vendor, family member)
- What the relationship context is (known history, tone, how Commander addresses them)
- What conversational thread, if any, this replies to

If relationship context is not in the dossier or prior thread, Wing asks ONE clarifying question before drafting: "What's my context on [name]?" Then drafts complete.

**Persona responsible for personal opening:** Dani (client voice) for D2M client emails. Hale (for personal assist / non-client emails). Luna/Naia pass still applies for long-form creative.

---

## DECISION 2 — Inbox/Draft routing rules (simplified, replaces prior rules)

| Email type | Draft created in | Send from | Commander finds it in |
|---|---|---|---|
| D2M client products (validation, proposals, itineraries) | d2mconcierge — label THUNDERBIRD-Commander-Review | Commander sends from d2mconcierge | d2mconcierge Drafts / Sent |
| Pro bono / D2M-adjacent business (research, vendor contact) | d2mconcierge — label THUNDERBIRD-Commander-Review | Commander sends from d2mconcierge | d2mconcierge Drafts / Sent |
| Personal non-D2M (classmate assist, family, friends) | johnloucks3 — label WING-PERSONAL-DRAFT | Commander sends from johnloucks3 | johnloucks3 Drafts / Sent |
| D2M-to-Chief internal (reports, briefs, intel) | FULL SEND to johnloucks3 inbox — no draft step | Wing sends directly | johnloucks3 Inbox |

**Changes from prior rules:**
- Personal assist emails now have a defined home: johnloucks3 draft, label WING-PERSONAL-DRAFT (NEW)
- D2M client → Commander sends from d2mconcierge (now explicit, was implicit)
- Internal reports → johnloucks3 inbox full send (CONFIRMED — no change)

---

## DECISION 3 — ALL emails use USAFA colors formatting + signature block

**New rule:** Every email the Wing produces or drafts for Commander — regardless of type — uses USAFA color formatting:
- Background: cream (#f7f3ea)  
- Primary text/ink: blue (#0000ff)
- Accent/banner: navy blue (#003087 or current D2M navy)
- Font: Georgia

**Signature block:** Every email has a signature block. No email exits the Wing without one.

---

## DECISION 4 — Personal emails: USAFA colors YES, D2M logo NO

**New rule:** Personal non-D2M emails use USAFA color formatting and signature block but do NOT include the D2M logo, D2M banner, or Dreams2Memories branding. Commander's personal sig block should be:

```
John Loucks
[USAFA Class of '75 callsign/designation as appropriate]
[phone if appropriate]
```

No D2M branding. No agency title. Personal email = personal identity.

D2M client emails retain the full D2M banner and logo.

---

## DECISION 5 — Dani always encloses her avatar photo in sig block

**New rule:** Every email Dani drafts or sends includes her avatar photo (`storage/output/images/dani_moreau_avatar.png`) in the signature block. This is permanent and non-optional.

---

## DECISION 6 — ALL personas enclose avatar photo in sig block

**New rule:** Every Wing persona includes their avatar photo in their signature block for all emails they draft or send. This creates visual identity consistency and allows recipients to identify the persona.

**Available avatars (9 confirmed):**
- Hale: `victoria_hale_avatar.png`
- Dani: `dani_moreau_avatar.png`
- Luna: `luna_voss_avatar.png`
- Dembe: `marcus_dembe_avatar.png`
- Naia: `naia_solberg_vega_avatar.png`
- Castillo: `ryan_castillo_avatar.png`
- Washington: `james_washington_avatar.png`
- Bridge/Ikeda: `tomoko_ikeda_avatar.png`
- Harlan: `vic_harlan_avatar.png`

**Missing avatars — generation needed (10 personas):**
- Sterling (A7) — Thomas 'Gauge' Sterling
- Navarro (A1)
- Keel (A4)
- Reyes (A8)
- ELON (A12)
- Sienna (A13)
- TALON
- JET
- ZEN
- Horizon (A11)

Gap decision: Use Hale avatar as placeholder for missing personas? Or hold sig photo until generated? Flag to Commander.

---

## STERLING IMPLEMENTATION TASKS

When ready to execute, Sterling should update:

1. **CLAUDE.md** — Replace "EMAIL ACCOUNT SEPARATION" section with Decision 2 table above
2. **CLAUDE.md** — Add new section: "EMAIL SIGNATURE BLOCK STANDARDS" (Decisions 3-6)
3. **CLAUDE.md** — Add to Dani persona rules: "Always enclose avatar photo in sig block"
4. **Create new SO file:** `standing_orders/SO_EMAIL_RULES_UPDATE_20260530.md`
5. **Update `core/email/thunderbird_gmail.py`** — `_wrap_body_html()` to inject persona photo in sig block

---

*Staged: V. Hale, VCS · 2026-05-30 · Awaiting Sterling execution*
*Commander directive: 2026-05-30 session*
