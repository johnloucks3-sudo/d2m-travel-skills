#!/usr/bin/env python3
"""
USAF Staff Summary Sheet (AF Form 1768) Visual Coversheet Generator
Includes Official Moniker Badges & Signatures:
  • ⭐ COMMANDER YODA — SecAF / CSAF Fused (LLC Owner)
  • 👑 HALE-AG (4-Star Lead) — VCSAF / Lead Orchestrator
  • 🦅 TALON (3-Star) — CONDOR Wing Commander
  • ✈️ JET (3-Star) — F-22 Raptor WIND Group Commander
  • 🪶 CHIEF STERLING — Chief Master Sergeant of the Air Force (CMSAF / E-9 War Headdress)
"""
import sys
import json

def render_ascii_sss(sss_id, title, opr, action, suspense, status, chops=None):
    chops = chops or []
    lines = []
    lines.append("================================================================================")
    lines.append("                DEPARTMENT OF THE AIR FORCE — STAFF SUMMARY SHEET              ")
    lines.append("                              (AF FORM 1768)                                   ")
    lines.append("================================================================================")
    lines.append(f" SSS ID:    {sss_id:<30} SUSPENSE:  {suspense:<20}")
    lines.append(f" OPR:       {opr:<30} ACTION:    {action:<20}")
    lines.append(f" SUBJECT:   {title}")
    lines.append(f" STATUS:    {status.upper()}")
    lines.append("--------------------------------------------------------------------------------")
    lines.append(" COORDINATION & COMMAND STAFF CHOP CHAIN (NO BLANKET COORDS ACCEPTED):")
    lines.append("--------------------------------------------------------------------------------")
    if not chops:
        lines.append(" (No chops recorded yet)")
    else:
        for c in chops:
            office = c.get('office', 'N/A')
            verdict = c.get('status', c.get('verdict', 'N/A')).upper()
            comment = c.get('comment', 'No comment provided')
            sig = c.get('signature', f"— {office}")
            
            # Official Command Moniker & Badges
            moniker = ""
            if "TALON" in office or "CC" in office:
                moniker = "🦅 [TALON-3★ | CONDOR WING COMMANDER]"
            elif "JET" in office or "OC" in office:
                moniker = "✈️ [JET-3★ | F-22 RAPTOR WIND COMMANDER]"
            elif "STERLING" in office or "A7" in office or "Silver" in office:
                moniker = "🪶 [CHIEF STERLING | CMSAF / E-9 WAR HEADDRESS]"
            elif "HALE" in office or "AG" in office:
                moniker = "👑 [HALE-AG-4★ | LEAD ORCHESTRATOR / VCSAF]"
            elif "Commander" in office or "YODA" in office:
                moniker = "⭐ [COMMANDER YODA | SECAF/CSAF FUSED]"
            else:
                moniker = f"📌 [{office}]"

            lines.append(f" COMMAND STAFF / OFFICE : {moniker}")
            lines.append(f" VERDICT               : {verdict}")
            lines.append(f" SUBSTANTIVE REMARKS   : {comment}")
            lines.append(f" SIGNATURE             : {sig}")
            lines.append(" ------------------------------------------------------------------------------")
    lines.append("================================================================================")
    return "\n".join(lines)

def main():
    sample = render_ascii_sss(
        sss_id="SSS-008",
        title="Full Command Staff Alignment: JET F-22 Raptor & Chief Sterling CMSAF E-9 War Headdress Badges",
        opr="HALE-AG (4-Star Lead)",
        action="APPR",
        suspense="2026-08-01",
        status="accomplished",
        chops=[
            {
                "office": "TALON (CC)",
                "verdict": "concur",
                "comment": "CONDOR Wing client ops aligned. Dani 6-step chain active.",
                "signature": "— Lt Gen TALON, Commander CONDOR Wing"
            },
            {
                "office": "JET (OC)",
                "verdict": "concur",
                "comment": "F-22 Raptor WIND Group ready for high-speed DeepSeek-v4 infrastructure sweeps.",
                "signature": "— Lt Gen JET, Commander WIND Group (F-22 Raptor)"
            },
            {
                "office": "STERLING",
                "verdict": "concur_with_comment",
                "comment": "Enlisted force stands ready. Chief Silver front/back gates verified across all SSS packages.",
                "signature": "— Chief Master Sergeant Steve 'Silver' Sterling, CMSAF"
            },
            {
                "office": "Commander Yoda",
                "verdict": "APPROVED",
                "comment": "Full command staff roster approved and adopted across Thunderbird.",
                "signature": "— John A. Loucks III, SecAF/CSAF Fused (LLC Owner)"
            }
        ]
    )
    print(sample)

if __name__ == "__main__":
    main()
