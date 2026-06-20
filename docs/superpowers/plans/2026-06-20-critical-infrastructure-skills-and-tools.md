# Critical Infrastructure (CI) Skills & Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a governed "Critical Infrastructure" layer — a registry of CI skills, each paired with a CI tool, a measurable razor-sharp currency policy, a dedicated owner persona (Whetstone), a daily health/currency sweep tool, and the OA commission tracker as the first concrete CI-consuming deliverable.

**Architecture:** A single JSON registry (`config/ci_registry.json`) is the source of truth AND the policy — each entry carries health-probe + currency-window + re-eval-cadence + fallback + owner. `core/ci/` holds the loader/validator and the health/currency engine; `scripts/ci_sweep.py` runs it on a timer and pages on degradation. CI skills **wrap existing assets** (portal/keepalive scripts, headless-spawn wrapper, Anansi) — this is a governance/currency layer, not a from-scratch rebuild. Two tool upgrades (portal-access stealth tool, Anansi enhancer) are **research-gated** on `intel/CI_web_stack_research_20260620.md` (Dembe agent, in flight). A new persona, Whetstone (A14), owns currency/updating; ELON owns discovery, Dembe access-intel, Sterling the gate/metrics.

**Tech Stack:** Python 3.13, pytest, JSON registry, systemd user timers, existing `core/` modules (`thunderbird_headless_spawn.py`, `harlan_booking_master.py`), Anansi (`.venv/bin/anansi`), portal scripts in `scripts/`.

**Scope note (per writing-plans scope check):** This is deliberately ONE plan delivered in sequenced phases. Phases 1–2 and 5 are research-independent and ship working software immediately. Phase 3 is research-gated (decision-gate tasks; fill on Dembe agent completion). Phase 0 (OA tracker) is independent and already Commander-approved. Each phase produces working, testable software on its own.

**Naming decisions made (Commander reviews on plan approval):**
- New persona: **A14 "Whetstone"** — Director of Critical Infrastructure Currency ("keeps the blades razor-sharp"). Rename freely on review.
- Registry: `config/ci_registry.json`. Engine: `core/ci/`. CLI: `scripts/ci_sweep.py`. Policy SO: `standing_orders/SO_CI_RAZOR_SHARP_20260620.md`.

**Razor-sharp definition (measurable, not a slogan):** A CI skill is `RAZOR_SHARP` iff its health probe returns GREEN **and** `now - last_verified < currency_window_hours` **and** `now - last_reeval < reeval_cadence_days`. Otherwise `DULL` (currency/re-eval overdue) or `RED` (probe failed) → page the owner. The registry table IS the policy; the SO references it.

---

## File Structure

| File | Responsibility | New/Modify |
|------|---------------|-----------|
| `config/ci_registry.json` | Source of truth + policy: every CI skill, paired tool, owner, probe, currency window, re-eval cadence, fallback, status | Create |
| `core/ci/__init__.py` | Package marker | Create |
| `core/ci/registry.py` | Load + validate the registry; compute razor-sharp status per entry | Create |
| `core/ci/ci_health.py` | The meta CI tool: run every probe, compute status, write dashboard, return page-worthy degradations | Create |
| `scripts/ci_sweep.py` | CLI entry: run the sweep, print/JSON, page on RED/DULL | Create |
| `core/finance/oa_commission_tracker.py` | OA trailing-12-mo received-commission tracker; pages at 90%/95% | Create |
| `config/oa_commission_ledger.json` | Pluggable data source v1: recorded received-commission line items | Create |
| `Personas/a14_whetstone_personality.md` | New persona: CI Keeper / currency owner | Create |
| `standing_orders/SO_CI_RAZOR_SHARP_20260620.md` | The razor-sharp policy (references the registry table) | Create |
| `tests/ci/test_registry.py` | Registry load/validate/status tests | Create |
| `tests/ci/test_ci_health.py` | Health engine tests | Create |
| `tests/finance/test_oa_commission_tracker.py` | OA tracker tests | Create |
| `output/CI_DASHBOARD.md` | Generated dashboard (gitignored output) | Generated |
| `CLAUDE.md` | Add CI doctrine pointer + Whetstone to staff references | Modify |

---

## PHASE 0 — OA Commission Tracker (independent, Commander-approved)

**Why first:** Concrete, already greenlit, answers "how will I be notified." Data source is pluggable so it is NOT blocked on the portal CI tool. Baseline truth: commission is counted when **received** (post-travel payout), which today ≈ $0 toward the OA $10K (90%) threshold — NOT the $23K pipeline (that spans three hosts and is unsailed).

### Task 0.1: Determine + document the OA data source

**Files:**
- Create: `config/oa_commission_ledger.json`
- Test: `tests/finance/test_oa_commission_tracker.py`

- [ ] **Step 1: Investigate how OA statements are actually obtained**

Run these and record results in the ledger header comment:
```bash
cd /home/john/Thunderbird
grep -rin "outsideagents\|outside agents" --include="*.py" --include="*.md" . | grep -vi "regent\|\.git/" | head
# Confirm: is there an OA agent-portal login, or are statements emailed?
```
Expected: no existing automated OA access (confirmed 2026-06-20). Conclusion: **v1 data source = a recorded ledger** (`config/oa_commission_ledger.json`) that Harlan/Commander append from the weekly OA statement (paid Tuesdays). v2 (Phase 3, research-gated) = automate via the portal-access CI tool.

- [ ] **Step 2: Create the ledger seed file**

```json
{
  "_doc": "Outside Agents received-commission ledger. Tier upgrades are per-host on commission RECEIVED (post-travel payout), trailing 12 months. OA: 80% base; 90% at $10,000; 95% at $40,000 (exact $ from OA Learn-More subpage; mechanism confirmed via Anansi from OA FAQ 2026-06-20). OA pays weekly Tuesdays after supplier pays. v1: append each weekly statement line manually; v2: automate via portal-access CI tool.",
  "host": "Outside Agents, LLC",
  "thresholds": {"tier_90_usd": 10000, "tier_95_usd": 40000},
  "received": []
}
```
Each future `received[]` entry shape: `{"date": "YYYY-MM-DD", "client": "", "booking": "", "supplier": "Viking|Bedsonline", "gross_commission_usd": 0.0, "d2m_received_usd": 0.0, "statement_ref": ""}`.

- [ ] **Step 3: Commit**

```bash
git add config/oa_commission_ledger.json
git commit -m "feat(oa-tracker): seed Outside Agents received-commission ledger (v1 data source)"
```

### Task 0.2: OA tracker — trailing-12-month rolling total + tier status

