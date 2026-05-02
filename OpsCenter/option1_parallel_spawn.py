#!/usr/bin/env python3
"""
OPTION 1 PARALLEL AGENT SPAWNER
Spawns up to 5 agents simultaneously for maximum throughput.
Usage: python3 option1_parallel_spawn.py --preset kuklinski_loucks_mcleod
"""
import subprocess
import os
import json
from pathlib import Path
from datetime import datetime
import argparse
import sys

class ParallelAgentSpawner:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = Path("/home/john/Thunderbird/logs")
        self.output_dir = Path("/home/john/Thunderbird/output")
        self.log_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        self.spawn_log = self.log_dir / f"parallel_spawn_{self.timestamp}.log"
        self.pids = []

    def log(self, message):
        """Log message to both stdout and file."""
        print(message)
        with open(self.spawn_log, 'a') as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")

    def spawn_gemini_task(self, task_name: str, prompt: str, output_file: str):
        """Spawn a Gemini research task."""
        log_file = self.log_dir / f"{task_name}.log"

        script = f"""
import google.generativeai as genai
import os
genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.0-flash')

prompt = '''{prompt}'''

response = model.generate_content(prompt)
with open('{output_file}', 'w') as f:
    f.write(response.text)

print(f"✓ {{task_name}} complete: {{output_file}}")
        """

        env = dict(os.environ)
        if 'GEMINI_API_KEY' not in env:
            self.log(f"❌ {task_name}: GEMINI_API_KEY not set")
            return None

        try:
            proc = subprocess.Popen(
                ['python3', '-c', script],
                stdout=open(log_file, 'w'),
                stderr=subprocess.STDOUT,
                env=env,
                start_new_session=True,
            )
            self.log(f"✓ {task_name} spawned (PID {proc.pid}) → {output_file}")
            self.pids.append((task_name, proc.pid, output_file))
            return proc.pid
        except Exception as e:
            self.log(f"❌ {task_name} spawn failed: {e}")
            return None

    def spawn_aider_task(self, task_name: str, files: list, instruction: str):
        """Spawn an Aider editing task."""
        log_file = self.log_dir / f"{task_name}.log"

        files_str = ' '.join(files)

        env = dict(os.environ)
        env['AIDER_BACKEND'] = 'gemini'

        try:
            proc = subprocess.Popen(
                f'aider --no-auto-commits --yes {files_str} -m "{instruction}"',
                shell=True,
                stdout=open(log_file, 'w'),
                stderr=subprocess.STDOUT,
                env=env,
                start_new_session=True,
            )
            self.log(f"✓ {task_name} spawned (PID {proc.pid}) → {len(files)} files")
            self.pids.append((task_name, proc.pid, f"{len(files)} files"))
            return proc.pid
        except Exception as e:
            self.log(f"❌ {task_name} spawn failed: {e}")
            return None

    def spawn_claude_task(self, task_name: str, prompt: str, output_file: str):
        """Spawn a Claude Max task."""
        log_file = self.log_dir / f"{task_name}.log"

        full_prompt = f"""{prompt}

WRITE your complete response to {output_file}
Do NOT output to stdout.
        """

        env = dict(os.environ)

        try:
            proc = subprocess.Popen(
                ['/home/john/.local/bin/claude', '-p', full_prompt, '--model', 'claude-opus-4-7'],
                stdout=open(log_file, 'w'),
                stderr=subprocess.STDOUT,
                env=env,
                start_new_session=True,
            )
            self.log(f"✓ {task_name} spawned (PID {proc.pid}) → {output_file}")
            self.pids.append((task_name, proc.pid, output_file))
            return proc.pid
        except Exception as e:
            self.log(f"❌ {task_name} spawn failed: {e}")
            return None

    def preset_kuklinski_loucks_mcleod(self):
        """Preset: Research for 3 top clients + document cleanup."""
        self.log("\n=== OPTION 1 PARALLEL EXECUTION ===")
        self.log("Preset: Kuklinski + Loucks + McLeod")
        self.log("")

        # Gemini Research Tasks (free)
        self.spawn_gemini_task(
            "gemini_kuklinski_research",
            """
Research cruise options for luxury market, specifically for a Viking audience.
Focus on: current ship deployments, premium cabins, enrichment programs, pricing.
Write in analyst style.
            """,
            str(self.output_dir / "research_kuklinski_viking.txt")
        )

        self.spawn_gemini_task(
            "gemini_loucks_research",
            """
Research Regent Seven Seas Grandeur positioning and Panama Canal itinerary appeal.
Focus on: cabin categories, dining venues, shore excursions, competitive advantages.
Write in analyst style.
            """,
            str(self.output_dir / "research_loucks_grandeur.txt")
        )

        self.spawn_gemini_task(
            "gemini_mcleod_research",
            """
Research Silversea positioning in luxury market and recent ship innovations.
Focus on: technology, service model, pricing vs competitors, target demographic.
Write in analyst style.
            """,
            str(self.output_dir / "research_mcleod_silversea.txt")
        )

        # Aider Document Task (cheap)
        dossier_files = [
            "/home/john/Thunderbird/dossiers/Kuklinski_Kyle.md",
            "/home/john/Thunderbird/dossiers/Loucks_John.md",
        ]

        self.spawn_aider_task(
            "aider_dossier_cleanup",
            dossier_files,
            "Standardize formatting: headers (###), bullet lists, remove duplicate sections"
        )

        # Claude Max Strategy Task
        self.spawn_claude_task(
            "claude_strategy_analysis",
            """
Based on current cruise market trends and client profiles:
1. Recommend cabin upgrades for Kuklinski (Viking) and Loucks (Regent)
2. Suggest specialty dining venues for each
3. Identify upsell opportunities

Be specific and quantify where possible.
            """,
            str(self.output_dir / "strategy_cabin_dining_analysis.txt")
        )

        self.log("")
        self.log(f"✓ Spawned {len(self.pids)} agents in parallel")
        self.log(f"📊 Spawn log: {self.spawn_log}")
        self.log("")
        self.print_status()

    def print_status(self):
        """Print current spawn status."""
        self.log("\n--- AGENT STATUS ---")
        for i, (name, pid, target) in enumerate(self.pids, 1):
            self.log(f"{i}. {name} (PID {pid}) → {target}")
        self.log("\nTo monitor: tail -f /home/john/Thunderbird/logs/*.log")
        self.log("Results will appear in: /home/john/Thunderbird/output/")

def main():
    parser = argparse.ArgumentParser(description='Option 1 Parallel Agent Spawner')
    parser.add_argument('--preset', choices=['kuklinski_loucks_mcleod'], default='kuklinski_loucks_mcleod',
                        help='Task preset')
    args = parser.parse_args()

    spawner = ParallelAgentSpawner()

    if args.preset == 'kuklinski_loucks_mcleod':
        spawner.preset_kuklinski_loucks_mcleod()

    spawner.log(f"\n✓ All tasks spawned. Execution log: {spawner.spawn_log}")

if __name__ == "__main__":
    main()
