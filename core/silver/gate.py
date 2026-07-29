"""
core/silver/gate.py — CMSgt Steve "Silver" Sterling: FRONT frame + BACK gate.

Mandatory on every project/work product (Commander directive 2026-07-16).
Silver stands at both ends of a task:
  FRONT — silver_front_frame(): validates that "done" is concretely framed
          BEFORE work starts (checkable criteria, named ground-truth source).
  BACK  — run_gate(): deterministic check battery on the actual work product
          BEFORE certification. Silver never guesses a pass.

Every frame and verdict is appended to OpsCenter/silver_ledger.jsonl and echoed
as a CHIEF SILVER line in hale_decisions.md — the visibility record the
Commander asked for. Enforcement lives in core/relay/delegation_wiring.py
(no frame → no ticket; no passing verdict → no certification).

Supersedes scripts/silver_gate.py (now a thin CLI shim onto this module).
"""
from __future__ import annotations

import base64
import collections
import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, date
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
LEDGER = ROOT / "OpsCenter/silver_ledger.jsonl"
DECISIONS = ROOT / "hale_decisions.md"

PASS, HOLD, OVERRIDE = "PASS", "HOLD", "OVERRIDE"

WORD = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}

# A criterion is "checkable" if it names something a machine or second seat can
# verify: a number, a path/file, a commit/url/sheet ref, or a count word.
_CHECKABLE = re.compile(
    r"\d|/|\.md|\.json|\.html|\.py|commit|http|sheet|row|"
    r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\b", re.I)

# A verification artifact must be a concrete reference, not a claim.
_CONCRETE_ARTIFACT = re.compile(r"/|@|\bhttps?://|\.[a-z]{2,4}\b|#\d|\brow\b", re.I)

_PLACEHOLDERS = ("📷", "TODO", "TBD", "FIXME", "lorem ipsum", "PLACEHOLDER", "XXX-")


def is_checkable(text: str) -> bool:
    """Public wrapper on the FRONT gate's checkability test (Commander
    directive 2026-07-29 — Wing tasking-clarity templates reuse Silver's own
    checkability bar instead of a second, parallel heuristic). True if
    `text` names something a machine or second seat can verify: a number, a
    path/file, a commit/url/sheet ref, or a count word."""
    return bool(_CHECKABLE.search(text or ""))


@dataclass
class Verdict:
    stage: str                      # "front" | "back"
    mission_id: str
    work_product: str
    verdict: str                    # PASS | HOLD | OVERRIDE
    checks_run: list[str] = field(default_factory=list)
    holds: list[str] = field(default_factory=list)
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    overridden_by: str | None = None   # set only when verdict == OVERRIDE

    @property
    def ok(self) -> bool:
        return self.verdict in (PASS, OVERRIDE)

    def as_dict(self) -> dict:
        return asdict(self)


def _log(v: Verdict) -> None:
    """Append to the Silver ledger + hale_decisions.md. Best-effort — a logging
    failure never changes a verdict, but the verdict itself is already decided."""
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a") as f:
            f.write(json.dumps(v.as_dict()) + "\n")
    except Exception:
        pass
    try:
        line = (f"\n- **CHIEF SILVER** [{v.ts[:16]}Z] {v.stage.upper()} "
                f"{v.mission_id} → {v.verdict}"
                + (f" ({len(v.holds)} hold(s): {'; '.join(v.holds)[:200]})" if v.holds else "")
                + f" — {v.work_product[:80]}")
        with DECISIONS.open("a") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ── FRONT — frame "done" before work starts ────────────────────────────────

def silver_front_frame(
    mission_id: str,
    title: str,
    acceptance_criteria: str,
    ground_truth_sources: list[str] | None = None,
) -> Verdict:
    """Silver at the front of the task: is "done" framed concretely enough that
    a second seat could verify it without asking the assignee?"""
    holds: list[str] = []
    checks = ["criteria-present", "criteria-checkable", "ground-truth-named"]
    crit = (acceptance_criteria or "").strip()

    if not crit:
        holds.append("no acceptance criteria — 'done' is undefined")
    elif not _CHECKABLE.search(crit):
        holds.append("criteria name nothing checkable (no count, path, ref, or artifact) — "
                     "a second seat could not verify this without asking the assignee")

    sources = [s for s in (ground_truth_sources or []) if s.strip()]
    if not sources:
        holds.append("no ground-truth source named — verdicts would rest on the assignee's own claim")
    else:
        missing = [s for s in sources
                   if ("/" in s or s.endswith((".md", ".json", ".html", ".py")))
                   and not (ROOT / s).exists() and not Path(s).exists()]
        if missing:
            checks.append("ground-truth-exists")
            holds.append(f"named ground-truth source(s) do not exist: {missing}")

    v = Verdict("front", mission_id, title, HOLD if holds else PASS, checks, holds)
    _log(v)
    return v


# ── BACK — deterministic check battery on the work product ─────────────────

def _excursion_claims(text: str) -> list[int]:
    """Only TOTAL claims count: 'six shore excursions' / 'six excursions are
    reserved' are totals; 'two excursions, both of you' (one day's tours) is not."""
    num = r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten)"
    out = []
    for pat in (num + r"\s+shore\s+excursions?",
                num + r"\s+excursions?\s+(?:are|were|is|reserved|confirmed|booked|included|in all|in total)"):
        for m in re.finditer(pat, text, re.I):
            g = m.group(1).lower()
            out.append(int(g) if g.isdigit() else WORD.get(g, 0))
    return [n for n in out if n]