**Files:**
- Create: `core/finance/oa_commission_tracker.py`
- Test: `tests/finance/test_oa_commission_tracker.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/finance/test_oa_commission_tracker.py
import json
from datetime import date
from pathlib import Path
import sys
sys.path.insert(0, "/home/john/Thunderbird")
from core.finance.oa_commission_tracker import rolling_received, tier_for, OATracker

def test_rolling_received_excludes_older_than_12_months():
    entries = [
        {"date": "2025-01-01", "d2m_received_usd": 5000.0},  # >12mo before as_of
        {"date": "2026-02-01", "d2m_received_usd": 3000.0},
        {"date": "2026-05-01", "d2m_received_usd": 2000.0},
    ]
    total = rolling_received(entries, as_of=date(2026, 6, 20))
    assert total == 5000.0  # only the two within trailing 12 months

def test_tier_thresholds():
    assert tier_for(0.0) == 80
    assert tier_for(9999.99) == 80
    assert tier_for(10000.0) == 90
    assert tier_for(39999.99) == 90
    assert tier_for(40000.0) == 95

def test_tracker_reports_distance_to_next_tier(tmp_path):
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({
        "host": "Outside Agents, LLC",
        "thresholds": {"tier_90_usd": 10000, "tier_95_usd": 40000},
        "received": [{"date": "2026-06-01", "d2m_received_usd": 2500.0}],
    }))
    t = OATracker(ledger_path=ledger)
    status = t.status(as_of=date(2026, 6, 20))
    assert status["rolling_received_usd"] == 2500.0
    assert status["current_tier_pct"] == 80
    assert status["to_next_tier_usd"] == 7500.0  # 10000 - 2500
    assert status["crossed_90"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/john/Thunderbird && python3 -m pytest tests/finance/test_oa_commission_tracker.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.finance.oa_commission_tracker'`

- [ ] **Step 3: Write minimal implementation**

```python
# core/finance/oa_commission_tracker.py
"""Outside Agents received-commission tracker.

Tier is per-host on commission RECEIVED (post-travel payout), trailing 12 months.
OA: 80% base; 90% at $10,000; 95% at $40,000. Source of truth: config/oa_commission_ledger.json.
Harlan owns the numbers. Pages Commander when a threshold is crossed.
"""
from __future__ import annotations
import json
from datetime import date, timedelta
from pathlib import Path

DEFAULT_LEDGER = Path("/home/john/Thunderbird/config/oa_commission_ledger.json")
TIER_90_USD = 10000.0
TIER_95_USD = 40000.0


def _parse(d: str) -> date:
    y, m, dd = (int(x) for x in d.split("-"))
    return date(y, m, dd)


def rolling_received(entries: list[dict], as_of: date) -> float:
    cutoff = as_of - timedelta(days=365)
    return round(sum(
        float(e.get("d2m_received_usd", 0.0))
        for e in entries
        if cutoff < _parse(e["date"]) <= as_of
    ), 2)


def tier_for(rolling_usd: float) -> int:
    if rolling_usd >= TIER_95_USD:
        return 95
    if rolling_usd >= TIER_90_USD:
        return 90
    return 80


class OATracker:
    def __init__(self, ledger_path: Path = DEFAULT_LEDGER):
        self.ledger_path = Path(ledger_path)

    def _load(self) -> dict:
        return json.loads(self.ledger_path.read_text())

    def status(self, as_of: date | None = None) -> dict:
        as_of = as_of or date.today()
        data = self._load()
        entries = data.get("received", [])
        rolling = rolling_received(entries, as_of)
        tier = tier_for(rolling)
        next_threshold = TIER_90_USD if tier == 80 else (TIER_95_USD if tier == 90 else None)
        to_next = round(next_threshold - rolling, 2) if next_threshold else 0.0
        return {
            "host": data.get("host", "Outside Agents, LLC"),
            "as_of": as_of.isoformat(),
            "rolling_received_usd": rolling,
            "current_tier_pct": tier,
            "to_next_tier_usd": to_next,
            "crossed_90": rolling >= TIER_90_USD,
            "crossed_95": rolling >= TIER_95_USD,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/john/Thunderbird && python3 -m pytest tests/finance/test_oa_commission_tracker.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add core/finance/oa_commission_tracker.py tests/finance/test_oa_commission_tracker.py
git commit -m "feat(oa-tracker): trailing-12mo rolling received-commission + tier status"
```

### Task 0.3: OA tracker paging + brief integration

**Files:**
- Modify: `core/finance/oa_commission_tracker.py`
- Test: `tests/finance/test_oa_commission_tracker.py`

- [ ] **Step 1: Write the failing test (append)**

```python
def test_page_message_on_crossing(tmp_path):
    from core.finance.oa_commission_tracker import OATracker
    ledger = tmp_path / "l.json"
    ledger.write_text(json.dumps({
        "host": "Outside Agents, LLC",
        "thresholds": {"tier_90_usd": 10000, "tier_95_usd": 40000},
        "received": [{"date": "2026-06-01", "d2m_received_usd": 10500.0}],
    }))
    t = OATracker(ledger_path=ledger)
    msg = t.page_if_crossed(as_of=date(2026, 6, 20))
    assert msg is not None
    assert "90%" in msg and "$10,500" in msg

def test_no_page_below_threshold(tmp_path):
    from core.finance.oa_commission_tracker import OATracker
    ledger = tmp_path / "l2.json"
    ledger.write_text(json.dumps({"host": "OA", "thresholds": {}, "received": []}))
    t = OATracker(ledger_path=ledger)
    assert t.page_if_crossed(as_of=date(2026, 6, 20)) is None
```

- [ ] **Step 2: Run to verify fail**

Run: `cd /home/john/Thunderbird && python3 -m pytest tests/finance/test_oa_commission_tracker.py::test_page_message_on_crossing -v`
Expected: FAIL — `AttributeError: 'OATracker' object has no attribute 'page_if_crossed'`

- [ ] **Step 3: Implement `page_if_crossed` (append to class)**

```python
    def page_if_crossed(self, as_of: date | None = None) -> str | None:
        s = self.status(as_of)
        if s["crossed_95"]:
            return (f"💰 OA COMMISSION TIER — 95% reached. Trailing-12mo received "
                    f"${s['rolling_received_usd']:,.2f} (host: {s['host']}). Verify OA portal bumped your split.")
        if s["crossed_90"]:
            return (f"💰 OA COMMISSION TIER — 90% reached. Trailing-12mo received "
                    f"${s['rolling_received_usd']:,.2f} (host: {s['host']}). Verify OA portal bumped your split.")
        return None
```

- [ ] **Step 4: Run to verify pass**

