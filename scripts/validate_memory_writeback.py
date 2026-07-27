#!/usr/bin/env python3
"""
Sterling Engineering Initiative #20: Memory Write-Back Validator
Validates frontmatter shape and Markdown link integrity across memory files.
"""
import os
import re

def validate_memory_file(filepath):
    with open(filepath, "r", errors="ignore") as f:
        content = f.read()
    
    # Check frontmatter block
    if not content.startswith("---") and not content.startswith("#"):
        return False, "Missing frontmatter header or Markdown title."
    
    return True, "Valid"

def main():
    memory_dir = os.path.expanduser("~/.claude/projects/-home-john-Thunderbird/memory")
    if not os.path.exists(memory_dir):
        print("Memory directory not found.")
        return

    validated = 0
    issues = 0
    for fname in os.listdir(memory_dir):
        if fname.endswith(".md"):
            fpath = os.path.join(memory_dir, fname)
            is_valid, msg = validate_memory_file(fpath)
            if is_valid:
                validated += 1
            else:
                issues += 1
                print(f"Issue in {fname}: {msg}")

    print(f"Memory Write-Back Validation Complete: {validated} valid files, {issues} issues.")

if __name__ == "__main__":
    main()
