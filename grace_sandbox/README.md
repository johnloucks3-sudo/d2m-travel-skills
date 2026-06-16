# Grace Sandbox

Grace — D2M's gift-world persona — runs jailed inside this directory.

- **Why:** the data fence. Grace works here, never in the repo. She physically cannot reach `dossiers/`, `config/`, `.env`, or any client/business data. See `docs/GRACE_TOOL_ALLOWLIST.md`.
- **`.gemini/settings.json`** — Grace's fenced config: native Gemini tools (shell/file/web-search) OFF. Capability comes from D2M's own allowlisted tools, never the native CLI toolset.
- **`work/`** — Grace's scratch space for anything she generates.
- **Persona:** `Personas/grace_gift_persona.md` · **Voice/route:** `scripts/grace.sh` (`grace` / `/grace`).

"A gift given with no strings." The fence is around the *data*, never the person.