Run: `cd /home/john/Thunderbird && python3 -m pytest tests/finance/test_oa_commission_tracker.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Wire into the daily sweep + brief (manual integration note)**

Add to the AM brief generator a one-line FINANCIAL PULSE row sourced from `OATracker().status()`: `"OA tier: {current_tier_pct}% · ${rolling_received_usd:,.0f} received (trailing 12mo) · ${to_next_tier_usd:,.0f} to {next}%"`. The `page_if_crossed()` call goes in the daily OODA Observe sweep (Phase 2 `ci_sweep.py` can host it, or `agents/thunderbird_daily_brief.py`). Harlan signs off OA ledger entries.

- [ ] **Step 6: Commit**

```bash
git add core/finance/oa_commission_tracker.py tests/finance/test_oa_commission_tracker.py
git commit -m "feat(oa-tracker): threshold paging at 90%/95% + brief integration note"
```

---

## PHASE 1 — CI Registry + Razor-Sharp Policy + Whetstone Persona (research-independent)

### Task 1.1: CI registry schema + seed (the source of truth AND the policy)

**Files:**
- Create: `config/ci_registry.json`

- [ ] **Step 1: Write the registry seed**

Each of the 5 CI skills is an entry. `ci_tool` for portal-access + web-fetch is `"<PENDING-RESEARCH>"` (filled in Phase 3). `wraps` references EXISTING assets — this is a governance layer, not a rebuild.

```json
{
  "version": 1,
  "updated": "2026-06-20",
  "_doc": "Critical Infrastructure registry. This table IS the razor-sharp policy (SO_CI_RAZOR_SHARP_20260620.md). A skill is RAZOR_SHARP iff probe==GREEN AND age(last_verified)<currency_window_hours AND age(last_reeval)<reeval_cadence_days. Owners: id=ELON(discovery), access=Dembe(access-intel), gate=Sterling(complexity/cost/metrics), keeper=Whetstone(currency+updating, daily).",
  "skills": [
    {
      "id": "portal-access",
      "name": "Cruise-line Portal Access",
      "ci_tool": "<PENDING-RESEARCH:intel/CI_web_stack_research_20260620.md>",
      "wraps": ["scripts/regent_oa_reauth.py", "scripts/centrav_session_warm.py", "scripts/grab_regent_cookies_cdp.py", "scripts/portal_live_probe.py"],
      "id_owner": "elon", "access_owner": "dembe", "gate_owner": "sterling", "keeper": "whetstone",
      "health_probe": "python3 scripts/portal_live_probe.py --json",
      "currency_window_hours": 24,
      "reeval_cadence_days": 30,
      "fallback": "manual cookie capture via setup-browser-cookies skill (gstack)",
      "last_verified": null, "last_reeval": "2026-06-20", "status": "unknown"
    },
    {
      "id": "web-fetch",
      "name": "Web Fetch & Scrape",
      "ci_tool": "<PENDING-RESEARCH:intel/CI_web_stack_research_20260620.md>",
      "wraps": [".venv/bin/anansi", ".claude/skills/scrape/SKILL.md", ".claude/skills/browse/SKILL.md"],
      "id_owner": "elon", "access_owner": "dembe", "gate_owner": "sterling", "keeper": "whetstone",
      "health_probe": "/home/john/Thunderbird/.venv/bin/anansi fetch https://example.com --output text",
      "currency_window_hours": 168,
      "reeval_cadence_days": 30,
      "fallback": "playwright headless (last resort)",
      "last_verified": null, "last_reeval": "2026-06-20", "status": "unknown"
    },
    {
      "id": "headless-dispatch",
      "name": "Headless AI Dispatch (claude -p / MAX OAuth)",
      "ci_tool": "core/ai_infra/thunderbird_headless_spawn.py",
      "wraps": ["OpsCenter/dispatch_claude.py", "core/ai_infra/thunderbird_headless_spawn.py"],
      "id_owner": "elon", "access_owner": "sterling", "gate_owner": "sterling", "keeper": "whetstone",
      "health_probe": "test -x /home/john/.local/bin/claude && test -f /home/john/.claude/.credentials.json",
      "currency_window_hours": 2,
      "reeval_cadence_days": 30,
      "fallback": "managed agents API (dispatch_claude.py --managed)",
      "last_verified": null, "last_reeval": "2026-06-20", "status": "unknown"
    },
    {
      "id": "credential-keepalive",
      "name": "Credential & OAuth Keepalive",
      "ci_tool": "scripts/keepalive_supervisor.py",
      "wraps": ["scripts/keepalive_supervisor.py", "scripts/portal_keepalive.py", "scripts/centrav_session_auto_keepalive.py"],
      "id_owner": "elon", "access_owner": "dembe", "gate_owner": "sterling", "keeper": "whetstone",
      "health_probe": "python3 scripts/keepalive_supervisor.py --status --json",
      "currency_window_hours": 3,
      "reeval_cadence_days": 30,
      "fallback": "manual re-auth via centrav_reauth.py / regent_oa_reauth.py",
      "last_verified": null, "last_reeval": "2026-06-20", "status": "unknown"
    },
    {
      "id": "tech-adoption",
      "name": "New-Tech Scout / Watch-list / Integration",
      "ci_tool": "core/intel/thunderbird_incubator.py",
      "wraps": ["core/intel/thunderbird_incubator.py", "OpsCenter/wind_staff.py"],
      "id_owner": "elon", "access_owner": "dembe", "gate_owner": "sterling", "keeper": "whetstone",
      "health_probe": "python3 -c \"import importlib.util as u; s=u.spec_from_file_location('i','core/intel/thunderbird_incubator.py'); print('ok')\"",
      "currency_window_hours": 24,
      "reeval_cadence_days": 14,
      "fallback": "manual Dembe sweep via wind_staff.py dembe",
      "last_verified": null, "last_reeval": "2026-06-20", "status": "unknown"
    }
  ]
}
```

- [ ] **Step 2: Add the replacement policy (Commander directive 2026-06-20 — "fail XXX times or undue delay → replace")**

Add a top-level `replacement_policy` block AND a `latency_sla_ms` field to each skill. These are the **measurable replacement triggers** — distinct from currency (DULL). A tool moves to status `REPLACE` when its failure/latency history breaches these.

Add to the registry root (sibling of `skills`):
```json
"replacement_policy": {
  "_doc": "A CI tool → REPLACE (ELON nominates a replacement, Whetstone integrates, old tool → graveyard) when ANY trigger fires. Failure = probe/op returned not-ok or timed out. Latency measured per run (ms).",
  "consecutive_failures_max": 3,
  "rolling_window_days": 7,
  "failures_in_window_max": 5,
  "latency_breach_factor": 3.0,
  "latency_breach_runs_of_last_5": 3,
  "consecutive_timeouts_max": 2
}
```
And add `"latency_sla_ms"` to each skill entry:
- `portal-access`: `90000` (login flows)
- `web-fetch`: `15000`
- `headless-dispatch`: `300000`
- `credential-keepalive`: `30000`
- `tech-adoption`: `60000`

**The criteria (this is the "figure out the criteria" answer — status `REPLACE` if ANY fires):**

| Trigger | Threshold | Why this number |
|---|---|---|
| Consecutive failures | ≥ **3** in a row | 1–2 = transient blip; 3 straight = systemic |
| Rolling failure rate | ≥ **5 failures in 7 days** | chronic flakiness even when not consecutive |
| Undue delay (sustained) | run > `latency_sla_ms` on ≥ **3 of last 5** runs | slow trend, not one slow run |
| Undue delay (spike) | any single run > **3× `latency_sla_ms`** | one catastrophic hang counts |
| Hung tool | probe timeout (60s) ≥ **2 consecutive** | tool is wedged |

`REPLACE` is more severe than `DULL`/`RED`: RED = down now (may recover); DULL = currency overdue (refresh it); **REPLACE = chronic — swap the tool.** REPLACE pages Whetstone AND notifies ELON (replacement nomination from his watch-list/graveyard) → Sterling gates → Whetstone integrates.

- [ ] **Step 3: Validate JSON**

Run: `cd /home/john/Thunderbird && python3 -c "import json; d=json.load(open('config/ci_registry.json')); assert d['replacement_policy']['consecutive_failures_max']==3; assert all('latency_sla_ms' in s for s in d['skills']); print('valid')"`
Expected: `valid`

- [ ] **Step 4: Commit**

```bash
git add config/ci_registry.json
git commit -m "feat(ci): seed CI registry — 5 skills, paired tools, razor-sharp + replacement policy"
```

### Task 1.2: Registry loader + razor-sharp status computation

**Files:**
- Create: `core/ci/__init__.py`, `core/ci/registry.py`
- Test: `tests/ci/test_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/ci/test_registry.py
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys
sys.path.insert(0, "/home/john/Thunderbird")
from core.ci.registry import load_registry, razor_sharp_status

