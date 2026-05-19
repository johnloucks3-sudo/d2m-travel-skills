#!/usr/bin/env python3
"""
FOOLPROOF HEADLESS CLAUDE RESEARCH TASK
========================================
Single-purpose script: Research 3rd-party Claude integrators, agentic models, voice control.
NO dispatcher. NO complexity. Direct subprocess spawn with foolproof pattern.

Usage: python3 research_integrators_headless.py
Output: /home/john/Thunderbird/OpsCenter/opencode_knowledge/research_integrators_RESULT.md
Email:  johnloucks3@gmail.com (when email_on_complete=True)
"""

import subprocess
import os
import json
import sys
from pathlib import Path
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================
OUTPUT_DIR = Path("/home/john/Thunderbird/OpsCenter/opencode_knowledge")
LOG_DIR = Path("/home/john/Thunderbird/logs")
OUTPUT_FILE = OUTPUT_DIR / f"research_integrators_RESULT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
LOG_FILE = LOG_DIR / f"headless_claude_integrators_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
CLAUDE_BIN = Path.home() / ".local" / "bin" / "claude"
CREDS_FILE = Path.home() / ".claude" / ".credentials.json"

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
LOG_DIR.mkdir(exist_ok=True, parents=True)

# ============================================================================
# FOOLPROOF PATTERN: LOAD OAUTH TOKEN
# ============================================================================
def load_oauth_token():
    """Load OAuth token from credentials file. Fail hard if missing."""
    if not CREDS_FILE.exists():
        raise FileNotFoundError(f"FATAL: Credentials file not found at {CREDS_FILE}")

    try:
        creds = json.loads(CREDS_FILE.read_text())
        token = creds.get("claudeAiOauth", {}).get("accessToken")
        if not token:
            raise ValueError("No accessToken in credentials")
        return token
    except Exception as e:
        raise RuntimeError(f"Failed to load OAuth token: {e}")

# ============================================================================
# FOOLPROOF PATTERN: BUILD PROMPT WITH EXPLICIT WRITE [PATH]
# ============================================================================
def build_research_prompt():
    """Build the research prompt with EXPLICIT WRITE [PATH] instruction."""
    prompt = f"""You are Claude Sonnet, researching integration options for the Thunderbird Wing AI system.

TASK: Research and provide a comprehensive summary of:
1. **3rd Party Integrators for Claude**: Find tools/platforms similar to OpenCode that integrate with Claude API for agentic workflows. Include: name, key features, integration method, pricing, URL.
2. **Agentic Models for Thunderbird Wing**: Identify models (especially agentic/autonomous ones) that could improve Thunderbird Wing characteristics: multi-step reasoning, tool use, task decomposition, self-correction, parallel execution.
3. **Voice Activation & Control**: Tools/platforms for adding voice control to agentic systems working with Claude. Include: wake word engines, STT providers, voice command frameworks.

Provide actionable summaries with URLs. Use markdown with clear sections.

===== CRITICAL INSTRUCTION =====
WRITE your COMPLETE research output to {OUTPUT_FILE}
DO NOT output to stdout.
ALL output must go to the file path above.
Format as markdown with headers, tables, and URLs.
===== END CRITICAL INSTRUCTION =====

Begin research now. Output everything to {OUTPUT_FILE}."""
    return prompt

# ============================================================================
# FOOLPROOF PATTERN: SPAWN HEADLESS CLAUDE
# ============================================================================
def spawn_headless_claude(prompt, token, output_file, log_file):
    """
    Spawn headless Claude using the FOOLPROOF PATTERN:
    - Explicit WRITE [PATH] in prompt
    - OAuth token injected into environment
    - start_new_session=True (CRITICAL for detachment)
    - stdout/stderr to log file
    - Explicit model selection
    """

    # Build environment
    env = dict(os.environ)
    env["CLAUDE_CODE_OAUTH_TOKEN"] = token

    # Spawn
    print(f"[SPAWN] Starting headless Claude → {log_file}")
    print(f"[SPAWN] Output will be written to → {output_file}")

    try:
        with open(log_file, "w") as log_fd:
            proc = subprocess.Popen(
                [
                    str(CLAUDE_BIN),
                    "-p", prompt,
                    "--model", "claude-sonnet-4-6",
                    "--output-format", "text"
                ],
                stdout=log_fd,
                stderr=subprocess.STDOUT,
                env=env,
                start_new_session=True,  # ← CRITICAL: Detaches process
            )

        print(f"✅ Spawned Claude (PID {proc.pid})")
        print(f"   Log: {log_file}")
        print(f"   Output: {output_file}")
        return True

    except Exception as e:
        print(f"❌ FATAL: Failed to spawn Claude: {e}")
        return False

# ============================================================================
# MAIN EXECUTION
# ============================================================================
def main():
    print("\n" + "="*70)
    print("FOOLPROOF HEADLESS CLAUDE RESEARCH TASK")
    print("="*70 + "\n")

    # Step 1: Verify prerequisites
    print("[CHECK] Verifying prerequisites...")
    if not CLAUDE_BIN.exists():
        print(f"❌ FATAL: Claude binary not found at {CLAUDE_BIN}")
        return False
    print(f"✅ Claude binary: {CLAUDE_BIN}")

    if not CREDS_FILE.exists():
        print(f"❌ FATAL: Credentials file not found at {CREDS_FILE}")
        return False
    print(f"✅ Credentials file: {CREDS_FILE}")

    # Step 2: Load OAuth token
    print("\n[AUTH] Loading OAuth token...")
    try:
        token = load_oauth_token()
        print(f"✅ OAuth token loaded")
    except Exception as e:
        print(f"❌ FATAL: {e}")
        return False

    # Step 3: Build prompt with EXPLICIT WRITE [PATH]
    print("\n[PROMPT] Building research prompt...")
    prompt = build_research_prompt()
    print(f"✅ Prompt built (contains WRITE {OUTPUT_FILE})")

    # Step 4: Spawn headless Claude
    print("\n[SPAWN] Starting headless Claude process...")
    success = spawn_headless_claude(prompt, token, OUTPUT_FILE, LOG_FILE)
    if not success:
        return False

    # Step 5: Wait and verify output (non-blocking check)
    print("\n[WAIT] Process spawned. Claude is running in background...")
    print(f"       Check logs: tail -f {LOG_FILE}")
    print(f"       Check output: tail -f {OUTPUT_FILE}")
    print(f"       Research will be saved to: {OUTPUT_FILE}")

    print("\n" + "="*70)
    print("✅ SPAWNED SUCCESSFULLY")
    print("="*70)
    print(f"\nNOTE: Research is running in background. Monitor with:")
    print(f"  tail -f {LOG_FILE}")
    print(f"\nResults will appear in:")
    print(f"  {OUTPUT_FILE}")
    print()

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
