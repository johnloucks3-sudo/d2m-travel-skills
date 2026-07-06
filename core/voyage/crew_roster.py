#!/usr/bin/env python3
"""
crew_roster.py — ship's officer / crew bio fetch, cache, and TP/portal integration.
Dreams2Memories Travel, LLC · Thunderbird Wing · Phase 4 experience enhancement

GROUND TRUTH (verified live 2026-07-06, not assumed):
  - Regent Seven Seas publishes a real per-ship page: rssc.com/ships/{slug}/officers.
    It sits behind the same Akamai wall as the rest of rssc.com (plain HTTP gets 403);
    CloakBrowser (already in tools/cloak/) clears it. Confirmed live against
    seven_seas_grandeur — 5 officers, names/titles/bios/photos all present.
  - Silversea does not publish a stable per-ship page at all. It only ever announces
    crew as a one-off, dated press release — almost always for a ship's MAIDEN VOYAGE.
    Confirmed live: the Silver Nova release (Aug 2023) and the Silver Muse release
    (cruiseindustrynews.com, March 2017 — nine years stale as of this writing).
  - Viking has no discoverable public per-ship crew source at all (checked 2026-07-06).
    There is no fetcher for it below — only the manual-entry path.
  - In every case the source is a LAUNCH roster, not a live per-sailing feed. Officers
    rotate on multi-month contracts. A name pulled from any of these sources is NOT
    evidence of who is aboard a specific future sailing.

This is why get_tp_snippet() defaults to returning None. Per CLAUDE.md Rule 1
(Negative-Space Rule): "If a fact is not confirmed in a primary source, it does not
appear in a client email... Silence is correct when status is unknown." A ship's
launch-roster page is not a primary source for a specific voyage's current crew, so
by default nothing from this module reaches client copy. A caller may override with
confirm_current=True, but only after independently reverifying for that exact sailing
(reservations desk, the client's own onboard documents, or a dated release for that
specific voyage) — that verification happens outside this module, never inside it.

Public API:
    fetch_regent_crew(ship_id, ship_slug, ship_name) -> CrewRoster
    ingest_press_release(ship_id, cruise_line, ship_name, url) -> CrewRoster
    add_manual_entry(ship_id, cruise_line, ship_name, members, source_note) -> CrewRoster
    refresh_ship(ship_id, cruise_line, ship_name, ...) -> CrewRoster
    load_crew_roster(ship_id) -> CrewRoster | None
    get_tp_snippet(ship_id, role, confirm_current=False) -> str | None
    render_crew_portal_html(ship_id) -> str        # portal use — always caveated, never asserts currency

CLI:
    python3 core/voyage/crew_roster.py refresh-regent seven_seas_grandeur seven_seas_grandeur "Seven Seas Grandeur"
    python3 core/voyage/crew_roster.py refresh-press silver_nova Silversea "Silver Nova" <press_release_url>
    python3 core/voyage/crew_roster.py show seven_seas_grandeur
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "crew_roster"
CLOAK_FETCH = ROOT / "tools" / "cloak" / "cloak_fetch.mjs"

# Default re-fetch cadence (team-lead spec: "on voyage date change or monthly refresh").
REFRESH_MAX_AGE_DAYS = 30
# get_tp_snippet default freshness gate — independent of, and stricter than, REFRESH_MAX_AGE_DAYS.
SNIPPET_MAX_AGE_DAYS = 14


# --------------------------------------------------------------------------- data model

@dataclass
class CrewMember:
    name: str
    title: str
    bio: str = ""
    photo_url: Optional[str] = None
    years_at_line: Optional[int] = None
    specialties: list[str] = field(default_factory=list)


@dataclass
class CrewRoster:
    ship_id: str
    cruise_line: str
    ship_name: str
    source_url: str
    fetched_at: str  # ISO 8601 UTC
    roster_type: str  # "line_published_officer_page" | "press_release" | "manual"
    note: str = ""
    members: list[CrewMember] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "CrewRoster":
        members = [CrewMember(**m) for m in d.get("members", [])]
        return cls(**{**d, "members": members})

    def age_days(self) -> float:
        fetched = datetime.fromisoformat(self.fetched_at)
        return (datetime.now(timezone.utc) - fetched).total_seconds() / 86400

    def member_by_role(self, role: str) -> Optional[CrewMember]:
        role_l = role.lower()
        return next((m for m in self.members if role_l in m.title.lower()), None)


# --------------------------------------------------------------------------- storage

def _storage_path(ship_id: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / f"crew_roster_{ship_id}.json"


def load_crew_roster(ship_id: str) -> Optional[CrewRoster]:
    p = _storage_path(ship_id)
    if not p.exists():
        return None
    return CrewRoster.from_dict(json.loads(p.read_text()))


def save_crew_roster(roster: CrewRoster) -> Path:
    p = _storage_path(roster.ship_id)
    p.write_text(json.dumps(roster.to_dict(), indent=2))
    return p


# --------------------------------------------------------------------------- fetch transport

def _cloak_fetch(url: str, output: str = "html", timeout_ms: int = 30000) -> str:
    """
    Shell out to the existing CloakBrowser stealth-fetch tool (defeats Akamai/Imperva/etc.).
    Writes stdout to a temp file rather than capturing via pipe — officer pages run
    well past typical pipe-buffer sizes, and reading back from disk avoids any pipe-capture
    truncation risk entirely (observed capture_output=True truncating a 373KB page to 64KB
    in this repo's sandboxed exec environment; file I/O has no such ceiling).
    """
    if not CLOAK_FETCH.exists():
        raise RuntimeError(f"cloak_fetch.mjs not found at {CLOAK_FETCH}")
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w+b", suffix=".out", delete=False) as tf:
        out_path = Path(tf.name)
    try:
        with open(out_path, "wb") as out_f:
            proc = subprocess.run(
                ["node", str(CLOAK_FETCH), url, "--output", output, "--timeout", str(timeout_ms)],
                cwd=str(CLOAK_FETCH.parent),
                stdout=out_f,
                stderr=subprocess.PIPE,
                timeout=(timeout_ms / 1000) + 30,
            )
        content = out_path.read_text(errors="ignore")
        if proc.returncode != 0:
            stderr = proc.stderr.decode(errors="ignore") if proc.stderr else ""
            raise RuntimeError(f"cloak_fetch failed for {url}: {stderr.strip()[-500:]}")
        return content
    finally:
        out_path.unlink(missing_ok=True)


_YEARS_RE = re.compile(r"(\d{1,2})[\s-]*year", re.I)


def _extract_years(bio: str) -> Optional[int]:
    m = _YEARS_RE.search(bio)
    return int(m.group(1)) if m else None


# --------------------------------------------------------------------------- Regent

def parse_regent_officers_html(html: str, base_url: str = "https://www.rssc.com") -> list[CrewMember]:
    """
    Parse an rssc.com /ships/{slug}/officers page.
    Structure (verified live 2026-07-06): each officer is a `div.c20` card with
    `h3.headline.-section` holding "NAME<br><div class=paragraph -large><strong>Title</strong>",
    and the bio lives in a same-order `div.c14_body_content_scroll` modal. Photos are plain
    <img alt="Full Name"> tags anywhere on the page.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("div", class_="c20")
    bios = soup.find_all("div", class_="c14_body_content_scroll")
    imgs = soup.find_all("img")

    def photo_for(name: str) -> Optional[str]:
        for im in imgs:
            alt = (im.get("alt") or "").strip()
            if alt and alt.lower() == name.lower():
                src = im.get("src") or im.get("data-src")
                return urljoin(base_url, src) if src else None
        return None

    members: list[CrewMember] = []
    for i, card in enumerate(cards):
        h3 = card.find("h3")
        if not h3:
            continue
        title_tag = h3.find("strong")
        title = title_tag.get_text(strip=True) if title_tag else ""
        name = h3.get_text(" ", strip=True)
        if title:
            name = name.replace(title, "").strip(" -–")
        if not name:
            continue
        bio = bios[i].get_text(" ", strip=True) if i < len(bios) else ""
        members.append(CrewMember(
            name=name,
            title=title,
            bio=bio,
            photo_url=photo_for(name),
            years_at_line=_extract_years(bio),
        ))
    return members


def fetch_regent_crew(ship_id: str, ship_slug: str, ship_name: str) -> CrewRoster:
    """Fetch + parse Regent's public per-ship officer page. Real, live, working — no fallback data."""
    url = f"https://www.rssc.com/ships/{ship_slug}/officers"
    html = _cloak_fetch(url, output="html")
    members = parse_regent_officers_html(html)
    if not members:
        raise RuntimeError(f"No officer cards parsed from {url} — page structure may have changed")
    page_text_lower = html.lower()
    launch_flag = "inaugural" in page_text_lower or "maiden voyage" in page_text_lower
    roster = CrewRoster(
        ship_id=ship_id,
        cruise_line="Regent Seven Seas",
        ship_name=ship_name,
        source_url=url,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        roster_type="line_published_officer_page",
        note=(
            ("Page explicitly labels this the ship's inaugural/maiden-voyage officer team. " if launch_flag else "")
            + "Regent does not refresh this page per sailing; crew rotate on multi-month contracts. "
            "Do not present any name here as 'currently aboard' without independently reverifying "
            "for the specific voyage."
        ),
        members=members,
    )
    return roster


# --------------------------------------------------------------------------- press-release ingest (Silversea/Viking)

# Matches the "NAME – Title" block style used in Silversea's own press-center releases
# (verified live against the Silver Nova maiden-voyage release, Aug 2023). Narrative-prose
# news reprints (e.g. cruiseindustrynews.com's 2017 Silver Muse piece) do NOT match this
# pattern and will correctly yield zero members rather than a bad parse — that's the
# intended failure mode; there is no general-purpose bio-extraction-from-prose here.
_PR_BLOCK_RE = re.compile(r"^([A-Z][A-Z .'\-]{3,40})\s*[–\-]\s*([A-Za-z /&]{3,40})$", re.M)


def parse_press_release_text(text: str) -> list[CrewMember]:
    members: list[CrewMember] = []
    matches = list(_PR_BLOCK_RE.finditer(text))
    for i, m in enumerate(matches):
        name = m.group(1).strip().title()
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        bio = text[start:end].strip().split("\n\n")[0].strip()
        members.append(CrewMember(name=name, title=title, bio=bio, years_at_line=_extract_years(bio)))
    return members


def ingest_press_release(ship_id: str, cruise_line: str, ship_name: str, url: str) -> CrewRoster:
    """
    Fetch + parse a cruise-line press release naming a ship's senior officers. This is the
    only public path for Silversea (no per-ship officer page exists). It is ALWAYS a launch
    or maiden-voyage announcement, never a live per-sailing feed — same caveat as Regent's
    officer page, just a weaker source (often years stale by the time a client sails).
    """
    text = _cloak_fetch(url, output="text")
    members = parse_press_release_text(text)
    if not members:
        raise RuntimeError(
            f"No 'NAME – Title' blocks parsed from {url} — this parser only handles the "
            "structured press-center format, not narrative-prose news reprints. Use "
            "add_manual_entry() to key in data from a prose source by hand."
        )
    roster = CrewRoster(
        ship_id=ship_id,
        cruise_line=cruise_line,
        ship_name=ship_name,
        source_url=url,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        roster_type="press_release",
        note=(
            "Parsed from a dated press release — typically a maiden/inaugural-voyage "
            "announcement, not a live per-sailing feed. Crew rotate on multi-month contracts; "
            "this release may already be years old. Do not present as 'currently aboard' "
            "without independently reverifying for the specific voyage."
        ),
        members=members,
    )
    return roster


def add_manual_entry(ship_id: str, cruise_line: str, ship_name: str,
                      members: list[CrewMember], source_note: str) -> CrewRoster:
    """
    Manual-entry path for lines with no scrapable public source at all (Viking, as of
    2026-07-06 — checked, nothing found) or for reverifying a specific sailing by hand
    (e.g. from a client's own onboard Daily Program). `source_note` must name where the
    data came from and when — this is stored verbatim, never inferred.
    """
    roster = CrewRoster(
        ship_id=ship_id,
        cruise_line=cruise_line,
        ship_name=ship_name,
        source_url="",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        roster_type="manual",
        note=source_note,
        members=members,
    )
    save_crew_roster(roster)
    return roster


# --------------------------------------------------------------------------- orchestration

def refresh_ship(ship_id: str, cruise_line: str, ship_name: str, *,
                  ship_slug: Optional[str] = None,
                  press_release_url: Optional[str] = None,
                  max_age_days: int = REFRESH_MAX_AGE_DAYS,
                  force: bool = False) -> CrewRoster:
    """
    Fetch-if-stale orchestrator. Call on voyage date change or as a monthly cron
    (team-lead spec). Regent uses ship_slug (automated, live); Silversea/Viking need an
    explicit press_release_url per call since there's no stable per-ship URL to derive.
    """
    existing = load_crew_roster(ship_id)
    if existing and not force and existing.age_days() < max_age_days:
        return existing

    if cruise_line.lower().startswith("regent"):
        if not ship_slug:
            raise ValueError("ship_slug required for Regent fetch")
        roster = fetch_regent_crew(ship_id, ship_slug, ship_name)
    elif press_release_url:
        roster = ingest_press_release(ship_id, cruise_line, ship_name, press_release_url)
    else:
        raise ValueError(
            f"No automated fetch path for {cruise_line} ship '{ship_id}' — Silversea/Viking "
            "have no stable per-ship officer page; pass press_release_url, or use "
            "add_manual_entry() for lines with no public source (Viking)."
        )

    save_crew_roster(roster)
    return roster


# --------------------------------------------------------------------------- TP / portal integration

def get_tp_snippet(ship_id: str, role: str, *,
                    max_fetch_age_days: int = SNIPPET_MAX_AGE_DAYS,
                    confirm_current: bool = False) -> Optional[str]:
    """
    TP-email integration point (e.g. TP 2.x Dining: "Your executive chef is...").

    Returns None unless the caller passes confirm_current=True AND the cached roster is
    fresher than max_fetch_age_days. confirm_current is not a formality — it asserts the
    caller has independently reverified this officer is aboard the specific sailing being
    written about. Neither condition alone is sufficient: a fresh fetch of a stale launch
    roster is still not evidence of who's aboard today. Default behavior is silence, per
    the Negative-Space Rule — the TP simply omits the crew line.
    """
    if not confirm_current:
        return None
    roster = load_crew_roster(ship_id)
    if not roster or roster.age_days() > max_fetch_age_days:
        return None
    member = roster.member_by_role(role)
    if not member:
        return None
    highlight = f"{member.name} ({member.title})"
    if member.years_at_line:
        highlight += f", {member.years_at_line} years with {roster.cruise_line}"
    return highlight


def render_tp_crew_block_html(ship_id: str, role: str = "Executive Chef", *,
                               max_fetch_age_days: int = SNIPPET_MAX_AGE_DAYS,
                               confirm_current: bool = False) -> str:
    """
    TP-template integration point — produces the {{CREW_HIGHLIGHT_BLOCK}} HTML fragment used
    by storage/tp_templates/tp_2_3_dining_reservations.html. Thin HTML wrapper around
    get_tp_snippet(); same gate, same default of "" (renders nothing) unless the caller
    supplies confirm_current=True against a fresh cache. See get_tp_snippet() docstring.
    """
    snippet = get_tp_snippet(ship_id, role, max_fetch_age_days=max_fetch_age_days,
                              confirm_current=confirm_current)
    if not snippet:
        return ""
    return (
        '<h2 style="color:#c8dcff;font-family:Georgia,serif;font-size:16px;letter-spacing:1.5px;'
        'text-transform:uppercase;margin:0 0 18px 0;border-bottom:1px solid rgba(180,200,255,0.3);'
        f'padding-bottom:8px">{escape(role.upper())}</h2>\n'
        '<p style="margin:0 0 24px 0;color:#d0e4ff;font-family:Georgia,serif;font-size:15px;'
        f'line-height:1.85">Your {escape(role.lower())} is {escape(snippet)}.</p>'
    )


def render_crew_portal_html(ship_id: str) -> str:
    """
    Client-portal integration point — a "Ship's Leadership" reference section. Unlike
    get_tp_snippet(), this always renders (no confirm_current gate) because the portal is
    framed as reference material, not a claim about a specific sailing — but every render
    carries the same-visible caveat inline, never silently. Returns "" if no roster cached.
    """
    roster = load_crew_roster(ship_id)
    if not roster or not roster.members:
        return ""
    rows = []
    for m in roster.members:
        photo = (
            f'<img src="{escape(m.photo_url)}" alt="{escape(m.name)}" '
            f'style="width:72px;height:72px;border-radius:50%;object-fit:cover;float:left;margin-right:12px">'
            if m.photo_url else ""
        )
        rows.append(
            f'<div style="margin-bottom:16px;overflow:hidden">{photo}'
            f'<strong>{escape(m.name)}</strong> — {escape(m.title)}<br>'
            f'<span style="font-size:13px;color:#666">{escape(m.bio[:220])}{"…" if len(m.bio) > 220 else ""}</span></div>'
        )
    caveat = (
        f'<p style="font-size:12px;color:#888;font-style:italic">Officer team as announced by '
        f'{escape(roster.cruise_line)} ({escape(roster.roster_type.replace("_", " "))}, fetched '
        f'{roster.fetched_at[:10]}). Crew rotate on multi-month contracts — this may not reflect '
        f'who is aboard your specific sailing.</p>'
    )
    return f'<div class="crew-roster-section"><h3>{escape(roster.ship_name)} — Ship\'s Leadership</h3>' + "".join(rows) + caveat + "</div>"


# --------------------------------------------------------------------------- CLI

def _cli() -> None:
    ap = argparse.ArgumentParser(description="Crew roster fetch/cache/inspect")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("refresh-regent", help="Live-fetch a Regent ship's officer page")
    p1.add_argument("ship_id")
    p1.add_argument("ship_slug")
    p1.add_argument("ship_name")
    p1.add_argument("--force", action="store_true")

    p2 = sub.add_parser("refresh-press", help="Ingest a Silversea/Viking press release")
    p2.add_argument("ship_id")
    p2.add_argument("cruise_line")
    p2.add_argument("ship_name")
    p2.add_argument("url")
    p2.add_argument("--force", action="store_true")

    p3 = sub.add_parser("show", help="Print the cached roster for a ship_id")
    p3.add_argument("ship_id")

    args = ap.parse_args()

    if args.cmd == "refresh-regent":
        roster = refresh_ship(args.ship_id, "Regent Seven Seas", args.ship_name,
                               ship_slug=args.ship_slug, force=args.force)
    elif args.cmd == "refresh-press":
        roster = refresh_ship(args.ship_id, args.cruise_line, args.ship_name,
                               press_release_url=args.url, force=args.force)
    else:
        roster = load_crew_roster(args.ship_id)
        if not roster:
            print(f"No cached roster for '{args.ship_id}'")
            return

    print(json.dumps(roster.to_dict(), indent=2))


if __name__ == "__main__":
    _cli()
