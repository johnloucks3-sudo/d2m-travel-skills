# STANDING ORDER — TP / Client-Draft Routing (johnloucks3 + send-as concierge)
**Date:** 2026-06-20 · **Authority:** Commander directive ("do we need to revise the process for TP drafts sent to johnloucks3 vs d2m") · **Author:** Hale (A7 Sterling process review post-hoc) · **Status:** ACTIVE
**Supersedes (for D2M client products):** the "client drafts → d2mconcierge only / NEVER johnloucks3" rule in `SO_EMAIL_RULES_UPDATE_20260530.md`, `SO_DRAFT_ROUTING_20260614.md`, and memory `feedback_johnloucks3_no_drafts`.

---

## THE DECISION
**All D2M client products (lifecycle TPs, validation emails, proposals, itineraries) stage as drafts in `johnloucks3`, with From = `concierge@d2mluxury.quest` (verified send-as alias) and Reply-To = concierge.**

## WHY (the conflict this resolves)
- **Old rule:** client products draft in d2mconcierge, label THUNDERBIRD-Commander-Review, Commander sends from d2mconcierge.
- **Reality:** Commander does not review or send from d2mconcierge — "I'm not going to look at anything in d2m drafts, I tried, cannot send you comments easily, no formatting." Drafts staged there stall; pipeline backs up (this is exactly how 5 WF-17 drafts aged in the queue).
- **The old rule's only purpose** was to keep the D2M business identity (`concierge@d2mluxury.quest`) on the send rather than John's personal address.
- **Resolving fact (verified 2026-06-20):** `concierge@d2mluxury.quest` is a verified (`accepted`) send-as alias on **johnloucks3** as well as d2mconcierge. So a draft can live in johnloucks3 (Commander's actual workspace) and still send with the D2M brand identity. The trade-off vanishes.

## THE RULE
| What | Where | From | Reply-To |
|---|---|---|---|
| D2M client products (TP/lifecycle, validation, proposals, itineraries) | **johnloucks3 drafts** | `concierge@d2mluxury.quest` | `concierge@d2mluxury.quest` |
| Pro bono / D2M-adjacent (vendor, research that goes to a client) | **johnloucks3 drafts** | `concierge@d2mluxury.quest` | `concierge@d2mluxury.quest` |
| Personal non-D2M (classmate, family, friend) | johnloucks3 drafts (WING-PERSONAL-DRAFT) | johnloucks3 (personal) | johnloucks3 |
| Internal (briefs, reports, intel) | johnloucks3 inbox — FULL SEND, no draft | d2mconcierge or wing | n/a |

- **Per-send override available:** for a purely personal note to a close friend-client, Commander may switch From to johnloucks3 at send time. Default for client products stays concierge.
- **WF-17 unchanged:** the draft is staged; the Commander is still the sole executor of the client send. Staging location/identity does NOT touch the WF-17 gate.
- **Build pattern:** create draft with `msg["from"] = "concierge@d2mluxury.quest"` and `msg["reply-to"] = "concierge@d2mluxury.quest"` against the johnloucks3 OAuth token (`creds/johnloucks3_token.json`). Reference: `drafts/redo_20260620/fix_from_sendas.py`.

## PROCESS-GAP FIX BUNDLED HERE
Sent client emails were not clearing the WF-17 lifecycle queue (`storage/lifecycle_draft_queue.jsonl`), so already-sent content (Kuklinski dining, sent May 15) kept resurfacing as "voice_drafted." Sterling owns closing this: a sent/superseded touchpoint must flip its queue status. Manual sweep done 2026-06-20; automation is a Sterling backlog item.
