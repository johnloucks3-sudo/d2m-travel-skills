"""
tcd.web — real, live web view of the TCD Google Sheet, served on
tcd.d2mluxury.quest via scripts/client_portal_server.py.

This is NOT a static snapshot. Every GET reads tcd.writeback.read_sheet_rows()
fresh; every action button POSTs straight into the same write-back contract
AppSheet already uses (item_model.SHEET_COLUMNS status/stage vocab), then
calls tcd.writeback.process_once() so the action executes immediately instead
of waiting for the 10-minute tcd-sync.timer pass. Same engine, same Sheet,
same audit trail (hale_decisions.md) as AppSheet — this is a second front end
on the existing data plane, not a parallel system.

Action → real vocab mapping (Commander-facing verb -> Sheet write):
  Approve -> stage=D          (Propose -> Decide; process_once auto-tasks to staff)
  Hold    -> status=Reference (parked, out of the active decision queue)
  Reject  -> status=Delete    (real cascade delete at the source)
  Close   -> status=Closed    (marks done, source record kept)
  Modify  -> comments append  (AppSheet-native row edit; process_once logs it)
"""
import html
import json
from urllib.parse import parse_qs

from . import writeback
from . import overrides as _overrides
from .item_model import SHEET_COLUMNS

INBOX_ORDER = [
    ("strategic", "Strategic", ">$5K commitments, >90-day calls, board-level items", "#c98a3f"),
    ("operational", "Operational", "client emails, daily ops, bookings, vendor calls", "#7fb8d9"),
    ("reference", "Reference", "standing orders, dossiers, research archive, parked items", "#6fada6"),
]

ACTIVE_STAGES = {"P", "D", "T"}  # Propose/Decide/Task — not yet Accomplished/Certified

# The Sheet's 311 rows include everything collectors.py pulls — raw Gmail
# inbox sweep (newsletters, CI probes, spam) included. That's fine for
# AppSheet's full board, wrong for a "decide without reading" Commander
# view. Scope down to rows that actually carry a curated decision signal:
# alert-*/watch-* ids (hale_state.json deferred_alerts + prediction-ledger
# watches — hand-curated, not raw inbox), inbox=="strategic" (the explicit
# >$5K/>90d/board-level bucket), or type=="decision". A raw "gmail-*" row
# never qualifies on its own — that prefix is unfiltered inbox mail.
def _id_prefix(row: dict) -> str:
    rid = row.get("id", "")
    return rid.split("-")[0] if rid else ""


def _pending_rows():
    from .multi_tab import collect_multi_tab
    rows = writeback.read_sheet_rows()
    rows.extend(collect_multi_tab())
    # Main-sheet rows already carry overrides baked in via the
    # collectors->sheet_sync round trip; multi_tab rows read a second
    # spreadsheet directly and never pass through that pipeline, so a
    # Commander action on one (see apply_non_sheet_action) would vanish on
    # the next reload without this. Re-applying to already-overridden main
    # rows is a harmless no-op (same value in, same value out).
    persisted = _overrides.load_overrides()
    for row in rows:
        rid = row.get("id", "")
        entry = persisted.get(rid)
        if not entry:
            continue
        if "stage" in entry:
            row["stage"] = _overrides.apply_override(rid, row.get("stage", ""), persisted)
        if "status" in entry:
            row["status"] = _overrides.apply_status(rid, row.get("status", ""), persisted)
        owner = _overrides.apply_owner(rid, persisted)
        if owner:
            row["owner"] = owner
    return rows


# Hold/Modify leave stage and status untouched (see apply_action's Hold
# comment), so the only durable, Sheet-backed signal that either happened is
# the marker text apply_action stamps into ``comments`` — same field
# AppSheet/the Sheet already shows, nothing client-only. rfind so the most
# recently stamped marker (furthest right in the comment trail) wins.
_ACTION_MARKERS = (
    ("[Commander HOLD via tcd.d2mluxury.quest]", "HELD", "held"),
    ("[Commander CLOSE via tcd.d2mluxury.quest]", "CLOSED", "closed"),
    ("[Commander via tcd.d2mluxury.quest]", "MODIFIED", "modified"),
)


