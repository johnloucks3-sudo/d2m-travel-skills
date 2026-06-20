#!/usr/bin/env python3
"""
dispatch_opencode.py — One-shot CLI for headless OpenCode spawning.

The CORRECT entrypoint for any agent (Claude Code, Telegram, shell scripts,
watcher) that needs to dispatch a task to headless OpenCode.

AVOIDS shell quoting issues — uses subprocess.Popen with a clean argument
vector. No $variable interpolation surprises, no --cwd vs --dir confusion.

BACKGROUND MODE (default): prompt MUST include a 'WRITE TO <path>' instruction
so the model writes output via bash. Returns PID immediately.

FOREGROUND MODE: blocks until done, extracts the text response from NDJSON
output stream. Best for short verification tasks.

USAGE:

  # Background (default) — prompt must include WRITE TO instruction:
  python3 OpsCenter/dispatch_opencode.py \\
      --task "my_task" \\
      --output /home/john/Thunderbird/output/task.md \\
      --prompt "Research X. WRITE your findings to /home/john/Thunderbird/output/task.md"

  # Prompt from file (preferred for long prompts):
  python3 OpsCenter/dispatch_opencode.py \\
      --task "my_task" \\
      --output /home/john/Thunderbird/output/task.md \\
      --prompt-file /tmp/prompt.txt

  # Foreground — returns text response in output_file:
  python3 OpsCenter/dispatch_opencode.py \\
      --task "quick_check" \\
      --output /tmp/check.md \\
      --prompt "Say hi" \\
      --foreground

Exit codes: 0=ok, 1=spawn/exec failure, 2=invalid args.

RETURNS JSON to stdout: {"status":"SPAWNED|COMPLETED|FAILED", ...}
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("dispatch_opencode")

OPENCODE_BIN = Path.home() / ".opencode" / "bin" / "opencode"
WORKDIR = ROOT
LOGS_DIR = ROOT / "logs"
OUTPUT_DIR = ROOT / "output"

MODEL_CHAIN = [
    "anthropic/claude-haiku-4-5-20251001",
    "anthropic/claude-sonnet-4-6",
]


def _try_model(binary: Path, model: str) -> bool:
    try:
        result = subprocess.run(
            [str(binary), "run", "-m", model, "--format", "json", "--dir", str(WORKDIR), "echo ok"],
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def _resolve_model(binary: Path) -> str:
    for model in MODEL_CHAIN:
        if _try_model(binary, model):
            logger.info("Using model: %s", model)
            return model
    return MODEL_CHAIN[0]


def _extract_text_from_ndjson(raw: str) -> str:
    """Extract the final 'text' event content from NDJSON output stream."""
    lines = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("type") == "text":
            part = event.get("part", {})
            text = part.get("text", "") if isinstance(part, dict) else ""
            if text:
                lines.append(text)
    return "\n".join(lines).strip()


def dispatch_opencode(
    prompt: str,
    output_file: str,
    task_name: str = "task",
    model: str | None = None,
    foreground: bool = False,
) -> dict:
    LOGS_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"opencode_{task_name}_{ts}.log"
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    binary = OPENCODE_BIN
    if not binary.exists():
        return {"status": "FATAL_BIN", "error": f"OpenCode binary not found at {binary}", "can_retry": False, "log_file": str(log_file)}

    resolved_model = model or _resolve_model(binary)

    cmd = [
        str(binary),
        "run",
        "-m", resolved_model,
        "--dir", str(WORKDIR),
        "--format", "json",
        prompt,
    ]

    logger.info("Dispatching OpenCode: task=%s model=%s foreground=%s", task_name, resolved_model, foreground)

    if foreground:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired:
            return {"status": "TIMEOUT", "error": "Exceeded 600s timeout", "can_retry": True, "log_file": str(log_file)}
        except Exception as e:
            return {"status": "FAILED", "error": str(e), "can_retry": True, "log_file": str(log_file)}

        with open(log_file, "w") as f:
            f.write(proc.stdout)
        if proc.stderr:
            with open(log_file, "a") as f:
                f.write(f"\n\nSTDERR:\n{proc.stderr}")

        text = _extract_text_from_ndjson(proc.stdout)
        if text:
            output_path.write_text(text)

        return {
            "status": "COMPLETED",
            "pid": proc.pid if hasattr(proc, 'pid') else 0,
            "log_file": str(log_file),
            "output_file": str(output_path),
            "model": resolved_model,
            "exit_code": proc.returncode,
            "response_length": len(text),
        }

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=open(log_file, "w"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    except Exception as e:
        return {"status": "FAILED", "error": str(e), "can_retry": True, "log_file": str(log_file)}

    logger.info("Background spawn launched: %s (PID %d)", task_name, proc.pid)
    return {
        "status": "SPAWNED",
        "pid": proc.pid,
        "log_file": str(log_file),
        "output_file": str(output_file),
        "model": resolved_model,
        "task_name": task_name,
        "background": True,
        "note": "Background mode — prompt must include WRITE TO path instruction.",
    }


def main():
    parser = argparse.ArgumentParser(description="Headless OpenCode dispatcher")
    parser.add_argument("--task", default="task", help="Task name (for logging)")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--prompt", help="Inline prompt text")
    parser.add_argument("--prompt-file", help="Path to prompt file")
    parser.add_argument("--model", help="Override model (default: auto-chain)")
    parser.add_argument("--foreground", action="store_true", help="Wait for completion (extracts text from NDJSON)")
    args = parser.parse_args()

    if args.prompt and args.prompt_file:
        print(json.dumps({"status": "FATAL_ARGS", "error": "Use --prompt OR --prompt-file, not both."}), file=sys.stderr)
        sys.exit(2)

    prompt = args.prompt
    if args.prompt_file:
        try:
            prompt = Path(args.prompt_file).read_text()
        except Exception as e:
            print(json.dumps({"status": "FATAL_ARGS", "error": f"Cannot read --prompt-file: {e}"}), file=sys.stderr)
            sys.exit(2)

    if not prompt:
        print(json.dumps({"status": "FATAL_ARGS", "error": "Provide --prompt or --prompt-file."}), file=sys.stderr)
        sys.exit(2)

    result = dispatch_opencode(
        prompt=prompt,
        output_file=args.output,
        task_name=args.task,
        model=args.model,
        foreground=args.foreground,
    )

    print(json.dumps(result, indent=2))
    if result.get("status") in ("FATAL_BIN", "FATAL_ARGS"):
        sys.exit(1)


if __name__ == "__main__":
    main()
