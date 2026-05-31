"""
OpenCode Headless Grok Build Spawn Module
=========================================
Reusable wrapper for spawning OpenCode Grok Build as detached headless process.

Usage:
    from OpsCenter.opencode_headless_grok_spawn import spawn_grok, GrokSpawnConfig

    # Simple spawn (auto-detached, async)
    result = spawn_grok("What is the optimal token compression ratio?")
    print(f"PID: {result.pid}, Log: {result.log_path}")

    # Blocking spawn (wait for completion)
    result = spawn_grok("Your question", blocking=True, timeout=60)
    print(f"Exit code: {result.exit_code}")
    print(result.output)

    # Custom model
    result = spawn_grok("Question", model="xai/grok-4.20-0309-reasoning")

    # With fallback
    result = spawn_grok("Question", fallback_model="deepseek/deepseek-chat")
"""

import subprocess
import os
import sys
import re
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class SpawnMode(Enum):
    """Spawn execution mode."""
    ASYNC = "async"  # Detached, returns immediately
    BLOCKING = "blocking"  # Wait for completion


@dataclass
class GrokSpawnConfig:
    """Configuration for Grok headless spawn."""
    model: str = "xai/grok-build-0.1"
    fallback_model: Optional[str] = "deepseek/deepseek-chat"
    mode: SpawnMode = SpawnMode.ASYNC
    timeout: Optional[int] = None  # Blocking mode only
    log_dir: Path = None  # Defaults to /tmp
    log_prefix: str = "opencode_grok"
    capture_output: bool = True
    verbose: bool = False

    def __post_init__(self):
        if self.log_dir is None:
            self.log_dir = Path("/tmp")


@dataclass
class GrokSpawnResult:
    """Result of Grok spawn operation."""
    success: bool
    pid: Optional[int] = None
    log_path: Path = None
    output: str = ""
    exit_code: Optional[int] = None
    error: Optional[str] = None
    model_used: str = ""
    duration_sec: float = 0.0

    def __str__(self):
        if self.success:
            if self.pid:
                return f"✓ PID {self.pid} | Log: {self.log_path} | Model: {self.model_used}"
            else:
                return f"✓ Exit {self.exit_code} | {self.model_used} | {self.duration_sec:.1f}s"
        else:
            return f"❌ {self.error}"


class OpenCodeHeadlessGrokSpawn:
    """Headless Grok Build spawn manager."""

    def __init__(self, config: Optional[GrokSpawnConfig] = None):
        """Initialize spawn manager.

        Args:
            config: GrokSpawnConfig instance (uses defaults if None)
        """
        self.config = config or GrokSpawnConfig()
        self.opencode_bin = Path.home() / ".opencode" / "bin" / "opencode"
        self.thunderbird_dir = Path.home() / "Thunderbird"
        self._validate_setup()

    def _validate_setup(self) -> None:
        """Validate OpenCode binary and environment."""
        if not self.opencode_bin.exists():
            raise FileNotFoundError(f"OpenCode binary not found: {self.opencode_bin}")

        if not self.thunderbird_dir.exists():
            raise FileNotFoundError(f"Thunderbird directory not found: {self.thunderbird_dir}")

    def _load_env(self) -> Dict[str, str]:
        """Load environment variables with XAI_API_KEY.

        Tries:
        1. Existing XAI_API_KEY in environment
        2. Load from .env file in Thunderbird
        3. Raise error if not found
        """
        env = dict(os.environ)

        # Check if already set
        if "XAI_API_KEY" in env:
            if self.config.verbose:
                print("✓ XAI_API_KEY found in environment")
            return env

        # Try to load from .env
        env_file = self.thunderbird_dir / ".env"
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("XAI_API_KEY="):
                        key_val = line.split("=", 1)[1].strip('"').strip("'")
                        env["XAI_API_KEY"] = key_val
                        if self.config.verbose:
                            print(f"✓ XAI_API_KEY loaded from {env_file}")
                        return env

        raise EnvironmentError(
            f"XAI_API_KEY not found in environment or {env_file}. "
            "Set XAI_API_KEY environment variable or add to .env file."
        )

    def _select_model(self) -> tuple[str, str]:
        """Select primary model and fallback.

        Returns:
            (primary_model, fallback_model) tuple
        """
        primary = self.config.model
        fallback = self.config.fallback_model or "deepseek/deepseek-chat"

        if self.config.verbose:
            print(f"  Primary: {primary}")
            print(f"  Fallback: {fallback}")

        return primary, fallback

    def _generate_log_path(self) -> Path:
        """Generate unique log file path."""
        timestamp = int(time.time() * 1000)  # Millisecond precision
        log_name = f"{self.config.log_prefix}_{timestamp}.log"
        return self.config.log_dir / log_name

    def spawn(self, question: str) -> GrokSpawnResult:
        """Spawn OpenCode Grok Build process.

        Args:
            question: The question/prompt to send to Grok

        Returns:
            GrokSpawnResult with status, PID, log path, and output
        """
        start_time = time.time()

        try:
            # Setup
            env = self._load_env()
            primary_model, fallback_model = self._select_model()
            log_path = self._generate_log_path()

            if self.config.verbose:
                print(f"\n🚀 Spawning OpenCode Grok Build")
                print(f"  Model: {primary_model}")
                print(f"  Mode: {self.config.mode.value}")
                print(f"  Log: {log_path}")
                print(f"  Question: {question[:60]}..." if len(question) > 60 else f"  Question: {question}")

            # Spawn process
            with open(log_path, "w") as log_file:
                proc = subprocess.Popen(
                    [str(self.opencode_bin), "run", "-m", primary_model, question],
                    stdout=log_file if self.config.capture_output else None,
                    stderr=subprocess.STDOUT if self.config.capture_output else None,
                    env=env,
                    start_new_session=True,  # Detach (critical for async mode)
                    cwd=str(self.thunderbird_dir)
                )

            pid = proc.pid

            # Async mode (return immediately)
            if self.config.mode == SpawnMode.ASYNC:
                duration = time.time() - start_time
                result = GrokSpawnResult(
                    success=True,
                    pid=pid,
                    log_path=log_path,
                    model_used=primary_model,
                    duration_sec=duration
                )
                if self.config.verbose:
                    print(f"✓ {result}")
                return result

            # Blocking mode (wait for completion)
            timeout = self.config.timeout or 120
            try:
                exit_code = proc.wait(timeout=timeout)
                duration = time.time() - start_time

                # Read output
                output = ""
                if self.config.capture_output and log_path.exists():
                    output = log_path.read_text()
                    # Clean ANSI codes
                    output = re.sub(r'\x1b\[[0-9;]*m', '', output).strip()

                result = GrokSpawnResult(
                    success=exit_code == 0,
                    pid=pid,
                    log_path=log_path,
                    output=output,
                    exit_code=exit_code,
                    model_used=primary_model,
                    duration_sec=duration
                )

                if self.config.verbose:
                    if exit_code == 0:
                        print(f"✓ Completed in {duration:.1f}s | Exit {exit_code}")
                    else:
                        print(f"⚠ Exit {exit_code} | {duration:.1f}s")

                return result

            except subprocess.TimeoutExpired:
                proc.kill()
                duration = time.time() - start_time
                return GrokSpawnResult(
                    success=False,
                    pid=pid,
                    log_path=log_path,
                    error=f"Process timeout after {timeout}s",
                    model_used=primary_model,
                    duration_sec=duration
                )

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            if self.config.verbose:
                print(f"❌ Spawn error: {error_msg}")
            return GrokSpawnResult(
                success=False,
                error=error_msg,
                duration_sec=duration
            )