def _check_portal(cdir: Path, others: list[str], dossier: str | None) -> list[str]:
    """Portal battery — count-match, images, segregation (2026-07-03 misses)."""
    holds: list[str] = []
    docs = [d for d in sorted(cdir.glob("*.md")) if d.name != "portal.json"]

    claims = {d.name: c for d in docs if (c := _excursion_claims(d.read_text()))}
    allnums = {n for v in claims.values() for n in v}
    if len(allnums) > 1:
        holds.append("count-match: excursion count disagrees across docs: "
                     + "; ".join(f"{k}={v}" for k, v in claims.items()))
    if dossier and Path(dossier).exists() and allnums:
        dm = re.search(r"(\d+)\s+excursions?\s+confirmed", Path(dossier).read_text(), re.I)
        if dm and max(allnums) != int(dm.group(1)):
            holds.append(f"count-match: portal states {max(allnums)} excursions "
                         f"but dossier ground-truth = {dm.group(1)} confirmed")

    html = cdir.parent / "html/index.html"
    if html.exists():
        h = html.read_text()
        if "📷" in h:
            holds.append(f"images: {h.count('📷')} caption placeholder(s) still rendering")
        stray = re.findall(r'src="(assets/[^"]+)"', h)
        if stray:
            holds.append(f"images: {len(stray)} image(s) not inlined (will 401 on auth): {stray[:3]}")
        bad = 0
        for b in re.findall(r"data:image/jpeg;base64,([A-Za-z0-9+/=]+)", h):
            try:
                raw = base64.b64decode(b[:200] + "=" * (-len(b[:200]) % 4))
                bad += raw[:2] != b"\xff\xd8"
            except Exception:
                bad += 1
        if bad:
            holds.append(f"images: {bad} inline image(s) are not valid JPEG")
    else:
        holds.append("images: no built index.html to check")

    if others:
        blob = " ".join(d.read_text() for d in docs).lower()
        hit = [o for o in others if re.search(rf"\b{re.escape(o.lower())}\b", blob)]
        if hit:
            holds.append(f"segregation: other couple named in copy: {hit}")
    return holds


def _check_file(p: Path, criteria: str) -> list[str]:
    """Generic file battery: exists, non-empty, no placeholder residue, and every
    number the criteria promise actually appears in the product."""
    holds: list[str] = []
    if not p.exists():
        return [f"artifact path does not exist: {p}"]
    try:
        text = p.read_text(errors="replace")
    except Exception:
        return []  # binary artifact — existence + size are the checkable subset
    if not text.strip():
        return [f"artifact is empty: {p}"]
    found = [m for m in _PLACEHOLDERS if m in text]
    if found:
        holds.append(f"placeholder residue in artifact: {found}")
    promised = set(re.findall(r"\b\d+\b", criteria))
    missing = [n for n in promised if n not in text]
    if missing:
        holds.append(f"criteria promise number(s) {missing} not found in artifact")
    return holds


