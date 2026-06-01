# CHROMEBOOK INITIALIZATION PROTOCOL — D2M TRAVEL
# ----------------------------------------------------
# Target: Chromebook (Outbound MCP / Interactive Terminal)

## 1. Connection Architecture
- **Inbound:** Strictly NO inbound SSH.
- **Outbound:** Secure tunnel (Cloudflare) to Yoga Server (192.168.1.198) acting as primary MCP host.
- **MCP Server:** Thunderbird core MCP (all 293 tools via HTTP).

## 2. Capability Matrix
| Capability | Local (Chromebook) | Remote (via MCP) |
|------------|--------------------|------------------|
| LLM Reasoning | No | Yes (Claude Max/Opus) |
| Code Execution | Limited (Shell/Python) | Yes (Yoga-native venv) |
| Persistent Storage| No | Yes (Yoga /storage) |
| MCP Tools | No | Yes (136/293) |

## 3. Coordination & Synchronicity
- **Dual-Terminal Strategy:** Chromebook and Yoga terminal share the same Gmail/Drive/Drive backend.
- **Step-Avoidance:** Never initiate a long-running task on Chromebook if a sync/tasking process (like `tasking-watcher`) is active on Yoga to avoid cross-agent clobbering.
- **Handoff State (Active Missions):**
  - McGlasson background paper (active).
  - SilverSea date issue (anchored to cycle).
  - Dossier: PENDING creation.

## 4. Standing Orders
- **NO CONFIRMATION EMAILS:** Execute directly. If it requires Commander review, draft it but keep in "Drafts" and notify via Telegram.
- **Direct Execution:** Treat instructions as immediate commands. Do not seek clarification unless mission-critical data (e.g., Auth Token) is missing.
- **Brand Consistency:** D2M Travel, LLC voice only.
