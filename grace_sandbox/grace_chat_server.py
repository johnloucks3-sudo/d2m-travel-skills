#!/usr/bin/env python3
"""
grace_chat_server.py — public chat backend for GRACE, D2M's gift-world persona.
Hale build · 2026-06-16 · serves the Google-Messages-style page at /buddy/grace/

WHAT THIS IS
  A tiny, killable HTTP service that lets a NON-technical visitor (no login, no key)
  message Grace from a web page. The D2M free Gemini key lives server-side here and
  NEVER reaches the browser. Grace's persona FRAME is applied to every turn.

GUARDRAILS (per docs/GRACE_TOOL_ALLOWLIST.md + the "Lend It Out" proposal)
  - Free Gemini 2.5 Flash, D2M key from repo .env, server-side only.
  - Daily hard cap 15,000 calls (shared counter grace_sandbox/.grace_call_count.json).
  - Per-IP throttle (beta abuse guard): 30 messages / 5 min.
  - Max input length 4,000 chars; only gemini-2.5-flash; no tools (plain text chat).
  - Message CONTENT is never logged or stored (privacy: free tier already sends to Google;
    D2M adds no second copy). Only counts/timestamps are kept.
  - No D2M business/client data is reachable from here — it only talks to Gemini.
Bind: 127.0.0.1:8911  (nginx proxies /buddy/grace/api/ -> here)
"""

import os
import re
import json
import time
import datetime
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

REPO_ROOT = "/home/john/Thunderbird"
ENV_FILE = os.path.join(REPO_ROOT, ".env")
COUNTER_FILE = os.path.join(REPO_ROOT, "grace_sandbox", ".grace_call_count.json")
STATIC_DIR = os.path.join(REPO_ROOT, "grace_sandbox", "public")

MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    f"models/{MODEL}:generateContent"
)

HOST, PORT = "127.0.0.1", 8911
DAILY_CALL_CAP = 15_000
MAX_INPUT_CHARS = 4_000
MAX_HISTORY_TURNS = 16          # cap context we send to Gemini
IP_WINDOW_SEC = 300             # 5 min
IP_MAX_IN_WINDOW = 30
HTTP_TIMEOUT = 30

# Grace's voice — kept in sync with scripts/grace.sh FRAME.
FRAME = (
    "You are Grace — a warm, patient 58-year-old helper for Dreams2Memories' free, "
    "public-good program. Your whole life has been making intimidating things feel "
    "possible: library reference desk, adult literacy, helping veterans through VA "
    "paperwork. You give help with NO strings attached and ask for nothing back. "
    "Voice: plain-spoken, dignified, unhurried. Short sentences. Never make anyone "
    "feel behind or foolish. Never use jargon — never say 'AI', 'LLM', or 'prompt'; "
    "it's just 'ask it'. Lead with dignity, not cleverness. Be honest about limits: "
    "say plainly when something should be double-checked, and never invite anyone to "
    "share another person's private medical or financial details. You serve people, "
    "not clients — never discuss prices, bookings, or sales. If someone wants to plan "
    "or book a trip, warmly tell them a real person at Dreams2Memories will follow up, "
    "and keep helping with whatever else they need. Keep replies fairly short unless "
    "they ask for more."
)


def load_key():
    with open(ENV_FILE) as f:
        for line in f:
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("GEMINI_API_KEY not found in .env")


GEMINI_KEY = load_key()


