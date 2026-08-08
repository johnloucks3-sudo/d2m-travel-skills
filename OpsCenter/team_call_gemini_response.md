# POINT PAPER: AI RATE LIMIT & QUOTA METERING ARCHITECTURE (GEMINI / TALON PERSPECTIVE)

**BLUF:** Programmatic rate limit and quota metering requires a tiered hybrid model: passive response-header parsing for real-time rate limits, authenticated OAuth telemetry endpoints for rolling usage buckets, local JSONL transcript sliding-window parsing for burst velocity proxies, and strict local pre-flight guards with cloud key endpoints for monthly spend ceilings.

## 1. PURPOSE
- Provide technical architecture for programmatically tracking, measuring, and predicting AI engine quota limits across 5-hour, daily, weekly, and monthly windows.

## 2. BACKGROUND
- Gemini/Antigravity and cross-engine integrations rely on heterogeneous quota structures:
  - Google Gemini API (AI Studio / Vertex AI): Rate limits governed by RPM/TPM/RPD.
  - Antigravity CLI: Local session trajectory tracking without direct Google quota status endpoints.
  - OpenRouter: Per-key usage metering and hard spend caps.
  - Poe: Token-based prepaid points reservoir with prompt caching dynamics.
  - Claude Code (CC): OAuth-backed 5-hour burst and 7-day rolling window utilization.

## 3. DISCUSSION: TIER-BY-TIER TECHNICAL SPECIFICS

### A. 5-Hour Session Limits / Burst Windows
- **Method:** Response Header Interception + Local Sliding-Window Transcript Proxy.
- **Google Gemini API (AI Studio / Vertex AI):**
  - Response Headers (HTTP 200 & 429):
    - `x-ratelimit-limit-requests`: Maximum request capacity per window.
    - `x-ratelimit-remaining-requests`: Remaining requests in current window.
    - `x-ratelimit-reset-requests`: UTC time string / duration until request reset.
    - `x-ratelimit-limit-tokens` & `x-ratelimit-remaining-tokens`: Token-level throughput controls.
    - `Retry-After`: Seconds to back off on HTTP 429 (`RESOURCE_EXHAUSTED`).
- **Antigravity CLI (Local Proxy):**
  - Authoritative Path: `~/.gemini/antigravity-cli/brain/*/.system_generated/logs/transcript.jsonl`.
  - Implementation: `core/relay/engine_limits.py` (`check_headroom('AG')`) reads `mtime` and counts `PLANNER_RESPONSE` / `USER_INPUT` events in a 1-hour sliding window against `DEFAULT_CAPS` (20 req/hr default cap).
- **Claude Code OAuth Peer Contrast (Verified via `core/relay/cc_capacity.py`):**
  - Endpoint: `GET https://api.anthropic.com/api/oauth/usage` with header `anthropic-beta: oauth-2025-04-20`.
  - JSON Fields: `five_hour.utilization` (float percentage) and `five_hour.resets_at` (ISO-8601 timestamp).
  - Cache: `~/.claude/hud/.usage-cache.json` (TTL: 60s).

### B. Daily Quotas & Exact Reset Timestamps
- **Method:** Canonical Reset Time Matching + gRPC Error Interception.
- **Google AI Studio / Gemini API:**
  - Daily Quotas (RPD - Requests Per Day) reset deterministically at **00:00 PST / 01:00 PDT (18:00 MT)**.
  - Error Payload (HTTP 429): Returns `google.rpc.QuotaFailure` with violation code `RESOURCE_EXHAUSTED` and error details specifying domain `googleapis.com` and service `generativeai.googleapis.com`.
- **GCP Vertex AI Quota API:**
  - Programmatic Query: `gcloud services quota list --service=generativeai.googleapis.com` or Cloud Monitoring API metric `serviceruntime.googleapis.com/quota/allocation/usage`.
- **Local Prediction:**
  - `core/relay/engine_limits.py` calculates delta to 18:00 MT target (`reset_dt = now_mt.replace(hour=18, minute=0, second=0)`).

### C. Weekly Volume Limits / Message Buckets
- **Method:** Rolling Window OAuth Telemetry & Key Account Polling.
- **Google Gemini API:**
  - Native Gemini API does NOT enforce weekly rolling limits (relies on RPD + billing limits).
- **Claude Code Peer Telemetry (Verified via `core/relay/cc_capacity.py`):**
  - Endpoint: `GET https://api.anthropic.com/api/oauth/usage`.
  - JSON Fields: `seven_day.utilization` (float percentage) and `seven_day.resets_at` (ISO-8601 timestamp).
- **OpenRouter (Key Polling):**
  - Endpoint: `GET https://openrouter.ai/api/v1/auth/key` with `Authorization: Bearer $OPENROUTER_API_KEY`.
  - JSON Field: `data.rate_limit` (rolling request velocity rules).

### D. Monthly Hard Spend Caps / Prepaid Balances
- **Method:** Authenticated Key Endpoint Auditing + Local Pre-Flight Spend Guards.
- **OpenRouter Hard Cap Enforcement:**
  - Endpoint: `GET https://openrouter.ai/api/v1/auth/key`.
  - JSON Fields: `data.limit` (USD max limit), `data.usage` (USD current spend), `data.is_free_tier`.
  - Wing Local Guard: `OPENROUTER_MONTHLY_HARD_CAP = 10.00` in `core/relay/engine_limits.py`. Blocks paid model routes when ledger spend >= $10.00 while preserving free models (`x-ai/grok-2:free`, `deepseek-r1:free`).
- **Poe Prepaid Points Reservoir Math (Verified via `core/relay/engine_limits.py`):**
  - Formula: `Points = turns * [(input_tokens / 1000) * in_rate + (output_tokens / 1000) * out_rate] + (searches * 467)`.
  - Prompt Caching: 90% discount on cached tokens (`POE_CACHE_DISCOUNT = 0.10`).
  - Gating: Fail-closed on unlisted models; approval required for runs > 15,000 pts (`POE_RUN_APPROVAL_THRESHOLD`).
- **GCP Cloud Billing Budgets API:**
  - Endpoint: `billingbudgets.googleapis.com/v1/projects/{project_id}/billingBudgets`.
  - Pub/Sub notification triggers automatic disable script on budget breach.

## 4. OPINION
- Relying on static client-side time-based resets (e.g., assuming 18:00 MT) without API header parsing creates blind spots during high-burst activity.
- The dual-layer model used in Thunderbird Wing (`core/relay/engine_limits.py` + `cc_capacity.py`)—combining live OAuth endpoints where available with local JSONL transcript trajectory counts—provides the highest reliability across heterogeneous AI backends.

## 5. RECOMMENDATIONS
- **Standardize Header Capture:** Implement a unified HTTP response wrapper across all Gemini/Google API clients to log `x-ratelimit-*` headers to `engine_usage_ledger.jsonl`.
- **OpenRouter Pre-Flight Sync:** Query `https://openrouter.ai/api/v1/auth/key` prior to dispatching paid model tasks to verify live balance against `OPENROUTER_MONTHLY_HARD_CAP`.
- **Integrate Poe Token Tracker:** Maintain strict token math verification in `check_poe_model()` to prevent point pool exhaustion prior to monthly replenishment.
