# Hale Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a unified `Plan`/`AssessResult` orchestrator library that gives Hale a mechanically-checkable compliance/initiative/evaluation ledger, plus a Stop-hook backstop that guarantees universal coverage without gating execution.

**Architecture:** One module (`core/ops/hale_orchestrator.py`) exposing `open_plan()` / `assess_plan()` / `close_plan()`, backed by a `PlanStore` that appends structured HTML-comment-delimited blocks to `hale_decisions.md` (never rewrites, `fcntl`-locked for the 8-instance Hale Bus). A Stop hook (`.claude/hooks/hale_orchestrator_backstop.py`) scans for orphaned/missing plans each turn and auto-files them so nothing silently escapes the log.

**Tech Stack:** Python 3.13 stdlib only (`dataclasses`, `fcntl`, `re`, `secrets`, `logging`) — no new dependencies. Tests via `pytest` (already installed, v9.0.3). Existing convention: tests live beside the module as `test_*.py`, not in a separate `tests/` tree (see `core/ops/*.py`, `core/test_schemas.py`).

**Companion spec:** `docs/superpowers/specs/2026-07-09-hale-orchestrator-design.md`

**Existing pattern reused, not duplicated:** `hale_decisions.md` already has a `###`-header prose format read by `core/ops/hale_decision_log.py`'s regex (`### YYYY-MM-DD HH:MM:SS — title`). The new `<!-- PLAN:OPEN ... -->` / `<!-- PLAN:CLOSE ... -->` blocks use HTML comments specifically so they never collide with that existing `###`-based parser — both readers coexist in the same file safely.

---

### Task 1: Core dataclasses

**Files:**
- Create: `core/ops/hale_orchestrator.py`
- Test: `core/ops/test_hale_orchestrator.py`

- [ ] **Step 1: Write the failing test**

```python
# core/ops/test_hale_orchestrator.py
from core.ops.hale_orchestrator import Plan, AssessResult


def test_plan_defaults():
    plan = Plan(plan_id="PLN-abc123", task_summary="test task")
    assert plan.tier == "trivial"
    assert plan.status == "open"
    assert plan.degraded is False
    assert plan.criteria == []
    assert plan.session_id is None


def test_assess_result_defaults():
    result = AssessResult(plan_id="PLN-abc123")
    assert result.verdict == "PASS"
    assert result.quality_tier is None
    assert result.criteria_met == []
    assert result.degraded is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/john/Thunderbird && .venv/bin/pytest core/ops/test_hale_orchestrator.py -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError: cannot import name 'Plan'`

- [ ] **Step 3: Write minimal implementation**

```python
# core/ops/hale_orchestrator.py
"""
Hale Orchestrator — unified plan/compliance/initiative/evaluation ledger.

Generalizes the assess/verify contract from core/ci/repairs/schema.py and the
structured-input/durable-log shape from core/ops/three_voice_arbitration.py
into Hale's own operating loop. Never blocks or gates execution — this is a
ledger, not a runtime supervisor. See docs/superpowers/specs/2026-07-09-hale-orchestrator-design.md.
"""
from __future__ import annotations

import logging
import secrets
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path("/home/john/Thunderbird")
HALE_DECISIONS = ROOT / "hale_decisions.md"
ERROR_LOG = ROOT / "logs" / "hale_orchestrator_errors.log"

ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("hale_orchestrator")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _h = logging.FileHandler(ERROR_LOG)
    _h.setFormatter(logging.Formatter("%(asctime)s [ORCHESTRATOR] %(levelname)s: %(message)s"))
    logger.addHandler(_h)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_plan_id() -> str:
    return f"PLN-{secrets.token_hex(3)}"


_DEFAULT_CRITERIA = [
    "no Commander gate crossed without authorization",
    "every file/action claimed as done is independently verifiable",
    "no unhandled exception",
]


@dataclass
class Plan:
    plan_id: str
    task_summary: str
    tier: str = "trivial"
    opened_at: str = field(default_factory=_now_iso)
    session_id: Optional[str] = None
    compliance_checks: list[str] = field(default_factory=list)
    initiative_notes: list[str] = field(default_factory=list)
    criteria: list[str] = field(default_factory=list)
    status: str = "open"
    degraded: bool = False


@dataclass
class AssessResult:
    plan_id: str
    verdict: str = "PASS"
    quality_tier: Optional[str] = None
    criteria_met: list[str] = field(default_factory=list)
    criteria_missed: list[str] = field(default_factory=list)
    criteria_unverified: list[str] = field(default_factory=list)
    notes: str = ""
    closed_at: str = field(default_factory=_now_iso)
    degraded: bool = False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/john/Thunderbird && .venv/bin/pytest core/ops/test_hale_orchestrator.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
cd /home/john/Thunderbird
git add core/ops/hale_orchestrator.py core/ops/test_hale_orchestrator.py
git commit -m "feat: Hale orchestrator — core Plan/AssessResult dataclasses"
```

---

### Task 2: PlanStore — durable, locked append + orphan/coverage queries

