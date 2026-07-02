# ELON Adoption Recommendations — W7 Sector Research
*A12 Technology Vanguard · 2026-07-02 · Sectors D (Agentic Apps) · F (LLM) · G (Travel B2B)*
*Posture: adopt-biased (SO Tech Vanguard Elevation 2026-06-21). Burden is on Sterling to show concrete harm.*

---

## ADOPT NOW

1. **Hybrid confidence-tiered email loop** (Sector D). Finish what commits `1eb2b7e93`/`27801906e` started: rules-first tier 1 → **confidence-scored** classifier → below-threshold mail NEVER auto-drafts, surfaces to Hale with reasoning. This is the 2026 industry-standard email-agent pattern and the direct fix for our 3-fault email diagnosis (326 junk missions, buried Kim Westbrook). WF-17 is already our human-in-loop gate. *Owner: Sterling build / Hale route. No new dependency — refactor of existing code.*

2. **Fix cc-fleet config → unblock MISSION-814** (Sector D). cc-fleet works; our Groq/Cerebras rejection is a config/endpoint/key mismatch, not a tool defect. Run `ccf doctor`, switch registered providers to presets (auto-fills endpoint+protocol), verify free-tier keys. Payoff: route non-critical agent work (log scans, bulk classification, file digests) to **free/cheap third-party models** — pure token-discipline win, zero Anthropic spend on grunt work. *Owner: ELON diagnose / Sterling gate. Config fix, ~1 session.*

3. **Opus 4.8 dispatch-code fix** (Sector F). Audit `dispatch_claude.py` + headless spawn code for hardcoded `thinking: {budget_tokens}` — it **400s on Opus 4.8**. Replace with the `effort` parameter (adaptive thinking). Also drop cache floor to 1,024 tok. *Owner: Sterling. Small, mandatory — silent breakage risk if we route to 4.8 with old code.*

## TRIAL

4. **Sonnet 5 as synthesis default** (Sector F). Released 2026-06-30. Benchmark vs Sonnet 4.6 on our two live lanes: client-voice copy + multi-source synthesis. If parity-or-better at same/lower cost, promote to default; else stay 4.6. *Owner: ELON+Whetstone fleet. Trial, not adopt — verify pricing/context first (not yet in public sources).*

5. **Sabre SabreMosaic MCP layer** (Sector G) — *watch/trial only.* Built on Model Context Protocol = Claude-native, would plug into our stack with no adapter if we ever need GDS depth. We're host-portal based today, so this is a standing watch item, not an active trial. Revisit if a client need forces GDS-direct.

6. **Amadeus precomputed-fares pattern** (Sector G) — *pattern trial, not vendor adoption.* The industry is moving off live fare queries (they don't scale for AI agents) toward precomputed/cached feeds. Apply the *pattern* to our fare-watch CI: cache fares, don't hammer live sessions (root cause of the 27-day dead-Centrav masking). *Owner: Dembe (fare intel) + Sterling (CI).*

## KILL / KEEP-OFF

7. **Fable 5 — keep OFF the routing table** (Sector F). $10/$50 (5×/2× Opus), reasoning-only, and demonstrated export-control reliability risk (suspended 12 days in June). No justification for a 1-person shop; Opus 4.8 covers every ceiling case. *Do not add to dispatch.*

8. **No new orchestration framework** (Sector D). Do NOT adopt LangGraph/CrewAI/AutoGen/OpenAI-SDK. Our Claude Code subagent + headless-dispatch + persona stack IS our orchestration layer, and it's where our token discipline, WF-17 gate, and personas live. The frameworks confirmed our patterns (checkpointing, debate/verify, role DSL) are industry-standard — adopting one would be a costly rewrite for zero net capability. *Kill the idea, keep the validation.*

9. **No cruise-line / GDS API adoption** (Sector G). No Regent/Silversea API exists; Viking portal features already covered by our scrapers. Regent access stays a CloakBrowser/manual-auth problem (MISSION-214/820) — no vendor rescue coming. Keep current posture; keep CloakBrowser trial alive.

---

## Cross-Sector Thesis
The 2026 market is converging on the exact architecture the Wing already runs — hybrid deterministic+judgment agents, MCP-native orchestration, human-in-loop escalation, back-office automation behind a human relationship moat. Our edge is not building more; it's **finishing our email loop, cutting grunt-work cost via cc-fleet + free models, and staying razor-sharp on model changes (Opus 4.8 breakage, Sonnet 5 eval)** — while competitors like Virgin flood the client-facing layer with 1,500 agents that we deliberately don't need. Adopt at tempo, lead don't follow.

*— ELON, A12*
