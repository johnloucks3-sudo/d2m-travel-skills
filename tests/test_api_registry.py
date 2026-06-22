import json
import re
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

def test_env_var_names_are_unique():
    data = json.loads(Path("config/api_registry.json").read_text())
    env_vars = [e["env_var"] for e in data["credentials"]]
    assert len(env_vars) == len(set(env_vars)), f"Duplicate env_var found: {[v for v in env_vars if env_vars.count(v) > 1]}"

def test_credential_names_are_unique():
    data = json.loads(Path("config/api_registry.json").read_text())
    names = [e["name"] for e in data["credentials"]]
    assert len(names) == len(set(names)), f"Duplicate name found: {[n for n in names if names.count(n) > 1]}"

def test_usage_warning_pct_in_range():
    data = json.loads(Path("config/api_registry.json").read_text())
    for entry in data["credentials"]:
        pct = entry["usage_warning_pct"]
        assert 0 <= pct <= 100, f"{entry['name']}: usage_warning_pct {pct} out of range 0-100"

def test_monthly_cost_is_non_negative():
    data = json.loads(Path("config/api_registry.json").read_text())
    for entry in data["credentials"]:
        assert entry["monthly_cost_usd"] >= 0, f"{entry['name']}: monthly_cost_usd cannot be negative"

def test_added_date_format():
    data = json.loads(Path("config/api_registry.json").read_text())
    for entry in data["credentials"]:
        assert re.match(r'^\d{4}-\d{2}-\d{2}$', entry["added"]), \
            f"{entry['name']}: added date '{entry['added']}' must be YYYY-MM-DD"
