#!/usr/bin/env python3
"""
test_crew_roster.py — live validation against 5 real client voyages.

Covers every ship currently on the D2M client wire that maps to one of the three named
cruise lines (Regent, Silversea, Viking):
  1. Seven Seas Grandeur  — Furlow / Ely-Darrow / Nichols (Aug 2026, 3 bookings)
  2. Seven Seas Grandeur  — McLeod/McGlasson (Dec 2026) — same ship, second voyage
  3. Silver Nova          — Loucks (May 2027)
  4. Silver Muse          — McLeod/McGlasson (Jun 2026) — negative case: only source found
     is a narrative-prose 2017 article; asserts the module correctly refuses to fabricate
     structured data from it rather than mis-parsing bios
  5. Viking Mars          — Kuklinski Group (Dec 2026) — no public source exists at all;
     asserts the manual-entry path (the only viable path Viking has today)

Run: .venv/bin/python3 core/voyage/test_crew_roster.py
Requires network + node (uses the real tools/cloak/cloak_fetch.mjs CloakBrowser tool for
voyages 1-4; voyage 5 and the gating tests are offline).
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.voyage.crew_roster import (  # noqa: E402
    CrewMember,
    add_manual_entry,
    get_tp_snippet,
    ingest_press_release,
    load_crew_roster,
    refresh_ship,
    render_crew_portal_html,
    save_crew_roster,
)

PASS = 0
FAIL = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {label}")
    else:
        FAIL += 1
        print(f"  FAIL  {label}  {detail}")


def voyage_1_2_regent_grandeur() -> None:
    print("\n[1+2] Regent Seven Seas Grandeur — Furlow/Ely-Darrow/Nichols + McLeod voyages")
    roster = refresh_ship("seven_seas_grandeur", "Regent Seven Seas", "Seven Seas Grandeur",
                           ship_slug="seven_seas_grandeur", force=True)
    check("live fetch returns 5 officers", len(roster.members) == 5, f"got {len(roster.members)}")
    captain = roster.member_by_role("Captain")
    check("Captain is Luciano Montesanto (matches independent WebSearch cross-check)",
          captain is not None and captain.name == "Luciano Montesanto")
    check("Captain has a photo_url", bool(captain and captain.photo_url))
    check("Captain photo_url is a real rssc.com asset path",
          bool(captain and captain.photo_url and captain.photo_url.startswith("https://www.rssc.com/sites/default/files/")))
    cd = roster.member_by_role("Cruise Director")
    check("Cruise Director is David Nevin (matches independent WebSearch cross-check)",
          cd is not None and cd.name == "David Nevin")
    check("roster flags itself as a launch/inaugural roster, not live", "inaugural" in roster.note.lower())
    check("2nd 'voyage' (McLeod, same ship) reads from the same authoritative cache",
          load_crew_roster("seven_seas_grandeur").fetched_at == roster.fetched_at)


def voyage_3_silversea_silver_nova() -> None:
    print("\n[3] Silversea Silver Nova — Loucks voyage (May 2027)")
    url = ("https://www.silversea.com/about-silversea/press-releases/2023/august/"
           "silversea-reveals-line-up-senior-officers-silver-nova-maiden-voyage.html")
    roster = refresh_ship("silver_nova", "Silversea", "Silver Nova", press_release_url=url, force=True)
    check("live press-release ingest returns 3 officers", len(roster.members) == 3, f"got {len(roster.members)}")
    # Note: Silversea's press-release format titles the top job "Master", not "Captain"
    # (Regent's officer page uses "Captain") — a real line-to-line naming difference.
    captain = roster.member_by_role("Master")
    check("Captain/Master bio contains Pontillo (matches independent WebSearch cross-check)",
          captain is not None and "Pontillo" in captain.name)
    cd = roster.member_by_role("Cruise Director")
    check("Cruise Director is Vicki Van Tassel", cd is not None and cd.name == "Vicki Van Tassel")
    check("roster_type is press_release (not claimed as a per-ship page)", roster.roster_type == "press_release")


def voyage_4_silver_muse_negative_case() -> None:
    print("\n[4] Silversea Silver Muse — McLeod voyage: negative case (no structured source)")
    try:
        ingest_press_release(
            "silver_muse", "Silversea", "Silver Muse",
            "https://cruiseindustrynews.com/cruise-news/16508-silversea-names-silver-muse-senior-officers.html",
        )
        check("narrative-prose source correctly refused (should have raised)", False)
    except RuntimeError as e:
        check("narrative-prose source correctly refused rather than mis-parsed", "NAME" in str(e) or "parsed" in str(e))
    check("no bad cache was written for silver_muse", load_crew_roster("silver_muse") is None)


def voyage_5_viking_mars_manual() -> None:
    print("\n[5] Viking Mars — Kuklinski Group voyage: manual-entry path (no public source exists)")
    roster = add_manual_entry(
        "viking_mars", "Viking Ocean", "Viking Mars",
        [CrewMember(name="Atle Knutsen", title="Captain", bio="First Master of Viking Mars.")],
        source_note="Manually keyed; no public per-ship officer page or press release found for "
                     "Viking as of 2026-07-06 (WebSearch checked).",
    )
    check("manual roster saved with roster_type=manual", roster.roster_type == "manual")
    check("source_note is present and non-empty (mandatory for manual entries)", len(roster.note) > 20)
    portal_html = render_crew_portal_html("viking_mars")
    check("portal render includes the caveat sentence even for manual entries",
          "may not reflect" in portal_html)


def gating_tests() -> None:
    print("\n[gate] Negative-Space Rule enforcement on get_tp_snippet()")
    check("default (confirm_current=False) withholds name even with fresh confirmed data",
          get_tp_snippet("seven_seas_grandeur", "Cruise Director") is None)
    snippet = get_tp_snippet("seven_seas_grandeur", "Cruise Director", confirm_current=True)
    check("confirm_current=True + fresh cache returns a usable snippet",
          snippet is not None and "Nevin" in snippet, detail=str(snippet))

    roster = load_crew_roster("seven_seas_grandeur")
    roster.fetched_at = (datetime.now(timezone.utc) - timedelta(days=99)).isoformat()
    save_crew_roster(roster)
    check("stale cache withholds name even with confirm_current=True",
          get_tp_snippet("seven_seas_grandeur", "Cruise Director", confirm_current=True) is None)
    # restore
    refresh_ship("seven_seas_grandeur", "Regent Seven Seas", "Seven Seas Grandeur",
                 ship_slug="seven_seas_grandeur", force=True)

    portal = render_crew_portal_html("seven_seas_grandeur")
    check("portal render always includes the rotation caveat (no confirm_current gate)",
          "Crew rotate on multi-month contracts" in portal)
    check("portal render returns empty string for a ship with no cache",
          render_crew_portal_html("no_such_ship_id") == "")


def main() -> int:
    voyage_1_2_regent_grandeur()
    voyage_3_silversea_silver_nova()
    voyage_4_silver_muse_negative_case()
    voyage_5_viking_mars_manual()
    gating_tests()
    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