def _action_state(row: dict):
    """(decided, label, css_key) derived purely from status/stage/comments —
    fields the Sheet/Gmail mirror already carries — so a page reload always
    shows the true last action instead of an action flashing then vanishing."""
    status = row.get("status", "")
    stage = row.get("stage", "")
    if status == "Closed":
        return True, "CLOSED", "closed"
    if status == "Delete":
        return True, "REJECTED", "rejected"
    if status == "Reference":
        return True, "HELD", "held"
    if stage not in ("", "P"):
        return True, "APPROVED", "approved"
    comments = row.get("comments", "") or ""
    best_idx, best = -1, None
    for marker, label, css_key in _ACTION_MARKERS:
        idx = comments.rfind(marker)
        if idx > best_idx:
            best_idx, best = idx, (label, css_key)
    if best:
        return True, best[0], best[1]
    return False, "", ""


def _card(row: dict) -> str:
    from . import mfr
    rid = html.escape(row.get("id", ""))
    title = html.escape(row.get("title", "") or "(untitled)")
    snippet = html.escape(mfr.describe(row))
    link = html.escape(row.get("link", ""), quote=True)
    source = html.escape(row.get("from", ""))
    date = html.escape(row.get("date", ""))
    priority = html.escape((row.get("priority") or "").upper())
    stage = html.escape(row.get("stage", ""))
    owner = html.escape(row.get("owner", ""))
    link_html = (f'<a class="src-link" href="{link}" target="_blank" rel="noopener">open source ↗</a>'
                 if link else '<span class="src-link" style="opacity:.4">no source link</span>')
    decided, label, css_key = _action_state(row)
    card_class = "card decided" if decided else "card"
    pill_class = f"status-pill show {css_key}" if decided else "status-pill"
    pill_text = html.escape(label)
    return f"""
      <article class="{card_class}" data-id="{rid}">
        <div class="card-main">
          <div class="card-id">{rid} · {priority or '—'} · stage {stage or '—'}{f' · owner {owner}' if owner else ''}</div>
          <div class="card-title">{title}</div>
          <div class="card-detail">{snippet}</div>
          <div class="card-meta"><span><b>From:</b> {source or '—'}</span><span><b>Date:</b> {date or '—'}</span>{link_html}</div>
        </div>
        <div class="card-actions">
          <span class="{pill_class}">{pill_text}</span>
          <div class="btn-row">
            <button class="act approve" data-action="approve">Approve</button>
            <button class="act modify" data-action="modify">Modify</button>
            <button class="act hold" data-action="hold">Hold</button>
            <button class="act reject" data-action="reject">Reject</button>
            <button class="act close" data-action="close">Close</button>
          </div>
        </div>
        <div class="note-field">
          <textarea placeholder="Type your edits or instruction…"></textarea>
          <div class="note-hint"><span>appends to this item's comments on the live Sheet</span><button class="note-commit" type="button">Log as Modified</button></div>
        </div>
      </article>"""


def render_board(rows=None) -> str:
    rows = rows if rows is not None else _pending_rows()
    by_inbox = {"strategic": [], "operational": [], "reference": []}
    for r in rows:
        by_inbox.setdefault(r.get("inbox") or "operational", []).append(r)
    # anything with an inbox value outside the three known ones still shows up
    # somewhere rather than silently vanishing
    for k in list(by_inbox):
        if k not in ("strategic", "operational", "reference"):
            by_inbox["operational"].extend(by_inbox.pop(k))

    sections = []
    total = 0
    for key, label, desc, color in INBOX_ORDER:
        # A Closed card is gone — not shown even collapsed. "Close" means
        # delete it from the board; the audit trail (hale_decisions.md) and
        # the Sheet/override still carry the record, this is display only.
        lane_rows = [r for r in by_inbox.get(key, []) if r.get("status") != "Closed"]
        active_rows = [r for r in lane_rows if r.get("status") not in ("Delete", "Reference") and r.get("stage") in ACTIVE_STAGES]
        closed_rows = [r for r in lane_rows if r.get("status") in ("Delete", "Reference") or r.get("stage") not in ACTIVE_STAGES]
        total += len(active_rows) + len(closed_rows)

        cards = "\n".join(_card(r) for r in active_rows)
        if not cards:
            cards = '<div class="empty-lane">Nothing active pending here right now.</div>'

        closed_cards = "\n".join(_card(r) for r in closed_rows)
        closed_html = ""
        if closed_cards:
            closed_html = f'''
            <details class="closed-section">
                <summary>Show Closed/Reference ({len(closed_rows)})</summary>
                <div class="card-list">{closed_cards}</div>
            </details>
            '''

        sections.append(f"""
  <section class="gate" data-gate="{key}">
    <div class="gate-head">
      <div class="gate-stripe" style="background:{color}"></div>
      <div><div class="gate-title">{label}</div><div class="gate-desc">{desc}</div></div>
    </div>
    <div class="card-list">{cards}</div>
    {closed_html}
  </section>""")
    return _PAGE.replace("__SECTIONS__", "\n".join(sections)).replace("__TOTAL__", str(total))


