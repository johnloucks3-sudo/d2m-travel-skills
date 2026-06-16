# IOI — Gemini Free Research Lane (Reyes A8 + Dembe A2)
*Internal Operating Instruction · Hale · 2026-06-14 · Free Gemini 2.5 Flash, $0, 1,500/day*

## What this is
A **first-pass research/scaffolding** tool on the free Gemini Flash tier. It produces raw, confidence-tagged research that the domain owner refines. It is **NOT** a client-copy tool and **NOT** a primary source.

## Who uses it
- **Reyes (A8)** — experience layer: excursions, dining, accessibility/mobility, port-readiness, upsell flags.
- **Dembe (A2)** — intel: destination/port intel, logistics, timing, weather, risk, competitor offerings.

## How to call it
```bash
gresearch reyes "accessible Santorini excursions for limited-mobility seniors"
gresearch dembe "Panama Canal cruise port intel Dec 2026 — weather, tendering, risk"
cat dossiers/<client>.md | gresearch reyes "accessibility notes for these ports"
```
(`gresearch` → `scripts/gemini_research.sh`. Quick non-research lookups → `gmn`.)

## Hard rules (SO-PIPELINE-INTEGRITY)
1. Output is a **draft for an expert**, never final client copy.
2. Every substantive claim is tagged **[CONFIRMED] / [INFERRED] / [UNKNOWN]**. UNKNOWN/INFERRED items MUST be verified against a primary source (cruise portal / TESS / dossier) before they touch a client product.
3. Booking-specific facts (tender port, dates, vendor, price) are **always [UNKNOWN]** until verified — Gemini does not know the specific booking.
4. This lane feeds the **creative chain** (Reyes → Luna → Naia → Dani → TALON/JET → WF-17). It does not bypass it.
5. Free Flash = Haiku-tier. Great for breadth/scaffolding; weak for client voice. Voice/synthesis stays Claude.

## Config notes
- Key: authoritative `GEMINI_API_KEY` from `.env` (stale `.bashrc` override removed 2026-06-14).
- Tools (web search / shell / file) are **disabled** in `~/.gemini/settings.json` — free key has no Search grounding; pure text generation only.
- First call in a shell warms up ~10–15s; subsequent calls fast.
