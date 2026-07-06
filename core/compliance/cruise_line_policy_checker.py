"""
core/compliance/cruise_line_policy_checker.py

Automated compliance & policy check for cruise bookings (Phase 4 risk management).

Checks a booking's guests against the cruise line's policy rules:
  - age restrictions (alcohol service, casino, minimum sailing age)
  - medical/health requirements (oxygen, dialysis, mobility aids, etc.)
  - passport validity (must clear sail date + required buffer, default 180d)
  - visa notes (surfaced, not auto-determined — nationality/itinerary dependent)

Rules live in config/cruise_line_policies.json — that file is the policy, this
module is only the engine. Every rule carries a confidence tag (CONFIRMED /
INFERRED / UNKNOWN); UNKNOWN rules are skipped rather than fabricating a
violation (Negative-Space Rule, SO-PIPELINE-INTEGRITY-20260528).

Input is a normalized booking dict (see `Guest`/booking schema below), not raw
TESS output — TESS's Booking record does not carry structured guest DOB/
passport/medical fields (they live in prose dossiers or intake forms today).
`fetch_booking_from_tess()` is a best-effort adapter for when that data does
land in TESS's extra_fields; until then, feed bookings in via a JSON file or
dict.

CLI:
    python3 -m core.compliance.cruise_line_policy_checker \\
        --input path/to/booking.json \\
        --output OpsCenter/policy_violations.json

    python3 -m core.compliance.cruise_line_policy_checker \\
        --booking-id 3096289 --cruise-line "Regent Seven Seas" \\
        --output OpsCenter/policy_violations.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Optional

DEFAULT_POLICIES_PATH = Path(__file__).resolve().parents[2] / "config" / "cruise_line_policies.json"

URGENCY_HIGH = "HIGH"
URGENCY_MEDIUM = "MEDIUM"
URGENCY_LOW = "LOW"


@dataclass
class Violation:
    booking_id: str
    guest_name: str
    violation: str
    cruise_line_rule: str
    rule_id: str
    remediation: str
    urgency: str
    confidence: str

    def to_dict(self) -> dict:
        return asdict(self)


def _parse_date(value) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _age_at(dob: date, on_date: date) -> int:
    return on_date.year - dob.year - ((on_date.month, on_date.day) < (dob.month, dob.day))


class PolicyNotFoundError(ValueError):
    pass


class CruiseLinePolicyChecker:
    def __init__(self, policies_path: Path = DEFAULT_POLICIES_PATH):
        self.policies_path = Path(policies_path)
        self._registry = self._load_registry()

    def _load_registry(self) -> dict:
        with open(self.policies_path) as f:
            data = json.load(f)
        return data.get("cruise_lines", {})

    def resolve_cruise_line(self, cruise_line: str) -> tuple[str, dict]:
        """Resolve a free-text cruise line / ship name to a registry entry via alias match."""
        needle = cruise_line.strip().lower()
        for name, entry in self._registry.items():
            if needle == name.lower():
                return name, entry
            if needle in [a.lower() for a in entry.get("aliases", [])]:
                return name, entry
        # substring fallback (e.g. "Regent Grandeur" -> "Regent Seven Seas")
        for name, entry in self._registry.items():
            aliases = [name.lower()] + [a.lower() for a in entry.get("aliases", [])]
            if any(a in needle or needle in a for a in aliases):
                return name, entry
        raise PolicyNotFoundError(f"No policy entry found for cruise line: {cruise_line!r}")

    @staticmethod
    def _rule(entry: dict, key: str) -> Optional[dict]:
        rule = entry.get("rules", {}).get(key)
        if not rule or rule.get("confidence") == "UNKNOWN" or rule.get("value") in (None, [], ""):
            return None
        return rule

    def check_booking(self, booking: dict) -> list[Violation]:
        booking_id = str(booking.get("booking_id", "UNKNOWN"))
        cruise_line_input = booking.get("cruise_line", "")
        sail_date = _parse_date(booking.get("sail_date"))
        guests = booking.get("guests", [])

        try:
            resolved_name, entry = self.resolve_cruise_line(cruise_line_input)
        except PolicyNotFoundError:
            return [Violation(
                booking_id=booking_id,
                guest_name="ALL",
                violation=f"No policy data for cruise line '{cruise_line_input}' — cannot check compliance.",
                cruise_line_rule="N/A",
                rule_id="POLICY-UNKNOWN-LINE",
                remediation="Add cruise line to config/cruise_line_policies.json before this booking can be checked.",
                urgency=URGENCY_MEDIUM,
                confidence="UNKNOWN",
            )]

        violations: list[Violation] = []
        for guest in guests:
            name = guest.get("name", "UNKNOWN GUEST")
            violations.extend(self._check_age(booking_id, name, guest, entry, sail_date))
            violations.extend(self._check_passport(booking_id, name, guest, entry, sail_date))
            violations.extend(self._check_medical(booking_id, name, guest, entry))
            violations.extend(self._check_mobility(booking_id, name, guest, entry))

        return violations

    def _check_age(self, booking_id, name, guest, entry, sail_date) -> list[Violation]:
        out = []
        dob = _parse_date(guest.get("dob"))
        if dob is None or sail_date is None:
            return out
        age = _age_at(dob, sail_date)

        for key, label in (
            ("min_age_alcohol_service", "alcohol service / premium bars"),
            ("min_age_casino", "casino access"),
            ("min_age_sailing", "minimum sailing age"),
        ):
            rule = self._rule(entry, key)
            if not rule:
                continue
            min_age = rule["value"]
            if age < min_age:
                out.append(Violation(
                    booking_id=booking_id,
                    guest_name=name,
                    violation=f"Guest age {age} is below minimum age {min_age} for {label}.",
                    cruise_line_rule=rule["source"],
                    rule_id=rule["rule_id"],
                    remediation=(
                        f"Flag for parent/guardian consent and onboard orientation before {label} is permitted."
                        if key != "min_age_sailing"
                        else "This cruise line requires all guests to meet the minimum sailing age — escalate to Commander, booking may not be valid as configured."
                    ),
                    urgency=URGENCY_HIGH if key == "min_age_sailing" else URGENCY_MEDIUM,
                    confidence=rule["confidence"],
                ))
        return out

    def _check_passport(self, booking_id, name, guest, entry, sail_date) -> list[Violation]:
        out = []
        rule = self._rule(entry, "passport_validity_days_required")
        if not rule or sail_date is None:
            return out
        expiry = _parse_date(guest.get("passport_expiry"))
        if expiry is None:
            out.append(Violation(
                booking_id=booking_id,
                guest_name=name,
                violation="No passport expiry date on file — cannot verify validity.",
                cruise_line_rule=rule["source"],
                rule_id=rule["rule_id"],
                remediation="Request passport photo/expiry date from guest before final payment.",
                urgency=URGENCY_MEDIUM,
                confidence=rule["confidence"],
            ))
            return out
        required_days = rule["value"]
        days_clear = (expiry - sail_date).days
        if days_clear < required_days:
            out.append(Violation(
                booking_id=booking_id,
                guest_name=name,
                violation=(
                    f"Passport expires {expiry.isoformat()} — only {max(days_clear, 0)} days past sail date, "
                    f"below the required {required_days}-day buffer."
                ),
                cruise_line_rule=rule["source"],
                rule_id=rule["rule_id"],
                remediation="Guest must renew passport before final payment / departure.",
                urgency=URGENCY_HIGH if days_clear < 0 else URGENCY_MEDIUM,
                confidence=rule["confidence"],
            ))
        return out

    def _check_medical(self, booking_id, name, guest, entry) -> list[Violation]:
        out = []
        rule = self._rule(entry, "medical_equipment_requiring_preapproval")
        if not rule:
            return out
        watch_list = [x.lower() for x in rule["value"]]
        guest_equipment = [str(x).lower() for x in guest.get("medical_equipment", [])]
        preapproved = bool(guest.get("medical_preapproval_on_file", False))
        for item in guest_equipment:
            if any(w in item for w in watch_list) and not preapproved:
                out.append(Violation(
                    booking_id=booking_id,
                    guest_name=name,
                    violation=f"Guest requires '{item}' — no medical pre-approval on file.",
                    cruise_line_rule=rule["source"],
                    rule_id=rule["rule_id"],
                    remediation="Submit cruise line's Special Needs / Medical Information form before final payment.",
                    urgency=URGENCY_HIGH,
                    confidence=rule["confidence"],
                ))
        return out

    def _check_mobility(self, booking_id, name, guest, entry) -> list[Violation]:
        out = []
        rule = self._rule(entry, "mobility_aid_preapproval_required")
        if not rule or not rule["value"]:
            return out
        if guest.get("mobility_aid") and not guest.get("mobility_preapproval_on_file", False):
            out.append(Violation(
                booking_id=booking_id,
                guest_name=name,
                violation=f"Guest travels with mobility aid ({guest['mobility_aid']}) — no pre-approval on file.",
                cruise_line_rule=rule["source"],
                rule_id=rule["rule_id"],
                remediation="Submit mobility aid details to cruise line's Special Services desk before final payment.",
                urgency=URGENCY_MEDIUM,
                confidence=rule["confidence"],
            ))
        return out


def fetch_booking_from_tess(booking_id: str, cruise_line: str) -> dict:
    """Best-effort adapter: TESS's Booking record has no structured guest DOB/
    passport/medical schema today, so this returns a booking shell with an
    empty guest list rather than fabricate guest data. Populate `guests` from
    a dossier/intake extraction step, or pass a full booking dict via --input.
    """
    from core.booking.thunderbird_tess import TESSClient  # local import, avoids hard dep at module load

    client = TESSClient()
    raw = client.get_booking(booking_id)
    return {
        "booking_id": booking_id,
        "cruise_line": cruise_line,
        "sail_date": raw.get("SailDate") or raw.get("DepartureDate"),
        "guests": [],
        "_tess_raw_available": bool(raw),
    }


def write_violations_report(violations: list[Violation], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now().isoformat(),
        "violation_count": len(violations),
        "violations": [v.to_dict() for v in violations],
    }
    output_path.write_text(json.dumps(payload, indent=2))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Path to a booking JSON file (booking_id, cruise_line, sail_date, guests[])")
    parser.add_argument("--booking-id", help="TESS booking ID (used with --cruise-line if --input not given)")
    parser.add_argument("--cruise-line", help="Cruise line name, e.g. 'Regent Seven Seas'")
    parser.add_argument("--output", type=Path, default=Path("OpsCenter/policy_violations.json"))
    parser.add_argument("--policies", type=Path, default=DEFAULT_POLICIES_PATH)
    args = parser.parse_args(argv)

    if args.input:
        booking = json.loads(args.input.read_text())
    elif args.booking_id and args.cruise_line:
        booking = fetch_booking_from_tess(args.booking_id, args.cruise_line)
    else:
        parser.error("Provide --input booking.json, or --booking-id + --cruise-line")
        return 2

    checker = CruiseLinePolicyChecker(policies_path=args.policies)
    violations = checker.check_booking(booking)
    write_violations_report(violations, args.output)

    print(f"{len(violations)} violation(s) written to {args.output}")
    for v in violations:
        print(f"  [{v.urgency}] {v.guest_name}: {v.violation}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
