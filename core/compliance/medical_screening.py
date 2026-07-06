"""
core/compliance/medical_screening.py

Pre-voyage medical screening form automation (Phase 4 compliance).

Generates a cruise-line-specific Google Form (built from the same
config/cruise_line_policies.json registry used by cruise_line_policy_checker.py),
schedules it to go out at T-90 days pre-voyage, stages the send as a Gmail
DRAFT (never sends — WF-17 gate, same as core/lifecycle/lifecycle_scheduler.py),
and syncs captured responses into the client's dossier JSON with concerns
flagged (oxygen, mobility aids, allergies, other pre-approval equipment).

PII fence: this module never dispatches guest medical data to OpenCode/
DeepSeek or any external-brain call. All parsing/flagging/dossier-sync happens
locally in this process. Do not add a brain-dispatch call here.

Negative-Space Rule (SO-PIPELINE-INTEGRITY-20260528): a flagged "concern" is a
keyword match against the guest's own answers, not a medical determination —
it is tagged INFERRED and routed for human/cruise-line confirmation, never
asserted as CONFIRMED in client-facing copy.

CLI:
    python3 -m core.compliance.medical_screening generate \\
        --cruise-line "Regent Seven Seas" --ship "Seven Seas Grandeur" \\
        --voyage "Lesser Antilles" --dossier dossiers_json/mcleod_group.json

    python3 -m core.compliance.medical_screening schedule \\
        --dossier dossiers_json/mcleod_group.json --embark-date 2026-12-19

    python3 -m core.compliance.medical_screening sync \\
        --form-id <id> --dossier dossiers_json/mcleod_group.json

    python3 -m core.compliance.medical_screening draft \\
        --form-url <url> --to guest@example.com --dossier dossiers_json/mcleod_group.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

THUNDERBIRD_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICIES_PATH = THUNDERBIRD_ROOT / "config" / "cruise_line_policies.json"
HALE_STATE_PATH = THUNDERBIRD_ROOT / "hale_state.json"

DEFAULT_LEAD_DAYS = 90
CONFIDENCE_INFERRED = "INFERRED"
CONFIDENCE_CONFIRMED = "CONFIRMED"

# Always-asked, cruise-line-agnostic questions. Per-cruise-line medical
# equipment items are appended from config/cruise_line_policies.json.
GENERIC_QUESTIONS: list[dict] = [
    {"text": "Do you require supplemental oxygen (concentrator, tank, or CPAP with oxygen) during travel?",
     "type": "MULTIPLE_CHOICE", "choices": ["Yes", "No"], "concern_key": "oxygen"},
    {"text": "Do you use a mobility aid (wheelchair, scooter, walker, cane)?",
     "type": "MULTIPLE_CHOICE", "choices": ["Yes", "No"], "concern_key": "mobility"},
    {"text": "If yes to a mobility aid — is it collapsible/foldable?",
     "type": "MULTIPLE_CHOICE", "choices": ["Yes", "No", "N/A"], "concern_key": "mobility_collapsible"},
    {"text": "Do you have any food allergies or severe dietary restrictions?",
     "type": "PARAGRAPH", "choices": [], "concern_key": "allergy"},
    {"text": "Are you currently receiving dialysis or other regular medical treatment that must continue onboard?",
     "type": "PARAGRAPH", "choices": [], "concern_key": "dialysis"},
    {"text": "Any other medical condition, equipment, or service animal the ship's medical center should know about before embarkation?",
     "type": "PARAGRAPH", "choices": [], "concern_key": "other"},
]


@dataclass
class ScreeningQuestion:
    text: str
    q_type: str
    choices: list[str]
    concern_key: str


@dataclass
class ScreeningConcern:
    guest_name: str
    concern_key: str
    question: str
    answer: str
    confidence: str
    remediation: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScreeningResult:
    form_id: str
    form_url: str
    response_count: int
    concerns: list[ScreeningConcern]
    responses_summary: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["concerns"] = [c.to_dict() for c in self.concerns]
        return d


def _load_policy_registry(policies_path: Path = DEFAULT_POLICIES_PATH) -> dict:
    with open(policies_path) as f:
        return json.load(f).get("cruise_lines", {})


def _resolve_cruise_line(cruise_line: str, registry: dict) -> tuple[str, dict]:
    needle = cruise_line.strip().lower()
    for name, entry in registry.items():
        if needle == name.lower() or needle in [a.lower() for a in entry.get("aliases", [])]:
            return name, entry
    for name, entry in registry.items():
        aliases = [name.lower()] + [a.lower() for a in entry.get("aliases", [])]
        if any(a in needle or needle in a for a in aliases):
            return name, entry
    return cruise_line, {}


def build_question_set(cruise_line: str, policies_path: Path = DEFAULT_POLICIES_PATH) -> list[ScreeningQuestion]:
    """Cruise-line-specific medical screening question set.

    Generic questions always included; a line-specific preapproval-equipment
    checklist question is appended when the registry has one on file.
    """
    registry = _load_policy_registry(policies_path)
    _, entry = _resolve_cruise_line(cruise_line, registry)
    questions = [ScreeningQuestion(q["text"], q["type"], q["choices"], q["concern_key"]) for q in GENERIC_QUESTIONS]

    equip_rule = entry.get("rules", {}).get("medical_equipment_requiring_preapproval")
    if equip_rule and equip_rule.get("value") and equip_rule.get("confidence") != "UNKNOWN":
        items = equip_rule["value"]
        questions.append(ScreeningQuestion(
            text=f"Do any of your party bring the following ({cruise_line} requires advance notice for these)? Select all that apply.",
            q_type="CHECKBOX",
            choices=list(items) + ["None of the above"],
            concern_key="line_specific_equipment",
        ))
    return questions


def build_form_title(cruise_line: str, ship: str, voyage: str) -> str:
    return f"D2M Pre-Voyage Medical Screening — {cruise_line} {ship} ({voyage})"


def build_form_description(embark_date: str) -> str:
    return (
        "Dreams2Memories Travel asks every guest to complete this brief medical "
        "screening before embarkation so we can flag any advance-approval items "
        "with the cruise line ahead of your sail date. This information stays "
        f"in your D2M file and is used only for embarkation readiness. Sail date: {embark_date}."
    )


# ── Google Forms creation (direct API — same pattern as api/thunderbird_forms_mcp.py) ──

def create_form(cruise_line: str, ship: str, voyage: str, embark_date: str,
                 policies_path: Path = DEFAULT_POLICIES_PATH) -> dict:
    """Create the live Google Form. Returns {form_id, url, edit_url, questions}.

    Uses api.thunderbird_google_auth.get_forms() directly (not the MCP tool)
    so this module can also run standalone from a timer, matching
    core/lifecycle/lifecycle_scheduler.py's convention.
    """
    from api.thunderbird_google_auth import get_forms  # deferred: optional heavy import

    service = get_forms()
    title = build_form_title(cruise_line, ship, voyage)
    description = build_form_description(embark_date)

    result = service.forms().create(body={"info": {"title": title}}).execute()
    form_id = result["formId"]

    service.forms().batchUpdate(formId=form_id, body={"requests": [{
        "updateFormInfo": {"info": {"description": description}, "updateMask": "description"},
    }]}).execute()

    questions = build_question_set(cruise_line, policies_path)
    for q in questions:
        item: dict = {"questionItem": {"question": {}}}
        if q.q_type == "PARAGRAPH":
            item["questionItem"]["question"]["textQuestion"] = {"paragraph": True}
        elif q.q_type == "TEXT":
            item["questionItem"]["question"]["textQuestion"] = {"paragraph": False}
        else:
            type_map = {"MULTIPLE_CHOICE": "RADIO", "CHECKBOX": "CHECKBOX", "DROPDOWN": "DROP_DOWN"}
            item["questionItem"]["question"]["choiceQuestion"] = {
                "type": type_map.get(q.q_type, "RADIO"),
                "options": [{"value": c} for c in q.choices],
            }
        item["title"] = q.text
        service.forms().batchUpdate(formId=form_id, body={
            "requests": [{"createItem": {"item": item, "location": {"index": 0}}}]
        }).execute()

    info = service.forms().get(formId=form_id).execute()
    return {
        "form_id": form_id,
        "url": info.get("responderUri", ""),
        "edit_url": f"https://docs.google.com/forms/d/{form_id}/edit",
        "questions": [q.__dict__ for q in questions],
    }


def fetch_responses(form_id: str) -> list[dict]:
    """Pull raw responses via the Forms API directly."""
    from api.thunderbird_google_auth import get_forms

    service = get_forms()
    form_info = service.forms().get(formId=form_id).execute()
    question_map = {}
    for item in form_info.get("items", []):
        qid = item.get("questionItem", {}).get("question", {}).get("questionId")
        if qid:
            question_map[qid] = item.get("title", "")

    result = service.forms().responses().list(formId=form_id).execute()
    parsed = []
    for resp in result.get("responses", []):
        answers = []
        for qid, answer_data in resp.get("answers", {}).items():
            text_answers = answer_data.get("textAnswers", {}).get("answers", [])
            values = [a.get("value", "") for a in text_answers]
            answers.append({"question": question_map.get(qid, ""), "answer": "; ".join(values)})
        parsed.append({"response_id": resp.get("responseId", ""), "answers": answers})
    return parsed


# ── Concern flagging (local-only — never routed through OpenCode/DeepSeek) ──

_CONCERN_KEY_BY_QUESTION_SUBSTRING = {
    "oxygen": "oxygen", "cpap": "oxygen",
    "mobility aid": "mobility", "wheelchair": "mobility", "scooter": "mobility", "walker": "mobility",
    "allerg": "allergy", "dietary": "allergy",
    "dialysis": "dialysis",
    "following (": "line_specific_equipment",
    "other medical condition": "other",
}

_REMEDIATION_BY_CONCERN_KEY = {
    "oxygen": "Verify oxygen/CPAP equipment against cruise line pre-approval requirement before embarkation.",
    "mobility": "Confirm mobility aid type + collapsibility with cruise line special-services desk.",
    "dialysis": "Confirm onboard/port dialysis arrangements with cruise line medical center.",
    "allergy": "Flag allergy to dining team and add to guest profile for onboard kitchen.",
    "line_specific_equipment": "Cross-check selected items against cruise line pre-approval list; file special-services request.",
    "other": "Route to cruise line special-services desk for individual review.",
}

_NEGATIVE_ANSWERS = {"no", "n/a", "none", "none of the above", ""}


def flag_concerns(guest_name: str, parsed_answers: list[dict]) -> list[ScreeningConcern]:
    """Keyword-match answers against known concern categories.

    Every concern is tagged INFERRED — this is a keyword match on the guest's
    own words, not a medical determination (Negative-Space Rule).
    """
    concerns = []
    for a in parsed_answers:
        question, answer = a["question"], a["answer"]
        answer_norm = answer.strip().lower()
        if answer_norm in _NEGATIVE_ANSWERS:
            continue
        q_lower = question.lower()
        concern_key = next((v for k, v in _CONCERN_KEY_BY_QUESTION_SUBSTRING.items() if k in q_lower), None)
        if not concern_key:
            continue
        concerns.append(ScreeningConcern(
            guest_name=guest_name,
            concern_key=concern_key,
            question=question,
            answer=answer,
            confidence=CONFIDENCE_INFERRED,
            remediation=_REMEDIATION_BY_CONCERN_KEY.get(concern_key, "Route to cruise line special-services desk."),
        ))
    return concerns


def build_screening_result(form_id: str, form_url: str, raw_responses: list[dict],
                            guest_name_by_response_index: Optional[list[str]] = None) -> ScreeningResult:
    all_concerns: list[ScreeningConcern] = []
    for i, resp in enumerate(raw_responses):
        guest_name = (guest_name_by_response_index[i] if guest_name_by_response_index and i < len(guest_name_by_response_index)
                      else f"Respondent {i + 1}")
        all_concerns.extend(flag_concerns(guest_name, resp["answers"]))

    if not raw_responses:
        summary = "No responses received yet."
    else:
        summary = f"{len(raw_responses)} response(s) received."
        if all_concerns:
            keys = sorted({c.concern_key for c in all_concerns})
            summary += f" Flagged concerns: {', '.join(keys)} ({len(all_concerns)} item(s), INFERRED — verify before client copy)."
        else:
            summary += " No concerns flagged."

    return ScreeningResult(form_id=form_id, form_url=form_url, response_count=len(raw_responses),
                            concerns=all_concerns, responses_summary=summary)


# ── Timing — T-90 scheduling, hooked into the existing deferred_alerts pattern ──

def compute_send_date(embark_date: str, lead_days: int = DEFAULT_LEAD_DAYS) -> date:
    embark = datetime.strptime(embark_date, "%Y-%m-%d").date()
    return embark - timedelta(days=lead_days)


def build_deferred_alert(client_name: str, booking_id: str, embark_date: str,
                          lead_days: int = DEFAULT_LEAD_DAYS) -> dict:
    """Same schema as hale_state.json's existing deferred_alerts entries —
    hooks into the existing scan/surface loop rather than a new scheduler."""
    trigger_date = compute_send_date(embark_date, lead_days)
    return {
        "id": f"MEDICAL-SCREENING-{booking_id}",
        "trigger_date": trigger_date.isoformat(),
        "priority": "P1",
        "message": (
            f"Medical screening (TP 2.5-equivalent, T-{lead_days}) due for {client_name} — "
            f"booking {booking_id}, embark {embark_date}. Generate form via "
            "`python3 -m core.compliance.medical_screening generate`, stage as draft, do not send."
        ),
        "client": client_name,
        "booking": booking_id,
        "condition": f"date>={trigger_date.isoformat()}",
        "condition_type": "date",
        "source": "core/compliance/medical_screening.py build_deferred_alert()",
    }


def append_deferred_alert(alert: dict, hale_state_path: Path = HALE_STATE_PATH) -> None:
    state = json.loads(hale_state_path.read_text())
    existing_ids = {a.get("id") for a in state.get("deferred_alerts", [])}
    if alert["id"] not in existing_ids:
        state.setdefault("deferred_alerts", []).append(alert)
        hale_state_path.write_text(json.dumps(state, indent=2))


# ── Dossier sync ──

def sync_to_dossier(dossier_path: Path, result: ScreeningResult, cruise_line: str) -> None:
    """Write medical_screening_responses into the client's dossier JSON.

    Local write only — no network dispatch of guest medical data.
    """
    data = json.loads(dossier_path.read_text()) if dossier_path.exists() else {}
    data["medical_screening"] = {
        "form_id": result.form_id,
        "form_url": result.form_url,
        "cruise_line": cruise_line,
        "response_count": result.response_count,
        "concerns": [c.to_dict() for c in result.concerns],
        "responses_summary": result.responses_summary,
        "last_synced": datetime.now(timezone.utc).isoformat(),
    }
    dossier_path.write_text(json.dumps(data, indent=2))


# ── Draft-only distribution (WF-17 gate — never send) ──

def stage_screening_email_draft(to: str, form_url: str, client_first_name: str,
                                 cc: str = "johnloucks3@gmail.com") -> dict:
    """Stage a Gmail DRAFT with the form link. Never sends — same WF-17
    discipline as core/lifecycle/lifecycle_scheduler.py's gmail_create_draft_sync.
    """
    from core.email.thunderbird_gmail import gmail_create_draft_sync

    subject = "A Quick Pre-Voyage Health & Mobility Check-In"
    body = (
        f"<p>Dear {client_first_name},</p>"
        "<p>Before your voyage, we ask every guest to complete this brief medical "
        "screening — it helps us flag anything the cruise line needs advance notice "
        "on (oxygen equipment, mobility aids, dietary allergies) so there are no "
        "surprises at embarkation.</p>"
        f'<p><a href="{form_url}">Complete your screening here</a> — it takes about two minutes.</p>'
        "<p>Thank you for helping us keep your journey seamless from the pier onward.</p>"
    )
    return gmail_create_draft_sync(to=to, subject=subject, body=body, cc=cc, label_review=True,
                                    product_type="medical_screening")


# ── CLI ──

def _cmd_generate(args):
    form = create_form(args.cruise_line, args.ship, args.voyage, args.embark_date)
    if args.dossier:
        dossier_path = Path(args.dossier)
        result = build_screening_result(form["form_id"], form["url"], [])
        sync_to_dossier(dossier_path, result, args.cruise_line)
    print(json.dumps({"medical_screening_form_link": form["url"], "form_id": form["form_id"],
                       "edit_url": form["edit_url"], "question_count": len(form["questions"])}, indent=2))


def _cmd_schedule(args):
    alert = build_deferred_alert(args.client_name, args.booking_id, args.embark_date, args.lead_days)
    append_deferred_alert(alert)
    print(json.dumps(alert, indent=2))


def _cmd_sync(args):
    raw = fetch_responses(args.form_id)
    guest_names = args.guest_names.split(",") if args.guest_names else None
    result = build_screening_result(args.form_id, args.form_url or "", raw, guest_names)
    if args.dossier:
        sync_to_dossier(Path(args.dossier), result, args.cruise_line or "")
    print(json.dumps({"responses_summary": result.responses_summary,
                       "response_count": result.response_count,
                       "concerns": [c.to_dict() for c in result.concerns]}, indent=2))


def _cmd_draft(args):
    result = stage_screening_email_draft(args.to, args.form_url, args.first_name, args.cc)
    print(json.dumps(result, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Pre-voyage medical screening automation")
    sub = parser.add_subparsers(dest="command", required=True)

    p_gen = sub.add_parser("generate", help="Create the Google Form")
    p_gen.add_argument("--cruise-line", required=True)
    p_gen.add_argument("--ship", required=True)
    p_gen.add_argument("--voyage", required=True)
    p_gen.add_argument("--embark-date", required=True)
    p_gen.add_argument("--dossier")
    p_gen.set_defaults(func=_cmd_generate)

    p_sched = sub.add_parser("schedule", help="Append T-90 deferred alert")
    p_sched.add_argument("--client-name", required=True)
    p_sched.add_argument("--booking-id", required=True)
    p_sched.add_argument("--embark-date", required=True)
    p_sched.add_argument("--lead-days", type=int, default=DEFAULT_LEAD_DAYS)
    p_sched.set_defaults(func=_cmd_schedule)

    p_sync = sub.add_parser("sync", help="Pull responses, flag concerns, sync dossier")
    p_sync.add_argument("--form-id", required=True)
    p_sync.add_argument("--form-url")
    p_sync.add_argument("--cruise-line")
    p_sync.add_argument("--dossier")
    p_sync.add_argument("--guest-names", help="Comma-separated, in response order")
    p_sync.set_defaults(func=_cmd_sync)

    p_draft = sub.add_parser("draft", help="Stage Gmail draft (never sends)")
    p_draft.add_argument("--to", required=True)
    p_draft.add_argument("--form-url", required=True)
    p_draft.add_argument("--first-name", required=True)
    p_draft.add_argument("--cc", default="johnloucks3@gmail.com")
    p_draft.set_defaults(func=_cmd_draft)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