**Files:**
- Modify: `core/ops/hale_orchestrator.py` (append `PlanStore` class)
- Test: `core/ops/test_hale_orchestrator.py` (append tests)

- [ ] **Step 1: Write the failing test**

```python
# append to core/ops/test_hale_orchestrator.py
import re
import threading
from core.ops.hale_orchestrator import Plan, AssessResult, PlanStore


def test_write_open_and_close_roundtrip(tmp_path):
    p = tmp_path / "decisions.md"
    p.write_text("# existing prose\n\n### 2026-07-01 10:00:00 — some old decision\n**Decision:** did a thing\n")

    plan = Plan(plan_id="PLN-111111", task_summary="do a thing", session_id="sess-A",
                criteria=["c1", "c2"])
    PlanStore.write_open(plan, path=p)

    result = AssessResult(plan_id="PLN-111111", verdict="PASS", criteria_met=["c1", "c2"])
    PlanStore.write_close(result, path=p)

    text = p.read_text()
    assert "<!-- PLAN:OPEN plan_id=PLN-111111" in text
    assert "<!-- PLAN:CLOSE plan_id=PLN-111111 verdict=PASS" in text
    # old prose format untouched
    assert "### 2026-07-01 10:00:00 — some old decision" in text


def test_find_orphaned_opens(tmp_path):
    p = tmp_path / "decisions.md"
    plan_a = Plan(plan_id="PLN-aaaaaa", task_summary="a", session_id="sess-A")
    plan_b = Plan(plan_id="PLN-bbbbbb", task_summary="b", session_id="sess-A")
    PlanStore.write_open(plan_a, path=p)
    PlanStore.write_open(plan_b, path=p)
    PlanStore.write_close(AssessResult(plan_id="PLN-aaaaaa", verdict="PASS"), path=p)

    orphaned = PlanStore.find_orphaned_opens("sess-A", path=p)
    assert len(orphaned) == 1
    assert orphaned[0]["plan_id"] == "PLN-bbbbbb"


def test_session_has_any_plan(tmp_path):
    p = tmp_path / "decisions.md"
    assert PlanStore.session_has_any_plan("sess-Z", path=p) is False
    PlanStore.write_open(Plan(plan_id="PLN-cccccc", task_summary="c", session_id="sess-Z"), path=p)
    assert PlanStore.session_has_any_plan("sess-Z", path=p) is True


def test_concurrent_appends_do_not_corrupt(tmp_path):
    p = tmp_path / "decisions.md"
    p.write_text("")

    def worker(i):
        PlanStore.write_open(Plan(plan_id=f"PLN-{i:06d}", task_summary=f"task {i}",
                                   session_id="sess-concurrent"), path=p)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    text = p.read_text()
    opened_ids = set(re.findall(r"plan_id=(PLN-\d{6})", text))
    assert len(opened_ids) == 20  # every write landed, none clobbered another
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/john/Thunderbird && .venv/bin/pytest core/ops/test_hale_orchestrator.py -v`
Expected: FAIL with `ImportError: cannot import name 'PlanStore'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to core/ops/hale_orchestrator.py
import fcntl
import os
import re


class PlanStore:
    """Reads/writes structured HTML-comment-delimited blocks in hale_decisions.md.
    Pure append-only — never rewrites the file. fcntl-locked so the 8 concurrent
    Hale instantiations (Hale Bus doctrine) never interleave writes."""

    OPEN_RE = re.compile(
        r"<!-- PLAN:OPEN plan_id=(?P<plan_id>\S+) tier=(?P<tier>\S+) "
        r"session_id=(?P<session_id>\S+) opened_at=(?P<opened_at>\S+) -->"
    )
    CLOSE_RE = re.compile(
        r"<!-- PLAN:CLOSE plan_id=(?P<plan_id>\S+) verdict=(?P<verdict>\S+) "
        r"quality_tier=(?P<quality_tier>\S+) closed_at=(?P<closed_at>\S+) -->"
    )

    @staticmethod
    def _append(text: str, path: Optional[Path] = None) -> None:
        target = path or HALE_DECISIONS
        with open(target, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(text)
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def write_open(plan: Plan, path: Optional[Path] = None) -> None:
        sid = plan.session_id or "none"
        block = (
            f"\n<!-- PLAN:OPEN plan_id={plan.plan_id} tier={plan.tier} "
            f"session_id={sid} opened_at={plan.opened_at} -->\n"
            f"**Plan Opened:** {plan.plan_id}\n"
            f"**Task:** {plan.task_summary}\n"
            f"**Tier:** {plan.tier}\n"
            f"**Compliance checks:** {'; '.join(plan.compliance_checks) or 'none'}\n"
            f"**Criteria:** {'; '.join(plan.criteria) or 'none'}\n"
            f"<!-- /PLAN:OPEN -->\n"
        )
        PlanStore._append(block, path=path)

    @staticmethod
    def write_close(result: AssessResult, path: Optional[Path] = None) -> None:
        qt = result.quality_tier or "none"
        block = (
            f"\n<!-- PLAN:CLOSE plan_id={result.plan_id} verdict={result.verdict} "
            f"quality_tier={qt} closed_at={result.closed_at} -->\n"
            f"**Plan Closed:** {result.plan_id}\n"
            f"**Verdict:** {result.verdict}\n"
            f"**Quality tier:** {qt}\n"
            f"**Criteria met:** {'; '.join(result.criteria_met) or 'none'}\n"
            f"**Criteria missed:** {'; '.join(result.criteria_missed) or 'none'}\n"
            f"**Criteria unverified:** {'; '.join(result.criteria_unverified) or 'none'}\n"
            f"**Notes:** {result.notes or 'none'}\n"
            f"<!-- /PLAN:CLOSE -->\n"
        )
        PlanStore._append(block, path=path)

    @staticmethod
    def _read(path: Optional[Path] = None) -> str:
        target = path or HALE_DECISIONS
        return target.read_text(errors="ignore") if target.exists() else ""

    @staticmethod
    def find_orphaned_opens(session_id: str, text: Optional[str] = None,
                             path: Optional[Path] = None) -> list[dict]:
        if text is None:
            text = PlanStore._read(path)
        opens = {
            m.group("plan_id"): m.groupdict()
            for m in PlanStore.OPEN_RE.finditer(text)
            if m.group("session_id") == session_id
        }
        closed_ids = {m.group("plan_id") for m in PlanStore.CLOSE_RE.finditer(text)}
        return [v for pid, v in opens.items() if pid not in closed_ids]

    @staticmethod
    def session_has_any_plan(session_id: str, text: Optional[str] = None,
                              path: Optional[Path] = None) -> bool:
        if text is None:
            text = PlanStore._read(path)
        return any(
            m.group("session_id") == session_id for m in PlanStore.OPEN_RE.finditer(text)
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/john/Thunderbird && .venv/bin/pytest core/ops/test_hale_orchestrator.py -v`
Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
cd /home/john/Thunderbird
git add core/ops/hale_orchestrator.py core/ops/test_hale_orchestrator.py
git commit -m "feat: Hale orchestrator — PlanStore locked append + orphan queries"
```

---

### Task 3: `open_plan()` — auto-derived criteria, tier pass-through, degrade-safe

**Files:**
- Modify: `core/ops/hale_orchestrator.py`
- Test: `core/ops/test_hale_orchestrator.py`

- [ ] **Step 1: Write the failing test**

```python
# append to core/ops/test_hale_orchestrator.py
from core.ops.hale_orchestrator import open_plan, _DEFAULT_CRITERIA
import core.ops.hale_orchestrator as ho_module