def _entry(**kw):
    base = {"id": "x", "currency_window_hours": 24, "reeval_cadence_days": 30,
            "last_verified": None, "last_reeval": "2026-06-20"}
    base.update(kw); return base

def test_load_registry_returns_skills():
    reg = load_registry(Path("/home/john/Thunderbird/config/ci_registry.json"))
    ids = {s["id"] for s in reg["skills"]}
    assert {"portal-access", "web-fetch", "headless-dispatch", "credential-keepalive", "tech-adoption"} <= ids

def test_red_when_probe_failed():
    now = datetime(2026, 6, 20, tzinfo=timezone.utc)
    assert razor_sharp_status(_entry(), probe_ok=False, now=now) == "RED"

def test_dull_when_currency_stale():
    now = datetime(2026, 6, 20, tzinfo=timezone.utc)
    stale = (now - timedelta(hours=48)).isoformat()
    assert razor_sharp_status(_entry(last_verified=stale, currency_window_hours=24), probe_ok=True, now=now) == "DULL"

def test_razor_sharp_when_fresh_and_green():
    now = datetime(2026, 6, 20, tzinfo=timezone.utc)
    fresh = (now - timedelta(hours=1)).isoformat()
    e = _entry(last_verified=fresh, last_reeval="2026-06-19", currency_window_hours=24, reeval_cadence_days=30)
    assert razor_sharp_status(e, probe_ok=True, now=now) == "RAZOR_SHARP"
```

- [ ] **Step 2: Run to verify fail**

Run: `cd /home/john/Thunderbird && python3 -m pytest tests/ci/test_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.ci'`

- [ ] **Step 3: Implement**

```python
# core/ci/__init__.py
```
(empty file)

```python
# core/ci/registry.py
"""CI registry loader + razor-sharp status computation.
The registry (config/ci_registry.json) is the source of truth AND the policy.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone, date
from pathlib import Path

DEFAULT_REGISTRY = Path("/home/john/Thunderbird/config/ci_registry.json")
REQUIRED_FIELDS = ("id", "name", "ci_tool", "health_probe", "currency_window_hours",
                   "reeval_cadence_days", "fallback", "keeper")


def load_registry(path: Path = DEFAULT_REGISTRY) -> dict:
    reg = json.loads(Path(path).read_text())
    for s in reg.get("skills", []):
        missing = [f for f in REQUIRED_FIELDS if f not in s]
        if missing:
            raise ValueError(f"CI registry entry {s.get('id','?')} missing fields: {missing}")
    return reg


def _age_hours(iso: str | None, now: datetime) -> float:
    if not iso:
        return float("inf")
    dt = datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt).total_seconds() / 3600.0


def _age_days(d: str | None, now: datetime) -> float:
    if not d:
        return float("inf")
    y, m, dd = (int(x) for x in d.split("-"))
    return (now.date() - date(y, m, dd)).days


def razor_sharp_status(entry: dict, probe_ok: bool, now: datetime | None = None) -> str:
    """RED (probe failed) | DULL (currency/re-eval overdue) | RAZOR_SHARP."""
    now = now or datetime.now(timezone.utc)
    if not probe_ok:
        return "RED"
    if _age_hours(entry.get("last_verified"), now) >= entry["currency_window_hours"]:
        return "DULL"
    if _age_days(entry.get("last_reeval"), now) >= entry["reeval_cadence_days"]:
        return "DULL"
    return "RAZOR_SHARP"
```

- [ ] **Step 4: Run to verify pass**

Run: `cd /home/john/Thunderbird && python3 -m pytest tests/ci/test_registry.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add core/ci/__init__.py core/ci/registry.py tests/ci/test_registry.py
git commit -m "feat(ci): registry loader + razor-sharp status engine"
```

### Task 1.3: Whetstone (A14) persona — doc artifact

**Files:**
- Create: `Personas/a14_whetstone_personality.md`

- [ ] **Step 1: Write the persona file**

