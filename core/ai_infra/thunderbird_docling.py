#!/usr/bin/env python3
"""
thunderbird_docling.py — Docling PDF/document extraction adapter.
IBM Research Apache-2.0. Converts cruise brochures, deck plans, and
policy PDFs into structured markdown for downstream AI processing.

Usage:
    from core.ai_infra.thunderbird_docling import extract_pdf, extract_url
    md = extract_pdf("/path/to/deck_plan.pdf")
    md = extract_url("https://example.com/brochure.pdf")
"""
from __future__ import annotations
from pathlib import Path
from typing import Union


def extract_pdf(path: Union[str, Path], export_format: str = "markdown") -> str:
    """Extract text/structure from a PDF file using Docling."""
    from docling.document_converter import DocumentConverter
    converter = DocumentConverter()
    result = converter.convert(str(path))
    if export_format == "markdown":
        return result.document.export_to_markdown()
    return result.document.export_to_text()


def extract_url(url: str, export_format: str = "markdown") -> str:
    """Extract text/structure from a URL (PDF or HTML) using Docling."""
    from docling.document_converter import DocumentConverter
    converter = DocumentConverter()
    result = converter.convert(url)
    if export_format == "markdown":
        return result.document.export_to_markdown()
    return result.document.export_to_text()


def extract_batch(paths: list, export_format: str = "markdown") -> dict:
    """Extract multiple documents. Returns {path: markdown_text}."""
    from docling.document_converter import DocumentConverter
    converter = DocumentConverter()
    out = {}
    for p in paths:
        try:
            result = converter.convert(str(p))
            out[str(p)] = result.document.export_to_markdown() if export_format == "markdown" else result.document.export_to_text()
        except Exception as e:
            out[str(p)] = f"ERROR: {e}"
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 thunderbird_docling.py <path_or_url>")
        sys.exit(1)
    target = sys.argv[1]
    if target.startswith("http"):
        print(extract_url(target))
    else:
        print(extract_pdf(target))
