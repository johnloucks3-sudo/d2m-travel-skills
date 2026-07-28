#!/usr/bin/env python3
import json
import re
from pathlib import Path

def parse_master_dossier():
    dossier_path = Path("/home/john/Thunderbird/validations/rssc_scrape/master_dossier.md")
    if not dossier_path.exists():
        print("Dossier path does not exist!")
        return {}
    
    content = dossier_path.read_text(encoding="utf-8")
    
    # Split by H1 headers
    h1_sections = re.split(r'\n# ', '\n' + content)
    
    ship_txt = ""
    port_sections_txt = []
    excursions_txt = ""
    
    for sec in h1_sections:
        sec = sec.strip()
        if not sec:
            continue
        if "Ship Dossier" in sec:
            ship_txt = sec
        elif "Excursions" in sec:
            excursions_txt = sec
        elif "Port" in sec:
            port_sections_txt.append(sec)
            
    print(f"Isolated: Ship Dossier, {len(port_sections_txt)} Port Dossier(s), Excursions Dossier")

    # 1. Parse Ship
    ship_data = {
        "overview": "",
        "suites": [],
        "dining": [],
        "decks": ""
    }
    if ship_txt:
        # Split by ##
        ship_h2 = re.split(r'\n## ', ship_txt)
        for h2 in ship_h2:
            h2 = h2.strip()
            if h2.startswith("1. Ship Overview"):
                ship_data["overview"] = "\n".join(h2.split("\n")[1:]).strip()
            elif h2.startswith("2. Accommodations"):
                suites_lines = h2.split("\n")[1:]
                ship_data["suites"] = [l.strip("* -").strip() for l in suites_lines if l.strip().startswith(('*', '-'))]
            elif h2.startswith("3. Dining Venues"):
                dining_lines = h2.split("\n")[1:]
                ship_data["dining"] = [l.strip("* -").strip() for l in dining_lines if l.strip().startswith(('*', '-'))]
            elif h2.startswith("4. Deck Plans"):
                ship_data["decks"] = "\n".join(h2.split("\n")[1:]).strip()

    # 2. Parse Ports
    port_details = {}
    port_keys = [
        ("Athens", ["Athens"]),
        ("Valletta", ["Valletta"]),
        ("Naples", ["Naples"]),
        ("Rome", ["Rome"]),
        ("Tuscany", ["Tuscany"]),
        ("Cannes", ["Cannes"]),
        ("Barcelona", ["Barcelona"]),
        ("Malaga", ["Málaga", "Malaga"]),
        ("Portimao", ["Portimão", "Portimao"]),
        ("Lisbon", ["Lisbon"]),
        ("Ponta Delgada", ["Ponta Delgada"]),
        ("St. John's", ["St. John's"]),
        ("Sydney", ["Sydney"]),
        ("Halifax", ["Halifax"]),
        ("Boston", ["Boston"]),
        ("Newport", ["Newport"]),
        ("New York", ["New York"])
    ]

    for p_sec in port_sections_txt:
        blocks = re.split(r'\n## ', p_sec)
        for block in blocks[1:]:
            lines = block.strip().split('\n')
            if not lines:
                continue
            title = lines[0].strip()
            
            # Find matched port key
            matched_port = None
            for pk, aliases in port_keys:
                if any(alias in title for alias in aliases):
                    matched_port = pk
                    break
            
            if not matched_port:
                continue
                
            info_lines = []
            romance_lines = []
            highlights = []
            img_url = ""
            
            current_mode = None
            
            for line in lines[1:]:
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                
                # Check for section boundaries
                if "Port Info" in line or "Port Information" in line:
                    current_mode = "info"
                    inline = re.sub(r'^.*Port Info(rmation)?:\s*\*\*?', '', line).strip()
                    if inline:
                        info_lines.append(inline)
                    continue
                elif "Port Romance" in line:
                    current_mode = "romance"
                    inline = re.sub(r'^.*Port Romance(\s*&\s*Marketing Copy)?:\s*\*\*?', '', line).strip()
                    if inline:
                        romance_lines.append(inline)
                    continue
                elif "Key Highlights" in line or "Highlights:" in line:
                    current_mode = "highlights"
                    continue
                elif "Image URL" in line or "Image:" in line:
                    current_mode = "image"
                    inline = re.sub(r'^.*Image URL:\s*\*\*?', '', line).strip()
                    inline = inline.strip('`* ')
                    if inline:
                        img_url = inline
                    continue
                elif line_stripped.startswith("!["):
                    img_match = re.search(r'\(([^)]+)\)', line_stripped)
                    if img_match:
                        img_url = img_match.group(1).strip()
                    continue
                
                # Parse lines under current mode
                if current_mode == "highlights" and line_stripped.startswith(('*', '-', '1.', '2.', '3.', '4.')):
                    # Strip leading bullet indicators (but keep inner styling)
                    clean_hl = line_stripped
                    if clean_hl.startswith(('* ', '- ')):
                        clean_hl = clean_hl[2:]
                    elif re.match(r'^\d+\.\s*', clean_hl):
                        clean_hl = re.sub(r'^\d+\.\s*', '', clean_hl)
                    clean_hl = clean_hl.strip()
                    if clean_hl:
                        highlights.append(clean_hl)
                elif current_mode == "info":
                    info_lines.append(line_stripped)
                elif current_mode == "romance":
                    romance_lines.append(line_stripped)
            
            # Clean images: extract first URL if multiple or formatting present
            if not img_url or "Image URLs" in img_url or "High-Quality" in img_url:
                urls = re.findall(r'https?://[^\s`"()[\]]+', block)
                for url in urls:
                    if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']) or 'unsplash.com' in url or 'images.unsplash' in url:
                        img_url = url
                        break
            
            port_details[matched_port] = {
                "info": " ".join(info_lines).strip().strip('* '),
                "romance": " ".join(romance_lines).strip().strip('* '),
                "highlights": highlights,
                "img": img_url
            }

    # 3. Parse Excursions
    excursions = {}
    if excursions_txt:
        p_sections = re.split(r'\n## ', excursions_txt)
        for p_sec in p_sections[1:]:
            p_lines = p_sec.strip().split('\n')
            p_title = p_lines[0].strip()
            
            matched_port = None
            for pk, aliases in port_keys:
                if any(alias in p_title for alias in aliases):
                    matched_port = pk
                    break
            
            if matched_port:
                # Find all excursions (###)
                exc_blocks = re.split(r'\n### ', '\n' + p_sec)
                port_excs = []
                for e_block in exc_blocks[1:]:
                    e_lines = e_block.strip().split('\n')
                    if not e_lines:
                        continue
                    e_title = e_lines[0].strip()
                    e_body = "\n".join(e_lines[1:])
                    
                    marketing = ""
                    m_match = re.search(r'\*\*Marketing Copy:\*\*\s*"([^"]+)"', e_body)
                    if m_match:
                        marketing = m_match.group(1)
                    
                    desc = ""
                    d_match = re.search(r'(?:\*\s*)?\*\*Description:\*\*\s*(.+)', e_body)
                    if d_match:
                        desc = d_match.group(1).strip().strip('"* ')
                        
                    duration = ""
                    dur_match = re.search(r'(?:\*\s*)?\*\*Duration:\*\*\s*(.+)', e_body)
                    if dur_match:
                        duration = dur_match.group(1).strip().strip('"* ')
                        
                    price = ""
                    pr_match = re.search(r'(?:\*\s*)?\*\*Pricing Tier:\*\*\s*(.+)', e_body)
                    if pr_match:
                        price = pr_match.group(1).strip().strip('"* ')
                        
                    port_excs.append({
                        "name": e_title,
                        "marketing": marketing,
                        "description": desc,
                        "duration": duration,
                        "price": price
                    })
                excursions[matched_port] = port_excs

    # Package everything
    dossier_data = {
        "ship": ship_data,
        "ports": port_details,
        "excursions": excursions
    }
    
    # Save to JSON
    json_path = Path("/home/john/Thunderbird/itinerary/dossier_data.json")
    json_path.write_text(json.dumps(dossier_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved parsed dossier data to {json_path}")

if __name__ == "__main__":
    parse_master_dossier()