def test_open_plan_auto_derives_criteria(tmp_path, monkeypatch):
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")
    plan = open_plan("read a file")
    assert plan.criteria == _DEFAULT_CRITERIA
    assert plan.tier == "trivial"
    assert (tmp_path / "decisions.md").read_text().count("PLAN:OPEN") == 1


def test_open_plan_explicit_criteria_pass_through(tmp_path, monkeypatch):
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")
    plan = open_plan("big task", criteria=["custom criterion"])
    assert plan.criteria == ["custom criterion"]


def test_open_plan_t2_folds_in_prompt_charter(tmp_path, monkeypatch):
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")
    charter = {"success_criteria": "ship the thing", "scope_in": "backend only"}
    plan = open_plan("T2 task", tier="T2", prompt_charter=charter)
    assert any("success_criteria: ship the thing" in c for c in plan.compliance_checks)
    assert any("scope_in: backend only" in c for c in plan.compliance_checks)


def test_open_plan_degrades_gracefully_on_write_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")

    def _boom(*a, **kw):
        raise OSError("disk full")

    monkeypatch.setattr(ho_module.PlanStore, "write_open", staticmethod(_boom))
    plan = open_plan("will fail to persist")
    assert plan.degraded is True
    assert plan.plan_id.startswith("PLN-")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/john/Thunderbird && .venv/bin/pytest core/ops/test_hale_orchestrator.py -v`
Expected: FAIL with `ImportError: cannot import name 'open_plan'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to core/ops/hale_orchestrator.py

