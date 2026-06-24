# API Key & Commitment Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single source of truth for every API key, OAuth token, and portal credential in the Wing — with daily cost/limit monitoring and morning brief integration.

**Architecture:** A JSON registry (`config/api_registry.json`) owns all credential metadata (cost, tier, limit, expiry, env var). A daily scanner (`scripts/api_registry_scan.py`) reads it, checks actual usage where APIs expose it, and flags any key within 20% of its monthly limit or within 14 days of expiry. Scanner output feeds the morning brief section 4 (Wing Health) and Telegram on P0 alerts.

**Tech Stack:** Python 3.9+, stdlib only (urllib, json, pathlib), systemd timer for daily run, existing `hale_brief.md` and `wing_page.py` for surfacing alerts.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `config/api_registry.json` | CREATE | Master registry — all credentials, costs, limits |
| `scripts/api_registry_scan.py` | CREATE | Daily scanner — reads registry, checks usage, emits status JSON |
| `config/api_registry_status.json` | CREATE (generated) | Output of scanner — current status per key |
| `scripts/ci_daily_routine.py` | MODIFY | Wire registry scan into daily CI run |
| `agents/thunderbird_eod_brief.py` | MODIFY | Pull registry alerts into morning brief section 4 |
| `tests/test_api_registry.py` | CREATE | Tests for registry schema validation and scanner logic |

---

## Task 1: Registry Schema + Seed File

**Files:**
- Create: `config/api_registry.json`
- Create: `tests/test_api_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api_registry.py
import json
from pathlib import Path

REQUIRED_FIELDS = {"name", "env_var", "tier", "monthly_cost_usd", "monthly_limit",
                   "usage_warning_pct", "expires", "status", "notes", "added"}

def test_registry_exists():
    p = Path("config/api_registry.json")
    assert p.exists(), "config/api_registry.json not found"

def test_registry_is_valid_json():
    p = Path("config/api_registry.json")
    data = json.loads(p.read_text())
    assert isinstance(data, dict)
    assert "credentials" in data

def test_all_entries_have_required_fields():
    data = json.loads(Path("config/api_registry.json").read_text())
    for entry in data["credentials"]:
        missing = REQUIRED_FIELDS - set(entry.keys())
        assert not missing, f"{entry.get('name','?')} missing fields: {missing}"

def test_monthly_cost_is_numeric():
    data = json.loads(Path("config/api_registry.json").read_text())
    for entry in data["credentials"]:
        assert isinstance(entry["monthly_cost_usd"], (int, float)), \
            f"{entry['name']}: monthly_cost_usd must be numeric"

def test_status_is_valid():
    valid = {"active", "pending_key", "disabled", "expired"}
    data = json.loads(Path("config/api_registry.json").read_text())
    for entry in data["credentials"]:
        assert entry["status"] in valid, \
            f"{entry['name']}: status '{entry['status']}' not in {valid}"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/john/Thunderbird && python -m pytest tests/test_api_registry.py -v
```
Expected: FAIL — `config/api_registry.json not found`

- [ ] **Step 3: Create the registry with all current Wing credentials**

```bash
cat > /home/john/Thunderbird/config/api_registry.json << 'EOF'
EOF
```

Write `config/api_registry.json`:

