"""Wing Managed Agents Client — core/ai_infra/managed_agent_client.py

Anthropic Managed Agents API wrapper for Thunderbird OS automations.
Replaces headless subprocess spawns for scheduled tasks (crons, timers,
intel sweeps, lifecycle checks, fare watches).

API beta header: managed-agents-2026-04-01
SDK: anthropic==0.111.0

Architecture:
  - Cloud environment  → non-PII tasks (intel, tech search, incubator)
  - Self-hosted env    → PII tasks (lifecycle, dossiers) — future build on YOGA
  - All tasks log tokens to OpsCenter/usage_ledger.json for Harlan
  - Agent + environment IDs cached in OpsCenter/.managed_agent_*.json
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import anthropic

log = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path(__file__).parent.parent.parent
_CACHE_DIR = THUNDERBIRD_DIR / "OpsCenter"
USAGE_LEDGER = _CACHE_DIR / "usage_ledger.json"
BETA = "managed-agents-2026-04-01"

# Haiku for mechanical tasks, Sonnet for synthesis — Opus only on explicit request
MODEL_ROUTING = {
    "haiku":  "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus":   "claude-opus-4-8",
}

COST_PER_TOKEN = {
    "haiku":  {"in": 0.25e-6,  "out": 1.25e-6},
    "sonnet": {"in": 3.0e-6,   "out": 15.0e-6},
    "opus":   {"in": 15.0e-6,  "out": 75.0e-6},
}

WING_SYSTEM = (
    "You are a Thunderbird Wing automation agent for Dreams2Memories Travel, LLC. "
    "Your output is consumed by other Wing scripts — be concise and structured. "
    "No preamble. No sign-off. Return the answer directly.\n"
    "Rules:\n"
    "- Financial figures must cite source (portal/TESS/dossier). Never infer.\n"
    "- If data is absent: say 'not found in [source]' — never fabricate.\n"
    "- If the task involves client PII (names, bookings, payments), tag [PII] on the first line."
)


def _load_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        env_path = THUNDERBIRD_DIR / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY=") and not line.startswith("#"):
                    key = line.split("=", 1)[1].strip()
                    break
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. "
            "Add API credits at console.anthropic.com/settings/billing, "
            "then ensure ANTHROPIC_API_KEY is set in .env."
        )
    return key


class WingAgentClient:
    """Thunderbird Wing interface to Anthropic Managed Agents API."""

    def __init__(self):
        self._client = anthropic.Anthropic(
            api_key=_load_api_key(),
            default_headers={"anthropic-beta": BETA},
        )
        self._env_id: Optional[str] = None
        self._agent_ids: dict[str, str] = {}

    # ── Environment ────────────────────────────────────────────────────────────

    def _get_or_create_environment(self) -> str:
        cache = _CACHE_DIR / ".managed_env.json"
        if self._env_id:
            return self._env_id
        if cache.exists():
            data = json.loads(cache.read_text())
            self._env_id = data["env_id"]
            return self._env_id

        env = self._client.beta.environments.create(
            name="wing-cloud",
            description="Thunderbird Wing automation environment — non-PII tasks",
        )
        cache.write_text(json.dumps({
            "env_id": env.id,
            "created": datetime.now(timezone.utc).isoformat(),
        }))
        self._env_id = env.id
        log.info(f"Created managed environment: {env.id}")
        return env.id

    # ── Agent ──────────────────────────────────────────────────────────────────

    def _get_or_create_agent(self, tier: str = "haiku") -> str:
        cache = _CACHE_DIR / f".managed_agent_{tier}.json"
        if tier in self._agent_ids:
            return self._agent_ids[tier]
        if cache.exists():
            data = json.loads(cache.read_text())
            self._agent_ids[tier] = data["agent_id"]
            return data["agent_id"]

        agent = self._client.beta.agents.create(
            model=MODEL_ROUTING[tier],
            name=f"wing-auto-{tier}",
            system=WING_SYSTEM,
        )
        cache.write_text(json.dumps({
            "agent_id": agent.id,
            "tier": tier,
            "created": datetime.now(timezone.utc).isoformat(),
        }))
        self._agent_ids[tier] = agent.id
        log.info(f"Created managed agent: {agent.id} (tier={tier})")
        return agent.id

    # ── Task execution ─────────────────────────────────────────────────────────

    def run_task(
        self,
        prompt: str,
        tier: str = "haiku",
        label: str = "automation",
        session_id: Optional[str] = None,
    ) -> dict:
        """Run a Wing automation task via Managed Agents API.

        Returns:
            {
              "output": str,
              "session_id": str,
              "input_tokens": int,
              "output_tokens": int,
              "cost_usd": float,
            }
        """
        env_id = self._get_or_create_environment()
        agent_id = self._get_or_create_agent(tier)

        if not session_id:
            session = self._client.beta.sessions.create(
                agent=agent_id,
                environment_id=env_id,
                title=label,
            )
            session_id = session.id

        # Send user turn
        self._client.beta.sessions.events.send(
            session_id,
            events=[{
                "type": "user.message",
                "content": [{"type": "text", "text": prompt}],
            }],
        )

        # Stream response — collect agent.message events, stop on session.status_idle
        output_parts: list[str] = []
        input_tok = output_tok = 0

        with self._client.beta.sessions.events.stream(session_id) as stream:
            for event in stream:
                etype = getattr(event, "type", "")
                if etype == "agent.message":
                    for block in getattr(event, "content", []):
                        text = getattr(block, "text", "")
                        if text:
                            output_parts.append(text)
                elif etype == "span.model_request_end":
                    mu = getattr(event, "model_usage", None)
                    if mu:
                        input_tok += getattr(mu, "input_tokens", 0)
                        output_tok += getattr(mu, "output_tokens", 0)
                elif etype == "session.status_idle":
                    break

        output = "".join(output_parts)
        cost = (
            input_tok * COST_PER_TOKEN.get(tier, COST_PER_TOKEN["sonnet"])["in"]
            + output_tok * COST_PER_TOKEN.get(tier, COST_PER_TOKEN["sonnet"])["out"]
        )

        self._log_usage(label, tier, input_tok, output_tok, cost)

        return {
            "output": output,
            "session_id": session_id,
            "input_tokens": input_tok,
            "output_tokens": output_tok,
            "cost_usd": round(cost, 6),
        }

    # ── Usage tracking ─────────────────────────────────────────────────────────

    def _log_usage(
        self, label: str, tier: str, input_tok: int, output_tok: int, cost: float
    ):
        try:
            if USAGE_LEDGER.exists():
                ledger = json.loads(USAGE_LEDGER.read_text())
            else:
                ledger = {"entries": [], "total_usd": 0.0}
            ledger.setdefault("entries", []).append({
                "ts": datetime.now(timezone.utc).isoformat(),
                "source": "managed_agents",
                "label": label,
                "tier": tier,
                "input_tokens": input_tok,
                "output_tokens": output_tok,
                "cost_usd": round(cost, 6),
            })
            ledger["total_usd"] = round(
                sum(e.get("cost_usd", 0) for e in ledger["entries"]), 6
            )
            USAGE_LEDGER.write_text(json.dumps(ledger, indent=2))
        except Exception as e:
            log.warning(f"Usage log failed (non-fatal): {e}")


# ── Convenience wrapper ────────────────────────────────────────────────────────

def run_wing_task(
    prompt: str,
    tier: str = "haiku",
    label: str = "automation",
) -> str:
    """Run a single Wing task and return text output. Convenience wrapper."""
    return WingAgentClient().run_task(prompt, tier=tier, label=label)["output"]