Doc artifact (prose — no TDD). Follow the structure of `Personas/a12_elon_personality.md` (IDENTITY SNAPSHOT, TEMPERAMENT, VOICE, COGNITIVE STYLE, STRONG OPINIONS, MANDATE, PET PEEVES, closing tagline). Required content:
- **Identity:** A14 "Whetstone" — Director of Critical Infrastructure Currency. Counterpart to ELON: ELON finds and kills; Whetstone keeps what survives razor-sharp. Obsessed with currency — a tool that worked last month but silently rotted is worse than no tool.
- **Mandate (CI Keeper):** owns the `config/ci_registry.json` currency lifecycle — runs/owns the daily `ci_sweep`, version-pins CI tools, watches for upstream breakage/deprecation, forces re-eval on cadence, executes updates, and integrates new tech ELON surfaces into the registry. One throat to choke for "is our critical infrastructure sharp right now?"
- **Lane boundaries:** ELON = discovery/ID (what to adopt/kill). Dembe = access-intel (how to get in, bot-walls). Sterling = gate (complexity/cost/metrics/SLA). Whetstone = currency + updating + integration. Whetstone does NOT pick tools (ELON) or set the bar (Sterling) — Whetstone keeps the chosen, gated tools alive and current.
- **Voice:** maintenance-engineer precision; "green six months ago is not green now"; reports in razor-sharp status.
- **Tagline:** `Whetstone — A14 Critical Infrastructure Currency | Keeps the blades sharp`.

- [ ] **Step 2: Commit**

```bash
git add Personas/a14_whetstone_personality.md
git commit -m "feat(persona): A14 Whetstone — CI currency keeper"
```

### Task 1.4: Razor-sharp policy SO + CLAUDE.md pointer — doc artifacts

**Files:**
- Create: `standing_orders/SO_CI_RAZOR_SHARP_20260620.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Write the SO**

The SO is short and references the registry table as the policy (do NOT restate per-skill values — point to `config/ci_registry.json`). Contents:
- **⚠️ ZERO-WORKAROUND STANDARD (Commander directive 2026-06-20 — "status quo of numerous fails and workarounds is unacceptable"):** A standing workaround on a CI skill is NOT a solution — it is an unreplaced failing tool, and it is the failure state this doctrine exists to end. **The standard is zero standing CI workarounds.** Rules: (1) any workaround applied to a CI skill MUST be recorded in that registry entry as `active_workaround: {desc, since, burn_down_by}` — an undocumented workaround is a policy violation; (2) an active workaround **counts as a failure** each sweep until removed (feeds the replacement triggers — so chronic workarounds force a REPLACE); (3) Whetstone owns burn-down — root-cause fix or tool replacement, never institutionalize the workaround; (4) the goal metric is `active_workarounds == 0`, reported on the dashboard. Spot-it-fix-it applies: don't surface the workaround, kill its root cause.
- **Designation:** Critical Infrastructure = capabilities whose failure stops the Wing from operating. v1 CI skills: portal-access, web-fetch, headless-dispatch, credential-keepalive, tech-adoption.
- **Policy:** Every CI skill MUST have a registry entry with all `REQUIRED_FIELDS`. Razor-sharp = probe GREEN + within currency window + re-eval not overdue (computed by `core/ci/registry.py`).
- **Cadence:** `scripts/ci_sweep.py` runs daily (systemd timer, Task 2.2); RED/DULL pages Whetstone (owner) → escalates to Commander only if a client-affecting CI skill is RED.
- **Ownership matrix:** ELON=ID · Dembe=access · Sterling=gate/metrics · Whetstone=currency/updating/integration.
- **Adding a CI skill:** ELON nominates → Sterling gates → Whetstone adds the registry entry with probe + windows + fallback → first sweep verifies.
- **Gate interaction:** Sterling gates the *build/adoption*; scouting (ELON/Dembe) runs unfiltered (per no-gate tech-search directive).
- **⚠️ HALE CI EXECUTION AUTHORITY (Commander directive 2026-06-20):** Hale has standing authority to **immediately direct a CI refresh, revision, replacement, or implementation** — no Commander gate, no notify-and-wait. The intent: keep D2M on the cutting edge without the Commander as a bottleneck. When a CI skill goes DULL/RED/REPLACE, Hale directs the fix on the spot (Whetstone executes, ELON nominates the swap, Sterling gates complexity post-hoc). **The ONLY thing that still reaches the Commander is a financial commitment** — Hale selects and implements the tool; the Commander signs the dollar (per "Commander owns all financial commitments"). Free/self-host CI changes = Hale executes immediately, reports after. Client-send gate unaffected.

- [ ] **Step 2: Add CLAUDE.md pointer**

Add a short section under the existing HARD RULE blocks:
```markdown
## ⚠️ CRITICAL INFRASTRUCTURE (CI) — RAZOR-SHARP DOCTRINE (SO 2026-06-20)
**CI skills = capabilities whose failure stops the Wing.** v1: portal-access · web-fetch · headless-dispatch · credential-keepalive · tech-adoption. Each has a paired CI tool + registry entry in `config/ci_registry.json` (the table IS the policy). Daily `scripts/ci_sweep.py` → razor-sharp status; RED/DULL pages **Whetstone (A14)**. Owners: ELON=ID · Dembe=access · Sterling=gate · Whetstone=currency. Full SO: `standing_orders/SO_CI_RAZOR_SHARP_20260620.md`.
```

- [ ] **Step 3: Commit**

```bash
git add standing_orders/SO_CI_RAZOR_SHARP_20260620.md CLAUDE.md
git commit -m "docs(ci): razor-sharp policy SO + CLAUDE.md doctrine pointer"
```

---

## PHASE 2 — CI Health/Currency Tool (the accompanying meta CI tool)

### Task 2.1: `ci_health` engine — run probes, compute status, build dashboard

**Files:**
- Create: `core/ci/ci_health.py`
- Test: `tests/ci/test_ci_health.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/ci/test_ci_health.py
import sys
sys.path.insert(0, "/home/john/Thunderbird")
from core.ci.ci_health import run_probe, sweep

def test_run_probe_ok_on_true():
    ok, detail = run_probe("true")
    assert ok is True

def test_run_probe_fail_on_false():
    ok, detail = run_probe("false")
    assert ok is False

def test_sweep_returns_status_per_skill(monkeypatch):
    import core.ci.ci_health as h
    fake = {"skills": [
        {"id": "a", "name": "A", "ci_tool": "t", "health_probe": "true",
         "currency_window_hours": 24, "reeval_cadence_days": 30, "fallback": "f",
         "keeper": "whetstone", "last_verified": None, "last_reeval": "2026-06-20"},
    ]}
    monkeypatch.setattr(h, "load_registry", lambda *a, **k: fake)
    results = sweep(update_verified=False)
    assert results[0]["id"] == "a"
    assert results[0]["status"] in ("RAZOR_SHARP", "DULL", "RED")
    assert "probe_ok" in results[0]
