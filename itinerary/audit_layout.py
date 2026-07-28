"""
audit_layout.py — Automated PDF Layout & Page-Break Auditor
Dreams2Memories Travel, LLC | Thunderbird Wing
"""

import sys
import subprocess
from pathlib import Path

def audit_pdf(pdf_path: str, max_pages: int = 5) -> dict:
    """Audit compiled PDF properties (page count and dimensions) using pdfinfo."""
    path = Path(pdf_path)
    if not path.exists():
        return {"status": "ERROR", "message": f"PDF file not found at '{pdf_path}'"}
        
    try:
        # Run system pdfinfo tool to extract metadata
        res = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=True)
        metadata = {}
        for line in res.stdout.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                metadata[k.strip().lower()] = v.strip()
                
        pages = int(metadata.get("pages", 0))
        page_size = metadata.get("page size", "unknown")
        
        status = "PASS"
        issues = []
        
        if pages > max_pages:
            status = "WARN"
            issues.append(f"Page count ({pages}) exceeds expected limit ({max_pages}). Check for trailing empty pages.")
            
        return {
            "status": status,
            "pages": pages,
            "page_size": page_size,
            "issues": issues,
            "message": f"Audited successfully. Pages: {pages}, Page Size: {page_size}."
        }
    except Exception as e:
        return {"status": "ERROR", "message": f"Failed running pdfinfo: {e}"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 audit_layout.py <path_to_pdf> [max_pages]")
        sys.exit(1)
    
    target_pdf = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    audit = audit_pdf(target_pdf, limit)
    print("Audit result:", audit)
