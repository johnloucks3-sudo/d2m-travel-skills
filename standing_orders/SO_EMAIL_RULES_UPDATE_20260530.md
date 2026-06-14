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

---

## AMENDMENT 2026-06-14 — COMMANDER REVIEW CONSOLIDATION (Commander directive)

### Label restructure (effective immediately)

| Old label | New label | Color | Account |
|---|---|---|---|
| `PIPELINE/Commander-Review` | `Commander Review/New` | 🔴 Red (#fb4c2f) | johnloucks3 |
| `THUNDERBIRD-Commander-Review` | `Commander Review/Done` | ⬜ Grey (#cccccc) | johnloucks3 |
| `THUNDERBIRD-Commander-Review` | `THUNDERBIRD-Commander-Review` | 🔴 Red (#fb4c2f) | d2mconcierge |

### New draft routing rule

**Commander lives in johnloucks3.** All review items must surface there — one inbox, one label folder.

Updated routing table (supersedes Decision 2 above):

| Email type | Draft created in | Review label applied | Commander finds it |
|---|---|---|---|
| D2M client products (WF-17) | johnloucks3 (review copy) + d2mconcierge (send copy) | `Commander Review/New` (red) | johnloucks3 left sidebar — red dot |
| Personal non-D2M | johnloucks3 | `Commander Review/New` (red) | johnloucks3 left sidebar — red dot |
| D2M-to-Chief internal | Full send to johnloucks3 inbox | None (already delivered) | johnloucks3 Inbox |

**Send flow:** Commander clicks draft in `Commander Review/New` → reviews content → clicks "Open in d2mconcierge" link in footer → sends from d2mconcierge with correct From address → Wing relabels to `Commander Review/Done`.

**Script:** `scripts/wf17_stage_review.py` — Wing calls this after any WF-17 pass to stage a review card in johnloucks3.

### When to relabel Done
- Wing moves `Commander Review/New` → `Commander Review/Done` after Commander confirms send
- OR Commander manually relabels when item is reviewed/no longer needed

---

## ENFORCEMENT

**A7 Sterling:** Audits all client email drafts at WF-17 gate for sig block compliance and USAFA color compliance. Violations returned to Hale before Commander review.

**Hale:** Routes drafts per updated Decision 2 table (Amendment 2026-06-14). Every WF-17 client product creates a johnloucks3 review card labeled `Commander Review/New`. Personal drafts in johnloucks3 also carry `Commander Review/New`.

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

---

## AMENDMENT — 2026-06-14 (Commander directive)

**Amends:** Decision 2 routing table — johnloucks3 draft exception

A 2026-06-04 policy (memory entry) tightened the "Personal non-D2M" row to require direct sends only (no drafts to johnloucks3). This amendment restores the draft capability with an explicit Commander OK gate.

**Rule (effective 2026-06-14):**

Wing may create drafts in johnloucks3 ONLY when Commander explicitly approves it in session. Acceptable signals: "draft to johnloucks3", "put in my drafts", "OK to draft to johnloucks3", or similar explicit language.

Without explicit Commander OK: continue sending direct to johnloucks3 inbox (full send) per the D2M-to-Chief internal row. The default is NOT draft — the default is direct send.

With explicit Commander OK: create draft in johnloucks3, label WING-PERSONAL-DRAFT.

**Updated routing table:**

| Email type | Default | On Commander OK | Label |
|---|---|---|---|
| D2M client products | d2mconcierge draft | N/A — WF-17 gate, no change | THUNDERBIRD-Commander-Review |
| Pro bono / D2M-adjacent | d2mconcierge draft | N/A | THUNDERBIRD-Commander-Review |
| Personal non-D2M | johnloucks3 draft | Already allowed — no change | WING-PERSONAL-DRAFT |
| D2M-to-Chief internal | johnloucks3 direct send | johnloucks3 draft (if OK given) | WING-PERSONAL-DRAFT |

*Amendment authored: V. Hale, per Commander directive 2026-06-14*

---

## AMENDMENT 2026-06-14B — D2M EMAIL SIGNATURE LAYOUT (Commander directive)

### Rule: Every D2M client email has TWO signature elements, in this order

```
[Email body]

────────────────────────────────────────
[Persona complete signature block — Hale or Dani, whoever authored the email]
  → avatar image · name · title · DREAMS2MEMORIES TRAVEL · email

[Commander's D2M signature block — VERY BOTTOM]
  → John A Loucks III · Owner · phone · email · website · D2M logo
```

### Element 1 — Persona complete signature block (above Commander sig)
- **Use the complete canonical sig block file** — not just an avatar image or emoji
- **Hale emails:** `storage/signatures/hale_sig.html`
  - Avatar: `victoria_hale_avatar.png` · Name: Victoria "Victory" Hale · Title: Chief of Staff
- **Dani emails:** `storage/signatures/dani_sig.html`
  - Avatar: `dani_moreau_avatar.png` · Name: Dani Moreau · Title: Concierge Intelligence
- Both sig files are self-contained HTML tables with base64-embedded avatars (64×64px, circular border)
- Placed ABOVE Commander's sig block, separated by a thin rule or whitespace
- Persona sig does NOT go at the very bottom — Commander sig occupies that slot

### Element 2 — Commander's D2M sig block (VERY BOTTOM — always last)
Source of truth: `storage/signatures/commander_d2m_sig.html` (pulled from Gmail 2026-06-14)

```
John A Loucks III
Owner, Dreams2Memories, LLC
719-291-0742
johnloucks3@gmail.com
www.d2mluxury.quest
[D2M logo image]
```

Full HTML: `storage/signatures/commander_d2m_sig.html`
Logo src (stable): `https://lh3.googleusercontent.com/d/1HYa61cNwcialWk64DimGwIfCAbUjESsu`

### Canonical sig file inventory (storage/signatures/)
| File | Persona | Contains |
|---|---|---|
| `hale_sig.html` | Victoria Hale (COS) | avatar · name · Chief of Staff · D2M · concierge email |
| `dani_sig.html` | Dani Moreau | avatar · name · Concierge Intelligence · D2M · concierge email |
| `commander_d2m_sig.html` | Commander (footer) | John A Loucks III · Owner · phone · email · D2M logo |

### What this replaces
Prior rule (Decision 6) placed only the persona avatar in the sig. This amendment specifies use of COMPLETE persona signature blocks (canonical files) plus Commander's D2M sig as permanent footer on all D2M client emails.

### Applies to
All D2M client-facing products: validation emails, lifecycle TPs, proposals, itineraries, insurance emails. Does NOT apply to internal Wing-to-Commander reports/briefs (those stay streamlined — no Commander sig block needed on his own reports).

*Amendment authored: V. Hale, per Commander directive 2026-06-14*