def open_plan(
    task_summary: str,
    tier: str = "trivial",
    criteria: Optional[list[str]] = None,
    compliance_checks: Optional[list[str]] = None,
    prompt_charter: Optional[dict] = None,
    session_id: Optional[str] = None,
) -> Plan:
    """Open a new Plan. criteria/compliance_checks default to the cheap
    auto-derived floor for trivial work; pass explicit values for T1+ tasks.
    prompt_charter (for tier T2/T3) is the caller-supplied Wing Exercise
    Prompt Charter dict — its fields fold into compliance_checks rather than
    being scraped automatically, since no single machine-readable charter
    store exists yet."""
    plan_id = _new_plan_id()
    try:
        resolved_criteria = list(criteria) if criteria else list(_DEFAULT_CRITERIA)
        resolved_checks = list(compliance_checks) if compliance_checks else []

        if tier in ("T2", "T3") and prompt_charter:
            for key in ("success_criteria", "scope_in", "scope_out", "named_staff", "exit_condition"):
                val = prompt_charter.get(key)
                if val:
                    resolved_checks.append(f"{key}: {val}")

        plan = Plan(
            plan_id=plan_id,
            task_summary=task_summary,
            tier=tier,
            session_id=session_id,
            compliance_checks=resolved_checks,
            criteria=resolved_criteria,
        )
        PlanStore.write_open(plan)
        return plan
    except Exception as exc:
        logger.error("open_plan failed: %s\n%s", exc, traceback.format_exc())
        return Plan(plan_id=plan_id, task_summary=task_summary, tier=tier,
                     session_id=session_id, degraded=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/john/Thunderbird && .venv/bin/pytest core/ops/test_hale_orchestrator.py -v`
Expected: `10 passed`

- [ ] **Step 5: Commit**

```bash
cd /home/john/Thunderbird
git add core/ops/hale_orchestrator.py core/ops/test_hale_orchestrator.py
git commit -m "feat: Hale orchestrator — open_plan with auto-derived criteria"
```

---

### Task 4: `assess_plan()` — three-branch verdict/quality-tier logic

**Files:**
- Modify: `core/ops/hale_orchestrator.py`
- Test: `core/ops/test_hale_orchestrator.py`

- [ ] **Step 1: Write the failing test**

```python
# append to core/ops/test_hale_orchestrator.py
from core.ops.hale_orchestrator import assess_plan


def test_assess_all_met_is_pass_trivial_no_tier():
    plan = Plan(plan_id="PLN-1", task_summary="t", tier="trivial", criteria=["c1", "c2"])
    result = assess_plan(plan, {"c1": "met", "c2": "met"})
    assert result.verdict == "PASS"
    assert result.quality_tier is None
    assert result.criteria_met == ["c1", "c2"]


def test_assess_any_missed_is_fail():
    plan = Plan(plan_id="PLN-2", task_summary="t", tier="T1", criteria=["c1", "c2"])
    result = assess_plan(plan, {"c1": "met", "c2": "missed"})
    assert result.verdict == "FAIL"
    assert result.quality_tier == "RED"
    assert result.criteria_missed == ["c2"]


def test_assess_only_unverified_is_pass_yellow_cap():
    plan = Plan(plan_id="PLN-3", task_summary="t", tier="T1", criteria=["c1", "c2"])
    result = assess_plan(plan, {"c1": "met", "c2": "unverified"})
    assert result.verdict == "PASS"
    assert result.quality_tier == "YELLOW"
    assert result.criteria_unverified == ["c2"]


def test_assess_missing_criterion_key_defaults_unverified():
    plan = Plan(plan_id="PLN-4", task_summary="t", tier="T2", criteria=["c1"])
    result = assess_plan(plan, {})
    assert result.criteria_unverified == ["c1"]
    assert result.verdict == "PASS"


def test_assess_all_met_nontrivial_is_green():
    plan = Plan(plan_id="PLN-5", task_summary="t", tier="T3", criteria=["c1"])
    result = assess_plan(plan, {"c1": "met"})
    assert result.quality_tier == "GREEN"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/john/Thunderbird && .venv/bin/pytest core/ops/test_hale_orchestrator.py -v`
Expected: FAIL with `ImportError: cannot import name 'assess_plan'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to core/ops/hale_orchestrator.py

def assess_plan(plan: Plan, criteria_status: dict[str, str], notes: str = "") -> AssessResult:
    """criteria_status maps each string in plan.criteria to 'met' | 'missed' |
    'unverified'. Any criterion absent from criteria_status defaults to
    'unverified' — never a silent 'met'. verdict is FAIL only on a real
    'missed'; 'unverified' alone caps quality_tier at YELLOW but never forces
    a hard FAIL (see design doc Error Handling section)."""
    try:
        met, missed, unverified = [], [], []
        for c in plan.criteria:
            state = criteria_status.get(c, "unverified")
            if state == "met":
                met.append(c)
            elif state == "missed":
                missed.append(c)
            else:
                unverified.append(c)

        verdict = "FAIL" if missed else "PASS"

        quality_tier = None
        if plan.tier != "trivial":
            if missed:
                quality_tier = "RED"
            elif unverified:
                quality_tier = "YELLOW"
            else:
                quality_tier = "GREEN"

        return AssessResult(
            plan_id=plan.plan_id,
            verdict=verdict,
            quality_tier=quality_tier,
            criteria_met=met,
            criteria_missed=missed,
            criteria_unverified=unverified,
            notes=notes,
        )
    except Exception as exc:
        logger.error("assess_plan failed: %s\n%s", exc, traceback.format_exc())
        return AssessResult(plan_id=plan.plan_id, verdict="FAIL",
                             notes="orchestrator error during assessment", degraded=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/john/Thunderbird && .venv/bin/pytest core/ops/test_hale_orchestrator.py -v`
Expected: `15 passed`

- [ ] **Step 5: Commit**

```bash
cd /home/john/Thunderbird
git add core/ops/hale_orchestrator.py core/ops/test_hale_orchestrator.py
git commit -m "feat: Hale orchestrator — assess_plan verdict/quality-tier logic"
```

---

### Task 5: `close_plan()` — final write, degrade-safe

**Files:**
- Modify: `core/ops/hale_orchestrator.py`
- Test: `core/ops/test_hale_orchestrator.py`

- [ ] **Step 1: Write the failing test**

```python
# append to core/ops/test_hale_orchestrator.py
from core.ops.hale_orchestrator import close_plan


def test_close_plan_writes_and_returns_true(tmp_path, monkeypatch):
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")
    result = AssessResult(plan_id="PLN-close1", verdict="PASS")
    ok = close_plan(result)
    assert ok is True
    assert "PLN-close1" in (tmp_path / "decisions.md").read_text()


def test_close_plan_degrades_gracefully_on_write_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")

    def _boom(*a, **kw):
        raise OSError("disk full")

    monkeypatch.setattr(ho_module.PlanStore, "write_close", staticmethod(_boom))
    result = AssessResult(plan_id="PLN-close2", verdict="PASS")
    ok = close_plan(result)
    assert ok is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/john/Thunderbird && .venv/bin/pytest core/ops/test_hale_orchestrator.py -v`
Expected: FAIL with `ImportError: cannot import name 'close_plan'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to core/ops/hale_orchestrator.py

def close_plan(result: AssessResult) -> bool:
    """Writes the CLOSED block. Returns False (never raises) if the write
    itself fails — the caller's actual task is already done by this point,
    so a ledger-write failure must never look like a task failure."""
    try:
        PlanStore.write_close(result)
        return True
    except Exception as exc:
        logger.error("close_plan failed: %s\n%s", exc, traceback.format_exc())
        return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/john/Thunderbird && .venv/bin/pytest core/ops/test_hale_orchestrator.py -v`
Expected: `17 passed`

- [ ] **Step 5: Commit**

```bash
cd /home/john/Thunderbird
git add core/ops/hale_orchestrator.py core/ops/test_hale_orchestrator.py
git commit -m "feat: Hale orchestrator — close_plan"
```

---

### Task 6: Stop-hook backstop — universal coverage

**Files:**
- Create: `.claude/hooks/hale_orchestrator_backstop.py`
- Test: `core/ops/test_hale_orchestrator_backstop.py`

- [ ] **Step 1: Write the failing test**

```python
# core/ops/test_hale_orchestrator_backstop.py
import json
import os
import subprocess
import sys

HOOK = "/home/john/Thunderbird/.claude/hooks/hale_orchestrator_backstop.py"


def _run_hook(stdin_payload: dict, decisions_path) -> str:
    env = os.environ.copy()
    env["HALE_ORCHESTRATOR_DECISIONS_PATH"] = str(decisions_path)
    proc = subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps(stdin_payload),
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.stdout + proc.stderr


def test_backstop_closes_orphaned_plan(tmp_path):
    decisions = tmp_path / "decisions.md"
    from core.ops.hale_orchestrator import Plan, PlanStore
    PlanStore.write_open(Plan(plan_id="PLN-orphan1", task_summary="x",
                               session_id="sess-hook-1"), path=decisions)

    _run_hook({"session_id": "sess-hook-1", "transcript_path": ""}, decisions)

    text = decisions.read_text()
    assert "<!-- PLAN:CLOSE plan_id=PLN-orphan1 verdict=FAIL" in text
    assert "never reached assessment" in text


def test_backstop_files_default_plan_when_transcript_has_tool_use(tmp_path):
    decisions = tmp_path / "decisions.md"
    decisions.write_text("")
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text('{"type": "tool_use", "name": "Read"}\n')

    _run_hook({"session_id": "sess-hook-2", "transcript_path": str(transcript)}, decisions)

    text = decisions.read_text()
    assert "<!-- PLAN:OPEN" in text
    assert "session_id=sess-hook-2" in text
    assert "<!-- PLAN:CLOSE" in text
    assert "verdict=PASS" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/john/Thunderbird && .venv/bin/pytest core/ops/test_hale_orchestrator_backstop.py -v`
Expected: FAIL — hook file doesn't exist yet (`FileNotFoundError` / non-zero exit)

- [ ] **Step 3: Add a test-only path override to the orchestrator**

The hook needs a way to point at a scratch file during tests without touching the real `hale_decisions.md`. Add an environment-variable override, checked once at import time:

```python
# modify core/ops/hale_orchestrator.py — replace the line:
#   HALE_DECISIONS = ROOT / "hale_decisions.md"
# with:
import os as _os
HALE_DECISIONS = Path(_os.environ.get("HALE_ORCHESTRATOR_DECISIONS_PATH", str(ROOT / "hale_decisions.md")))
```

- [ ] **Step 4: Write the hook implementation**

```python
#!/usr/bin/env python3
"""
Hale Orchestrator — Stop hook backstop.

Fires on every Stop event. Guarantees universal Plan coverage without ever
blocking session end:
  1. Any OPEN plan for this session with no matching CLOSE -> auto-closed
     FAIL, notes="never reached assessment" (an abandoned plan is real
     signal, not something to hide).
  2. If this session has zero Plan entries at all but the transcript shows
     tool activity -> auto-files a trivial default Plan, closed PASS with
     all default criteria marked unverified (the hook cannot mechanically
     check them — see design doc Error Handling).

All exceptions are caught and logged; this script always exits 0.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/john/Thunderbird")

from core.ops.hale_orchestrator import (  # noqa: E402
    Plan,
    AssessResult,
    PlanStore,
    _new_plan_id,
    _DEFAULT_CRITERIA,
    logger,
)


def _transcript_has_tool_use(transcript_path: str) -> bool:
    try:
        p = Path(transcript_path)
        if not transcript_path or not p.exists():
            return False
        with open(p, errors="ignore") as f:
            for line in f:
                if '"type": "tool_use"' in line or '"type":"tool_use"' in line:
                    return True
    except Exception:
        pass
    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception as exc:
        logger.error("backstop: failed to parse stdin: %s", exc)
        return 0

    session_id = payload.get("session_id") or "unknown"
    transcript_path = payload.get("transcript_path", "")

    try:
        orphaned = PlanStore.find_orphaned_opens(session_id)
        for o in orphaned:
            PlanStore.write_close(AssessResult(
                plan_id=o["plan_id"],
                verdict="FAIL",
                notes="never reached assessment",
            ))

        if not PlanStore.session_has_any_plan(session_id) and _transcript_has_tool_use(transcript_path):
            plan = Plan(
                plan_id=_new_plan_id(),
                task_summary="auto-filed: turn had tool activity with no explicit Plan",
                tier="trivial",
                session_id=session_id,
                criteria=list(_DEFAULT_CRITERIA),
            )
            PlanStore.write_open(plan)
            PlanStore.write_close(AssessResult(
                plan_id=plan.plan_id,
                verdict="PASS",
                criteria_unverified=list(_DEFAULT_CRITERIA),
                notes="auto-filed by backstop hook — criteria not mechanically checked",
            ))
    except Exception as exc:
        logger.error("backstop: unexpected failure: %s", exc)

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

```bash
chmod +x /home/john/Thunderbird/.claude/hooks/hale_orchestrator_backstop.py
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /home/john/Thunderbird && .venv/bin/pytest core/ops/test_hale_orchestrator_backstop.py -v`
Expected: `2 passed`

- [ ] **Step 6: Run the full suite to confirm no regressions**

Run: `cd /home/john/Thunderbird && .venv/bin/pytest core/ops/test_hale_orchestrator.py core/ops/test_hale_orchestrator_backstop.py -v`
Expected: `19 passed`

- [ ] **Step 7: Commit**

```bash
cd /home/john/Thunderbird
git add core/ops/hale_orchestrator.py .claude/hooks/hale_orchestrator_backstop.py core/ops/test_hale_orchestrator_backstop.py
git commit -m "feat: Hale orchestrator — Stop-hook backstop for universal Plan coverage"
```

---

### Task 7: Register the backstop hook

**Files:**
- Modify: `.claude/settings.local.json`

- [ ] **Step 1: Read the current file to get exact current content**

Run: `cat /home/john/Thunderbird/.claude/settings.local.json`

- [ ] **Step 2: Append the new hook to the existing `"Stop"` array**

Add this object to the `"Stop"` array (alongside the existing `session-end-sync.sh` entry — do not remove it):

```json
    {
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "python3 /home/john/Thunderbird/.claude/hooks/hale_orchestrator_backstop.py"
        }
      ]
    }
```

Use the Edit tool (not manual retyping) to insert this as a new array element after the existing `session-end-sync.sh` entry inside `"Stop": [ ... ]`.

- [ ] **Step 3: Validate the JSON is still well-formed**

Run: `python3 -c "import json; json.load(open('/home/john/Thunderbird/.claude/settings.local.json'))" && echo OK`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd /home/john/Thunderbird
git add .claude/settings.local.json
git commit -m "chore: register Hale orchestrator backstop as a Stop hook"
```

---

### Task 8: Integration test + live verification

**Files:**
- Test: `core/ops/test_hale_orchestrator_integration.py`

- [ ] **Step 1: Write the integration test**

```python
# core/ops/test_hale_orchestrator_integration.py
from core.ops.hale_orchestrator import open_plan, assess_plan, close_plan
import core.ops.hale_orchestrator as ho_module


def test_full_lifecycle_trivial_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")

    plan = open_plan("read a config file")
    result = assess_plan(plan, {c: "met" for c in plan.criteria})
    ok = close_plan(result)

    assert ok is True
    text = (tmp_path / "decisions.md").read_text()
    assert f"plan_id={plan.plan_id}" in text
    assert "PLAN:OPEN" in text and "PLAN:CLOSE" in text
    assert text.index("PLAN:OPEN") < text.index("PLAN:CLOSE")


def test_full_lifecycle_t1_plan_with_missed_criterion(tmp_path, monkeypatch):
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")

    plan = open_plan("ship a feature", tier="T1", criteria=["tests pass", "no gate crossed"])
    result = assess_plan(plan, {"tests pass": "missed", "no gate crossed": "met"})
    close_plan(result)

    assert result.verdict == "FAIL"
    assert result.quality_tier == "RED"
    text = (tmp_path / "decisions.md").read_text()
    assert "verdict=FAIL" in text
```

- [ ] **Step 2: Run the test**

Run: `cd /home/john/Thunderbird && .venv/bin/pytest core/ops/test_hale_orchestrator_integration.py -v`
Expected: `2 passed`

- [ ] **Step 3: Live verification against the real file (manual, one-time — not part of the automated suite)**

```bash
cd /home/john/Thunderbird
.venv/bin/python3 -c "
from core.ops.hale_orchestrator import open_plan, assess_plan, close_plan
plan = open_plan('live verification test — safe to leave in hale_decisions.md')
result = assess_plan(plan, {c: 'met' for c in plan.criteria})
close_plan(result)
print(plan.plan_id)
"
```

Then read the real file directly (not the function's return value) to confirm the blocks actually landed:

```bash
grep -A3 "PLAN:OPEN" /home/john/Thunderbird/hale_decisions.md | tail -10
grep -A3 "PLAN:CLOSE" /home/john/Thunderbird/hale_decisions.md | tail -10
```

Expected: both an OPEN and a CLOSE block for the plan_id printed above, visible in the real file.

- [ ] **Step 4: Run the complete test suite one final time**

Run: `cd /home/john/Thunderbird && .venv/bin/pytest core/ops/test_hale_orchestrator.py core/ops/test_hale_orchestrator_backstop.py core/ops/test_hale_orchestrator_integration.py -v`
Expected: `21 passed`

- [ ] **Step 5: Commit**

```bash
cd /home/john/Thunderbird
git add core/ops/test_hale_orchestrator_integration.py
git commit -m "test: Hale orchestrator — end-to-end integration coverage"
```

---

### Task 9: Cross-engine universal backstop (systemd timer, engine-agnostic)

**Added mid-execution per Commander directive:** "Hale orchestrator should apply to all Hale's especially Claude Code && Open Code." Investigation confirmed `opencode.json` has no `hook`/`lifecycle`/`plugin` key — OpenCode has no native equivalent to Claude Code's Stop hook. The Task 6/7 backstop only fires for Claude Code sessions. This task adds an engine-agnostic timer that catches orphaned plans regardless of which engine (or neither, in a hard crash) created them.

**Files:**
- Create: `scripts/hale_orchestrator_timer_sweep.py`
- Create: `~/.config/systemd/user/hale-orchestrator-sweep.service`
- Create: `~/.config/systemd/user/hale-orchestrator-sweep.timer`
- Test: `core/ops/test_hale_orchestrator_timer_sweep.py`

- [ ] **Step 1: Write the failing test**

```python
# core/ops/test_hale_orchestrator_timer_sweep.py
from scripts.hale_orchestrator_timer_sweep import sweep_all_orphans
from core.ops.hale_orchestrator import Plan, AssessResult, PlanStore


def test_sweep_closes_orphans_across_multiple_sessions(tmp_path):
    p = tmp_path / "decisions.md"
    PlanStore.write_open(Plan(plan_id="PLN-cc0001", task_summary="claude code task",
                               session_id="cc-session-1"), path=p)
    PlanStore.write_open(Plan(plan_id="PLN-oc0001", task_summary="opencode task",
                               session_id="oc-session-1"), path=p)
    PlanStore.write_close(AssessResult(plan_id="PLN-cc0001", verdict="PASS"), path=p)
    # PLN-oc0001 left open — simulates OpenCode (no Stop-hook backstop) or a crash

    closed = sweep_all_orphans(path=p, min_age_seconds=0)

    assert closed == ["PLN-oc0001"]
    text = p.read_text()
    assert "<!-- PLAN:CLOSE plan_id=PLN-oc0001 verdict=FAIL" in text
    assert "never reached assessment (timer sweep)" in text


def test_sweep_ignores_recently_opened_plans(tmp_path):
    p = tmp_path / "decisions.md"
    PlanStore.write_open(Plan(plan_id="PLN-fresh1", task_summary="still running",
                               session_id="sess-live"), path=p)

    closed = sweep_all_orphans(path=p, min_age_seconds=3600)

    assert closed == []
    assert "<!-- PLAN:CLOSE plan_id=PLN-fresh1" not in p.read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/john/Thunderbird/.claude/worktrees/hale-orchestrator && /home/john/Thunderbird/.venv/bin/pytest core/ops/test_hale_orchestrator_timer_sweep.py -v`
Expected: FAIL — `scripts/hale_orchestrator_timer_sweep.py` doesn't exist yet

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
"""
Hale Orchestrator — cross-engine universal backstop.

Runs on a systemd --user timer, independent of any single engine's session
lifecycle. Catches orphaned Plan blocks in hale_decisions.md regardless of
which engine created them (Claude Code, OpenCode, or any future engine) —
including crashes where no Stop hook fires at all. Complements (does not
replace) the Task 6 per-session Stop-hook backstop, which still closes
orphans faster for Claude Code specifically.
"""
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, "/home/john/Thunderbird")

from core.ops.hale_orchestrator import (  # noqa: E402
    AssessResult,
    PlanStore,
    HALE_DECISIONS,
    logger,
)

_ALL_OPENS_RE = re.compile(
    r"<!-- PLAN:OPEN plan_id=(?P<plan_id>\S+) tier=(?P<tier>\S+) "
    r"session_id=(?P<session_id>\S+) opened_at=(?P<opened_at>\S+) -->"
)


def _age_seconds(opened_at: str) -> float:
    try:
        opened = datetime.fromisoformat(opened_at)
        if opened.tzinfo is None:
            opened = opened.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - opened).total_seconds()
    except Exception:
        return float("inf")  # unparseable timestamp -> treat as old enough to sweep


def sweep_all_orphans(path: Optional[Path] = None, min_age_seconds: int = 900) -> list[str]:
    """Closes every OPEN plan (any session, any engine) older than
    min_age_seconds with no matching CLOSE, as FAIL. Returns the list of
    plan_ids closed. Default 900s (15 min) avoids racing a plan that's
    still legitimately in progress."""
    target = path or HALE_DECISIONS
    text = target.read_text(errors="ignore") if target.exists() else ""

    all_opens = {m.group("plan_id"): m.groupdict() for m in _ALL_OPENS_RE.finditer(text)}
    closed_ids = {m.group("plan_id") for m in PlanStore.CLOSE_RE.finditer(text)}

    closed_now = []
    for plan_id, fields in all_opens.items():
        if plan_id in closed_ids:
            continue
        if _age_seconds(fields["opened_at"]) < min_age_seconds:
            continue
        PlanStore.write_close(AssessResult(
            plan_id=plan_id,
            verdict="FAIL",
            notes="never reached assessment (timer sweep)",
        ), path=path)
        closed_now.append(plan_id)

    return closed_now


def main() -> int:
    try:
        closed = sweep_all_orphans()
        if closed:
            logger.info("timer sweep closed %d orphaned plan(s): %s", len(closed), closed)
    except Exception as exc:
        logger.error("timer sweep failed: %s", exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/john/Thunderbird/.claude/worktrees/hale-orchestrator && /home/john/Thunderbird/.venv/bin/pytest core/ops/test_hale_orchestrator_timer_sweep.py -v`
Expected: `2 passed`

- [ ] **Step 5: Create the systemd unit files**

```ini
# ~/.config/systemd/user/hale-orchestrator-sweep.service
[Unit]
Description=Hale Orchestrator — cross-engine orphan sweep

[Service]
Type=oneshot
ExecStart=/home/john/Thunderbird/.venv/bin/python3 /home/john/Thunderbird/scripts/hale_orchestrator_timer_sweep.py
```

```ini
# ~/.config/systemd/user/hale-orchestrator-sweep.timer
[Unit]
Description=Run Hale Orchestrator orphan sweep every 15 minutes

[Timer]
OnBootSec=5min
OnUnitActiveSec=15min

[Install]
WantedBy=timers.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now hale-orchestrator-sweep.timer
systemctl --user list-timers hale-orchestrator-sweep.timer
```

- [ ] **Step 6: Live verification**

```bash
systemctl --user start hale-orchestrator-sweep.service
journalctl --user -u hale-orchestrator-sweep.service --since "2 min ago" --no-pager
```

Expected: service ran, exit code 0, log line either silent (nothing to sweep) or reporting closed plan_ids.

- [ ] **Step 7: Commit**

```bash
cd /home/john/Thunderbird/.claude/worktrees/hale-orchestrator
git add scripts/hale_orchestrator_timer_sweep.py core/ops/test_hale_orchestrator_timer_sweep.py
git commit -m "feat: Hale orchestrator — cross-engine universal backstop (systemd timer)"
```

Note: the two systemd unit files live outside the git repo (`~/.config/systemd/user/`) and are not committed — they're installed directly on the host per Step 5.

---

## Spec Coverage Check

| Spec section | Covered by |
|---|---|
| `Plan` / `AssessResult` dataclasses, auto-derivation | Task 1, Task 3 |
| `PlanStore`, fenced blocks in `hale_decisions.md`, `fcntl` locking | Task 2 |
| Tier reuse (T2/T3 Prompt Charter fields) | Task 3 |
| `assess_plan` MET/MISSED/UNVERIFIED, PASS/FAIL, GREEN/YELLOW/RED | Task 4 |
| `close_plan` | Task 5 |
| Error handling — orchestrator failures never block, degrade gracefully | Task 3, Task 4, Task 5 (inline try/except in each) |
| Backstop hook — orphan auto-FAIL, universal auto-file | Task 6 |
| Hook registration | Task 7 |
| Concurrency (8-instance Hale Bus) | Task 2 (`test_concurrent_appends_do_not_corrupt`) |
| Live verification discipline | Task 8, Step 3 |
| Cross-engine parity (Claude Code + OpenCode) | Task 9 — library is engine-agnostic by construction (Tasks 1-5); Task 9 adds the universal backstop OpenCode's missing hook system can't provide |
