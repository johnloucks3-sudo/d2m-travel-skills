#!/usr/bin/env python3
"""CI probe — Dani identity layer (MISSION-651 / 2026-06-25).

Checks:
  1. thunderbird-telegram-gw.service is active
  2. DANI_CLIENT_PROMPT constant is present in the gateway module
  3. Non-Commander user_id causes _build_dani_claude_prompt to use client prompt
  4. Commander user_id causes _build_dani_claude_prompt to use full persona prompt

Exit 0 = GREEN. Exit 1 = RED.
"""
import subprocess, sys, os
sys.path.insert(0, "/home/john/Thunderbird")

def check(label, ok, detail=""):
    status = "OK" if ok else "FAIL"
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))
    return ok

results = []

# 1. Gateway service active
r = subprocess.run(
    ["systemctl", "--user", "is-active", "thunderbird-telegram-gw.service"],
    capture_output=True, text=True
)
results.append(check("gateway service active", r.stdout.strip() == "active", r.stdout.strip()))

# 2. DANI_CLIENT_PROMPT present in module source
gw = open("/home/john/Thunderbird/OpsCenter/thunderbird_telegram_gw.py").read()
results.append(check("DANI_CLIENT_PROMPT defined", "DANI_CLIENT_PROMPT" in gw))
results.append(check("_thread_ctx declared", "_thread_ctx = threading.local()" in gw))
results.append(check("_thread_ctx.user_id set at engine call", gw.count("_thread_ctx.user_id = user_id") >= 2,
                      f"{gw.count('_thread_ctx.user_id = user_id')} call sites (need >=2)"))

# 3. Import-level: non-Commander gets trainee branch
import importlib.util
spec = importlib.util.spec_from_file_location(
    "tgw", "/home/john/Thunderbird/OpsCenter/thunderbird_telegram_gw.py"
)
mod = importlib.util.module_from_spec(spec)
# Minimal env so module doesn't crash on missing tokens
os.environ.setdefault("TELEGRAM_D2MC2C_TOKEN", "dummy")
os.environ.setdefault("TELEGRAM_DANI_TOKEN", "dummy")
os.environ.setdefault("TELEGRAM_HALE_TOKEN", "dummy")
os.environ.setdefault("TELEGRAM_COMMANDER_ID", "7554895206")
try:
    spec.loader.exec_module(mod)

    # Simulate non-Commander call
    mod._thread_ctx.user_id = 9999999  # not Commander
    trainee_prompt = mod._build_dani_claude_prompt("", "hello")
    results.append(check("non-Commander gets trainee prompt",
                          "NEVER mention internal Wing personas" in trainee_prompt))

    # Simulate Commander call
    mod._thread_ctx.user_id = 7554895206
    commander_prompt = mod._build_dani_claude_prompt("", "hello")
    results.append(check("Commander gets full persona prompt",
                          "NEVER mention internal Wing personas" not in commander_prompt))

except Exception as e:
    results.append(check("module identity logic", False, str(e)))

passed = all(results)
print(f"\nDani identity layer: {'GREEN' if passed else 'RED'} ({sum(results)}/{len(results)} checks passed)")
sys.exit(0 if passed else 1)
