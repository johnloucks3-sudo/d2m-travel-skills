# ADK EVALUATION — COST & SECURITY BRIEFING
# Date: 2026-03-30 | Source: Claude web research
# Status: PRE-PHASE 3 — review before any ADK installation

---

## COST

ADK framework itself: FREE (open-source, Apache 2.0)
Deployment model for D2M: LOCAL on YOGA — zero cloud cost
Billing impact: None beyond existing Gemini API token usage
Vertex AI Agent Engine: NOT required for local deployment — skip entirely

Bottom line: ADK adds zero new costs to D2M stack.

---

## SECURITY ADVISORY — LITELLM SUPPLY CHAIN ATTACK (MARCH 24, 2026)

SEVERITY: CRITICAL
CVE: PYSEC-2026-2 / MAL-2026-2144
Threat actor: TeamPCP

WHAT HAPPENED:
Malicious LiteLLM versions 1.82.7 and 1.82.8 published to PyPI on March 24, 2026
between 10:39-16:00 UTC via stolen PyPI publishing credentials.
LiteLLM is an optional dependency of ADK (extensions extra) with no upper-bound pin.
Affected frameworks: Google ADK, CrewAI, DSPy, MLflow, Microsoft GraphRAG, OpenHands.

MALWARE BEHAVIOR:
- Harvested: LLM API keys, SSH keys, AWS/GCP/Azure creds, K8s tokens, DB passwords,
  shell history, .env files, CI/CD secrets
- Exfiltrated via AES-256/RSA-4096 to models.litellm.cloud (attacker-controlled)
- Installed persistence: systemd user service at ~/.config/sysmon/sysmon.py
- Executed automatically on every Python startup via .pth file — no import required

WHO IS NOT AFFECTED:
- Official LiteLLM Docker images (ghcr.io/berriai/litellm)
- Installations from before March 24 10:39 UTC or after ~16:00 UTC
- Anyone who had LiteLLM pinned to <=1.82.6

---

## IMMEDIATE CHECKS FOR YOGA

Run these before any ADK evaluation begins:

  pip show litellm
  find / -name "litellm_init.pth" 2>/dev/null
  find ~/.config -name "sysmon.py" 2>/dev/null

IF ANY HIT IS FOUND:
  1. Isolate YOGA from network immediately
  2. Rotate ALL credentials: Groq, Deepseek, Gemini, Anthropic, Google service account,
     SSH keys, .env files, any cloud credentials
  3. Rebuild from clean image before continuing

IF NO HIT:
  Safe to proceed with ADK evaluation — pin LiteLLM to <=1.82.6 in any requirements

---

## ADK EVALUATION DECISION

Do NOT install ADK with [extensions] or [eval] extras until LiteLLM supply chain
review is complete (Mandiant engaged by BerriAI as of March 26).
Base ADK install (no extras) does not pull LiteLLM — safe to evaluate now.

Safe install command:
  pip install google-adk   (NOT google-adk[extensions] or google-adk[eval])

---
*Saved 2026-03-30. Review before Phase 3 execution.*
