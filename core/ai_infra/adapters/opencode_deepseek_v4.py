import logging
import os
import re
import subprocess
import time
from pathlib import Path

from core.ai_infra.adapters.base import AdapterResult, HealthState

log = logging.getLogger("adapter.deepseek")

OPENCODE_BIN = Path("/home/john/.opencode/bin/opencode")
THUNDERBIRD_DIR = Path("/home/john/Thunderbird")
MODEL_ID = "opencode/deepseek-v4-flash-free"
TIMEOUT = 120

# Billing watchdog — alert on any non-zero cost
_BILLING_WARNING_LOGGED = False
_MAX_COST_WATCH = 5.0  # Cumulative soft limit before hard-refusing


def _strip_ansi(text: str) -> str:
    text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
    text = re.sub(r'^> build .*', '', text, flags=re.MULTILINE)
    return text.strip()


class DeepSeekV4Adapter:
    name = "deepseek_v4"
    tier_capabilities = ["ARB"]
    cost_pool = "opencode_native"
    point_cost_estimate = 0.0

    def __init__(self):
        self._cumulative_cost = 0.0

    def health_probe(self) -> tuple[HealthState, str]:
        try:
            r = subprocess.run(
                [str(OPENCODE_BIN), "--version"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                return ("GREEN", "opencode binary responds")
            return ("RED", f"opencode rc={r.returncode}")
        except Exception as e:
            return ("RED", str(e))

    def dispatch(self, system: str, user: str, max_tokens: int = 4096) -> AdapterResult:
        global _BILLING_WARNING_LOGGED

        if self._cumulative_cost >= _MAX_COST_WATCH:
            return AdapterResult(
                text=None, error=f"DeepSeek billing watchdog: cumulative cost ${self._cumulative_cost:.2f} exceeds ${_MAX_COST_WATCH:.2f}",
                cost_consumed=0, cost_pool=self.cost_pool,
                latency_ms=0, model_used=MODEL_ID,
            )

        full_prompt = f"{system[:4000]}\n\n{user}" if system else user
        env = dict(os.environ)
        env.pop("ANTHROPIC_BASE_URL", None)
        env["PATH"] = f"/home/john/.opencode/bin:{env.get('PATH', '')}"
        env.setdefault("HOME", "/home/john")

        t0 = time.monotonic()
        try:
            r = subprocess.run(
                [str(OPENCODE_BIN), "run", "-m", MODEL_ID, full_prompt],
                capture_output=True, text=True, timeout=TIMEOUT,
                cwd=str(THUNDERBIRD_DIR), env=env,
            )
            elapsed = int((time.monotonic() - t0) * 1000)
            output = _strip_ansi(f"{r.stdout}\n{r.stderr}")

            if r.returncode != 0:
                return AdapterResult(
                    text=None, error=f"rc={r.returncode}: {r.stderr[:200]}",
                    cost_consumed=0, cost_pool=self.cost_pool,
                    latency_ms=elapsed, model_used=MODEL_ID,
                )
            if not output:
                return AdapterResult(
                    text=None, error="Empty after ANSI strip",
                    cost_consumed=0, cost_pool=self.cost_pool,
                    latency_ms=elapsed, model_used=MODEL_ID,
                )

            # Billing watchdog: check stderr for cost indicators
            stderr_lower = (r.stderr or "").lower()
            cost_indicators = ["cost", "billed", "balance", "credit", "$$", "$"]
            if any(ind in stderr_lower for ind in cost_indicators):
                if not _BILLING_WARNING_LOGGED:
                    log.warning("DeepSeek billing indicator in stderr: %.200s", r.stderr)
                    _BILLING_WARNING_LOGGED = True
                self._cumulative_cost += 0.01  # nominal tracking

            return AdapterResult(
                text=output, error=None,
                cost_consumed=0, cost_pool=self.cost_pool,
                latency_ms=elapsed, model_used=MODEL_ID,
            )
        except subprocess.TimeoutExpired:
            elapsed = int((time.monotonic() - t0) * 1000)
            return AdapterResult(
                text=None, error=f"Timeout {TIMEOUT}s",
                cost_consumed=0, cost_pool=self.cost_pool,
                latency_ms=elapsed, model_used=MODEL_ID,
            )
        except Exception as e:
            elapsed = int((time.monotonic() - t0) * 1000)
            return AdapterResult(
                text=None, error=str(e),
                cost_consumed=0, cost_pool=self.cost_pool,
                latency_ms=elapsed, model_used=MODEL_ID,
            )


adapter = DeepSeekV4Adapter()