def apply_action(item_id: str, action: str, note: str = "") -> dict:
    """Write the real vocab for one Commander verb, then run the write-back
    pass immediately so it executes now instead of on the next 10-min timer.

    Every card on the board — whether it came from the main Items sheet or
    from a multi_tab.py tab (mission-/techscan-/next7-, a different
    spreadsheet with no per-row write path) — routes through here and ends
    up durably persisted: main-sheet rows via the real Sheet cell write,
    everything else via writeback.apply_non_sheet_action's override+audit
    fallback. Neither path is client-only state that a reload can wipe.
    """
    sheet_rows = writeback.read_sheet_rows()
    in_sheet = any(r.get("id") == item_id for r in sheet_rows)
    row = next((r for r in _pending_rows() if r.get("id") == item_id), None)
    prior_comments = (row or {}).get("comments", "")

    updates = {}
    if action == "approve":
        updates["stage"] = "D"
    elif action == "hold":
        # status="Reference" is a real SHEET_COLUMNS value but tcd/overrides.py
        # only persists stage/owner overrides — a bare status write here would
        # get silently clobbered by the next 10-min tcd-sync.timer full
        # rewrite (found live, 2026-07-28: wrote Reference, verified gone on
        # next read). A comment IS durable (process_once's comment-diff
        # branch + hale_decisions.md), so Hold logs intent that way instead
        # of pretending a non-durable status flip is a real park action.
        updates["comments"] = f"{prior_comments}\n[Commander HOLD via tcd.d2mluxury.quest]".strip()
    elif action == "reject":
        updates["status"] = "Delete"
    elif action == "close":
        # This board is the one place we can positively assert the caller
        # IS the Commander, so Close here is self-certifying — no reason
        # required, no Silver back-gate (that gate exists to check AI/
        # AppSheet-diff closes, not the Commander's own decision). See
        # _handle_close(actor="commander") in writeback.py.
        stamp = f"\n[Commander CLOSE via tcd.d2mluxury.quest] {note}".rstrip() if note else "\n[Commander CLOSE via tcd.d2mluxury.quest]"
        updates["comments"] = f"{prior_comments}{stamp}".strip()
        updates["status"] = "Closed"
    elif action == "modify":
        if not note:
            return {"ok": False, "error": "no note text supplied for modify"}
        updates["comments"] = f"{prior_comments}\n[Commander via tcd.d2mluxury.quest] {note}".strip()
    else:
        return {"ok": False, "error": f"unknown action {action!r}"}

    if in_sheet:
        writeback._default_write_fn(item_id, updates)
        result = writeback.process_once(actor="commander")
    else:
        result = writeback.apply_non_sheet_action(row or {"id": item_id}, updates, actor="commander")
    return {"ok": True, "action": action, "updates": updates, "process_result": result}


def handle_post_body(raw_body: bytes) -> dict:
    """Accept either JSON {id, action, note} or classic form-encoded POST."""
    try:
        payload = json.loads(raw_body)
    except (ValueError, json.JSONDecodeError):
        parsed = parse_qs(raw_body.decode("utf-8", "replace"))
        payload = {k: v[0] for k, v in parsed.items()}
    item_id = payload.get("id", "")
    action = payload.get("action", "")
    note = payload.get("note", "")
    if not item_id or not action:
        return {"ok": False, "error": "id and action required"}
    return apply_action(item_id, action, note)


_PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Thunderbird Commander Desktop — Decision Board</title>
<style>
  :root {
    --ground:#12161c; --surface:#1a212b; --surface-2:#222b37; --ink:#e9edf3; --ink-dim:#8e9ab0;
    --hairline:#2b3542; --accent:#c98a3f; --accent-ink:#241705; --good:#4fae7c; --good-ink:#06170f;
    --warn:#d9a441; --warn-ink:#221703; --crit:#dd6a52; --crit-ink:#220a04; --focus:#7fb8d9; --focus-ink:#04141c;
    --font-head:-apple-system,"Segoe UI",system-ui,sans-serif; --font-body:-apple-system,"Segoe UI",system-ui,sans-serif;
    --font-mono:ui-monospace,"SF Mono","Cascadia Code","Consolas",monospace;
  }
  @media (prefers-color-scheme: light) {
    :root { --ground:#e7ebef; --surface:#fff; --surface-2:#eef1f5; --ink:#1b232d; --ink-dim:#5b6779;
      --hairline:#d3dae2; --accent:#a8681f; --accent-ink:#fff7ec; --good:#2f8a5e; --good-ink:#eefaf3;
      --warn:#a97316; --warn-ink:#fff8ec; --crit:#b8402a; --crit-ink:#fff1ee; --focus:#2f6f92; --focus-ink:#eef7fb; }
  }
  * { box-sizing:border-box; }
  html,body { margin:0; padding:0; background:var(--ground); color:var(--ink); font-family:var(--font-body); }
  header.board { position:sticky; top:0; z-index:5; background:color-mix(in srgb, var(--ground) 88%, transparent);
    backdrop-filter:blur(10px); border-bottom:1px solid var(--hairline); padding:18px clamp(16px,4vw,40px) 14px; }
  h1 { font-family:var(--font-head); font-weight:800; text-transform:uppercase; letter-spacing:.02em;
    font-size:clamp(18px,2.4vw,24px); margin:0; }
  .subtitle { font-family:var(--font-mono); font-size:12px; color:var(--ink-dim); }
  main { max-width:940px; margin:0 auto; padding:28px clamp(16px,4vw,40px) 80px; display:flex; flex-direction:column; gap:30px; }
  .lede { font-size:14px; color:var(--ink-dim); line-height:1.55; max-width:66ch; }
  section.gate { display:flex; flex-direction:column; gap:12px; }
  .gate-head { display:flex; align-items:center; gap:10px; }
  .gate-stripe { width:3px; height:20px; border-radius:2px; }
  .gate-title { font-family:var(--font-head); font-weight:800; text-transform:uppercase; letter-spacing:.05em; font-size:13px; }
  .gate-desc { font-family:var(--font-mono); font-size:11px; color:var(--ink-dim); }
  .card-list { display:flex; flex-direction:column; gap:10px; }
  .card { position:relative; background:var(--surface); border:1px solid var(--hairline); border-radius:8px; padding:16px 18px;
    display:grid; grid-template-columns:1fr auto; gap:12px 20px; transition:opacity .25s, transform .25s; }
  .card.decided { opacity:.6; }
  .card-main { display:flex; flex-direction:column; gap:6px; min-width:0; padding-right:8px; }
  .card-id { font-family:var(--font-mono); font-size:11px; color:var(--ink-dim); }
  .card-title { font-size:15px; font-weight:600; }
  .card-detail { font-size:13px; color:var(--ink-dim); line-height:1.5; max-width:62ch; }
  .card-meta { display:flex; gap:14px; flex-wrap:wrap; font-family:var(--font-mono); font-size:11px; color:var(--ink-dim); }
  .card-meta b { color:var(--ink); font-weight:600; }
  .src-link { color:var(--focus); text-decoration:none; }
  .card-actions { display:flex; flex-direction:column; gap:6px; align-items:flex-end; justify-content:center; }
  .btn-row { display:flex; gap:6px; flex-wrap:wrap; justify-content:flex-end; max-width:230px; }
  button.act { font-family:var(--font-mono); font-size:11px; text-transform:uppercase; border:1px solid var(--hairline);
    background:var(--surface-2); color:var(--ink); padding:7px 11px; border-radius:5px; cursor:pointer; }
  button.act.approve:hover { background:var(--good); color:var(--good-ink); border-color:var(--good); }
  button.act.modify:hover { background:var(--focus); color:var(--focus-ink); border-color:var(--focus); }
  button.act.hold:hover { background:var(--warn); color:var(--warn-ink); border-color:var(--warn); }
  button.act.reject:hover { background:var(--crit); color:var(--crit-ink); border-color:var(--crit); }
  button.act.close:hover { background:var(--ink); color:var(--ground); border-color:var(--ink); }
  .status-pill { position:absolute; top:10px; right:12px; font-family:var(--font-mono); font-size:10px;
    font-weight:700; text-transform:uppercase; letter-spacing:.03em; padding:4px 10px; border-radius:20px;
    border:1px solid var(--hairline); background:var(--surface-2); color:var(--ink-dim); display:none; }
  .status-pill.show { display:inline-block; }
  .status-pill.approved { background:var(--good); color:var(--good-ink); border-color:var(--good); }
  .status-pill.held { background:var(--warn); color:var(--warn-ink); border-color:var(--warn); }
  .status-pill.rejected { background:var(--crit); color:var(--crit-ink); border-color:var(--crit); }
  .status-pill.modified { background:var(--focus); color:var(--focus-ink); border-color:var(--focus); }
  .status-pill.closed { background:var(--ink); color:var(--ground); border-color:var(--ink); }
  .note-field { grid-column:1/-1; display:none; flex-direction:column; gap:6px; }
  .note-field.show { display:flex; }
  .note-field textarea { width:100%; min-height:60px; background:var(--surface-2); border:1px solid var(--hairline);
    border-radius:5px; color:var(--ink); font-family:var(--font-body); font-size:12.5px; padding:8px 10px; }
  .note-hint { font-family:var(--font-mono); font-size:10.5px; color:var(--ink-dim); display:flex; justify-content:space-between; align-items:center; }
  .note-commit { font-family:var(--font-mono); font-size:10.5px; text-transform:uppercase; background:var(--focus);
    color:var(--focus-ink); border:none; border-radius:4px; padding:4px 9px; cursor:pointer; }
  .empty-lane { font-family:var(--font-mono); font-size:12px; color:var(--ink-dim); border:1px dashed var(--hairline);
    border-radius:8px; padding:16px 18px; }
  .toast { position:fixed; bottom:20px; right:20px; z-index:20; background:var(--ink); color:var(--ground);
    font-family:var(--font-mono); font-size:12px; padding:9px 14px; border-radius:6px; opacity:0;
    transform:translateY(6px); transition:opacity .2s,transform .2s; pointer-events:none; }
  .toast.show { opacity:1; transform:translateY(0); }
  .closed-section { margin-top: 15px; }
  .closed-section summary { font-family:var(--font-mono); font-size:12px; color:var(--ink-dim); cursor:pointer; padding:8px 0; user-select:none; }
  .closed-section .card-list { margin-top: 10px; }
  .closed-section .card { opacity: 0.7; }
</style></head>
<body>
<header class="board">
  <h1>Decision Board</h1>
  <div class="subtitle">THUNDERBIRD COMMANDER DESKTOP · live from the TCD Google Sheet · __TOTAL__ pending · writes execute immediately</div>
</header>
<main>
  <p class="lede"><b style="color:var(--ink)">This is live.</b> Every click writes straight to the same Sheet
  AppSheet uses and runs the same write-back engine — Approve stages it to your staff, Reject deletes it at the
  source, Close removes the card here and marks it done (source record kept, no reason needed). Hold and Modify
  both log a comment to the item's audit trail and gray the card out. Every card, whatever tab it came from, is
  tied to a real Sheet write or a persisted override — nothing shown here is client-only state.
  Reload any time for the current state; no export/import step.</p>
__SECTIONS__
</main>
<div class="toast" id="toast"></div>
<script>
function showToast(msg){var t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');
  clearTimeout(showToast._h);showToast._h=setTimeout(function(){t.classList.remove('show');},2500);}

var PILL_LABELS = {approve:'APPROVED', hold:'HELD', reject:'REJECTED', modify:'MODIFIED'};
var PILL_CLASS = {approve:'approved', hold:'held', reject:'rejected', modify:'modified'};

async function act(card, action){
  var id = card.getAttribute('data-id');
  var noteField = card.querySelector('.note-field');
  var textarea = noteField.querySelector('textarea');
  var note = textarea.value.trim();
  if (action === 'modify' && note === '') { noteField.classList.add('show'); textarea.focus();
    showToast('Type your edits, then click Log as Modified'); return; }
  showToast('Sending ' + action + '…');
  try {
    var res = await fetch('/tcd/act', { method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ id: id, action: action, note: note }) });
    var data = await res.json();
    if (data.ok) {
      if (action === 'close') {
        // Closed cards are deleted from the board — the write already
        // landed (Sheet cell or override, see apply_action), so remove the
        // card now instead of waiting on a full reload.
        showToast(id + ' → closed (removed)');
        card.style.opacity = '0'; card.style.transform = 'scale(.97)';
        setTimeout(function(){ card.remove(); }, 260);
        return;
      }
      card.classList.add('decided');
      var pill = card.querySelector('.status-pill');
      pill.textContent = PILL_LABELS[action] || action.toUpperCase();
      pill.className = 'status-pill show ' + (PILL_CLASS[action] || '');
      showToast(id + ' → ' + action + ' (live)');
      setTimeout(function(){ location.reload(); }, 900);
    } else {
      showToast('Failed: ' + (data.error || 'unknown error'));
    }
  } catch (e) { showToast('Network error: ' + e); }
}

document.querySelectorAll('.card').forEach(function(card){
  card.querySelectorAll('[data-action]').forEach(function(btn){
    btn.addEventListener('click', function(){ act(card, btn.getAttribute('data-action')); });
  });
  card.querySelector('.note-commit').addEventListener('click', function(){ act(card, 'modify'); });
});
</script>
</body></html>"""
