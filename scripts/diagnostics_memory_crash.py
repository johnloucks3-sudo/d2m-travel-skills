#!/usr/bin/env python3
"""
Memory Crash Diagnostics for Thunderbird/YOGA
Captures: Qdrant state, process memory, systemd limits, recent crashes
Usage: python3 diagnostics_memory_crash.py
Output: /home/john/Thunderbird/output/memory_crash_diagnostics_TIMESTAMP.md
"""

import json
import subprocess
import datetime
from pathlib import Path
from collections import defaultdict

OUTPUT_DIR = Path("/home/john/Thunderbird/output")
OUTPUT_DIR.mkdir(exist_ok=True)

def run(cmd, shell=False):
    """Run command, return stdout or empty string on failure."""
    try:
        if isinstance(cmd, str) and not shell:
            cmd = cmd.split()
        result = subprocess.run(cmd, capture_output=True, text=True, shell=shell, timeout=10)
        return result.stdout
    except Exception as e:
        return f"[ERROR: {e}]\n"

def format_memory(kb_str):
    """Convert KB to human-readable."""
    try:
        kb = int(kb_str.strip())
        if kb > 1024*1024:
            return f"{kb/(1024*1024):.1f} GB"
        elif kb > 1024:
            return f"{kb/1024:.1f} MB"
        else:
            return f"{kb} KB"
    except:
        return kb_str

# ============================================================================
# SECTION 1: SYSTEM MEMORY STATE
# ============================================================================
report = []
report.append("# THUNDERBIRD MEMORY CRASH DIAGNOSTICS")
report.append(f"**Captured:** {datetime.datetime.now().isoformat()} MT\n")

report.append("## 1. SYSTEM MEMORY STATE (now)\n")
report.append("```")
report.append(run("free -h"))
report.append("```\n")

report.append("**vmstat snapshot (1s interval, 5 samples):**\n")
report.append("```")
report.append(run("vmstat 1 5"))
report.append("```\n")

# ============================================================================
# SECTION 2: TOP MEMORY CONSUMERS
# ============================================================================
report.append("## 2. TOP 15 PROCESSES BY MEMORY\n")
report.append("```")
report.append(run("ps aux --sort=-%mem | head -20"))
report.append("```\n")

# Parse and summarize
proc_lines = run("ps aux --sort=-%mem | head -20").split("\n")
report.append("**Summary (service/daemon focus):**\n")
for line in proc_lines[1:11]:  # Skip header, take top 10
    parts = line.split()
    if len(parts) > 10:
        pid, user, cpu, mem, vsz, rss = parts[1], parts[0], parts[2], parts[3], parts[4], parts[5]
        cmd = " ".join(parts[10:13])  # First 3 words of command
        if float(mem) > 1.0:  # Only highlight >1% memory
            report.append(f"- **{cmd}** (PID {pid}, {mem}% RSS={format_memory(rss)})")
report.append("")

# ============================================================================
# SECTION 3: QDRANT STATE
# ============================================================================
report.append("## 3. QDRANT VECTOR DB (Thunderbird memories)\n")

qdrant_status = run("systemctl --user status qdrant")
report.append(f"**Service status:**\n```\n{qdrant_status}\n```\n")

qdrant_proc = run("ps aux | grep -i qdrant | grep -v grep")
if qdrant_proc:
    report.append("**Running process:**\n```\n" + qdrant_proc + "\n```\n")

    # Extract memory from process line
    parts = qdrant_proc.split()
    if len(parts) > 5:
        mem_pct = parts[3]
        rss = parts[5]
        report.append(f"- Memory usage: {mem_pct}% RSS = {format_memory(rss)}\n")
else:
    report.append("⚠️ **Qdrant not running**\n")

# Check config
qdrant_config = Path("/etc/qdrant/config.yaml")
if qdrant_config.exists():
    report.append(f"**Config (`{qdrant_config}`):**\n")
    config_content = qdrant_config.read_text()
    # Find memory-related lines
    report.append("```yaml")
    for line in config_content.split("\n"):
        if any(kw in line.lower() for kw in ["memory", "cache", "max", "storage"]):
            report.append(line)
    report.append("```\n")

