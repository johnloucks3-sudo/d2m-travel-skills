"""
core/comms/slack_transport.py — Slack transport for the Commander channel.

C2 RECALIBRATION Phase 3, Commander directive 2026-07-29.
Workspace: newworkspace-wya3670.slack.com

WHY SLACK, AND WHY IT IS NOT A REWRITE
--------------------------------------
The Commander has now tried Signal, WhatsApp, SMS and Telegram as C2. All four failed,
because the failure was never the channel — it was the absence of a gate. So Slack
enters as a RENDERER behind core/comms/commander_channel.py::notify(), not as a parallel
path. Everything Slack receives has already been deduped, format-checked and batched.

What Slack adds that the other four could not: a tap that is a RECORD. Approve / Close /
Defer buttons write straight to the closure ledger, so "I closed this" becomes a fact in
a file rather than an intention in an inbox. That is the fix for "I reduce my queue and
it keeps getting overridden."

CREDENTIALS
-----------
  SLACK_BOT_TOKEN  xoxb-…  Web API: post messages, create channels.
  SLACK_APP_TOKEN  xapp-…  Socket Mode: receive button clicks with NO public URL.

The app token matters more than it looks. Without Socket Mode, interactive buttons
require a publicly reachable HTTPS endpoint — a tunnel, a cert, another thing to break.
With it, the button path runs over an outbound websocket from this host.

This module is on the test_no_direct_sends ALLOWLIST because it IS a transport — the
thing the gate calls. It must never be called directly by feature code.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

import requests

ROOT = Path(__file__).resolve().parents[2]

API = "https://slack.com/api"
TIMEOUT = 15

COMMAND_CHANNEL = "d2m-command"   # consolidated briefs land here
ALERT_CHANNEL = "d2m-alerts"      # urgency=NOW breakthroughs only


class SlackError(RuntimeError):
    """Slack refused the call. Carries the API error string verbatim."""


# ─────────────────────────────────────────────────────────────────────────────────
# Credentials
# ─────────────────────────────────────────────────────────────────────────────────

def _load_env_file() -> None:
    """Read .env without a dotenv dependency. Never overwrites a real env var."""
    envf = ROOT / ".env"
    if not envf.exists():
        return
    for line in envf.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def bot_token() -> Optional[str]:
    _load_env_file()
    t = (os.environ.get("SLACK_BOT_TOKEN") or "").strip()
    return t if t.startswith("xoxb-") else None


def app_token() -> Optional[str]:
    _load_env_file()
    t = (os.environ.get("SLACK_APP_TOKEN") or "").strip()
    return t if t.startswith("xapp-") else None


def is_configured() -> bool:
    return bot_token() is not None


# ─────────────────────────────────────────────────────────────────────────────────
# Web API
# ─────────────────────────────────────────────────────────────────────────────────

def _call(method: str, payload: dict[str, Any]) -> dict:
    tok = bot_token()
    if not tok:
        raise SlackError(
            "SLACK_BOT_TOKEN missing or malformed (expected an xoxb- prefix). "
            "Add it to /home/john/Thunderbird/.env"
        )
    r = requests.post(f"{API}/{method}", timeout=TIMEOUT,
                      headers={"Authorization": f"Bearer {tok}",
                               "Content-Type": "application/json; charset=utf-8"},
                      data=json.dumps(payload).encode("utf-8"))
    try:
        data = r.json()
    except ValueError:
        raise SlackError(f"{method}: non-JSON response (HTTP {r.status_code})")
    if not data.get("ok"):
        raise SlackError(f"{method}: {data.get('error', 'unknown error')}")
    return data


def whoami() -> dict:
    """auth.test — the cheapest proof the token actually works."""
    return _call("auth.test", {})


def granted_scopes() -> set[str]:
    """What the installed token can actually do, straight from Slack's response header.

    Assuming scopes from the manifest is how you get a 3am `missing_scope` on the one
    night it matters. Ask the API instead.
    """
    tok = bot_token()
    if not tok:
        return set()
    try:
        r = requests.post(f"{API}/auth.test", timeout=TIMEOUT,
                          headers={"Authorization": f"Bearer {tok}"})
        return {s.strip() for s in r.headers.get("x-oauth-scopes", "").split(",") if s.strip()}
    except requests.RequestException:
        return set()


def ensure_channel(name: str) -> str:
    """Return a channel reference usable by chat.postMessage.

    Degrades deliberately rather than failing shut. A thin token must not cost the
    Commander a payment-deadline alert, so this walks down:

      1. channels:read present  -> resolve the real channel id (and create it if
         channels:manage is also present).
      2. Neither present        -> fall back to the '#name' literal, which
         chat.postMessage accepts for public channels when the bot holds
         chat:write.public or is already a member.

    The fallback is the reason a Slack install with only chat:write still delivers.
    """
    name = name.lstrip("#")
    scopes = granted_scopes()

    if "channels:read" in scopes:
        cursor = ""
        while True:
            params = {"limit": 200, "exclude_archived": True,
                      "types": "public_channel,private_channel"}
            if cursor:
                params["cursor"] = cursor
            try:
                data = _call("conversations.list", params)
            except SlackError:
                break                       # scope revoked mid-flight — use the fallback
            for ch in data.get("channels", []):
                if ch.get("name") == name:
                    return ch["id"]
            cursor = (data.get("response_metadata") or {}).get("next_cursor") or ""
            if not cursor:
                break

        if "channels:manage" in scopes:
            try:
                return _call("conversations.create",
                             {"name": name, "is_private": False})["channel"]["id"]
            except SlackError as e:
                if "name_taken" not in str(e):
                    raise

    return f"#{name}"


# ─────────────────────────────────────────────────────────────────────────────────
# Rendering — Block Kit from the same payload email gets
# ─────────────────────────────────────────────────────────────────────────────────

_TAG = re.compile(r"<[^>]+>")


def _html_to_mrkdwn(html: str) -> str:
    """Slack speaks mrkdwn, not HTML. Convert rather than dump tags into the channel —
    shipping raw markup is the exact defect this whole recalibration exists to end."""
    s = html
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</(p|div|tr|h[1-6]|li)>", "\n", s, flags=re.I)
    s = re.sub(r"<li[^>]*>", "• ", s, flags=re.I)
    s = re.sub(r"</t[dh]>", "  ", s, flags=re.I)
    s = re.sub(r"<(strong|b)>(.*?)</\1>", r"*\2*", s, flags=re.I | re.S)
    s = re.sub(r"<(em|i)>(.*?)</\1>", r"_\2_", s, flags=re.I | re.S)
    s = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", s, flags=re.I | re.S)
    s = re.sub(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', r"<\1|\2>", s, flags=re.I | re.S)
    s = _TAG.sub("", s)
    for ent, ch in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                    ("&nbsp;", " "), ("&#39;", "'"), ("&quot;", '"')):
        s = s.replace(ent, ch)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def build_blocks(title: str, body: str, *, item_id: Optional[str] = None,
                 urgency: str = "WINDOW") -> list[dict]:
    """Block Kit for one item. When item_id is given, attach the action row —
    that is what turns a notification into a closable piece of work."""
    text = _html_to_mrkdwn(body) if "<" in body else body
    if len(text) > 2900:                       # Slack section limit is 3000
        text = text[:2880] + "\n… (truncated)"

    icon = "🔴" if urgency == "NOW" else "📋"
    blocks: list[dict] = [
        {"type": "header",
         "text": {"type": "plain_text", "text": f"{icon} {title}"[:150], "emoji": True}},
        {"type": "section", "text": {"type": "mrkdwn", "text": text or "_(no content)_"}},
    ]
    if item_id:
        blocks.append({"type": "actions", "block_id": f"act::{item_id}", "elements": [
            {"type": "button", "action_id": "approve", "style": "primary",
             "text": {"type": "plain_text", "text": "Approve"}, "value": item_id},
            {"type": "button", "action_id": "close",
             "text": {"type": "plain_text", "text": "Close"}, "value": item_id},
            {"type": "button", "action_id": "defer",
             "text": {"type": "plain_text", "text": "Defer"}, "value": item_id},
        ]})
    return blocks


# ─────────────────────────────────────────────────────────────────────────────────
# Public entry point — called BY the gate, never by feature code
# ─────────────────────────────────────────────────────────────────────────────────

def post(title: str, body: str, *, urgency: str = "WINDOW",
         item_id: Optional[str] = None, channel: Optional[str] = None) -> dict:
    ch_name = channel or (ALERT_CHANNEL if urgency == "NOW" else COMMAND_CHANNEL)
    ch_id = ensure_channel(ch_name)
    res = _call("chat.postMessage", {
        "channel": ch_id,
        "text": title,                          # notification/fallback text
        "blocks": build_blocks(title, body, item_id=item_id, urgency=urgency),
        "unfurl_links": False, "unfurl_media": False,
    })
    return {"channel": ch_name, "channel_id": ch_id, "ts": res.get("ts")}


def publish_home(user_id: str, view: dict) -> dict:
    """views.publish — replace a user's App Home tab wholesale.

    Unlike chat.postMessage this is not additive: every call replaces whatever the tab
    currently shows, in full. That is the property that makes App Home fit a live queue
    view instead of another stream to scroll past — it renders current state, not one
    more notification on top of the last one.

    Like the rest of this module, publish_home is on the test_no_direct_sends ALLOWLIST
    because it IS a transport — the thing the gate/home layer calls. It must never be
    called directly by feature code.
    """
    return _call("views.publish", {"user_id": user_id, "view": view})


def selftest() -> int:
    """`python3 -m core.comms.slack_transport` — proves the wiring end to end."""
    if not is_configured():
        print("SLACK_BOT_TOKEN not set. Add it to .env:")
        print("  printf 'SLACK_BOT_TOKEN=xoxb-…\\nSLACK_APP_TOKEN=xapp-…\\n' >> "
              f"{ROOT}/.env")
        return 2
    try:
        who = whoami()
        print(f"auth.test OK — team={who.get('team')} bot={who.get('user')}")
        have = granted_scopes()
        want = {"chat:write", "chat:write.public", "channels:manage",
                "channels:read", "groups:read", "im:write", "users:read"}
        print(f"granted scopes: {', '.join(sorted(have)) or '(none reported)'}")
        missing = sorted(want - have)
        if missing:
            print(f"missing scopes: {', '.join(missing)}")
            print("  -> add at api.slack.com/apps > OAuth & Permissions > Bot Token Scopes,")
            print("     then Reinstall to Workspace. Posting still works via the #name fallback.")
        print(f"socket-mode app token: "
              f"{'present' if app_token() else 'ABSENT (buttons stay inert until it is set)'}")
        r = post("Thunderbird C2 — transport check",
                 "Slack transport is live. This message came through "
                 "`commander_channel.notify()`, so it was deduped, format-checked "
                 "and routed like everything else.\n\n"
                 "Buttons activate once the Socket Mode receiver is running.",
                 item_id="c2-selftest")
        print(f"posted to #{r['channel']} ts={r['ts']}")
        return 0
    except SlackError as e:
        print(f"FAIL: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(selftest())
