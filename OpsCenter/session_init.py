#!/usr/bin/env python3
"""
Session initialization — fires at startup via hooks/session_open.sh
L1 PRIORITY (SO-2026-06-24): Load HALE BUS state from prior session
L2: Check persona inboxes for pending dissent/observations
L3: Verify credential timers
"""

import sys
import json
import os
from pathlib import Path

# Setup paths
TBIRD = Path(__file__).parent.parent
sys.path.insert(0, str(TBIRD))

# 🚨 HALE BUS MANDATORY STARTUP READ — fires BEFORE anything else (SO-2026-06-24)
print("⚡ [HALE BUS] Loading inter-instance state...")
try:
    from core.hale_bus.hale_bus_read import load_bus_at_startup

    instance_type = os.getenv("HALE_INSTANCE", "claude_code")
    bus_state = load_bus_at_startup(instance_type)

    if bus_state:
        print(f"✅ [HALE BUS] State loaded from {len(bus_state.get('hale_instances', {}))} instances")

        # Log critical directives
        directives = bus_state.get('critical_state', {}).get('commander_directives', [])
        if directives:
            print(f"🔴 [HALE BUS] {len(directives)} critical directive(s):")
            for d in directives[:3]:
                print(f"   - {d.get('id', '?')}: {d.get('scope', '')}")

        # Log FPD alerts
        fpds = bus_state.get('critical_state', {}).get('fpd_alerts', [])
        if fpds:
            print(f"⚠️  [HALE BUS] {len(fpds)} FPD alert(s)")
    else:
        print("ℹ️  [HALE BUS] No prior state — cold start")
except Exception as e:
    print(f"⚠️  [HALE BUS] Failed to load: {e} (continuing with cold start)")

# Check persona inboxes (RabbitMQ on yoga)
print("[PERSONA] Checking inboxes...")
try:
    import requests
    # RabbitMQ management API on yoga
    rabbit_url = "http://100.69.222.124:15672/api/queues"
    response = requests.get(rabbit_url, auth=("guest", "guest"), timeout=2)
    if response.status_code == 200:
        queues = response.json()
        inbox_count = sum(q.get("messages", 0) for q in queues if "inbox" in q.get("name", "").lower())
        if inbox_count > 0:
            print(f"[PERSONA] ⚠️ {inbox_count} pending messages in persona inboxes")
    else:
        print(f"[PERSONA] ℹ️ RabbitMQ unavailable (graceful fallback)")
except Exception as e:
    print(f"[PERSONA] ℹ️ Inbox check skipped: {e}")

# Verify credential timers
print("[CREDENTIALS] Checking status...")
try:
    cred_status_path = Path("/home/john/Thunderbird/hale_state.json")
    if cred_status_path.exists():
        with open(cred_status_path) as f:
            state = json.load(f)
        creds = state.get("wing_health", {}).get("credential_status", {})
        expired = [k for k, v in creds.items() if v.get("status") != "OK"]
        if expired:
            print(f"[CREDENTIALS] 🚨 EXPIRED: {', '.join(expired)}")
        else:
            print(f"[CREDENTIALS] ✅ All credentials valid")
    else:
        print("[CREDENTIALS] ℹ️ No state file found")
except Exception as e:
    print(f"[CREDENTIALS] ⚠️ Could not verify: {e}")

# 🆕 Keyword Router & Context-Mode Tools (SO-2026-06-27)
print("[KEYWORD ROUTER] Loading auto-routing config...")
try:
    from core.ai_infra.session_startup_keyword_router import (
        init_keyword_router,
        session_startup_banner,
    )

    router, prior_context = init_keyword_router("claude-code")
    session_startup_banner("claude-code", prior_context)

    # Export router globally so main loop can access
    os.environ["KEYWORD_ROUTER_LOADED"] = "1"
    print("[KEYWORD ROUTER] ✅ Active — @ctx, @zen, @free, @oc keywords enabled")

except Exception as e:
    print(f"[KEYWORD ROUTER] ⚠️ Failed to load: {e} (falling back to default routing)")

print("[SESSION] Initialization complete")
