#!/usr/bin/env python3
"""
Search Google Drive for client lifecycle-related files.
"""

import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

try:
    from api.thunderbird_drive import _get_drive_service
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


def search_drive(query, max_results=50):
    """Search Google Drive for files."""
    try:
        service = _get_drive_service()

        # Escape single quotes
        safe_query = query.replace("'", "\\'")

        # Search query - looking in name or full text
        q = f"(name contains '{safe_query}' or fullText contains '{safe_query}') and trashed = false"

        results = (
            service.files()
            .list(
                q=q,
                pageSize=min(max_results, 100),
                fields="files(id, name, mimeType, modifiedTime, size, webViewLink)",
                orderBy="modifiedTime desc",
            )
            .execute()
        )

        files = results.get("files", [])
        return files

    except Exception as e:
        print(f"Error searching Drive: {e}")
        return []


def main():
    # Search terms for client lifecycle files
    search_terms = [
        "lifecycle",
        "client lifecycle",
        "timeline",
        "Gantt",
        "anchor date",
        "FPD",
        "embark",
        "disembark",
        "Kuklinski",
        "Morton",
        "Furlow",
        "Nichols",
        "Ely",
        "Westbrook",
        "Silver Nova",
        "Lyons",
        "RSSC",
    ]

    print(f"Searching Google Drive for client lifecycle files...")
    print(f"Search terms: {', '.join(search_terms[:5])}...")
    print("-" * 80)

    all_files = []

    for term in search_terms:
        print(f"Searching for: '{term}'")
        files = search_drive(term, max_results=20)
        for file in files:
            # Add search term as reference
            file["matched_term"] = term
            all_files.append(file)

    # Remove duplicates by file ID
    unique_files = {}
    for file in all_files:
        file_id = file["id"]
        if file_id not in unique_files:
            unique_files[file_id] = file
        else:
            # Merge matched terms
            if file["matched_term"] not in unique_files[file_id]["matched_term"]:
                unique_files[file_id]["matched_term"] += f", {file['matched_term']}"

    # Sort by modified time
    sorted_files = sorted(
        unique_files.values(), key=lambda x: x.get("modifiedTime", ""), reverse=True
    )

    # Filter by file types we care about
    relevant_extensions = [".docx", ".html", ".md", ".txt", ".pdf"]
    filtered_files = []
    for file in sorted_files:
        name = file["name"].lower()
        mime = file.get("mimeType", "")
        # Check if it's a document type we care about
        if (
            any(name.endswith(ext) for ext in relevant_extensions)
            or "document" in mime
            or "html" in mime
            or "text" in mime
        ):
            filtered_files.append(file)

    print(f"\nFound {len(filtered_files)} relevant files:")
    print("=" * 80)

    for i, file in enumerate(filtered_files, 1):
        print(f"\n{i}. {file['name']}")
        print(f"   ID: {file['id']}")
        print(f"   Type: {file.get('mimeType', 'N/A')}")
        print(f"   Modified: {file.get('modifiedTime', 'N/A')}")
        print(f"   Size: {file.get('size', 'N/A')} bytes")
        print(f"   Link: {file.get('webViewLink', 'N/A')}")
        print(f"   Matched terms: {file.get('matched_term', 'N/A')}")

    # Save results to a file
    if filtered_files:
        output_file = Path(__file__).parent / "drive_search_results.json"
        with open(output_file, "w") as f:
            json.dump(filtered_files, f, indent=2)
        print(f"\nResults saved to: {output_file}")

    return len(filtered_files)


if __name__ == "__main__":
    main()
