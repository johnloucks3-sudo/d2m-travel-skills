#!/usr/bin/env python3
"""
Revert Spencer Intake Form to original baseline (removing Loucks Skybird quote).
"""
from pathlib import Path

def revert_spencer():
    html_path = Path("/home/john/Thunderbird/output/Spencer_GrandTour_2027/client/html/intake.html")
    index_path = Path("/home/john/Thunderbird/output/Spencer_GrandTour_2027/client/html/index.html")

    content = html_path.read_text()
    
    # Remove Skybird snippet from Spencer form
    marker_start = '<!-- SKYBIRD TRAVEL BRITISH AIRWAYS FEATURED BUSINESS CLASS OPTION -->'
    marker_end = '</div>\n      </div>'

    if marker_start in content:
        part1 = content.split(marker_start)[0]
        part2 = content.split('<!-- Group 1: Yaggi Family -->')[1]
        
        reverted_html = part1 + '<!-- Group 1: Yaggi Family -->' + part2
        html_path.write_text(reverted_html)
        index_path.write_text(reverted_html)
        print("✅ Spencer Intake Form reverted cleanly!")
    else:
        print("⚠️ Skybird snippet marker not found on Spencer form.")

if __name__ == "__main__":
    revert_spencer()
