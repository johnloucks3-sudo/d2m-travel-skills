"""
core/comms/slack_receiver.py — Socket Mode receiver. A tap becomes a record.

C2 RECALIBRATION Phase 3, Commander directive 2026-07-29.

WHY THIS IS THE POINT OF SLACK
------------------------------
The Commander has tried Signal, WhatsApp, SMS and Telegram as C2. All four failed,
and none of them could do the one thing that actually matters here: make his decision
STICK. He closes an item, and the next regeneration brings it back.

core/comms/commander_queue.py fixed the ledger side. This module closes the loop from
his end — an Approve / Close / Defer tap in Slack writes straight into that append-only
ledger. One tap, permanently recorded, no email round trip, no "I'll get to it."

WHY SOCKET MODE AND NOT A WEBHOOK
---------------------------------
Interactive Slack buttons normally need a publicly reachable HTTPS endpoint — a tunnel,
a cert, a DNS record, and three more things that break at 2am. Socket Mode instead opens
an OUTBOUND websocket from this host. Nothing inbound, nothing exposed, no tunnel. That
is why the xapp- app token matters more than it looks.

RUNNING IT
----------
    SLACK_BOT_TOKEN=xoxb-…   Web API   (post, update messages)
    SLACK_APP_TOKEN=xapp-…   Socket Mode (receive interactions)

    python3 -m core.comms.slack_receiver            # foreground, prints what it does
    systemctl --user start slack-receiver.service   # unit ships alongside this file

Degrades honestly: with no tokens it prints exactly what is missing and exits 2,
rather than looping on a connection it can never make.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.comms import slack_transport as tx          # noqa: E402
from core.comms.commander_queue import close, reopen  # noqa: E402

AUDIT_PATH = ROOT / "OpsCenter" / "slack_interactions.jsonl"

# Slack drops the socket if an envelope is not acked quickly; keep handlers cheap.
ACK_DEADLINE_SEC = 3
RECONNECT_BACKOFF = (1, 2, 5, 10, 30, 60)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audit(**row: Any) -> dict:
    row.setdefault("ts", _now())
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    return row


# ─────────────────────────────────────────────────────────────────────────────────
# Connection
# ─────────────────────────────────────────────────────────────────────────────────

def open_connection() -> str:
    """apps.connections.open — exchange the app token for a one-shot WSS URL."""
    app_tok = tx.app_token()
    if not app_tok:
        raise tx.SlackError(
            "SLACK_APP_TOKEN missing or malformed (expected an xapp- prefix). "
            "Socket Mode cannot start without it."
        )
    r = requests.post("https://slack.com/api/apps.connections.open", timeout=tx.TIMEOUT,
                      headers={"Authorization": f"Bearer {app_tok}"})
    data = r.json()
    if not data.get("ok"):
        raise tx.SlackError(f"apps.connections.open: {data.get('error', 'unknown')}")
    return data["url"]


# ─────────────────────────────────────────────────────────────────────────────────
# Interaction handling
# ─────────────────────────────────────────────────────────────────────────────────

def _new_task_modal_view() -> dict:
    """Block Kit for the App Home 'File a task' modal — title required, priority
    and owner optional. The title input ships WITHOUT "optional": true, so Slack's
    own client refuses to submit an empty title before it ever reaches us; that
    matters because by the time handle_view_submission runs, the envelope has
    already been acked with no payload (see _run_once), so there is no way to
    reject back into the modal via response_action at that point."""
    return {
        "type": "modal",
        "callback_id": "new_task",
        "title": {"type": "plain_text", "text": "File a Task"},
        "submit": {"type": "plain_text", "text": "Create"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "task_title",
                "label": {"type": "plain_text", "text": "Title"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "value",
                    "placeholder": {"type": "plain_text", "text": "What needs doing?"},
                },
            },
            {
                "type": "input",
                "block_id": "task_priority",
                "optional": True,
                "label": {"type": "plain_text", "text": "Priority"},
                "element": {
                    "type": "static_select",
                    "action_id": "value",
                    "placeholder": {"type": "plain_text", "text": "P2 (default)"},
                    "options": [
                        {"text": {"type": "plain_text", "text": "P0 — now"}, "value": "P0"},
                        {"text": {"type": "plain_text", "text": "P1 — today"}, "value": "P1"},
                        {"text": {"type": "plain_text", "text": "P2 — routine"}, "value": "P2"},
                    ],
                },
            },
            {
                "type": "input",
                "block_id": "task_owner",
                "optional": True,
                "label": {"type": "plain_text", "text": "Owner"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "value",
                    "placeholder": {"type": "plain_text", "text": "unassigned"},
                },
            },
        ],
    }


def _handle_open_task_modal(payload: dict, user: str) -> dict:
    """action_id == "open_task_modal" — push the new-task modal.

    Must be fast and do nothing else first: trigger_id expires ~3s after Slack
    issues it, and it is one-shot (a second views.open with the same trigger_id
    fails).
    """
    trigger_id = payload.get("trigger_id")
    if not trigger_id:
        return _audit(status="error", detail="open_task_modal carried no trigger_id",
                      user=user)
    try:
        tx.open_modal(trigger_id, _new_task_modal_view())
    except Exception as exc:
        return _audit(status="error", detail=f"open_modal failed: "
                      f"{type(exc).__name__}: {exc}", user=user)
    return _audit(status="ok", detail="task modal opened", user=user)


def handle_block_action(payload: dict) -> Optional[dict]:
    """Turn one button tap into a ledger entry.

    Attribution matters here. The tap comes from the Commander's own Slack account, so
    it is recorded as by="Commander" — this is the ONE place that attribution is
    genuinely earned rather than assumed. commander_queue.close() requires `by`
    explicitly precisely so it can never be defaulted into elsewhere.
    """
    actions = payload.get("actions") or []
    if not actions:
        return None
    action = actions[0]
    action_id = action.get("action_id")
    user = (payload.get("user") or {}).get("username") or (payload.get("user") or {}).get("id", "?")

    # "File a task" opens a modal — it carries a trigger_id, not an item_id, so it
    # is dispatched before the item_id extraction below (which every Approve/
    # Close/Defer button relies on).
    if action_id == "open_task_modal":
        return _handle_open_task_modal(payload, user)

    item_id = (action.get("value") or "").strip()

    if not item_id:
        return _audit(status="ignored", detail="button carried no item id", action_id=action_id)

    try:
        if action_id in ("close", "approve"):
            verb = "Closed" if action_id == "close" else "Approved"
            close(item_id, by="Commander", reason=f"Slack {action_id} by {user}",
                  source="slack_button")
            result = f"✅ {verb} — {item_id} is off your desk permanently."
        elif action_id == "defer":
            # Defer is deliberately NOT a close. It leaves the item open; the record
            # exists so a deferral is visible rather than silent.
            reopen(item_id, by="Commander", reason=f"Slack defer by {user}")
            result = f"⏸ Deferred — {item_id} stays on your desk."
        else:
            return _audit(status="ignored", detail=f"unknown action_id {action_id!r}",
                          item_id=item_id)
    except Exception as exc:
        return _audit(status="error", item_id=item_id, action_id=action_id,
                      detail=f"{type(exc).__name__}: {exc}")

    row = _audit(status="ok", item_id=item_id, action_id=action_id, user=user, result=result)

    # Mirror the decision into the canonical audit trail.
    #
    # commander_queue.close() above makes the closure PERMANENT — that is the fix for
    # "my queue keeps getting overridden" and it is not in question. But it writes only
    # to commander_closures.jsonl. hale_decisions.md is what the rest of the Wing parses,
    # and until this call existed the Commander's taps never reached it: three real taps
    # on 2026-07-29 landed in the ledger and left no trace in the audit trail. Found by a
    # test that asserted the absence rather than by reading anyone's report.
    #
    # actor="Commander" is asserted explicitly and is EARNED here — payload["user"] was
    # read above, so this call site genuinely knows the tap came from his own account.
    # tcd_actions.apply() defaults to "ai" precisely so no other caller can claim this.
    #
    # Best-effort by design: TCD items and commander_queue items are different id spaces,
    # so a mission id simply will not resolve in the TCD set. That is expected, not an
    # error, and it must never undo a closure that already succeeded.
    if action_id in ("close", "approve"):
        try:
            from core.comms import tcd_actions
            tcd_actions.apply(item_id, "close", actor="Commander",
                              value=f"Slack {action_id} by {user}")
            row["audit_trail"] = "hale_decisions.md"
        except Exception as exc:
            row["audit_trail_skipped"] = f"{type(exc).__name__}: {exc}"

    # Republish App Home so the item actually LEAVES his desk.
    #
    # An App Home tap has no response_url — that only exists for channel messages — so
    # without this the view is only rebuilt on the next app_home_opened event. The
    # Commander taps Close, the closure is recorded permanently, and the card just sits
    # there looking untouched. He reported exactly that on 2026-07-29: "When I CLOSE an
    # item in Slack it does not disappear." The record was right; the screen was lying.
    #
    # Best-effort: a failed republish must never undo a closure that already succeeded.
    user_id = (payload.get("user") or {}).get("id")
    if user_id and (payload.get("view") or {}).get("type") == "home":
        try:
            from core.comms import slack_home
            from core.comms.commander_queue import build_queue
            tx.publish_home(user_id=user_id,
                            view=slack_home.build_home_view(build_queue().get("items", [])))
            row["home_republished"] = True
        except Exception as exc:
            row["home_republish_error"] = f"{type(exc).__name__}: {exc}"

    # Replace the buttons with the outcome so the channel shows state, not stale options.
    try:
        rt = payload.get("response_url")
        if rt:
            requests.post(rt, timeout=tx.TIMEOUT, json={
                "replace_original": True,
                "text": result,
                "blocks": [{"type": "section",
                            "text": {"type": "mrkdwn", "text": result}}],
            })
    except Exception as exc:
        row["update_error"] = f"{type(exc).__name__}: {exc}"
    return row


def handle_app_home_opened(payload: dict) -> Optional[dict]:
    """Render the App Home tab when the Commander opens it.

    slack_home owns the view — what the tab looks like, which items it draws from — this
    receiver only wires the trigger to the render. slack_home is being built in parallel
    by another agent, so its absence must degrade to an audit row, never a crash: the
    receiver is live C2, and a bad or half-built import must not take Approve/Close/Defer
    down with it.
    """
    event = payload.get("event") or {}
    user_id = event.get("user")
    if not user_id:
        return _audit(status="ignored", detail="app_home_opened carried no user id")

    try:
        from core.comms import slack_home
    except Exception as exc:
        return _audit(status="error", detail=f"slack_home import failed: "
                      f"{type(exc).__name__}: {exc}", user=user_id)

    try:
        from core.comms.commander_queue import build_queue
        # slack_home exports build_home_view, not build_view. Two agents built the two
        # halves of this call in parallel and each picked a reasonable name; the mismatch
        # would have failed into an audit row rather than an exception, so App Home would
        # simply never render while nothing looked broken. Caught by checking the module's
        # actual exports instead of trusting either agent's report.
        view = slack_home.build_home_view(build_queue().get("items", []))
        tx.publish_home(user_id=user_id, view=view)
    except Exception as exc:
        return _audit(status="error", detail=f"app_home render/publish failed: "
                      f"{type(exc).__name__}: {exc}", user=user_id)

    return _audit(status="ok", detail="app_home published", user=user_id)


def _field(values: dict, block_id: str) -> Optional[str]:
    """Pull one value out of view.state.values — a plain_text_input keys its value
    under "value", a static_select keys it under "selected_option"."""
    block = values.get(block_id) or {}
    for element in block.values():
        v = element.get("value")
        if v:
            return v.strip()
        opt = element.get("selected_option")
        if opt:
            return opt.get("value")
    return None


def handle_view_submission(payload: dict) -> Optional[dict]:
    """callback_id == "new_task" — file a REAL mission from the modal.

    Goes through OpsCenter/mission_board_sync.py's own add_mission() — the single
    creation + open-duplicate-check path that module documents as "the ONE place
    mission-creation ... logic lives" — never mission_board.json directly, and
    respects the module's own fcntl lock (acquire_lock/save_board), same as every
    other real caller (cmd_add, tcd/writeback.py's create-task path).

    A failed creation must not crash the receiver — this is live C2. Anything that
    goes wrong lands as an _audit row, never an exception that reaches _dispatch.

    Note on the 3-second ack: by the time this runs, _run_once has already acked
    the envelope with no payload (ACK FIRST — see that function's comment), so
    there is no response_action available here to reject back into the modal.
    That is why the title field in _new_task_modal_view is a required (non-
    optional) input block — Slack's client enforces it before submission ever
    reaches this handler.
    """
    view = payload.get("view") or {}
    if view.get("callback_id") != "new_task":
        return None  # some other modal's submission — not ours

    user = (payload.get("user") or {}).get("username") or (payload.get("user") or {}).get("id", "?")
    values = (view.get("state") or {}).get("values") or {}

    title = _field(values, "task_title")
    priority = _field(values, "task_priority") or "P2"
    owner = _field(values, "task_owner") or "unassigned"

    if not title:
        # Defensive only — the modal's required input block should prevent this.
        return _audit(status="error", detail="new_task submitted with no title",
                      user=user)

    try:
        from tcd._imports import load_mission_board_sync
        mbs = load_mission_board_sync()
        fd = mbs.acquire_lock()
        try:
            board = mbs.load_board()
            message, mission_id = mbs.add_mission(
                board, title, description="Filed from Slack App Home (New Task modal)",
                priority=priority, assigned_to=owner, source="slack",
            )
            mbs.save_board(board, fd)
        except Exception:
            mbs.release_lock(fd)
            raise
    except Exception as exc:
        return _audit(status="error", detail=f"mission creation failed: "
                      f"{type(exc).__name__}: {exc}", user=user, title=title,
                      priority=priority, owner=owner)

    return _audit(status="ok", detail="mission created via Slack modal", user=user,
                  mission_id=mission_id, title=title, priority=priority, owner=owner,
                  board_message=message)


def _dispatch(envelope: dict) -> None:
    etype = envelope.get("type")
    payload = envelope.get("payload") or {}
    if etype == "interactive" and payload.get("type") == "block_actions":
        handle_block_action(payload)
    elif etype == "interactive" and payload.get("type") == "view_submission":
        handle_view_submission(payload)
    elif etype == "slash_commands":
        _audit(status="ignored", detail="slash command received; no handler wired yet",
               command=payload.get("command"))
    elif etype == "events_api" and (payload.get("event") or {}).get("type") == "app_home_opened":
        handle_app_home_opened(payload)
    # all other events_api envelopes are acked and dropped — this receiver exists for
    # decisions, not for mirroring channel chatter into the Wing.


# ─────────────────────────────────────────────────────────────────────────────────
# Loop
# ─────────────────────────────────────────────────────────────────────────────────

async def _run_once() -> None:
    import websockets

    url = open_connection()
    print(f"[slack-receiver] connected {url.split('?')[0]}")
    async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
        async for raw in ws:
            try:
                env = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if env.get("type") == "hello":
                print("[slack-receiver] hello — listening for Approve/Close/Defer")
                continue
            if env.get("type") == "disconnect":
                print(f"[slack-receiver] server asked us to reconnect "
                      f"({env.get('reason')})")
                return

            # Log EVERY envelope before doing anything with it. On 2026-07-29 a tap
            # produced total silence and there was no way to tell "Slack never sent it"
            # from "we received it and ignored it" — two very different bugs. One line
            # here collapses that ambiguity permanently.
            print(f"[slack-receiver] envelope type={env.get('type')!r} "
                  f"payload_type={(env.get('payload') or {}).get('type')!r}")

            # ACK FIRST. Slack tears down the socket if an envelope is not acked
            # promptly, so the ledger write must never sit in front of the ack.
            eid = env.get("envelope_id")
            if eid:
                await ws.send(json.dumps({"envelope_id": eid}))

            try:
                _dispatch(env)
            except Exception as exc:                       # a bad tap must not kill C2
                _audit(status="error", detail=f"dispatch: {type(exc).__name__}: {exc}")


async def run_forever() -> None:
    attempt = 0
    while True:
        try:
            await _run_once()
            attempt = 0                                    # clean reconnect resets backoff
        except Exception as exc:
            delay = RECONNECT_BACKOFF[min(attempt, len(RECONNECT_BACKOFF) - 1)]
            print(f"[slack-receiver] {type(exc).__name__}: {exc} — retry in {delay}s")
            attempt += 1
            await asyncio.sleep(delay)


def main() -> int:
    if not tx.is_configured():
        print("SLACK_BOT_TOKEN missing. Add both tokens to /home/john/Thunderbird/.env:")
        print("  printf 'SLACK_BOT_TOKEN=xoxb-…\\nSLACK_APP_TOKEN=xapp-…\\n' >> "
              f"{ROOT}/.env")
        return 2
    if not tx.app_token():
        print("SLACK_APP_TOKEN missing (xapp-…). Socket Mode needs it; without it the")
        print("Approve/Close/Defer buttons would require a public HTTPS endpoint.")
        return 2
    try:
        who = tx.whoami()
        print(f"[slack-receiver] auth OK — team={who.get('team')} bot={who.get('user')}")
    except tx.SlackError as exc:
        print(f"[slack-receiver] auth failed: {exc}")
        return 1
    try:
        asyncio.run(run_forever())
    except KeyboardInterrupt:
        print("\n[slack-receiver] stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
