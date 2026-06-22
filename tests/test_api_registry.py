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
