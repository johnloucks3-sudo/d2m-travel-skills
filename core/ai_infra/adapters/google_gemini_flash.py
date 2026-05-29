import json
import logging
import os
import time
import urllib.request

from core.ai_infra.adapters.base import AdapterResult, HealthState

log = logging.getLogger("adapter.gemini_flash")

# DISABLED 2026-05-29 — Gemini costs being eliminated (GCP cap $5/mo). Route to Claude MAX.
_GEMINI_DISABLED = True

MODEL_ID = "gemini-2.5-flash"


def _get_api_key() -> str:
    return os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY", "")


class GeminiFlashAdapter:
    name = "google_gemini_flash"
    tier_capabilities = ["BULK"]
    cost_pool = "google_ai_pro"
    point_cost_estimate = 0.0

    def health_probe(self) -> tuple[HealthState, str]:
        if _GEMINI_DISABLED:
            return ("RED", "Gemini disabled 2026-05-29 — use Claude MAX")
        key = _get_api_key()
        if not key:
            return ("RED", "No GOOGLE_API_KEY configured")
        return ("GREEN", "API key present")

    def dispatch(self, system: str, user: str, max_tokens: int = 4096) -> AdapterResult:
        if _GEMINI_DISABLED:
            return AdapterResult(
                text=None, error="Gemini disabled 2026-05-29 — route to Claude MAX",
                cost_consumed=0, cost_pool=self.cost_pool,
                latency_ms=0, model_used=MODEL_ID,
            )
        api_key = _get_api_key()
        if not api_key:
            return AdapterResult(
                text=None, error="No GOOGLE_API_KEY",
                cost_consumed=0, cost_pool=self.cost_pool,
                latency_ms=0, model_used=MODEL_ID,
            )

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{MODEL_ID}:generateContent?key={api_key}"
        )

        payload_parts = []
        if system:
            payload_parts.append({"role": "user", "parts": [{"text": system}]})
        payload_parts.append({"role": "user", "parts": [{"text": user}]})

        body = json.dumps({
            "contents": payload_parts,
            "generationConfig": {"maxOutputTokens": max_tokens},
        }).encode()

        t0 = time.monotonic()
        try:
            req = urllib.request.Request(
                url, data=body,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=60)
            elapsed = int((time.monotonic() - t0) * 1000)
            data = json.loads(resp.read())

            candidate = data.get("candidates", [{}])[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            text = (parts[0].get("text", "") if parts else "").strip()

            if not text:
                finish = candidate.get("finishReason", "unknown")
                return AdapterResult(
                    text=None, error=f"Gemini empty: finishReason={finish}",
                    cost_consumed=0, cost_pool=self.cost_pool,
                    latency_ms=elapsed, model_used=MODEL_ID,
                )
            return AdapterResult(
                text=text, error=None,
                cost_consumed=0, cost_pool=self.cost_pool,
                latency_ms=elapsed, model_used=MODEL_ID,
            )
        except urllib.error.HTTPError as e:
            elapsed = int((time.monotonic() - t0) * 1000)
            body = e.read().decode(errors="replace")[:300]
            return AdapterResult(
                text=None, error=f"Gemini HTTP {e.code}: {body}",
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


adapter = GeminiFlashAdapter()
