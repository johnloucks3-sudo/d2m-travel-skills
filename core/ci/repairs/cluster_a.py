#!/usr/bin/env python3
"""
CI Rapid-Repair Warehouse — Cluster A: Web / Portal / Scrape (9 skills)
Dreams2Memories Travel, LLC · Thunderbird Wing
Author: Brig Gen (Ret.) Thomas "Gauge" Sterling (A7) · Sterling-fleet A · 2026-07-02

Skills (9):
  portal-access          CAUTION  / DESTRUCTIVE (reCAPTCHA=MANUAL)
  web-fetch              SAFE     (pip reinstall)
  regent-portal-live     CAUTION  / DESTRUCTIVE (Akamai=MANUAL)
  competitive-intel-apis SAFE     / DESTRUCTIVE (API key rotation=MANUAL)
  cruise-intelligence    SAFE     (cache recreate)
  nominatim-geocoding    SAFE
  hotel-scan             DESTRUCTIVE, repairable=False  (DORMANT/MANUAL-ONLY)
  transfer-scan          DESTRUCTIVE, repairable=False  (DORMANT/MANUAL-ONLY)
  cloak-browser-regent   SAFE (npm reinstall) / DESTRUCTIVE (Akamai rule change=MANUAL)
                         NO existing repair_ — apply-path authored from recipe.

Authoring rules observed:
  - explore() is READ-ONLY: probe + signals. Never mutates.
  - assess()  is SIDE-EFFECT-FREE: classifies mode only.
  - repair(mode, apply=False): DRY-RUN by default.
    apply=True wraps the EXISTING body by import (never rewriting internals).
    cloak-browser-regent: no existing body — npm-reinstall apply-path authored here.
  - verify()  re-runs the skill's health_probe independently.
  - risk_tier defaults to DESTRUCTIVE (fail-safe) when unsure.
  - DORMANT skills: repairable=False (NOT_REPAIRABLE escalation, nothing staged).

Sources:
  output/ci_repair/research_domain_recipes.md §1.1 – §1.9
  core/ci/ci_auto_repair_engine.py (existing repair bodies)
  config/ci_registry.json (health_probe paths)
  docs/CI_RAPID_REPAIR_SCHEMA.md
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from core.ci.repairs.schema import (
    AssessResult,
    FailureContext,
    ProbeState,
    RepairPlan,
    RiskTier,
    probe_context,
    repair_capability,
    run_probe,
    systemctl_is_active,
)

# Import the EXISTING, TESTED repair bodies — wrap by import, single source, no drift.
# (per schema.py PRESERVE-INTERNALS RULE and CI_RAPID_REPAIR_SCHEMA.md §3 step 2)
from core.ci.ci_auto_repair_engine import (
    repair_portal_access,
    repair_web_fetch,
    repair_regent_portal_live,
    repair_competitive_intel_apis,
    repair_cruise_intelligence,
    repair_nominatim_geocoding,
    repair_hotel_scan,
    repair_transfer_scan,
)

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
VENV_PY = str(THUNDERBIRD_ROOT / ".venv/bin/python3")
COOKIE_STATUS = THUNDERBIRD_ROOT / "OpsCenter" / "state" / "cookie_refresh_status.json"
CLOAK_DIR = THUNDERBIRD_ROOT / "tools" / "cloak"


# ============================================================================
# 1. portal-access — Cruise-line Portal Access
#    Baseline: CAUTION (session warm auto-applies + notifies)
#    Assess raises to DESTRUCTIVE for reCAPTCHA / Akamai manual modes
# ============================================================================

_PORTAL_PROBE = "ci_probe_portal_access.py"


@repair_capability(
    "portal-access",
    risk_tier=RiskTier.CAUTION,
    sources=[
        "output/ci_repair/research_domain_recipes.md §1.1",
        "core/ci/ci_auto_repair_engine.py::repair_portal_access",
    ],
    timeout_seconds=180,
    max_attempts=2,
    cooldown_seconds=600,
    verify_settle_seconds=8,
)
def _portal_access():
    def explore() -> FailureContext:
        # READ-ONLY: run probe, capture stderr, check cookie status file.
        cookie_age_hours: float = -1.0
        try:
            if COOKIE_STATUS.exists():
                cs = json.loads(COOKIE_STATUS.read_text())
                # Look for regent cookie age if stored
                regent_info = cs.get("regent", cs.get("aspxauth", {}))
                if isinstance(regent_info, dict):
                    cookie_age_hours = float(regent_info.get("age_hours", -1))
        except Exception:
            pass

        ctx = probe_context(
            "portal-access",
            _PORTAL_PROBE,
            extra_signals={
                "cookie_status_present": COOKIE_STATUS.exists(),
                "cookie_age_hours": cookie_age_hours,
            },
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()
        # Akamai challenge / reCAPTCHA indicators → DESTRUCTIVE / MANUAL-ONLY
        if any(tok in stderr for tok in ("akamai", "recaptcha", "captcha", "challenge", "403")):
            return AssessResult(
                mode="akamai_or_recaptcha_block",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason=(
                    "Akamai/reCAPTCHA block detected — requires Commander real-browser "
                    "session via grab_regent_cookies_cdp.py; no automated path"
                ),
            )
        # Regent OA expired separately
        if "regent_oa" in stderr or "oa" in stderr:
            return AssessResult(
                mode="regent_oa_expired",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="Regent OA reCAPTCHA blocks automation — Commander Firefox re-auth required",
            )
        # Default: cookie/session expired — auto-repair via rssc_session_keepalive + centrav
        return AssessResult(
            mode="session_cookie_expired",
            repairable=True,
            effective_tier=RiskTier.CAUTION,
            reason="Centrav or Regent ASPXAUTH session expired — running keepalive scripts",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="portal-access",
            mode=mode,
            actions=[
                "scripts/centrav_session_relogin.py — re-authenticate Centrav laravel_session",
                "scripts/rssc_session_keepalive.py — refresh Regent ASPXAUTH (48h window)",
                "Verify either succeeds (OR logic); TRUE if at least one portal recovers",
            ],
        )
        if not apply:
            return plan  # DRY-RUN
        plan.applied = True
        plan.apply_ok = bool(repair_portal_access())
        return plan

    def verify() -> ProbeState:
        return run_probe(_PORTAL_PROBE)

    return explore, assess, repair, verify


# ============================================================================
# 2. web-fetch — Web Fetch & Scrape
#    Baseline: SAFE (idempotent pip reinstall)
# ============================================================================

_WEB_FETCH_PROBE = "ci_probe_web_fetch.py"


@repair_capability(
    "web-fetch",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §1.2",
        "core/ci/ci_auto_repair_engine.py::repair_web_fetch",
    ],
    timeout_seconds=120,
    max_attempts=2,
    cooldown_seconds=300,
    verify_settle_seconds=5,
)
def _web_fetch():
    def explore() -> FailureContext:
        # READ-ONLY: check anansi + trafilatura importability
        anansi_ok = False
        trafilatura_ok = False
        try:
            r_a = subprocess.run(
                [VENV_PY, "-c", "import anansi; print('OK')"],
                capture_output=True, text=True, timeout=15,
            )
            anansi_ok = r_a.returncode == 0 and "OK" in r_a.stdout
        except Exception:
            pass
        try:
            r_t = subprocess.run(
                [VENV_PY, "-c", "import trafilatura; print('OK')"],
                capture_output=True, text=True, timeout=15,
            )
            trafilatura_ok = r_t.returncode == 0 and "OK" in r_t.stdout
        except Exception:
            pass

        ctx = probe_context(
            "web-fetch",
            _WEB_FETCH_PROBE,
            extra_signals={
                "anansi_importable": anansi_ok,
                "trafilatura_importable": trafilatura_ok,
            },
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()
        anansi_ok = ctx.signals.get("anansi_importable", False)
        trafilatura_ok = ctx.signals.get("trafilatura_importable", False)

        # Package collision (issubclass error from wrong PyPI anansi package)
        if "issubclass" in stderr or "collision" in stderr:
            return AssessResult(
                mode="anansi_package_collision",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="anansi PyPI collision — pip reinstall + import verify resolves",
            )
        # Missing packages
        if not anansi_ok or not trafilatura_ok:
            return AssessResult(
                mode="package_missing_or_broken",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason=f"anansi_importable={anansi_ok} trafilatura_importable={trafilatura_ok}; pip reinstall",
            )
        # Bot-wall / SPA empty — no local repair, just escalate
        if "403" in stderr or "bot" in stderr or "cloudflare" in stderr:
            return AssessResult(
                mode="bot_wall_block",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="Bot-wall on target — escalate to CloakBrowser; local packages are fine",
            )
        # Default: package repair
        return AssessResult(
            mode="package_missing_or_broken",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason="Generic web-fetch probe failure — pip reinstall anansi+trafilatura",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="web-fetch",
            mode=mode,
            actions=[
                f"{VENV_PY} -m pip install anansi trafilatura -q",
                f"{VENV_PY} -c \"import anansi; print('OK')\" — verify import",
            ],
        )
        if not apply:
            return plan  # DRY-RUN
        plan.applied = True
        plan.apply_ok = bool(repair_web_fetch())
        return plan

    def verify() -> ProbeState:
        return run_probe(_WEB_FETCH_PROBE)

    return explore, assess, repair, verify


# ============================================================================
# 3. regent-portal-live — Regent Live Portal (On-Demand)
#    Baseline: CAUTION (keepalive auto-applies + notifies)
#    Assess raises to DESTRUCTIVE for Akamai CDP block
# ============================================================================

_REGENT_PROBE = "ci_probe_regent_portal_live.py"


@repair_capability(
    "regent-portal-live",
    risk_tier=RiskTier.CAUTION,
    sources=[
        "output/ci_repair/research_domain_recipes.md §1.3",
        "core/ci/ci_auto_repair_engine.py::repair_regent_portal_live",
    ],
    timeout_seconds=180,
    max_attempts=2,
    cooldown_seconds=600,
    verify_settle_seconds=10,
)
def _regent_portal_live():
    def explore() -> FailureContext:
        # READ-ONLY: probe + cookie status signals
        cookie_age_hours: float = -1.0
        try:
            if COOKIE_STATUS.exists():
                cs = json.loads(COOKIE_STATUS.read_text())
                regent_info = cs.get("regent", cs.get("aspxauth", {}))
                if isinstance(regent_info, dict):
                    cookie_age_hours = float(regent_info.get("age_hours", -1))
        except Exception:
            pass

        ctx = probe_context(
            "regent-portal-live",
            _REGENT_PROBE,
            extra_signals={
                "cookie_status_present": COOKIE_STATUS.exists(),
                "cookie_age_hours": cookie_age_hours,
            },
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()

        # Akamai CDP block → DESTRUCTIVE / Commander manual
        if any(tok in stderr for tok in ("akamai", "captcha", "challenge", "403")):
            return AssessResult(
                mode="akamai_cdp_block",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason=(
                    "Akamai bot-detection blocks CDP scrape — Commander opens Firefox, "
                    "grabs fresh ASPXAUTH via grab_regent_cookies_cdp.py"
                ),
            )
        # Selector change (empty result from capture script)
        if "empty" in stderr or "0 record" in stderr or "json" in stderr:
            return AssessResult(
                mode="selector_changed",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason=(
                    "Booking capture returns empty — selectors may have changed; "
                    "Whetstone REFRESH required on reference_regent_portal_selectors.md"
                ),
            )
        # Default: ASPXAUTH cookie expired — CAUTION keepalive
        return AssessResult(
            mode="aspxauth_expired",
            repairable=True,
            effective_tier=RiskTier.CAUTION,
            reason="Regent ASPXAUTH expired (48h window) — rssc_session_keepalive.py",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="regent-portal-live",
            mode=mode,
            actions=[
                "scripts/rssc_session_keepalive.py — refresh Regent ASPXAUTH cookie",
                "On failure: escalate to Commander for Firefox manual re-auth (CDP path)",
            ],
        )
        if not apply:
            return plan  # DRY-RUN
        plan.applied = True
        plan.apply_ok = bool(repair_regent_portal_live())
        return plan

    def verify() -> ProbeState:
        return run_probe(_REGENT_PROBE)

    return explore, assess, repair, verify


# ============================================================================
# 4. competitive-intel-apis — Competitive Intelligence APIs
#    Baseline: SAFE (dep reinstall, script fix)
#    Assess raises to DESTRUCTIVE for API key rotation
# ============================================================================

_INTEL_PROBE = "ci_probe_competitive_intel_apis.py"
_INTEL_CACHE = THUNDERBIRD_ROOT / "intel"


@repair_capability(
    "competitive-intel-apis",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §1.4",
        "core/ci/ci_auto_repair_engine.py::repair_competitive_intel_apis",
    ],
    timeout_seconds=120,
    max_attempts=2,
    cooldown_seconds=300,
    verify_settle_seconds=5,
)
def _competitive_intel_apis():
    def explore() -> FailureContext:
        # READ-ONLY: check monitor script + cache freshness
        monitor_script = THUNDERBIRD_ROOT / "intel" / "cruise_competitor_monitor.py"
        cache_files = list(_INTEL_CACHE.glob("*.json")) if _INTEL_CACHE.exists() else []
        cache_age_hours: float = -1.0
        if cache_files:
            import time
            newest = max(cache_files, key=lambda p: p.stat().st_mtime)
            cache_age_hours = (time.time() - newest.stat().st_mtime) / 3600.0

        ctx = probe_context(
            "competitive-intel-apis",
            _INTEL_PROBE,
            extra_signals={
                "monitor_script_present": monitor_script.exists(),
                "cache_age_hours": cache_age_hours,
                "cache_file_count": len(cache_files),
            },
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()

        # API key invalid / expired (401 from competitor API)
        if "401" in stderr or "api key" in stderr or "unauthorized" in stderr:
            return AssessResult(
                mode="api_key_invalid",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="Competitor API returns 401 — API key rotation requires Commander action",
            )
        # Bot-wall on scrape target (403/429)
        if "403" in stderr or "429" in stderr or "bot" in stderr:
            return AssessResult(
                mode="bot_wall_scrape_target",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="Bot-wall on competitor site — rotate to anansi --browser / CloakBrowser tier",
            )
        # Stale cache (>168h)
        if ctx.signals.get("cache_age_hours", 0) > 168:
            return AssessResult(
                mode="stale_cache",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason=f"Intel cache age={ctx.signals.get('cache_age_hours'):.1f}h > 168h — re-run monitor",
            )
        # Script missing / import error
        if not ctx.signals.get("monitor_script_present", True):
            return AssessResult(
                mode="monitor_script_missing",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="cruise_competitor_monitor.py absent — pip deps reinstall may restore",
            )
        # Default: dep reinstall
        return AssessResult(
            mode="dependency_error",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason="Generic import/dep error in competitive intel monitor — pip reinstall",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="competitive-intel-apis",
            mode=mode,
            actions=[
                "pip install requests beautifulsoup4 -q in .venv",
                "Verify intel/cruise_competitor_monitor.py exists",
                "Re-run intel/cruise_competitor_monitor.py to refresh cache",
            ],
        )
        if not apply:
            return plan  # DRY-RUN
        plan.applied = True
        plan.apply_ok = bool(repair_competitive_intel_apis())
        return plan

    def verify() -> ProbeState:
        return run_probe(_INTEL_PROBE)

    return explore, assess, repair, verify


# ============================================================================
# 5. cruise-intelligence — Cruise Intelligence Cache
#    Baseline: SAFE (cache recreate, dep reinstall)
# ============================================================================

_CRUISE_INTEL_PROBE = "ci_probe_cruise_intelligence.py"
_CRUISE_CACHE_FILES = [
    THUNDERBIRD_ROOT / "intel" / "cruise_critic_cache.json",
    THUNDERBIRD_ROOT / "intel" / "cruise_intel_cache.json",
]


@repair_capability(
    "cruise-intelligence",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §1.5",
        "core/ci/ci_auto_repair_engine.py::repair_cruise_intelligence",
    ],
    timeout_seconds=120,
    max_attempts=2,
    cooldown_seconds=300,
    verify_settle_seconds=5,
)
def _cruise_intelligence():
    def explore() -> FailureContext:
        import time

        # READ-ONLY: check for corrupt / stale cache files, script presence
        cache_corrupt = False
        cache_age_hours: float = -1.0
        existing = [p for p in _CRUISE_CACHE_FILES if p.exists()]

        for cp in existing:
            try:
                json.loads(cp.read_text())
            except Exception:
                cache_corrupt = True

        if existing:
            newest_mtime = max(p.stat().st_mtime for p in existing)
            cache_age_hours = (time.time() - newest_mtime) / 3600.0

        critic_script = THUNDERBIRD_ROOT / "intel" / "cruise_critic_monitor.py"
        sweep_script = THUNDERBIRD_ROOT / "intel" / "cruise_line_intel_sweep.py"

        ctx = probe_context(
            "cruise-intelligence",
            _CRUISE_INTEL_PROBE,
            extra_signals={
                "cache_corrupt": cache_corrupt,
                "cache_age_hours": cache_age_hours,
                "cache_files_found": len(existing),
                "cruise_critic_script_present": critic_script.exists(),
                "sweep_script_present": sweep_script.exists(),
            },
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()

        if ctx.signals.get("cache_corrupt"):
            return AssessResult(
                mode="cache_corrupt",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="Cache JSON corrupt — delete + re-run intel sweep to regenerate",
            )
        if ctx.signals.get("cache_age_hours", 0) > 168:
            return AssessResult(
                mode="cache_stale",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason=f"Cache stale ({ctx.signals.get('cache_age_hours'):.1f}h) — re-run sweep",
            )
        if "importerror" in stderr or "modulenot" in stderr:
            return AssessResult(
                mode="dependency_error",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="Import error in cruise intelligence scripts — pip reinstall deps",
            )
        # Bot-wall on Cruise Critic
        if "403" in stderr or "429" in stderr:
            return AssessResult(
                mode="source_blocked",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="Source site blocking scrape — throttle + Anansi fallback",
            )
        return AssessResult(
            mode="cache_stale",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason="Generic cruise-intelligence probe failure — re-run intel sweep",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="cruise-intelligence",
            mode=mode,
            actions=[
                "Delete corrupt/stale cache JSON files in intel/",
                "pip install missing deps (requests, bs4) -q",
                "Re-run intel/cruise_line_intel_sweep.py to regenerate cache",
            ],
        )
        if not apply:
            return plan  # DRY-RUN
        plan.applied = True
        plan.apply_ok = bool(repair_cruise_intelligence())
        return plan

    def verify() -> ProbeState:
        return run_probe(_CRUISE_INTEL_PROBE)

    return explore, assess, repair, verify


# ============================================================================
# 6. nominatim-geocoding — Nominatim Geocoding ($0 OSM)
#    Baseline: SAFE (rate-limit backoff, pip reinstall)
# ============================================================================

_NOMINATIM_PROBE = "ci_probe_nominatim_geocoding.py"


@repair_capability(
    "nominatim-geocoding",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §1.6",
        "core/ci/ci_auto_repair_engine.py::repair_nominatim_geocoding",
    ],
    timeout_seconds=60,
    max_attempts=2,
    cooldown_seconds=120,
    verify_settle_seconds=5,
)
def _nominatim_geocoding():
    def explore() -> FailureContext:
        # READ-ONLY: check requests importability + script presence
        requests_ok = False
        try:
            r = subprocess.run(
                [VENV_PY, "-c", "import requests; print('OK')"],
                capture_output=True, text=True, timeout=10,
            )
            requests_ok = r.returncode == 0 and "OK" in r.stdout
        except Exception:
            pass

        nominatim_script = THUNDERBIRD_ROOT / "scripts" / "nominatim_geocode.py"

        ctx = probe_context(
            "nominatim-geocoding",
            _NOMINATIM_PROBE,
            extra_signals={
                "requests_importable": requests_ok,
                "nominatim_script_present": nominatim_script.exists(),
            },
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()

        # OSM service down — no local repair
        if "503" in stderr or "timeout" in stderr or "service unavailable" in stderr:
            return AssessResult(
                mode="osm_service_down",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="OSM Nominatim temporarily unavailable — no local fix; wait + reprobe",
            )
        # Rate-limit violation (429)
        if "429" in stderr or "rate" in stderr:
            return AssessResult(
                mode="rate_limit_violated",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="Nominatim 1 req/s policy violated — repair verifies delay compliance",
            )
        # Missing requests library
        if not ctx.signals.get("requests_importable", True):
            return AssessResult(
                mode="requests_missing",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="requests library missing — pip install requests",
            )
        # Default: pip reinstall
        return AssessResult(
            mode="dependency_error",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason="Generic nominatim probe failure — pip reinstall requests",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="nominatim-geocoding",
            mode=mode,
            actions=[
                "pip install requests -q in .venv",
                "Verify User-Agent header set per OSM policy in nominatim_geocode.py",
                "Confirm ≥1s inter-request delay in calling code",
            ],
        )
        if not apply:
            return plan  # DRY-RUN
        plan.applied = True
        plan.apply_ok = bool(repair_nominatim_geocoding())
        return plan

    def verify() -> ProbeState:
        return run_probe(_NOMINATIM_PROBE)

    return explore, assess, repair, verify


# ============================================================================
# 7. hotel-scan — Hotel Price Scanner
#    CORRECTED 2026-07-09: the "DORMANT/no data source" classification below was
#    STALE AND WRONG — scripts/hotel_scan.py runs cleanly right now (reads dossiers,
#    checks existing hotel windows, writes state — no external partner-API
#    dependency at all). The registry was only RED because last_run had gone
#    stale (173.6h vs 25h limit) — nobody had a repair path that just re-ran it.
#    Baseline: SAFE (re-run script to refresh state)
# ============================================================================

_HOTEL_PROBE = "ci_probe_hotel_scan.py"
_HOTEL_SCRIPT = THUNDERBIRD_ROOT / "scripts" / "hotel_scan.py"


@repair_capability(
    "hotel-scan",
    risk_tier=RiskTier.SAFE,
    sources=[
        "Corrected 2026-07-09 — prior DORMANT classification was stale; script verified working",
    ],
    timeout_seconds=60,
    max_attempts=2,
    cooldown_seconds=1800,
    verify_settle_seconds=5,
)
def _hotel_scan():
    def explore() -> FailureContext:
        ctx = probe_context(
            "hotel-scan",
            _HOTEL_PROBE,
            extra_signals={"hotel_script_present": _HOTEL_SCRIPT.exists()},
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()
        if not ctx.signals.get("hotel_script_present", True):
            return AssessResult(
                mode="script_missing",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="scripts/hotel_scan.py missing — restore from git, not auto-repairable",
            )
        if "stale" in stderr:
            return AssessResult(
                mode="stale_state",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="State file stale — script itself works, just needs a fresh run",
            )
        return AssessResult(
            mode="unknown_error",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason="Non-stale RED — attempt a re-run before escalating",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="hotel-scan",
            mode=mode,
            actions=["Re-run scripts/hotel_scan.py to refresh OpsCenter/state/hotel_scan_state.json"],
        )
        if not apply:
            return plan  # DRY-RUN
        try:
            r = subprocess.run(
                ["python3", str(_HOTEL_SCRIPT)],
                cwd=str(THUNDERBIRD_ROOT), capture_output=True, text=True, timeout=45,
            )
            plan.applied = True
            plan.apply_ok = (r.returncode == 0)
        except Exception:
            plan.applied = True
            plan.apply_ok = False
        return plan

    def verify() -> ProbeState:
        return run_probe(_HOTEL_PROBE)

    return explore, assess, repair, verify


# ============================================================================
# 8. transfer-scan — Ground Transfer Scanner
#    CORRECTED 2026-07-09: the "DORMANT/no data source" classification below was
#    STALE AND WRONG — scripts/transfer_scan.py runs cleanly right now (reads
#    dossiers, checks existing transfer windows, writes state — no external API
#    dependency at all). The registry was only RED because last_run had gone
#    stale (>25h) — nobody had a repair path that just re-ran the script.
#    Baseline: SAFE (re-run script to refresh state)
# ============================================================================

_TRANSFER_PROBE = "ci_probe_transfer_scan.py"
_TRANSFER_SCRIPT = THUNDERBIRD_ROOT / "scripts" / "transfer_scan.py"


@repair_capability(
    "transfer-scan",
    risk_tier=RiskTier.SAFE,
    sources=[
        "Corrected 2026-07-09 — prior DORMANT classification was stale; script verified working",
    ],
    timeout_seconds=60,
    max_attempts=2,
    cooldown_seconds=1800,
    verify_settle_seconds=5,
)
def _transfer_scan():
    def explore() -> FailureContext:
        ctx = probe_context(
            "transfer-scan",
            _TRANSFER_PROBE,
            extra_signals={"transfer_script_present": _TRANSFER_SCRIPT.exists()},
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()
        if not ctx.signals.get("transfer_script_present", True):
            return AssessResult(
                mode="script_missing",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason="scripts/transfer_scan.py missing — restore from git, not auto-repairable",
            )
        if "stale" in stderr:
            return AssessResult(
                mode="stale_state",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="State file stale — script itself works, just needs a fresh run",
            )
        return AssessResult(
            mode="unknown_error",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason="Non-stale RED — attempt a re-run before escalating",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        plan = RepairPlan(
            skill_id="transfer-scan",
            mode=mode,
            actions=["Re-run scripts/transfer_scan.py to refresh OpsCenter/state/transfer_scan_state.json"],
        )
        if not apply:
            return plan  # DRY-RUN
        try:
            r = subprocess.run(
                ["python3", str(_TRANSFER_SCRIPT)],
                cwd=str(THUNDERBIRD_ROOT), capture_output=True, text=True, timeout=45,
            )
            plan.applied = True
            plan.apply_ok = (r.returncode == 0)
        except Exception:
            plan.applied = True
            plan.apply_ok = False
        return plan

    def verify() -> ProbeState:
        return run_probe(_TRANSFER_PROBE)

    return explore, assess, repair, verify


# ============================================================================
# 9. cloak-browser-regent — CloakBrowser Tier 3 (Regent Akamai Wall Bypass)
#    NO existing repair_ function — apply-path AUTHORED FROM RECIPE (Dembe §1.9)
#    Baseline: SAFE (npm reinstall) / DESTRUCTIVE (Akamai rule change = MANUAL)
# ============================================================================

_CLOAK_PROBE = "ci_probe_cloak_browser_regent.py"
_CLOAK_MODULES = CLOAK_DIR / "node_modules" / "cloakbrowser"
_SMART_FETCH = THUNDERBIRD_ROOT / "core" / "web" / "smart_fetch.py"


@repair_capability(
    "cloak-browser-regent",
    risk_tier=RiskTier.SAFE,
    sources=[
        "output/ci_repair/research_domain_recipes.md §1.9",
        "tools/cloak/cloak_fetch.mjs",
        "core/web/smart_fetch.py",
        "MISSION-1498 (cloak-browser deployment)",
    ],
    timeout_seconds=120,
    max_attempts=2,
    cooldown_seconds=300,
    verify_settle_seconds=8,
)
def _cloak_browser_regent():
    def explore() -> FailureContext:
        # READ-ONLY: check Node.js presence, cloakbrowser module, smart_fetch routing
        node_in_path = False
        node_version = ""
        try:
            r = subprocess.run(
                ["node", "--version"],
                capture_output=True, text=True, timeout=10,
            )
            node_in_path = r.returncode == 0
            node_version = r.stdout.strip()
        except Exception:
            pass

        cloak_module_present = _CLOAK_MODULES.exists()
        package_json_present = (CLOAK_DIR / "package.json").exists()
        smart_fetch_present = _SMART_FETCH.exists()

        # READ-ONLY check: is rssc.com in the smart_fetch Tier 3 host list?
        rssc_in_tier3 = False
        if smart_fetch_present:
            try:
                content = _SMART_FETCH.read_text()
                rssc_in_tier3 = "rssc.com" in content
            except Exception:
                pass

        ctx = probe_context(
            "cloak-browser-regent",
            _CLOAK_PROBE,
            extra_signals={
                "node_in_path": node_in_path,
                "node_version": node_version,
                "cloakbrowser_module_present": cloak_module_present,
                "package_json_present": package_json_present,
                "smart_fetch_present": smart_fetch_present,
                "rssc_in_tier3_hostlist": rssc_in_tier3,
            },
        )
        return ctx

    def assess(ctx: FailureContext) -> AssessResult:
        stderr = (ctx.probe_stderr or "").lower()

        # Node.js not in PATH — STATEFUL (needs nvm or apt install)
        if not ctx.signals.get("node_in_path", True):
            return AssessResult(
                mode="node_not_in_path",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason=(
                    "Node.js not found in PATH — install Node ≥18 via nvm or system package manager; "
                    "requires Commander action (sudo/nvm) beyond wing automation"
                ),
            )

        # Akamai rule set changed — Tier 3 now blocked despite CloakBrowser
        if "403" in stderr or "content" in stderr and "2kb" in stderr:
            return AssessResult(
                mode="akamai_rule_changed",
                repairable=False,
                effective_tier=RiskTier.DESTRUCTIVE,
                reason=(
                    "Akamai rule set changed — CloakBrowser Tier 3 blocked; "
                    "Whetstone REPLACE trigger: evaluate nodriver or residential proxy"
                ),
            )

        # smart_fetch not routing to Tier 3 (rssc.com missing from host list)
        if not ctx.signals.get("rssc_in_tier3_hostlist", True) and ctx.signals.get("smart_fetch_present"):
            return AssessResult(
                mode="smart_fetch_routing_gap",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="rssc.com not in smart_fetch Tier 3 known-walled host list — config fix (SAFE)",
            )

        # cloakbrowser module missing or corrupt — npm install
        if not ctx.signals.get("cloakbrowser_module_present", True) or "module_not_found" in stderr:
            return AssessResult(
                mode="npm_package_missing",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="cloakbrowser npm package missing/corrupt — cd tools/cloak && npm install cloakbrowser",
            )

        # Version stale (fingerprint detectable)
        if "version" in stderr or "stale" in stderr or "alpha" in stderr:
            return AssessResult(
                mode="npm_package_stale",
                repairable=True,
                effective_tier=RiskTier.SAFE,
                reason="CloakBrowser version stale — npm update cloakbrowser (no alpha builds)",
            )

        # Default: npm reinstall
        return AssessResult(
            mode="npm_package_missing",
            repairable=True,
            effective_tier=RiskTier.SAFE,
            reason="Generic cloak-browser-regent failure — npm reinstall cloakbrowser",
        )

    def repair(mode: str, apply: bool = False) -> RepairPlan:
        """
        AUTHORED FROM RECIPE (Dembe §1.9) — no existing repair_ function.
        SAFE path: npm install/update cloakbrowser in tools/cloak/.
        DESTRUCTIVE path: not reached (repairable=False → NOT_REPAIRABLE).
        """
        if mode == "npm_package_stale":
            actions = [
                f"cd {CLOAK_DIR} && npm update cloakbrowser (do NOT install alpha builds)",
                f"Verify {CLOAK_DIR}/node_modules/cloakbrowser exists post-update",
                "Re-run ci_probe_cloak_browser_regent.py to confirm content > 2KB from rssc.com",
            ]
        elif mode == "smart_fetch_routing_gap":
            actions = [
                f"Add 'rssc.com' to Tier 3 known-walled host list in {_SMART_FETCH}",
                "No service restart required — smart_fetch.py is imported per-call",
                "Re-probe to confirm Tier 3 route activates for rssc.com requests",
            ]
        else:
            # Default: npm install
            actions = [
                f"cd {CLOAK_DIR} && npm install cloakbrowser",
                f"Verify {_CLOAK_MODULES} exists after install",
                f"node {CLOAK_DIR}/cloak_fetch.mjs — smoke test against rssc.com",
                "Confirm response body > 2KB (Akamai edge cleared)",
            ]

        plan = RepairPlan(
            skill_id="cloak-browser-regent",
            mode=mode,
            actions=actions,
        )
        if not apply:
            return plan  # DRY-RUN

        # APPLY PATH — authored from recipe (no repair_ wrapper exists)
        # SAFE modes only reach here (DESTRUCTIVE modes are repairable=False).
        plan.applied = True
        ok = False
        try:
            if mode == "smart_fetch_routing_gap":
                # READ + WRITE: add rssc.com to Tier 3 host list if absent
                if _SMART_FETCH.exists():
                    content = _SMART_FETCH.read_text()
                    # Only write if rssc.com genuinely missing (idempotent guard)
                    if "rssc.com" not in content:
                        # Insert into a recognizable Tier 3 host list pattern.
                        # This is a conservative targeted patch — do not rewrite the file.
                        content = content.replace(
                            "TIER3_HOSTS = [",
                            'TIER3_HOSTS = [\n    "rssc.com",  # Regent public site — Akamai wall (added by CI repair)',
                        )
                        if "rssc.com" in content:
                            _SMART_FETCH.write_text(content)
                            ok = True
                        # else: pattern not found — repair cannot locate anchor safely
                    else:
                        ok = True  # already present — idempotent
            else:
                # npm install or npm update
                npm_cmd = (
                    ["npm", "update", "cloakbrowser"]
                    if mode == "npm_package_stale"
                    else ["npm", "install", "cloakbrowser"]
                )
                r = subprocess.run(
                    npm_cmd,
                    cwd=str(CLOAK_DIR),
                    capture_output=True, text=True, timeout=90,
                )
                ok = r.returncode == 0 and _CLOAK_MODULES.exists()
        except Exception:
            ok = False

        plan.apply_ok = ok
        return plan

    def verify() -> ProbeState:
        return run_probe(_CLOAK_PROBE)

    return explore, assess, repair, verify
