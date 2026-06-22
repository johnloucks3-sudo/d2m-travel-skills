#!/usr/bin/env python3
"""
har_capture.py — Extract and replay authenticated API calls from HAR files.

Use case: Cruise line B2B portals without partner APIs (Princess, MSC, Norwegian).
  1. Log into portal in Firefox → DevTools → Network → Export HAR
  2. extract_api_calls(har, domain) → find authenticated endpoints
  3. replay_call(call) → pull live data with captured auth

Usage:
    from core.travel.har_capture import load_har, extract_api_calls, replay_call
    har = load_har("capture.har")
    calls = extract_api_calls(har, domain_filter="book.princess.com")
    result = replay_call(calls[0])
    print(result.json())
"""
import json
import requests
from pathlib import Path


def load_har(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def extract_api_calls(har: dict, domain_filter: str = "",
                      method_filter: str = "") -> list[dict]:
    """Extract API calls from a HAR file. Only JSON/XML responses included."""
    results = []
    for entry in har.get("log", {}).get("entries", []):
        req = entry.get("request", {})
        resp = entry.get("response", {})
        url = req.get("url", "")
        method = req.get("method", "GET")

        if domain_filter and domain_filter not in url:
            continue
        if method_filter and method.upper() != method_filter.upper():
            continue
        mime = resp.get("content", {}).get("mimeType", "")
        if "json" not in mime and "xml" not in mime:
            continue

        headers = {h["name"]: h["value"] for h in req.get("headers", [])}
        auth_header = headers.get("Authorization") or headers.get("Cookie", "")

        results.append({
            "url": url,
            "method": method,
            "headers": headers,
            "auth_header": auth_header,
            "body": req.get("postData", {}).get("text", ""),
            "response_status": resp.get("status"),
            "response_preview": resp.get("content", {}).get("text", "")[:200],
        })
    return results


def replay_call(call: dict, override_headers: dict = None) -> requests.Response:
    """Replay a captured API call with optional header overrides."""
    headers = dict(call.get("headers", {}))
    if override_headers:
        headers.update(override_headers)
    method = call.get("method", "GET").upper()
    body = call.get("body", "")
    r = requests.request(method, call["url"], headers=headers,
                         data=body.encode() if body else None, timeout=30)
    return r


def har_to_playbook(har_path: str | Path, domain: str,
                    output_path: str | Path = None) -> str:
    """Extract all API calls from a HAR and write a markdown playbook."""
    har = load_har(har_path)
    calls = extract_api_calls(har, domain_filter=domain)
    lines = [f"# HAR Playbook — {domain}",
             f"Extracted {len(calls)} authenticated API endpoints\n"]
    for i, c in enumerate(calls, 1):
        lines.append(f"## Call {i}: {c['method']} {c['url']}")
        auth = c['auth_header']
        lines.append(f"- Auth: `{auth[:60]}...`" if len(auth) > 60 else f"- Auth: `{auth}`")
        lines.append(f"- Response: HTTP {c['response_status']}")
        lines.append(f"- Preview: `{c['response_preview'][:100]}`\n")
    out = "\n".join(lines)
    if output_path:
        Path(output_path).write_text(out)
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: har_capture.py <har_file> <domain_filter> [output.md]")
        sys.exit(1)
    har_path, domain = sys.argv[1], sys.argv[2]
    out_path = sys.argv[3] if len(sys.argv) > 3 else None
    result = har_to_playbook(har_path, domain, out_path)
    if not out_path:
        print(result)
