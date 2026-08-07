# PROTO — ATO (Agentic Tool Optimization) Evaluation
**Date:** 2026-08-06 · **Evaluator:** HALE-OC (prototype worker) · **Repo:** github.com/WillNigri/Agentic-Tool-Optimization (MIT)
**Target:** Stand up ATO as an evaluated prototype; compare against ROUND TABLE design (`ROUND_TABLE_SPEC.md`).

---

## PURPOSE
Verify ATO v2.19.2 installs, launches, and can serve war-room/review receipts on this Linux box (openSUSE Tumbleweed, X11 `kwin_x11` on `:0`). No git commit, no repo edits, reversible user-space install.

## INSTALL (user-space, no root, no repo edits)
```bash
# A) CLI + desktop binary — extract from official .deb into ~/.local/bin
mkdir -p /tmp/opencode/ato-rel
base="https://github.com/WillNigri/Agentic-Tool-Optimization/releases/download/v2.19.2"
curl -fsSL -o /tmp/opencode/ato-rel/ato.AppImage "$base/ATO_2.19.2_amd64.AppImage"
curl -fsSL -o /tmp/opencode/ato-rel/ato.deb       "$base/ATO_2.19.2_amd64.deb"
cd /tmp/opencode/ato-rel && ar x ato.deb && tar xf data.tar.gz
cp usr/bin/ato usr/bin/ato-desktop "$HOME/.local/bin/" && chmod +x "$HOME/.local/bin/ato" "$HOME/.local/bin/ato-desktop"

# B) AppImage (alternative): runs directly — chmod +x ato.AppImage && ./ato.AppImage
# macOS alt: `brew install willnigri/ato/ato` (README). Linux: .deb/AppImage (used here).
# NOTE: agentictool.ai/install.sh returned EMPTY body on this box (2026-08-06) — unreliable; .deb path is canonical.
```
**Artifacts:** `~/.local/bin/ato` (23 MB CLI ELF) · `~/.local/bin/ato-desktop` (40 MB Tauri GUI) · `~/.ato/local.db` (SQLite, auto-created). Reversible = delete 2 files + DB.

## VERIFICATION EVIDENCE (ground truth, not self-report)
| Check | Result |
|---|---|
| `ato --version` | `ato 2.19.2` (exact release from GitHub `v2.19.2`, 2026-07-04) |
| `ato --help` | Full CLI: war-rooms · sessions · review · dispatch · runs · replays · bench · route · optimize · daemon · mesh |
| GUI launch (`ato-desktop` on DISPLAY=:0) | Process alive (PID captured), no crash; **no local HTTP port** — local-first (SQLite `~/.ato/local.db`) |
| `ss -ltnp` after launch | No new ATO listener. Pre-existing only: litellm:4000, node:8080, temporal:41xxx (NOT ATO) |
| Persistence | `ato dispatches recent` → 20 prior `claude` runs (Aug 2–5) already in `~/.ato/local.db` — receipts persist across sessions; method proven end-to-end |
| Model keys | Env-var path (`ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`) + encrypted keychain table (`llm_api_keys`). ANTHROPIC/DEEPSEEK/GEMINI already SET on this box |
| War-rooms | `ato war-rooms` → close/reopen/get/share/sweep. War room = N execution_logs sharing a `war_room_id`; close runs coordinator over all seats → title/summary/tags |
| Sessions | `ato sessions` → new/list/get/delete/close/reopen/share. Sticky multi-turn (claude-only for now) |
| Review | `ato review --reviewer claude --reviewer codex --reviewer gemini --against main [--consensus]` → multi-LLM review, `.md` transcript, `--out` file |

### HONEST GAPS (build ≤ README)
- ⚠️ **`ato demo-war-room` does NOT exist** in v2.19.2 — README example is stale; only `demo-compare` ships.
- ⚠️ **Ollama is NOT a dispatch runtime** in v2.19.2. Dispatcher vocabulary is fixed: `{claude, codex, gemini, openclaw, hermes}`. `ato dispatch ollama` → `Error: Unknown runtime 'ollama'`. The zero-config demo silently fell back to the **stub** seat (fake reply, 0s, $0.0000). Local qwen2.5:7b (Ollama, running) is unreachable as a seat. API-wrapper seats (grok/deepseek/qwen/openrouter) exist on the **review** path only (`--reviewer`), not `dispatch`.
- Desktop is a Tauri GUI, not a browser app; optional cloud web exists (teams/auth) — irrelevant to local box.
- No Commander-paced sequencing; no card/presenter metaphor; receipts only after execution.

## FIT VERDICT — ATO vs ROUND TABLE (5 lines)
1. **RT: Commander-paced, one-card-at-a-time (SPACE to advance), ordered CC→AG→OC→Grok — ATO: async fan-out, no pacing, no single-step presentation → NO.**
2. **RT: pre-write file-based cards, zero-token playback — ATO: generates live from dispatches, no pre-write card model → NO.**
3. **RT: color-coded seats 🔵🟢🟡🔴 — ATO: per-runtime badges + per-seat analytics, but no RT seat-color/presenter mapping → PARTIAL.**
4. **RT: receipt/transcript — ATO: STRONG match. Per-dispatch receipts (prompt, tool calls, bytes, cost, files touched), coordinator close-summaries, `.md` transcript, SQLite archive, file attribution → YES.**
5. **RT: file-based, crash-safe, zero-dep — ATO: SQLite + keychain + transcript files; heavier (Tauri + keychain + optional cloud), but still local-first → PARTIAL.**

**Summary:** ATO is a first-class **receipt/transcript/audit engine** for multi-seat runs, not a Round Table sequencer. It covers RT's weakest layers (evidence + cost + attribution) but cannot replace the Commander-paced pre-written card viewer; and it can't reach this box's DeepSeek/Ollama seats as dispatch runtimes in v2.19.2.

## RECOMMEND
**HYBRID** — adopt ATO as the receipts/transcript/attribution layer under RT's Commander-paced viewer (RT stays the "meeting room"; ATO becomes the flight recorder for CC/GEMINI/API seats); refuse ATO as the RT UI or as the sequencer. Re-evaluate when a DeepSeek/Ollama dispatch runtime ships.

---
*End of evaluation. Install fully user-space + reversible; nothing committed to the Thunderbird repo.*
