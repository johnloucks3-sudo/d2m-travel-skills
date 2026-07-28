# Dossier Visual Card — Data Schema

One JSON file per client in `data/*.json`. Renderer: `render_cards.py` →
`cards/{client_id}.html`. Internal briefing tool — Commander/staff only, never
a client deliverable (see `alerts[].internal_only`).

| Field | Source | Notes |
|---|---|---|
| `client_id` | filename | slug, matches output card filename |
| `display_name` | dossier frontmatter `full_name` | |
| `accent_hex` / `accent_label` | assigned, validated categorical slot | see PALETTE.md — fixed per client, never reused |
| `cruise_line`, `ship`, `voyage_name`, `booking_ref` | dossier frontmatter | |
| `suite`, `deck` | dossier "STATUS" line / Suite Details table | |
| `departure_date`, `return_date` | dossier frontmatter `departure`/`return` | ISO 8601 |
| `payment.overall_status` | dossier frontmatter `payment_status` | `paid` \| `partial` \| `pending` |
| `payment.total_amount`, `paid_to_date`, `balance_due` | dossier "RSSC PORTAL DATA" (portal is Rule 4 authoritative source — falls back to invoice if portal absent) | |
| `payment.stages[]` | dossier Key Dates + portal deposit/FPD lines | ordered list, each stage `status`: `paid` \| `partial` \| `unpaid` — drives the ladder rung color independently, so a 2-stage (deposit+FPD) or 3-stage (+balance) ladder both render correctly |
| `next_touchpoint` | dossier `> LIFECYCLE` note, cross-checked against `hale_brief.md` WF-17 queue | `note` field records any conflict found between sources — do not silently pick one |
| `quick_facts.days_to_departure` | computed: `departure_date` − `data_as_of` | |
| `quick_facts.itinerary_status` | mission board (`MISSION-802` etc.) | |
| `quick_facts.excursions_confirmed/total`, `specialty_dining_confirmed/total` | dossier "SHORE EXCURSIONS" / "Specialty dining" rows | |
| `alerts[]` | dossier flags, mission board P0/P1 items scoped to this client | `level`: `critical` \| `P0` \| `P1` \| `P2` \| `info`. `internal_only: true` = dossier explicitly marks this NEVER-client-copy (e.g. medical) — card renders it with a 🔒 INTERNAL badge, still visible to the Commander |
| `source_dossier`, `data_as_of` | provenance stamp | every card footer cites its source file + pull date — Rule 1 negative-space discipline applied to an internal tool too |

**Extraction note:** fields were hand-verified against the three live dossiers this
pass (2026-07-10), not regex-scraped — dossier markdown structure varies enough
(free-text STATUS lines, inconsistent table formats) that a blind parser risks
silently wrong output on a Commander-facing card. A future pass could add a
regex/LLM extractor with this schema as the target and a diff-against-dossier
check before trusting it unattended.
