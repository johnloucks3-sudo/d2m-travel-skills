"""
Thunderbird Skills API — Per-Persona Tool Packages
====================================================
Dreams2Memories Travel, LLC

The Anthropic Skills API packages code + instructions as SKILL.md containers
uploaded to the Files API. Skills run via the code execution tool — reducing
the 97-tool MCP overload by giving each persona only the tools they need.

Max 8 skills per request, max 8MB per skill.
Skills are beta: betas=["skills-2025-03-13"] (or current beta tag)

Architecture:
  - Each persona gets a SKILL.md file with Python functions for their domain
  - Uploaded once via Files API, referenced by skill_id
  - Registry: config/skills_registry.json
  - Skills defined below: dani, a2_dembe, a5_castillo, a9_harlan, cos_hale

SKILL.md format:
  # SKILL: <name>
  ## Description
  <what it does>
  ## Code
  ```python
  <python functions available to the model>
  ```
  ## Instructions
  <how the model should use the functions>

CLI:
  python thunderbird_skills_api.py --upload-all       # upload all skill packages
  python thunderbird_skills_api.py --list              # list registry
  python thunderbird_skills_api.py --upload <name>     # upload one skill
  python thunderbird_skills_api.py --delete <name>     # delete one skill
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("thunderbird_skills_api")

THUNDERBIRD_DIR  = Path.home() / "Thunderbird"
SKILLS_DIR       = THUNDERBIRD_DIR / "skills"
REGISTRY_FILE    = THUNDERBIRD_DIR / "config" / "skills_registry.json"

# ── Skill definitions ─────────────────────────────────────────────────────────
# Each entry: name, description, filename (auto-generated in skills/)

SKILL_DEFINITIONS = {
    "dani_travel": {
        "description": "Dani (A3) — travel concierge tools: destination lookup, cruise search, hotel rates, tour search, port weather",
        "content": """# SKILL: dani_travel
## Description
Dani's concierge toolkit for answering client travel questions. Covers destination research,
cruise voyage search, hotel rate lookup, tour options, and port weather.

## Instructions
Use these functions when a client asks about destinations, cruise options, hotels, excursions,
or travel conditions. Always present results in a warm, concierge tone. Summarize clearly —
clients don't need raw JSON.

## Code
```python
import json

def search_cruise_voyages(cruise_line: str, destination: str = "", year: int = 2026) -> dict:
    \"\"\"Search available cruise voyages. cruise_line: silversea|regent|cunard|oceania|seabourn|viking|ponant\"\"\"
    # Implemented via MCP: search_live_cruise_voyages
    return {"action": "search_live_cruise_voyages", "cruise_line": cruise_line,
            "destination": destination, "year": year}

def get_port_weather(port: str, travel_date: str = "") -> dict:
    \"\"\"Get weather forecast for a cruise port.\"\"\"
    return {"action": "get_port_weather_forecast", "port": port, "date": travel_date}

def search_hotels(destination: str, check_in: str, check_out: str,
                  guests: int = 2, luxury: bool = True) -> dict:
    \"\"\"Search hotel options for a destination.\"\"\"
    return {"action": "search_hotels", "destination": destination,
            "check_in": check_in, "check_out": check_out, "guests": guests}

def search_tours(destination: str, category: str = "cultural") -> dict:
    \"\"\"Search shore excursions and tours. category: cultural|culinary|adventure|scenic\"\"\"
    return {"action": "search_tours", "destination": destination, "category": category}

def get_travel_advisory(destination: str) -> dict:
    \"\"\"Get current travel advisory and safety information for a destination.\"\"\"
    return {"action": "get_travel_advisories", "destination": destination}
```
""",
    },

    "a2_intel": {
        "description": "A2 Dembe — market intelligence tools: cruise intel, competitor analysis, destination research, X/OSINT feeds",
        "content": """# SKILL: a2_intel
## Description
Wraith's intelligence toolkit. Covers cruise industry news, competitive pricing surveillance,
destination deep-dives, and OSINT social monitoring.

## Instructions
Use precision and evidence. State confidence levels. Don't speculate beyond the data.
Cite sources where available. Present findings as an intelligence brief, not a sales pitch.