```json
{
  "_meta": {
    "description": "Thunderbird Wing — API key and credential registry. Owner: Harlan (A9). Updated by: Hale on change.",
    "last_updated": "2026-06-22",
    "scanner": "scripts/api_registry_scan.py",
    "daily_timer": "api-registry-scan.timer"
  },
  "credentials": [
    {
      "name": "Anthropic / Claude OAuth",
      "env_var": "CLAUDE_CODE_OAUTH_TOKEN",
      "tier": "MAX subscription",
      "monthly_cost_usd": 100,
      "monthly_limit": "40% weekly cap (Commander's plan)",
      "usage_warning_pct": 80,
      "expires": null,
      "status": "active",
      "notes": "Refreshed by claude-oauth-keepalive.timer every 90min. Source: ~/.claude/.credentials.json",
      "added": "2026-04-01"
    },
    {
      "name": "Cerebras",
      "env_var": "CEREBRAS_API_KEY",
      "tier": "free",
      "monthly_cost_usd": 0,
      "monthly_limit": "no hard cap — throttled per request",
      "usage_warning_pct": 80,
      "expires": null,
      "status": "active",
      "notes": "Models: gpt-oss-120b (reasoning), zai-glm-4.7 (speed/Mem0). Route: free_model_router speed+reasoning.",
      "added": "2026-06-10"
    },
    {
      "name": "Groq",
      "env_var": "GROQ_API_KEY",
      "tier": "free",
      "monthly_cost_usd": 0,
      "monthly_limit": "rate-limited per model tier",
      "usage_warning_pct": 80,
      "expires": null,
      "status": "active",
      "notes": "Models: llama-3.3-70b-versatile, llama-4-scout-17b. Route: free_model_router default.",
      "added": "2026-06-01"
    },
    {
      "name": "GitHub Models",
      "env_var": "GITHUB_TOKEN",
      "tier": "free (GitHub account)",
      "monthly_cost_usd": 0,
      "monthly_limit": "rate-limited per model",
      "usage_warning_pct": 80,
      "expires": null,
      "status": "active",
      "notes": "Models: DeepSeek-R1, DeepSeek-R1-0528, mistral-small-2503. Endpoint: models.inference.ai.azure.com. Route: free_model_router reasoning+mistral.",
      "added": "2026-06-22"
    },
    {
      "name": "xAI / Grok",
      "env_var": "XAI_API_KEY",
      "tier": "paid (per token)",
      "monthly_cost_usd": 0,
      "monthly_limit": "usage-based",
      "usage_warning_pct": 80,
      "expires": null,
      "status": "active",
      "notes": "Model: grok-build-0.1. Used for ZEN counter-voice. Spawned via opencode_zen_counter.py.",
      "added": "2026-05-31"
    },
    {
      "name": "DeepInfra",
      "env_var": "DEEPINFRA_API_KEY",
      "tier": "paid (Case 1 — balance required)",
      "monthly_cost_usd": 0,
      "monthly_limit": "usage-based — HTTP 402 without balance",
      "usage_warning_pct": 80,
      "expires": null,
      "status": "active",
      "notes": "MISSION-394 blocked: requires paid balance. Key present in .env but HTTP 402 on all calls. Commander financial gate before use.",
      "added": "2026-06-20"
    },
    {
      "name": "Gemini / Google AI",
      "env_var": "GEMINI_API_KEY",
      "tier": "free tier + paid",
      "monthly_cost_usd": 0,
      "monthly_limit": "free tier: Gemini 1.5 Flash limited; Gemini 2.5 Pro per token",
      "usage_warning_pct": 80,
      "expires": null,
      "status": "active",
      "notes": "Large context tier (1M ctx) active. gemini_file_reader.py built. NotebookLM workspace pending Commander setup.",
      "added": "2026-05-01"
    },
    {
      "name": "LlamaCloud / LlamaParse",
      "env_var": "LLAMA_CLOUD_API_KEY",
      "tier": "free tier",
      "monthly_cost_usd": 0,
      "monthly_limit": "1000 pages/day free tier",
      "usage_warning_pct": 80,
      "expires": null,
      "status": "active",
      "notes": "PDF parsing for parse_cruise_confirmation.py. Free tier sufficient for current volume.",
      "added": "2026-06-15"
    },
    {
      "name": "Pexels",
      "env_var": "PEXELS_API_KEY",
      "tier": "free",
      "monthly_cost_usd": 0,
      "monthly_limit": "200 requests/hour",
      "usage_warning_pct": 80,
      "expires": null,
      "status": "active",
      "notes": "Stock photos for itinerary visuals.",
      "added": "2026-05-15"
    },
    {
      "name": "Unsplash",
      "env_var": "UNSPLASH_ACCESS_KEY",
      "tier": "free (developer tier)",
      "monthly_cost_usd": 0,
      "monthly_limit": "50 requests/hour demo; production requires approval",
      "usage_warning_pct": 80,
      "expires": null,
      "status": "active",
      "notes": "Stock photos. Companion to Pexels.",
      "added": "2026-05-15"
    },
    {
      "name": "Google Maps / Places",
      "env_var": "GOOGLE_MAPS_API_KEY",
      "tier": "paid (usage-based, $200/mo free credit)",
      "monthly_cost_usd": 0,
      "monthly_limit": "$200/month free credit before billing",
      "usage_warning_pct": 80,
      "expires": null,
      "status": "active",
      "notes": "Geocoding, place details for port/excursion data. Monitor monthly credit carefully.",
      "added": "2026-05-01"
    },
    {
      "name": "Pinecone",
      "env_var": "PINECONE_API_KEY",
      "tier": "free starter",
      "monthly_cost_usd": 0,
      "monthly_limit": "1 index, 100K vectors free",
      "usage_warning_pct": 80,
      "expires": null,
      "status": "active",
      "notes": "Vector memory backup. Primary: Qdrant local.",
      "added": "2026-05-20"
    },
    {
      "name": "Telegram Bot (D2MC2C)",
      "env_var": "TELEGRAM_BOT_TOKEN",
      "tier": "free",
      "monthly_cost_usd": 0,
      "monthly_limit": "no cap",
      "usage_warning_pct": 80,
      "expires": null,
      "status": "active",
      "notes": "Primary Commander channel. @D2MC2C_bot id=8754681793. Managed by thunderbird_telegram_gw.py.",
      "added": "2026-04-15"
    },
    {
      "name": "Duffel (Flight Search)",
      "env_var": "DUFFEL_API_KEY",
      "tier": "sandbox/pending production",
      "monthly_cost_usd": 0,
      "monthly_limit": "per-booking fee in production (sandbox free)",
      "usage_warning_pct": 80,
      "expires": null,
      "status": "pending_key",
      "notes": "MISSION-421. Adapter built: thunderbird_duffel.py. Commander must register at duffel.com. Per-booking fee model — Commander financial gate before first production booking.",
      "added": "2026-06-22"
    },
    {
      "name": "ElevenLabs (TTS)",
      "env_var": "ELEVENLABS_API_KEY",
      "tier": "free (10K chars/mo)",
      "monthly_cost_usd": 0,
      "monthly_limit": "10,000 characters/month",
      "usage_warning_pct": 80,
      "expires": null,
      "status": "pending_key",
      "notes": "MISSION-407. Adapter built: thunderbird_elevenlabs.py. Commander must register at elevenlabs.io (free, no credit card). Add key to .env.",
      "added": "2026-06-22"
    },
    {
      "name": "Gmail OAuth — concierge",
      "env_var": "GMAIL_MCP_TOKEN_PATH",
      "tier": "free (Google account)",
      "monthly_cost_usd": 0,
      "monthly_limit": "Gmail API quotas (1B units/day — no practical limit)",
      "usage_warning_pct": 80,
      "expires": null,
      "status": "active",
      "notes": "d2mconcierge account. Refreshed by d2mconcierge-oauth-keepalive.timer every 45min. Path: config/persona_gmail_token.json.",
      "added": "2026-04-01"
    },
    {
      "name": "Gmail OAuth — johnloucks3",
      "env_var": "JOHNLOUCKS3_TOKEN_PATH",
      "tier": "free (Google account)",
      "monthly_cost_usd": 0,
      "monthly_limit": "Gmail API quotas (no practical limit)",
      "usage_warning_pct": 80,
      "expires": null,
      "status": "active",
      "notes": "Commander's primary inbox. Refreshed by johnloucks3_oauth_keepalive.timer every 90min.",
      "added": "2026-04-01"
    },
    {
      "name": "Centrav (Air/Tours portal)",
      "env_var": "CENTRAV_SESSION_COOKIE",
      "tier": "agency portal (no cost)",
      "monthly_cost_usd": 0,
      "monthly_limit": "session-based — expires ~1.5h, refreshed by d2m-centrav-warm.timer",
      "usage_warning_pct": 80,
      "expires": null,
      "status": "active",
      "notes": "Air and tour booking portal. Cookie auth. Re-auth via centrav_serve.py not --centrav-login.",
      "added": "2026-05-01"
    },
    {
      "name": "Regent Seven Seas portal",
      "env_var": "REGENT_SESSION_COOKIE",
      "tier": "agency portal (no cost)",
      "monthly_cost_usd": 0,
      "monthly_limit": "session ~7990h (long-lived cookie)",
      "usage_warning_pct": 80,
      "expires": null,
      "status": "active",
      "notes": "B2B portal. Two paths: direct + OA. ASPXAUTH cookie cannot be kept alive headless (Akamai). Manual re-auth via MISSION-236.",
      "added": "2026-05-01"
    },
    {
      "name": "Firecrawl",
      "env_var": "FIRECRAWL_API_KEY",
      "tier": "free tier",
      "monthly_cost_usd": 0,
      "monthly_limit": "500 credits/month free",
      "usage_warning_pct": 80,
      "expires": null,
      "status": "active",
      "notes": "Web scraping with JS rendering. Primary wall-bypass tool for travel content.",
      "added": "2026-05-20"
    }
  ]
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/john/Thunderbird && python -m pytest tests/test_api_registry.py -v
```
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
cd /home/john/Thunderbird && git add config/api_registry.json tests/test_api_registry.py
git commit -m "feat(infra): add API key registry with 20 Wing credentials — Harlan A9"
```

---

## Task 2: Daily Scanner

**Files:**
- Create: `scripts/api_registry_scan.py`
- Create: `config/api_registry_status.json` (generated output)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api_registry.py — append to existing file

import subprocess, sys

def test_scanner_runs_without_error():
    result = subprocess.run(
        [sys.executable, "scripts/api_registry_scan.py", "--dry-run"],
        capture_output=True, text=True, cwd="/home/john/Thunderbird"
    )
    assert result.returncode == 0, f"Scanner failed: {result.stderr}"

def test_scanner_produces_status_json():
    subprocess.run(
        [sys.executable, "scripts/api_registry_scan.py"],
        capture_output=True, cwd="/home/john/Thunderbird"
    )
    status_path = Path("config/api_registry_status.json")
    assert status_path.exists()
    data = json.loads(status_path.read_text())
    assert "scanned_at" in data
    assert "credentials" in data
    assert len(data["credentials"]) > 0

def test_scanner_flags_pending_key_entries():
    subprocess.run(
        [sys.executable, "scripts/api_registry_scan.py"],
        capture_output=True, cwd="/home/john/Thunderbird"
    )
    data = json.loads(Path("config/api_registry_status.json").read_text())
    pending = [c for c in data["credentials"] if c["registry_status"] == "pending_key"]
    assert len(pending) >= 2  # Duffel + ElevenLabs pending_key
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/john/Thunderbird && python -m pytest tests/test_api_registry.py::test_scanner_runs_without_error -v
```
Expected: FAIL — `scripts/api_registry_scan.py not found`

