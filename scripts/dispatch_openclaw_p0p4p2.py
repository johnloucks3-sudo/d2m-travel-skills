#!/usr/bin/env python3
"""
OpenClaw P0/P4/P2 Implementation Dispatch
Spawns OpenCode (DeepSeek V3.1) to implement Skill Builder, Multi-Agent Spawn, Heartbeat
Output: /home/john/Thunderbird/output/OPENCLAW_P0P4P2_BUILD.md
"""

import sys
from pathlib import Path

# Add Thunderbird to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from OpsCenter.opencode_headless_claude_dispatch import dispatch_to_headless_claude

OPENCLAW_PROMPT = """You are DeepSeek V3.1 running as an autonomous code generation agent for Dreams2Memories Travel, LLC (Thunderbird OS).

MISSION: Implement 3 OpenClaw architectural patterns (P0, P4, P2) in Thunderbird codebase.

CRITICAL CONSTRAINTS:
- NO client-facing output without Commander approval (WF-17 gate)
- NO replacement of existing systems — layer on top only
- All generated code MUST be tested before commit
- All new files go to ~/Thunderbird/core/ (appropriate subdirectory)
- All tests go to ~/Thunderbird/tests/
- Output structure: WRITE all code, tests, and implementation log to /home/john/Thunderbird/output/OPENCLAW_P0P4P2_BUILD.md

IMPLEMENTATION ORDER: P0 → P4 → P2 (this order; P0 has fewest dependencies)

---

## P0: MESSAGING-BASED SKILL BUILDER

**CONTEXT:**
- Core skill builder engine exists: ~/Thunderbird/core/ai_infra/thunderbird_skill_builder.py
- Safety constraints: ~/Thunderbird/core/ai_infra/skill_builder_config.py
- Skills API: ~/Thunderbird/core/learning/thunderbird_skills_api.py
- MCP server: ~/Thunderbird/core/mcp/travel_mcp_server.py (line 52 already imports register_skills_tools)

**TASK:**
Create `/build-skill` Telegram C2 command handler + MCP tool registration.

**FILE 1: Add to ~/Thunderbird/core/communication/thunderbird_telegram_c2.py**

Function signature:
```python
async def cmd_build_skill(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    \"\"\"
    Handler for /build-skill "description" command.
    Spawns Sonnet → generates skill code → validates → registers in MCP → responds to Commander.
    \"\"\"
```

Requirements:
1. Extract skill description from message text
2. Call ThunderbirdSkillBuilder.classify_requirement(description)
3. Call ThunderbirdSkillBuilder.generate_skill_code(requirement, model="claude-sonnet-4-6")
4. Validate against skill_builder_config.py constraints
5. Write to ~/Thunderbird/core/{domain}/ based on classification
6. Call register_skill_builder_tools() in MCP server
7. Send response with usage example

**FILE 2: Add function to ~/Thunderbird/core/ai_infra/thunderbird_skill_builder.py**

Function signature:
```python
def register_skill_builder_tools() -> dict:
    \"\"\"
    Register skill builder itself as MCP tools.
    Returns: {"tools": [skill_builder_tool_1, skill_builder_tool_2, ...]}
    Tools: classify_requirement, generate_skill_code, validate_skill, register_skill
    \"\"\"
```

**FILE 3: Modify ~/Thunderbird/core/mcp/travel_mcp_server.py**

Add to server initialization:
```python
from core.ai_infra.thunderbird_skill_builder import register_skill_builder_tools

# In setup_tools():
builder_tools = register_skill_builder_tools()
self.tools.update(builder_tools)
```

**TEST VECTORS (test in ~/Thunderbird/tests/test_p0_skill_builder.py):**

1. Test `/build-skill "add a function to check if a flight is available"` → generates Python skill → validates → registers
2. Test skill with unsafe code (eval, subprocess) → rejected by validator
3. Test skill registration in MCP → tool callable via MCP interface
4. Test hot-reload without restarting MCP server

Expected: 4/4 PASS

---

## P4: MULTI-AGENT SPAWN FROM CHAT

**CONTEXT:**
- Headless spawn wrapper: ~/Thunderbird/core/ai_infra/thunderbird_headless_spawn.py
- A2A protocol: ~/Thunderbird/core/ai_infra/thunderbird_a2a.py
- Telegram C2: ~/Thunderbird/core/communication/thunderbird_telegram_c2.py

**TASK:**
Create `/spawn N "task description"` command + multi-agent orchestration + result aggregation.

**FILE 1: NEW FILE ~/Thunderbird/core/ai_infra/thunderbird_multi_agent.py**

Functions:
```python
class MultiAgentOrchestrator:
    \"\"\"Spawn N OpenCode agents, aggregate results.\"\"\"

    async def spawn_agents(self, n: int, task: str, variations: list) -> list:
        \"\"\"Spawn N OpenCode instances with task variations.\"\"\"

    async def aggregate_results(self, results: list) -> str:
        \"\"\"Consolidate N agent outputs into one report.\"\"\"

    def _generate_variation(self, task: str, index: int) -> str:
        \"\"\"Create task variation for agent N.\"\"\"
```

Requirements:
1. Spawn N headless Claude instances (DeepSeek V3.1)
2. Each gets task + variation (e.g., "analyze cruise pricing [VARIATION: focus on luxury lines]")
3. Collect outputs from N processes
4. Aggregate: consolidate findings, remove duplicates, summarize differences
5. Return single formatted report

**FILE 2: Add to ~/Thunderbird/core/communication/thunderbird_telegram_c2.py**

Function signature:
```python
async def cmd_spawn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    \"\"\"
    Handler for /spawn N "description" command.
    Spawns N OpenCode agents, aggregates results, sends back.
    \"\"\"
```

Requirements:
1. Parse: `/spawn 3 "analyze cruise line pricing by segment"`
2. Extract N=3, task="analyze cruise line pricing by segment"
3. Call MultiAgentOrchestrator.spawn_agents(3, task)
4. Wait for all 3 results (timeout: 10 min)
5. Aggregate via MultiAgentOrchestrator.aggregate_results()
6. Format as table/summary
7. Send to Commander

**TEST VECTORS (test in ~/Thunderbird/tests/test_p4_multi_agent.py):**

1. Test `/spawn 2 "compare Regent vs Silversea pricing"` → spawns 2 agents → aggregates
2. Test timeout: agent runs >10min → returns partial results
3. Test result deduplication: both agents find same fact → appears once in output
4. Test variation generation: each agent gets different focus area

Expected: 4/4 PASS

---

## P2: PROACTIVE HEARTBEAT ASSESSMENTS

**CONTEXT:**
- Morning briefing exists: ~/Thunderbird/agents/thunderbird_morning_briefing.py
- Usage monitor: ~/Thunderbird/core/ops/thunderbird_usage_monitor.py
- Mission board: ~/Thunderbird/OpsCenter/mission_board.json
- Dossiers: ~/Thunderbird/dossiers/*.md

**TASK:**
Create systemd timer (every 2 hours) that scans system health + mission board + dossiers + API quotas. Generate optimization recommendations. Alert Commander via Telegram if action needed.

**FILE 1: NEW FILE ~/Thunderbird/core/ops/thunderbird_heartbeat.py**

Functions:
```python
class HeartbeatAssessment:
    \"\"\"Proactive 2-hour heartbeat assessment.\"\"\"

    async def scan_inbox_queues(self) -> dict:
        \"\"\"Check opencode_inbox, claude_inbox queue depth.\"\"\"

    async def scan_mission_board(self) -> dict:
        \"\"\"Detect stale missions (>24h no update).\"\"\"

    async def scan_dossiers(self) -> dict:
        \"\"\"Detect FPD alerts (≤30 days), missing required fields.\"\"\"

    async def scan_system_health(self) -> dict:
        \"\"\"Check disk usage, API quotas, service status.\"\"\"

    async def generate_recommendations(self, findings: dict) -> str:
        \"\"\"Analyze findings, return 3-5 prioritized actions.\"\"\"

    async def alert_commander(self, findings: dict, recommendations: str):
        \"\"\"Send Telegram alert if action-critical findings detected.\"\"\"
```

Requirements:
1. Scan inbox queue depths (count unprocessed items in opencode_inbox.md, claude_inbox.md)
2. Scan mission board: missions with updated_at >24h old → flag as "stale, needs check-in"
3. Scan dossiers: FPD dates within ≤30 days → HIGH priority alert; missing required fields → log
4. Scan system: `/df` disk usage (alert if >85%), check API quota usage (OpenRouter, Anthropic), verify key services running (MCP, Telegram, tasking watcher)
5. Generate recommendations: "Queue depth increasing (15→22 items), recommend immediate dispatch" or "McLeod FPD in 18 days, send final payment reminder"
6. Send Telegram to Commander only if critical (FPD <30 days, disk >85%, service down)

**FILE 2: NEW FILE ~/Thunderbird/deploy/d2m-heartbeat.timer**

```ini
[Unit]
Description=Thunderbird Heartbeat Assessment Timer
After=network-online.target

[Timer]
OnBootSec=5min
OnUnitActiveSec=2h
Unit=d2m-heartbeat.service

[Install]
WantedBy=timers.target
```

**FILE 3: NEW FILE ~/Thunderbird/deploy/d2m-heartbeat.service**

```ini
[Unit]
Description=Thunderbird Heartbeat Assessment Service
After=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /home/john/Thunderbird/core/ops/thunderbird_heartbeat.py
User=john
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**TEST VECTORS (test in ~/Thunderbird/tests/test_p2_heartbeat.py):**

1. Test inbox queue scan: create 5 items in opencode_inbox.md → heartbeat detects "queue depth 5"
2. Test mission board stale detection: create mission with updated_at >24h old → flagged
3. Test dossier FPD alert: create dossier with FPD=2026-05-15 (within 30 days) → HIGH alert
4. Test system health: mock `/df` output at 87% → alert generated
5. Test recommendation generation: given findings dict → produces 3-5 recommendations ranked by priority

Expected: 5/5 PASS

---

## IMPLEMENTATION CHECKLIST

- [ ] P0 Skill Builder: 3 files, 4 tests
- [ ] P4 Multi-Agent: 2 files, 4 tests
- [ ] P2 Heartbeat: 3 files, 5 tests
- [ ] All files written to ~/Thunderbird/output/OPENCLAW_P0P4P2_BUILD.md
- [ ] All tests run and report PASS/FAIL
- [ ] No client-facing outputs generated
- [ ] No existing systems modified (only additions/layering)

---

## OUTPUT STRUCTURE

WRITE complete build output to:
**~/Thunderbird/output/OPENCLAW_P0P4P2_BUILD.md**

Format:
```
# OpenClaw P0/P4/P2 Implementation Build
Date: [timestamp]
Status: [COMPLETE | PARTIAL | FAILED]

## P0: Skill Builder
- Files: [list]
- Tests: [4/4 PASS / details]
- Implementation: [code blocks]

## P4: Multi-Agent Spawn
- Files: [list]
- Tests: [4/4 PASS / details]
- Implementation: [code blocks]

## P2: Heartbeat Assessment
- Files: [list]
- Tests: [5/5 PASS / details]
- Implementation: [code blocks]

## Integration Checklist
- [x/y] Files created
- [x/y] Tests passing
- [x/y] No client-facing output
- [x/y] No system replacement

## Next Steps
[Actions for Commander to integrate into Thunderbird]
```
"""