def run_gate(
    work_product: str,
    acceptance_criteria: str,
    *,
    mission_id: str = "ADHOC",
    others: list[str] | None = None,
    dossier: str | None = None,
) -> Verdict:
    """Silver at the back of the task. Routes to the right battery:
      - portal client dir       → count-match / images / segregation
      - local file              → exists / non-empty / no placeholders / criteria numbers
      - non-path reference      → must at least be a concrete ref (commit/url/row), not a claim
    Deterministic only — never guesses a pass."""
    holds: list[str] = []
    checks: list[str] = []
    wp = (work_product or "").strip()

    if not wp:
        holds.append("no work product given — nothing to gate")
    else:
        p = Path(wp) if wp.startswith("/") else ROOT / wp
        # allow "path@commit" refs — gate the path part
        local = p if p.exists() else Path(str(p).split("@")[0])
        if local.is_dir():
            checks += ["count-match", "images", "segregation"]
            holds += _check_portal(local, others or [], dossier)
        elif local.exists():
            checks += ["file-exists", "non-empty", "placeholders", "criteria-numbers"]
            holds += _check_file(local, acceptance_criteria)
        else:
            checks.append("concrete-reference")
            if not _CONCRETE_ARTIFACT.search(wp):
                holds.append(f"artifact is a bare claim, not a concrete reference: {wp!r}")

    if not (acceptance_criteria or "").strip():
        checks.append("criteria-present")
        holds.append("no acceptance criteria — nothing to validate against")

    v = Verdict("back", mission_id, wp, HOLD if holds else PASS, checks, holds)
    _log(v)
    if not v.ok:
        _page_hold(v)
    return v


def human_override(mission_id: str, work_product: str, overridden_by: str,
                    *, stage: str = "back") -> Verdict:
    """The Commander's own close IS the verification (Commander directive
    2026-07-29 — CHIEF SILVER exists to stop an AI seat from self-certifying
    a hollow completion, not to interrogate the Commander). No artifact, no
    criteria, no deterministic battery — but never a SILENT bypass: this
    still writes an attributed row to the same ledger every PASS/HOLD lands
    in, verdict=OVERRIDE, so `brief_section()` and any audit can always tell
    "a human overrode the gate" from "the gate actually passed." Callers MUST
    reserve this for a genuine human close (see the "COMMANDER" literal gate
    in staff_summary_sheet.close_sss / mission_board_sync.cmd_sss_close /
    cmd_complete) — an AI seat closing its own work always goes through
    run_gate() instead, unchanged."""
    who = (overridden_by or "").strip()
    if not who:
        raise ValueError("human_override requires an attributed overridden_by (who asserted this close)")
    v = Verdict(stage, mission_id, work_product or "(no artifact — human override)",
                OVERRIDE, ["human-override"], [], overridden_by=who)
    _log(v)
    return v


def _page_hold(v: Verdict) -> None:
    """A back-gate HOLD is a stopped work product — page the Commander via the
    disciplined wing_page lane (P1, one-and-done dedup). Best-effort."""
    try:
        import html
        from core.comms.wing_page import send_page, P1
        send_page(
            problem=html.escape(f"CHIEF SILVER HOLD — {v.mission_id}: {v.work_product[:80]}"),
            discussion="\n".join(html.escape(f"• {h}") for h in v.holds[:6]),
            action="Fix the holds; the ticket cannot certify until the gate passes.",
            level=P1, source="CHIEF SILVER",
        )
    except Exception:
        pass


# ── Internal-ops battery (board hygiene, inbox dupes, memory parity) ───────

