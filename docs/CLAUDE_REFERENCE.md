# THUNDERBIRD — REFERENCE TABLES & SECTIONS
**Load on demand. Essential hard rules remain in CLAUDE.md only.**

---

## 1. Identity
- **Company:** Dreams2Memories Travel, LLC — EXCLUSIVE branding. NEVER "Love Group Travel."
- **Owner:** John Loucks ("Yoda") — Colorado Springs / Monument, CO
- **Contact:** johnloucks3@gmail.com · 719-291-0742 (work cell — cleared for all D2M emails, 2026-03-23)
- **Working Directory:** ~/Thunderbird/

---

## 2. The Wing — AI Staff
*Full roster, architecture rules, and 2026-05-13 transformation archived:* `/mem read reference_d2m_wing_structure_staff_roster`
**Slots:** COS=Hale · EXEC=Naia · A1=Navarro · A2=Dembe · A3=Dani · A5=Castillo · A6=Luna · A7=Sterling · A8=Reyes · A9=Harlan · A12=ELON · CH=Washington
**Key rules:** Dani=client-only · Luna→Naia→Hale→Dani mandatory · 12-SO cap · Hale: COS(AM)/COO(day)/EA(eve) · A9 runs commission audits (not Hale)

---

## 3. Behavioral Protocols
*8 Staff Skills, Code Standards, Booking Protocol archived:* `/mem read reference_behavioral_protocols_and_session_checklist`
**8 Skills (NON-NEGOTIABLE):** Diff→Principle→Forward · Ask · Debate/Align · Covey 5 · Learn · Dani=Agg/Artist/Adv
**Client output priority:** Words → Experience → Images → Inspiration

### Booking Protocol — Auto-Dossier (4 steps)
`dossiers/` update → Booking Master Sheet → `THUNDERBIRD_MASTER_PLAN.md` → Drive mirror

---

## 4. Commission Defaults

| Type | Rate |
|------|------|
| Standard hotels/cruises | 25% markup on net |
| Premium / SLH properties | 22% markup on net |
| Ponant agent commission | 16-20% base |
| EUR → USD | 1.09 default; verify live for quotes > $5,000 |

Formula: `client_price = net_usd * (1 + markup)` — code: `_apply_markup()` in search modules.

---

## 5. Architecture
See [docs/ARCHITECTURE_REFERENCE.md](docs/ARCHITECTURE_REFERENCE.md) for component table, YOGA/domains, MCP failure playbook.

---

## 6. AI Incubator Pipeline (Standing Order 2026-03-24)
See [docs/INCUBATOR_CADENCE.md](docs/INCUBATOR_CADENCE.md) for daily cadence, crew order, build queue.

---

## 6b. Intel Standards
See [docs/INTEL_STANDARDS.md](docs/INTEL_STANDARDS.md) for report structure, scope, staff paper format.

---

## 7. Targeted Cruise Lines
Silversea · Regent Seven Seas · Cunard · Oceania · Seabourn · Viking · AmaWaterways · Ponant

---

## 8. Session Checklist
*Full checklist + protocols archived:* `/mem read reference_behavioral_protocols_and_session_checklist`
Interview before major coding · `fmt_usd()` for USD · Photos as base64 URIs · D2M branding only · MCP fail: retry→alternate→alert

---

## 9. Agent Teams
See [docs/AGENT_TEAMS.md](docs/AGENT_TEAMS.md) for experimental team workflows.

---

## 10. Output Contract & Quality Standards (SO 2026-03-27)
*Full standards archived:* `/mem read reference_output_contract_quality_standards`
**Format:** Brief first · Telegram ≤4096 · Intel=JSON+hyperlinks · Staff papers=ISSUE/DISCUSSION/OPTIONS/ACTIONS · Client email=cream(#f7f3ea)/blue(#0000ff)/Georgia/navy banner · Sign-off="Thanks" NEVER "Best"
**NEVERS:** No outside-wing sends without Commander · No D2M client/ops drafts in johnloucks3 (personal assist drafts allowed under label WING-PERSONAL-DRAFT) · No "Love Group Travel" · No fabricated data · No Dani outside client role · No amended commits · No force-push

---

# RTK (Rust Token Killer)
Full command reference archived. Load when needed: `/mem read reference_rtk_token_killer_commands`
**Golden Rule:** Always prefix with `rtk`. Safe passthrough if no filter. Works in `&&` chains.