```

- [ ] **Step 2: Run to verify fail**

Run: `cd /home/john/Thunderbird && python3 -m pytest tests/ci/test_ci_health.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.ci.ci_health'`

- [ ] **Step 3: Implement**

```python
# core/ci/ci_health.py
"""CI health/currency engine — the meta CI tool.
Runs each registry entry's probe, computes razor-sharp status, writes the dashboard,
optionally stamps last_verified, returns page-worthy degradations.
"""
from __future__ import annotations
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from core.ci.registry import load_registry, razor_sharp_status, DEFAULT_REGISTRY

DASHBOARD = Path("/home/john/Thunderbird/output/CI_DASHBOARD.md")
PROBE_TIMEOUT = 60


def run_probe(cmd: str) -> tuple[bool, str]:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=PROBE_TIMEOUT, cwd="/home/john/Thunderbird")
        return (r.returncode == 0, (r.stdout or r.stderr)[:200])
    except subprocess.TimeoutExpired:
        return (False, f"probe timeout {PROBE_TIMEOUT}s")
    except Exception as e:
        return (False, str(e)[:200])


def sweep(registry_path: Path = DEFAULT_REGISTRY, update_verified: bool = True) -> list[dict]:
    reg = load_registry(registry_path)
    now = datetime.now(timezone.utc)
    results = []
    for s in reg["skills"]:
        probe_ok, detail = run_probe(s["health_probe"])
        if probe_ok and update_verified:
            s["last_verified"] = now.isoformat()
        status = razor_sharp_status(s, probe_ok, now)
        results.append({"id": s["id"], "name": s["name"], "status": status,
                        "probe_ok": probe_ok, "detail": detail, "keeper": s["keeper"],
                        "ci_tool": s["ci_tool"], "fallback": s["fallback"]})
    if update_verified:
        Path(registry_path).write_text(json.dumps(reg, indent=2) + "\n")
    return results


def degradations(results: list[dict]) -> list[dict]:
    return [r for r in results if r["status"] in ("RED", "DULL")]


def write_dashboard(results: list[dict]) -> Path:
    now = datetime.now(timezone.utc).isoformat()
    lines = [f"# CI DASHBOARD — {now}", "",
             "| Skill | Status | Probe | CI Tool | Keeper |", "|---|---|---|---|---|"]
    icon = {"RAZOR_SHARP": "🟢", "DULL": "🟡", "RED": "🔴"}
    for r in results:
        lines.append(f"| {r['name']} | {icon.get(r['status'],'?')} {r['status']} | "
                     f"{'ok' if r['probe_ok'] else 'FAIL'} | `{r['ci_tool']}` | {r['keeper']} |")
    DASHBOARD.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD.write_text("\n".join(lines) + "\n")
    return DASHBOARD
```

- [ ] **Step 4: Run to verify pass**

Run: `cd /home/john/Thunderbird && python3 -m pytest tests/ci/test_ci_health.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add core/ci/ci_health.py tests/ci/test_ci_health.py
git commit -m "feat(ci): health/currency engine — probes, status, dashboard, degradations"
```

### Task 2.2: `ci_sweep.py` CLI + paging + systemd timer

**Files:**
- Create: `scripts/ci_sweep.py`

- [ ] **Step 1: Write the CLI**

```python
#!/usr/bin/env python3
"""ci_sweep.py — run the CI razor-sharp sweep, print/JSON, page on degradation.
Usage:
  python3 scripts/ci_sweep.py            # human table
  python3 scripts/ci_sweep.py --json     # machine output
  python3 scripts/ci_sweep.py --page     # page Whetstone/Commander on RED/DULL
"""
import argparse, json, sys
sys.path.insert(0, "/home/john/Thunderbird")
from core.ci.ci_health import sweep, degradations, write_dashboard

CLIENT_AFFECTING = {"portal-access", "credential-keepalive"}  # RED here → escalate to Commander


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--page", action="store_true")
    ap.add_argument("--no-update", action="store_true", help="don't stamp last_verified")
    args = ap.parse_args()

    results = sweep(update_verified=not args.no_update)
    write_dashboard(results)
    degraded = degradations(results)

    if args.json:
        print(json.dumps({"results": results, "degraded": degraded}, indent=2))
    else:
        for r in results:
            print(f"{r['status']:12s} {r['name']}  (probe {'ok' if r['probe_ok'] else 'FAIL'})")
        if degraded:
            print(f"\n⚠️ {len(degraded)} CI skill(s) not razor-sharp.")

    if args.page and degraded:
        try:
            from OpsCenter.wing_page import page  # existing pager (wing_page.py)
            client_red = [d for d in degraded if d["id"] in CLIENT_AFFECTING and d["status"] == "RED"]
            audience = "commander" if client_red else "whetstone"
            msg = "CI razor-sharp degradation:\n" + "\n".join(
                f"- {d['name']}: {d['status']} (fallback: {d['fallback']})" for d in degraded)
            page(audience, msg)
        except Exception as e:
            print(f"[page failed: {e}]", file=sys.stderr)

    return 1 if any(d["status"] == "RED" for d in degraded) else 0


if __name__ == "__main__":
    sys.exit(main())
```

> **Wrap-don't-rebuild note:** `OpsCenter/wing_page.py` is the existing pager (per memory `feedback_comms_doctrine_macro_awareness`). Confirm its function signature before wiring — adjust the `page(audience, msg)` call to match. If absent, fall back to the Telegram gateway.

- [ ] **Step 2: Smoke test**

Run: `cd /home/john/Thunderbird && python3 scripts/ci_sweep.py --no-update`
Expected: a status line per skill; non-research skills (headless-dispatch, credential-keepalive, tech-adoption) probe live; portal-access/web-fetch may show RED until Phase 3 tools land.

- [ ] **Step 3: Create systemd user timer (daily 0600 MT)**

Create `~/.config/systemd/user/ci-sweep.service` and `ci-sweep.timer` mirroring an existing timer (e.g. `portal-keepalive`). Service `ExecStart=/usr/bin/python3 /home/john/Thunderbird/scripts/ci_sweep.py --page`. Then:
```bash
systemctl --user daemon-reload && systemctl --user enable --now ci-sweep.timer
systemctl --user status ci-sweep.timer --no-pager
```
Expected: timer active.

- [ ] **Step 4: Commit**

```bash
git add scripts/ci_sweep.py
git commit -m "feat(ci): ci_sweep CLI + paging + daily timer wiring"
```

### Task 2.3: Failure/latency history + replacement-trigger engine

