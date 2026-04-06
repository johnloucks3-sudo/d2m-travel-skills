# RULE: 30-Second Auto-Approval + Claude Authority
**Set: 2026-04-04 08:54 MDT | Commander Order — Standing Until Revoked**

---

## 30-SECOND AUTO-APPROVAL CLOCK
When Hale (COS) asks Commander for approval on any action:
1. **Start 30-second clock**
2. **If NO input after 30 seconds → ASSUME APPROVED → execute immediately**
3. This applies to ALL operational decisions, file changes, deployments, syncs, etc.

### EXCEPTIONS (30-sec rule DOES NOT apply):

| Exception | Rule |
|-----------|------|
| **Claude Opus tasks** | Must get explicit approval. Sonnet 4.6 and Haiku 4.6 are ALWAYS authorized — no approval needed. |
| **Client-facing emails** | Must get explicit approval. NEVER auto-approve. WF17 gate stands. |

## CLAUSE AUTHORIZATION LEVELS

| Model | Authorization | Notes |
|-------|---------------|-------|
| **Claude Sonnet 4.6** | ALWAYS authorized | Task freely, no approval |
| **Claude Haiku 4.6** | ALWAYS authorized | Task freely, no approval |
| **Claude Opus** | Explicit approval required | High-value, complex tasks. 30-sec rule excluded. |

## CLIENT EMAIL PROTOCOL
- All client-facing emails require Commander's explicit "approved" / "send" / "go"
- Internal emails (staff, ops, system) follow normal auto-approval rules
- WF17 approval gate is the technical enforcement layer

---
**This rule is standing. Does not expire. Revocable only by Commander order.**