# ---- daily cap counter (shared with grace_agent.py) -----------------------
def bump_daily_counter():
    today = datetime.date.today().isoformat()
    data = {"date": today, "count": 0}
    try:
        with open(COUNTER_FILE) as f:
            data = json.load(f)
    except Exception:
        pass
    if data.get("date") != today:
        data = {"date": today, "count": 0}
    if data["count"] >= DAILY_CALL_CAP:
        return False, data["count"]
    data["count"] += 1
    try:
        with open(COUNTER_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass
    return True, data["count"]


# ---- per-IP throttle ------------------------------------------------------
_ip_hits = defaultdict(deque)


def throttle_ok(ip):
    now = time.time()
    dq = _ip_hits[ip]
    while dq and now - dq[0] > IP_WINDOW_SEC:
        dq.popleft()
    if len(dq) >= IP_MAX_IN_WINDOW:
        return False
    dq.append(now)
    return True


def call_gemini(user_msg, history):
    contents = []
    for turn in history[-MAX_HISTORY_TURNS:]:
        role = turn.get("role")
        text = (turn.get("text") or "").strip()
        if not text:
            continue
        g_role = "user" if role == "user" else "model"
        contents.append({"role": g_role, "parts": [{"text": text}]})
    contents.append({"role": "user", "parts": [{"text": user_msg}]})

    payload = {
        "systemInstruction": {"parts": [{"text": FRAME}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048,
            # Gemini 2.5 Flash is a THINKING model: thinking tokens count against
            # maxOutputTokens. At the old 800 cap, ~345 tokens went to internal
            # "thoughts", leaving the reply to truncate mid-sentence (or come back
            # empty) — the "partial responses" Stefanie reported. Grace is a plain
            # warm helper and needs no extended reasoning, so we turn thinking off
            # and give the whole budget to the reply. (Verified 2026-06-17.)
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    r = requests.post(
        f"{GEMINI_URL}?key={GEMINI_KEY}",
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=HTTP_TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    try:
        cand = data["candidates"][0]
        text = cand["content"]["parts"][0]["text"].strip()
        # Safety net: if a very long answer still hits the cap, close gently
        # instead of cutting mid-sentence.
        if cand.get("finishReason") == "MAX_TOKENS":
            text += ("\n\n(There's more I can share on this — just say "
                     "\"keep going\" and I'll continue.)")
        return text
    except (KeyError, IndexError):
        # safety / blocked / empty
        return ("I'm sorry — I couldn't find the words for that one. "
                "Try asking it a little differently?")


class Handler(BaseHTTPRequestHandler):
    server_version = "GraceChat/1.0"

    def _send(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, relpath, ctype):
        # Serve only from STATIC_DIR; never follow paths outside it.
        safe = os.path.normpath(os.path.join(STATIC_DIR, relpath))
        if not safe.startswith(STATIC_DIR + os.sep) and safe != STATIC_DIR:
            self._send(404, {"error": "not found"}); return
        try:
            with open(safe, "rb") as f:
                body = f.read()
        except OSError:
            self._send(404, {"error": "not found"}); return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path.rstrip("/") in ("/health", "/buddy/grace/api/health"):
            self._send(200, {"ok": True, "persona": "grace"})
        elif path in ("/", "/index.html", "/buddy/grace/", "/buddy/grace/index.html"):
            self._send_file("index.html", "text/html; charset=utf-8")
        elif path in ("/grace_avatar.png", "/buddy/grace/grace_avatar.png"):
            self._send_file("grace_avatar.png", "image/png")
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path.split("?", 1)[0].rstrip("/") not in (
            "/chat", "/api/chat", "/buddy/grace/api/chat"
        ):
            self._send(404, {"error": "not found"})
            return

        # Public path is Cloudflare -> cloudflared tunnel -> here (nginx bypassed),
        # so the real client IP arrives as CF-Connecting-IP, not X-Real-IP.
        ip = (self.headers.get("CF-Connecting-IP")
              or self.headers.get("X-Real-IP")
              or self.client_address[0])
        if not throttle_ok(ip):
            self._send(429, {"error": "Slow down a moment, then try again."})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            req = json.loads(raw or b"{}")
        except Exception:
            self._send(400, {"error": "bad request"})
            return

        msg = (req.get("message") or "").strip()
        history = req.get("history") or []
        if not msg:
            self._send(400, {"error": "empty message"})
            return
        if len(msg) > MAX_INPUT_CHARS:
            msg = msg[:MAX_INPUT_CHARS]

        ok, count = bump_daily_counter()
        if not ok:
            self._send(503, {"reply": (
                "I've helped a lot of folks today and need to rest until tomorrow. "
                "Please come back in the morning — I'll be right here.")})
            return

        try:
            reply = call_gemini(msg, history if isinstance(history, list) else [])
        except Exception:
            self._send(502, {"reply": (
                "Something on my end hiccuped. Give it a minute and ask me again.")})
            return

        self._send(200, {"reply": reply})

    def log_message(self, fmt, *args):
        # Privacy: never log message bodies. Only method + status + IP + day-count.
        return


def main():
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"[grace_chat] listening on http://{HOST}:{PORT}  model={MODEL} cap={DAILY_CALL_CAP}/day")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    main()
