#!/usr/bin/env python3
"""
Extract Claude OAuth token from Claude Desktop configuration
"""

import json
import os
import base64
import sys


def extract_claude_oauth():
    """Extract OAuth token from Claude Desktop config"""

    config_path = os.path.expanduser("~/.config/Claude/config.json")

    if not os.path.exists(config_path):
        print("Error: Claude config.json not found")
        return None

    try:
        with open(config_path, "r") as f:
            config = json.load(f)

        # OAuth token is stored in oauth:tokenCache field
        if "oauth:tokenCache" in config:
            token_cache = config["oauth:tokenCache"]
            print(f"Found OAuth token cache in config.json")

            # The token appears to be base64 encoded
            try:
                decoded = base64.b64decode(token_cache).decode("utf-8", errors="ignore")
                print(f"Token cache decoded (first 200 chars): {decoded[:200]}")

                # Try to find the actual token in the decoded data
                # Claude stores tokens in a specific format
                if "sk-ant-api" in decoded:
                    token_start = decoded.find("sk-ant-api")
                    token_end = (
                        decoded.find('"', token_start)
                        if '"' in decoded[token_start:]
                        else decoded.find(" ", token_start)
                    )
                    if token_end == -1:
                        token_end = len(decoded)

                    token = decoded[token_start:token_end].strip()
                    print(f"Extracted token: {token[:50]}...")
                    return token

            except Exception as e:
                print(f"Error decoding token: {e}")

        print("No OAuth token found in config")
        return None

    except Exception as e:
        print(f"Error reading config: {e}")
        return None


def test_claude_with_token(token):
    """Test if the extracted token works with Claude"""
    if not token:
        return False

    try:
        # Run claude with the token
        env = os.environ.copy()
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("ANTHROPIC_BASE_URL", None)

        import subprocess

        result = subprocess.run(
            ["claude", "--dangerously-skip-permissions", "-p", "test"],
            env=env,
            capture_output=True,
            timeout=10,
        )

        if result.returncode == 0:
            print("✓ Token works with Claude!")
            return True
        else:
            print(f"✗ Token failed with Claude: {result.stderr.decode()[:100]}")
            return False

    except Exception as e:
        print(f"Error testing token: {e}")
        return False


def write_thunderbird_cache(token):
    """Write token to Thunderbird cache location"""
    cache_path = "/home/john/Thunderbird/OpsCenter/.claude_oauth_cache"

    if token:
        try:
            with open(cache_path, "w") as f:
                f.write(f"CLAUDE_CODE_OAUTH_TOKEN={token}")
            print(f"✓ Wrote token to {cache_path}")
            return True
        except Exception as e:
            print(f"Error writing cache: {e}")
            return False
    return False


if __name__ == "__main__":
    print("Extracting Claude OAuth token...")
    token = extract_claude_oauth()

    if token:
        print(f"\nTesting token...")
        if test_claude_with_token(token):
            print("\nWriting to Thunderbird cache...")
            write_thunderbird_cache(token)
            print("✅ OAuth token extracted and cached successfully")
        else:
            print("❌ Token does not work with Claude")
            sys.exit(1)
    else:
        print("❌ No OAuth token found")
        sys.exit(1)
