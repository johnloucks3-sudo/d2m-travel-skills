#!/usr/bin/env python3
"""
thunderbird_llamaparse.py — LlamaParse PDF extraction adapter.
LlamaIndex cloud API. Superior table/form extraction vs raw pypdf.
LLAMA_CLOUD_API_KEY required (active in .env).

Usage:
    from core.ai_infra.thunderbird_llamaparse import parse_pdf, parse_pdf_sync
    docs = await parse_pdf("path/to/document.pdf")
    docs = parse_pdf_sync("path/to/document.pdf")  # blocking
"""
from __future__ import annotations
import os
from pathlib import Path

_ENV = Path(__file__).parent.parent.parent / ".env"


def _get_api_key() -> str:
    val = os.environ.get("LLAMA_CLOUD_API_KEY", "")
    if val:
        return val
    try:
        for line in _ENV.read_text().splitlines():
            if line.startswith("LLAMA_CLOUD_API_KEY=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def parse_pdf_sync(
    path: str,
    result_type: str = "markdown",
    num_workers: int = 4,
    verbose: bool = False,
) -> list:
    """
    Parse a PDF with LlamaParse (blocking). Returns list of Document objects.
    result_type: "markdown" or "text"
    """
    from llama_parse import LlamaParse
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("LLAMA_CLOUD_API_KEY not set in .env")
    parser = LlamaParse(
        api_key=api_key,
        result_type=result_type,
        num_workers=num_workers,
        verbose=verbose,
    )
    return parser.load_data(path)


async def parse_pdf(
    path: str,
    result_type: str = "markdown",
    verbose: bool = False,
) -> list:
    """Parse a PDF with LlamaParse (async). Returns list of Document objects."""
    from llama_parse import LlamaParse
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("LLAMA_CLOUD_API_KEY not set in .env")
    parser = LlamaParse(
        api_key=api_key,
        result_type=result_type,
        verbose=verbose,
    )
    return await parser.aload_data(path)


def extract_text(path: str) -> str:
    """Convenience: parse PDF and return joined markdown text."""
    docs = parse_pdf_sync(path)
    return "\n\n".join(d.text for d in docs)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 thunderbird_llamaparse.py <path.pdf>")
        sys.exit(1)
    print(extract_text(sys.argv[1]))
