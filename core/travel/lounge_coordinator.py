"""
Airport Lounge Access Coordinator
Dreams2Memories Travel, LLC

Matches a client's credit card portfolio against config/credit_card_lounge_benefits.json
to find eligible lounge networks, then matches those networks against
config/airport_lounge_directory.json for the client's actual airports/airlines
to produce a per-leg lounge access plan.

"Pre-authorization" is a request record, not a live booking. None of Priority
Pass / LoungeKey / Lounge Club / Centurion expose a public third-party booking
API — access is verified at the door via card + ID (walk-in networks) or by a
same-day phone/email reservation (reservation-required lounges, e.g. Centurion
Lounge at capacity-limited airports). pre_authorize_entry() therefore stamps an
entry_method + action-needed note per lounge rather than calling out to a real
API. See docstring on entry_method values below.

No client's card portfolio is inferred or assumed — it must come from the
caller (client intake / dossier). Card data is not present in any current
dossier (verified 2026-07-06 — see config/client_credit_cards.json header).
"""

import json
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
CARD_BENEFITS_PATH = CONFIG_DIR / "credit_card_lounge_benefits.json"
LOUNGE_DIRECTORY_PATH = CONFIG_DIR / "airport_lounge_directory.json"
OUTPUT_DIR = Path(__file__).parent / "output"

# Networks where a same-day reservation is typically required due to capacity
# limits, rather than pure walk-in-with-card entry.
RESERVATION_REQUIRED_NETWORKS = {"Centurion Lounge"}


def load_card_benefits(path: Path = CARD_BENEFITS_PATH) -> dict:
    return json.loads(path.read_text())


def load_lounge_directory(path: Path = LOUNGE_DIRECTORY_PATH) -> dict:
    return json.loads(path.read_text())


def eligible_networks(cards: list[str], benefits_cfg: dict) -> dict[str, dict]:
    """
    cards: list of card names as they appear in credit_card_lounge_benefits.json.
    Returns {network_name: {"guests": int, "condition": str, "via_card": str}} —
    one entry per distinct network, keeping the best (max guests) entitlement
    when more than one card in the portfolio grants the same network.
    """
    result: dict[str, dict] = {}
    for card in cards:
        card_cfg = benefits_cfg.get(card)
        if card_cfg is None:
            continue
        for net in card_cfg.get("networks", []):
            name = net["network"]
            existing = result.get(name)
            if existing is None or net["guests"] > existing["guests"]:
                result[name] = {
                    "guests": net["guests"],
                    "condition": net["condition"],
                    "via_card": card,
                }
    return result


def unmatched_cards(cards: list[str], benefits_cfg: dict) -> list[str]:
    """Cards the caller passed in that carry no lounge network (e.g. Amex Gold)."""
    return [c for c in cards if c in benefits_cfg and not benefits_cfg[c].get("networks")]


def unknown_cards(cards: list[str], benefits_cfg: dict) -> list[str]:
    """Cards not present in the benefits database at all — needs research, not silence."""
    return [c for c in cards if c not in benefits_cfg]


def lounges_at_airport(
    airport_code: str,
    networks: dict[str, dict],
    airline: Optional[str] = None,
    directory_cfg: Optional[dict] = None,
) -> list[dict]:
    """
    Returns every lounge at airport_code reachable via any network the client
    holds, each annotated with which network/card unlocked it. Airline is
    accepted for future airline-specific-lounge filtering (e.g. Star Alliance
    reciprocal lounges limited to same-day international Star Alliance travel)
    and is passed through as a note when a lounge's directory entry carries an
    airline-conditional "note" field — it does not filter results, since lounge
    reciprocal rules vary by fare class as well as airline and a false negative
    (hiding a lounge the client can actually use) is worse than surfacing one
    with its condition attached.
    """
    directory_cfg = directory_cfg or load_lounge_directory()
    airport = directory_cfg.get(airport_code)
    if airport is None:
        return []

    matches = []
    for lounge in airport["lounges"]:
        net_name = lounge["network"]
        if net_name in networks:
            entry = dict(lounge)
            entry["airport_code"] = airport_code
            entry["network"] = net_name
            entry["via_card"] = networks[net_name]["via_card"]
            entry["guests_included"] = networks[net_name]["guests"]
            entry["condition"] = networks[net_name]["condition"]
            matches.append(entry)
    return matches