**Files:**
- Create: `core/ci/replacement.py`
- Modify: `core/ci/ci_health.py` (record each sweep run into history)
- Test: `tests/ci/test_replacement.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/ci/test_replacement.py
import sys
sys.path.insert(0, "/home/john/Thunderbird")
from datetime import datetime, timezone, timedelta
from core.ci.replacement import needs_replacement

NOW = datetime(2026, 6, 20, tzinfo=timezone.utc)
POLICY = {"consecutive_failures_max": 3, "rolling_window_days": 7,
          "failures_in_window_max": 5, "latency_breach_factor": 3.0,
          "latency_breach_runs_of_last_5": 3, "consecutive_timeouts_max": 2}

def _run(days_ago, ok, ms, timed_out=False):
    return {"ts": (NOW - timedelta(days=days_ago)).isoformat(), "ok": ok,
            "duration_ms": ms, "timed_out": timed_out}

def test_no_replace_when_healthy():
    hist = [_run(i, True, 1000) for i in range(5)]
    assert needs_replacement(hist, sla_ms=15000, policy=POLICY, now=NOW)[0] is False

def test_replace_on_3_consecutive_failures():
    hist = [_run(3, True, 1000), _run(2, False, 0), _run(1, False, 0), _run(0, False, 0)]
    ok, reason = needs_replacement(hist, sla_ms=15000, policy=POLICY, now=NOW)
    assert ok is True and "consecutive" in reason

def test_replace_on_rolling_failure_rate():
    # 5 non-consecutive failures within 7 days
    hist = [_run(6, False, 0), _run(5, True, 1), _run(4, False, 0), _run(3, True, 1),
            _run(2, False, 0), _run(1, False, 0), _run(0, False, 0)]
    ok, reason = needs_replacement(hist, sla_ms=15000, policy=POLICY, now=NOW)
    assert ok is True and "in 7 days" in reason

def test_replace_on_latency_spike():
    hist = [_run(0, True, 50000)]  # 50s vs 15s SLA → >3x
    ok, reason = needs_replacement(hist, sla_ms=15000, policy=POLICY, now=NOW)
    assert ok is True and "spike" in reason

def test_replace_on_sustained_latency():
    hist = [_run(4, True, 20000), _run(3, True, 1000), _run(2, True, 20000),
            _run(1, True, 1000), _run(0, True, 20000)]  # 3 of last 5 over 15s SLA
    ok, reason = needs_replacement(hist, sla_ms=15000, policy=POLICY, now=NOW)
    assert ok is True and "sustained" in reason
```

- [ ] **Step 2: Run to verify fail**

Run: `cd /home/john/Thunderbird && python3 -m pytest tests/ci/test_replacement.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.ci.replacement'`

- [ ] **Step 3: Implement**

```python
# core/ci/replacement.py
"""Replacement-trigger criteria (Commander directive 2026-06-20).
A CI tool that fails too often or runs too slow must be replaced, not just refreshed.
History entries: {"ts": iso, "ok": bool, "duration_ms": int, "timed_out": bool}.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta


def _parse(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def needs_replacement(history: list[dict], sla_ms: int, policy: dict,
                      now: datetime | None = None) -> tuple[bool, str]:
    now = now or datetime.now(timezone.utc)
    if not history:
        return (False, "no history")
    ordered = sorted(history, key=lambda h: h["ts"])
    last5 = ordered[-5:]

    # Consecutive failures (trailing)
    consec = 0
    for h in reversed(ordered):
        if not h["ok"]:
            consec += 1
        else:
            break
    if consec >= policy["consecutive_failures_max"]:
        return (True, f"{consec} consecutive failures (max {policy['consecutive_failures_max']})")

    # Consecutive timeouts (trailing)
    consec_to = 0
    for h in reversed(ordered):
        if h.get("timed_out"):
            consec_to += 1
        else:
            break
    if consec_to >= policy["consecutive_timeouts_max"]:
        return (True, f"{consec_to} consecutive timeouts (hung tool)")

    # Rolling failure rate
    cutoff = now - timedelta(days=policy["rolling_window_days"])
    win_failures = sum(1 for h in ordered if _parse(h["ts"]) > cutoff and not h["ok"])
    if win_failures >= policy["failures_in_window_max"]:
        return (True, f"{win_failures} failures in {policy['rolling_window_days']} days "
                      f"(max {policy['failures_in_window_max']})")

    # Latency spike — any single run > factor x SLA
    spike = sla_ms * policy["latency_breach_factor"]
    for h in last5:
        if h["ok"] and h["duration_ms"] > spike:
            return (True, f"latency spike {h['duration_ms']}ms > {spike:.0f}ms "
                          f"({policy['latency_breach_factor']}x SLA)")

    # Sustained latency — N of last 5 over SLA
    over = sum(1 for h in last5 if h["ok"] and h["duration_ms"] > sla_ms)
    if over >= policy["latency_breach_runs_of_last_5"]:
        return (True, f"sustained slowness — {over} of last 5 runs over {sla_ms}ms SLA")

    return (False, "within thresholds")
```

- [ ] **Step 4: Run to verify pass**

Run: `cd /home/john/Thunderbird && python3 -m pytest tests/ci/test_replacement.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Record history in the sweep + surface REPLACE status**

Modify `core/ci/ci_health.py`: append `{"ts", "ok", "duration_ms", "timed_out"}` to `config/ci_history/<skill_id>.jsonl` on each probe (time the `run_probe` call). After computing `razor_sharp_status`, also call `needs_replacement(history, sla_ms, policy, now)`; if True, override the result `status` to `"REPLACE"` and add `replace_reason`. `ci_sweep.py --page`: route `REPLACE` to **both Whetstone and ELON** (replacement nomination), with the reason string. Add `REPLACE` to the dashboard icon map (`🔁`).

```python
# in ci_health.py run_probe — time it:
import time
def run_probe(cmd: str) -> tuple[bool, str, int, bool]:
    t0 = time.monotonic()
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=PROBE_TIMEOUT, cwd="/home/john/Thunderbird")
        ms = int((time.monotonic() - t0) * 1000)
        return (r.returncode == 0, (r.stdout or r.stderr)[:200], ms, False)
    except subprocess.TimeoutExpired:
        ms = int((time.monotonic() - t0) * 1000)
        return (False, f"probe timeout {PROBE_TIMEOUT}s", ms, True)
    except Exception as e:
        ms = int((time.monotonic() - t0) * 1000)
        return (False, str(e)[:200], ms, False)
