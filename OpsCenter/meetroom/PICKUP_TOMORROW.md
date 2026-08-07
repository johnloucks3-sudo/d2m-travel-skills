# WAR ROOM — PICK UP TOMORROW (2026-08-07)
**Resume marker.** Git tag: `war-room` (commit `14574d86c`). Mission: **MISSION-786**.

## Where things stand
| Item | Status |
|---|---|
| Capability: ROUND TABLE — virtual play-by-play meetroom for the 4 HALES | OPEN at **T2 design gate** |
| Commander view (live) | ✅ https://d2mluxury.quest/meetroom/rt.html — deck verified playing (4 cards, zero JS errors) |
| Inputs filed | CC ✅ AG ✅ OC ✅ **Grok ⬜ — needs Commander's grok.com login (bsk can't SSO)** |
| Committed + tagged | ✅ `war-room` |

## Next (in order)
1. **T3 — Grok:** Commander signs into grok.com in the connected bsk browser → harvest `grok_hale_input.md` (same 4-question brief as the other seats; `grok_call.py --model heavy`).
2. **T2 — Commander approves `ROUND_TABLE_SPEC.md`** (design gate).
3. **T4 — rescue** `scratch/FOR_DELETION/run_ag_staff_meeting.py` (prototype; CC flagged — don't delete).
4. **Build phase** (after T2+T3): `rt_brief.py` (OC) · `round_table.py` (CC) · `rt_recorder.py` (AG).
5. **T8 build gate:** courtroom audit + Silver gate. **T9:** dry-run session. **T10:** first live ROUND TABLE.

## Night log (2026-08-06, sign-off)
- **Competitive scan ran (web lane).** Perplexity key EXPIRED (401) — flagged for rotation. 5 candidates shortlisted in `WAR_ROOM_COMPETITIVE_SCAN.md`.
- **Commander chose prototypes #1 + #4:** **ATO** (multi-LLM war-room, MIT, open-source) and **ChatDev 2.0 (DevAll)** (zero-code multi-agent web console).
- Bring-up was DISPATCHED then CANCELLED at sign-off — **prototypes NOT yet built.** Next session: run them (see tasks).

## Tomorrow, first things
1. **Prototype ATO** → `PROTO_ATO.md` · **Prototype ChatDev 2.0** → `PROTO_CHATDEV.md` (both to `/tmp/opencode/`, reversible, no repo edits).
2. **T3 Grok** — Commander grok.com login → file `grok_hale_input.md`.
3. **T2** — Commander signs `ROUND_TABLE_SPEC.md` (design gate).
4. Then T4 rescue + build `rt_brief/round_table/rt_recorder`.

## Open Commander wants from yesterday
- RT Desk one-click index page (all papers/charts/slides one click) — proposed, unbuilt
- Charts/images lanes attachable to cards (Grok Imagine when login's back)

## Files
- Spec: `OpsCenter/meetroom/ROUND_TABLE_SPEC.md` · Concept: `ROUND_TABLE_CONCEPT.md` · Walkthrough: `walkthrough.md`
- Inputs: `{cc,ag,oc,grok}_hale_input.md` · Viewer: `rt_view.py` (+`rt.html`)
- Deployment: `d2m-dashboard.service` :8901 `/meetroom` mount in `core/visual_synthesis/dashboard_app/server.py`