## Code
```python
def run_ship_intelligence(cruise_line: str, ship_name: str = "") -> dict:
    \"\"\"Run a full intelligence sweep on a cruise line or specific ship.\"\"\"
    return {"action": "run_ship_intelligence_sweep", "cruise_line": cruise_line,
            "ship_name": ship_name}

def run_competitive_surveillance(cruise_lines: list = None) -> dict:
    \"\"\"Run competitive pricing and positioning surveillance.\"\"\"
    return {"action": "run_competitive_surveillance",
            "cruise_lines": cruise_lines or ["silversea", "regent", "seabourn"]}

def get_world_intel(regions: list = None) -> dict:
    \"\"\"Get multi-domain world intelligence brief.\"\"\"
    return {"action": "get_multi_domain_intel",
            "regions": regions or ["caribbean", "mediterranean", "alaska"]}

def scrape_x_feed(topics: list = None) -> dict:
    \"\"\"Scrape X/Twitter for cruise industry intel.\"\"\"
    return {"action": "scrape_x_osint_feed",
            "topics": topics or ["luxury cruise", "cruise industry news"]}
```
""",
    },

    "a9_finance": {
        "description": "A9 Harlan — finance tools: commission reconciliation, cost analysis, booking audit",
        "content": """# SKILL: a9_finance
## Description
Vic Harlan's number-crunching toolkit. Commission audits, markup calculations,
cost-benefit analysis, and booking financial reconciliation.

## Instructions
Be blunt. Numbers first, commentary second. If something looks wrong, say so directly.
Round to 2 decimal places. Always show the math.

## Code
```python
def calculate_commission(net_price: float, markup_pct: float = 25.0,
                          currency: str = "USD", eur_rate: float = 1.09) -> dict:
    \"\"\"Calculate D2M commission and client price.
    markup_pct: 25 for standard, 22 for premium/SLH properties.\"\"\"
    net_usd = net_price * eur_rate if currency == "EUR" else net_price
    client_price = net_usd * (1 + markup_pct / 100)
    commission = client_price - net_usd
    return {
        "net_usd": round(net_usd, 2),
        "client_price": round(client_price, 2),
        "commission": round(commission, 2),
        "markup_pct": markup_pct,
        "currency_used": currency,
    }

def reconcile_commissions(booking_ids: list = None) -> dict:
    \"\"\"Pull commission data from OA/Tess for reconciliation.\"\"\"
    return {"action": "reconcile_commissions", "booking_ids": booking_ids}

def audit_oa_commissions() -> dict:
    \"\"\"Scrape OA portal for pending and received commissions.\"\"\"
    return {"action": "oa_scrape_commissions"}
```
""",
    },

    "cos_ops": {
        "description": "COS Hale — operations tools: weekly report, morning briefing, staff coordination, calendar sync",
        "content": """# SKILL: cos_ops
## Description
Iron Vic's operational command tools. Weekly reports, morning briefings,
booking anchors, calendar sync, and staff tasking coordination.

## Instructions
Measured, authoritative. Lead with the operational picture, then the detail.
Flag anything that needs Commander decision. Never bury the lede.

## Code
```python
def generate_weekly_report() -> dict:
    \"\"\"Generate the weekly D2M operations and revenue report.\"\"\"
    return {"action": "generate_weekly_report"}

def send_morning_briefing() -> dict:
    \"\"\"Compile and send the morning intelligence briefing to Commander.\"\"\"
    return {"action": "send_morning_briefing"}

def scan_booking_anchors() -> dict:
    \"\"\"Scan for upcoming payment deadlines and action items.\"\"\"
    return {"action": "scan_anchor_dates"}

def sync_anchors_to_calendar() -> dict:
    \"\"\"Push booking milestones and deadlines to Google Calendar.\"\"\"
    return {"action": "sync_anchors_to_calendar"}

def create_client_task(client_name: str, action: str, priority: str = "normal") -> dict:
    \"\"\"Create a client action task. priority: urgent|normal|low\"\"\"
    return {"action": "create_client_task", "client": client_name,
            "task": action, "priority": priority}
```
""",
    },

    "a5_strategy": {
        "description": "A5 Castillo — strategy tools: competitive positioning, pricing models, growth opportunity analysis",
        "content": """# SKILL: a5_strategy