```
Update `sweep()` to unpack the 4-tuple, append history, and apply the REPLACE override. Update `tests/ci/test_ci_health.py` `run_probe` assertions to the 4-tuple shape.

**Zero-workaround enforcement:** if a skill entry has a non-null `active_workaround`, `sweep()` appends a synthetic `{"ok": False, "reason": "active_workaround"}` to that skill's history each run — so a standing workaround feeds the replacement triggers and forces a REPLACE if not burned down. The dashboard shows an `active_workarounds` count; the goal is 0.

- [ ] **Step 6: Commit**

```bash
git add core/ci/replacement.py core/ci/ci_health.py tests/ci/test_replacement.py tests/ci/test_ci_health.py
git commit -m "feat(ci): replacement-trigger engine — fail-count + undue-latency criteria"
```

---

## PHASE 3 — Research-Gated Tool Upgrades (DECISION GATE)

> **GATE STATUS: RESEARCH COMPLETE** — `intel/CI_web_stack_research_20260620.md` (Dembe, 2026-06-20). Recommendations below. **One Commander gate remains: the residential-proxy spend** (see Task 3.1 — no proxy is configured today, and the Imperva rate-limit that blocked your own IP is an IP-reputation problem no software fixes). The Trafilatura enhancer (Task 3.2) is free/self-host — no gate.

**Dembe BLUF:** The discriminating axis is bot-wall TYPE, not tool popularity. We log into D2M's *own legitimate accounts*, so a single clean residential IP likely suffices (mobile proxy = over-buy, vendor marketing). Architecture confidence HIGH; per-tool ranking MODERATE until tested on our actual portals.

### Task 3.1: Adopt portal-access CI tool — Camoufox + clean IP (⚠️ Commander spend gate)

**Recommendation (Dembe):** two-layer, self-host-first:
1. **Camoufox, headed, persistent `user_data_dir`** — for Regent this is ONE tool doing both jobs: beats Akamai fingerprint/behavioral AND keeps ASPXAUTH warm (headless keepalive is what Akamai kills). `nodriver` = light lane for Centrav/Viking. `curl_cffi` (already installed) stays for TLS-fingerprint-only walls.
2. **Clean residential proxy / stable IP** — the ONLY fix for the Imperva rate-limit.

- [ ] **Step 1 (⚠️ COMMANDER GATE — financial):** Decide the proxy path. **Fork A:** self-host Camoufox + residential proxy (~$29–99/mo, our maintenance). **Fork B:** hosted bundle — Browserbase or Steel.dev ($20–99/mo) = stealth browser + clean IP + persistent sessions in one bill, no maintenance. Commander owns this spend (no threshold). Sterling gates complexity. **Do not provision a proxy without Commander sign-off.**
- [ ] **Step 2:** Install the chosen browser tool into `.venv` (Camoufox: `pip install camoufox[geoip]`). Set `config/ci_registry.json` → `portal-access.ci_tool` to the new entrypoint; keep existing `scripts/grab_regent_cookies_cdp.py` etc. in `wraps` as the cookie-capture layer.
- [ ] **Step 3:** Write the integration sub-plan (headed launch + persistent profile, per-portal session capture, bot-wall routing by wall-type, update `scripts/portal_live_probe.py` to exercise the new path). Authored once Fork A/B is chosen. Commit registry change.

### Task 3.2: Adopt web-fetch enhancer — Trafilatura (free, no gate)

**Recommendation (Dembe):** **Trafilatura** (free, self-host, single-digit-ms, top F1 0.883) as the default clean-extract pass behind Anansi/curl for static/article pages — beats Anansi head-to-head on speed + clean text. **WATCH Jina AI Reader** as the zero-setup single-URL fallback. Neither renders JS → keep Anansi `--browser` (or Crawl4AI) for SPA pages.

- [ ] **Step 1:** `cd /home/john/Thunderbird && .venv/bin/pip install trafilatura` and verify: `.venv/bin/python3 -c "import trafilatura; print(trafilatura.__version__)"`.
- [ ] **Step 2:** Set `config/ci_registry.json` → `web-fetch.ci_tool` = `trafilatura` (primary clean-extract); Anansi remains the fetch/SPA layer + fallback. Update the `web-fetch` health probe to exercise a Trafilatura extract.
- [ ] **Step 3:** Write `docs/CI_WEB_FETCH.md` (decision + head-to-head evidence, Jina on watch) and commit registry change.

---

## PHASE 4 — Verify existing CI skills are wired (wrap, don't rebuild)

### Task 4.1: Confirm the 3 research-independent CI skills probe GREEN

- [ ] **Step 1:** Run `python3 scripts/ci_sweep.py --no-update --json` and confirm `headless-dispatch`, `credential-keepalive`, `tech-adoption` return `probe_ok: true`. 
- [ ] **Step 2:** For any that FAIL: the probe command in the registry is wrong OR the underlying asset is genuinely down. Fix the probe command to match the real asset (do NOT build a new asset). Re-run.
- [ ] **Step 3:** Commit any registry probe-command corrections.

---

## Self-Review (writing-plans checklist)

**1. Spec coverage:**
- OA commission tracker → Phase 0 ✅
- Find Playwright replacement + Anansi enhancer → Dembe agent launched + Phase 3 decision gates ✅
- Designate portal access as CI skill → registry `portal-access` + SO ✅
- Determine other CI skills → 5 skills (the 4 chosen + tech-adoption added by Commander) ✅
- Policy to keep razor-sharp → registry-as-policy + SO + daily sweep ✅
- Accompanying CI tool per skill → `ci_tool` field per entry; meta-tool = `ci_health`/`ci_sweep` ✅
- Persona for ID/access/currency → ownership matrix (ELON/Dembe/Sterling) + new Whetstone for currency ✅

**2. Placeholder scan:** The two `<PENDING-RESEARCH>` markers are intentional decision-gates (Phase 3), not lazy placeholders — they are explicitly gated on a launched research artifact and must not be filled by guessing. All code steps contain complete code.

**3. Type consistency:** `razor_sharp_status(entry, probe_ok, now)`, `load_registry(path)`, `sweep(registry_path, update_verified)`, `OATracker(ledger_path).status(as_of)` / `.page_if_crossed(as_of)` — names consistent across tasks and tests. Status vocabulary `RAZOR_SHARP|DULL|RED` consistent in registry.py, ci_health.py, ci_sweep.py, dashboard.

**Open items for Commander on review:**
- Persona name "Whetstone / A14" — adjust callsign freely.
- OA tier exact $ thresholds ($10K/$40K) are MODERATE confidence (third-party; OA's own page gates the detail). Phase 3 portal-access tool could later confirm from the OA portal directly.

---

## Execution Handoff

Phases 0, 1, 2 are research-independent and ready now. Phase 3 unblocks when the Dembe research artifact lands. Phase 4 is a verification pass.