def internal_ops_check() -> list[str]:
    """Silver on the Wing's own machinery: duplicate open missions, re-injected
    inbox tasks, OC/CC memory parity (2026-07-04 Commander directive)."""
    holds: list[str] = []
    try:
        board = json.loads((ROOT / "OpsCenter/mission_board.json").read_text())
        norm = lambda t: frozenset(re.sub(r"[^a-z0-9\s]", "", t.lower()).split())
        seen: dict[frozenset, str] = {}
        for m in board.get("missions", []):
            if m.get("status") not in ("active", "in_progress", "open", "pending"):
                continue
            key = norm(m.get("title", ""))
            if key and key in seen:
                holds.append(f"board-dup: {m['id']} duplicates {seen[key]}")
            elif key:
                seen[key] = m["id"]
    except Exception as e:
        holds.append(f"board-dup: mission board unreadable: {str(e)[:60]}")

    for inbox in ("claude_inbox.md", "OpsCenter/collaboration/opencode_inbox.md"):
        p = ROOT / inbox
        if p.exists():
            ids = re.findall(r"## TASK: (\S+)\nstatus: UNREAD", p.read_text())
            dupes = [t for t, c in collections.Counter(ids).items() if c > 1]
            if dupes:
                holds.append(f"inbox-dup: {inbox}: injected UNREAD more than once: {dupes}")

    agents_md = ROOT / "AGENTS.md"
    mem = Path("/home/john/.claude/projects/-home-john-Thunderbird/memory/MEMORY.md")
    if not agents_md.exists():
        holds.append("memory-parity: AGENTS.md missing — OC has zero context")
    else:
        text = agents_md.read_text()
        if "cat /home/john/.claude/projects/-home-john-Thunderbird/memory/MEMORY.md" not in text:
            holds.append("memory-parity: AGENTS.md no longer chains to CC memory index")
        if "MEMORY WRITE-BACK" not in text:
            holds.append("memory-parity: AGENTS.md missing write-back contract")
    if not mem.exists():
        holds.append("memory-parity: shared memory substrate MEMORY.md gone")
    return holds


def internal_ops_verdict() -> Verdict:
    holds = internal_ops_check()
    v = Verdict("back", "INTERNAL-OPS", "wing machinery",
                HOLD if holds else PASS,
                ["board-dup", "inbox-dup", "memory-parity"], holds)
    _log(v)
    return v


# ── Visibility — daily CHIEF SILVER brief section ───────────────────────────

def brief_section(for_date: date | None = None) -> str:
    """Render the standing CHIEF SILVER section for the morning/EOD brief:
    what he framed, passed, held today — and a red flag on silence."""
    d = (for_date or datetime.now(timezone.utc).date()).isoformat()
    entries = []
    if LEDGER.exists():
        for line in LEDGER.read_text().splitlines():
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("ts", "").startswith(d):
                entries.append(e)
    lines = ["## 🛡️ CHIEF SILVER — Overseer Activity"]
    if not entries:
        lines.append("🔴 **ZERO Silver gate entries today.** If any work product "
                     "shipped, the mandatory front/back gate was bypassed.")
        return "\n".join(lines)
    fronts = [e for e in entries if e["stage"] == "front"]
    backs = [e for e in entries if e["stage"] == "back"]
    held = [e for e in entries if e["verdict"] == HOLD]
    overridden = [e for e in entries if e["verdict"] == OVERRIDE]
    lines.append(f"- Framed (front): {len(fronts)} · Gated (back): {len(backs)} · "
                 f"Held: {len(held)} · Human overrides: {len(overridden)}")
    for e in held:
        lines.append(f"  - 🔴 HOLD {e['mission_id']} — {'; '.join(e['holds'])[:160]}")
    for e in overridden:
        lines.append(f"  - 🟡 OVERRIDE {e['mission_id']} — by {e.get('overridden_by', '?')} (no gate run)")
    for e in entries:
        if e["verdict"] == PASS:
            lines.append(f"  - ✅ {e['stage'].upper()} {e['mission_id']} — {e['work_product'][:70]}")
    try:
        from core.silver.insight_exchange import brief_lines
        ix = brief_lines()
        if ix:
            lines.append("- Insight Exchange (open cards + seat hit-rates):")
            lines.extend(ix)
    except Exception:
        pass
    return "\n".join(lines)


def print_verdict(v: Verdict) -> int:
    print(f"CHIEF SILVER — {v.stage.upper()} {v.mission_id}")
    if v.ok:
        print(f"  PASS. Checks: {', '.join(v.checks_run)}. Ships.")
        return 0
    print(f"  HOLD — {len(v.holds)} finding(s). This doesn't reach the Commander until fixed:")
    for h in v.holds:
        print(f"   • {h}")
    print("  — CMSgt S. Sterling, Command Chief")
    return 1