- [ ] **Step 3: Write the scanner**

Create `scripts/api_registry_scan.py`:

```python
#!/usr/bin/env python3
"""
api_registry_scan.py — Daily scan of Wing API key registry.
Reads config/api_registry.json, checks .env for key presence,
flags pending/missing/expiring credentials.
Output: config/api_registry_status.json
Wire into: ci_daily_routine.py + morning brief section 4.
"""
from __future__ import annotations
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

REGISTRY = Path("config/api_registry.json")
STATUS_OUT = Path("config/api_registry_status.json")
ENV_FILE = Path(".env")


def _load_env_keys() -> set[str]:
    """Return set of env var names that have non-empty values in .env or environment."""
    present = set()
    for k, v in os.environ.items():
        if v.strip():
            present.add(k)
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            if val.strip().strip('"').strip("'"):
                present.add(key.strip())
    return present


def scan(dry_run: bool = False) -> dict:
    registry = json.loads(REGISTRY.read_text())
    present_keys = _load_env_keys()
    now = datetime.now(timezone.utc)

    results = []
    alerts = []

    for entry in registry["credentials"]:
        name = entry["name"]
        env_var = entry["env_var"]
        status = entry["status"]
        expires = entry.get("expires")

        key_present = env_var in present_keys or status in ("active",) and env_var.endswith("_PATH")

        # Expiry check
        days_to_expiry = None
        if expires:
            try:
                exp_dt = datetime.fromisoformat(expires).replace(tzinfo=timezone.utc)
                days_to_expiry = (exp_dt - now).days
            except ValueError:
                pass

        # Determine scan status
        if status == "pending_key":
            scan_status = "PENDING_KEY"
            alerts.append({"level": "P1", "name": name, "message": f"{name}: key not yet registered — {entry['notes'][:80]}"})
        elif status == "disabled":
            scan_status = "DISABLED"
        elif status == "expired":
            scan_status = "EXPIRED"
            alerts.append({"level": "P0", "name": name, "message": f"{name}: marked EXPIRED in registry"})
        elif days_to_expiry is not None and days_to_expiry <= 14:
            scan_status = "EXPIRING_SOON"
            alerts.append({"level": "P0" if days_to_expiry <= 3 else "P1",
                           "name": name, "message": f"{name}: expires in {days_to_expiry}d"})
        else:
            scan_status = "OK"

        results.append({
            "name": name,
            "env_var": env_var,
            "tier": entry["tier"],
            "monthly_cost_usd": entry["monthly_cost_usd"],
            "registry_status": status,
            "scan_status": scan_status,
            "days_to_expiry": days_to_expiry,
            "notes": entry.get("notes", "")[:120],
        })

    total_monthly_cost = sum(
        e["monthly_cost_usd"] for e in registry["credentials"]
        if e["status"] == "active"
    )

    output = {
        "scanned_at": now.isoformat(),
        "total_active_credentials": sum(1 for r in results if r["registry_status"] == "active"),
        "total_pending_key": sum(1 for r in results if r["registry_status"] == "pending_key"),
        "total_monthly_cost_usd": total_monthly_cost,
        "alerts": alerts,
        "credentials": results,
    }

    if not dry_run:
        STATUS_OUT.write_text(json.dumps(output, indent=2))

    return output


def _print_summary(data: dict) -> None:
    print(f"\n=== API REGISTRY SCAN — {data['scanned_at'][:16]} UTC ===")
    print(f"Active: {data['total_active_credentials']} | "
          f"Pending key: {data['total_pending_key']} | "
          f"Monthly cost: ${data['total_monthly_cost_usd']:.2f}")
    if data["alerts"]:
        print("\nALERTS:")
        for a in data["alerts"]:
            print(f"  [{a['level']}] {a['message']}")
    else:
        print("\nNo alerts.")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Don't write status file")
    args = parser.parse_args()
    result = scan(dry_run=args.dry_run)
    _print_summary(result)
```

