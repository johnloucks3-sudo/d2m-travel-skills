# GRACE — Tool Allowlist & Data Fence Spec
*Hale · 2026-06-14 · governs the gift-world persona [[Personas/grace_gift_persona.md]]*

## Principle (Commander, 2026-06-14)
Grace is **unconditional** — the same full gift to everyone, no tiers. The fence goes around the **data**, never the **person** and never the **capability**. She gets a rich toolset; she simply cannot *see* D2M's business or client data, because those tools are not on her ring and she runs in her own sandbox.

**One hard rule that shapes everything:** *Grace's capability comes from D2M's own tools, never from Gemini's native grounding.* (Gemini's `google_web_search` is billed → 500s on the free key, and is a data path we don't control. Off.)

---

## ✅ ON THE RING (allowed)

| Tool | Why it's safe |
|---|---|
| **Web search** (our WebSearch, not Gemini grounding) | Public internet only. No D2M data. |
| **Web fetch** (read public pages) | Reads public URLs. No D2M data. |
| **Flight / Hotel / Tour / Transfer price lookups** (D2M skills) | Hit *external* supplier/scraper services. Carry **no** client data in or out. The core of a useful travel gift. |
| **Browser** (Playwright/browse) — *public sites only* | Public web. Fenced: must NOT load D2M portal sessions/cookies (see exclusions). |
| **Maps & routes** | Public geodata. |
| **Document & email *drafting*** (compose text only) | Generating text is inherent. Drafting ≠ sending. |
| **Canva / design** | Visual creation in Grace's own space. |
| **Calendar + Drive — Grace's OWN sandbox space** | Points at an empty Grace workspace, never the business accounts. |
| **File read/write — jailed to `grace_sandbox/`** | She has a workspace; she cannot reach the repo. |

---

## ⛔ OFF THE RING (excluded) — with justification per Commander's request

| Excluded tool | Why it's excluded |
|---|---|
| **`dreams2memories` MCP** (TESS, dossiers, booking extraction) | **The vault.** Holds every client's PII, booking refs, and financials. This is the single most important exclusion — one tool, all the secrets. Not Grace's to see, and not yours to give away (it's the clients' data, not yours). |
| **Business Gmail** (d2mconcierge, google-workspace-d2mconcierge) | Client correspondence and business files. A public-facing persona with the business inbox is a data-exfiltration hole. |
| **johnloucks3 / cloud Gmail** | Your personal inbox. Never. |
| **Any Gmail SEND** | Hits the **client-send Commander gate**. Grace drafts; she never sends to a client. Prohibition, not a gate. |
| **`tess-add` / TESS write** | Mutates the CRM = business-data write. Grace is read-the-world, not write-the-business. |
| **`lastminute_com` booking / change_flight** | Can **commit a booking** = financial-commit gate. Also redundant — our own price skills cover lookups without the booking surface. |
| **`n8n`** | Triggers wing automations/sends. A public persona must not be able to fire internal workflows. |
| **General shell (`run_shell_command` / Bash)** | The master key. A shell defeats *every other fence* — it can read `.env`, the dossiers, escape the jail. If Grace ever needs to run code, it gets a separate jailed executor, never raw shell. |
| **Repo file access (`read_file`/`write_file` outside jail)** | `dossiers/`, `config/`, `.env`, `hale_state.json` live in the repo. Grace is jailed to `grace_sandbox/` so she physically cannot read them. |
| **Browser with D2M portal sessions/cookies** | The browser tool is allowed for *public* sites; it must never use logged-in Regent/Centrav/TESS sessions — that would back-door the vault through the browser. |
| **Figma** | Not excluded for safety — excluded as YAGNI. Add later if a real need appears (lean-stack discipline). |

---

## The fences, in three lines
1. **Tool allowlist** — the ~10 vault/send/spend tools above are simply not wired to her.
2. **Sandbox identity + jail** — she runs from `grace_sandbox/` (own `.gemini/settings.json`), her Drive/Calendar are her own empty space, file ops can't leave the jail.
3. **Gates still bind** — no client send, no financial commit, ever. Drafting and lookups only.

## Cost
Free Gemini Flash, shared D2M key, **hard cap 15K/day**. Cost risk to D2M ≈ $0; reaching the cap is unlikely. (Commander call, 2026-06-14.)

## Honest status
- **Working now:** safe text Grace, jailed to the sandbox (`grace.sh`).
- **Staged (needs build):** wiring the allowlisted *action* tools (price skills, browser, web fetch) into Grace's runtime as a controlled agent — because the native Gemini CLI toolset is exactly what we're fencing off. This is a follow-on build, speced here.
- **Needs one Commander step:** a separate Google account for Grace's sandbox Drive/Calendar (so they're provably not the business accounts). Until then, text + lookups work; sandbox Drive/Calendar wait.

---

## PRIVACY & POSITIONING DECISIONS (Commander, 2026-06-14)

**1. Stay on FREE tier for now.** Grace remains on free Gemini. The no-train data path (paid Gemini billing or Vertex with data governance) is the documented **evolution decision** — folded into the plan, NOT executed. "We will decide how to evolve her." (Free tier *does* train on conversations — that is why #2 and #3 are mandatory.)

**2. Honest disclosure — MANDATORY (Padre's rule).** Because she's on the free tier, every Grace touchpoint tells the truth in plain words: powered by Google's free assistant → conversation is sent to Google to create answers → don't share account numbers/SSN/full medical or financial details → D2M never stores conversations or uses them to sell anything. (Now in the intro email.)

**3. NO FALSE CLAIMS — advertise only what's true.** Commander + Padre. Do NOT claim: "private" (free tier trains), "smarter than Gemini" (she IS Gemini), or "she remembers you" (**memory is NOT built**). Pulled the memory line from the email for this reason.

**What we MAY honestly claim (true today):** a warm, consistent voice (not cold/generic); a real person (John) stands behind her; she's openly an AI, a *different kind*; patient, takes her time, never makes you feel behind; no ads, no upsell, D2M harvests nothing to market to you; a free gift, nothing owed.

**Evolution options (Commander to decide later, not claimed until built):**
- **Memory** (the "she remembers you" differentiator) — requires build WITH encryption-at-rest, per-user isolation, one-tap delete. Memory + privacy are one project.
- **No-train tier** — makes "private" honest and is the real edge over free Gemini. Same fix answers both "is she private" and "why not just use Gemini."

**Browser link:** Buddy not yet hosted → email ships with email-contact only, link marked "coming soon." Hosting = the one open follow-up.
