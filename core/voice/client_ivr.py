#!/usr/bin/env python3
"""
client_ivr.py — Voice-based client IVR (Twilio)

Phone interface for existing D2M clients to self-serve four intents:
booking status, excursions, final payment date, and who their concierge is.

⚠️ WF-17 boundary: this answers callers in real time with no per-call human
review — same category as an email/SMS client send. Non-financial answers
(concierge identity, general excursion info) go out unverified. Financial
specifics (balance, final payment date/amount) are gated behind a caller
verification step (DOB match against the dossier, or booking-reference
fallback) before they're spoken. Writing this module is not the same as
authorizing it against real client phone traffic — pointing a live Twilio
number at real clients needs Commander/WF-17 sign-off first.

Architecture: stdlib HTTPServer + twilio.twiml (matches OpsCenter/whatsapp_webhook.py).
Twilio POSTs -> validate signature -> per-CallSid state machine -> TwiML response.

Endpoints:
  POST /voice          Twilio Voice webhook (initial call + every Gather turn)
  POST /voice/status   Twilio status callback — writes call duration on completion
  GET  /health

Data source: dossiers/*.md YAML frontmatter (parsed independently of
scripts/validate_dossier.py to avoid importing a non-network module into a
network-facing process). TESS/portal live lookup is NOT wired here — that
needs an interactive OAuth flow that can't run inside a webhook handler, so
financial figures are dossier-sourced and tagged as such in every log line.

Known limitations (documented, not hidden):
  - Verification DOB parsing only recognizes ISO, MM/DD/YYYY, and "Month D,
    YYYY" forms in Twilio's speech-to-text output — not spelled-out words
    ("nineteen sixty"). Needs a real-call pass to tune against actual STT output.
  - Excursion answers are deliberately generic (dossiers don't reliably carry
    a structured excursion list) — Rule 1 Negative-Space doctrine: don't state
    specifics that aren't confirmed in a primary source.
  - Call state lives in-process memory, not persisted — a process restart
    mid-call drops context back to GREETING.
  - "10 real test calls" from the task spec were not run — there's no
    provisioned Twilio number/public endpoint in this environment. See
    test_client_ivr.py for the simulated-call test suite that stands in for it.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import sys
from base64 import b64encode
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qsl

from twilio.twiml.voice_response import Dial, Gather, VoiceResponse

THUNDERBIRD = Path(__file__).parent.parent.parent
DOSSIERS_DIR = THUNDERBIRD / "dossiers"
CALL_LOG = Path(__file__).parent / "call_log.jsonl"

PORT = 8771
COMMANDER_PHONE = "+17192910742"
CONCIERGE_NAME = "Dani Moreau"

log = logging.getLogger("client-ivr")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# In-process per-call conversation state, keyed by Twilio CallSid.
CALL_STATES: dict[str, dict] = {}

_MONTHS = {name.lower(): i for i, name in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}

_DOB_RE = re.compile(r"DOB[:\s]+(\d{4}-\d{2}-\d{2})", re.IGNORECASE)

_ESCALATE_PHRASES = ("human", "real person", "representative", "operator",
                     "talk to someone", "speak to someone", "speak with someone")
_FINAL_PAYMENT_PHRASES = ("final payment", "balance", "how much do i owe",
                          "what do i owe", "payment due", "due date", "owe")
_EXCURSION_PHRASES = ("excursion", "shore", "tour", "activities", "port")
_CONCIERGE_PHRASES = ("concierge", "who is my agent", "who's my agent",
                      "travel agent", "who is my concierge", "who's my concierge")
_BOOKING_STATUS_PHRASES = ("booking", "status", "confirmed", "reservation",
                           "my trip", "my cruise", "my voyage")
_NEGATIVE_PHRASES = ("no", "nothing", "that's all", "thats all", "goodbye", "bye")
_NAME_STOPWORDS = {"and", "the", "of", "de", "la", "mr", "mrs", "dr", "ms"}


# ── env ──────────────────────────────────────────────────────────────────────
def load_env() -> dict:
    env = dict(os.environ)
    env_file = THUNDERBIRD / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


# ── dossier data bridge ──────────────────────────────────────────────────────
def parse_frontmatter(path: Path) -> dict | None:
    """Extract YAML frontmatter from a dossier markdown file."""
    text = path.read_text(errors="replace")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    fm_block = text[3:end].strip()
    fields: dict[str, str] = {}
    for line in fm_block.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fields[k.strip()] = v.split("#")[0].strip().strip('"')
    return fields


def load_client_records() -> list[dict]:
    """Every dossier with frontmatter + a booking number, flattened to one record each."""
    records = []
    if not DOSSIERS_DIR.exists():
        return records
    for path in sorted(DOSSIERS_DIR.glob("*.md")):
        fields = parse_frontmatter(path)
        if not fields or not fields.get("booking"):
            continue
        fields["_path"] = str(path)
        records.append(fields)
    return records


def _extract_dob(path: Path) -> str | None:
    """Best-effort DOB lookup in the dossier body (e.g. 'DOB 1959-08-31')."""
    text = path.read_text(errors="replace")
    m = _DOB_RE.search(text)
    return m.group(1) if m else None


def find_client_by_speech(records: list[dict], utterance: str) -> list[dict]:
    """Match a spoken last name or booking number against loaded dossier records."""
    speech_norm = re.sub(r"[^a-z0-9 ]", "", utterance.lower())
    speech_words = set(speech_norm.split())
    digits = re.sub(r"\D", "", utterance)

    matches = []
    for r in records:
        booking = re.sub(r"\D", "", str(r.get("booking", "")))
        if digits and len(digits) >= 5 and digits in booking:
            matches.append(r)
            continue
        full_name = r.get("full_name", "").lower()
        if not full_name:
            continue
        name_words = {w for w in re.sub(r"[^a-z0-9 ]", "", full_name).split()
                      if len(w) >= 3 and w not in _NAME_STOPWORDS}
        if name_words & speech_words:
            matches.append(r)
    # de-dupe while preserving order (a record can match on both name and digits)
    seen = set()
    deduped = []
    for r in matches:
        key = r.get("booking")
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    return deduped


# ── speech parsing helpers ───────────────────────────────────────────────────
def parse_spoken_date(text: str) -> str | None:
    """Best-effort ISO date extraction from Twilio speech-to-text output."""
    if not text:
        return None
    t = text.strip()
    m = re.search(r"\d{4}-\d{2}-\d{2}", t)
    if m:
        return m.group(0)
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", t)
    if m:
        mm, dd, yyyy = m.groups()
        return f"{int(yyyy):04d}-{int(mm):02d}-{int(dd):02d}"
    m = re.search(r"([A-Za-z]+)\s+(\d{1,2})[a-z]{0,2},?\s+(\d{4})", t)
    if m:
        month_name, dd, yyyy = m.groups()
        month = _MONTHS.get(month_name.lower())
        if month:
            return f"{int(yyyy):04d}-{month:02d}-{int(dd):02d}"
    return None


def speak_date(iso: str) -> str:
    try:
        d = date.fromisoformat(iso)
    except Exception:
        return iso or "a date we have on file"
    month = ["January", "February", "March", "April", "May", "June", "July",
             "August", "September", "October", "November", "December"][d.month - 1]
    return f"{month} {d.day}, {d.year}"


def spell_digits(s) -> str:
    digits = re.sub(r"\D", "", str(s))
    return ", ".join(digits) if digits else str(s)


# ── intent classification ────────────────────────────────────────────────────
def classify_intent(text: str) -> str:
    t = (text or "").lower()
    if any(p in t for p in _ESCALATE_PHRASES):
        return "escalate"
    if any(p in t for p in _FINAL_PAYMENT_PHRASES):
        return "final_payment"
    if any(p in t for p in _EXCURSION_PHRASES):
        return "excursions"
    if any(p in t for p in _CONCIERGE_PHRASES):
        return "concierge"
    if any(p in t for p in _BOOKING_STATUS_PHRASES):
        return "booking_status"
    return "unclear"


# ── response builders (dossier-sourced, tagged as such in the log) ──────────
def respond_booking_status(record: dict) -> str:
    line = record.get("cruise_line", "")
    ship = record.get("ship", "your ship")
    departure = record.get("departure", "")
    payment_status = record.get("payment_status", "")
    status_map = {"paid_in_full": "paid in full", "active": "confirmed and active"}
    status_txt = status_map.get(payment_status, payment_status or "on file")
    dep_txt = speak_date(departure) if departure else "a date I don't have on file"
    return (f"Your {line} {ship} booking is {status_txt}, departing {dep_txt}.")


def respond_final_payment(record: dict) -> str:
    payment_status = record.get("payment_status", "")
    if payment_status == "paid_in_full":
        return "Good news — your final payment has already been received in full. No balance is due."
    fpd = record.get("fpd", "")
    amount = record.get("fpd_amount", "")
    if not fpd:
        return "I don't have a final payment date on file for this booking. I'll connect you with your concierge to confirm."
    try:
        amt_txt = f"${int(float(amount)):,}" if amount else "the remaining balance"
    except ValueError:
        amt_txt = "the remaining balance"
    return f"Your final payment of {amt_txt} is due on {speak_date(fpd)}."


def respond_excursions(record: dict) -> str:
    return ("Your shore excursions are confirmed as part of your voyage package. "
            "For the port-by-port excursion schedule, I'll have your concierge send "
            "that over, or you can check your D2M client portal if one's been set up "
            "for this trip.")


def respond_concierge(record: dict) -> str:
    return f"{CONCIERGE_NAME} is your Concierge at Dreams to Memories Travel — she's your point of contact for anything about this trip."


# ── call log ─────────────────────────────────────────────────────────────────
def log_call_event(call_sid: str, event: dict) -> None:
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "call_sid": call_sid, **event}
    CALL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with CALL_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")


# ── TwiML builders ───────────────────────────────────────────────────────────
def _twiml_gather(prompt: str) -> str:
    vr = VoiceResponse()
    gather = Gather(input="speech dtmf", action="/voice", method="POST",
                     speech_timeout="auto", language="en-US", timeout=6)
    gather.say(prompt, voice="Polly.Joanna")
    vr.append(gather)
    vr.say("Sorry, I didn't get a response.", voice="Polly.Joanna")
    vr.redirect("/voice")
    return str(vr)


def _twiml_say(text: str, hangup: bool = False) -> str:
    vr = VoiceResponse()
    vr.say(text, voice="Polly.Joanna")
    if hangup:
        vr.hangup()
    return str(vr)


# ── state machine ─────────────────────────────────────────────────────────────
def _new_state() -> dict:
    return {
        "stage": "GREETING",
        "record": None,
        "candidates": [],
        "intent": None,
        "verified": False,
        "verify_attempts": 0,
        "identify_attempts": 0,
    }


def get_or_init_state(call_sid: str) -> dict:
    return CALL_STATES.setdefault(call_sid, _new_state())


def _escalate(call_sid: str, state: dict, reason: str) -> str:
    record = state.get("record") or {}
    log_call_event(call_sid, {"event": "escalated", "reason": reason,
                               "matched_booking": record.get("booking")})
    CALL_STATES.pop(call_sid, None)
    vr = VoiceResponse()
    vr.say("Let me connect you with a member of our team.", voice="Polly.Joanna")
    dial = Dial(timeout=20)
    dial.number(COMMANDER_PHONE)
    vr.append(dial)
    vr.say("We weren't able to connect you right now. Please call back, or email d2mconcierge@gmail.com.",
           voice="Polly.Joanna")
    return str(vr)


def _handle_identify(call_sid: str, state: dict, speech: str, digits: str) -> str:
    utterance = speech or digits
    if not utterance:
        state["identify_attempts"] += 1
        if state["identify_attempts"] >= 2:
            return _escalate(call_sid, state, "no_identify_input")
        return _twiml_gather("I didn't catch a name or booking number. Please say your last name or booking reference.")

    if any(p in utterance.lower() for p in _ESCALATE_PHRASES):
        return _escalate(call_sid, state, "explicit_human_request")

    records = load_client_records()
    matches = find_client_by_speech(records, utterance)

    if len(matches) == 1:
        state["record"] = matches[0]
        state["stage"] = "INTENT"
        log_call_event(call_sid, {"event": "identified",
                                   "matched_booking": matches[0].get("booking"),
                                   "matched_name": matches[0].get("full_name")})
        return _twiml_gather(
            "Thanks, I have your booking on file. How can I help — you can ask about "
            "your booking status, your excursions, your final payment, or who your concierge is.")

    if len(matches) > 1:
        state["candidates"] = matches
        state["stage"] = "DISAMBIGUATE"
        return _twiml_gather("I found more than one booking under that name. Please say your full booking reference number.")

    state["identify_attempts"] += 1
    if state["identify_attempts"] >= 2:
        return _escalate(call_sid, state, "no_match")
    return _twiml_gather("I couldn't find a booking under that name. Please say your booking reference number instead.")


def _handle_disambiguate(call_sid: str, state: dict, speech: str, digits: str) -> str:
    utterance = digits or speech or ""
    digit_str = re.sub(r"\D", "", utterance)
    for r in state["candidates"]:
        booking = re.sub(r"\D", "", str(r.get("booking", "")))
        if digit_str and digit_str in booking:
            state["record"] = r
            state["stage"] = "INTENT"
            log_call_event(call_sid, {"event": "identified", "matched_booking": r.get("booking"),
                                       "matched_name": r.get("full_name"), "via": "disambiguation"})
            return _twiml_gather("Got it. How can I help — booking status, excursions, final payment, or your concierge?")
    state["identify_attempts"] += 1
    if state["identify_attempts"] >= 2:
        return _escalate(call_sid, state, "disambiguation_failed")
    return _twiml_gather("I still couldn't match that. Please say your full booking reference number.")


def _deliver_financial_response(call_sid: str, state: dict) -> str:
    record = state["record"]
    intent = state["intent"]
    text = respond_booking_status(record) if intent == "booking_status" else respond_final_payment(record)
    log_call_event(call_sid, {"event": "response_given", "intent": intent, "verified": True,
                               "source": "dossier", "response_summary": text[:200]})
    state["stage"] = "FOLLOWUP"
    return _twiml_gather(text + " Is there anything else I can help with?")


def _handle_intent(call_sid: str, state: dict, speech: str, digits: str) -> str:
    utterance = speech or ""
    intent = classify_intent(utterance)
    state["intent"] = intent
    record = state["record"]
    log_call_event(call_sid, {"event": "intent_detected", "intent": intent,
                               "matched_booking": record.get("booking")})

    if intent == "escalate":
        return _escalate(call_sid, state, "explicit_human_request")
    if intent == "unclear":
        return _twiml_gather(
            "Sorry, I didn't understand. You can ask about your booking status, "
            "your excursions, your final payment, or who your concierge is.")
    if intent == "concierge":
        text = respond_concierge(record)
        log_call_event(call_sid, {"event": "response_given", "intent": intent, "verified": False,
                                   "source": "static", "response_summary": text[:200]})
        state["stage"] = "FOLLOWUP"
        return _twiml_gather(text + " Is there anything else I can help with?")
    if intent == "excursions":
        text = respond_excursions(record)
        log_call_event(call_sid, {"event": "response_given", "intent": intent, "verified": False,
                                   "source": "dossier", "response_summary": text[:200]})
        state["stage"] = "FOLLOWUP"
        return _twiml_gather(text + " Is there anything else I can help with?")

    # booking_status / final_payment carry financial specifics — verify first
    if state["verified"]:
        return _deliver_financial_response(call_sid, state)
    state["stage"] = "VERIFY"
    return _twiml_gather("For your security, please say your date of birth — for example, January 5th, 1960.")


def _handle_verify(call_sid: str, state: dict, speech: str, digits: str) -> str:
    record = state["record"]
    dob_on_file = _extract_dob(Path(record["_path"]))
    spoken = parse_spoken_date(speech) if speech else None

    ok = False
    if dob_on_file and spoken and spoken == dob_on_file:
        ok = True
    elif not dob_on_file and digits:
        booking = re.sub(r"\D", "", str(record.get("booking", "")))
        if booking and (digits.endswith(booking[-4:]) or digits == booking):
            ok = True

    if ok:
        state["verified"] = True
        log_call_event(call_sid, {"event": "verified", "matched_booking": record.get("booking")})
        return _deliver_financial_response(call_sid, state)

    state["verify_attempts"] += 1
    log_call_event(call_sid, {"event": "verify_failed", "attempt": state["verify_attempts"]})
    if state["verify_attempts"] >= 2:
        return _escalate(call_sid, state, "verification_failed")
    return _twiml_gather("That doesn't match our records. Please say your date of birth again, or say 'human' to speak with someone.")


def _handle_followup(call_sid: str, state: dict, speech: str, digits: str) -> str:
    utterance = (speech or "").lower()
    if any(w in utterance for w in _NEGATIVE_PHRASES):
        log_call_event(call_sid, {"event": "call_ended_by_caller"})
        CALL_STATES.pop(call_sid, None)
        return _twiml_say("Thank you for calling Dreams to Memories Travel. Have a wonderful day.", hangup=True)
    state["stage"] = "INTENT"
    return _handle_intent(call_sid, state, speech, digits)


def process_turn(call_sid: str, from_number: str, speech: str, digits: str) -> str:
    """Core IVR state machine — one Twilio webhook turn in, one TwiML string out.

    Kept free of any HTTP/socket concerns so it's directly unit-testable.
    """
    state = get_or_init_state(call_sid)
    speech = (speech or "").strip()
    digits = (digits or "").strip()
    stage = state["stage"]

    if stage == "GREETING":
        log_call_event(call_sid, {"event": "call_started", "caller": from_number})
        state["stage"] = "IDENTIFY"
        return _twiml_gather(
            "Thank you for calling Dreams to Memories Travel. "
            "Please say your last name or your booking reference number.")
    if stage == "IDENTIFY":
        return _handle_identify(call_sid, state, speech, digits)
    if stage == "DISAMBIGUATE":
        return _handle_disambiguate(call_sid, state, speech, digits)
    if stage == "INTENT":
        return _handle_intent(call_sid, state, speech, digits)
    if stage == "VERIFY":
        return _handle_verify(call_sid, state, speech, digits)
    if stage == "FOLLOWUP":
        return _handle_followup(call_sid, state, speech, digits)
    return _escalate(call_sid, state, "unknown_stage")


def handle_status_callback(call_sid: str, call_status: str, call_duration: str) -> None:
    """Twilio status callback — fires on ringing/answered/completed. We only
    care about the terminal event, where CallDuration is populated."""
    if call_status != "completed":
        return
    try:
        duration_seconds = int(call_duration) if call_duration else None
    except ValueError:
        duration_seconds = None
    log_call_event(call_sid, {"event": "call_completed", "call_status": call_status,
                               "duration_seconds": duration_seconds})
    CALL_STATES.pop(call_sid, None)


# ── Twilio signature validation (same algorithm as OpsCenter/whatsapp_webhook.py) ──
def validate_twilio_request(url: str, params: dict, signature: str, auth_token: str) -> bool:
    if not auth_token:
        log.error("TWILIO_AUTH_TOKEN not set — cannot validate signature")
        return False
    s = url
    for key in sorted(params.keys()):
        s += key + (params[key] or "")
    mac = hmac.new(auth_token.encode(), s.encode("utf-8"), hashlib.sha1)
    computed_sig = b64encode(mac.digest()).decode()
    valid = hmac.compare_digest(computed_sig, signature)
    if not valid:
        log.warning("Twilio signature FAILED (computed=%s, got=%s)", computed_sig, signature)
    return valid


# ── HTTP server ──────────────────────────────────────────────────────────────
PUBLIC_URL_BASE = os.environ.get("IVR_PUBLIC_URL_BASE", "https://voice.d2mluxury.quest")


class IVRHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log.info(fmt, *args)

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"client-ivr OK")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path not in ("/voice", "/voice/", "/voice/status", "/voice/status/"):
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        params = dict(parse_qsl(body))

        signature = self.headers.get("X-Twilio-Signature", "")
        url = f"{PUBLIC_URL_BASE}{self.path}"
        auth_token = load_env().get("TWILIO_AUTH_TOKEN", "")
        if not validate_twilio_request(url, params, signature, auth_token):
            self.send_response(403)
            self.end_headers()
            return

        call_sid = params.get("CallSid", "")

        if self.path.startswith("/voice/status"):
            handle_status_callback(call_sid, params.get("CallStatus", ""), params.get("CallDuration", ""))
            self.send_response(204)
            self.end_headers()
            return

        from_number = params.get("From", "")
        speech = params.get("SpeechResult", "")
        digits = params.get("Digits", "")
        twiml = process_turn(call_sid, from_number, speech, digits)

        self.send_response(200)
        self.send_header("Content-Type", "text/xml")
        self.end_headers()
        self.wfile.write(twiml.encode("utf-8"))


class _ReuseAddrHTTPServer(HTTPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    log.info("Client IVR starting on port %d", PORT)
    log.info("Voice webhook: %s/voice  Status callback: %s/voice/status", PUBLIC_URL_BASE, PUBLIC_URL_BASE)
    server = _ReuseAddrHTTPServer(("127.0.0.1", PORT), IVRHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutdown")
