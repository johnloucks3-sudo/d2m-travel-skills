#!/usr/bin/env python3
"""
sync_poe_opencode.py — Sync Poe API key AND model IDs into opencode.json
Dreams2Memories Travel, LLC

Run this whenever you rotate the Poe API key at poe.com/api_key:
    1. Update POE_API_KEY in ~/Thunderbird/config/poe.env
    2. python3 scripts/sync_poe_opencode.py

Or use the shell alias:  poe-sync

Why this exists:
    opencode.json's poe provider requires apiKey as a literal value.
    Without it, @ai-sdk/openai-compatible falls back to OPENAI_API_KEY from
    the shell environment, which is either unset or wrong — causing intermittent
    auth failures that "re-auth through poe.com" cannot fix (browser session ≠ API key).

    This script also syncs model IDs from agents/thunderbird_poe_config.py into
    opencode.json so the two stay consistent and model 404 errors don't appear
    after a restart.
"""

import json
import sys
import importlib.util
from pathlib import Path

THUNDERBIRD = Path(__file__).resolve().parent.parent
POE_ENV     = THUNDERBIRD / "config" / "poe.env"
OC_JSON     = THUNDERBIRD / "opencode.json"
POE_CONFIG  = THUNDERBIRD / "agents" / "thunderbird_poe_config.py"


def read_poe_env() -> dict[str, str]:
    result = {}
    if not POE_ENV.exists():
        sys.exit(f"ERROR: {POE_ENV} not found")
    for line in POE_ENV.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip()
    return result


def load_model_profiles() -> dict[str, str]:
    """Load MODEL_PROFILES from thunderbird_poe_config.py and return {opencode_key: poe_model_id}.

    Builds the opencode model map from the canonical poe_config source of truth.
    Only includes models that make sense as OpenCode interactive targets (excludes
    image-gen, community bots, and unused aliases).
    """
    if not POE_CONFIG.exists():
        print(f"WARNING: {POE_CONFIG} not found — skipping model sync")
        return {}

    spec = importlib.util.spec_from_file_location("thunderbird_poe_config", POE_CONFIG)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        print(f"WARNING: Could not load poe_config: {e} — skipping model sync")
        return {}

    profiles: dict = getattr(mod, "MODEL_PROFILES", {})

    # Map profile key → poe_model_id for the subset we expose in OpenCode
    # Exclude image-gen bots and community bots that change names frequently
    EXCLUDE = {"grok-imagine", "nano-banana", "nano-banana-2", "nano-webui"}
    result = {}
    for key, profile in profiles.items():
        if key in EXCLUDE:
            continue
        poe_id = profile.get("poe_model", "")
        label  = profile.get("label", key)
        if poe_id:
            # Use the poe_model ID as the opencode model key (must match exactly)
            result[poe_id] = f"{label} (Poe)"

    return result


def main() -> None:
    cfg = read_poe_env()

    key = cfg.get("POE_API_KEY", "")
    if not key:
        sys.exit("ERROR: POE_API_KEY not set in config/poe.env")

    if not OC_JSON.exists():
        sys.exit(f"ERROR: {OC_JSON} not found")

    data = json.loads(OC_JSON.read_text())

    poe_provider = data.get("provider", {}).get("poe")
    if not poe_provider:
        sys.exit("ERROR: 'poe' provider not found in opencode.json")

    # ── Sync API key ──────────────────────────────────────────────────────────
    old_key = poe_provider.get("options", {}).get("apiKey", "<not set>")
    poe_provider.setdefault("options", {})["apiKey"] = key

    key_changed = old_key != key
    masked_old  = old_key[:8] + "..." if len(old_key) > 8 else old_key
    masked_new  = key[:8] + "..."

    # ── Sync model IDs from poe_config.py ─────────────────────────────────────
    model_map = load_model_profiles()
    models_changed = False

    if model_map:
        old_models = poe_provider.get("models", {})
        new_models = {poe_id: {"name": label} for poe_id, label in model_map.items()}

        if old_models != new_models:
            poe_provider["models"] = new_models
            models_changed = True

    # ── Write back ────────────────────────────────────────────────────────────
    OC_JSON.write_text(json.dumps(data, indent=2) + "\n")

    # ── Report ────────────────────────────────────────────────────────────────
    print("opencode.json updated")
    if key_changed:
        print(f"  poe.apiKey: {masked_old}  ->  {masked_new}")
    else:
        print(f"  poe.apiKey: unchanged ({masked_new})")

    if models_changed:
        print(f"  models synced from poe_config.py: {len(model_map)} models")
        for poe_id in sorted(model_map):
            print(f"    {poe_id}")
    elif model_map:
        print(f"  models: already in sync ({len(model_map)} models)")
    else:
        print(f"  models: skipped (poe_config.py not loadable)")

    print("Restart OpenCode for changes to take effect.")


if __name__ == "__main__":
    main()