def pre_authorize_entry(lounge: dict, client_name: str) -> dict:
    """
    Stamps an entry_method onto a lounge match. Two outcomes:
      - "WALK_IN_VERIFIED" — present card + boarding pass + photo ID at the
        lounge desk; no advance action needed.
      - "RESERVATION_REQUIRED" — network is capacity-limited (see
        RESERVATION_REQUIRED_NETWORKS); action_needed names the concrete step.
    This does not call an external API — none of these networks expose one
    for third-party reservation. Treat this as the pre-flight checklist item,
    not a completed booking.
    """
    result = dict(lounge)
    if lounge["network"] in RESERVATION_REQUIRED_NETWORKS:
        result["entry_method"] = "RESERVATION_REQUIRED"
        result["action_needed"] = (
            f"Call {lounge['name']} or reserve via the issuer's Centurion "
            f"Lounge app under {client_name}'s name — same-day capacity limits apply."
        )
    else:
        result["entry_method"] = "WALK_IN_VERIFIED"
        result["action_needed"] = None
    return result


def build_lounge_access_plan(
    client_name: str,
    cards: list[str],
    legs: list[dict],
    benefits_cfg: Optional[dict] = None,
    directory_cfg: Optional[dict] = None,
) -> dict:
    """
    legs: [{"airport_code": "DEN", "airline": "United"}, ...] — one per airport
    the client will pass through (embark + disembark + connections).

    Returns:
      {
        "client": str,
        "cards": [...],
        "unknown_cards": [...],   # not in the benefits db — needs research
        "no_lounge_cards": [...], # in the db, but carry zero lounge networks
        "networks": {network: {...}},
        "legs": [
          {"airport_code": ..., "airline": ..., "lounges": [pre-authorized lounge dicts]}
        ],
      }
    """
    benefits_cfg = benefits_cfg or load_card_benefits()
    directory_cfg = directory_cfg or load_lounge_directory()

    networks = eligible_networks(cards, benefits_cfg)
    plan_legs = []
    for leg in legs:
        matches = lounges_at_airport(
            leg["airport_code"], networks, leg.get("airline"), directory_cfg
        )
        authorized = [pre_authorize_entry(m, client_name) for m in matches]
        plan_legs.append(
            {
                "airport_code": leg["airport_code"],
                "airline": leg.get("airline"),
                "lounges": authorized,
            }
        )

    return {
        "client": client_name,
        "cards": cards,
        "unknown_cards": unknown_cards(cards, benefits_cfg),
        "no_lounge_cards": unmatched_cards(cards, benefits_cfg),
        "networks": networks,
        "legs": plan_legs,
    }


def write_lounge_access_json(plan: dict, output_path: Optional[Path] = None) -> Path:
    output_path = output_path or (
        OUTPUT_DIR / f"lounge_access_{plan['client'].replace(' ', '_').replace('&', 'and')}.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(plan, indent=2))
    return output_path


def tp_data_block(plan: dict) -> list[dict]:
    """
    Factual per-airport data for insertion into a pre-voyage touchpoint by the
    creative chain (Reyes/Dani own the client-facing prose — this returns
    structured facts only, per CLAUDE.md Failure A: Hale/JET routes and
    supplies data, it does not author client copy).
    Skips legs with zero lounge matches so the TP doesn't reference an empty set.
    """
    blocks = []
    for leg in plan["legs"]:
        if not leg["lounges"]:
            continue
        blocks.append(
            {
                "airport_code": leg["airport_code"],
                "lounges": [
                    {
                        "name": l["name"],
                        "terminal": l["terminal"],
                        "hours": l["hours"],
                        "amenities": l["amenities"],
                        "entry_method": l["entry_method"],
                        "action_needed": l["action_needed"],
                        "via_card": l["via_card"],
                    }
                    for l in leg["lounges"]
                ],
            }
        )
    return blocks


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("usage: lounge_coordinator.py '<client name>' '<CARD1,CARD2>' 'AIRPORT1:AIRLINE1,AIRPORT2:AIRLINE2'")
        sys.exit(1)

    client_name = sys.argv[1]
    cards = [c.strip() for c in sys.argv[2].split(",")]
    legs = []
    for token in sys.argv[3].split(","):
        code, _, airline = token.partition(":")
        legs.append({"airport_code": code.strip(), "airline": airline.strip() or None})

    result_plan = build_lounge_access_plan(client_name, cards, legs)
    out = write_lounge_access_json(result_plan)
    print(json.dumps(result_plan, indent=2))
    print(f"\nWritten: {out}")