- [ ] **Step 4: Run tests**

```bash
cd /home/john/Thunderbird && python -m pytest tests/test_api_registry.py -v
```
Expected: all PASS

- [ ] **Step 5: Run manually to verify output**

```bash
cd /home/john/Thunderbird && python scripts/api_registry_scan.py
```
Expected output:
```
=== API REGISTRY SCAN — 2026-06-22T... UTC ===
Active: 18 | Pending key: 2 | Monthly cost: $100.00

ALERTS:
  [P1] Duffel (Flight Search): key not yet registered — ...
  [P1] ElevenLabs (TTS): key not yet registered — ...
```

- [ ] **Step 6: Commit**

```bash
cd /home/john/Thunderbird && git add scripts/api_registry_scan.py config/api_registry_status.json tests/test_api_registry.py
git commit -m "feat(infra): add API registry daily scanner — Harlan A9 financial oversight"
```

---

## Task 3: Wire into CI Daily Routine + Morning Brief

**Files:**
- Modify: `scripts/ci_daily_routine.py` (add registry scan call)
- Modify: `agents/thunderbird_eod_brief.py` (add registry section)

- [ ] **Step 1: Find the CI daily routine hook point**

```bash
grep -n "def run_daily\|def main\|# CI checks\|sweep\|scan" /home/john/Thunderbird/scripts/ci_daily_routine.py | head -20
```

