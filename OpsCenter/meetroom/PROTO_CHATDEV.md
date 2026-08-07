# PROTO — ChatDev 2.0 (DevAll) | All-Hands Multi-Agent Orchestration Prototype
**Bring-up date:** 2026-08-06/07 · **System:** openSUSE Tumbleweed (SELinux enforcing) · **Engine:** Docker containers `/tmp/opencode/chatdev`
**Scope:** RESEARCH + BRING-UP only. No commits, no Thunderbird repo edits, no irreversible system installs.

## BLUF
ChatDev DevAll `:6400` backend + `:5173` Vue frontend **stand up and respond** from pre-built
Docker images (no host bind mount). Verified: backend healthy, workflow templates API live, frontend
page served. **PENDING for full function:** LLM API key required at workflow *execution* time.

## 1. Bring-up method + commands
Repo (fresh upstream clone already present): `/tmp/opencode/chatdev` (OpenBMB/ChatDev @ `4fb2db0`).

```
# A) Preferred — Docker images (backend image built OK; frontend image built OK)
cd /tmp/opencode/chatdev
docker compose up --build          # README path — BLOCKED at runtime by SELinux bind-mount (see §4)
```

**Working fallback (used for verification):** run the already-built images directly — *no bind mount*,
so SELinux cannot block container reads (source is baked into the image at build time).
```
docker run -d --name chatdev-backend -p 6400:6400 -e API_KEY= chatdev-backend
docker run -d --name chatdev-frontend -p 5173:5173 -e VITE_API_BASE_URL=http://localhost:6400 chatdev-frontend
```
NOTE: edits were only to the scratch `/tmp/opencode/chatdev` clone; the Thunderbird repo was untouched.

## 2. Verification evidence
| Check | Result | Evidence |
|---|---|---|
| (a) Clone | ✅ | `/tmp/opencode/chatdev`, upstream HEAD `4fb2db0` |
| (b) Backend :6400 | ✅ | `{"status":"healthy"}` on `/health`; `/health/live`→alive; Uvicorn startup complete |
| (b) Backend API live | ✅ | OpenAPI served: `/api/workflows`, `/api/workflow/run`, `/api/config/schema`, `/health*` |
| (b) Workflow templates | ✅ | `GET /api/workflows` → list of YAML graphs (ChatDev_v1, GameDev, MACNet, …), **no key needed** |
| (c) Frontend :5173 | ✅ | `HTTP 200`, `<title>DevAll</title>`, Vite v7.3.0 ready, serves `/src/main.js` |

## 3. Does creating a workflow need an LLM key?
- **Browse / compose the graphical workflow:** NO key required (design-time). Templates and graph
  vocabulary load purely from local YAML (`/api/workflows`).
- **Execute / run a workflow:** YES — key required. Each Agent node schema
  (`entity/configs/node/agent.py`) has a `provider` (openai/gemini/…) + `api_key`
  (default `${API_KEY}`) field; `/api/workflow/run` resolves these to make live LLM calls.
- Placeholder config `.env` ships with a dummy OpenAI key; until a real key / local model
  (LM Studio/Ollama base URL) is wired, **graphs can be built but not run**.

## 4. Blocker (captured, not sunk further)
`docker compose up --build` tears down to **SELinux EACCES** on every bind mount
(`EACCES: permission denied` opening `/app/server_main.py` / `/app/package.json`) because the host
is SELinux-enforcing and compose mounts `/tmp` (tmpfs) without `:z` relabel. Fix = add `:z` to the
compose volume mounts (edit-compose). Not applied — images already run clean without bind mounts, so
verification proceeded via the direct-image path instead. (Additional wrinkle: backgrounding
`docker compose` from the CLI hung the persistent shell — routed around by launching with detached fds.)

## FIT VERDICT vs ROUND TABLE (Commander-paced, color-coded seats, pre-write cards, receipt/transcript, file-based, web-accessible)
- ✅ **Web-accessible** — yes: browser UI `:5173`, file data on disk.
- ⚠️ **Color-coded seats** — Vue-flow node graph; seat identity/color code not a designed concept (would need a custom schema).
- ⚠️ **Pre-write cards / receipts / transcript** — not built-in; each node holds a text card (can be written before run) but no ordered receipt/transcript ledger out of the box.
- ⚠️ **File-based** — native data is YAML + WareHouse output artifacts; a durable per-session archive/receipt is not a designed feature.
- ⚠️ **Commander-paced** — orchestration is agent-graph-driven; a Commander-paced gate/stop-between-nodes control is not present.

*Net: a capable machine for wiring a custom multi-agent workflow to the web, short on the Round Chat's
receipt/transcript + paced-seat semantics unless hand-built.*

## RECOMMEND: HYBRID
Keep DevAll as the orchestration engine prototype if Round Chat needs a live web + workflows backplane;
do NOT adopt as a drop-in replacement — its seat-color/card/receipt/pacing semantics are absent and must
be layered on. Otherwise the lighter existing Round-table flow stays the simpler bet.