# Module-level convenience functions

_global_spawn = None

def _get_global_spawn(config: Optional[GrokSpawnConfig] = None) -> OpenCodeHeadlessGrokSpawn:
    """Get or create global spawn instance."""
    global _global_spawn
    if _global_spawn is None or config is not None:
        _global_spawn = OpenCodeHeadlessGrokSpawn(config)
    return _global_spawn


def spawn_grok(
    question: str,
    model: str = "xai/grok-build-0.1",
    blocking: bool = False,
    timeout: Optional[int] = None,
    verbose: bool = False
) -> GrokSpawnResult:
    """Spawn Grok Build and return result.

    Args:
        question: The prompt/question for Grok
        model: Model identifier (default: xai/grok-build-0.1)
        blocking: Wait for completion (default: False, async detached)
        timeout: Timeout in seconds for blocking mode (default: 120)
        verbose: Print debug output (default: False)

    Returns:
        GrokSpawnResult with status and output

    Example:
        # Async (fire-and-forget)
        result = spawn_grok("What's the best token optimization strategy?")
        print(f"Running as PID {result.pid}, check {result.log_path} for output")

        # Blocking (wait for answer)
        result = spawn_grok("Question", blocking=True, timeout=60)
        print(result.output)
    """
    config = GrokSpawnConfig(
        model=model,
        mode=SpawnMode.BLOCKING if blocking else SpawnMode.ASYNC,
        timeout=timeout,
        verbose=verbose
    )
    spawner = _get_global_spawn(config)
    return spawner.spawn(question)


def spawn_grok_custom(config: GrokSpawnConfig, question: str) -> GrokSpawnResult:
    """Spawn Grok with custom configuration.

    Args:
        config: GrokSpawnConfig instance
        question: The prompt/question

    Returns:
        GrokSpawnResult

    Example:
        config = GrokSpawnConfig(
            model="xai/grok-4.20-0309-reasoning",
            mode=SpawnMode.BLOCKING,
            timeout=60,
            verbose=True
        )
        result = spawn_grok_custom(config, "Your question")
    """
    spawner = _get_global_spawn(config)
    return spawner.spawn(question)


if __name__ == "__main__":
    # Test script
    import argparse

    parser = argparse.ArgumentParser(description="Test OpenCode headless Grok spawn")
    parser.add_argument("question", nargs="*", help="Question for Grok")
    parser.add_argument("--model", default="xai/grok-build-0.1", help="Grok model")
    parser.add_argument("--blocking", action="store_true", help="Block until completion")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout (blocking mode)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    question = " ".join(args.question) or "List three ways to optimize token usage in AI systems."

    result = spawn_grok(
        question,
        model=args.model,
        blocking=args.blocking,
        timeout=args.timeout,
        verbose=args.verbose
    )

    print(f"\n{result}\n")

    if result.output:
        print("Output:")
        print(result.output)
