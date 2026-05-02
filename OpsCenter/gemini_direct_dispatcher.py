#!/usr/bin/env python3
"""
gemini_direct_dispatcher.py — Direct Gemini 1.5 Flash via Service Account
==========================================================================
Brain 1 (Ops): Replaces DeepSeek entirely.
- Research, data extraction, bulk analysis, routine reports
- Direct Google Generative AI API via service account JWT
- Cost: Free tier + $0.075/1M tokens after quota
- Zero intermediary fees, no API key leakage

Usage:
    from gemini_direct_dispatcher import dispatch_to_gemini
    result = dispatch_to_gemini("Analyze cruise lines...", mission_id="MISSION-001")
"""

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Optional
import base64
import hmac
import hashlib

log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
GEMINI_TIMEOUT_SECS = 120

BASE_DIR = Path(__file__).parent.parent
SERVICE_ACCOUNT_FILE = Path("/home/john/Thunderbird/.service_account_gemini.json")

# Cache for access token (expires in 1 hour)
_access_token_cache = {"token": None, "expires_at": 0}


def _load_service_account() -> dict:
    """Load service account JSON from disk."""
    if not SERVICE_ACCOUNT_FILE.exists():
        raise FileNotFoundError(f"Service account not found at {SERVICE_ACCOUNT_FILE}")
    with open(SERVICE_ACCOUNT_FILE) as f:
        return json.load(f)


def _get_access_token() -> str:
    """Get Google OAuth2 access token using service account JWT (openssl-based)."""
    # Check cache
    current_time = time.time()
    if _access_token_cache["token"] and current_time < _access_token_cache["expires_at"]:
        return _access_token_cache["token"]

    # Load service account
    sa = _load_service_account()

    # Create JWT header and payload
    header = {"alg": "RS256", "typ": "JWT"}
    payload = {
        "iss": sa["client_email"],
        "scope": "https://www.googleapis.com/auth/generative-language",
        "aud": "https://oauth2.googleapis.com/token",
        "exp": int(current_time) + 3600,
        "iat": int(current_time),
    }

    # Encode header and payload in base64url
    import base64
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    message = f"{header_b64}.{payload_b64}"

    # Sign with openssl using private key
    try:
        # Write private key to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            f.write(sa["private_key"])
            key_file = f.name

        # Sign the message
        sign_result = subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", key_file],
            input=message.encode(),
            capture_output=True,
            timeout=5,
        )

        if sign_result.returncode != 0:
            raise Exception(f"OpenSSL signing failed: {sign_result.stderr.decode()}")

        # Base64url encode signature
        signature_b64 = base64.urlsafe_b64encode(sign_result.stdout).decode().rstrip("=")
        token = f"{message}.{signature_b64}"

        # Cleanup
        os.unlink(key_file)

    except Exception as e:
        log.error(f"JWT signing failed: {e}")
        raise

    # Exchange JWT for access token
    token_response = subprocess.run(
        [
            "curl",
            "-s",
            "-X", "POST",
            "https://oauth2.googleapis.com/token",
            "-d", f"grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion={token}",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    try:
        token_data = json.loads(token_response.stdout)
        if "error" in token_data:
            raise Exception(f"Token exchange failed: {token_data.get('error_description', token_data.get('error'))}")

        access_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 3600)

        # Cache the token
        _access_token_cache["token"] = access_token
        _access_token_cache["expires_at"] = current_time + expires_in - 60

        return access_token
    except Exception as e:
        log.error(f"Failed to get access token: {e}")
        raise


def dispatch_to_gemini(task_text: str, mission_id: str = None, max_tokens: int = 8000) -> str:
    """
    Call Gemini 1.5 Flash API directly via service account.

    Args:
        task_text: The task prompt
        mission_id: Optional mission ID for logging
        max_tokens: Max output tokens (default 8000, max 16000)

    Returns:
        str: Response text from Gemini, or error message
    """
    try:
        # Get access token
        access_token = _get_access_token()
    except Exception as e:
        err = f"Failed to authenticate: {str(e)}"
        log.error(err)
        return f"ERROR: {err}"

    # Build request payload
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": task_text
                    }
                ]
            }
        ],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 1.0,
        }
    }

    try:
        # Call Gemini API with bearer token
        curl_cmd = [
            "curl",
            "-s",
            "-X", "POST",
            "-H", "Content-Type: application/json",
            "-H", f"Authorization: Bearer {access_token}",
            "-d", json.dumps(payload),
            GEMINI_ENDPOINT,
        ]

        log.info(f"[{mission_id}] Dispatching to Gemini 1.5 Flash (service account)")

        result = subprocess.run(
            curl_cmd,
            capture_output=True,
            text=True,
            timeout=GEMINI_TIMEOUT_SECS,
            cwd=str(BASE_DIR)
        )

        if result.returncode != 0:
            err = f"Gemini API call failed: {result.stderr}"
            log.error(f"[{mission_id}] {err}")
            return f"ERROR: {err}"

        # Parse response
        try:
            response = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            err = f"Invalid JSON from Gemini: {result.stdout[:200]}"
            log.error(f"[{mission_id}] {err}")
            return f"ERROR: {err}"

        # Check for API errors
        if "error" in response:
            err_msg = response["error"].get("message", "Unknown error")
            log.error(f"[{mission_id}] Gemini API error: {err_msg}")
            return f"ERROR: {err_msg}"

        # Extract text from response
        try:
            content = response["candidates"][0]["content"]["parts"][0]["text"]
            log.info(f"[{mission_id}] Gemini response received ({len(content)} chars)")
            return content
        except (KeyError, IndexError) as e:
            err = f"Unexpected response structure: {result.stdout[:300]}"
            log.error(f"[{mission_id}] {err}")
            return f"ERROR: {err}"

    except subprocess.TimeoutExpired:
        err = f"Gemini timeout after {GEMINI_TIMEOUT_SECS}s"
        log.error(f"[{mission_id}] {err}")
        return f"ERROR: {err}"

    except Exception as e:
        err = str(e)
        log.error(f"[{mission_id}] Unexpected error: {err}")
        return f"ERROR: {err}"


def dispatch_to_gemini_batch(tasks: list[dict]) -> list[dict]:
    """
    Dispatch multiple tasks to Gemini in sequence (respects rate limits).

    Args:
        tasks: List of {"text": str, "mission_id": str, "max_tokens": int}

    Returns:
        List of {"mission_id": str, "result": str}
    """
    results = []
    for task in tasks:
        result = dispatch_to_gemini(
            task.get("text", ""),
            mission_id=task.get("mission_id"),
            max_tokens=task.get("max_tokens", 8000)
        )
        results.append({
            "mission_id": task.get("mission_id"),
            "result": result
        })
        # Small delay between requests to avoid rate limiting
        time.sleep(0.5)
    return results


if __name__ == "__main__":
    # Test
    test_prompt = "List 3 factors that influence cruise line pricing. Be concise."
    result = dispatch_to_gemini(test_prompt, mission_id="TEST-001")
    print(result)
