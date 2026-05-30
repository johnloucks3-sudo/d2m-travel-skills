# STANDING ORDER — EMAIL RULES UPDATE
## SO Reference: SO_EMAIL_RULES_UPDATE_20260530
## Effective: 2026-05-30
## Authority: Commander directive, 2026-05-30 session
## Owner: A7 Sterling (enforcement) | Hale (routing compliance)
## Status: ACTIVE

---

## SCOPE

This SO governs six email-production decisions made by Commander on 2026-05-30. It supersedes conflicting language in prior email SOs on the specific topics below. It does NOT supersede the WF-17 client-send prohibition (SO_WF17_CLIENTSEND_PROHIBITION_20260530) or the email send gate (SO 21 MAR 2026).

---

## DECISION 1 — WING WRITES COMPLETE EMAIL INCLUDING PERSONAL OPENING

**Rule:** For any email the Wing drafts for Commander to send — whether D2M client, personal assist, or internal report — the Wing writes the COMPLETE email including the personal/relationship framing paragraph. Commander should not need to add an opening himself before sending.

**What this requires:** When routing a draft, the Wing persona must know:
- Who the recipient is (classmate, client, vendor, family member)
- What the relationship context is (known history, tone, how Commander addresses them)
- What conversational thread, if any, this replies to

If relationship context is not in the dossier or prior thread, Wing asks ONE clarifying question before drafting: "What is my context on [name]?" Then drafts complete.

**Persona responsible for personal opening:**
- Dani (A3) — D2M client emails
- Hale — personal assist / non-client emails (Luna/Naia pass still applies for long-form creative)

---

## DECISION 2 — EMAIL DRAFT ROUTING TABLE (SUPERSEDES PRIOR EMAIL ACCOUNT SEPARATION RULES)

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

## DECISION 3 — ALL EMAILS USE USAFA COLOR FORMATTING

**Rule:** Every email the Wing produces or drafts for Commander — regardless of type — uses USAFA color formatting:
- Background: cream (#f7f3ea)
- Primary text/ink: blue (#0000ff)
- Accent/banner: navy blue (#003087 or current D2M navy)
- Font: Georgia

---

## DECISION 4 — PERSONAL EMAILS: USAFA COLORS YES, D2M LOGO NO

**Rule:** Personal non-D2M emails use USAFA color formatting and signature block but do NOT include the D2M logo, D2M banner, or Dreams2Memories branding.

Personal sig block format:
```
John Loucks
[USAFA Class of '75 callsign/designation as appropriate]
[phone if appropriate]
```

No D2M branding. No agency title. Personal email = personal identity.

D2M client emails retain the full D2M banner and logo.

---

## DECISION 5 — ALL EMAILS HAVE A SIGNATURE BLOCK

**Rule:** No email exits the Wing without a signature block. Every email has one, regardless of type (client, personal, internal).

---

## DECISION 6 — ALL PERSONAS INCLUDE AVATAR PHOTO IN SIGNATURE BLOCK

**Rule:** Every Wing persona includes their avatar photo in their signature block for all emails they draft or send. Creates visual identity consistency.

**Available avatars (9 confirmed) — path: `storage/output/images/`:**
- Hale: `victoria_hale_avatar.png`
- Dani: `dani_moreau_avatar.png`
- Luna: `luna_voss_avatar.png`
- Dembe: `marcus_dembe_avatar.png`
- Naia: `naia_solberg_vega_avatar.png`
- Castillo: `ryan_castillo_avatar.png`
- Washington: `james_washington_avatar.png`
- Bridge/Ikeda: `tomoko_ikeda_avatar.png`
- Harlan: `vic_harlan_avatar.png`

**Missing avatars (10 personas — generation required):**
Sterling (A7), Navarro (A1), Keel (A4), Reyes (A8), ELON (A12), Sienna (A13), TALON, JET, ZEN, Horizon (A11)

**Gap rule:** Personas without a generated avatar omit the photo slot until their avatar is produced. Do NOT use another persona's avatar as a placeholder. Flag missing avatars to Commander via standard brief.

---

## ENFORCEMENT

**A7 Sterling:** Audits all client email drafts at WF-17 gate for sig block compliance and USAFA color compliance. Violations returned to Hale before Commander review.

**Hale:** Routes drafts to correct account per Decision 2 table. Verifies label applied. Personal drafts in johnloucks3 must carry label WING-PERSONAL-DRAFT.

**Metric:** `email_sig_block_compliance_pct` — target 100%. Added to `OpsCenter/a7_metrics_dashboard.json`. First measurement: 2026-06-06 (one week post-activation).

---

## RELATIONSHIP TO OTHER SOs

- SO_WF17_CLIENTSEND_PROHIBITION_20260530 — UNAFFECTED. Client-send prohibition stands in full.
- SO 21 MAR 2026 (Email Send Gate) — UNAFFECTED. Gate rules stand.
- SO 24 MAR 2026 (Email Account Separation) — SUPERSEDED on the specific routing rules. Decision 2 table above is the governing routing authority.
- SO 17 MAY 2026 (Draft with Stationery) — COMPLEMENTARY. Stationery process unchanged; this SO adds persona avatar requirement.

---

*Authored: A7 Sterling, 2026-05-30*
*Staged by: V. Hale, VCS*
*Commander directive: 2026-05-30 session*