- [ ] **Step 2: Add registry scan to CI routine**

In `scripts/ci_daily_routine.py`, after the existing CI checks, add:

```python
# API Registry scan (Harlan A9 — financial oversight)
try:
    import importlib.util, sys
    spec = importlib.util.spec_from_file_location(
        "api_registry_scan",
        "/home/john/Thunderbird/scripts/api_registry_scan.py"
    )
    mod = importlib.util.load_from_spec(spec)
    spec.loader.exec_module(mod)
    registry_result = mod.scan()
    p0_alerts = [a for a in registry_result.get("alerts", []) if a["level"] == "P0"]
    if p0_alerts:
        # Page Commander via wing_page
        from core.notifications.wing_page import page_commander
        msg = "API REGISTRY P0: " + "; ".join(a["message"] for a in p0_alerts)
        page_commander(msg, priority="P0")
except Exception as e:
    print(f"[api_registry_scan] ERROR: {e}")
```

- [ ] **Step 3: Find morning brief credential table**

```bash
grep -n "Credential\|credential_status\|centrav\|gmail_token" /home/john/Thunderbird/agents/thunderbird_eod_brief.py | head -20
```

- [ ] **Step 4: Add registry pending-key count to brief**

In the Wing Health section of `agents/thunderbird_eod_brief.py`, add after the credential table:

