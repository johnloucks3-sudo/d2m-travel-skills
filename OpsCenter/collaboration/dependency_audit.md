# THUNDERBIRD DEPENDENCY AUDIT
# Date: 2026-03-30 | Author: Claude Sonnet 4.6
# Status: COMPLETE — ready for pinning action

---

## FILES AUDITED

1. /home/john/Thunderbird/requirements.txt (117 lines) — MAIN
2. /home/john/Thunderbird/reverie/api/requirements.txt (31 lines) — REVERIE API
3. /home/john/Thunderbird/.claude/worktrees/funny-kowalevski/requirements.txt
   — IDENTICAL to main requirements.txt (worktree copy, keep in sync)

---

## LITELLM STATUS

LiteLLM: NOT PRESENT in any requirements file.
Not installed on YOGA (confirmed by live check).
No transitive dependency pulls LiteLLM in current stack.
STATUS: CLEAN — no action required.

---

## PINNING STATUS

### Main requirements.txt
STATUS: FULLY PINNED — every package uses == version pinning.
No open-ended >= pins found.
No unpinned packages found.
This is already production-safe from a pinning perspective.

### reverie/api/requirements.txt
STATUS: FULLY PINNED — every package uses == version pinning.
One exception: uvicorn[standard]==0.34.0 — extras bracket is fine, version is pinned.
STATUS: CLEAN.

---

## VERSION CONFLICT DETECTED

google-auth version mismatch between files:
  Main requirements.txt:         google-auth==2.49.0
  reverie/api/requirements.txt:  google-auth==2.38.0

google-api-python-client mismatch:
  Main requirements.txt:         google-api-python-client==2.192.0
  reverie/api/requirements.txt:  google-api-python-client==2.165.0

google-auth-oauthlib mismatch:
  Main requirements.txt:         google-auth-oauthlib==1.3.0
  reverie/api/requirements.txt:  google-auth-oauthlib==1.2.1

pydantic-settings mismatch:
  Main requirements.txt:         pydantic-settings==2.13.1
  reverie/api/requirements.txt:  pydantic-settings==2.7.1

python-multipart mismatch:
  Main requirements.txt:         python-multipart==0.0.22
  reverie/api/requirements.txt:  python-multipart==0.0.20

httpx-sse mismatch:
  Main requirements.txt:         httpx-sse==0.4.3
  reverie/api/requirements.txt:  httpx-sse==0.4.0

ACTION REQUIRED: Reverie API runs in its own environment (Hetzner CX21) so
version isolation is intentional — but google-auth and google-api-python-client
divergence should be reviewed and aligned when Reverie is next updated.

---

## HIGH-VALUE PACKAGES — SECURITY WATCH LIST

These packages have elevated supply chain risk due to high download volume,
AI ecosystem centrality, or recent incident history. Monitor advisories actively.

| Package | Version Pinned | Risk Reason |
|---------|---------------|-------------|
| anthropic | 0.84.0 ✅ | Core AI SDK — high-value target |
| openai | 2.26.0 ✅ | Core AI SDK — high-value target |
| google-genai | 1.66.0 ✅ | Gemini SDK — central to stack |
| mcp | 1.26.0 ✅ | MCP protocol — new, evolving |
| playwright | 1.58.0 ✅ | Browser automation — broad system access |
| cryptography | 46.0.5 ✅ | Crypto primitives — critical |
| pydantic | 2.12.5 ✅ | Data validation — used everywhere |
| requests | 2.32.5 ✅ | HTTP — used everywhere |
| Jinja2 | 3.1.6 ✅ | Template engine — injection risk if unpinned |
| weasyprint | 68.1 ✅ | PDF generation — complex dependency tree |

All are currently pinned. No action required — maintain pinning on updates.

---

## NEW DEPENDENCY POLICY (forward-looking)

Per Commander decision (2026-03-30), all new dependencies must follow:

1. Always pin to exact version: package==X.Y.Z
2. No open-ended pins: never package>=X.Y.Z without upper bound
3. Before adding any new package:
   - Check OSV (osv.dev) for known vulnerabilities
   - Check if package pulls LiteLLM or other high-risk transitive deps
   - Document why the package is needed in a comment above the entry
4. After any pip install: immediately add pinned version to requirements.txt
5. Worktree requirements.txt (/home/john/Thunderbird/.claude/worktrees/funny-kowalevski/)
   must be kept in sync with main requirements.txt manually or via script

---

## ADK INSTALLATION GUIDANCE (when Phase 3 begins)

Safe: pip install google-adk
  → Does NOT pull LiteLLM
  → Add to requirements.txt as: google-adk==X.Y.Z (pin after install)

Unsafe until LiteLLM supply chain review complete:
  pip install google-adk[extensions]
  pip install google-adk[eval]
  → Both pull LiteLLM as optional dependency
  → Hold until BerriAI/Mandiant review confirms clean release

---

## SUMMARY

| File | Pinned | LiteLLM | Action |
|------|--------|---------|--------|
| requirements.txt | ✅ Fully | ✅ Not present | None |
| reverie/api/requirements.txt | ✅ Fully | ✅ Not present | Align Google versions on next update |
| worktree requirements.txt | ✅ Fully | ✅ Not present | Keep in sync with main |

Overall status: CLEAN. No immediate action required beyond version alignment noted above.

---
*Audit complete 2026-03-30. Next audit: before any Phase 3 framework installation.*

## ADK INSTALLATION LOG (2026-03-30)

Installed: google-adk==1.28.0 (base only — no [extensions], no [eval])
Method: pip install google-adk into /home/john/Thunderbird/.venv
LiteLLM: NOT pulled as dependency — confirmed clean

ACTION REQUIRED — add to requirements.txt:
  google-adk==1.28.0

WEBSOCKETS DOWNGRADE — REVIEW NEEDED:
ADK pulled websockets==15.0.1, replacing websockets==16.0 (was in requirements.txt)
This is a minor version downgrade. Check if any Thunderbird module requires 16.0.
If yes, there may be a version conflict to resolve before ADK is used in production.

New packages installed as ADK dependencies (add to requirements.txt if keeping ADK):
  Mako, aiosqlite, alembic, authlib, cloudpickle, google-cloud-aiplatform,
  google-cloud-bigquery, google-cloud-storage, grpcio, opentelemetry-*, sqlalchemy,
  pyarrow, watchdog, and others — see install log above for full list.

NOTE: ADK brings in a significant Google Cloud dependency tree. Most of these
(BigQuery, Spanner, PubSub, etc.) are not needed for local D2M use.
For Phase 3 evaluation, this is acceptable. For production, consider whether
a lighter integration approach is warranted.
