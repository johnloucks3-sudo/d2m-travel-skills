#!/usr/bin/env python3
"""
Claude Code Only Spawn - New Pattern
Claude Code handles its own OAuth independently
"""
import subprocess
from pathlib import Path
from datetime import datetime

# Setup paths
LOG_DIR = Path("/home/john/Thunderbird/logs")
OUTPUT_DIR = Path("/home/john/Thunderbird/output")
CLAUDE_BIN = "/home/john/.local/bin/claude"

# Ensure directories exist
LOG_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Timestamp for unique filenames
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = LOG_DIR / f"claude_code_review_{ts}.log"
output_file = OUTPUT_DIR / f"sonnet_review_{ts}.md"

# Build the prompt with explicit WRITE instruction
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

WRITE your complete analysis to {output_file} in this exact format:

# SONNET-MODEL REVIEW: Claude Code Enhancements Analysis
## Date: {datetime.now().strftime('%Y-%m-%d')}

### Executive Summary
[1-2 paragraph summary of key findings]

### Enhancement Catalog (20+ Candidates)
| Enhancement | Domain | Impact Score | Maturity | Model Advantage | Notes |
|-------------|--------|-------------|----------|-----------------|-------|
[Table with minimum 20 enhancements]

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

print(f"Spawning Claude Code for sonnet review...")
print(f"Log: {log_file}")
print(f"Output: {output_file}")

# Spawn Claude Code with independent OAuth handling
try:
    proc = subprocess.Popen(
        [
            CLAUDE_BIN,
            "-p", prompt,
            "--model", "claude-sonnet-4-6",
            "--output-format", "text"
        ],
        stdout=open(log_file, "w"),
        stderr=subprocess.STDOUT
    )
    print(f"✅ Claude Code spawned successfully (PID {proc.pid})")
    print(f"🔗 Process hierarchy: OpenCode → Claude Code → Headless Claude")
    print(f"🔐 OAuth: Claude Code handles independently")
    print(f"📁 Output: Will be written to {output_file}")
    print("🚀 Process is now independent - OpenCode can exit")
    
except Exception as e:
    print(f"❌ Failed to spawn Claude Code: {e}")
    exit(1)