# ============================================================================
# SECTION 4: THUNDERBIRD SYSTEMD UNITS
# ============================================================================
report.append("## 4. THUNDERBIRD SYSTEMD UNITS (memory limits)\n")

units_output = run("systemctl --user list-units --type=service --all | grep -E 'thunder|qdrant|opencode|mcp'")
report.append("**Active units:**\n```\n" + units_output + "\n```\n")

# Check MemoryMax on each
report.append("**Memory ceilings (MemoryMax):**\n")
for unit in ["thunderbird-telegram-gw", "qdrant", "opencode-spsa-monitor"]:
    limits = run(f"systemctl --user show {unit}.service -p MemoryLimit -p MemoryMax")
    if limits.strip():
        report.append(f"- {unit}: {limits.strip()}\n")

# ============================================================================
# SECTION 5: RECENT CRASHES / ERRORS
# ============================================================================
report.append("## 5. RECENT CRASH LOGS (journalctl, last 100 lines)\n")

journal = run("journalctl --user -n 100 -p err --no-pager")
report.append("```\n" + journal + "\n```\n")

# Look for OOM, crashes, segfaults
report.append("**Pattern scan (OOM/crash/segfault):**\n")
for line in journal.split("\n"):
    if any(kw in line.upper() for kw in ["OOM", "CRASH", "SEGFAULT", "KILLED", "MEMORY", "WAVE"]):
        report.append(f"- {line[:120]}\n")

# ============================================================================
# SECTION 6: KDE MEMORY FOOTPRINT (if running)
# ============================================================================
report.append("## 6. KDE PLASMA MEMORY FOOTPRINT\n")

kde_procs = run("ps aux | grep -i kde | grep -v grep")
if kde_procs:
    report.append("**KDE processes running:**\n```\n" + kde_procs + "\n```\n")

    # Sum up KDE memory
    kde_mem_total = 0
    for line in kde_procs.split("\n"):
        parts = line.split()
        if len(parts) > 5:
            try:
                kde_mem_total += int(parts[5])
            except:
                pass
    report.append(f"**Total KDE memory estimate:** {format_memory(str(kde_mem_total))}\n")
else:
    report.append("✅ KDE not running (or minimal footprint)\n")

# ============================================================================
# SECTION 7: RECOMMENDATIONS
# ============================================================================
report.append("## 7. RECOMMENDATIONS\n")

# Analyze and recommend
mem_free = run("free | grep Mem | awk '{print $7}'").strip()
try:
    mem_free_kb = int(mem_free)
    mem_free_pct = (mem_free_kb / 4000000) * 100 if mem_free_kb > 0 else 0  # Rough estimate

    if mem_free_pct < 15:
        report.append("🔴 **CRITICAL:** Free memory <15%. Immediate action needed.\n")
        report.append("- (1) Increase Qdrant MemoryMax ceiling enforcement\n")
        report.append("- (2) Reduce OpenCode worker count\n")
        report.append("- (3) Switch KDE→GNOME (saves 200-300 MB)\n")
    elif mem_free_pct < 25:
        report.append("🟡 **WARNING:** Free memory <25%. Monitor closely.\n")
        report.append("- Consider GNOME switch if KDE is >400 MB\n")
        report.append("- Tune Qdrant cache if >40% of system RAM\n")
    else:
        report.append("✅ **OK:** Free memory >25%. No immediate crisis.\n")
        report.append("- Proactive: set MemoryMax limits on all daemons\n")
except:
    pass

report.append("\n**What crashed 'wave'?**\n")
report.append("- If journalctl shows OOM → increase available RAM or reduce daemon load\n")
report.append("- If segfault → check Wayland/X11 compatibility\n")
report.append("- If service killed → systemd MemoryLimit exceeded\n")

# ============================================================================
# WRITE OUTPUT
# ============================================================================
output_path = OUTPUT_DIR / f"memory_crash_diagnostics_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
output_path.write_text("\n".join(report))

print(f"✅ Diagnostics written to: {output_path}")
print(f"\n📊 Quick summary:")
print(f"   Free memory: {mem_free}")
print(f"   Top process: {run('ps aux --sort=-%mem | head -2 | tail -1').split()[10:13]}")
print(f"   Qdrant status: {'RUNNING' if qdrant_proc else 'NOT RUNNING'}")
print(f"\n📖 Full report: cat {output_path}")
