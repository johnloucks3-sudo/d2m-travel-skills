#!/usr/bin/env python3
"""
Headless Claude spawn for Sonnet-model review
Following HEADLESS_CLAUDE_SPAWN_GUIDE.md precisely
"""
import os
import json
import subprocess
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(message)s"
)
logger = logging.getLogger("sonnet_review_spawn")

# Paths
LOG_DIR = Path("/home/john/Thunderbird/logs")
OUTPUT_DIR = Path("/home/john/Thunderbird/output")
CLAUDE_BIN = "/home/john/.local/bin/claude"

# Ensure directories exist
LOG_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Timestamp for unique filenames
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = LOG_DIR / f"claude_sonnet_review_{ts}.log"
output_file = OUTPUT_DIR / f"sonnet_review_{ts}.md"

# Load OAuth token
creds_path = Path.home() / ".claude" / ".credentials.json"
env = dict(os.environ)

if not creds_path.exists():
    logger.error(f"FATAL: Credentials file missing at {creds_path}")
    logger.error("Have Commander re-authenticate via Claude Desktop app")
    exit(1)

try:
    creds = json.loads(creds_path.read_text())
    token = creds.get("claudeAiOauth", {}).get("accessToken")
    if not token:
        logger.error("FATAL: No accessToken in credentials file")
        exit(1)
    env["CLAUDE_CODE_OAUTH_TOKEN"] = token
    logger.info("✅ OAuth token loaded successfully")
except Exception as e:
    logger.error(f"FATAL: Could not load credentials: {e}")
    exit(1)

# Build prompt with EXPLICIT WRITE instruction (per guide)
prompt = f"""
You are performing a sonnet-model review for Commander John Loucks.

TASK: Comprehensive Sonnet-Model Review of ALL Claude Code Enhancements to Thunderbird OS Multi-Model Stack

SPECIFIC REQUIREMENTS:
1. NO CANDIDATE ELIMINATION — analyze, don't filter. Include ALL enhancements even if duplicative
2. Minimum 20 candidates across all domains: persona, tools, MCP, automation, workflow
3. Synthesize patterns — identify enhancement clusters and strategic vectors
4. Prioritize by impact — judge which enhancements deliver 10x vs incremental

SEARCH SOURCES:
- AGENTS.md, CLAUDE.md, opencode_memory.md
- OpsCenter/keyword_router.py — intelligence routing
- core/ enhancements (MCP server, email, communication, intel)
- Personas/hale_cos.md — COS transformation
- scripts/ — automation utilities
- docs/MULTI_MODEL_STACK.md
- OpsCenter/mission_board.json — mission automation
- ALL Claude Code contributions in last 90 days

ANALYSIS FRAMEWORK:
- Impact Score (0-10): Business value × adoption rate
- Technical Maturity: Production-ready vs prototype
- Model-Specific Advantage: Why Claude Sonnet vs Qwen/DeepSeek?
- Commander Cognitive Load Reduction: Does it reduce Commander tasking?

KEY QUESTIONS TO ANSWER:
1. What 3-5 enhancements deliver 10x improvement already?
2. Where have we over-engineered or built "AI for AI"?
3. What 3 vectors represent biggest opportunity for next 90 days?
4. How good is our model routing (Sonnet vs Haiku vs Opus vs DeepSeek)?
5. Where do we risk Claude Code dependence that creates single point of failure?

OUTPUT FORMAT REQUIREMENTS:
- Executive summary with top findings
- Table of all 20+ candidates with scores and analysis
- Pattern synthesis and strategic recommendations
- Risk assessment and dependency analysis

WRITE your complete analysis to {output_file} in this exact format:

# SONNET-MODEL REVIEW: Claude Code Enhancements Analysis
## Date: {datetime.now().strftime('%Y-%m-%d')}

### Executive Summary
[Your 1-2 paragraph summary of key findings]

### Enhancement Catalog (20+ Candidates)
| Enhancement | Domain | Impact Score | Maturity | Model Advantage | Notes |
|-------------|--------|-------------|----------|-----------------|-------|
[Table with all enhancements]

### Pattern Synthesis
- **Cluster 1:** [Description]
- **Cluster 2:** [Description] 
- **Cluster 3:** [Description]

### Strategic Recommendations
1. **Immediate (Next 30 days):** [Actions]
2. **Medium-term (Next 90 days):** [Actions]
3. **Long-term:** [Actions]

### Risk Assessment
- **High Risk:** [Items]
- **Medium Risk:** [Items]
- **Low Risk:** [Items]

### Model Routing Effectiveness
- Current routing score: [X/10]
- Improvement opportunities: [List]

Do NOT output anything to stdout. All output goes to {output_file}.
"""

# Spawn the subprocess
logger.info(f"Spawning headless Claude for sonnet review → {log_file}")
try:
    proc = subprocess.Popen(
        [
            CLAUDE_BIN,
            "-p", prompt,
            "--model", "claude-sonnet-4-6",
            "--output-format", "text"
        ],
        stdout=open(log_file, "w"),
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True,  # CRITICAL: Detaches process
    )
    logger.info(f"✅ Claude spawned successfully (PID {proc.pid})")
    logger.info(f"Output will be written to: {output_file}")
    logger.info(f"Logs available at: {log_file}")
except Exception as e:
    logger.error(f"FATAL: Failed to spawn Claude: {e}")
    exit(1)

# Do NOT wait for process. Exit normally.
logger.info("✅ Spawn successful. Process running in background.")
logger.info(f"COS/Supervisor will monitor at {log_file}")
logger.info("You may exit now.")