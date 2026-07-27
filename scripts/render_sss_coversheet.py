#!/usr/bin/env python3
"""
USAF Staff Summary Sheet (AF Form 1768) Visual Coversheet Generator
Supports 3-Star Commander Monikers, Moniker Badges, Substantive Comments, and Signatures.
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
    lines.append(" COORDINATION & 3-STAR COMMANDER CHOP CHAIN (NO BLANKET COORDS ACCEPTED):")
    lines.append("--------------------------------------------------------------------------------")
    if not chops:
        lines.append(" (No chops recorded yet)")
    else:
        for c in chops:
            office = c.get('office', 'N/A')
            verdict = c.get('status', c.get('verdict', 'N/A')).upper()
            comment = c.get('comment', 'No comment provided')
            sig = c.get('signature', f"— {office}")
            
            # Commander Moniker Badges
            moniker = ""
            if "TALON" in office or "CC" in office:
                moniker = "🦅 [TALON-3★ | CONDOR WING COMMANDER]"
            elif "JET" in office or "OC" in office:
                moniker = "⚡ [JET-3★ | WIND GROUP COMMANDER]"
            elif "Commander" in office or "YODA" in office:
                moniker = "⭐ [COMMANDER YODA | SECAF/CSAF]"
            else:
                moniker = f"📌 [{office}]"

            lines.append(f" COMMANDER / OFFICE : {moniker}")
            lines.append(f" VERDICT            : {verdict}")
            lines.append(f" SUBSTANTIVE REMARKS: {comment}")
            lines.append(f" SIGNATURE          : {sig}")
            lines.append(" ------------------------------------------------------------------------------")
    lines.append("================================================================================")
    return "\n".join(lines)

def main():
    sample = render_ascii_sss(
        sss_id="SSS-007",
        title="Operational Deployment of 3-Star Commander Independence Protocols & Signatures",
        opr="HALE-AG (4-Star Lead)",
        action="APPR",
        suspense="2026-08-01",
        status="accomplished",
        chops=[
            {
                "office": "TALON (CC)",
                "verdict": "concur_with_comment",
                "comment": "Fully concur with 4-Star lead strategy. CONDOR Wing requires direct visual QC veto on all Dani 6-step products before WF-17.",
                "signature": "— Lt Gen TALON, Commander CONDOR Wing"
            },
            {
                "office": "JET (OC)",
                "verdict": "concur",
                "comment": "WIND Group support infrastructure is locked. DeepSeek-v4 fallback route benchmarked at 1.2s per script sweep.",
                "signature": "— Lt Gen JET, Commander WIND Group"
            },
            {
                "office": "Commander Yoda",
                "verdict": "APPROVED",
                "comment": "Approved for full operational adoption across Thunderbird Wing.",
                "signature": "— John A. Loucks III, SecAF/CSAF Fused (LLC Owner)"
            }
        ]
    )
    print(sample)

if __name__ == "__main__":
    main()
