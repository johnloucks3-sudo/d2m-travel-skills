import json
import logging
import os
import subprocess
import time
from pathlib import Path

from core.ai_infra.adapters.base import AdapterResult, HealthState

log = logging.getLogger("adapter.claude_max")

CLAUDE_BIN = "/home/john/.local/bin/claude"
THUNDERBIRD_DIR = "/home/john/Thunderbird"
ENGINE_TIMEOUT = 300
CLAUDE_CREDS = Path.home() / ".claude" / ".credentials.json"


class ClaudeMaxOAuthAdapter:
    """Claude via MAX OAuth. FLAG-tier only — reserved for Hale-CC, JET, TALON."""

    def __init__(self, name: str, model_id: str, cost_pool: str, tier_capabilities: list[str] | None = None):
        self.name = name
        self.model_id = model_id
        self.cost_pool = cost_pool
        self.tier_capabilities = tier_capabilities or ["FLAG"]
        self.point_cost_estimate = 1.0

    def _build_env(self) -> dict:
        env = dict(os.environ)
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("ANTHROPIC_BASE_URL", None)
        if CLAUDE_CREDS.exists():
            try:
                tok = json.loads(CLAUDE_CREDS.read_text()).get("claudeAiOauth", {}).get("accessToken")
                if tok:
                    env["CLAUDE_CODE_OAUTH_TOKEN"] = tok
            except Exception:
                pass
        return env

    def health_probe(self) -> tuple[HealthState, str]:
        if not os.path.exists(CLAUDE_BIN):
            return ("RED", "claude binary not found")
        return ("GREEN", f"{self.model_id} ready")

    def dispatch(self, system: str, user: str, max_tokens: int = 4096) -> AdapterResult:
        full_prompt = f"{system}\n\n{user}" if system else user
        env = self._build_env()
        t0 = time.monotonic()
        try:
            r = subprocess.run(
                [CLAUDE_BIN, "--model", self.model_id, "-p", full_prompt,
                 "--dangerously-skip-permissions"],
                capture_output=True, text=True, timeout=ENGINE_TIMEOUT,
                env=env, cwd=THUNDERBIRD_DIR,
            )
            elapsed = int((time.monotonic() - t0) * 1000)
            if r.returncode == 0:
                text = r.stdout.strip()
                if text:
                    return AdapterResult(
                        text=text, error=None,
                        cost_consumed=1.0, cost_pool=self.cost_pool,
                        latency_ms=elapsed, model_used=self.model_id,
                    )
                return AdapterResult(
                    text=None, error="Claude returned empty stdout",
                    cost_consumed=1.0, cost_pool=self.cost_pool,
                    latency_ms=elapsed, model_used=self.model_id,
                )
            return AdapterResult(
                text=None, error=f"Claude rc={r.returncode}: {r.stderr[:200]}",
                cost_consumed=1.0, cost_pool=self.cost_pool,
                latency_ms=elapsed, model_used=self.model_id,
            )
        except subprocess.TimeoutExpired:
            elapsed = int((time.monotonic() - t0) * 1000)
            return AdapterResult(
                text=None, error=f"Claude timeout {ENGINE_TIMEOUT}s",
                cost_consumed=1.0, cost_pool=self.cost_pool,
                latency_ms=elapsed, model_used=self.model_id,
            )
        except Exception as e:
            elapsed = int((time.monotonic() - t0) * 1000)
            return AdapterResult(
                text=None, error=str(e),
                cost_consumed=1.0, cost_pool=self.cost_pool,
                latency_ms=elapsed, model_used=self.model_id,
            )


sonnet_adapter = ClaudeMaxOAuthAdapter(
    name="claude_max_oauth_sonnet",
    model_id="claude-sonnet-4-6",
    cost_pool="max_weekly_sonnet",
)
opus_adapter = ClaudeMaxOAuthAdapter(
    name="claude_max_oauth_opus",
    model_id="claude-opus-4-6",
    cost_pool="max_weekly_all",
)