## Description
Viper's strategy toolkit. OODA-loop business analysis, pricing models,
competitive positioning, and growth vector identification.

## Instructions
Fast, decisive. Think in frameworks. Present options with tradeoffs.
Flag strategic risks. Commander-facing only — no client exposure.

## Code
```python
def analyze_pricing_position(cruise_line: str, voyage_id: str = "") -> dict:
    \"\"\"Analyze our pricing vs. direct consumer rates for a cruise.\"\"\"
    return {"action": "scrape_consumer_tour_prices", "cruise_line": cruise_line,
            "voyage_id": voyage_id}

def compute_booking_anchors(client_name: str = "") -> dict:
    \"\"\"Compute financial anchors (deposits, final payments) for open bookings.\"\"\"
    return {"action": "compute_booking_anchors", "client": client_name}

def run_tech_monitor() -> dict:
    \"\"\"Run tech and AI industry monitor for strategic signals.\"\"\"
    return {"action": "run_tech_monitor"}
```
""",
    },
}

# ── Registry I/O ──────────────────────────────────────────────────────────────

def _load_registry() -> dict:
    if REGISTRY_FILE.exists():
        try:
            return json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _save_registry(registry: dict) -> None:
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(json.dumps(registry, indent=2), encoding="utf-8")

# ── Anthropic client ──────────────────────────────────────────────────────────

def _get_client():
    import anthropic
    return anthropic.Anthropic()

# ── Core operations ───────────────────────────────────────────────────────────

def upload_skill(skill_name: str, force: bool = False) -> dict:
    """Upload a skill package to Files API. Returns registry entry."""
    if skill_name not in SKILL_DEFINITIONS:
        return {"error": f"Unknown skill: {skill_name}. Valid: {list(SKILL_DEFINITIONS)}"}

    defn = SKILL_DEFINITIONS[skill_name]
    content_bytes = defn["content"].encode("utf-8")
    content_size  = len(content_bytes)

    registry = _load_registry()
    existing = registry.get(skill_name, {})

    if not force and existing.get("file_id") and existing.get("size_bytes") == content_size:
        return existing

    client = _get_client()

    # Delete old version
    if existing.get("file_id"):
        try:
            client.beta.files.delete(existing["file_id"])
        except Exception:
            pass

    try:
        result = client.beta.files.upload(
            file=(f"{skill_name}.md", content_bytes, "text/plain"),
        )
        entry = {
            "file_id":     result.id,
            "skill_name":  skill_name,
            "description": defn["description"],
            "synced_at":   datetime.now(timezone.utc).isoformat(),
            "size_bytes":  content_size,
        }
        registry[skill_name] = entry
        _save_registry(registry)
        logger.info("Uploaded skill %s → %s", skill_name, result.id)
        return entry
    except Exception as e:
        return {"error": str(e), "skill": skill_name}


def upload_all_skills(force: bool = False) -> dict:
    results = {"uploaded": [], "skipped": [], "errors": []}
    for name in SKILL_DEFINITIONS:
        entry = upload_skill(name, force=force)
        if "error" in entry:
            results["errors"].append({"skill": name, "error": entry["error"]})
        elif entry.get("synced_at"):
            # Check if it was actually uploaded or just returned existing
            results["uploaded"].append({"skill": name, "file_id": entry["file_id"]})
        else:
            results["skipped"].append(name)
    return results


def get_skill_block(skill_name: str) -> dict | None:
    """Return a Files API content block for a skill package."""
    registry = _load_registry()
    entry = registry.get(skill_name)
    if not entry or not entry.get("file_id"):
        return None
    return {
        "type": "document",
        "source": {
            "type":    "file",
            "file_id": entry["file_id"],
        },
        "title": f"SKILL: {skill_name}",
    }


def get_persona_skills(persona: str) -> list[dict]:
    """Return skill blocks for a given persona shortname.
    persona: dani | a2 | a5 | a9 | cos
    """
    mapping = {
        "dani":    ["dani_travel"],
        "a2":      ["a2_intel"],
        "a3":      ["dani_travel"],
        "a5":      ["a5_strategy"],
        "a9":      ["a9_finance"],
        "cos":     ["cos_ops"],
        "a2_dembe":  ["a2_intel"],
        "a5_castillo": ["a5_strategy"],
        "a9_harlan":   ["a9_finance"],
    }
    skill_names = mapping.get(persona.lower(), [])
    blocks = []
    for name in skill_names:
        block = get_skill_block(name)
        if block:
            blocks.append(block)
    return blocks


def list_registry() -> list[dict]:
    registry = _load_registry()
    return [{"skill": k, **v} for k, v in sorted(registry.items())]


def delete_skill(skill_name: str) -> dict:
    registry = _load_registry()
    entry = registry.get(skill_name)
    if not entry or not entry.get("file_id"):
        return {"error": f"No file_id in registry for {skill_name}"}
    client = _get_client()
    try:
        client.beta.files.delete(entry["file_id"])
        del registry[skill_name]
        _save_registry(registry)
        return {"deleted": skill_name, "file_id": entry["file_id"]}
    except Exception as e:
        return {"error": str(e)}


# ── MCP tool registration ─────────────────────────────────────────────────────

def register_skills_tools(mcp) -> None:

    @mcp.tool()
    def upload_skill_package(skill_name: str, force: bool = False) -> str:
        """Upload a persona skill package to Anthropic Files API.
        skill_name: dani_travel | a2_intel | a9_finance | cos_ops | a5_strategy"""
        result = upload_skill(skill_name, force=force)
        if "error" in result:
            return f"Error: {result['error']}"
        return json.dumps(result, indent=2)

    @mcp.tool()
    def upload_all_skill_packages(force: bool = False) -> str:
        """Upload all persona skill packages to Files API."""
        result = upload_all_skills(force=force)
        return (
            f"Uploaded: {len(result['uploaded'])} | "
            f"Skipped: {len(result['skipped'])} | "
            f"Errors: {len(result['errors'])}"
        )

    @mcp.tool()
    def list_skill_packages() -> str:
        """List all skill packages in the registry."""
        entries = list_registry()
        if not entries:
            return "No skills uploaded yet. Run upload_all_skill_packages first."
        lines = [
            f"{e['skill']}: {e.get('file_id','—')} — {e.get('description','')}"
            for e in entries
        ]
        return "\n".join(lines)


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = sys.argv[1:]

    if "--list" in args:
        entries = list_registry()
        if not entries:
            print("No skills registered. Run --upload-all first.")
        else:
            print(f"{'Skill':<20} {'File ID':<30} {'KB':>4}  Description")
            print("-" * 100)
            for e in entries:
                kb = e.get("size_bytes", 0) // 1024
                print(f"{e['skill']:<20} {e.get('file_id','—'):<30} {kb:>4}  {e.get('description','')[:50]}")

    elif "--upload-all" in args:
        force = "--force" in args
        print(f"Uploading all skill packages{' (forced)' if force else ''}...")
        result = upload_all_skills(force=force)
        print(f"  Uploaded: {len(result['uploaded'])}")
        print(f"  Skipped:  {len(result['skipped'])}")
        print(f"  Errors:   {len(result['errors'])}")
        for e in result["errors"]:
            print(f"    ERROR {e['skill']}: {e['error']}")
        for u in result["uploaded"]:
            print(f"    OK {u['skill']} → {u['file_id']}")

    elif "--upload" in args:
        idx = args.index("--upload")
        if idx + 1 < len(args):
            name = args[idx + 1]
            force = "--force" in args
            result = upload_skill(name, force=force)
            print(json.dumps(result, indent=2))
        else:
            print(f"Usage: --upload <skill_name>  (valid: {list(SKILL_DEFINITIONS)})")

    elif "--delete" in args:
        idx = args.index("--delete")
        if idx + 1 < len(args):
            result = delete_skill(args[idx + 1])
            print(json.dumps(result, indent=2))
        else:
            print("Usage: --delete <skill_name>")

    elif "--skills" in args:
        print("Available skill definitions:")
        for name, defn in SKILL_DEFINITIONS.items():
            print(f"  {name}: {defn['description']}")

    else:
        print("Usage:")
        print("  python thunderbird_skills_api.py --upload-all [--force]")
        print("  python thunderbird_skills_api.py --upload <name> [--force]")
        print("  python thunderbird_skills_api.py --list")
        print("  python thunderbird_skills_api.py --delete <name>")
        print("  python thunderbird_skills_api.py --skills")