def main():
    """Dispatch OpenClaw P0/P4/P2 implementation via direct headless spawn."""
    import subprocess
    import json
    import os
    from datetime import datetime

    output_file = Path("/home/john/Thunderbird/output/OPENCLAW_P0P4P2_BUILD.md")
    log_dir = Path("/home/john/Thunderbird/logs")
    log_file = log_dir / f"openclaw_p0p4p2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    output_file.parent.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("OpenClaw P0/P4/P2 Implementation Dispatch")
    print("=" * 70)
    print(f"Task: Implement Skill Builder, Multi-Agent Spawn, Heartbeat")
    print(f"Output: {output_file}")
    print(f"Logs: {log_file}")
    print()

    try:
        # Load OAuth token
        creds_path = Path.home() / ".claude" / ".credentials.json"
        env = dict(os.environ)

        if creds_path.exists():
            creds = json.loads(creds_path.read_text())
            token = creds.get("claudeAiOauth", {}).get("accessToken")
            if token:
                env["CLAUDE_CODE_OAUTH_TOKEN"] = token
                print("✅ OAuth token loaded")
            else:
                print("⚠️  No OAuth token in credentials file")
        else:
            print(f"⚠️  Credentials file not found at {creds_path}")

        # Build prompt with WRITE instruction
        prompt = OPENCLAW_PROMPT + f"\n\nWRITE all output to {output_file}"

        # Spawn headless Claude with explicit Haiku model
        proc = subprocess.Popen(
            [
                "/home/john/.local/bin/claude",
                "-p", prompt,
                "--model", "claude-haiku-4-5-20251001"
            ],
            stdout=open(log_file, "w"),
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True
        )

        print(f"✅ Task spawned with PID {proc.pid}")
        print()
        print("Monitor progress:")
        print(f"  tail -f {log_file}")
        print()
        print("When complete, review output:")
        print(f"  cat {output_file}")
        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