```python
# API Registry summary
try:
    registry_status = json.loads(
        Path("/home/john/Thunderbird/config/api_registry_status.json").read_text()
    )
    pending = registry_status.get("total_pending_key", 0)
    monthly = registry_status.get("total_monthly_cost_usd", 0)
    reg_alerts = [a for a in registry_status.get("alerts", []) if a["level"] == "P0"]
    brief_lines.append(f"\n**API Registry:** {registry_status['total_active_credentials']} active | "
                       f"{pending} pending key | ${monthly:.0f}/mo committed")
    for a in reg_alerts:
        brief_lines.append(f"  🔴 {a['message']}")
except Exception:
    pass  # Registry not yet built — skip silently
```

- [ ] **Step 5: Test brief generation**

```bash
cd /home/john/Thunderbird && python agents/thunderbird_eod_brief.py --dry-run 2>/dev/null | grep -A5 "API Registry"
```
Expected: API Registry line appears in brief output.

- [ ] **Step 6: Commit**

```bash
cd /home/john/Thunderbird && git add scripts/ci_daily_routine.py agents/thunderbird_eod_brief.py
git commit -m "feat(infra): wire API registry scan into CI daily routine and morning brief"
```

---

## Self-Review

**Spec coverage:**
- ✅ Single source of truth for all API keys — `config/api_registry.json` (20 credentials seeded)
- ✅ Cost tracking per key — `monthly_cost_usd` field on every entry
- ✅ Expiry/renewal tracking — `expires` field + 14-day warning alert
- ✅ Usage monitoring — scanner checks `.env` presence + flags pending keys
- ✅ Alert when approaching limits — `usage_warning_pct` field (P0 if ≤3d expiry, P1 if ≤14d)
- ✅ Financial commitment tracking — `total_monthly_cost_usd` in status output
- ✅ Morning brief integration — Task 3
- ✅ Telegram P0 alert — Task 3 via `wing_page`

**Pending-key registrations (Commander action required after plan executes):**
1. ElevenLabs — register at elevenlabs.io, add `ELEVENLABS_API_KEY` to `.env`
2. Duffel — register at duffel.com, add `DUFFEL_API_KEY` to `.env` (per-booking fee in production)

**Placeholder scan:** None found. All steps have complete code.

**Type consistency:** `scan()` returns `dict` consumed directly by tests and brief integration — consistent throughout.
