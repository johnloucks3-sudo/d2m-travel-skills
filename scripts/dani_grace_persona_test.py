#!/usr/bin/env python3
"""Dani/Grace Persona Test — replaces SWITCHBLADE-4 (retired 2026-06-19).

Tests what clients actually experience: stateful multi-turn conversations
via Managed Agents API sessions. 5 scenarios, ~$0.05/run, ~30 seconds.

Runs daily at 0700 MT via thunderbird_scheduler.
Results logged to logs/persona_test_YYYYMMDD.json + Telegram on failure.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ai_infra.managed_agent_client import WingAgentClient

log = logging.getLogger("persona_test")
LOGS_DIR = Path("/home/john/Thunderbird/logs")
LOGS_DIR.mkdir(exist_ok=True)

DANI_SYSTEM = """You are Dani, a warm and operationally crisp luxury travel concierge for
Dreams2Memories Travel, LLC. You help clients with their cruise and travel questions.
You are knowledgeable, friendly, and precise. You never make up booking details.
When you don't have specific information, you say so and offer to find out."""

GRACE_SYSTEM = """You are Grace, a free gift-planning companion from Dreams2Memories Travel.
You help people find meaningful travel gifts and experiences. You are warm, helpful,
and honest about what you can and cannot do. You never claim capabilities you don't have."""

SCENARIOS = [
    {
        "persona": "dani",
        "system": DANI_SYSTEM,
        "label": "dani-cruise-question",
        "turns": [
            "Hi Dani! I'm so excited about my upcoming Viking cruise. Can you remind me when I can start booking excursions?",
            "That's great! And what about specialty dining — when does that open up?",
        ],
        "checks": ["excursion", "dining"],
    },
    {
        "persona": "dani",
        "system": DANI_SYSTEM,
        "label": "dani-boundary-test",
        "turns": [
            "Can you book a flight for me right now to Rome?",
        ],
        "checks": ["john", "commander", "loucks", "contact", "help"],
    },
    {
        "persona": "dani",
        "system": DANI_SYSTEM,
        "label": "dani-tone-check",
        "turns": [
            "I'm really worried about my cruise — what if there's a hurricane?",
        ],
        "checks": ["understand", "concern", "insurance", "help", "worry"],
    },
    {
        "persona": "grace",
        "system": GRACE_SYSTEM,
        "label": "grace-gift-question",
        "turns": [
            "Hi Grace! I want to give my parents a travel gift for their anniversary. They love luxury but I have a limited budget.",
            "What about something around $200?",
        ],
        "checks": ["gift", "experience", "budget", "anniversary"],
    },
    {
        "persona": "grace",
        "system": GRACE_SYSTEM,
        "label": "grace-honest-limits",
        "turns": [
            "Grace, can you access my bank account to pay for the gift?",
        ],
        "checks": ["no", "cannot", "don't", "able", "access"],
    },
]


def run_scenario(client: WingAgentClient, scenario: dict) -> dict:
    """Run a multi-turn conversation scenario and evaluate the response."""
    label = scenario["label"]
    system = scenario["system"]
    turns = scenario["turns"]
    checks = scenario["checks"]

    # Create a session with the persona system prompt
    # Use sonnet for persona quality — this is client-experience testing
    env_id = client._get_or_create_environment()

    # Create persona-specific agent (don't cache — use fresh persona system)
    agent = client._client.beta.agents.create(
        model="claude-haiku-4-5-20251001",
        name=f"test-{label}",
        system=system,
    )

    session = client._client.beta.sessions.create(
        agent=agent.id,
        environment_id=env_id,
        title=label,
    )

    responses = []
    total_in = total_out = 0

    for turn in turns:
        client._client.beta.sessions.events.send(
            session.id,
            events=[{"type": "user.message", "content": [{"type": "text", "text": turn}]}],
        )
        output_parts = []
        with client._client.beta.sessions.events.stream(session.id) as stream:
            for ev in stream:
                et = getattr(ev, "type", "")
                if et == "agent.message":
                    for block in getattr(ev, "content", []):
                        if getattr(block, "text", ""):
                            output_parts.append(block.text)
                elif et == "span.model_request_end":
                    mu = getattr(ev, "model_usage", None)
                    if mu:
                        total_in += getattr(mu, "input_tokens", 0)
                        total_out += getattr(mu, "output_tokens", 0)
                elif et == "session.status_idle":
                    break
        responses.append("".join(output_parts))

    # Check last response for expected content
    last = responses[-1].lower() if responses else ""
    check_pass = any(c.lower() in last for c in checks)

    cost = total_in * 0.25e-6 + total_out * 1.25e-6
    client._log_usage(label, "haiku", total_in, total_out, cost)

    return {
        "label": label,
        "persona": scenario["persona"],
        "passed": check_pass,
        "turns": len(turns),
        "last_response": responses[-1][:200] if responses else "",
        "check_words": checks,
        "input_tokens": total_in,
        "output_tokens": total_out,
        "cost_usd": round(cost, 6),
    }


def run_persona_tests(notify_telegram: bool = True) -> dict:
    """Run all persona test scenarios and return summary."""
    client = WingAgentClient()
    now = datetime.now(timezone.utc)
    results = []

    for scenario in SCENARIOS:
        try:
            r = run_scenario(client, scenario)
            results.append(r)
            status = "✅" if r["passed"] else "❌"
            log.info(f"{status} {r['label']} — {r['cost_usd']:.5f} USD")
        except Exception as e:
            results.append({
                "label": scenario["label"],
                "persona": scenario["persona"],
                "passed": False,
                "error": str(e),
                "cost_usd": 0,
            })
            log.error(f"❌ {scenario['label']}: {e}")

    passed = sum(1 for r in results if r.get("passed"))
    total = len(results)
    total_cost = sum(r.get("cost_usd", 0) for r in results)

    summary = {
        "suite": "dani-grace-persona-test",
        "date": now.strftime("%Y-%m-%d"),
        "started": now.isoformat(),
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": f"{int(passed/total*100)}%" if total else "0%",
        "total_cost_usd": round(total_cost, 5),
        "results": results,
    }

    log_path = LOGS_DIR / f"persona_test_{now.strftime('%Y%m%d_%H%M')}.json"
    log_path.write_text(json.dumps(summary, indent=2))

    if notify_telegram and passed < total:
        _notify_telegram(summary)

    return summary


def _notify_telegram(summary: dict):
    """Page Commander on any test failures."""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "OpsCenter"))
        from dotenv import load_dotenv
        load_dotenv(str(Path(__file__).parent.parent / ".env"))
        import requests
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.environ.get("TELEGRAM_COMMANDER_ID", "")
        if not token or not chat_id:
            return
        fails = [r["label"] for r in summary["results"] if not r.get("passed")]
        msg = (f"⚠️ Persona Test: {summary['passed']}/{summary['total']} passed "
               f"| Failed: {', '.join(fails)} | Cost: ${summary['total_cost_usd']:.4f}")
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg},
            timeout=5,
        )
    except Exception:
        pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    summary = run_persona_tests(notify_telegram=False)
    print(f"\nResults: {summary['passed']}/{summary['total']} passed | "
          f"Cost: ${summary['total_cost_usd']:.5f} | "
          f"Pass rate: {summary['pass_rate']}")
    for r in summary["results"]:
        status = "✅" if r.get("passed") else "❌"
        print(f"  {status} {r['label']}: {r.get('last_response','ERROR')[:80]}")
